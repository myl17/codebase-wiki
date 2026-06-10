---
type: view
category: ai-agent-frameworks
generated: 2026-06-09
sources: ["wiki/repos/openclaw/dimensions/openclaw-architecture.md","wiki/repos/openclaw/dimensions/openclaw-extension-points.md","wiki/repos/openclaw/dimensions/openclaw-performance-tradeoffs.md","wiki/repos/openclaw/dimensions/openclaw-dependency-strategy.md","wiki/repos/openclaw/dimensions/openclaw-testing-philosophy.md","wiki/repos/hermes-agent/dimensions/hermes-agent-architecture.md","wiki/repos/hermes-agent/dimensions/hermes-agent-extension-points.md","wiki/repos/hermes-agent/dimensions/hermes-agent-performance-tradeoffs.md","wiki/repos/hermes-agent/dimensions/hermes-agent-dependency-strategy.md","wiki/repos/hermes-agent/dimensions/hermes-agent-testing-philosophy.md"]
---

# OpenClaw vs Hermes Agent — 全维度对比

## 一句话定位

| | OpenClaw | Hermes Agent |
|---|---|---|
| **本质** | 自托管个人 AI 助手**运行时**（daemon） | 自学习 AI Agent**框架**（session-based） |
| **语言** | TypeScript monorepo | Python monorepo |
| **出品方** | 个人项目 (mariozechner) | Nous Research |

---

## 1. Architecture

### 相同点

两者都是**类六层架构**的 agent 运行系统，共享几乎完全相同的子系统清单：
- 消息平台网关 (20+ IM channel adapters)
- LLM 抽象层 (AgentHarness / AIAgent)
- 上下文引擎 (ContextEngine / ContextCompressor)
- 记忆系统 (Memory providers)
- Cron 任务调度
- 插件/Hook 系统
- SQLite 会话存储
- 可观测性层

两者的数据流主干也一致：`IM 消息 → Channel Adapter → Session Binding → Context Engine → Agent Loop → Outbound`。

### 差异点

| 维度 | OpenClaw | Hermes Agent | 原因 |
|---|---|---|---|
| **编排器** | `AgentHarness` 接口 + `selectAgentHarness()` 多实现选择 | `AIAgent` 单体类 (11510行) | OpenClaw 的 harness 接口来自其私有 `pi-agent-core` 包族的设计约定；Hermes 的 AIAgent 是从 run_agent.py 重构产物，从 3600 行单体逐步提取周边模块但核心保持集中 |
| **Gateway 角色** | 纯控制平面 — HTTP 路由 + auth，不执行 AI 调用 | 完整生命周期管理 — session 创建、agent 缓存、模型路由、delivery routing | OpenClaw 的 Gateway 是 monorepo 中一个薄层；Hermes 的 GatewayRunner 是整个多平台消息系统的中枢 |
| **安全层** | **5 层 Tool Policy Pipeline**（profile/provider/global/agent/group），纯配置驱动，同步门控 | **3 层交互式审批**（YOLO → Smart(aux LLM) → Manual），运行时阻塞等待用户响应 | OpenClaw 面向**单人自托管**场景，owner 权限模型足够；Hermes 面向**多用户多平台**聊天场景，需要每会话交互式审批 |
| **可观测性** | 生产级 OpenTelemetry（Traces + Metrics + Logs 三路导出，采样率配置，敏感内容 redact） | 运维级文件日志（RotatingFileHandler + 密文脱敏 + PID/运行状态）+ per-session 成本追踪 | OpenClaw 面向可观测性平台集成；Hermes 面向个人/server 运维诊断 |
| **进程管理** | 完整 Process Supervisor（ManagedRun/SpawnMode/RunState，respawn 策略，单例暴露） | 无独立进程看门狗，仅在 Docker entrypoint 中处理 | TS 运行时的进程管理需求更复杂（Node.js 单线程需 spawn 子进程）；Python 的 subprocess + threading 模式不同 |

### 根本原因

两者架构差异源于**使用模型不同**——这是理解和区分这两个框架最关键的一维：

**OpenClaw = 持续运行的后台服务（daemon）** ^[gateway/status.py:1-60] ^[gateway/platforms/base.py:813-893]

类似一间 24 小时营业的餐厅。用户部署后作为 systemd service 常驻运行，`ProcessSupervisor` 作为看门狗监视所有子进程（崩了自动重启）。Gateway 持续监听 20+ IM 平台的消息——用户发一条 Telegram 消息，Gateway 创建 session、注入记忆、调用 agent、推送回复。用户不在线时 cron 定时任务也在运行。这是**基础设施思维**：部署一次，持续服务。

关键代码证据：
- `gateway/status.py` 通过 PID 文件检测守护进程是否存活
- `gateway/platforms/base.py:813` 的 adapter 持续保持平台长连接（WebSocket/SSE）
- `gateway/run.py:604-611` 的 `_agent_cache` 跨消息缓存 AIAgent 保持 prompt cache
- `src/process/supervisor/` 管理 ManagedRun/SpawnMode/RunState 和 respawn 策略

**Hermes Agent = 每次对话按需创建的会话（session-based）** ^[run_agent.py:535-570] ^[run_agent.py:8130-8189]

类似每次预约才能吃的私厨。用户在终端敲 `hermes` → `AIAgent.__init__()` 创建新实例 → `run_conversation()` 执行 tool-calling 循环（包含 `IterationBudget` 限制最多 90 轮）→ 返回结果 → 实例销毁。即使开了 `hermes gateway` 看起来像后台服务，内部仍然是每条消息创建一个 AIAgent，跑完即毁。这是**任务思维**：每次对话是独立任务，有明确预算和边界。

关键代码证据：
- `run_agent.py:535` 的 `AIAgent.__init__()` 每次消息都创建新实例
- `run_agent.py:170-199` 的 `IterationBudget` 给每个会话迭代上限
- `run_agent.py:8130-8189` 的 `run_conversation()` 执行完返回，不保持长生命周期

**这直接解释了所有架构差异**:

| 架构差异 | 根因 |
|---|---|
| OpenClaw 优化启动速度、有 Process Supervisor、引入 OpenTelemetry | **daemon** 需要快速故障恢复、运维可观测 |
| Hermes 优化 per-session token 成本、有 IterationBudget、Smart Model Routing | **session-based** 每个会话是独立成本单元 |
| OpenClaw 用 5 层 policy pipeline 预配置权限 | **单人自托管** daemon，owner 事先配置足够 |
| Hermes 用 3 层交互式审批 + Gateway 阻塞队列 | **多用户多平台**，每条消息可能来自不同人，需要实时审批 |
| OpenClaw 有 inbound debounce + message throughput 优化 | **daemon** 需要处理高频消息涌入 |
| Hermes 有 execute_code refund + credential pool failover | **session-based** 每个会话的失败成本高，需要容错 |

---

## 2. Extension Points

### 相同点

两者都提供了完整的多层次扩展体系：
- 工具注册系统
- IM 平台适配器
- 记忆后端 (memory providers)
- 上下文引擎
- 生命周期 hooks/events
- Skills/技能系统

### 差异点

| 维度 | OpenClaw | Hermes Agent | 原因 |
|---|---|---|---|
| **注册风格** | **统一 API** — `OpenClawPluginApi` 上 25 个 `register*` 方法，一个 `register(api)` 入口可以注册一切 | **联邦式** — 文件约定（`tools/*.py` 的 `registry.register()`）+ 目录约定（`plugins/<type>/<name>/`）+ 配置（`config.yaml`） | TS 的强类型接口文化 vs Python 的 duck-typing + 约定优于配置文化 |
| **Hook 粒度** | **28 个细粒度 hook**，包括 `before_prompt_build`、`llm_input`、`llm_output` 等 prompt 注入和模型交互钩子 | **8 个粗粒度事件**，聚焦 gateway 生命周期和 agent 状态转换 | OpenClaw 的 hook 系统是为**prompt 级干预**设计的（记忆注入、system prompt 修改）；Hermes 的 hook 是为**平台集成**设计的（gateway 启停、会话边界） |
| **Plugin 元数据** | JSON manifest (`openclaw.plugin.json`) — 声明 provider、model prefix、capability contract、config schema | 无统一 manifest — 通过 SLOT 约定和目录结构隐式发现 | TS 生态的 manifest-first 传统 vs Python 的 import-time 自注册传统 |
| **独占槽位** | `registerContextEngine` 和 `registerMemoryCapability` 全局只有一个活跃实现 | Memory（最多 1 个外部 provider，Builtin 始终启用）、ContextEngine（只有 1 个）、其余无限制 | 两者都认识到 context engine 和 memory 是全局资源，不能多路并存 |
| **MCP 集成** | 协议支持（`@modelcontextprotocol/sdk`），但未作为一级扩展点在 wiki 中单独论述 | **一级扩展点** — 通过 `config.yaml` 声明即可连接外部 MCP server，包含 stdio/HTTP transport、自动重连、sampling 支持 | Hermes 更激进地采用 MCP 作为"零编码扩展"手段，降低用户门槛 |
| **扩展难度** | 中等 — 需理解 `OpenClawPluginApi` 类型系统和 monorepo workspace 结构 | 低到中 — 最简单的工具只需 10 行 Python 放在正确目录 | Hermes 的 Python 脚本约定天然比 TS 的类型系统对新手更友好 |

---

## 3. Performance Tradeoffs

### 相同点

两者都深度利用 Anthropic Prompt Caching 降低多轮对话成本，都有 context compression 机制在上下文接近窗口上限时触发压缩。

### 差异点

| 维度 | OpenClaw | Hermes Agent | 原因 |
|---|---|---|---|
| **优化重心** | **启动时间** — compile cache + lazy module + respawn 策略，启动性能有 CI budget 强制 | **运行时成本** — Smart Model Routing、Credential Pool、Iteration Budget、Rate Limit 追踪 | OpenClaw 是 daemon，每次重启需要快速恢复服务；Hermes 是会话 agent，每个 session 的 token 成本是用户直接感知的 |
| **Prompt Cache 策略** | Cache boundary marker（`<!-- OPENCLAW_CACHE_BOUNDARY -->`）切分 prompt，1h TTL on native API | `system_and_3`（4 breakpoints 覆盖 system + 最后 3 条非系统消息），默认 5min TTL | OpenClaw 的 marker 方式更精确控制缓存边界；Hermes 的 breakpoint 方式更简单直接，不需要修改 prompt 内容 |
| **并行执行** | Worker pool 动态计算（根据 `os.availableParallelism()` + loadavg + 内存自适应） | 固定 8 workers，按工具类型分类（永远串行/安全并行/路径范围并行） | OpenClaw 面向服务器环境（资源感知自适应）；Hermes 面向各种环境（固定上限保底） |
| **消息吞吐** | Inbound debounce + command poll exponential backoff | 无明显消息吞吐优化 | OpenClaw 处理高频 IM 消息场景更多 |
| **成本意识** | 无 per-session 成本追踪 | `estimate_usage_cost()` per-session，smart model routing 节省简单对话成本 | Nous Research 面向用户直接承担 LLM token 费用；OpenClaw 面向自有 API key |

---

## 4. Dependency Strategy

### 相同点

两者都采用分层依赖策略，都有可选依赖的优雅降级机制。

### 差异点

| 维度 | OpenClaw | Hermes Agent | 原因 |
|---|---|---|---|
| **核心 AI 依赖** | 深度耦合 `@mariozechner/*` 私有包族（442 次 import，版本精确锁定 0.66.1）— **替换成本极高** | 依赖开源 `openai` SDK 作为唯一 LLM transport — 替换成本高但生态广泛 | OpenClaw 的作者同时维护 `@mariozechner/*`，纵向整合；Hermes 基于开源生态构建 |
| **Stdlib vs Ecosystem** | 重度依赖 Node.js stdlib（3125 处 `node:*` import），进程/文件/网络全部走 stdlib | 核心 7 个第三方依赖，其余通过 20+ pip extras 按需安装 | TS 生态的 "stdlib-first" 传统；Python 生态的 "pip extras" 灵活安装 |
| **版本锁风格** | 混合策略 — 29 个精确锁（关键路径） + 41 个范围锁（工具类库） | 三层锁定 — 范围锁（`>=lower,<upper`）+ `uv.lock`（5512 行 hash）+ Docker SHA256 | TS 的 `^`/`~` 语义是标配；Python 社区正在从 pip 迁移到 uv/lockfile |
| **单点风险** | `@mariozechner/pi-ai`（176 次 import，覆盖 LLM transport + 模型配置） | `openai` SDK（20+ provider 全部通过它路由） | 不同的单点风险但相同的结构弱点——核心 LLM 通信路径都高度依赖单一包 |
| **Channel 隔离** | 每个 channel extension 有独立 `package.json`，依赖完全隔离 | 所有 platform adapter 共享 `pyproject.toml`，messaging extras 下统一管理 | monorepo workspace 天然支持独立 package；Python 单包结构统一管理更简单 |

---

## 5. Testing Philosophy

### 相同点

两者都以行为测试为主、单元测试为绝对主力、CI 并行执行、集成/e2e 测试分层。

### 差异点

| 维度 | OpenClaw | Hermes Agent | 原因 |
|---|---|---|---|
| **测试规模** | 2671 个测试文件 | 578 个测试文件 | OpenClaw 的 monorepo 结构（每 extension 独立包）导致测试文件数膨胀；Hermes 的单包结构更紧凑 |
| **测试类型** | 5 类：单元 + 契约 + e2e + live + Docker e2e | 3 类：单元 + 集成 + e2e | OpenClaw 的契约测试自动覆盖所有 channel plugin——这是 monorepo + 接口约束的天然优势 |
| **架构边界守护** | **20+ lint 脚本**可执行化架构约束（如 `lint:extensions:no-src-outside-plugin-sdk`） | **模块镜像**（`tools/` ↔ `tests/tools/`）作为隐式边界 | OpenClaw 把 lint 当作架构约束的可执行文档；Hermes 更依赖目录结构约定 |
| **性能测试** | CLI 启动时间有 CI budget fixture，超出即失败 | 无性能 budget | 与两者的性能优化方向一致：OpenClaw 优化启动，Hermes 优化运行时成本 |
| **测试隔离** | Worker pool 动态计算，pool type 可配置 | `autouse fixture` 隔离 `HERMES_HOME` + 30s 硬超时 | Python 的 fixture monkeypatch 模式；TS 的 vitest pool 模式 |
| **安全扫描** | 无 CI 安全扫描 workflow | Supply Chain Audit workflow（`.pth` 检测、base64+exec 检测、依赖审查） | Hermes 支持外部 skill 安装，需要更强的供给链安全防线 |

---

## 总结：根本原因分析

### 为什么存在这些异同？

**1. 语言生态决定了扩展开销**

TypeScript monorepo 的 workspace + `package.json` 方式天然鼓励**细粒度包隔离**和**契约测试**；Python 单包的 `pyproject.toml` + extras 方式天然鼓励**紧凑结构**和**约定优于配置**。这解释了为什么 OpenClaw 有 2671 个测试文件和 25 个 register 方法，而 Hermes 有 578 个测试文件和 9 个扩展机制。

**2. 使用模型决定了优化方向**

OpenClaw 是**持久化守护进程**（用户部署后长期运行），因此优化**启动速度**和**消息吞吐**，配备进程看门狗和 OpenTelemetry。Hermes 是**会话式 agent 框架**（每次对话按需启停），因此优化**per-session token 成本**，配备 smart model routing、iteration budget 和 per-session 使用量追踪。

**3. 用户场景决定了安全模型**

OpenClaw 面向**单人自托管**，安全模型是配置驱动的 5 层 policy pipeline——owner 预配置谁可以用哪些工具，运行时同步门控。Hermes 面向**多用户多平台聊天**，安全模型是交互式的 3 层审批——每个危险命令在每个会话中实时请求用户确认。

**4. 源码所有权决定了依赖策略**

OpenClaw 深度依赖作者自己的 `@mariozechner/*` 私有包族——这是纵向整合的优势（快速迭代、深度定制），但也是最大风险（单点失败、社区贡献受限）。Hermes 依赖开源 `openai` SDK——生态广泛、替代路径存在（OpenRouter/Anthropic 直连），但无法像私有包那样深度定制。

**5. "自学习" 是 Hermes 最根本的差异化能力**

OpenClaw 有 skills（markdown 文件注入 system prompt）和 memory（向量搜索 + sqlite-vec），但**没有系统 prompt 中自驱动的学习指令**——agent 不会主动去创建、改进、回忆，这些行为需要人类触发。

Hermes 通过三段系统指令构建了完整的学习闭环 ^[agent/prompt_builder.py:145-171]：

| 指令 | 触发行为 |
|---|---|
| `SKILLS_GUIDANCE` | 完成复杂任务后**主动创建** skill；使用 skill 时发现过时就**立即 patch** |
| `MEMORY_GUIDANCE` | 用户纠正/分享偏好时**主动保存**；发现做事新方式时**保存为 skill** |
| `SESSION_SEARCH_GUIDANCE` | 用户提及过去对话时**主动搜索**历史会话，不要让他们重复 |

三级时间尺度的自我改进：
- **实时层**: `memory` 工具在每轮后持久化，同会话立即生效
- **跨会话层**: `session_search` + FTS5 索引回忆历史对话，用户不需要重复
- **代际层**: `skill_manage` 创建/改进可复用步骤，agent 越用越能干

这一差异渗透到了架构的多个维度——CLI 启动时自动 `sync_skills()` ^[hermes_cli/main.py:743-747]、skill 安装前 `skills_guard` 安全扫描 ^[tools/skills_guard.py:82-484]、[agentskills.io](https://agentskills.io) 开放标准互操作。

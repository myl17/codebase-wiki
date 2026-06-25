# 候选 Concept + Concept 更新详细清单 R3

> 交叉审查：nanobot 草稿 vs openclaw/hermes 种子库
> 日期：2026-06-17

---

## 一、新候选 Concept（10 个）

### C-R3-1: Execution Engine Product-Layer Decoupling（执行引擎产品层解耦）

**维度**：Architecture
**问题陈述**：如何让 LLM 执行引擎不耦合到特定的产品层逻辑（channel/session/cron），使其在不同使用场景间复用？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | AgentRunner 纯数据接口 | 不持有 channel/session/cron 引用，只接受 messages 和 tool_registry 纯数据输入 | `agent/runner.py:83-89` |
| openclaw | 外部库委托 | 将 agent 执行完全委托给 `@mariozechner/pi-agent-core` 第三方库——外部库天然产品无关 | `src/agents/pi-embedded-runner/` |
| hermes | 耦合编排器 | AIAgent 同时处理 tool-calling 循环和 gateway/session 平台适配——在 `run_agent.py` 中耦合 | `run_agent.py:8130-8189` |

---

### C-R3-2: Hook Composition Strategy: Pipeline vs Fan-out（Hook 组合策略）

**维度**：Extension Points
**问题陈述**：如何让不同语义类型的 hook 采用不同的组合策略——内容变换需要串行管道，事件通知需要并行扇出？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 按方法区分：finalize_content 管道串联 + 其余方法扇出 | 内容变换逐步加工（一个 hook 的输出是下一个的输入），事件通知互不阻塞 | `agent/hook.py:57` |
| openclaw | 全扇出：28 个生命周期 hook 各自独立触发 | 每个 plugin 只订阅自己需要的 hook 节点，不区分管道/扇出 | `src/plugins/hook-types.ts` |
| hermes | 全扇出：MemoryProvider 15+ 生命周期回调独立触发 | on_pre_compress、on_delegation 等回调各自独立执行 | `agent/memory_provider.py:42-232` |

---

### C-R3-3: Scheduled Wake-up: Deterministic vs LLM-Judged（定时唤醒策略）

**维度**：Architecture
**问题陈述**：如何让定期唤醒兼具确定性调度和 LLM 基于上下文的主动判断？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | Heartbeat（LLM 判断）+ Cron（确定性）双模 | Heartbeat 用仅含 skip/run 的虚拟 tool 让 LLM 基于上下文判断；Cron 覆盖 at/every/cron 确定性触发 | `heartbeat/service.py:25-30, heartbeat/service.py:88-111; cron/service.py:65` |
| openclaw | Cron isolated-agent 模式 | 每次触发创建独立 agent session，周期性任务互不干扰 | `src/cron/` |
| hermes | 未在种子库中记录 | — | — |

---

### C-R3-4: LLM Provider Integration Strategy（LLM 供应商集成策略）

**维度**：Dependency Strategy
**问题陈述**：如何适配 20+ LLM 供应商的 API 差异——自行维护原生适配 vs 委托第三方库 vs 使用 API 网关？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 全自控原生 SDK 适配 | 移除 litellm，自行维护 3,719 行适配代码，5 种 backend 覆盖 20+ 供应商，零间接依赖 | `providers/base.py, providers/registry.py` |
| openclaw | 完全委托第三方库 | 所有 LLM 调用通过 `@mariozechner/pi-agent-core` 处理，自己不维护任何 provider 适配 | `src/agents/pi-embedded-runner/` |
| hermes | 混合：供应商解析链 | 按优先级链式解析（OpenRouter → Nous Portal → Codex OAuth → Native Anthropic），混合使用第三方网关和原生 SDK | `gateway/run.py` provider 解析逻辑 |

---

### C-R3-5: Memory Consolidation (Write) Timing（记忆压缩写入时机）

**维度**：Architecture / Performance Tradeoffs
**问题陈述**：如何让记忆压缩（将对话历史压缩为长期记忆）不阻塞主 agent 的对话流程？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 完全异步（fire-and-forget） | Consolidator 使用独立 provider 实例，`asyncio.create_task` 异步运行，压缩失败不影响正在进行对话，结果下一轮生效 | `agent/memory.py:346-365, agent/loop.py:470-474` |
| hermes | 同步写入 + 异步预取（混合） | 记忆写入在 turn 结束时同步执行（`sync_turn()`），但检索预取是后台异步（`queue_prefetch`） | `agent/memory_manager.py, run_agent.py:11236-11239` |
| openclaw | 工具驱动按需（无独立压缩管线） | 记忆写入通过 `memory_search`/`memory_get` 工具由 LLM 自主触发，没有独立的 Consolidator 概念 | `extensions/memory-core/src/tools.ts:177-394` |

---

### C-R3-6: Message Bus Architecture（消息总线架构）

**维度**：Architecture
**问题陈述**：如何让不同来源的消息（IM/子 agent/Cron/Heartbeat）统一进入处理管线，同时将 Channel 和 AgentLoop 完全解耦？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 极简 asyncio.Queue 事件总线 | 两个单向队列（inbound/outbound），入站不区分来源，Channel 和 AgentLoop 完全解耦 | `bus/queue.py:8-20` |
| openclaw | Channel Plugin → Hook 系统 → Agent | Channel plugin 通过结构化 hook 管线（28 个生命周期 hook）注入消息，来源类型在 hook 层面区分 | `src/channels/plugins/types.plugin.ts, src/plugins/hook-types.ts` |
| hermes | BasePlatformAdapter 统一基类 | 20+ 平台通过 PlatformAdapter 基类接入，消息进入统一的 AIAgent 处理管线 | `gateway/platforms/base.py:813-893` |

---

### C-R3-7: Testing Investment Prioritization（测试资源分配策略）

**维度**：Testing Philosophy
**问题陈述**：如何在有限测试资源下，按风险优先级分配测试投入——安全测试 vs 接口兼容性测试 vs 安全规则覆盖测试？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 安全优先 | 26,048 行测试代码中安全测试（SSRF/exec 沙箱/workspace 隔离）比重最大，因为安全漏洞后果远大于功能 bug | `security/network.py; tests/tools/test_exec_security.py` |
| openclaw | 接口兼容性优先 | 契约测试（`installChannelActionsContractSuite`）自动覆盖所有注册 plugin，确保扩展生态一致性 | `src/plugins/types.ts` |
| hermes | 安全规则覆盖优先 | 100+ 规则专项测试（如 `test_sql_injection.py`），重点关注变体绕过场景 | 专项测试文件（如 `test_sql_injection.py`） |

---

### C-R3-8: Skill Injection Granularity（技能注入粒度）

**维度**：Extension Points
**问题陈述**：如何在技能数量增长时平衡 LLM 可见性和 context window 消耗——全量注入 vs 完全不注入 vs 分级注入？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 二分法：always 全文注入 + 其余 XML 摘要 + 按需 read_file | always 技能确保关键指令 LLM 可见，低频技能以 XML 摘要呈现、agent 按需加载详情 | `agent/skills.py:23-50, agent/skills.py:109-117` |
| openclaw | Markdown Skills 作为第三层扩展（文件系统引用） | Skills 文件不注入 system prompt，LLM 通过工具或文件系统引用访问 | `src/agents/skills.ts` |
| hermes | 全量注入 system prompt | SKILL.md 文件全量注入 system prompt，每次会话启动时加载——简单可靠但不可扩展 | `agent/prompt_builder.py:449-453` |

---

### C-R3-9: Sub-agent Sandboxing（子 agent 隔离）

**维度**：Architecture
**问题陈述**：如何让子 agent 复用主 agent 的执行能力，同时安全地限制其权限——防止递归创建、权限扩散和工具滥用？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 共享引擎 + 受限 ToolRegistry + 结果经 bus 注入 | 子 agent 复用 AgentRunner，无 message/spawn/cron 工具防递归，结果走与 IM 消息相同的 bus 路径 | `agent/subagent.py:70-85, agent/subagent.py:102-129` |
| hermes | 资源隔离（50 轮硬上限 + 1 次 grace call） | 子 agent 通过 turn 预算做资源限制，预算信息不注入 LLM（避免过早放弃），但无工具级权限限制 | `run_agent.py:170-199` |
| openclaw | 子 agent 通过 pi-agent-core 管理 | 种子库中未详细记录子 agent 隔离机制 | 待回溯 |

---

### C-R3-10: Subsystem Assembly Visibility（子系统组装可见性）

**维度**：Architecture
**问题陈述**：如何组织所有子系统的实例化和连线，使系统的整体构成具有最大可发现性——单体 hub vs 依赖注入容器 vs 分散初始化？

| 仓库 | 方案 | 简述 | 溯源码路径 |
|------|------|------|-----------|
| nanobot | 单体 Hub 构造函数集中组装 | 所有子系统在一个 `__init__()` 中实例化和连线，读一个函数即知全貌 | `agent/loop.py:115-228` |
| openclaw | 服务容器/Dependency Injection | 子系统通过注册中心（Registry Map）和工厂模式分散注册和组装 | `src/agents/harness/registry.ts` |
| hermes | 分散初始化 | 子系统在 `run_agent.py` 和 `gateway/run.py` 中分散初始化，无中心组装点 | `run_agent.py, gateway/run.py` |

---

## 二、已有 Concept 更新清单（4 个）

### U-R3-1: `context-compression-quality` — 追加方案 C「规则透明压缩」

**当前状态**：方案 A（openclaw LLM 摘要）+ 方案 B（hermes LLM 摘要 + 结构化模板）
**nanobot 追加**：方案 C——四层透明治理，完全不用 LLM

| 机制层 | nanobot 实现 | 对应 openclaw | 对应 hermes |
|--------|-------------|--------------|-------------|
| 前置修复 | **Backfill**：补全孤立的 tool_use 再裁剪 | 无 | `_sanitize_tool_pairs` 修复 orphaned 对 |
| 历史压缩 | **Microcompact**：压缩 10 轮前的 tool result 为一行摘要，纯规则 | `stripToolResultDetails` 摘除 details 字段 | `_prune_old_tool_results` 三遍扫描（dedup + 单行摘要 + 参数截断） |
| 单结果截断 | **Budget**：截断单个超大 tool result | `SAFETY_MARGIN` token 估算 + 分块控制 | 消息正文 6000 字符上限 |
| 全局裁剪 | **Snip**：从尾部按 token 预算裁剪 | 从头部逐块丢弃（`pruneHistoryForContextShare`） | 保留 head + tail，压缩中间 |

**溯源码路径**：`agent/runner.py:102-107`（四层入口）, `agent/runner.py:553-640`（Backfill/Microcompact/Budget/Snip 实现）

**关键差异**：
- nanobot 从**尾部**裁剪（Snip），openclaw 从**头部**丢弃（prune），hermes 保留头尾压缩**中间**
- nanobot 的四层操作全在 engine 内部、对 LLM 透明；openclaw 和 hermes 都需要额外的 LLM 调用生成摘要
- nanobot 的 Backfill 修复 orphaned tool_use 是 openclaw 和 hermes 都未实现的前置步骤

---

### U-R3-2: `llm-input-token-cost-reduction` — 追加方案 A 变体「纯函数式 cache-stable 构造」

**当前状态**：方案 A（openclaw 内容层缓存边界标记）+ 方案 B（hermes 进程实例层缓存复用）
**nanobot 追加**：方案 A 的纯函数变体——通过构造纪律替代显式边界标记

**机制**：
nanobot 的 ContextBuilder 是六层固定顺序的纯函数式构建器：
```
identity → bootstrap files → memory → always skills → skills summary → recent history
```

每层 `---` 分隔，不依赖运行时状态，函数输入确定则输出确定。保证只要 identity、bootstrap files、memory、always skills 不变化，整个 prompt 前缀就是 cache-stable 的。

与 openclaw 方案 A 的关键区别：
- openclaw：**显式标记**（`<!-- OPENCLAW_CACHE_BOUNDARY -->`）告诉 API 层在哪里切分稳定/动态内容
- nanobot：**隐式约定**——纯函数式构造 + 固定顺序 + 无运行时状态依赖。不做 API 层面的 cache_control 操作，而是从构造源头保证稳定性

**溯源码路径**：`agent/context.py:17`（ContextBuilder 定义）, `agent/context.py:30-63`（六层构建逻辑）

---

### U-R3-3: `plugin-subsystem-auto-discovery` — 追加两个新实例

**当前状态**：openclaw `supports()` + priority（运行时动态策略选择）+ hermes AST 扫描（启动时静态代码分析）
**nanobot 追加**：

#### 实例 3：pkgutil 自发现 + entry_points 外部插件（Channel 发现）

**机制类型**：启动时包管理器级扫描 + 外部注册
**所属仓库**：nanobot Channel System
**维度**：Extension Points

**机制**（`channels/registry.py:23, channels/registry.py:42-55`）：
- **内置发现**：pkgutil 遍历 `channels/` 包目录，自动发现所有 channel 子模块
- **外部发现**：通过 Python `entry_points`（`pip install` 可安装第三方 channel 插件）
- **优先级覆盖**：内置 channel 优先于同名外部 plugin——第三方无法通过名称冲突劫持内置功能

与已有实例的对比：
- vs openclaw `supports()`：nanobot 是启动时扫描而非运行时动态决策；无 priority 竞争
- vs hermes AST 扫描：nanobot 使用 pkgutil（包结构约定）而非 AST 解析（代码语法约定），更鲁棒但要求遵循目录结构
- **独特价值**：entry_points 支持让第三方通过 pip 分发包——这是 hermes 的 AST 扫描（仅扫描内置 `tools/` 目录）和 openclaw 的 `registerAgentHarness()`（需要写 JS 代码）都没有覆盖的扩展分发场景

**溯源码路径**：`channels/registry.py:23`（自发现入口）, `channels/registry.py:42-55`（双层扫描逻辑）

#### 实例 4：显式 register() 确定性注册（Tool 注册）

**机制类型**：显式点名注册（反自动发现）
**所属仓库**：nanobot ToolRegistry
**维度**：Extension Points

**机制**（`agent/tools/registry.py:8-18, agent/loop.py:225-229`）：
- 每个工具在 `_register_default_tools()` 中显式 `register()` 点名
- 不做 AST 扫描、不做装饰器发现、不做模块自省
- builtins 按名称排序在前以保证 prompt cache 稳定前缀
- 一眼可知系统有哪些工具——完全确定性

与已有实例的对比：
- vs hermes AST 扫描：直接哲学对立——hermes 追求零摩擦（加文件即可），nanobot 追求零意外（点名才算数）
- vs openclaw `registerAgentHarness()`：都是显式 register，但 openclaw 的 harness 需要额外实现 `supports()` 方法，nanobot 的工具注册只需要一个 `register()` 调用

**溯源码路径**：`agent/tools/registry.py:8-18`（注册 API）, `agent/loop.py:225-229`（`_register_default_tools()` 集中注册点）

---

### U-R3-4: `memory-retrieval-timing` — 扩展「记忆写入时机」维度

**当前状态**：聚焦于记忆检索时机（工具驱动按需 vs 后台异步预取），未覆盖记忆写入/压缩时机。
**nanobot 追加**：在 Concept 中新增「记忆压缩（写入）时机」对比维度。

| 维度 | nanobot | hermes | openclaw |
|------|---------|--------|----------|
| 压缩触发 | 每轮结束后自动（在 AgentLoop 中 `asyncio.create_task`） | 每轮结束后自动（在 main loop 中 `sync_turn` 同步执行） | LLM 主动调用工具时（`memory_search` 是只读，无独立压缩管线） |
| 是否阻塞主循环 | **否**——完全异步 | **是**——在 turn 结束的清理阶段同步完成 | N/A |
| 失败影响 | 不影响正在进行的对话，结果下一轮生效 | 同步失败可能导致 turn 结束逻辑中断 | LLM 收到错误可见处理 |

**溯源码路径**：`agent/memory.py:346-365`（Consolidator 异步实现）, `agent/loop.py:470-474`（`create_task` 调用点）

---

## 三、nanobot 独有条目（待后续仓库，2 个）

这些条目在 openclaw 和 hermes 的种子库中没有对应记录，且不是遗漏——三个仓库在此问题上的设计不同，但 openclaw 和 hermes 可能也有等效机制未被记录。标记为 nanobot 独有，等待第四个仓库确认后升级为 Concept。

### N-R3-1: Session Persistence Strategy（会话持久化策略）

**问题**：如何存储和加载会话数据，使其追加友好、人类可读，且发给 LLM 的历史始终从合法边界开始？
**nanobot 选择**：JSONL 文件 + 惰性加载 + 合法边界裁剪（`session/manager.py:96, session/manager.py:69, session/manager.py:119`）
**openclaw/hermes 情况**：种子库中无会话存储格式的设计选择。openclaw 的 TaskFlow 使用 SQLite 持久化任务状态（非会话），hermes 的 session 管理未在种子库中作为设计选择记录。

### N-R3-2: Message Inbound Debounce（入站消息防抖）

**问题**：如何在 IM 场景下处理用户分条发送导致的碎片化消息？——反向检查发现，openclaw 种子库中有「入站消息防抖」（`inbound-debounce-policy`），但 nanobot 草稿中未提及此问题。
**nanobot 情况**：需回溯 `bus/queue.py` 确认是否实现了消息合并/防抖逻辑。
**待办**：Phase 3a 回溯确认 nanobot 是否面对此问题及如何处理。

---

## 四、反向检查补充条目（5 个，待 Phase 3a 回溯确认）

以下在种子库中标记为 openclaw/hermes 独有的条目，nanobot 很可能也面对，但草稿中未提取。需在 Phase 3a 回溯 nanobot Entity 页确认后补充。

| # | 种子库条目 | nanobot 可能需要回溯的文件 |
|---|-----------|--------------------------|
| 1 | LLM provider 接口粒度（compact?/reset? 可选方法） | `providers/base.py`——5 种 backend 如何处理不同能力 provider |
| 2 | 启动时懒加载 plugin 代码 | `channels/registry.py`——pkgutil 扫描是否全量加载 |
| 3 | 入站消息防抖（inbound debounce） | `bus/queue.py`——消息总线是否处理碎片化消息合并 |
| 4 | 对话轮次预算控制（防止无限 tool-calling 循环） | `agent/runner.py`——AgentRunner 是否有 turn 硬上限 |
| 5 | 多粒度工具权限策略 | `agent/tools/registry.py`——是否有不同粒度（agent/sub-agent/channel）的工具可见性控制 |

---

## 汇总

| 类别 | 数量 | 标注 |
|------|------|------|
| 新候选 Concept | 10 | C-R3-1 至 C-R3-10 |
| 已有 Concept 更新 | 4 | context-compression-quality, llm-input-token-cost-reduction, plugin-subsystem-auto-discovery, memory-retrieval-timing |
| nanobot 独有（待后续仓库） | 2 | N-R3-1, N-R3-2 |
| 反向检查漏提（待 Phase 3a） | 5 | provider 接口粒度、懒加载、防抖、turn 预算、工具权限策略 |
| 已有 Concept 无需更新 | 3 | context-engine-singleton-vs-pluggable, dangerous-operation-prevention, tool-execution-safety-approval |

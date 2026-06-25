# 交叉审查报告 R3：nanobot 草稿 vs 已有种子库

> 审查日期：2026-06-17
> 审查范围：nanobot 设计选择草稿（15 条）vs 已有种子库（48 条，含 openclaw + hermes）

---

## 任务 1：逐条对比

### 条目 1：子系统整体如何组装和连线

**维度**：Architecture
**种子库匹配**：无直接匹配。「Agent 编排模型」（hermes）关注的是编排逻辑集中化，不是组装可见性。
**判断**：nanobot 独有——待观察。
**理由**：nanobot 追求"读一个构造函数即知全貌"的极致可发现性（`agent/loop.py:115-228`）。openclaw 使用服务容器/Dependency Injection 模式分散注册，hermes 的组装散落在 `run_agent.py` 和 `gateway/run.py` 中。三个仓库在此问题上的策略截然不同，但 openclaw 和 hermes 的种子库中未将此作为独立设计选择记录。待后续仓库出现第四个方案时升级为 Concept。
**溯源**：`entity/nanobot-agent-loop.md` → `agent/loop.py:115-228`

---

### 条目 2：执行引擎如何跨场景复用

**维度**：Architecture
**种子库匹配**：无直接匹配。hermes 的「Agent 编排模型」关注的是单一编排器的存在性而非其产品层解耦度。
**判断**：候选新 Concept「Execution Engine Product-Layer Decoupling」。
**理由**：三个仓库都面临"执行引擎如何不耦合到特定产品逻辑"的问题，答案不同：
- **nanobot**：AgentRunner 完全不持有 channel/session/cron 引用，只接受 messages + tool_registry 纯数据输入
- **openclaw**：将 agent 执行委托给第三方库 `@mariozechner/pi-agent-core`——外部库天然产品无关
- **hermes**：AIAgent 与 gateway/session 耦合——`run_agent.py` 同时处理编排和平台适配

nanobot 的"内部纯模块"、openclaw 的"外部库委托"、hermes 的"耦合编排器"形成清晰的三方案对比。
**溯源**：`entity/nanobot-agent-runner.md` → `agent/runner.py:83-89`

---

### 条目 3：上下文窗口治理如何在引擎内部自执行

**维度**：Performance Tradeoffs
**种子库匹配**：**已有 Concept `context-compression-quality`**。种子库中有「如何在压缩对话历史时保留关键任务状态？」（openclaw + hermes）和「如何减少压缩摘要中的噪声？」（openclaw + hermes）。
**判断**：**已有 Concept 更新**——追加 nanobot 为第三个方案。
**差异分析**：
- openclaw：LLM 摘要 + strip tool result details + 自适应分块
- hermes：辅助 LLM 摘要 + 结构化模板 + 三层 token budget + 反抖动
- **nanobot：四层透明治理（Backfill → Microcompact → Budget → Snip），对 LLM 完全透明，不使用 LLM 生成摘要**

nanobot 的独特之处：
1. **Backfill**：补全孤立的 tool_use（无对应 tool_result），修复消息序列的合法性后剪裁——openclaw 和 hermes 都没有这个前置步骤
2. **Microcompact**：压缩 10 轮前的 tool result 为一行结果摘要——纯规则、无 LLM 调用
3. **Budget**：截断单个 tool result 的超大内容——类似于 openclaw 的 strip details 和 hermes 的单行摘要
4. **Snip**：按 token 预算从尾部裁剪消息——从尾部而非头部（openclaw 从头部逐块丢弃，hermes 中间压缩保留 head+tail）

**关键差异**：nanobot 完全不使用 LLM 做摘要——四层操作全部是确定性规则。这是 context-compression-quality Concept 中的第三种哲学：「规则透明」vs openclaw 的「LLM 摘要保留状态」vs hermes 的「LLM 摘要结构化模板」。
**溯源**：`entity/nanobot-agent-runner.md` → `agent/runner.py:102-107, agent/runner.py:553-640`

---

### 条目 4：内容变换钩子和事件通知钩子如何采用不同组合策略

**维度**：Extension Points
**种子库匹配**：部分相关——openclaw 有「如何细分生命周期 hook」（28 个 hook），但关注的是粒度而非组合策略。hermes 的 MemoryProvider 有 15+ 生命周期回调，但没有区分管道 vs 扇出。
**判断**：候选新 Concept「Hook Composition Strategy: Pipeline vs Fan-out」。
**理由**：nanobot 明确区分了两种 hook 语义并采用不同的组合策略：
- `finalize_content`：管道串联（一个 hook 的输出是下一个的输入，适合内容逐步加工）
- 其余方法（如事件通知）：扇出（所有 hook 独立并行触发，互不阻塞）

openclaw 的 28 个 hook 各自独立触发（全是扇出），hermes 的 MemoryProvider 回调也全是独立触发。nanobot 首次在 hook 系统中引入了"按语义选择组合策略"的设计。但这依赖 openclaw/hermes 是否也有类似区分——需要回溯确认。
**溯源**：`entity/nanobot-agent-hook.md` → `agent/hook.py:57`

---

### 条目 5：IM 平台插件如何同时支持内置和第三方开发

**维度**：Extension Points
**种子库匹配**：**已有 Concept `plugin-subsystem-auto-discovery`**。种子库已有 openclaw（`supports()` + priority）和 hermes（AST 扫描）。
**判断**：**已有 Concept 更新**——追加 nanobot 为第三个方案。
**差异分析**：nanobot 的双层 Channel 发现提供了与前两者不同的机制：
- openclaw：运行时动态策略选择（`supports(ctx)`）
- hermes：启动时静态 AST 扫描
- **nanobot：双层发现——pkgutil 自发现（内置 `channels/` 目录）+ entry_points（pip 可安装第三方插件），内置优先覆盖**

这是一个**启动时扫描 + 优先级覆盖 + 外部发现**的组合模式。与 hermes 的 AST 扫描类似（都是启动时发现），但：
1. nanobot 使用 pkgutil 遍历包目录而非 AST 解析——不依赖代码约定，更鲁棒
2. entry_points 支持让第三方无需修改任何 nanobot 源码即可注册 channel
3. 内置优先覆盖提供了安全性——第三方无法通过同名 channel 劫持内置功能
**溯源**：`entity/nanobot-channel-system.md` → `channels/registry.py:23, channels/registry.py:42-55`

---

### 条目 6：System Prompt 多层内容如何组织

**维度**：Architecture
**种子库匹配**：**已有 Concept `llm-input-token-cost-reduction`**。种子库已有 openclaw（cache boundary 标记）和 hermes（AIAgent 实例缓存）。
**判断**：**已有 Concept 更新**——追加 nanobot 为第三个方案（或方案 A 的纯函数变体）。
**差异分析**：
- openclaw：在 prompt 文本中插入显式 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记切分稳定/动态内容
- hermes：跨消息复用 AIAgent 实例，依赖 Anthropic prompt cache prefix 自动匹配
- **nanobot：六层固定顺序纯函数式 ContextBuilder（identity → bootstrap files → memory → always skills → skills summary → recent history），每层 `---` 分隔，不依赖运行时状态**

nanobot 的方案是方案 A（prompt 内容层）的变体，但不使用显式边界标记。它通过**纯函数式构造 + 固定顺序 + 无运行时状态依赖**来保证 prompt cache 前缀稳定——只要 identity、bootstrap files、memory、always skills 不变化，整个前缀就是缓存命中的。相当于用**构造纪律替代边界标记**。
**溯源**：`entity/nanobot-context-builder.md` → `agent/context.py:17, agent/context.py:30-63`

---

### 条目 7：定期唤醒如何兼具确定性和 LLM 主动性

**维度**：Architecture
**种子库匹配**：部分相关——openclaw 有「如何让定时任务不污染用户对话历史」（isolated-agent mode），但关注的是隔离而非调度策略双模。
**判断**：候选新 Concept「Scheduled Wake-up: Deterministic vs LLM-Judged」。
**理由**：nanobot 同时提供两种互补的唤醒机制：
- **Heartbeat**：用仅含 skip/run 的虚拟 tool 让 LLM 基于上下文判断是否需要执行——LLM 有自主判断权
- **Cron**：覆盖确定的 at/every/cron 时间触发——确定性调度

openclaw 只有 Cron（isolated-agent 模式），hermes 的种子库中无定时唤醒条目。nanobot 的 Heartbeat 机制（LLM-judged 唤醒）是独特创新——解决了"agent 有没有话要说"这类无法用 cron 表达式表达的唤醒场景。
**溯源**：`entity/nanobot-cron-heartbeat.md` → `heartbeat/service.py:25-30, heartbeat/service.py:88-111; cron/service.py:65`

---

### 条目 8：如何适配多 LLM 供应商而不引入第三方转发层

**维度**：Dependency Strategy
**种子库匹配**：无直接匹配。openclaw 的「如何管理对外部私有核心库的深度依赖」关注的是深度绑定第三方库的代价，而非 provider 适配策略。
**判断**：候选新 Concept「LLM Provider Integration Strategy」。
**理由**：三个仓库在"如何接入多个 LLM provider"上做出了结构性不同的选择：
- **nanobot**：移除 litellm，自行维护原生 SDK 适配层（3,719 行代码，5 种 backend，20+ 供应商，零间接供应商依赖）
- **openclaw**：委托给 `@mariozechner/pi-agent-core` 私有库处理——自己完全不维护 provider 适配
- **hermes**：通过 provider 解析链（OpenRouter → Nous Portal → Codex OAuth → Native Anthropic）——混合使用第三方网关和原生 SDK

这形成了一个清晰的 spectrum：完全自控（nanobot）→ 混合（hermes）→ 完全委托（openclaw）。
**溯源**：`entity/nanobot-llm-provider.md` → `providers/base.py, providers/registry.py`

---

### 条目 9：记忆压缩如何不阻塞主对话

**维度**：Architecture
**种子库匹配**：**已有 Concept `memory-retrieval-timing`**（部分相关）。该 Concept 覆盖的是记忆检索时机（工具驱动 vs 后台预取），而非记忆写入/压缩时机。
**判断**：**已有 Concept 更新或扩展**——在 `memory-retrieval-timing` 中追加 nanobot 的记忆写入（压缩）时机方案。
**差异分析**：
- openclaw：记忆检索是工具驱动按需（LLM 调用 `memory_search`），记忆写入未在 Concept 中覆盖
- hermes：记忆检索是后台异步预取（`queue_prefetch`），记忆写入是 turn 结束时同步持久化（`sync_turn`）
- **nanobot：Consolidator 独立 provider + `asyncio.create_task` 异步后台运行——压缩不共享主 agent 的 provider 实例，失败不影响正在进行对话，结果下一轮生效**

nanobot 的方案将记忆压缩从对话关键路径中完全移除。hermes 的 `sync_turn()` 虽然也在 turn 结束后执行，但在 agent loop 内同步完成（同一线程）。nanobot 的 `asyncio.create_task` 将其变成真正的 fire-and-forget 异步任务。
**溯源**：`entity/nanobot-memory-system.md` → `agent/memory.py:346-365, agent/loop.py:470-474`

---

### 条目 10：不同来源的消息如何统一进入处理管线

**维度**：Architecture
**种子库匹配**：无直接匹配。openclaw 有「如何让控制平面和 AI 执行层解耦」（Gateway 纯路由层）和「如何让 plugin 向控制平面注入自定义 API」，但关注的是 gateway-plugin 通信而非消息总线。
**判断**：候选新 Concept「Message Bus Architecture」。
**理由**：nanobot 的事件总线极简设计（两个单向 asyncio.Queue——inbound/outbound，将 Channel 和 AgentLoop 完全解耦）代表了消息路由的一种极端立场。所有来源（IM/子 agent/Cron/Heartbeat）的消息无差别进入同一个 inbound 队列，AgentLoop 不区分来源。

openclaw 的 Channel → Hook → Agent 路径更结构化（生命周期 hook 细分了不同来源的处理），hermes 的 BasePlatformAdapter 更面向平台适配。这三个仓库在消息路由上的设计光谱值得作为一个 Concept 记录。
**溯源**：`entity/nanobot-message-bus.md` → `bus/queue.py:8-20`

---

### 条目 11：测试资源如何分配以最大化安全效果

**维度**：Testing Philosophy
**种子库匹配**：部分相关——openclaw 的「如何确保所有 plugin 的接口兼容性？」（契约测试）和 hermes 的「安全模块的测试策略」（100+ 规则边界测试），但关注的是测试方法而非资源分配哲学。
**判断**：候选新 Concept「Testing Investment Prioritization」。
**理由**：三个仓库在测试资源分配上体现了不同的风险模型：
- **nanobot**：安全测试优先——26,048 行测试中安全（SSRF/exec 沙箱/workspace 隔离）比重最大，因为安全漏洞后果远大于功能 bug
- **openclaw**：接口兼容性优先——契约测试自动覆盖所有注册 plugin，确保扩展生态的一致性
- **hermes**：安全规则覆盖优先——100+ 规则专项测试，重点是变体绕过场景

这反映了三种不同的"最大风险"判断：nanobot 认为最大风险是安全漏洞，openclaw 认为是 plugin 生态碎片化，hermes 认为是安全规则被绕过。
**溯源**：`entity/nanobot-security.md` → `security/network.py; tests/tools/test_exec_security.py`

---

### 条目 12：会话数据如何存储以兼顾可读性和正确性

**维度**：Architecture
**种子库匹配**：无直接匹配。hermes 有日志相关条目（三路日志、后台进程输出管理），但不是会话持久化格式。openclaw 的 TaskFlow 使用 SQLite 但那是任务状态而非会话存储。
**判断**：nanobot 独有——待观察。
**理由**：nanobot 的 JSONL + 惰性加载 + 合法边界裁剪（对齐到 user-turn）是一个精心设计的会话存储方案。JSONL 追加友好、人类可读、惰性加载省内存、合法边界裁剪确保 LLM 收到的历史总是 well-formed。openclaw 和 hermes 的会话存储方案在种子库中未作为设计选择记录，可能是漏提，但当前缺乏直接对比素材。
**溯源**：`entity/nanobot-session-manager.md` → `session/manager.py:96, session/manager.py:69, session/manager.py:119`

---

### 条目 13：技能知识如何注入而不让 prompt 膨胀

**维度**：Extension Points
**种子库匹配**：部分相关——openclaw 的「如何降低 agent 能力扩展的门槛」（Markdown Skills）和 hermes 的「技能注入策略」（全量注入 system prompt）。
**判断**：候选新 Concept「Skill Injection Granularity」。
**理由**：nanobot 提供了介于 openclaw 和 hermes 之间的第三条路：
- openclaw：Markdown Skills 作为第三层扩展，不注入 system prompt，通过文件系统引用
- hermes：SKILL.md 全量注入 system prompt，不区分优先级
- **nanobot：always 技能全文注入 system prompt + 其余技能以 XML 摘要呈现、agent 按需 `read_file` 加载**

nanobot 的 always/on-demand 二分法同时解决了两个问题：关键技能确保 LLM 可见（always 注入），大量低频技能不撑爆 context window（XML 摘要 + 按需加载）。这是一个在 openclaw（完全不注入）和 hermes（全量注入）之间的 pragmatic middle ground。
**溯源**：`entity/nanobot-skills.md` → `agent/skills.py:23-50, agent/skills.py:109-117`

---

### 条目 14：子 agent 如何复用主 agent 能力同时限制权限

**维度**：Architecture
**种子库匹配**：部分相关——hermes 的「Agent 编排模型」提到子 agent 有 50 轮硬上限，「对话轮次预算控制」中提到预算信息不注入 LLM。但这些关注的是资源控制，不是权限隔离。
**判断**：候选新 Concept「Sub-agent Sandboxing」。
**理由**：nanobot 的子 agent 安全模型是三层隔离：
1. **共享引擎**：复用 AgentRunner（不重复实现 tool-calling 循环）
2. **受限 ToolRegistry**：无 message/spawn/cron 工具，防止递归和权限扩散
3. **结果经 bus 注入**：走与 IM 消息完全相同的处理路径，不特殊化

hermes 的子 agent 通过 turn 预算做资源隔离（50 轮硬上限 + 1 次 grace call），但没有工具级权限限制。openclaw 的子 agent 通过 pi-agent-core 管理，种子库中无详细记录。
**溯源**：`entity/nanobot-subagent.md` → `agent/subagent.py:70-85, agent/subagent.py:102-129`

---

### 条目 15：工具注册如何做到完全确定性

**维度**：Extension Points
**种子库匹配**：**已有 Concept `plugin-subsystem-auto-discovery`**。hermes 的 AST 扫描正是隐式发现——与 nanobot 的显式注册形成直接对比。
**判断**：**已有 Concept 更新**——追加 nanobot 为第三个方案（显式确定性注册）。
**差异分析**：
- openclaw：`supports()` + priority 动态策略选择（运行时）
- hermes：AST 扫描自动发现 `registry.register()` 顶层调用（隐式约定）
- **nanobot：显式 `register()` 调用——不做 AST 扫描、装饰器发现、模块自省。每个工具在 `_register_default_tools()` 中点名，builtins 按名称排序保证 prompt cache 稳定前缀**

nanobot 选择显式注册的理由是"完全确定性"——一眼可知系统有哪些工具，隐式发现可能遗漏或误判。这与 hermes 的 AST 扫描形成直接的哲学对立：hermes 追求零摩擦（加文件即可），nanobot 追求零意外（点名才算数）。
**溯源**：`entity/nanobot-tool-registry.md` → `agent/tools/registry.py:8-18, agent/loop.py:225-229`

---

## 任务 2：反向检查——已有种子库中是否有 nanobot 遗漏的设计选择

### 从 openclaw 独有条目反向检查

| 种子库条目 | nanobot 是否面对 | 草稿是否覆盖 | 结论 |
|-----------|-----------------|-------------|------|
| LLM provider 接口粒度（compact?/reset? 可选方法） | 是——nanobot 的 Provider 适配层面临不同 provider 的能力差异 | 未覆盖 | 漏提。nanobot 的 5 种 backend 设计可能隐含了类似的接口粒度处理，需回溯 `providers/base.py` 确认 |
| Channel plugin 依赖隔离（独立 npm 包） | 否——nanobot 的 channel 在 monorepo 内 | N/A | 不适用 |
| 启动时懒加载 plugin 代码 | 是——pkgutil 扫描可能全量加载 | 未覆盖 | 漏提。需确认 pkgutil 扫描是否在启动时加载所有 channel 代码 |
| 入站消息防抖 | 是——IM 场景可能面临碎片化消息 | 未覆盖 | 漏提。nanobot 的消息总线是否处理消息合并？ |
| 记忆向量存储后端可替换 | 否——nanobot 无向量检索 | N/A | 不适用 |
| 本地向量搜索后端（sqlite-vec） | 否——nanobot 无向量检索 | N/A | 不适用 |
| 生命周期 hook 细分（28 个） | 是——nanobot 有 AgentHook 系统 | 部分覆盖 | 条目 4 覆盖了组合策略，但未对比 hook 数量/粒度 |
| Plugin 接口兼容性契约测试 | 是——nanobot 有 plugin/extension 系统 | 未覆盖 | 漏提。nanobot 如何保证 channel/hook 的接口兼容？ |
| CLI 冷启动加速 | 是——nanobot 是 CLI 工具 | 未覆盖 | 漏提。Python CLI 冷启动优化是否被考虑？ |
| 子进程生命周期管理 | 是——nanobot 可能管理 MCP server 等子进程 | 未覆盖 | 漏提。MCP server 连接管理涉及子进程生命周期 |
| 长任务状态持久化 | 是——nanobot 的多轮对话涉及状态保持 | 条目 12 覆盖了会话存储 | 部分覆盖。但 TaskFlow 级别的任务状态（跨进程重启）未提及 |
| 长时间命令轮询（指数退避） | 未知 | 未覆盖 | 待确认 |
| 多粒度工具权限策略（5 层 pipeline） | 是——nanobot 可能有工具权限控制 | 未覆盖 | 漏提。nanobot 如何在不同粒度上控制工具权限？ |

### 从 hermes 独有条目反向检查

| 种子库条目 | nanobot 是否面对 | 草稿是否覆盖 | 结论 |
|-----------|-----------------|-------------|------|
| 工具执行并发策略 | 未知——需查看 AgentRunner 的工具执行模式 | 未覆盖 | 待确认。如 nanobot 支持并行工具调用，这是一个重要的设计和安全选择 |
| 对话轮次预算控制 | 是——nanobot 的 tool-calling 循环可能无限 | 未覆盖 | 漏提。nanobot 如何防止无限循环？条目 3 的 Budget/Snip 是 context 层面，不是 turn 预算 |
| 审批结果持久化 | 否——nanobot 无审批系统 | N/A | 不适用 |
| 上下文压力通知策略 | 是——条目 3 覆盖了 Snip（透明裁剪） | 条目 3 覆盖 | 已覆盖。nanobot 的 Snip 对 LLM 透明，与 hermes 的"不注入 LLM"策略一致 |
| 多平台适配架构（16 处配置点） | 是——nanobot 的 Channel 系统 | 条目 5 覆盖了发现，但未提及配置点数量 | 部分覆盖 |
| Gateway 审批等待策略 | 否——nanobot 无 Gateway 模式 | N/A | 不适用 |
| 记忆系统可靠性（builtin 始终启用） | 是——nanobot 的记忆系统是单体内置 | 条目 9 覆盖了 Consolidator | 已覆盖。nanobot 的记忆系统没有外部 provider，不存在 builtin vs external 的可靠性问题 |
| 记忆系统可扩展性（15+ 生命周期回调） | 否——nanobot 的 MemoryStore 是单一实现 | N/A | 不适用 |
| 日志安全脱敏（40+ API key 前缀） | 未知 | 未覆盖 | 待确认 |
| 日志文件组织（三路日志 + session_id） | 未知 | 未覆盖 | 待确认 |
| 后台进程输出管理 | 未知 | 未覆盖 | 待确认 |
| Agent 自学习触发机制 | 否——nanobot 的 Dream 是记忆处理，非技能创建 | N/A | 不适用 |
| 技能注入策略（全量注入） | 是——条目 13 覆盖 | 条目 13 覆盖 | 已覆盖 |
| 技能的自我维护能力 | 未知 | 未覆盖 | 待确认 |
| 外部技能安全分级（四级信任矩阵） | 否——nanobot 无技能市场/外部技能 | N/A | 不适用 |
| 技能安装安全防护（隔离区） | 否——同上 | N/A | 不适用 |
| 安全模块的测试策略（100+ 规则边界测试） | 是——条目 11 覆盖了安全测试投入 | 条目 11 覆盖 | 已覆盖 |
| 工具注册中心生命周期（全局单例 + RLock） | 是——条目 15 覆盖 | 条目 15 覆盖 | 已覆盖 |
| 工具集的组合与复用（includes 递归） | 否——nanobot 使用显式 flat 注册 | 条目 15 覆盖了注册方式 | 已覆盖。nanobot 的显式注册不需要 includes 组合 |

### 反向检查汇总：nanobot 草稿中遗漏的设计选择

以下条目在 seeds 中被标记为 openclaw/hermes 特有，但 nanobot 很可能也面对——需在 Phase 3a 回溯确认：

1. **LLM provider 接口粒度**（漏提）——nanobot 的 5 种 backend 对不同能力 provider 的接口适配策略
2. **启动时懒加载**（漏提）——pkgutil 扫描是否全量加载 channel 代码，冷启动是否有优化
3. **入站消息防抖**（漏提）——IM 场景下碎片化消息合并策略
4. **对话轮次预算控制**（漏提）——AgentRunner 的 tool-calling 循环是否有硬上限
5. **多粒度工具权限策略**（漏提）——是否有不同粒度（agent/sub-agent/channel）的工具权限控制

---

## 任务 3：已有 Concept 更新检查

### Concept 1: `context-compression-quality`
**nanobot 是否提供新方案**：**是**。四层透明治理（Backfill + Microcompact + Budget + Snip）是第三种压缩策略。
- 与方案 A（openclaw LLM 摘要）不同：nanobot 完全不使用 LLM 做摘要
- 与方案 B（hermes LLM 摘要 + 结构化模板）不同：nanobot 不使用 LLM，所有层都是确定性规则
- nanobot 的 Backfill（修复 orphaned tool_use）是 openclaw 和 hermes 都没有的前置步骤
- nanobot 的 Snip（从尾部裁剪）与 openclaw 的 prune（从头部丢弃）方向相反
**更新内容**：追加方案 C「规则透明压缩」。溯源：`agent/runner.py:102-107, agent/runner.py:553-640`

### Concept 2: `context-engine-singleton-vs-pluggable`
**nanobot 是否提供新方案**：**否**。nanobot 的上下文治理（四层透明操作）是 AgentRunner 内部的固定逻辑，没有可插拔的 Context Engine 概念。
**结论**：跳过。nanobot 在此问题上不构成新的对比维度。

### Concept 3: `dangerous-operation-prevention`
**nanobot 是否提供新方案**：**否**。nanobot 的安全模型是 SSRF + exec 沙箱 + workspace 隔离——这些是基础设施级防护，不是危险操作检测/审批。nanobot 没有审批系统，没有危险模式正则，没有 pre-LLM 工具过滤 pipeline（就种子库当前的条目 11 和 entity 页来看）。
**结论**：跳过。nanobot 的安全策略与 openclaw/hermes 的审批/检测策略属于不同层面，不直接可比。

### Concept 4: `llm-input-token-cost-reduction`
**nanobot 是否提供新方案**：**是**。六层固定顺序纯函数式 ContextBuilder 是方案 A（prompt 内容层）的一个变体——通过构造纪律替代显式边界标记。
- openclaw：显式 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记切分稳定/动态 + pi-ai `cacheRetention` + OpenRouter wrapper
- hermes：AIAgent 实例缓存 + `apply_anthropic_cache_control` system_and_3 策略
- **nanobot：纯函数式构造 + 固定顺序 + 无运行时状态依赖 + builtins 按名称排序保证稳定前缀**

nanobot 没有显式 cache_control 标记操作（至少在草稿中未体现），但它通过构造纪律来保证 cache 稳定性。这是一个在"显式标记"和"实例缓存"之间的第三条路："构造约定"。
**更新内容**：追加方案 A 变体「纯函数式 cache-stable 构造」。溯源：`agent/context.py:17, agent/context.py:30-63`

### Concept 5: `memory-retrieval-timing`
**nanobot 是否提供新方案**：**是（写入侧）**。现有 Concept 聚焦于记忆检索时机（工具驱动 vs 后台预取），nanobot 的 Consolidator 提供了记忆写入（压缩）时机的答案。
- openclaw：记忆写入未在 Concept 中详细覆盖（`memory_search` 是只读工具）
- hermes：记忆写入在 turn 结束时同步执行（`sync_turn()`）
- **nanobot：Consolidator 独立 provider + `asyncio.create_task` 完全异步，不阻塞主循环**

nanobot 的方案将记忆压缩从关键路径完全移除，比 hermes 的 turn-end sync 更进一步。
**更新内容**：在 Concept 中新增「记忆写入时机」维度，或将其作为子节追加。溯源：`agent/memory.py:346-365, agent/loop.py:470-474`

### Concept 6: `plugin-subsystem-auto-discovery`
**nanobot 是否提供新方案**：**是（两个新实例）**。
- 条目 5（Channel 发现）：pkgutil 自发现 + entry_points 外部插件，内置优先覆盖——这是第三种发现机制
- 条目 15（工具注册）：显式 register()——与 hermes 的 AST 隐式扫描形成直接对比

这两个实例分别代表自动发现的两种新策略：「包管理器级发现」和「显式确定性注册」。前者补充了"内置 vs 第三方"的优先级管理需求，后者提供了一个与 hermes 的隐式约定截然相反的立场。
**更新内容**：追加两个实例。溯源：`channels/registry.py:23, channels/registry.py:42-55` 和 `agent/tools/registry.py:8-18, agent/loop.py:225-229`

### Concept 7: `tool-execution-safety-approval`
**nanobot 是否提供新方案**：**否**。nanobot 没有审批系统（无 human-in-the-loop exec approval），安全策略是沙箱隔离而非审批门控。
**结论**：跳过。nanobot 的安全模型是 prevention-by-isolation（沙箱防止伤害），openclaw/hermes 是 prevention-by-approval（审批阻止危险操作）。两者解决同一问题的不同层面，但 nanobot 的沙箱隔离方式在种子库中没有作为审批系统的直接替代方案来记录。

---

## 总结

### 数量统计

| 类别 | 数量 |
|------|------|
| nanobot 草稿条目 | 15 |
| 已有 Concept 匹配（需更新） | 5（context-compression-quality, llm-input-token-cost-reduction, plugin-subsystem-auto-discovery, memory-retrieval-timing, + 1 partial） |
| 候选新 Concept | 10 |
| nanobot 独有（待观察） | 2（条目 1 组装连线、条目 12 会话存储） |
| 反向检查发现漏提 | 5（provider 接口粒度、懒加载、防抖、turn 预算、工具权限策略） |
| 已有 Concept 无需更新 | 2（context-engine-singleton-vs-pluggable, dangerous-operation-prevention, tool-execution-safety-approval） |

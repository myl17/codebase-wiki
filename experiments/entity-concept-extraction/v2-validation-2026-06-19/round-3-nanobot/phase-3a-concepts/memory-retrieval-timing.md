---
concept: memory-retrieval-timing
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
  - nanobot
---

# 记忆检索与注入时机：Prompt 组装期批量注入还是后台异步预取？

## 标准化问题陈述

在多轮对话中，如何决定记忆检索与注入 LLM 上下文的时机——是在 prompt 组装阶段批量注入还是后台异步预取？

## 核心关切

1. **新鲜度**：实时检索可获取包含当前轮刚写入的最新记忆；预取返回的是上一轮结束时检索的结果，当前轮新增记忆不可见
2. **确定性**：同一轮对话内多次 API 调用（tool call 循环）期间，记忆内容若变化会导致 prompt 不一致，LLM 行为不可复现
3. **用户感知延迟**：同步检索——尤其是跨多后端聚合——直接增加用户等待的首次 token 时间（TTFT）
4. **多后端兼容**：不同记忆后端（SQLite 向量搜索、外部 HTTP API、云服务）检索延迟差异巨大，注入时机设计需兼容从毫秒到秒级的延迟范围
5. **异步预取的过时问题**：上一轮结束后入队的预取结果反映的是上一轮对话状态，无法包含本轮上下文——命中率依赖对话连续性
6. **Provider 状态隔离**：记忆操作（检索/压缩）的 LLM API 调用是否与主 agent 对话共享同一 provider 实例——若共享则速率限制计数器、连接池、重试状态互相污染

## 已知权衡位置

### 位置 A：openclaw — Prompt 组装阶段批量注入

**优先满足的关切**：确定性（同一次 LLM 调用期间的 prompt 不变，tool call 循环中记忆内容稳定）；多后端兼容（不同 backend 在组装阶段统一调 `promptBuilder`，延迟差异不影响架构）

**接受妥协的关切**：新鲜度（组装发生在 API 调用前，当前轮新增记忆不可见——必须等到下一轮 prompt 组装）

**核心特征**：记忆检索不发生在每轮对话的运行时，而是在 prompt 组装（`assemble`）阶段通过 `buildMemoryPromptSection` 统一构建记忆 prompt section，注入 system prompt 中。记忆能力通过 `registerMemoryCapability` 注册为一个 exclusive 槽位（全局唯一活跃实现，后来者替换前者而非并存）。记忆内容作为 system prompt 的一部分在同一轮内保持稳定——无论 tool call 循环多少次，记忆 prompt 内容不变。

**关键机制（源码可见）**：

1. **`registerMemoryCapability` exclusive 槽位注册**（`src/plugins/memory-state.ts:170-174`）：`memoryPluginState.capability = { pluginId, capability: { ...capability } }` ——直接覆盖而非追加，全局只能有一个活跃记忆实现。这是替换式架构（非增量式）——与 hermes-agent 内置 + 外部并存形成对比。

2. **`buildMemoryPromptSection` prompt section 构建**（`src/plugins/memory-state.ts:206-219`）：从 exclusive capability 的 `promptBuilder` 获取主记忆 section，再追加所有 `promptSupplements`（按 pluginId 排序保证确定性）。所有记忆后端在此统一输出 string[]，调用方（system prompt 组装）不感知后端差异。

3. **`buildMemorySection` 在 system prompt 组装中调用**（`src/agents/system-prompt.ts:169-182`、`613-618`）：`buildMemorySection` 是 `buildMemoryPromptSection` 的薄封装，由 `isMinimal` 和 `includeMemorySection` 门控。调用位置在 system prompt 构建函数中，与 identity、safety、skills、docs 等 section 并列——记忆是 system prompt 的一个组成部分，而非运行时注入。

4. **`buildMemorySystemPromptAddition` 为 context engine 提供记忆 opt-in**（`src/context-engine/delegate.ts:74-87`）：非 legacy context engine 通过此函数显式 opt-in 获取记忆 prompt section，避免在非 legacy 路径下重复实现记忆格式化逻辑。调用 `buildMemoryPromptSection` → `normalizeStructuredPromptSection` → 返回标准化 prompt 片段。

5. **`MemorySearchManager` 接口抽象多后端搜索**（`src/memory-host-sdk/host/types.ts:68-94`）：`search()` 方法统一封装向量搜索与语义检索，支持 `builtin`（SQLite + sqlite-vec）和 `qmd`（外部引擎）两种 backend。backend 差异在 `search()` 实现层处理，组装阶段只消费 `promptBuilder` 的输出，不直接依赖特定 backend。

**已知代价**：
- 当前轮写入的记忆（通过 memory_search 工具）在当前轮不可见——必须等到下一轮 prompt 组装
- 无异步预取机制：每次 prompt 组装都是同步检索，检索延迟叠加到 prompt 组装耗时
- exclusive 槽位意味着无法同时使用两个记忆后端构建互补的 prompt section（只能有一个 promptBuilder）
- 记忆 prompt section 在 tool call 循环中不可更新——即使 agent 在循环中通过工具操作了记忆，prompt 不变

**已知实例**：
- [[openclaw/nodes/components/openclaw-memory-system]]
- [[openclaw/nodes/components/openclaw-context-engine]]

---

### 位置 B：hermes-agent — 后台预取 + 不阻塞关键路径

**优先满足的关切**：用户感知延迟（`queue_prefetch_all` 在后台 daemon 线程触发检索，不阻塞 API 调用）；多后端兼容（每个 provider 独立管理自己的预取线程和缓存，provider 间互不阻塞）

**接受妥协的关切**：新鲜度（预取结果来自上一轮 `queue_prefetch_all`，当前轮刚写入的记忆不可见）；确定性（预取线程完成时间不确定——如果上一轮后台预取未完成，当前轮 `prefetch` 可能返回空或部分结果）

**核心特征**：记忆采用两阶段时序——每轮结束后 `queue_prefetch_all` 启动后台线程异步检索，结果缓存于 provider 的 `_prefetch_result`；下一轮开始时 `prefetch_all` 从缓存读取（若后台线程还在运行则 join 等待最多 3 秒），将记忆内容注入当前轮用户消息（API-call time 临时注入，不留痕于持久化的 messages）。整个流程中记忆检索不阻塞 API 调用——检索发生在上一轮结束到下一轮开始之间的窗口期。

**关键机制（源码可见）**：

1. **`queue_prefetch_all` 后台预取入队**（`agent/memory_manager.py:197-206`）：遍历所有注册的 provider，调用 `provider.queue_prefetch(query, session_id=session_id)`。调用时机在 `run_agent.py:11236-11239`：`sync_all` 同步完成轮次后立即 `queue_prefetch_all(original_user_message)` ——当前轮刚结束就为下一轮启动预取。

2. **`HindsightMemoryProvider.queue_prefetch` daemon 线程实现**（`plugins/memory/hindsight/__init__.py:672-713`）：创建 `threading.Thread(target=_run, daemon=True, name="hindsight-prefetch")`，线程内调用 `client.arecall` 或 `client.areflect` API，结果写入 `self._prefetch_result`（受 `_prefetch_lock` 保护）。`_memory_mode == "tools"` 或 `_auto_recall == False` 时跳过——预取是可配置的。

3. **`MemoryManager.prefetch_all` 同步收集缓存结果**（`agent/memory_manager.py:178-195`）：遍历所有 provider 调用 `provider.prefetch(query, session_id=session_id)`，合并非空结果字符串。调用时机在 `run_agent.py:8484-8488`：在 tool call 循环外、第一次 API 调用前执行一次，结果缓存到 `_ext_prefetch_cache` 供循环内各次 API 调用复用——避免每次 tool call 都重新预取。

4. **`HindsightMemoryProvider.prefetch` 等待并消费后台结果**（`plugins/memory/hindsight/__init__.py:654-670`）：若 `_prefetch_thread` 仍在运行则 `join(timeout=3.0)` 等待完成（带超时免死锁）；从 `_prefetch_result` 取走结果后清空（`self._prefetch_result = ""`）；返回带 preamble 头部的格式化上下文。若超时或无结果返回空字符串——本轮的代价是记忆缺失而非延迟。

5. **`build_memory_context_block` 围栏包装 + API-call 注入**（`agent/memory_manager.py:65-80`）：预取结果包裹在 `<memory-context>...</memory-context>` XML 围栏中，前缀 `[System note: The following is recalled memory context, NOT new user input.]` ——明确告诉 LLM 这不是用户输入而是背景信息。注入位置在 `run_agent.py:8561-8577`：在构建 API 消息列表时，找到当前轮用户消息的索引，将 `_ext_prefetch_cache` 和 plugin 上下文临时拼接到消息 `content` 中——原始的 `messages` 列表不变，记忆注入不留痕于持久化层。

6. **`MemoryProvider.system_prompt_block` 静态信息分离**（`agent/memory_provider.py:83-90`）：provider 的静态信息（指令、状态）通过 `system_prompt_block()` 在 system prompt 组装阶段注入（`MemoryManager.build_system_prompt`），与预取上下文分离——静态信息是稳定可缓存的，预取上下文是每轮变化的。这种分离避免把缓存失效的代价波及 system prompt。

**已知代价**：
- `queue_prefetch_all` 发生在**上一轮**结束后——预取用的 query 是上一轮的用户消息，不包含当前轮上下文
- 若上一轮预取线程未完成（网络延迟、API 超时），`prefetch` 最多等 3 秒后放弃，本轮无记忆注入
- 预取结果来自异步线程——两次预取之间若同一 session 的另一个并发请求修改了记忆后端，可能读到脏数据
- `_prefetch_result` 是单槽位缓存——若 `queue_prefetch_all` 和 `prefetch_all` 在不匹配的节奏下调用，可能消费空缓存或旧缓存

**已知实例**：
- [[hermes-agent/nodes/extension-points/hermes-agent-memory-provider]]
- [[hermes-agent/nodes/components/hermes-agent-ai-agent]]

---

### 位置 C：nanobot — Consolidator 同 Provider 时序隔离 + 异步后台任务

**优先满足的关切**：时序隔离（`asyncio.create_task()` 后台运行，压缩不阻塞主循环，主 agent API 调用不被压缩任务阻塞）；零阻塞（主循环在 `_schedule_background` 调度后立即继续，不等待压缩完成）

**接受妥协的关切**：结果延迟生效（压缩结果在下轮 context 组装时才可见，本轮使用压缩前内容）；失败不中断但下一轮仍用旧内容

**核心特征**：Consolidator 是 nanobot 三层记忆架构（MemoryStore → Consolidator → Dream）中的压缩层，独立于主循环运行。与位置 A（检索型——每次组装时同步检索记忆后端）和位置 B（预取型——后台线程异步检索向量存储）不同，Consolidator 的核心任务不是检索记忆，而是将历史对话压缩为文件级摘要——但它在**何时**执行这项工作的时序设计上，与记忆检索时机面临相同的架构权衡。Consolidator 复用主 AgentLoop 的同一个 provider 实例（并非独立副本——源码 `agent/loop.py:210-219` 中 `provider` 参数与 `self.provider` 指向同一对象），隔离完全通过 `asyncio.create_task()` 在时序层面实现——压缩任务在后台运行，主 agent 在压缩期间不受阻塞。压缩失败不会中断正在进行的对话。压缩结果写入 `agent/memory/prompt/` 目录，在下一轮 ContextBuilder 组装 system prompt 的 memory 层时被读取并注入。

**关键机制（源码可见）**：

1. **同 provider 实例 + `asyncio.create_task()` 时序隔离启动**（`agent/loop.py:210-219`）：Consolidator 在 AgentLoop 初始化时创建，接收的 `provider` 参数与 AgentLoop 的 `self.provider` 是同一个对象实例（源码中未见 deep copy 或独立实例创建），通过 `asyncio.create_task()` 在后台启动压缩任务。隔离是**时序隔离**（temporal isolation）而非**实例隔离**（instancial isolation）——压缩任务和主循环的 API 调用在时间上不会直接竞争，但它们共享同一个 provider 对象的内部状态（速率限制计数器、连接池等）。

2. **Consolidator 触发点**（`agent/loop.py:572`）：在消息处理流程中的特定位置触发 Consolidator 检查——当条件满足时（如累积足够轮次），启动新一轮压缩。触发逻辑嵌入在主循环路径中，但通过 `asyncio.create_task()` 将实际工作抛到后台，主循环立即继续。

3. **Consolidator 压缩逻辑**（`agent/memory.py:346+`）：核心压缩实现——将历史消息按会话分组，通过 LLM 生成摘要，写入 `agent/memory/prompt/` 目录的文件中。压缩是幂等的——同一会话的多次压缩会覆盖之前的结果。压缩不涉及向量检索或语义搜索——纯 LLM 摘要 + 文件 I/O。

4. **ContextBuilder memory 层注入**（`agent/context.py:30-63`）：系统 prompt 的 memory 层在组装阶段读取 MEMORY.md 内容和 `agent/memory/prompt/` 下的压缩摘要文件。压缩结果在下轮组装时才生效——这是异步压缩的固有延迟：本轮 context 组装时读到的压缩文件是上一轮（或更早）触发压缩的结果。

**已知代价**：
- 共享 provider 意味着速率限制计数器不隔离——压缩的 API 调用计入同一 provider 的 quota，可能挤占主 agent 对话的速率限制配额；连接池和重试状态也是共享的，压缩任务的重试/错误可能间接影响 provider 的内部状态
- 本轮使用旧压缩内容——压缩结果在下轮 context 组装时才可见，本轮对话使用的记忆摘要不包含本轮内容
- 压缩失败不中断主循环——但本轮的代价是下一轮仍使用旧压缩内容（可能缺失关键上下文，LLM 基于过时摘要做出决策）
- 文件 I/O 后端的局限性——无向量检索、无语义搜索，压缩摘要的命中精度完全依赖 LLM 的摘要质量

**已知实例**：
- [[nanobot/dimensions/nanobot-architecture]]
- [[nanobot/dimensions/nanobot-performance-tradeoffs]]

---

## 跨仓库对比

| 维度 | openclaw（Prompt 组装阶段批量注入） | hermes-agent（后台预取 + 不阻塞关键路径） | nanobot（Consolidator 同 Provider 时序隔离 + 异步后台压缩） |
|------|------------------------------------|----------------------------------------|---------------------------------------------------|
| **检索/压缩时机** | Prompt 组装阶段（`assemble`），同步检索 | 上一轮结束后入队后台线程，下一轮开始时消费缓存 | 主循环触发点异步启动压缩（`asyncio.create_task()`），下轮 context 组装时读取压缩文件 |
| **注入位置** | System prompt section（与 identity/safety/skills 并列） | 用户消息尾部（`<memory-context>` 围栏，API-call 临时注入） | System prompt memory 层（MEMORY.md + `agent/memory/prompt/` 压缩摘要文件） |
| **确定性** | 高——同一轮内 system prompt 不变，记忆内容在整个 tool call 循环中稳定 | 中——依赖后台预取线程完成度，若未完成本轮记忆缺失 | 高——本轮内压缩文件不变（压缩在下轮才更新），同一轮内记忆内容稳定 |
| **新增记忆可见性** | 不保证——组装发生在 API 调用前，当前轮工具写入的记忆要到下一轮组装才可见 | 不保证——预取上一轮结束前入队，当前轮写入要到下一轮预取才可见 | 不保证——压缩结果在下轮 context 组装时才可见，本轮写入要到下一轮压缩后才被摘要覆盖 |
| **用户感知延迟** | 有——同步检索延迟叠加到 prompt 组装耗时，影响 TTFT | 低——检索在后台完成，API 调用路径上只做缓存读取和 join（最多 3s） | 极低——`asyncio.create_task()` 后台运行，主循环路径上零阻塞 |
| **Provider 状态隔离** | 否——记忆检索复用主 agent 的 provider/builder 调用链，速率限制计数器共享 | 否——预取通过独立 provider 接口调用，但 provider 实例共享连接池和速率限制状态 | 否——Consolidator 复用主 AgentLoop 的 provider 实例，速率限制计数器、连接池、重试状态均共享；隔离仅通过 `asyncio.create_task()` 在时序层面实现（temporal isolation） |
| **多后端处理** | promptBuilder 统一抽象——所有后端在组装阶段输出 string[]，后端差异对调用方透明 | 每个 provider 独立管理线程和缓存——provider 间隔离，互不阻塞 | 单一文件 I/O 后端（MemoryStore 读/写 MEMORY.md + Consolidator 写 `agent/memory/prompt/`），无多后端抽象层 |
| **后端数量约束** | exclusive 槽位（1 个 promptBuilder，+ 多个 promptSupplement） | 内置必开启 + 最多 1 个外部 provider（增量式，内置不可移除） | 固定三层架构（MemoryStore + Consolidator + Dream），非插件式，不可替换 |
| **缓存/预取策略** | 无——每次组装重新检索（检索结果由向量引擎缓存决定） | 有——`queue_prefetch_all` 后台线程 + `_prefetch_result` 单槽位缓存 | 有——压缩结果写入文件（`agent/memory/prompt/`），下轮组装时读取；无内存级缓存 |
| **失败处理** | promptBuilder 异常由调用方处理，可能导致记忆 section 缺失 | 每个 provider 异常独立捕获（非致命），预取失败本轮的代价是记忆缺失 | 压缩失败不中断主循环（`asyncio.create_task()` 隔离），下一轮使用旧压缩内容 |
| **持久化边界** | 记忆内容写入 system prompt，理论上被持久化到会话文件 | 记忆注入暂时性（API-call time only），不污染持久化的 messages | 压缩结果持久化到文件系统（`agent/memory/prompt/`），跨轮次、跨进程可复用 |
| **核心取舍** | 宁可每次组装都检索一遍也要保证同一轮内的确定性 | 宁可用上一轮结果（可能过时）也不阻塞当前轮 API 调用 | 宁可用上一轮压缩结果（可能过时）也不让压缩阻塞主循环；时序隔离以共享 provider 内部状态（速率限制计数器、连接池）为代价 |

## 选择指南

| 场景 | 推荐偏向 | 理由 |
|------|---------|------|
| 单轮内多次 tool call，需保证 prompt 一致 | openclaw 批量注入 | system prompt 在整轮中不变，tool call 循环内记忆内容不漂移 |
| 延迟敏感——TTFT 是核心指标 | hermes-agent 后台预取 | 检索在后台完成，API 调用路径只做轻量缓存读取 |
| 多记忆后端并存，后端延迟差异大（本地 SQLite + 远程云服务） | hermes-agent provider 隔离 | 每个 provider 独立线程，慢后端不阻塞快后端，彼此隔离 |
| 需要记忆内容写入后立即可检索 | 三者均不满足 | 三者都不保证当前轮写入的记忆当前轮可见——这是时序设计的固有代价 |
| 记忆注入要明确区分于用户输入 | hermes-agent 围栏模式 | `<memory-context>` XML fence + system note，LLM 被明确告知这是背景信息 |
| 需要两个记忆后端同时贡献 prompt | openclaw promptSupplement | exclusive 槽位 + supplement 列表，允许一个主实现 + 任意数量补充 |
| 需要在 system prompt 中缓存记忆指令 | openclaw system prompt 路径 | 记忆作为 system prompt section，可与 system prompt cache 机制联动 |
| 记忆结果需可审计、可复现 | openclaw 同步检索 | 每次组装同步检索，结果可精确追溯到具体的检索参数和向量引擎状态 |
| 文件级记忆压缩，不依赖向量数据库，需要零阻塞压缩 | nanobot Consolidator 后台压缩 | 同 provider 实例 + `asyncio.create_task()` 时序隔离，压缩和对话在时间上解耦；纯文件 I/O 无外部依赖 |
| 需要 Provider 状态隔离——压缩 API 调用不影响主 agent 速率限制 | 三者均不满足 | 三者均共享 provider 实例；若需实例级隔离需自行实现独立 provider 副本创建 |
| 需要跨进程、跨重启复用记忆压缩结果 | nanobot 文件持久化 | 压缩结果写入文件系统，其他进程或重启后可读取，不依赖内存缓存生命周期 |

## 溯源表

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/plugins/memory-state.ts` | 170-174 | `registerMemoryCapability` exclusive 槽位——全局只能有一个活跃实现 |
| openclaw | `src/plugins/memory-state.ts` | 206-219 | `buildMemoryPromptSection` 合并 capability promptBuilder + supplements |
| openclaw | `src/agents/system-prompt.ts` | 169-182 | `buildMemorySection` 门控封装——isMinimal/includeMemorySection 决定是否包含记忆 |
| openclaw | `src/agents/system-prompt.ts` | 613-618 | `buildMemorySection` 在 system prompt 组装中的调用位置 |
| openclaw | `src/context-engine/delegate.ts` | 74-87 | `buildMemorySystemPromptAddition` —— context engine 路径显式 opt-in 记忆 |
| openclaw | `src/context-engine/legacy.ts` | 38-54 | `LegacyContextEngine.assemble` pass-through——记忆在别处 (system-prompt.ts) 注入 |
| openclaw | `src/memory-host-sdk/host/types.ts` | 68-94 | `MemorySearchManager` 接口——search/readFile/status，统一多 backend |
| hermes-agent | `agent/memory_manager.py` | 197-206 | `queue_prefetch_all` ——遍历 provider 后台预取入队 |
| hermes-agent | `agent/memory_manager.py` | 178-195 | `prefetch_all` ——同步收集所有 provider 的缓存结果 |
| hermes-agent | `agent/memory_manager.py` | 65-80 | `build_memory_context_block` —— `<memory-context>` 围栏 + system note 包装 |
| hermes-agent | `agent/memory_manager.py` | 83-90 | `MemoryManager` 类 docstring —— 完整时序说明（prefetch → sync → queue_prefetch） |
| hermes-agent | `agent/memory_provider.py` | 92-104 | `MemoryProvider.prefetch` ABC ——应快速返回缓存结果，不阻塞 |
| hermes-agent | `agent/memory_provider.py` | 106-112 | `MemoryProvider.queue_prefetch` ABC ——后台预取，下一轮消费 |
| hermes-agent | `agent/memory_provider.py` | 83-90 | `MemoryProvider.system_prompt_block` ABC ——静态信息与预取上下文分离 |
| hermes-agent | `plugins/memory/hindsight/__init__.py` | 654-670 | `HindsightMemoryProvider.prefetch` ——join 后台线程 (timeout 3s) + 取走缓存 + 清空 |
| hermes-agent | `plugins/memory/hindsight/__init__.py` | 672-713 | `HindsightMemoryProvider.queue_prefetch` ——daemon 线程调用 recall/reflect API，结果写 `_prefetch_result` |
| hermes-agent | `run_agent.py` | 8469-8490 | 预取调用点：`on_turn_start` → `prefetch_all` → 缓存 `_ext_prefetch_cache`，在 tool loop 外 |
| hermes-agent | `run_agent.py` | 8561-8577 | API-call 注入点：`build_memory_context_block` + plugin 上下文临时拼接到用户消息 |
| hermes-agent | `run_agent.py` | 11233-11241 | 轮次收尾：`sync_all` + `queue_prefetch_all` — 同步后立即为下一轮预取 |
| nanobot | `agent/loop.py` | 210-219 | Consolidator 同 provider 实例创建 + `asyncio.create_task()` 后台启动——压缩与对话通过 asyncio 时序隔离（temporal isolation），非实例隔离 |
| nanobot | `agent/loop.py` | 572 | Consolidator 触发点——消息处理流程中条件检查，满足时启动新一轮后台压缩 |
| nanobot | `agent/memory.py` | 346+ | Consolidator 压缩逻辑——历史消息按会话分组 → LLM 摘要 → 写入 `agent/memory/prompt/` 文件 |

## 关联

- [[openclaw/nodes/components/openclaw-memory-system]] — openclaw MemorySystem 组件（可替换记忆后端）
- [[openclaw/nodes/components/openclaw-context-engine]] — openclaw ContextEngine 组件（prompt 生命周期管理）
- [[hermes-agent/nodes/extension-points/hermes-agent-memory-provider]] — hermes-agent MemoryProvider 扩展点
- [[hermes-agent/nodes/components/hermes-agent-ai-agent]] — hermes-agent AIAgent 中央编排器（预取调用点所在）
- [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]] — hermes-agent ContextEngine（另一侧的 prompt 组装对比）
- [[nanobot/dimensions/nanobot-architecture]] — nanobot 三层记忆架构（MemoryStore + Consolidator + Dream）
- [[nanobot/dimensions/nanobot-performance-tradeoffs]] — nanobot Consolidator 异步压缩性能取舍
- [[可替换记忆后端]] — 父级 concept（记忆后端可替换性维度）

---

## 修复记录

**2026-06-19**：根据 phase-3b-verify/memory-retrieval-timing-verify.md 验证报告修复 1 处 ⚠️ 关键错误。

**发现**：验证报告指出 `agent/loop.py:210-219` 中 Consolidator 接收的 `provider` 参数与 AgentLoop 的 `self.provider` 是同一个对象实例，并非独立副本。隔离是通过 `asyncio.create_task()` 实现的**时序隔离**（temporal isolation），而非**实例隔离**（instancial isolation）。

**修正内容**：
1. 权衡位置名称从「Consolidator 独立 Provider 实例 + 异步后台任务」改为「Consolidator 同 Provider 时序隔离 + 异步后台任务」
2. 优先满足的关切从「Provider 状态隔离」改为「时序隔离（`asyncio.create_task()` 后台运行，不阻塞主循环）」
3. 关键机制描述修正：不再声称「独立 provider 实例」，改为「共享同一个 provider 对象，通过 `asyncio.create_task()` 实现时序解耦」
4. 代价修正：「多一个 provider 实例的资源开销」改为「共享 provider 意味着速率限制计数器不隔离——压缩的 API 调用计入同一 provider 的 quota」
5. 跨仓库对比表「Provider 状态隔离」行：nanobot 从「是」改为「否」，明确说明隔离仅在时序层面
6. 跨仓库对比表「核心取舍」行同步修正
7. 选择指南「需要 Provider 状态隔离」场景从推荐 nanobot 改为「三者均不满足」
8. 溯源表 nanobot 条目同步修正

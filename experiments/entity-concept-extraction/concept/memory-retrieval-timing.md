# memory-retrieval-timing

## 问题陈述

如何设计记忆检索的触发模型以在时效性、延迟和 LLM 上下文窗口开销之间取得平衡？

跨仓库分析 openclaw、hermes 和 nanobot 的记忆检索与压缩策略。三者代表了三种根本不同的检索与写入模型：

- **openclaw**：**工具驱动按需检索**。系统提示中包含静态的工具使用指引，LLM 在对话中自主决定何时调用 `memory_search`/`memory_get` 工具，检索在工具调用时实时执行。
- **hermes**：**后台异步预取**。系统在每轮结束后后台触发记忆检索，下一轮 API 调用时将缓存结果注入 user message，对 LLM 透明。
- **nanobot**：**同步文件注入 + cron 调度两阶段写入**。记忆检索在系统提示构建时直接读文件完成（同步、无检索、无 LLM 参与）；记忆压缩分两层——Consolidator 做 token-budget 触发的异步摘要归档，Dream 做 cron 调度的两阶段深度写入。检索和写入完全解耦，各自独立调度。

这三种模型在 staleness 特性、LLM 上下文窗口开销、检索延迟发放方式上各有取舍，且解决的核心问题不同——openclaw 解决"如何给 LLM 可查询的持久记忆"，hermes 解决"如何透明注入相关记忆而不增加 LLM 推理负担"，nanobot 解决"如何让记忆检索零延迟且记忆压缩不影响对话可用性"。

## 已知答案图谱

### 方案 A：工具驱动按需检索（openclaw）

**模型**：LLM 在对话中自主调用记忆工具执行实时检索，系统不预取记忆内容。

**具体实现**：

记忆系统由两层组成。第一层是**系统提示中的静态指引文本**。在系统提示组装阶段，`buildMemorySection()`（`src/agents/system-prompt.ts:169-182`）调用 `buildMemoryPromptSection()`（`src/plugins/memory-state.ts:206-219`）。`buildMemoryPromptSection()` 调用由记忆插件通过 `registerMemoryCapability()`（`src/plugins/memory-state.ts:170-175`）注册的 `promptBuilder` 函数。该 `promptBuilder` 是一个**纯同步函数**，签名为 `(params: { availableTools: Set<string>; citationsMode?: MemoryCitationsMode }) => string[]`——它只生成静态指引文本，不执行任何检索。

默认的 `promptBuilder` 由 `memory-core` 内置扩展（`extensions/memory-core/src/prompt-section.ts:3-38`）提供，它根据可用工具集合生成指引段落：

```
## Memory Recall
Before answering anything about prior work, decisions, dates, people, preferences,
or todos: run memory_search on MEMORY.md + memory/*.md + indexed session transcripts;
then use memory_get to pull only the needed lines. If low confidence after search,
say you checked.
```

此文本在整个 session 期间保持静态——它告诉 LLM **如何使用**工具，而非已检索的内容。

第二层是**工具执行层**。LLM 在对话中自主调用 `memory_search` 或 `memory_get` 工具（`memory-core` 扩展在 `extensions/memory-core/index.ts:42-58` 注册）。每次工具调用时：

- `createMemorySearchTool()`（`extensions/memory-core/src/tools.ts:177-311`）通过 `getMemoryManagerContext()` 获取 `MemorySearchManager` 实例，调用 `manager.search(query, options)` 执行混合检索（向量 + 关键词，可配置权重默认 vector=0.7 / text=0.3），可选 MMR 多样化和时间衰减。搜索后端可以是内置 SQLite（FTS + sqlite-vec 向量扩展）或外部 QMD 服务。

- `createMemoryGetTool()`（`extensions/memory-core/src/tools.ts:313-394`）按路径读取特定记忆文件片段。

检索发生在 LLM 调用工具的那一刻——latency 在关键路径上，但 staleness 为零（索引实时同步，配置了文件监听和增量更新）。

**插件扩展机制**（`src/plugins/memory-state.ts`）：
- `MemoryPluginCapability.promptBuilder`（`memory-state.ts:127-132`）：独占槽位。`registerMemoryCapability()`（`memory-state.ts:170-175`）直接覆盖——多插件场景下后者覆盖前者。注册的是静态文本生成函数，不执行检索。
- `MemoryPromptSupplement`（`memory-state.ts:195-204`）：非独占比索通道。`registerMemoryPromptSupplement()` 允许多个插件提供补充提示段落，按 `pluginId` 字母序稳定排列。
- `before_prompt_build` hook（`src/plugins/hook-before-agent-start.types.ts:15-34`）：通用插件 hook，在每次 LLM 调用前触发（`src/agents/pi-embedded-runner/run/attempt.ts:1644`）。可注入 `systemPrompt`、`prependContext`、`prependSystemContext`、`appendSystemContext` 四个字段。这不是记忆专用通道——任何插件都可以使用它注入上下文，与记忆检索无关。

**机制细节**：
- 检索触发时机：完全由 LLM 决定——它可以在对话的任何时刻调用 memory_search（通常在回答需要前置知识的问题前）
- Staleness：即时（zero-staleness）。每次 memory_search 调用执行实时搜索，索引通过文件监听（debounce 1.5s）和定时同步（可配置 interval）保持最新
- 检索在 LLM 调用的关键路径上：LLM 发 tool call → 执行混合检索 → 结果返回 LLM → LLM 继续推理
- 每次 memory_search 调用消耗 context window（tool call + 搜索结果 token）
- 可靠性依赖 LLM 遵循系统提示中的指引——LLM 可能忘记调用 memory_search

### 方案 B：每轮后台异步预取（hermes）

**时机**：当前 turn 完成后在后台线程触发记忆检索，下一轮 API 调用时消费缓存的检索结果。检索与 LLM 调用不在同一关键路径上。

**具体实现**：

MemoryManager 在每轮对话的三个时间点介入（`agent/memory_manager.py`）：

1. **Turn 开始时**（`run_agent.py:8475`）：`on_turn_start()` 通知所有 provider 新 turn 开始，用于 cadence 计数和注入频率判断。

2. **API 调用前**（`run_agent.py:8488`）：`prefetch_all(query)` 收集所有 provider 的缓存结果。结果在整个 tool 循环中复用（多次 tool call 不重复调用 prefetch）。缓存结果通过 `build_memory_context_block()` 包裹为 `<memory-context>` 标签，注入到当前 turn 的 user message 末尾（`run_agent.py:8568-8577`）。注入是 API-call-time only——不污染 session 持久化的消息记录。

3. **Turn 结束后**（`run_agent.py:11238-11239`）：先 `sync_all()` 持久化此轮对话，然后 `queue_prefetch_all()` 触发所有 provider 的后台预取，为下一轮准备缓存。

Provider 基类（`agent/memory_provider.py:92-112`）定义了 `prefetch()` 返回缓存结果和 `queue_prefetch()` 触发后台检索。默认实现均为 no-op。

**Honcho provider 的线程调度细节**（`plugins/memory/honcho/__init__.py:631-677`）：

`queue_prefetch()` 启动一个 daemon 线程运行 dialectic 查询（多 pass LLM 推理生成用户摘要），结果写入 `_prefetch_result`（由 `threading.Lock` 保护）。`prefetch()` 在下一轮被调用时：先检查是否有后台上下文刷新产出了更新的 base context（`pop_context_result()`），然后 join 后台 prefetch 线程（timeout 3s），读取 `_prefetch_result` 并清空。

**机制细节**：
- Staleness 窗口：恰好 1 个 turn。Turn N 中写入的新事实在 turn N 结束时 `sync_turn()` 持久化，turn N 结束时 `queue_prefetch()` 触发检索（使用 turn N 的消息），turn N+1 的 `prefetch()` 消费检索结果。意味着 turn N 写入的内容在 turn N+1 的 API 调用时可用
- 首轮特殊处理（`prefetch()` 第 563-596 行）：当 `_last_dialectic_turn == -999` 时（首轮），不依赖 `queue_prefetch`（尚未运行过），而是同步执行 dialectic 查询，但有超时保护（默认 8s，来自 `config.timeout`）。超时后放弃首轮 dialectic，等待下一 cadence 周期补上
- Cadence 门控：`_context_cadence = 1`（base context 每轮刷新），`_dialectic_cadence = 3`（dialectic 最多每 3 轮触发一次，因为涉及昂贵的 LLM 推理）。两个 cadence 独立计算
- 线程安全：`_prefetch_lock` 保护 prefetch 结果的读写；`_base_context_lock` 保护 base context 缓存的更新。sync 线程（`_sync_thread`）在启动新的 sync 前 join 上一轮残留线程（timeout 5s），防止堆积

### 方案 C：同步文件注入 + cron 调度两阶段写入（nanobot）

**检索模型**：记忆检索是系统提示构建时的同步文件读取——每次 `build_system_prompt()` 调用 `MemoryStore.get_memory_context()` 读取 `MEMORY.md` 全文注入系统提示。无异步、无 LLM 参与、无 embedding/向量检索。

**写入模型**：记忆压缩与检索完全解耦，分两层独立调度——Consolidator 做对话历史的 token-budget 截断归档，Dream 做 cron 调度的深度两阶段记忆更新。

**检索的具体实现**：

`ContextBuilder.build_system_prompt()`（`nanobot/agent/context.py:30-63`）按固定顺序组装系统提示：

1. Identity（workspace 路径、运行时信息）
2. Bootstrap 文件（AGENTS.md / SOUL.md / USER.md / TOOLS.md）
3. **记忆上下文**：`self.memory.get_memory_context()`（`context.py:42-44`）——调用 `MemoryStore.get_memory_context()`（`memory.py:217-219`），后者调用 `read_memory()` 同步读取 `MEMORY.md` 全文，格式化为 `## Long-term Memory\n{content}`。当文件为空时返回空字符串，提示中不出现记忆段落——静默降级
4. Always-on skills
5. Skills summary
6. Recent history：`read_unprocessed_history(since_cursor=get_last_dream_cursor())`（`context.py:56-61`），返回 Dream 尚未处理的 `history.jsonl` 条目，上限 50 条

记忆检索发生在**系统提示构建时**——在 LLM API 调用之前完成。检索路径是纯文件 I/O（`Path.read_text()`），微秒级完成，不涉及任何网络调用或外部 provider。

**压缩的具体实现**：

记忆压缩分两层：

**第一层：Consolidator**（`memory.py:346-515`）——token-budget 触发的对话历史截断。

- 触发条件：`estimate_session_prompt_tokens()` 估算当前 session 的 prompt token 数超过安全预算（`context_window_tokens - max_completion_tokens - 1024`）时触发
- 执行者：`Consolidator.archive()`（`memory.py:419-449`）调用 `self.provider.chat_with_retry()` 对截断的旧消息做 LLM 摘要，结果追加到 `history.jsonl`。LLM 调用失败时走 `raw_archive()`（`memory.py:336-343`）降级路径——原样保存消息到 JSONL，不丢失数据
- 时序：**混合模式**。pre-turn 路径（`loop.py:533`）用 `await` 同步执行——但只有在 token 超限时才触发 LLM 调用，正常情况仅在几个估算调用后即返回。post-turn 路径（`loop.py:572`）通过 `_schedule_background()`（`loop.py:470-474`）以 `asyncio.create_task()` 异步调度——压缩摘要不阻塞 turn 完成
- 隔离机制：`asyncio.create_task()` 将归档作为独立协程运行。由于 Consolidator 与主循环共享同一个 provider 实例（`loop.py:210-218`），并发保护由 session 级 `asyncio.Lock`（`memory.py:376-378`）提供——同一 session 的多次 consolidation 串行化，避免竞态
- 最大 5 轮压缩循环（`_MAX_CONSOLIDATION_ROUNDS = 5`），每轮截一个 user-turn 边界（`pick_consolidation_boundary()`，`memory.py:380-400`），边压缩边重新估算 token 数，直到降到目标预算以下或无更多安全边界

**第二层：Dream**（`memory.py:519-675`）——cron 调度的深度两阶段记忆更新。

- 触发条件：cron 调度，默认每 2 小时执行一次（`DreamConfig.interval_h = 2`，`config/schema.py:39`），也可通过 `/dream` 命令手动触发（`command/builtin.py:109-132`）
- Cursor 机制：`get_last_dream_cursor()`（`memory.py:304-310`）追踪已处理的 `history.jsonl` 位置。每次运行只处理新条目，最大批处理 20 条（`max_batch_size`）
- **两阶段流程**：
  - **Phase 1（LLM 分析）**：纯 LLM 调用（`memory.py:595-606`），`tool_choice=None`，系统提示为 `dream_phase1.md` 模板——要求 LLM 对比对话历史与现有记忆文件，输出 `[FILE]`（新增事实）和 `[FILE-REMOVE]`（过期内容）标记的原子事实列表
  - **Phase 2（AgentRunner 执行）**：将 Phase 1 的分析结果交给 `AgentRunner`（`memory.py:626-643`），配备 `read_file` + `edit_file` 工具，LLM 对 `MEMORY.md`/`SOUL.md`/`USER.md` 做精确的增量编辑——不重写整个文件
- 失败处理：Phase 1 失败 → 整个 Dream 跳过（return False）。Phase 2 失败 → cursor 仍然前进（`memory.py:652-654`），防止 Phase 1 重复执行。cursor 前进后 `compact_history()` 截断超量旧条目
- Git 版本控制：Dream 执行后有变更时，`GitStore.auto_commit()` 自动提交（`memory.py:669-673`），commit message 包含时间戳和变更数
- 完全离带：Dream 由 cron 服务独立调度（`cron/service.py`），不经过 agent loop 的 turn 处理流程，完全不影响对话可用性

**机制细节**：
- 检索触发时机：每次 `build_system_prompt()` 调用——即每轮对话开始前系统提示构建时。（注：由于 Python 的 ContextBuilder 实例复用，系统提示实际只在首轮构建，后续轮复用首轮构建的系统提示；但 `build_messages()` 每次调用时会读取 recent history）
- Staleness：零（检索时直接读文件当前内容）。但由于 Dream 是 cron 调度的（默认 2h），新对话事实最快 2h 后才写入 `MEMORY.md`。Consolidator 的 `archive()` 写入 `history.jsonl` 后，如果未到达 Dream 调度点，recent history 段落会临时桥接这个 gap（`context.py:56-61`）
- 检索不在 LLM 调用的关键路径上：纯文件读取，微秒级，在 API 调用前完成
- 上下文窗口开销固定：`MEMORY.md` 全文进入 system prompt，无额外 tool call overhead。不随对话轮数增长（Dream 负责保持 `MEMORY.md` 精简）
- 可靠性不依赖 LLM 遵循指令：检索是系统行为，LLM 无法"忘记"读取记忆——记忆就在 system prompt 中
- Dream 写入的 staleness 窗口：最长 2h（取决于 cron interval 配置），可配置缩短但会增加 LLM 调用开销

## 跨仓库对比

### 记忆检索

| 维度 | openclaw | hermes | nanobot |
|------|----------|--------|---------|
| 检索模型 | 工具驱动按需检索（LLM 自主触发） | 后台异步预取（系统自动触发） | 同步文件注入（系统提示构建时读 MEMORY.md） |
| 检索触发者 | LLM（决定何时调用 memory_search 工具） | 系统（每轮结束后 queue_prefetch） | 系统（每次 build_system_prompt() 时自动读取） |
| 检索距 LLM 调用的时间 | 零（工具调用时实时执行，在关键路径上） | 固定 1 turn staleness（预取在关键路径外） | 零（系统提示构建时读取，在 API 调用前完成） |
| 阻塞 LLM token generation | 阻塞（tool call 需等待搜索完成） | 不阻塞（prefetch 只消费缓存，检索在后台完成） | 不阻塞（纯文件 I/O，微秒级，非 LLM 检索路径） |
| 检索结果时效性 | 即时（实时搜索，索引通过文件监听保持同步） | Turn 级动态但滞后 1 轮 | 即时（直接读文件当前内容） |
| LLM 是否感知检索 | 是（LLM 明确调用工具，结果进入上下文窗口） | 否（透明注入 user message，对 LLM 不可见检索动作） | 否（记忆作为系统提示的一部分注入，LLM 感知到记忆文本但感知不到检索动作） |
| 多轮 tool call 期间的策略 | LLM 每轮自主决定是否再次搜索 | 缓存复用：同一轮多次 tool call 不重复 prefetch | 无需决策：系统提示构建时读取一次（同一轮不重复构建） |
| 首轮行为 | LLM 自主决定是否搜索（无冷启动问题） | 特殊处理：同步查询 + 超时退避（默认 8s），后续异步 | 无冷启动问题：MEMORY.md 总是存在（至少为空文件） |
| 上下文窗口开销 | 每次搜索消耗 token（tool call + 结果） | 每次注入消耗 token（`<memory-context>` 标签内容），但不在 tool-use 路径上 | 固定（MEMORY.md 全文进入 system prompt，无额外 tool call 开销） |
| 外部 provider 的延迟容忍 | 检索在关键路径，受 provider 延迟直接影响 | 超时保护：prefetch 线程 join 有 3s timeout，sync 线程 5s timeout | 无外部 provider 依赖（纯本地文件读取） |
| 记忆检索失败后果 | LLM 收到空结果/错误并可见处理（显式失败） | 记忆段落为空（provider 异常被 catch，LLM 无感知） | 静默降级：MEMORY.md 为空时记忆段落空白，LLM 无感知 |
| 资源开销 | 仅当 LLM 决定搜索时产生（按需） | 每轮皆有（但 cadence 门控限制昂贵操作频率） | 极低（一次文件读取，无网络、无 embedding、无向量检索） |
| 扩展机制 | promptBuilder（独占）+ promptSupplement（非独占）+ before_prompt_build hook（通用） | MemoryProvider 插件系统（prefetch/queue_prefetch 接口） | ContextBuilder 固定管道（无记忆专用扩展通道；bootstrap 文件 + skills 可间接注入内容） |

### 记忆压缩（写入）时机

此维度关注记忆写入发生在对话生命周期的哪个阶段、是否阻塞主流程、压缩失败如何降级。

| 维度 | openclaw | hermes | nanobot |
|------|----------|--------|---------|
| 压缩触发模型 | 无独立压缩管线（LLM 通过 tool call 直接写入记忆文件） | 无独立压缩管线（honcho provider 外部管理；agent 端只做 sync_turn 全量消息持久化） | 双层管线：Consolidator（token-budget 触发）+ Dream（cron 调度） |
| 压缩执行者 | LLM（作为工具使用的一部分自主决定写入时机和内容） | Honcho 外部服务（agent 侧只负责 `sync_turn()` 持久化对话消息） | Consolidator: LLM summarization → `history.jsonl`; Dream: AgentRunner with `edit_file` → `MEMORY.md`/`SOUL.md`/`USER.md` |
| 与主对话的时序关系 | 在关键路径上（tool call 内同步执行——写入完成前 LLM 不继续推理） | 在关键路径上（`sync_turn()` 在 turn 结束时同步执行，写入完成前不返回控制流） | 混合：pre-turn 同步 `await`（仅超限时触发 LLM 调用）+ post-turn 异步 `create_task`（不阻塞 turn 完成）+ Dream cron 完全离带 |
| 压缩失败对主对话的影响 | 阻塞该轮 tool call（LLM 收到工具错误，需自行处理） | 阻塞 turn 结束（sync 异常导致该轮消息未持久化，可能丢失对话记录） | 不阻塞：Consolidator 的 `archive()` 失败走 `raw_archive()` 降级（原样写入，无 LLM 摘要）；Dream 完全离带，失败不影响对话 |
| 压缩产物 | `MEMORY.md` / `memory/*.md` 文件 | Honcho 服务端持久化消息 + dialectic 摘要 | Consolidator → `history.jsonl`；Dream → `MEMORY.md` / `SOUL.md` / `USER.md` |
| 写入粒度 | 由 LLM 自主决定（单行增删到全文重写均可） | 全量消息持久化（每轮 `sync_turn` 完整保存对话消息） | Consolidator: batch 级摘要（按 user-turn 边界截断归档）；Dream: 原子事实级增删（`[FILE]` / `[FILE-REMOVE]` 标记驱动） |
| 版本控制 | 无内建版本控制 | 无内建版本控制 | GitStore 自动 commit（Dream 执行后有变更时） |
| 调度策略 | 无调度（LLM 自主决定何时写入） | 每轮必然执行（`sync_turn` 在 turn 结束时必调） | Consolidator: token-budget 门控（仅当 prompt tokens 超安全预算时触发）；Dream: cron 每 2h（`DreamConfig.interval_h` 可配置） |
| 并发保护 | 无（单 tool call 串行执行） | `_prefetch_lock` + `_base_context_lock`（线程级锁） | session 级 `asyncio.Lock`（`memory.py:376-378`）——同 session 多次 consolidation 串行化 |

## 设计权衡

### openclaw 的选择

**优势**：
- 零 staleness：索引通过文件监听和定时同步保持最新，每次 memory_search 执行实时检索。LLM 总是拿到此刻的最新信息
- LLM 拥有检索决策权：LLM 根据当前对话上下文自主判断是否需要搜索、搜索什么、何时搜索。不需要系统预测 LLM 的信息需求——LLM 自己最清楚需要什么
- 简单性：不引入后台线程协调、锁管理、超时处理等复杂性问题。检索是一个普通的同步工具调用
- 扩展性：插件系统提供三层扩展（独占 promptBuilder、补充 promptSupplements、通用 before_prompt_build hook），外部插件可以自定义记忆提示文本或注入额外上下文

**劣势**：
- 上下文窗口开销：每次 memory_search 调用需要消耗 tool call token + 搜索结果 token。在长对话中，频繁的记忆搜索可能加速上下文膨胀
- 可靠性依赖 LLM 的指令遵循：系统提示中的静态文本指引 LLM 调用 memory_search，但 LLM 可能在某些场景下忘记调用。没有系统级保证记忆一定会被检索
- 关键路径延迟：memory_search 的执行时间（向量搜索 + 结果读取）直接增加该轮 tool-call 往返的延迟

### hermes 的选择

**优势**：
- Staleness 可控且可量化：恰好 1 个 turn。用户可以预期"我刚说的偏好会在下一轮被记住"
- Cadence 门控降低资源开销：`dialectic_cadence = 3` 将最昂贵的 LLM 推理检索限制为每 3 轮一次，避免每轮产生多次额外 LLM 调用
- 分层缓存策略：base context（轻量、高频）和 dialectic supplement（重量、低频）分开管理，各自独立 cadence
- 对 LLM 透明：LLM 不需要感知记忆系统存在——不需要额外推理"我是否应该搜索记忆"，也不需要消耗 context window 进行 tool call

**劣势**：
- 线程管理复杂度：daemon 线程的 join timeout、锁竞争、残留线程堆积等场景需要仔细处理。sync 线程在启动新线程前必须 join 旧线程（timeout 5s），否则可能堆积未完成的网络请求
- 首轮冷启动问题：首轮没有上一轮的 `queue_prefetch` 结果可用（线程尚未创建），必须走同步路径，引入了首轮延迟（默认 8s 超时，对慢网络可能显著）。更深层的问题是：首轮同步查询的超时退避意味着 user 的第一个问题可能得不到任何记忆上下文
- 缓存失效不精确：`pop_context_result()` 检查是否有更新的 base context，但 dialectic 结果的 fresh/stale 判断由调用方负责，缺乏显式的陈旧标记

### nanobot 的选择

**优势**：
- 检索零延迟：纯文件 I/O 读取，微秒级完成，无网络调用、无 embedding 计算、无向量检索。检索开销在所有方案中最低
- 系统可靠性保证：记忆检索是系统行为而非 LLM 决策——`MEMORY.md` 总是在 system prompt 中，LLM 无法"忘记"读取记忆。消除了 openclaw 的"LLM 可能不调用工具"的可靠性风险
- 写入完全不影响可用性：Consolidator 的 post-turn 路径通过 `asyncio.create_task()` 异步执行，Dream 完全由 cron 独立调度。两者都不阻塞主对话——即使压缩失败，降级路径（`raw_archive()`）也保证数据不丢失
- 原子事实级写入粒度：Dream 的两阶段设计将分析（Phase 1 LLM 推理）和执行（Phase 2 AgentRunner + edit_file）分离，实现了精确的增量编辑而非全文重写。`[FILE]` / `[FILE-REMOVE]` 标记驱动的方式使每次写入的变更可追溯
- Git 版本控制：`GitStore.auto_commit()` 为每次 Dream 变更提供可追溯的审计记录——回滚、diff、时间线查询的开箱支持
- 双层压缩的灵活性：Consolidator 处理即时需求（token 超限时快速归档），Dream 处理深度需求（cron 批量分析提取洞察）。两者互补，不会在对话高峰期触发昂贵分析

**劣势**：
- 记忆写入的 staleness 窗口大：Dream 默认 2h 调度间隔意味着新对话事实最多 2h 后才写入 `MEMORY.md`。虽然 recent history 段落（`context.py:56-61`）临时桥接了最近 50 条未处理条目，但这些条目是原始对话文本而非结构化事实——LLM 需要在推理中自己整理
- 检索无语义理解：纯文件读取意味着检索精度完全依赖 `MEMORY.md` 的组织质量。没有 embedding/向量搜索，LLM 总是看到 `MEMORY.md` 全文——当文件变大时，相关信息和无关信息都在 context 中，没有检索过滤
- 系统提示膨胀风险：`MEMORY.md` 全文进入 system prompt。如果 Dream 未有效精简（例如 Phase 2 失败而 cursor 仍前进导致 stale 数据堆积），system prompt 将随文档增长而膨胀，压缩可用 context 空间
- 无记忆专用扩展通道：ContextBuilder 的管道是固定的——没有 openclaw 式的插件 promptBuilder 机制，也没有 hermes 式的 MemoryProvider 插件系统。外部扩展只能通过 bootstrap 文件或 skills 间接注入内容
- 写入检索完全解耦的双刃剑：Consolidator 写入 `history.jsonl`、Dream 消费 `history.jsonl` 写入 `MEMORY.md`、ContextBuilder 读取 `MEMORY.md`——三个环节的时间差构成了从"事实发生"到"记忆可用"的端到端延迟（最长 2h + Dream 执行时间），无法通过临时加速某个环节来缩短

### 三种模型的核心差异

openclaw、hermes 和 nanobot 不是同一种"检索时机"问题的三个答案——它们解决了不同的问题：

- openclaw 将记忆检索建模为**LLM 的工具使用能力**的一部分。LLM 像使用 bash、read、web_search 一样使用 memory_search。记忆是一个可查询的数据源，LLM 拥有完整的检索决策权。
- hermes 将记忆检索建模为**系统的上下文增强能力**。系统在后台持续维护对 LLM 有帮助的记忆上下文，并将其透明地注入对话。LLM 不需要任何记忆感知即可受益。
- nanobot 将记忆检索建模为**文件系统的静态投影**。记忆检索就是读文件，不需要查询、不需要索引、不需要 LLM 推理。压缩和检索彻底解耦，各自在独立调度维度上运行（Consolidator 管即时 token budget、Dream 管深度分析、ContextBuilder 管注入）。

这引出了两个更深层的设计问题：

1. **记忆检索应该有 LLM 参与还是对 LLM 透明？** openclaw 选择了参与（LLM 拥有检索决策权），hermes 和 nanobot 选择了透明（系统负责注入，LLM 被动接收）——但透明的实现路径截然不同：hermes 用后台预取 + 缓存结果，nanobot 用同步文件读取。

2. **记忆写入应该不影响对话可用性到什么程度？** 三个方案对此给出了不同的优先级排序：openclaw 将写入与工具调用合并（简单但阻塞），hermes 将写入放在 turn 结束的关键路径上（可靠但可能延迟 turn 完成），nanobot 将写入完全推到离带和异步路径上（最大可用性但引入 staleness gap）。

## 溯源

- [[openclaw-memory-system]] — Memory 系统的 Entity 页
- [[hermes-memory-manager]] — MemoryManager + MemoryProvider 的 Entity 页
- [[nanobot-memory-system]] — nanobot MemoryStore + Consolidator + Dream 的 Entity 页
- [[nanobot-context-builder]] — ContextBuilder（系统提示组装 + 记忆注入点）的 Entity 页
- [[nanobot-agent-loop]] — AgentLoop（Consolidator 调度点 + `_schedule_background`）的 Entity 页
- `src/plugins/memory-state.ts:127-132` (openclaw) — `MemoryPluginCapability` 类型定义（promptBuilder / flushPlanResolver / runtime / publicArtifacts）
- `src/plugins/memory-state.ts:170-175` (openclaw) — `registerMemoryCapability()` 独占槽位注册
- `src/plugins/memory-state.ts:195-204` (openclaw) — `registerMemoryPromptSupplement()` 非独占补充通道
- `src/plugins/memory-state.ts:206-219` (openclaw) — `buildMemoryPromptSection()` 聚合 promptBuilder + supplements
- `src/agents/system-prompt.ts:169-182` (openclaw) — `buildMemorySection()` 调用 buildMemoryPromptSection 生成系统提示记忆段落
- `extensions/memory-core/src/prompt-section.ts:3-38` (openclaw) — 默认 promptBuilder 实现，生成 `## Memory Recall` 工具使用指引文本
- `extensions/memory-core/src/tools.ts:177-311` (openclaw) — `createMemorySearchTool()` 实现，LLM 调用时执行混合向量+关键词检索
- `extensions/memory-core/src/tools.ts:313-394` (openclaw) — `createMemoryGetTool()` 实现，按路径读取记忆文件片段
- `extensions/memory-core/index.ts:33-58` (openclaw) — memory-core 扩展注册 promptBuilder + memory_search/memory_get 工具
- `src/agents/memory-search.ts` (openclaw) — `resolveMemorySearchConfig()` 解析向量/混合检索配置（hybrid、MMR、temporal decay 等）
- `src/plugins/hook-before-agent-start.types.ts:15-34` (openclaw) — `PluginHookBeforePromptBuildResult` 类型定义（4 字段：systemPrompt / prependContext / prependSystemContext / appendSystemContext）
- `src/agents/pi-embedded-runner/run/attempt.ts:1623-1660` (openclaw) — `before_prompt_build` hook 在每次 LLM 调用前执行
- `agent/memory_provider.py:92-112` (hermes) — `prefetch()` / `queue_prefetch()` 接口定义
- `agent/memory_manager.py:178-206` (hermes) — `prefetch_all()` / `queue_prefetch_all()` 编排逻辑
- `run_agent.py:8479-8490` (hermes) — API 调用前收集缓存记忆结果
- `run_agent.py:8561-8577` (hermes) — 记忆注入到 user message 的注入点
- `run_agent.py:11236-11239` (hermes) — turn 结束后的 sync + queue prefetch
- `plugins/memory/honcho/__init__.py:631-677` (hermes) — Honcho provider 的后台线程调度实现
- `nanobot/agent/context.py:30-63` (nanobot) — `ContextBuilder.build_system_prompt()` 记忆注入管道（get_memory_context + read_unprocessed_history）
- `nanobot/agent/memory.py:217-219` (nanobot) — `MemoryStore.get_memory_context()` 同步读取 MEMORY.md
- `nanobot/agent/memory.py:246-248` (nanobot) — `MemoryStore.read_unprocessed_history()` 读取 Dream 未处理的 history.jsonl 条目
- `nanobot/agent/memory.py:304-310` (nanobot) — `MemoryStore.get_last_dream_cursor()` cursor 追踪
- `nanobot/agent/memory.py:346-374` (nanobot) — `Consolidator.__init__()` 构造器（接收 provider + 参数）
- `nanobot/agent/memory.py:376-378` (nanobot) — `Consolidator.get_lock()` session 级 asyncio.Lock 并发保护
- `nanobot/agent/memory.py:380-400` (nanobot) — `Consolidator.pick_consolidation_boundary()` user-turn 边界选择
- `nanobot/agent/memory.py:419-449` (nanobot) — `Consolidator.archive()` LLM 摘要 + 写入 history.jsonl（失败时 raw_archive 降级）
- `nanobot/agent/memory.py:451-512` (nanobot) — `Consolidator.maybe_consolidate_by_tokens()` token-budget 循环压缩主逻辑
- `nanobot/agent/memory.py:519-542` (nanobot) — `Dream.__init__()` 两阶段处理器构造器
- `nanobot/agent/memory.py:559-675` (nanobot) — `Dream.run()` 两阶段流程：Phase 1 plain LLM 分析 + Phase 2 AgentRunner 执行
- `nanobot/agent/memory.py:652-654` (nanobot) — cursor 前进（Phase 2 失败时仍前进，防止 Phase 1 重复执行）
- `nanobot/agent/memory.py:669-673` (nanobot) — GitStore.auto_commit() Dream 变更自动提交
- `nanobot/agent/loop.py:210-218` (nanobot) — Consolidator 初始化（与主循环共享 provider 实例）
- `nanobot/agent/loop.py:220-224` (nanobot) — Dream 初始化
- `nanobot/agent/loop.py:470-474` (nanobot) — `AgentLoop._schedule_background()` asyncio.create_task() 调度点
- `nanobot/agent/loop.py:533` (nanobot) — pre-turn 同步 consolidation（`await consolidator.maybe_consolidate_by_tokens`）
- `nanobot/agent/loop.py:572` (nanobot) — post-turn 异步 consolidation（`_schedule_background(consolidator.maybe_consolidate_by_tokens)`）
- `nanobot/config/schema.py:34-52` (nanobot) — `DreamConfig` cron 调度配置（默认 every 2h）
- `nanobot/command/builtin.py:109-132` (nanobot) — `/dream` 命令手动触发 Dream
- `nanobot/templates/agent/dream_phase1.md` (nanobot) — Phase 1 模板：对比历史 vs 记忆文件，输出 `[FILE]` / `[FILE-REMOVE]`
- `nanobot/templates/agent/dream_phase2.md` (nanobot) — Phase 2 模板：AgentRunner 编辑指引

## 维度

Architecture / Performance Tradeoffs

## 源码验证检查清单

- [x] openclaw 的记忆检索是工具驱动还是系统提示组装时执行？**工具驱动**。`buildMemorySection()` 生成静态指引文本（告诉 LLM 使用 memory_search/memory_get 工具），LLM 在对话中自主调用这些工具时执行实时检索（`extensions/memory-core/src/tools.ts:177-394`）。不存在"系统提示组装时烘焙搜索结果"的机制。
- [x] hermes 的 `queue_prefetch` 是否是真正的后台异步？**是**。Honcho provider 的 `queue_prefetch()` 启动 `threading.Thread(target=_run, daemon=True)`，将结果写入 `_prefetch_result`（受 `threading.Lock` 保护）。`prefetch()` 在下一轮 join 该线程（timeout 3s）并读取结果。不阻塞 LLM 调用的关键路径。
- [x] Staleness 窗口具体多大？**hermes：恰好 1 个 turn**。Turn N 的 `queue_prefetch` 在 turn N 结束时触发，turn N+1 的 `prefetch` 消费。Turn N 中写入的新事实在 turn N+1 的 API 调用时可用。**openclaw：即时（zero-staleness）**。每次 `memory_search` 调用执行实时检索，索引通过文件监听保持同步。**nanobot 检索：即时**（直接读文件当前内容）；**nanobot 写入：最长 2h**（Dream cron 默认 interval），但 recent history 临时桥接。
- [x] 是否存在首轮冷启动问题？**hermes 存在**。首轮的 `prefetch()` 检测到 `_last_dialectic_turn == -999`（从未运行过 `queue_prefetch`），走同步路径，有超时保护（默认 8s）。超时后放弃首轮 dialectic，首次用户提问可能得不到记忆上下文。**openclaw 不存在**——LLM 在首轮即可自主调用 memory_search 工具，不需要预热。**nanobot 不存在**——`MEMORY.md` 总是存在（至少为空文件），系统提示构建时总是读取。
- [x] nanobot 的 Consolidator 是否使用独立 provider 实例？**否**。Consolidator 初始化时接收的 `provider` 参数与主循环共享同一个实例（`loop.py:210-218`）。隔离来自 `asyncio.create_task()` 异步调度（post-turn 路径）+ session 级 `asyncio.Lock` 并发保护（`memory.py:376-378`），而非独立的 provider 实例。
- [x] nanobot 的 Consolidator post-turn 路径是否真正异步？**是**。`_schedule_background()` 使用 `asyncio.create_task()` 将 `maybe_consolidate_by_tokens()` 作为独立协程调度（`loop.py:470-474`）。不 `await`，不阻塞 turn 完成。但 pre-turn 路径（`loop.py:533`）是同步 `await`——仅在 token 超限时触发 LLM 调用，正常情况快速返回。
- [x] nanobot 的 Dream 两阶段流程是否确实独立于 agent loop？**是**。Dream 由 cron 服务独立调度（`cron/service.py`），或通过 `/dream` 命令手动触发。不经过 `AgentLoop._process_message()` 的 turn 处理流程。Phase 1 失败时整个 run 跳过（return False），Phase 2 失败时 cursor 仍前进（防止 Phase 1 重复）。

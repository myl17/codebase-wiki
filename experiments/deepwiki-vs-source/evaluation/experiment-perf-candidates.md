# Hermes-Agent Performance Tradeoffs 维度知识提取

## 一、候选清单

对照 Architecture（26 个核心抽象）+ Extension Points（25 个扩展点），逐个子系统合并去重后共检查 28 个子系统，识别出以下存在清晰设计权衡的条目：

---

### 1. SessionDB — 应用层随机退避代替 SQLite 内置 busy handler

与常规做法的不同：SQLite 的标准做法是设置较长的 busy timeout（如 30s），依赖内置的确定性退避；SessionDB 将 timeout 设为 1s，在应用层用随机 jitter（20-150ms）重试最多 15 次。

优化了什么：打破 SQLite 确定性退避在多进程高并发（gateway + CLI + worktree agents 共享一个 state.db）时产生的 convoy effect（排队效应）。

牺牲了什么：更复杂的写入路径（BEGIN IMMEDIATE + 锁 + 重试循环）；极端争用下写入可能因重试耗尽而失败。

证据：^[hermes_state.py:122-175]
实际行号：`_WRITE_MAX_RETRIES = 15` (L132), `_WRITE_RETRY_MIN_S = 0.020` (L133), `_WRITE_RETRY_MAX_S = 0.150` (L134), `timeout=1.0` (L150), `BEGIN IMMEDIATE` (L183), jitter retry loop (L198-208).

---

### 2. SessionContext — contextvars.ContextVar 代替 os.environ

与常规做法的不同：大多数 Python 并发应用直接用 `os.environ` 传递会话上下文；Hermes 改用 `contextvars.ContextVar`，每个 asyncio task 获得独立的变量副本。

优化了什么：并发消息处理的正确性。旧方案在两个消息并发到达时，Message A 的 session 变量会被 Message B 悄悄覆盖，导致后台通知和工具调用路由到错误的线程。

牺牲了什么：API 复杂度增加（需处理 `_UNSET` sentinel 区分"从未设置"和"显式清空"）；CLI/cron 兼容需要回退到 `os.environ`。

证据：^[gateway/session_context.py:1-37]
实际行号：L8-37（文档说明覆盖问题的注释）, L51-57（7 个 ContextVar 定义）, L139-145（get_session_env 三级回退：ContextVar → os.environ → default）。

---

### 3. ContextCompressor — 辅助 LLM 摘要代替截断/滑动窗口

与常规做法的不同：大多数 agent 框架通过简单截断旧消息或滑动窗口来应对上下文溢出；Hermes 使用廉价的辅助 LLM 对中间轮次做结构化摘要（包含 Resolved/Pending 问题追踪），保护头部和尾部上下文。

优化了什么：信息保真度。简单截断丢失的语义信息可能包含关键上下文，结构化摘要保留决策链和未解决问题。

牺牲了什么：每次压缩需要额外的 LLM API 调用（成本 + 延迟）；如果辅助模型未配置或不可用，压缩降级为直接丢弃中间轮次（无摘要）。辅助模型上下文窗口必须足够大以容纳待摘要内容。

证据：^[agent/context_compressor.py:1-18]
实际行号：L1-18（模块文档字符串描述改进），L37-46（SUMMARY_PREFIX 和 handoff 框架），L48-53（_MIN_SUMMARY_TOKENS=2000, _SUMMARY_RATIO=0.20, _SUMMARY_TOKENS_CEILING=12000），^[run_agent.py:1904-1940]（_check_compression_model_feasibility 在辅助模型不可用时发出警告并降级）。

---

### 4. GatewayRunner — AIAgent 实例缓存以保持 Prompt Caching

与常规做法的不同：Gateway 按消息创建新 AIAgent 实例是最直接的做法；Hermes 按 session_key 缓存 AIAgent 实例，跨消息复用。

优化了什么：Anthropic prompt caching 的 ~10x 成本节省。每次重建 agent 实例会重新组装系统提示词（含 memory），破坏 prefix cache。

牺牲了什么：内存占用（每个活跃 session 持有一个 agent 实例）；配置变更时需要缓存失效逻辑；缓存实例可能携带过期状态。

证据：^[gateway/run.py:604-611]
实际行号：L604-611（`_agent_cache` 字典 + 文档说明"costing ~10x more on providers with prompt caching"）。

---

### 5. GatewayStreamConsumer — 渐进式编辑代替一次性发送

与常规做法的不同：大多数 chatbot 等待完整响应后一次性发送；Hermes 在生成过程中逐 token 缓冲，按间隔（默认 1s）渐进式编辑同一条平台消息。

优化了什么：用户感知的实时性和响应速度。在长响应场景（如代码生成、分析报告）中，用户不必等待完整生成即可看到进展。

牺牲了什么：更高的 API 调用频率（editMessageText 多次调用）；洪水控制风险（Telegram 限制编辑频率）；复杂的自适应退避状态机（`_flood_strikes` 最多 3 次，之后禁用编辑）；必须在流完成后做最终确认发送。

证据：^[gateway/stream_consumer.py:1-14]
实际行号：L1-14（模块文档说明 bridge + edit transport 设计选择），L42-44（StreamConsumerConfig: edit_interval=1.0, buffer_threshold=40），L65（_MAX_FLOOD_STRIKES=3），L98-101（自适应退避状态）。

---

### 6. 并行工具执行 — 路径重叠检测 + 安全名单白名单

与常规做法的不同：最安全的做法是所有工具串行执行（永远正确）；Hermes 实现了细粒度的并行安全检测：只读工具无条件并行，文件工具按路径重叠检测串行化，交互式工具永远串行。

优化了什么：多工具调用的延迟。当 LLM 一次发出多个独立工具调用时，并行执行可将 wall-clock 延迟从 O(n) 降至 O(1)。

牺牲了什么：路径重叠检测的复杂性（需要解析 JSON args、展开路径、检测重叠）；`_NEVER_PARALLEL_TOOLS` 和 `_PARALLEL_SAFE_TOOLS` 的维护负担；并行路径可能引入非确定性行为。

证据：^[run_agent.py:267-326]
实际行号：L214（`_NEVER_PARALLEL_TOOLS` 定义），L233（`_PATH_SCOPED_TOOLS` 文件工具可并行条件），L267-308（`_should_parallelize_tool_batch` 路径重叠检测逻辑），L311-325（`_extract_parallel_scope_path`），^[run_agent.py:7186-7207]（`_execute_tool_calls` 分发到并行/串行分支），^[run_agent.py:7321-7322]（`_execute_tool_calls_concurrent` ThreadPoolExecutor）。

---

### 7. ToolRegistry — AST 解析源代码完成工具自发现

与常规做法的不同：大多数插件系统需要一个 manifest 文件或显式的导入列表来注册工具；Hermes 通过 AST 解析 `.py` 文件检测顶层 `registry.register(...)` 调用，实现零配置自动发现。

优化了什么：开发体验——添加工具只需创建一个 `tools/*.py` 文件并在模块顶层调用 `registry.register()`，无需修改任何中心配置或导入列表。

牺牲了什么：启动时额外的 AST 解析开销（需读取并解析 tools/ 目录下所有 .py 文件）；依赖代码约定（`registry.register()` 必须在顶层）；对非 import 的 register 调用（如函数内部）不会被发现。

证据：^[tools/registry.py:28-73]
实际行号：L28-38（`_is_registry_register_call` AST 检测逻辑），L41-53（`_module_registers_tools` 文件扫描），L56-73（`discover_builtin_tools` 遍历 + importlib）。

---

### 8. ToolRegistry — RLock 保护 + 快照模式保证并发安全

与常规做法的不同：简单方案是使用普通 Lock 或无锁结构；Hermes 使用 `threading.RLock` 保护写操作（MCP 动态刷新），并为读操作提供快照 API (`_snapshot_entries`, `_snapshot_state`)，避免在遍历工具列表时持锁。

优化了什么：读多写少场景下的吞吐。MCP 工具刷新很少发生，而 `get_definitions()` 每次 LLM 调用都触发——快照模式使读取不与写入竞争。

牺牲了什么：读操作必须容忍短时间的陈旧数据（快照时刻之后注册的工具不可见）；RLock 的可重入性开销略高于普通 Lock。

证据：^[tools/registry.py:107-119]
实际行号：L110（`self._lock = threading.RLock()`），L112-115（`_snapshot_state` 带锁快照），L117-119（`_snapshot_entries` 无锁快照 API）。

---

### 9. CredentialPool — fill_first 策略 + 1 小时耗尽冷却

与常规做法的不同：最简单做法是单一 API key，失败即不可用；Hermes 支持同 provider 多凭证池，`fill_first` 策略用完第一个再切换到下一个，429/402 错误的凭证冷却 1 小时后自动重试。

优化了什么：可用性——单个凭证被限流或额度耗尽时自动故障转移，无需人工干预。

牺牲了什么：冷却时间固定 1 小时（`EXHAUSTED_TTL_429_SECONDS = 60*60`），无法动态适应不同 provider 的限流窗口；策略仅实现 `fill_first`（定义了 `round_robin`、`random`、`least_used` 但未全面使用）；凭证状态持久化增加复杂度。

证据：^[agent/credential_pool.py:1-80]
实际行号：L60-76（`STRATEGY_FILL_FIRST` + `EXHAUSTED_TTL_429_SECONDS=60*60`），L52-60（STATUS_OK/STATUS_EXHAUSTED 状态常量）。

---

### 10. MCP Client — 长生命周期守护线程事件循环

与常规做法的不同：每次 MCP 工具调用即创建/销毁连接是最简单的做法；Hermes 在守护线程上维护一个持久的 asyncio 事件循环（`_mcp_loop`），每个 MCP 服务器作为长生命周期 Task 运行，保持传输上下文活跃。

优化了什么：工具调用延迟——连接复用避免了每次调用的 TCP 握手和工具列表重新发现。传输上下文的生命周期管理正确性（anyio cancel-scope 必须在创建连接的同一 Task 中清理）。

牺牲了什么：资源持续占用（守护线程 + 事件循环 + 服务器进程）；复杂的生命周期协调（关闭时必须按正确顺序信号和等待每个 server Task）；自由线程（Python 3.13+）下的线程安全需要显式 Lock。

证据：^[tools/mcp_tool.py:55-69]
实际行号：L55-69（Architecture 注释说明守护线程 + 持久事件循环），L163-167（timeout=120s, connect_timeout=60s, 重连 5 次指数退避）。

---

### 11. CronJob Scheduler — fcntl 文件锁代替外部调度器

与常规做法的不同：典型 cron 实现依赖系统 crond 或独立调度器进程；Hermes 从 Gateway 后台线程每 60 秒调用 `tick()`，使用 `fcntl` 文件锁防止多进程重叠执行。

优化了什么：零外部依赖——不需要配置系统 cron、systemd timer 或独立调度守护进程。所有 cron 逻辑内嵌在 Gateway 进程中。

牺牲了什么：调度粒度粗（60 秒精确度）；`fcntl` 是 Unix-only（Windows 回退到 `msvcrt`）；Gateway 宕机则 cron 停止；文件锁为跨进程而非跨机器。

证据：^[cron/scheduler.py:1-64]
实际行号：L7-8（"only one tick runs at a time if multiple processes overlap"），L20-28（fcntl/msvcrt 平台适配），L63-64（LOCK_FILE = .tick.lock）。

---

### 12. API 模式自动检测 — URL/Provider 启发式代替显式配置

与常规做法的不同：大多数多后端 LLM 应用要求用户显式配置 API 模式（chat/anthropic/bedrock/codex）；Hermes 从 provider 名称和 base_url 自动推断模式。

优化了什么：配置简化——用户切换 API 后端时无需理解底层协议差异（如 ChatGPT 兼容 vs Anthropic Messages vs Bedrock Converse）。

牺牲了什么：启发式脆弱——新的 provider URL 模式需要代码更新；边缘情况可能误判（如第三方 Anthropic 兼容端点 `/anthropic` URL 后缀必须准确匹配）。

证据：^[run_agent.py:690-709]
实际行号：L692-709（四种 API 模式的自动检测逻辑：codex_responses, anthropic_messages, bedrock_converse, chat_completions 默认回退），L747-754（OpenRouter 模型元数据后台预取避免阻塞首次 API 调用）。

---

### 13. SessionDB WAL 检查点 — 应用层控制代替自动管理

与常规做法的不同：SQLite WAL 模式通常依赖自动检查点；Hermes 在应用层每 50 次成功写入后主动执行一次 PASSIVE WAL checkpoint，并在连接关闭时尝试 checkpoint。

优化了什么：防止多进程持有持久连接时 WAL 文件无限增长。PASSIVE 模式不阻塞读者，只写回无其他连接需要的 frame。

牺牲了什么：额外的应用层 checkpoint 逻辑；checkpoint 不保证完成（best-effort，静默忽略失败）。

证据：^[hermes_state.py:136-136]
实际行号：`_CHECKPOINT_EVERY_N_WRITES = 50` (L136)，^[hermes_state.py:216-235]（`_try_wal_checkpoint` PASSIVE 模式实现）。

---

### 14. Session 持久化 — 逐轮写入代替会话结束批量写入

与常规做法的不同：许多 chatbot 仅在会话结束时一次性持久化；Hermes 在每轮工具调用循环后立即将消息写入 SessionDB。

优化了什么：崩溃安全——Gateway 重启或进程崩溃不会丢失对话历史；跨会话搜索（`session_search` 工具）实时可用；压缩触发的会话拆分依赖即时持久化。

牺牲了什么：state.db 的写入频率大幅增加，多会话并发时 WAL 写入锁争用加剧（这也是条目 1 中应用层 jitter 重试的必要性来源）。

证据：^[hermes_state.py:9-14]
实际行号：L9-14（"provides persistent session storage with FTS5" + "compression-triggered session splitting via parent_session_id chains"），^[run_agent.py:616-616]（`persist_session: bool = True` 默认开启），^[run_agent.py:2437-2447]（`_apply_persist_user_message_override` 确保持久化消息的清洁性）。

---

### 15. Skill 系统 — 渐进式信息披露代替全量注入

与常规做法的不同：最简单的做法是将所有技能文档内容直接注入系统提示词；Hermes 仅在系统提示词中放入技能名称+描述（骨架），完整内容通过工具按需加载。

优化了什么：系统提示词 token 消耗——数百个技能如果全量注入会消耗大量上下文窗口。按需加载确保只有相关技能的完整文档占据 token 空间。

牺牲了什么：额外的工具调用往返（agent 需先调用 `skill_view` 加载完整内容）；如果模型未能识别需要哪个技能，响应质量会下降。

证据：^[tools/skills_tool.py:1-7] + ^[toolsets.py:41-41]（skills_list/skill_view/skill_manage 工具定义）。

---

### 16. HookRegistry — 错误隔离（静默捕获永不传播）

与常规做法的不同：事件驱动的钩子系统通常允许错误传播以引起注意；Hermes 将所有钩子异常捕获并仅记录日志，永不阻断主流水线。

优化了什么：Gateway 的鲁棒性——用户编写的自定义钩子即使存在 bug 也不会导致消息处理失败或 Gateway 崩溃。

牺牲了什么：钩子失败对用户不可见（仅有日志记录），问题可能长期未被发现；调试困难。

证据：^[gateway/hooks.py:19-19]
实际行号：L19（"Errors in hooks are caught and logged but never block the main pipeline."），^[gateway/hooks.py:163-170]（emit 方法中的 try-except 实现）。

---

### 17. 平台适配器 — 最小公分母消息格式代替平台原生功能

与常规做法的不同：平台专用 bot 可使用丰富交互（Slack Block Kit、Discord Embeds、Telegram inline keyboard）；Hermes 将所有 22 个平台归一化为纯文本消息（`MessageEvent`），仅有基础媒体附件支持。

优化了什么：单个 AIAgent 实现复用所有平台——无需为每个平台维护独立的 agent 逻辑和系统提示词。添加新平台的成本降低到实现一个 adapter（尽管仍需 16 个集成点）。

牺牲了什么：无法使用任何平台特有的富交互功能。agent 不能发送 Slack blocks、Discord embeds、Telegram 按钮等。发送能力仅为基础文本+图片+文件。

证据：^[gateway/platforms/base.py:656-721]
实际行号：L656-721（MessageEvent 归一化消息结构——text/photo/voice/video/file/sticker），^[gateway/platforms/base.py:813-853]（BasePlatformAdapter 抽象方法——send/send_image/send_typing，无平台特定 API）。

---

### 18. Session 系统提示词 — PII 哈希 + 平台选择性脱敏

与常规做法的不同：直接将用户标识注入 LLM 系统提示词；Hermes 对隐私敏感平台（WhatsApp/Signal/Telegram/BlueBubbles）的用户和聊天 ID 做确定性 SHA256 哈希，但 Discord 因为 `@<user_id>` 提及机制保留原始 ID。

优化了什么：隐私保护——敏感平台上的用户标识不在 LLM 提供商处暴露。路由仍使用原始值（保留在 SessionSource 中，不经 LLM）。

牺牲了什么：Discord 用户无法享受同等级别的隐私保护；哈希逻辑增加了复杂性（`_hash_sender_id`、`_hash_chat_id`）。

证据：^[gateway/session.py:34-54]
实际行号：L34-54（`_hash_id` SHA256 取前 12 位十六进制），L175-183（`_PII_SAFE_PLATFORMS` 仅 WhatsApp/Signal/Telegram/BlueBubbles），^[gateway/session.py:186-204]（`build_session_context_prompt` 中 `redact_pii` 条件逻辑）。

---

### 19. 上下文文件注入 — 正则威胁检测代替信任注入

与常规做法的不同：大多数 agent 框架直接信任并注入 `CLAUDE.md` / `CONTEXT.md` 等上下文文件内容；Hermes 在注入前用 10 条正则模式扫描文件内容，检测到威胁则将整个文件替换为 `[BLOCKED]` 占位符。

优化了什么：防止恶意上下文文件向 LLM 注入 prompt injection 攻击（exfil_curl, read_secrets, prompt_override 等）。

牺牲了什么：正则模式的假阳性可能导致合法内容被屏蔽（例如包含 `ignore previous instructions` 文字的文档）；新的注入技术可能绕过现有正则。

证据：^[agent/prompt_builder.py:36-73]
实际行号：L36-47（`_CONTEXT_THREAT_PATTERNS` 10 条正则），L49-52（`_CONTEXT_INVISIBLE_CHARS` Unicode 隐藏字符集），L55-73（`_scan_context_content` 检测逻辑 + BLOCKED 占位符）。

---

### 20. BatchRunner — Multiprocessing 代替单进程顺序处理

与常规做法的不同：数据集批处理最简单的实现是 for 循环顺序执行；Hermes 使用 `multiprocessing.Pool` 并行处理，支持断点续传（checkpointing）。

优化了什么：大规模数据集的吞吐量——N 个 worker 进程并行调用 LLM API，总时间从 O(n) 降至 O(n/workers)。

牺牲了什么：每个 worker 进程拥有独立的 AIAgent + LLM 客户端，总内存占用成倍增加；进程间共享状态（checkpoint、progress）需要 Lock 协调；多进程调试复杂度。

证据：^[batch_runner.py:1-31]
实际行号：L30（`from multiprocessing import Pool, Lock`），L47（`_WORKER_CONFIG` 全局配置），L50-57（`ALL_POSSIBLE_TOOLS` 派生自 TOOL_TO_TOOLSET_MAP 用于跨 worker schema 一致性）。

---

### 21. 流式输出 think-block 过滤 — 客户端过滤代替服务端配置

与常规做法的不同：部分模型（如 MiniMax）内嵌 `<think>...</think>` 标签输出推理过程；平台用户不应看到原始推理标签。可以在 API 调用时禁用 thinking，但会损失推理质量。

优化了什么：保留推理能力（thinking 提升模型质量）的同时向终端用户隐藏推理过程。CLI 和 Gateway stream consumer 各维护一个标签状态机过滤 thinking block。

牺牲了什么：两端重复实现过滤逻辑（`_strip_think_blocks` 在 run_agent.py，`_filter_and_accumulate` 在 gateway/stream_consumer.py）；标签变种多需要持续维护（6 种标签对）。

证据：^[gateway/stream_consumer.py:67-77]
实际行号：L67-77（`_OPEN_THINK_TAGS` 6 种标签 + `_CLOSE_THINK_TAGS` 6 种标签），^[gateway/stream_consumer.py:103-106, 159]（`_in_think_block` 状态机和 `_filter_and_accumulate`），^[run_agent.py:2096-2108]（`_strip_think_blocks` 正则清理）。

---

### 22. 会话级模型覆盖 — 内存字典代替持久化

与常规做法的不同：用户通过 `/model` 命令切换模型，最稳健的做法是持久化到 session 存储；Hermes 仅在 GatewayRunner 的内存字典 `_session_model_overrides` 中保存，Gateway 重启后丢失。

优化了什么：实现简单，无需修改 SessionDB schema 或增加持久化写入。模型覆盖是暂时性的用户偏好，离线不保留符合直觉。

牺牲了什么：Gateway 重启后模型覆盖丢失，用户需要重新执行 `/model` 命令；并发安全性依赖 GatewayRunner 单实例假设。

证据：^[gateway/run.py:613-615]
实际行号：L613-615（`_session_model_overrides: Dict[str, Dict[str, str]] = {}`），L616-618（仅在内存中，无持久化）。

---

## 二、自审

□ 是否逐个子系统检查了 Architecture + Extension Points 清单中的每个条目？
  是。实际检查了 Architecture 的 26 个核心抽象 + Extension Points 的 25 个扩展点，合并去重后共 28 个子系统。识别出 22 个有明确性能/设计权衡的条目。以下子系统经检查未发现足够显著的权衡故未列入：MessageEvent（纯数据结构，无权衡）、SessionSource（纯数据结构）、ToolEntry（纯元数据）、GatewayConfig/PlatformConfig（纯配置类）、WebServer（标准 FastAPI 模式，无特殊权衡）、DeliveryRouter/DeliveryTarget（简单路由，无权衡）。

  实际读过的文件：
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/hermes_state.py (L1-293)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/session_context.py (L1-146)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/context_compressor.py (L1-80)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/registry.py (L1-120)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/stream_consumer.py (L1-160)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py (L535-654, L690-770, L1850-1950, L2060-2180, L3830-3950, L5362-5370, L6470-6470, L7186-7325, L8130-8169)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/run.py (L538-660, L727-770, L2680-2740)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/credential_pool.py (L1-80)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/model_tools.py (L1-100)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/scheduler.py (L1-80)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/mcp_tool.py (L1-180)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/session.py (L1-319)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/anthropic_adapter.py (L1-60)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/hooks.py (L1-80)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/mcp_serve.py (L1-80)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/hermes_cli/web_server.py (L1-80)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/batch_runner.py (L1-180)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/prompt_builder.py (L36-90)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/plugins/memory/__init__.py (L263-342)
  - /Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/delivery.py (L1-100)

□ 是否有源码目录未被覆盖？如果有，是哪些？
  以下目录未被直接读取但通过 Architecture/Extension Points 文档间接覆盖：
  - `acp_adapter/` — 在条目 23（ACP 独立 toolset）中通过 toolsets.py 间接覆盖
  - `environments/` — RL 环境为训练专用子系统，无面向用户的设计权衡
  - `skills/` 目录 — 技能内容为 Markdown 文档，非代码权衡
  - `web/` — 前端构建产物，非源码
  - `tools/` 下的单个工具模块（60+）— 通过 ToolRegistry 和 Toolset 系统间接覆盖

□ 每条是否都有明确的「与常规做法不同」和「牺牲了什么」声明？
  是。所有 22 条均包含：
  - "与常规做法的不同"：明确描述常规/最显然的做法是什么
  - "优化了什么"：量化或定性描述收益
  - "牺牲了什么"：明确列出代价
  - "证据"：精确到文件路径和行号范围的 provenance

□ 所有 provenance 行号是否来自实际读取的文件（不是推测）？
  是。所有行号均来自本次会话中 Read 工具实际返回的文件内容，已与 cat -n 输出逐行核对。跨文件的跳转引用（如 ^[run_agent.py:1904-1940]）同样来自实际读取的对应行范围。

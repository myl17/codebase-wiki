# nanobot Structural Entity & Ontology Extraction

从源码直接提取。nanobot 版本 0.1.5，Python >= 3.11。

---

## Part One: Structural Entities

---

### Entity: Agent Runner (Core Execution Engine)

**代码位置**：`nanobot/agent/runner.py`
**这个模块解决什么问题**：执行工具调用 LLM 循环的核心引擎，不包含产品层关注点（会话管理、消息路由）。
**对外暴露什么**：
- `AgentRunner` 类（第 83 行）：接收 `AgentRunSpec`，执行 tool-use loop，返回 `AgentRunResult` ^[nanobot/agent/runner.py:83]
- `AgentRunSpec` dataclass（第 45 行）：单次 agent 执行的配置 ^[nanobot/agent/runner.py:45]
- `AgentRunResult` dataclass（第 70 行）：执行结果 ^[nanobot/agent/runner.py:70]
**它和谁交互**：
- 被 `AgentLoop` 调用（`nanobot/agent/loop.py:185`）
- 被 `SubagentManager` 调用（`nanobot/agent/subagent.py:13`）
- 依赖 `LLMProvider`（第 86 行）
- 依赖 `ToolRegistry`（第 47 行）
- 依赖 `AgentHook`（第 56 行）
**为什么它是可分离的**：独立的模块文件，通过 `AgentRunSpec` 纯数据类配置，不依赖任何产品层（会话、消息总线、通道）。

**关键机制**（源码可见）：
- **多轮工具调用循环**：最多 `max_iterations` 轮，每轮调用 LLM、执行工具、追加结果 ^[nanobot/agent/runner.py:102]
- **空响应退避重试**：`_MAX_EMPTY_RETRIES = 2`，对 blank 文本 retry ^[nanobot/agent/runner.py:34]
- **长度截断恢复**：finish_reason == "length" 时自动追加 continue 消息重试（最多 `_MAX_LENGTH_RECOVERIES = 3` 次）^[nanobot/agent/runner.py:232-251]
- **上下文裁剪（snip）**：基于 token 估算，按 context_window_tokens 预算裁剪历史消息 ^[nanobot/agent/runner.py:640-697]
- **微压缩（microcompact）**：将旧的 compactable 工具结果替换为单行摘要，保留最近 10 个结果 ^[nanobot/agent/runner.py:593-617]
- **orphan tool result 补充**：自动为缺失 tool_call_id 对应结果的 tool call 插入合成错误消息 ^[nanobot/agent/runner.py:552-591]
- **工具并发执行**：`concurrent_tools=True` 时按 `concurrency_safe` 属性分区并行执行 ^[nanobot/agent/runner.py:699-722]

**源码证据**：
- 入口文件：`nanobot/agent/runner.py`
- 核心类型定义：`AgentRunner` class ^[nanobot/agent/runner.py:83], `AgentRunSpec` ^[nanobot/agent/runner.py:45], `AgentRunResult` ^[nanobot/agent/runner.py:70]

---

### Entity: Agent Loop (Product-Layer Orchestrator)

**代码位置**：`nanobot/agent/loop.py`
**这个模块解决什么问题**：在 AgentRunner 之上叠加产品层关注点——消息总线集成、会话管理、内存合并、MCP 连接、流式响应。
**对外暴露什么**：
- `AgentLoop` 类（第 115 行）：核心编排器 ^[nanobot/agent/loop.py:115]
- `_LoopHook` 类（第 46 行）：内部 Hook 实现，连接 loop 和 streaming/进度回调 ^[nanobot/agent/loop.py:46]
**它和谁交互**：
- 持有 `AgentRunner` 实例 ^[nanobot/agent/loop.py:185]
- 持有 `MessageBus` 引用 ^[nanobot/agent/loop.py:131]
- 持有 `SessionManager` ^[nanobot/agent/loop.py:183]
- 持有 `ContextBuilder` ^[nanobot/agent/loop.py:182]
- 持有 `CommandRouter` ^[nanobot/agent/loop.py:226]
- 持有 `SubagentManager` ^[nanobot/agent/loop.py:186]
- 持有 `ToolRegistry` ^[nanobot/agent/loop.py:184]
- 被 `Nanobot` facade 调用 ^[nanobot/nanobot.py:33]
- 被 `cli/commands.py` 的 gateway 命令调用
**为什么它是可分离的**：独立模块，是整个系统的核心编排点，通过构造函数依赖注入所有子组件。

**关键机制**（源码可见）：
- **异步消息派发**：`run()` 方法从 inbound queue 消费消息，为每个消息创建 `asyncio.Task` ^[nanobot/agent/loop.py:363-397]
- **每会话串行锁**：`_session_locks` 确保同 session 的消息串行处理 ^[nanobot/agent/loop.py:402]
- **并发门控**：通过 `_concurrency_gate` semaphore 限制跨 session 的并发 LLM 请求数 ^[nanobot/agent/loop.py:403-404]
- **流式响应**：构建 `on_stream`/`on_stream_end` 回调，将 LLM delta 以 `_stream_delta`/`_stream_end` 元数据标记发送到 outbound bus ^[nanobot/agent/loop.py:407-436]
- **运行时 checkpoint 恢复**：通过 session metadata 持久化 in-flight turn 状态，崩溃重启后能恢复续接 ^[nanobot/agent/loop.py:683-732]
- **MCP 惰性连接**：`_connect_mcp()` 一次性、惰性连接，失败自动重试下一条消息 ^[nanobot/agent/loop.py:256-275]
- **斜杠命令优先级处理**：`is_priority()` 检查在 dispatch lock 之前处理 `/stop`、`/restart` 等 ^[nanobot/agent/loop.py:385-390]
- **统一会话模式**：`unified_session=True` 时所有 channel 共享 `unified:default` session ^[nanobot/agent/loop.py:44]
- **工具上下文传递**：执行前将 channel/chat_id 注入 MessageTool、SpawnTool、CronTool ^[nanobot/agent/loop.py:278-283]

**源码证据**：
- 入口文件：`nanobot/agent/loop.py`
- 核心类型定义：`AgentLoop` ^[nanobot/agent/loop.py:115]

---

### Entity: LLM Provider Interface & Implementations

**代码位置**：`nanobot/providers/`
**这个模块解决什么问题**：抽象不同 LLM 后端的调用接口，统一为 `chat()` / `chat_stream()` + retry 策略。
**对外暴露什么**：
- `LLMProvider` ABC（`nanobot/providers/base.py:80`）：定义 `chat()` abstract method ^[nanobot/providers/base.py:250-275]
- `LLMResponse` dataclass（`base.py:47-63`）：统一响应格式 ^[nanobot/providers/base.py:47]
- `ToolCallRequest` dataclass（`base.py:18-44`）：标准化的工具调用请求 ^[nanobot/providers/base.py:18]
- `GenerationSettings` dataclass（`base.py:71-77`）：默认生成参数 ^[nanobot/providers/base.py:71]
- `ProviderSpec` dataclass（`registry.py:21-65`）：provider 元数据注册 ^[nanobot/providers/registry.py:21]
- `PROVIDERS` tuple（`registry.py:75-361`）：30+ 个 provider 的注册表 ^[nanobot/providers/registry.py:75]
- `AnthropicProvider`（`anthropic_provider.py:24`）：原生 Anthropic SDK 集成 ^[nanobot/providers/anthropic_provider.py:24]
- `OpenAICompatProvider`（`openai_compat_provider.py`）：OpenAI 兼容 API 通用实现
- `AzureOpenAIProvider`（`azure_openai_provider.py`）：Azure OpenAI 直接 API
- `OpenAICodexProvider`（`openai_codex_provider.py`）：OAuth-based Codex
- `GitHubCopilotProvider`（`github_copilot_provider.py`）：OAuth-based Copilot
**它和谁交互**：
- 被 `AgentRunner` 持有和调用 ^[nanobot/agent/runner.py:86]
- 被 `Nanobot._make_provider()` 根据 config 实例化 ^[nanobot/nanobot.py:117-177]
- 被 `HeartbeatService` 调用 ^[nanobot/heartbeat/service.py:56]
**为什么它是可分离的**：独立目录 + `ABC` 接口 + 5 个具体实现 + 注册表机制 + 配置可切换。

**关键机制**（源码可见）：
- **Retry 策略**：`_run_with_retry()` 实现标准重试（1s/2s/4s 退避）和 persistent 模式（持续重试直到相同错误超过 10 次）^[nanobot/providers/base.py:629-698]
- **429 分类处理**：`_is_retryable_429_response()` 区分 billing 配额 429（不可重试）和 rate limit 429（可重试）^[nanobot/providers/base.py:334-354]
- **重试间隔解析**：`_extract_retry_after()` 从文本内容中解析 retry-after 秒数 ^[nanobot/providers/base.py:532-548]
- **Header 重试解析**：`_extract_retry_after_from_headers()` 支持 `retry-after-ms` 和 `retry-after` HTTP 头 ^[nanobot/providers/base.py:559-599]
- **Provider 匹配**：`Config._match_provider()` 按前缀优先 > 关键词匹配 > 本地 fallback > gateway fallback > 泛 fallback 的优先级 ^[nanobot/config/schema.py:218-281]
- **Role alternation 强制**：`_enforce_role_alternation()` 合并连续同角色消息、删除尾部 assistant 消息 ^[nanobot/providers/base.py:356-390]
- **空内容清理**：`_sanitize_empty_content()` 处理空字符串 content 和 `_meta` 字段 ^[nanobot/providers/base.py:155-202]
- **Streaming fallback**：`chat_stream()` 默认实现 fallback 到非流式调用，子类可覆盖 ^[nanobot/providers/base.py:423-448]
- **Prompt caching marker**：`_tool_cache_marker_indices()` 标记 builtin/MCP 边界供 Anthropic cache_control 使用 ^[nanobot/providers/base.py:217-234]

**源码证据**：
- 入口文件：`nanobot/providers/base.py`
- Provider 注册表：`nanobot/providers/registry.py`
- 具体实现：`anthropic_provider.py`, `openai_compat_provider.py`, `azure_openai_provider.py`, `openai_codex_provider.py`, `github_copilot_provider.py`

---

### Entity: Chat Channel Interface & Implementations

**代码位置**：`nanobot/channels/`
**这个模块解决什么问题**：抽象不同聊天平台的集成，统一为 `start()` / `stop()` / `send()` / `send_delta()` 接口。
**对外暴露什么**：
- `BaseChannel` ABC（`nanobot/channels/base.py:15`）：定义 `start()` ^[base.py:68], `stop()` ^[base.py:80], `send()` ^[base.py:85], `send_delta()` ^[base.py:98]
- `ChannelManager`（`manager.py:20`）：管理所有 channel 的启停、消息路由、retry ^[nanobot/channels/manager.py:20]
- `discover_all()`（`registry.py:54`）：pkgutil 扫描 + entry_points 发现所有 channel ^[nanobot/channels/registry.py:54]
- 13 个具体 channel 实现：`telegram.py`, `discord.py`, `whatsapp.py`, `weixin.py`, `feishu.py`, `dingtalk.py`, `slack.py`, `matrix.py`, `email.py`, `qq.py`, `wecom.py`, `mochat.py`
**它和谁交互**：
- 被 `ChannelManager` 管理
- 通过 `MessageBus` 与 `AgentLoop` 解耦通信
- `BaseChannel._handle_message()` 将入站消息发布到 bus ^[nanobot/channels/base.py:127-171]
**为什么它是可分离的**：独立目录 + ABC 接口 + 13 个具体实现 + 注册表 auto-discovery + entry_points 插件 + 配置可启用/禁用。

**关键机制**（源码可见）：
- **pkgutil 自动发现**：`discover_channel_names()` 扫描 `nanobot.channels` 包，自动发现 built-in channel ^[nanobot/channels/registry.py:17-25]
- **entry_points 插件发现**：`discover_plugins()` 通过 `nanobot.channels` 组加载外部插件 ^[nanobot/channels/registry.py:40-51]
- **流式支持检测**：`supports_streaming` 属性检查 config 中 `streaming: true` 且子类覆盖了 `send_delta` ^[nanobot/channels/base.py:110-115]
- **发送重试**：`ChannelManager._send_with_retry()` 指数退避重试（1s/2s/4s）^[nanobot/channels/manager.py:248-276]
- **流式 delta 合并**：`_coalesce_stream_deltas()` 对同一 stream 的连续 delta 合并，减少 API 调用 ^[nanobot/channels/manager.py:198-246]
- **权限控制**：`is_allowed()` 检查 sender_id 是否在 allowFrom 列表中，空列表拒绝所有 ^[nanobot/channels/base.py:117-125]
- **语音转录**：`transcribe_audio()` 支持 OpenAI Whisper 和 Groq 转录 ^[nanobot/channels/base.py:40-54]
- **进度消息过滤**：`_dispatch_outbound()` 根据 `send_progress`/`send_tool_hints` 配置过滤进度消息 ^[nanobot/channels/manager.py:167-171]
- **重启通知**：`_notify_restart_done_if_needed()` 当通过 `/restart` 重启后自动通知 channel ^[nanobot/channels/manager.py:111-126]

**源码证据**：
- 入口文件：`nanobot/channels/base.py`
- 注册发现：`nanobot/channels/registry.py`
- 管理器：`nanobot/channels/manager.py`

---

### Entity: Agent Tool System & Registry

**代码位置**：`nanobot/agent/tools/`
**这个模块解决什么问题**：定义 agent 可使用的工具能力，提供 JSON Schema 驱动的参数验证、类型转换、注册管理。
**对外暴露什么**：
- `Tool` ABC（`nanobot/agent/tools/base.py:117`）：定义 `name`, `description`, `parameters`, `execute()` ^[nanobot/agent/tools/base.py:137-172]
- `Schema` ABC（`base.py:21`）：JSON Schema 片段抽象 ^[nanobot/agent/tools/base.py:21]
- `ToolRegistry`（`registry.py:8`）：注册/注销/查找/执行工具 ^[nanobot/agent/tools/registry.py:8]
- `tool_parameters` 装饰器（`base.py:246`）：声明式参数 schema 定义 ^[nanobot/agent/tools/base.py:246]
- 10+ 内置工具：
  - `filesystem.py`：ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
  - `search.py`：GlobTool, GrepTool
  - `shell.py`：ExecTool
  - `web.py`：WebSearchTool, WebFetchTool
  - `message.py`：MessageTool
  - `spawn.py`：SpawnTool
  - `cron.py`：CronTool
  - `mcp.py`：MCP 动态工具
**它和谁交互**：
- 被 `AgentLoop._register_default_tools()` 注册 ^[nanobot/agent/loop.py:229-254]
- 被 `AgentRunner` 用于执行工具调用 ^[nanobot/agent/runner.py:85]
- MCP 工具通过 `connect_mcp_servers()` 动态注册 ^[nanobot/agent/tools/mcp.py]
**为什么它是可分离的**：独立目录 + Tool ABC + 10+ 实现 + ToolRegistry 注册机制 + MCP 动态加载。

**关键机制**（源码可见）：
- **Schema 驱动类型转换**：`Tool.cast_params()` 按 JSON Schema type 进行安全类型转换（字符串到整数/布尔等）^[nanobot/agent/tools/base.py:180-223]
- **Schema 验证**：`Schema.validate_json_schema_value()` 递归验证 JSON Schema，支持 nested object/array/enum/min/max ^[nanobot/agent/tools/base.py:41-94]
- **Tool schema 稳定性排序**：`ToolRegistry.get_definitions()` 将 built-in 和 MCP 工具分别排序后拼接，确保 prompt cache 稳定 ^[nanobot/agent/tools/registry.py:45-63]
- **prepare_call 钩子**：`prepare_call()` 在 execute 之前进行解析、转换、验证三部曲 ^[nanobot/agent/tools/registry.py:65-83]
- **并发安全标记**：`Tool.read_only`, `Tool.concurrency_safe`, `Tool.exclusive` 属性控制并行执行策略 ^[nanobot/agent/tools/base.py:154-167]
- **MCP 工具包装**：`_normalize_schema_for_openai()` 将 MCP nullable union 格式转换为 OpenAI-compatible ^[nanobot/agent/tools/mcp.py:34]
- **工具结果大小截断**：`max_tool_result_chars` 限制工具结果字符串长度 ^[nanobot/agent/tools/registry.py:83]
- **重复外部查找阻止**：`repeated_external_lookup_error()` 检测重复的 web_search/web_fetch 调用并阻止 ^[nanobot/agent/runner.py:435-449]

**源码证据**：
- 入口文件：`nanobot/agent/tools/base.py`
- 注册中心：`nanobot/agent/tools/registry.py`
- 具体工具：`filesystem.py`, `search.py`, `shell.py`, `web.py`, `message.py`, `spawn.py`, `cron.py`, `mcp.py`, `sandbox.py`

---

### Entity: Message Bus

**代码位置**：`nanobot/bus/`
**这个模块解决什么问题**：提供异步消息队列，解耦 channel 和 agent core 的通信。
**对外暴露什么**：
- `MessageBus`（`queue.py:8`）：`publish_inbound()` / `consume_inbound()` / `publish_outbound()` / `consume_outbound()` ^[nanobot/bus/queue.py:20-33]
- `InboundMessage` dataclass（`events.py:8`）：入站消息结构 ^[nanobot/bus/events.py:8]
- `OutboundMessage` dataclass（`events.py:27`）：出站消息结构 ^[nanobot/bus/events.py:27]
**它和谁交互**：
- Channel 推送入站消息
- AgentLoop 消费入站消息、发布出站消息
- ChannelManager 消费出站消息
**为什么它是可分离的**：独立目录 + 独立数据结构 + 完全通过队列解耦，不依赖任何其他模块。

**关键机制**（源码可见）：
- **双队列解耦**：使用 `asyncio.Queue` 作为 inbound/outbound 双向通道 ^[nanobot/bus/queue.py:17-18]
- **Session key 推导**：`InboundMessage.session_key` 默认按 `channel:chat_id` 格式生成 ^[nanobot/bus/events.py:21-24]
- **流式元数据标记**：通过 `metadata` dict 中的 `_stream_delta`, `_stream_end`, `_progress` 等标记实现流式传输 ^[nanobot/bus/events.py:18]
- **Session key override**：支持 `session_key_override` 用于 thread-scoped 会话 ^[nanobot/bus/events.py:19]

**源码证据**：
- 入口文件：`nanobot/bus/queue.py`
- 事件类型：`nanobot/bus/events.py`

---

### Entity: Configuration System

**代码位置**：`nanobot/config/`
**这个模块解决什么问题**：定义和加载所有配置项，支持 JSON 文件 + 环境变量覆盖。
**对外暴露什么**：
- `Config` pydantic `BaseSettings`（`schema.py:203`）：根配置类，支持 `NANOBOT_` 前缀环境变量 ^[nanobot/config/schema.py:203]
- `AgentsConfig`/`AgentDefaults`：agent 行为配置 ^[nanobot/config/schema.py:62-87]
- `ProvidersConfig`：LLM provider 配置 ^[nanobot/config/schema.py:97-126]
- `ChannelsConfig`：channel 配置（extra="allow" 允许任意 channel 字段）^[nanobot/config/schema.py:18-31]
- `ToolsConfig`/`WebToolsConfig`/`ExecToolConfig`/`MCPServerConfig`：工具配置 ^[nanobot/config/schema.py:153-201]
- `DreamConfig`：memory consolidation 配置 ^[nanobot/config/schema.py:34-59]
- `GatewayConfig`/`ApiConfig`/`HeartbeatConfig`：服务配置 ^[nanobot/config/schema.py:127-151]
- `load_config()`/`resolve_config_env_vars()`（`loader.py`）：加载和环境变量替换
- `get_workspace_path()`/`get_media_dir()`（`paths.py`）：路径工具
**它和谁交互**：被所有模块通过 Config 实例引用。
**为什么它是可分离的**：独立目录 + Pydantic schema + 环境变量映射 + 所有模块通过依赖注入获取 config。

**关键机制**（源码可见）：
- **camelCase alias**：`Base.model_config = ConfigDict(alias_generator=to_camel)` 自动支持 camelCase 和 snake_case 键 ^[nanobot/config/schema.py:16]
- **环境变量嵌套分隔符**：`NANOBOT__` 前缀 + `__` 双下划线嵌套分隔符 ^[nanobot/config/schema.py:313]
- **Provider 自动匹配**：`Config._match_provider()` 按 5 级优先级自动匹配 provider ^[nanobot/config/schema.py:218-281]
- **Provider fallback chain**：provider 前缀 > keyword 匹配 > local 匹配 > gateway fallback > 泛 fallback ^[nanobot/config/schema.py:240-281]
- **API base 解析**：gateway/local provider 有默认 base URL 回退 ^[nanobot/config/schema.py:298-311]
- **Dream cron 兼容**：`DreamConfig.build_schedule()` 支持 legacy cron 字符串和新的 interval 模式 ^[nanobot/config/schema.py:48-52]

**源码证据**：
- 入口文件：`nanobot/config/schema.py`
- 加载器：`nanobot/config/loader.py`
- 路径工具：`nanobot/config/paths.py`

---

### Entity: Session Management

**代码位置**：`nanobot/session/`
**这个模块解决什么问题**：持久化和管理对话会话，以 JSONL 格式存储，支持内存缓存和迁移。
**对外暴露什么**：
- `Session` dataclass（`manager.py:17`）：单个对话会话 ^[nanobot/session/manager.py:17]
- `SessionManager`（`manager.py:96`）：管理会话的 CRUD ^[nanobot/session/manager.py:96]
**它和谁交互**：
- 被 `AgentLoop` 持有和使用 ^[nanobot/agent/loop.py:183]
- 被 `Consolidator` 用于读取会话中的未合并消息 ^[nanobot/agent/memory.py:214]
**为什么它是可分离的**：独立目录 + 独立文件格式（JSONL）。

**关键机制**（源码可见）：
- **JSONL 存储**：`session_key.jsonl` 文件，首行为 metadata（`_type: "metadata"`），后续行为消息 ^[nanobot/session/manager.py:190-201]
- **消息对齐**：`get_history()` 从最后一个 `user` 消息开始，避免 mid-turn 截断 ^[nanobot/session/manager.py:44-46]
- **Legacy 迁移**：`_load()` 自动从 `~/.nanobot/sessions/` 迁移旧 session 到 workspace ^[nanobot/session/manager.py:142-149]
- **Safe filename**：session key 中的特殊字符被替换为安全文件名 ^[nanobot/session/manager.py:111]
- **降采样保留**：`retain_recent_legal_suffix()` 截断到最近 N 条消息并对齐 user turn ^[nanobot/session/manager.py:69-93]
- **Orphan tool result 清理**：`find_legal_message_start()` 删除开头的 orphan tool 结果 ^[nanobot/session/manager.py:50-53]

**源码证据**：
- 入口文件：`nanobot/session/manager.py`

---

### Entity: Memory System

**代码位置**：`nanobot/agent/memory.py`
**这个模块解决什么问题**：文件级 memory 持久化（MEMORY.md）和历史记录管理，提供 Consolidator（token 驱动合并）和 Dream（定时二阶段深度合并）。
**对外暴露什么**：
- `MemoryStore`（第 31 行）：纯文件 I/O，管理 MEMORY.md, history.jsonl, SOUL.md, USER.md ^[nanobot/agent/memory.py:31]
- `Consolidator`（约第 200+ 行）：token count 驱动的自动合并
- `Dream`（约第 300+ 行）：定时二阶段（Phase 1: 增量归档, Phase 2: 上下文重写）合并
**它和谁交互**：
- 被 `ContextBuilder` 持有 ^[nanobot/agent/context.py:27]
- 被 `AgentLoop` 持有（consolidator, dream）^[nanobot/agent/loop.py:210-224]
- `MemoryStore` 被 `AgentLoop._save_turn()` 间接使用
**为什么它是可分离的**：独立的文件格式约定 + Consolidator 和 Dream 双处理器设计。

**关键机制**（源码可见）：
- **Git 版本追踪**：`GitStore` 用 dulwich 追踪 SOUL.md, USER.md, MEMORY.md 的变更 ^[nanobot/agent/memory.py:52-54]
- **Token 驱动合并**：`Consolidator.maybe_consolidate_by_tokens()` 根据 token count 判断是否需要合并
- **Dream 两阶段**：Phase 1 增量归档新消息到 memory files（文件操作），Phase 2 用 LLM 重写 MEMORY.md（上下文整合）
- **Legacy 迁移**：`_maybe_migrate_legacy_history()` 从 HISTORY.md 迁移到 history.jsonl ^[nanobot/agent/memory.py:70-80]
- **Cursor 管理**：`.cursor` 和 `.dream_cursor` 文件跟踪读取进度 ^[nanobot/agent/memory.py:50-51]
- **模板目录**：`nanobot/templates/memory/` 包含 Dream 两阶段 prompt 模板

**源码证据**：
- 入口文件：`nanobot/agent/memory.py`
- Prompt 模板：`nanobot/templates/memory/`

---

### Entity: Context Builder

**代码位置**：`nanobot/agent/context.py`
**这个模块解决什么问题**：组装 LLM 调用的完整上下文——system prompt + bootstrap files + memory + skills + history + 运行时上下文。
**对外暴露什么**：
- `ContextBuilder`（第 17 行）：`build_system_prompt()`, `build_messages()` ^[nanobot/agent/context.py:17]
**它和谁交互**：
- 被 `AgentLoop` 持有 ^[nanobot/agent/loop.py:182]
- 持有 `MemoryStore` ^[nanobot/agent/context.py:27]
- 持有 `SkillsLoader` ^[nanobot/agent/context.py:28]
**为什么它是可分离的**：独立模块 + 纯函数式构建，不依赖运行时状态。

**关键机制**（源码可见）：
- **Bootstrap 文件**：自动加载 AGENTS.md, SOUL.md, USER.md, TOOLS.md ^[nanobot/agent/context.py:20]
- **运行时上下文注入**：`_build_runtime_context()` 生成带 `[Runtime Context]` 标记的时间/通道元数据，注入用户消息前 ^[nanobot/agent/context.py:80-87]
- **多模态消息合并**：`_merge_message_content()` 支持字符串和 content blocks 的合并 ^[nanobot/agent/context.py:89-101]
- **Base64 图片内联**：`_build_user_content()` 将媒体文件转换为 base64 data URI ^[nanobot/agent/context.py:147-170]
- **Image MIME 检测**：用 magic bytes 检测真实 MIME 类型，fallback 到扩展名 ^[nanobot/agent/context.py:159]
- **Prompt 模板渲染**：通过 `render_template()` 加载 `templates/agent/` 下的 Jinja2 模板

**源码证据**：
- 入口文件：`nanobot/agent/context.py`

---

### Entity: Command Router

**代码位置**：`nanobot/command/`
**这个模块解决什么问题**：斜杠命令的 tiered dispatch——优先级命令（/stop）、精确匹配、前缀匹配、拦截器。
**对外暴露什么**：
- `CommandRouter`（`router.py:27`）：四级路由表 ^[nanobot/command/router.py:27]
- `CommandContext` dataclass（`router.py:16`）：命令上下文 ^[nanobot/command/router.py:16]
- `register_builtin_commands()`（`builtin.py`）：注册所有内置 slash 命令
**它和谁交互**：
- 被 `AgentLoop` 持有和调用 ^[nanobot/agent/loop.py:226-227]
- 在 `AgentLoop.run()` 中处理优先命令（/stop, /restart）^[nanobot/agent/loop.py:385-390]
- 在 `AgentLoop._process_message()` 中处理常规命令 ^[nanobot/agent/loop.py:529-531]
**为什么它是可分离的**：独立目录 + tiered dispatch 架构 + 内置处理器分离。

**关键机制**（源码可见）：
- **四级分发**：priority（不含锁） > exact > prefix（最长前缀优先） > interceptor（fallback）^[nanobot/command/router.py:27-42]
- **优先命令无锁处理**：`/stop` 和 `/restart` 在 `is_priority()` 检查后不经 session lock 直接执行 ^[nanobot/agent/loop.py:385-390]
- **前缀排序**：prefix handler 按长度降序排列，确保最长匹配优先 ^[nanobot/command/router.py:50-52]

**源码证据**：
- 入口文件：`nanobot/command/router.py`
- 内置命令：`nanobot/command/builtin.py`

---

### Entity: Cron Service

**代码位置**：`nanobot/cron/`
**这个模块解决什么问题**：定时任务调度——支持 cron 表达式、固定间隔、一次性执行三种模式。
**对外暴露什么**：
- `CronService`（`service.py:65`）：任务管理、调度执行、持久化 ^[nanobot/cron/service.py:65]
- `CronJob`, `CronSchedule`, `CronPayload`, `CronJobState`, `CronStore`（`types.py`）：数据类型
- `CronSchedule` 的三种 kind：`"cron"`（表达式）、`"every"`（毫秒间隔）、`"at"`（一次性）^[nanobot/cron/types.py]
**它和谁交互**：
- 被 `AgentLoop` 持有（通过 `cron_service` 参数）^[nanobot/agent/loop.py:142]
- `CronTool` 作为 agent tool 暴露给 LLM ^[nanobot/agent/tools/cron.py]
- 通过 `on_job` 回调触发 agent turn
**为什么它是可分离的**：独立目录 + 独立文件存储 + 多实例通过 FileLock + action.jsonl 协调。

**关键机制**（源码可见）：
- **Timer 驱动调度**：`_arm_timer()` 计算最近的到期时间并设置 asyncio timer ^[nanobot/cron/service.py:267-287]
- **多实例协调**：通过 `FileLock` + `action.jsonl` 文件实现在 Gateway 运行时和 CLI `cron add` 之间的操作同步 ^[nanobot/cron/service.py:135-169]
- **重算 next_run**：`_recompute_next_runs()` 在服务启动和配置变更时重新计算所有 job 的 next run ^[nanobot/cron/service.py:250-258]
- **One-shot 处理**：`kind == "at"` 的 job 执行后根据 `delete_after_run` 决定删除或禁用 ^[nanobot/cron/service.py:338-343]
- **运行历史**：保留最近 20 条 `CronRunRecord`，记录 duration/status/error ^[nanobot/cron/service.py:329-335]
- **系统任务保护**：`payload.kind == "system_event"` 的 job 不能被用户删除 ^[nanobot/cron/service.py:425-427]
- **时区支持**：cron 表达式支持 IANA 时区，通过 `zoneinfo.ZoneInfo` 计算 ^[nanobot/cron/service.py:38-48]

**源码证据**：
- 入口文件：`nanobot/cron/service.py`
- 类型定义：`nanobot/cron/types.py`

---

### Entity: Heartbeat Service

**代码位置**：`nanobot/heartbeat/`
**这个模块解决什么问题**：周期性唤醒 agent 检查 HEARTBEAT.md 中是否有待处理任务，通过 LLM 虚拟工具调用决策是否需要执行。
**对外暴露什么**：
- `HeartbeatService`（`service.py:40`）：两阶段执行——Phase 1 决策（LLM 判断 skip/run），Phase 2 执行（跑完整 agent loop）^[nanobot/heartbeat/service.py:40]
**它和谁交互**：
- 被 CLI `gateway` 命令创建
- 调用 `LLMProvider` 进行决策
- 通过 `on_execute` 回调运行完整 agent turn
- 通过 `on_notify` 回调交付结果
**为什么它是可分离的**：独立目录 + 独立的虚拟工具调用协议。

**关键机制**（源码可见）：
- **虚拟工具调用决策**：给 LLM 一个只有 `heartbeat` 工具的 schema，要求 LLM 返回 `skip` 或 `run` + tasks 摘要 ^[nanobot/heartbeat/service.py:14-37]
- **两阶段执行**：Phase 1 是轻量决策（No tool execution），Phase 2 只在 `run` 时触发完整 agent loop ^[nanobot/heartbeat/service.py:40-51]
- **执行后评估**：`evaluate_response()` 用 LLM 判断是否值得通知用户 ^[nanobot/heartbeat/service.py:168-175]
- **手动触发**：`trigger_now()` 允许外部手动触发一次 heartbeat ^[nanobot/heartbeat/service.py:179-187]
- **文件驱动**：`HEARTBEAT.md` 是用户编辑的 tasks 清单，heartbeat 检查此文件 ^[nanobot/heartbeat/service.py:76-85]

**源码证据**：
- 入口文件：`nanobot/heartbeat/service.py`

---

### Entity: Subagent Manager

**代码位置**：`nanobot/agent/subagent.py`
**这个模块解决什么问题**：管理后台子 agent 执行——独立的工具集、独立的 session scope，用于 spawn 工具触发异步后台任务。
**对外暴露什么**：
- `SubagentManager`（第 42 行）：`spawn()` 方法创建并运行子 agent ^[nanobot/agent/subagent.py:42]
- `_SubagentHook`（第 26 行）：仅日志的 hook ^[nanobot/agent/subagent.py:26]
**它和谁交互**：
- 被 `AgentLoop` 持有 ^[nanobot/agent/loop.py:186]
- 被 `SpawnTool` 调用 ^[nanobot/agent/tools/spawn.py]
- 通过系统消息通道与主 loop 通信（`channel="system"`）
**为什么它是可分离的**：独立模块 + 独立工具集 + 通过 system channel 与主 loop 解耦。

**关键机制**（源码可见）：
- **独立工具集**：子 agent 只拥有 filesystem/search/exec/web 工具，无 message/spawn/cron/mcp ^[nanobot/agent/subagent.py:15-19]
- **System channel 通信**：子 agent 结果通过 `channel="system"` 的 InboundMessage 发送回主 loop ^[nanobot/agent/subagent.py]
- **专用 runner**：每个子 agent 使用独立的 `AgentRunner`，共享 provider 和 model ^[nanobot/agent/subagent.py]
- **Subagent system prompt**：通过 `render_template("agent/subagent_system_prompt.md")` 加载

**源码证据**：
- 入口文件：`nanobot/agent/subagent.py`

---

### Entity: Agent Hook (Lifecycle)

**代码位置**：`nanobot/agent/hook.py`
**这个模块解决什么问题**：为 agent 执行循环提供可扩展的生命周期钩子——before_iteration, on_stream, before_execute_tools, after_iteration, finalize_content。
**对外暴露什么**：
- `AgentHook`（第 29 行）：5 个钩子方法 + `wants_streaming()` ^[nanobot/agent/hook.py:29]
- `AgentHookContext` dataclass（第 13 行）：每轮迭代的可变状态 ^[nanobot/agent/hook.py:13]
- `CompositeHook`（第 57 行）：将多个 hook 组合为 fan-out 链 ^[nanobot/agent/hook.py:57]
**它和谁交互**：
- 被 `AgentRunner` 在每个迭代阶段调用 ^[nanobot/agent/runner.py:90]
- 被 `_LoopHook` 继承实现产品层行为 ^[nanobot/agent/loop.py:46]
- 被 `Nanobot.run()` 通过 `hooks` 参数注入 ^[nanobot/nanobot.py:103]
**为什么它是可分离的**：独立模块 + 清晰的接口 + CompositeHook 组合模式 + SDK 通过 hook 扩展。

**关键机制**（源码可见）：
- **Fan-out 错误隔离**：`CompositeHook._for_each_hook_safe()` 捕获每个 hook 的异常（除了标记 `_reraise=True` 的）^[nanobot/agent/hook.py:74-83]
- **Content 管道**：`finalize_content` 按顺序管道化处理 content ^[nanobot/agent/hook.py:100-103]
- **Streaming 投票**：`wants_streaming()` 任一 hook 返回 True 即启用 ^[nanobot/agent/hook.py:71-72]

**源码证据**：
- 入口文件：`nanobot/agent/hook.py`

---

### Entity: API Server

**代码位置**：`nanobot/api/server.py`
**这个模块解决什么问题**：提供 OpenAI-compatible HTTP API（`/v1/chat/completions`, `/v1/models`），所有请求路由到单个固定 session。
**对外暴露什么**：
- `create_app()` 工厂函数：返回 aiohttp Application ^[nanobot/api/server.py]
- `API_SESSION_KEY = "api:default"`（第 19 行）^[nanobot/api/server.py:19]
**它和谁交互**：
- 持有 `AgentLoop` 引用，调用 `process_direct()`
- 通过 aiohttp 暴露 HTTP
**为什么它是可分离的**：独立目录 + 可选的 API extra 依赖 + 与主 loop 通过 process_direct 解耦。

**关键机制**（源码可见）：
- **固定 session**：所有 API 请求共享 `api:default` session ^[nanobot/api/server.py:19]
- **Streaming 支持**：`stream=True` 时返回 SSE 格式的 text/event-stream ^[nanobot/api/server.py]
- **Authorization 校验**：通过 `X-Nanobot-API-Key` 或 Bearer token ^[nanobot/api/server.py]
- **Method 限制**：支持 `GET` 和 `POST`
- **Timeout 保护**：`asyncio.wait_for()` 限制单次请求时限为 `ApiConfig.timeout` 秒 ^[nanobot/config/schema.py:142]

**源码证据**：
- 入口文件：`nanobot/api/server.py`

---

### Entity: Security (SSRF Protection)

**代码位置**：`nanobot/security/network.py`
**这个模块解决什么问题**：防止 SSRF 攻击——验证 URL 目标不解析到内网/私有地址。
**对外暴露什么**：
- `validate_url_target()`（第 46 行）：DNS 解析并验证 URL 目标 ^[nanobot/security/network.py:46]
- `validate_resolved_url()`（第 81 行）：验证已重定向的 URL ^[nanobot/security/network.py:81]
- `contains_internal_url()`（第 113 行）：检查命令字符串中是否包含内网 URL ^[nanobot/security/network.py:113]
- `configure_ssrf_whitelist()`（第 28 行）：配置 SSRF 白名单 CIDR ^[nanobot/security/network.py:28]
**它和谁交互**：
- 被 `ExecTool` 用于验证 shell 命令中的 URL
- 被 `WebFetchTool` 用于验证 fetch 目标
**为什么它是可分离的**：独立目录 + 纯函数 + 无依赖。

**关键机制**（源码可见）：
- **私有地址范围**：阻止 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16 (cloud metadata), 100.64.0.0/10 (C-GNAT) ^[nanobot/security/network.py:10-21]
- **IPv6 阻止**：::1/128, fc00::/7, fe80::/10 ^[nanobot/security/network.py:18-20]
- **Whitelist 覆盖**：白名单 CIDR（如 Tailscale 100.64.0.0/10）可跳过隐私检查 ^[nanobot/security/network.py:40-43]
- **Scheme 检查**：仅允许 http/https ^[nanobot/security/network.py:56-57]

**源码证据**：
- 入口文件：`nanobot/security/network.py`

---

### Entity: Sandbox Backend

**代码位置**：`nanobot/agent/tools/sandbox.py`
**这个模块解决什么问题**：为 shell 命令执行提供沙箱包装，目前支持 bubblewrap (bwrap)。
**对外暴露什么**：
- `wrap_command()`（第 51 行）：按名称选择后端，返回包装后的命令 ^[nanobot/agent/tools/sandbox.py:51]
- `_BACKENDS` 字典（第 48 行）：注册的后端函数映射 ^[nanobot/agent/tools/sandbox.py:48]
- `_bwrap()`（第 14 行）：使用 bubblewrap 创建 Linux namespace 隔离 ^[nanobot/agent/tools/sandbox.py:14]
**它和谁交互**：
- 被 `ExecTool` 调用包装 shell 命令
- 通过 `tools.exec.sandbox` 配置项切换
**为什么它是可分离的**：独立的字典注册机制 + 配置可替换。

**关键机制**（源码可见）：
- **bwrap 隔离**：创建新的 mount namespace，仅 bind-mount /usr（必需）和可选目录，workspace 父目录（含 config.json）被 tmpfs 隐藏 ^[nanobot/agent/tools/sandbox.py:29-45]
- **Media 只读访问**：media 目录以只读方式 bind-mount，允许 exec 读取上传附件 ^[nanobot/agent/tools/sandbox.py:41]
- **CWD 安全**：cwd 被强制限制在 workspace 内 ^[nanobot/agent/tools/sandbox.py:25-27]
- **后端注册模式**：`_BACKENDS = {"bwrap": _bwrap}` 字典注册，添加新后端只需增加 entry ^[nanobot/agent/tools/sandbox.py:48]

**源码证据**：
- 入口文件：`nanobot/agent/tools/sandbox.py`

---

### Entity: CLI Interface

**代码位置**：`nanobot/cli/`
**这个模块解决什么问题**：Typer-based 命令行接口——agent, gateway, channels, cron, onboard 等子命令。
**对外暴露什么**：
- `app` typer.Typer 实例（`commands.py:59`）：CLI 入口，`pyproject.toml` 中 `nanobot = "nanobot.cli.commands:app"` ^[nanobot/cli/commands.py:59]
- `StreamRenderer`（`stream.py`）：Rich-based Markdown 流式渲染
- `onboard.py`：交互式配置向导
- `models.py`：模型列表展示
**它和谁交互**：
- 通过 `Nanobot.from_config()` 创建 bot 实例
- 通过 `Config` 读取配置
- 通过 `MessageBus` 和 `AgentLoop` 驱动 CLI agent 模式
**为什么它是可分离的**：独立目录 + Typer 框架 + 通过 `Nanobot` facade 与核心解耦。

**关键机制**（源码可见）：
- **Rich Markdown 流式渲染**：`StreamRenderer` 使用 Rich console 实时渲染 LLM 输出
- **Prompt Toolkit 输入**：`PromptSession` 提供行编辑、历史、粘贴支持 ^[nanobot/cli/commands.py:25-28]
- **SafeFileHistory**：处理 Windows surrogate 字符问题 ^[nanobot/cli/commands.py:38-48]
- **TTY input flush**：生成输出期间丢弃缓冲的按键 ^[nanobot/cli/commands.py:77-100]

**源码证据**：
- 入口文件：`nanobot/cli/commands.py`
- 流式渲染：`nanobot/cli/stream.py`
- 安装向导：`nanobot/cli/onboard.py`

---

### Entity: Nanobot Facade (SDK)

**代码位置**：`nanobot/nanobot.py`
**这个模块解决什么问题**：高层编程接口，让 Python 代码以 SDK 方式使用 nanobot agent。
**对外暴露什么**：
- `Nanobot` 类（第 23 行）：`from_config()` 工厂 + `run()` 方法 ^[nanobot/nanobot.py:23]
- `RunResult` dataclass（第 15 行）：执行结果 ^[nanobot/nanobot.py:15]
**它和谁交互**：
- 创建 `AgentLoop` 实例
- 通过 `process_direct()` 绕过消息总线直接与 agent 交互
- 被 CLI `gateway` 命令使用
- 作为 `__all__` 导出 ^[nanobot/__init__.py:32]
**为什么它是可分离的**：独立模块 + 纯 facade 模式 + 公共 API 入口。

**关键机制**（源码可见）：
- **Config-driven 构造**：`from_config()` 加载配置、解析 provider、组装完整 AgentLoop ^[nanobot/nanobot.py:36-86]
- **Hook 注入**：`run()` 支持 `hooks` 参数注入自定义 lifecycle hooks ^[nanobot/nanobot.py:103-105]
- **Session 隔离**：`session_key` 参数隔离不同调用者的对话历史 ^[nanobot/nanobot.py:93]
- **Provider 工厂**：`_make_provider()` 根据 backend 类型和 provider spec 实例化正确的 Provider 子类 ^[nanobot/nanobot.py:117-177]

**源码证据**：
- 入口文件：`nanobot/nanobot.py`

---

### Entity: Skills System

**代码位置**：`nanobot/agent/skills.py`
**这个模块解决什么问题**：管理 agent skills——从 workspace 和内置目录加载 SKILL.md 文件，按需注入 system prompt。
**对外暴露什么**：
- `SkillsLoader`：管理 always skills 和 on-demand skills
- `BUILTIN_SKILLS_DIR`：内置 skills 目录路径 ^[nanobot/agent/loop.py:22]
**它和谁交互**：
- 被 `ContextBuilder` 持有 ^[nanobot/agent/context.py:28]
- Skill 模板通过 `render_template()` 加载
**为什么它是可分离的**：独立的文件加载机制 + 内置 skills 目录。

**关键机制**（源码可见）：
- **Always vs On-Demand**：`get_always_skills()` 返回始终激活的 skills，其他按需加载
- **Skill 模板目录**：`nanobot/skills/` 目录包含 skill-creator 和内置 skills
- **Workspace override**：workspace 中的 skills 覆盖内置

**源码证据**：
- 入口文件：`nanobot/agent/skills.py`
- 内置 skills：`nanobot/skills/`

---

### Entity: Prompt Templates

**代码位置**：`nanobot/utils/prompt_templates.py` + `nanobot/templates/`
**这个模块解决什么问题**：Jinja2-based 模板渲染系统，管理 agent 的各种 prompt 片段。
**对外暴露什么**：
- `render_template()` 函数（`prompt_templates.py`）：按名称加载模板并渲染 ^[nanobot/utils/prompt_templates.py]
**它和谁交互**：被 `ContextBuilder`、`AgentLoop`、`SubagentManager`、`Consolidator`、`Dream` 等调用。
**为什么它是可分离的**：独立的模板目录 + Jinja2 引擎 + 资源分离（markdown 文件而非代码内嵌）。

**关键机制**（源码可见）：
- **Jinja2 模板引擎**：支持变量插值、条件、循环
- **模板目录结构**：`nanobot/templates/agent/`, `nanobot/templates/memory/`
- **Type-safe 参数**：模板参数通过 Python 变量传入

**源码证据**：
- 入口文件：`nanobot/utils/prompt_templates.py`
- 模板目录：`nanobot/templates/`

---

### Entity: Utilities

**代码位置**：`nanobot/utils/`
**这个模块解决什么问题**：跨模块共享的工具函数。
**对外暴露什么**：
- `helpers.py`：`truncate_text()`, `strip_think()`, `estimate_message_tokens()`, `build_assistant_message()`, `image_placeholder_text()`, `safe_filename()`, `ensure_dir()`, `current_time_str()`, `sync_workspace_templates()` 等
- `runtime.py`：`EMPTY_FINAL_RESPONSE_MESSAGE`, `build_finalization_retry_message()`, `build_length_recovery_message()`, `ensure_nonempty_tool_result()`, `repeated_external_lookup_error()`
- `path.py`：`is_within_workspace()` 路径安全检查
- `restart.py`：`/restart` 命令的环境变量传递
- `gitstore.py`：`GitStore` — dulwich-based git 操作（用于 memory track）
- `evaluator.py`：`evaluate_response()` — LLM 判断是否值得通知
- `tool_hints.py`：`format_tool_hints()` — 工具调用提示格式化
- `searchusage.py`：外部查找用量跟踪
**它和谁交互**：被所有其他模块引用。
**为什么它是可分离的**：独立目录 + 纯函数集合 + 无状态。

**源码证据**：
- 入口文件：`nanobot/utils/helpers.py`

---

### Entity: Bridge (WhatsApp)

**代码位置**：`bridge/`
**这个模块解决什么问题**：TypeScript Node.js bridge 用于 WhatsApp 连接，通过 baileys 库实现 WhatsApp Web 协议。
**对外暴露什么**：
- Node.js package（`bridge/package.json`）
- TypeScript 源文件（`bridge/src/`）
**它和谁交互**：被 `nanobot/channels/whatsapp.py` 管理和调用。
**为什么它是可分离的**：独立的 Node.js 项目 + 独立的 package.json + 通过 `nanobot channels login whatsapp` CLI 启动。

**关键机制**（源码可见）：
- **baileys WhatsApp Web 协议**：Node.js 端实现 WhatsApp WebSocket 连接
- **与 Python 通信**：通过本地 HTTP/localhost 与 Python channel 通信
- **Wheel 打包**：通过 `hatch.build.targets.wheel.force-include` 将 bridge 打包进 Python wheel ^[pyproject.toml:112]

**源码证据**：
- 入口文件：`bridge/package.json`

---

## Part Two: Candidate Ontology Nodes

---

### Ontology 候选: LLM Provider Abstraction (LLM 供应者抽象)

**信号类型**：接口 + 多实现 + 注册机制 + 配置可替换（全部四种信号）

**源码证据**：
- Interface/ABC 定义：`LLMProvider` class in `nanobot/providers/base.py:80`，定义了 `chat()` abstract method ^[nanobot/providers/base.py:250-275]
- 多个具体实现：
  - `AnthropicProvider` ^[nanobot/providers/anthropic_provider.py:24]
  - `OpenAICompatProvider` ^[nanobot/providers/openai_compat_provider.py]
  - `AzureOpenAIProvider` ^[nanobot/providers/azure_openai_provider.py]
  - `OpenAICodexProvider` ^[nanobot/providers/openai_codex_provider.py]
  - `GitHubCopilotProvider` ^[nanobot/providers/github_copilot_provider.py]
- 注册机制：`PROVIDERS` tuple（30+ `ProviderSpec` 条目）^[nanobot/providers/registry.py:75-361]，`find_by_name()` 查找 ^[nanobot/providers/registry.py:369-375]
- 配置可替换：`config.agents.defaults.provider` 可选择 "auto" 或具体名称（如 "anthropic", "openrouter"）^[nanobot/config/schema.py:67-69]

**下属 Entity**：
- LLM Provider Interface & Implementations (`nanobot/providers/`)
- Nanobot Facade (`nanobot/nanobot.py`) — `_make_provider()` 使用该抽象 ^[nanobot/nanobot.py:117-177]
- Configuration System — `ProvidersConfig` 定义了所有 provider 的配置字段 ^[nanobot/config/schema.py:97-126]

**判断置信度**：高（接口 + 5+ 实现 + 注册表 + 配置切换 + ProviderSpec 元数据注册）

---

### Ontology 候选: Chat Channel Abstraction (聊天通道抽象)

**信号类型**：接口 + 多实现 + 注册机制 + 配置可替换（全部四种信号）

**源码证据**：
- Interface/ABC 定义：`BaseChannel` ABC in `nanobot/channels/base.py:15`，定义 `start()` ^[base.py:68], `stop()` ^[base.py:80], `send()` ^[base.py:85], `send_delta()` ^[base.py:98]
- 13 个具体实现：telegram.py, discord.py, whatsapp.py, weixin.py, feishu.py, dingtalk.py, slack.py, matrix.py, email.py, qq.py, wecom.py, mochat.py
- 注册机制：`discover_all()` 通过 pkgutil 扫描 + entry_points 插件发现 ^[nanobot/channels/registry.py:54-71]
- 配置可替换：`channels.*.enabled` 每个 channel 独立启用/禁用 ^[nanobot/config/schema.py:26]

**下属 Entity**：
- Chat Channel Interface & Implementations (`nanobot/channels/`)
- Channel Manager (`nanobot/channels/manager.py`) — 使用 BaseChannel 接口管理所有 channel
- Message Bus (`nanobot/bus/`) — 被 BaseChannel._handle_message() 用于消息传递 ^[nanobot/channels/base.py:127-171]
- Bridge (`bridge/`) — whatsapp channel 的 Node.js 辅助

**判断置信度**：高（接口 + 13 实现 + 注册发现 + entry_points 插件 + 配置启用）

---

### Ontology 候选: Agent Tool System (Agent 工具系统)

**信号类型**：接口 + 多实现 + 注册机制 + 配置可替换（全部四种信号）

**源码证据**：
- Interface/ABC 定义：`Tool` ABC in `nanobot/agent/tools/base.py:117`，定义 `name`, `description`, `parameters`, `execute()` ^[nanobot/agent/tools/base.py:137-172]
- 10+ 个具体实现：ReadFileTool, WriteFileTool, EditFileTool, ListDirTool, GlobTool, GrepTool, ExecTool, WebSearchTool, WebFetchTool, MessageTool, SpawnTool, CronTool（分别在 filesystem.py, search.py, shell.py, web.py, message.py, spawn.py, cron.py）
- 注册机制：`ToolRegistry.register()` / `unregister()` ^[nanobot/agent/tools/registry.py:18-23]，MCP 工具通过 `connect_mcp_servers()` 动态注册 ^[nanobot/agent/tools/mcp.py]
- 配置可替换：`tools.web.enable`, `tools.exec.enable`, `tools.mcp_servers` 配置控制工具可用性 ^[nanobot/config/schema.py:164-201]

**下属 Entity**：
- Agent Tool System & Registry (`nanobot/agent/tools/`)
- Agent Runner — 通过 `ToolRegistry` 执行工具调用 ^[nanobot/agent/runner.py:83]
- MCP Integration (`nanobot/agent/tools/mcp.py`) — 动态加载外部工具
- Sandbox Backend (`nanobot/agent/tools/sandbox.py`) — ExecTool 的沙箱包装

**判断置信度**：高（接口 + 10+ 实现 + 注册表 + 配置控制 + MCP 动态扩展）

---

### Ontology 候选: Schema-Driven Validation (Schema 驱动验证)

**信号类型**：接口 + 多实现

**源码证据**：
- Interface/ABC 定义：`Schema` ABC in `nanobot/agent/tools/base.py:21`，定义 `to_json_schema()` ^[nanobot/agent/tools/base.py:107] 和 `validate_value()` ^[nanobot/agent/tools/base.py:112]
- 6 个具体实现：`StringSchema`, `IntegerSchema`, `NumberSchema`, `BooleanSchema`, `ArraySchema`, `ObjectSchema` ^[nanobot/agent/tools/__init__.py:5-12]
- 额外实现：`tool_parameters_schema` 组合模式 ^[nanobot/agent/tools/schema.py]

**下属 Entity**：
- Agent Tool System — `Tool.cast_params()` 和 `Tool.validate_params()` 使用 Schema 进行参数转换和验证 ^[nanobot/agent/tools/base.py:180-232]
- Tool Registry — `prepare_call()` 调用 cast 和 validate ^[nanobot/agent/tools/registry.py:65-83]
- MCP Integration — `_normalize_schema_for_openai()` 转换 MCP schema 为 OpenAI-compatible ^[nanobot/agent/tools/mcp.py:34]

**判断置信度**：中（接口 + 6+ 实现 + 嵌套组合模式，但无独立注册机制或配置切换）

---

### Ontology 候选: Agent Lifecycle Hooks (Agent 生命周期钩子)

**信号类型**：接口 + 多实现 + 组合模式

**源码证据**：
- Interface/ABC 定义：`AgentHook` class in `nanobot/agent/hook.py:29`，定义 5 个生命周期方法 ^[nanobot/agent/hook.py:38-54]
- 多个实现：
  - `_LoopHook` in `nanobot/agent/loop.py:46` — 产品层实现 ^[nanobot/agent/loop.py:46]
  - `_SubagentHook` in `nanobot/agent/subagent.py:26` — 子 agent logging ^[nanobot/agent/subagent.py:26]
  - `CompositeHook` in `nanobot/agent/hook.py:57` — fan-out 组合器 ^[nanobot/agent/hook.py:57]
- 注入机制：`AgentRunner` 构造函数接受 `AgentHook` ^[nanobot/agent/runner.py:90]，`Nanobot.run()` 的 `hooks` 参数 ^[nanobot/nanobot.py:103]

**下属 Entity**：
- Agent Hook (`nanobot/agent/hook.py`)
- Agent Runner — 在每个生命周期节点调用 hook ^[nanobot/agent/runner.py:117]
- Agent Loop — `_LoopHook` 实现 ^[nanobot/agent/loop.py:46]
- Nanobot Facade — 通过 `hooks` 参数暴露 ^[nanobot/nanobot.py:103-105]

**判断置信度**：中（接口 + 3 实现 + 组合器 + SDK 注入点，但无注册表或配置切换）

---

### Ontology 候选: Command Routing (命令路由)

**信号类型**：注册机制

**源码证据**：
- 注册机制：`CommandRouter` 提供 `priority()`, `exact()`, `prefix()`, `intercept()` 四种注册方法 ^[nanobot/command/router.py:44-55]
- 四级分发：priority > exact > prefix（最长前缀优先） > interceptor ^[nanobot/command/router.py:27-42]
- 内置命令注册：`register_builtin_commands()` 注册所有内置 handler ^[nanobot/command/builtin.py]

**下属 Entity**：
- Command Router (`nanobot/command/`)
- Agent Loop — 持有并调用 CommandRouter ^[nanobot/agent/loop.py:385-390, 529-531]

**判断置信度**：中（注册机制 + tiered dispatch，但无接口抽象，所有 handler 是同类型 function）

---

### Ontology 候选: Cron Scheduling (定时任务调度)

**信号类型**：独立包导出

**源码证据**：
- 独立目录：`nanobot/cron/`
- 导出的核心类型：`CronService` ^[nanobot/cron/service.py:65], `CronSchedule`（三种 kind：cron/every/at）^[nanobot/cron/types.py]
- 配置控制：`DreamConfig.build_schedule()` 使用 CronSchedule ^[nanobot/config/schema.py:48-52]
- 工具暴露：`CronTool` 将调度能力暴露给 LLM ^[nanobot/agent/tools/cron.py]

**下属 Entity**：
- Cron Service (`nanobot/cron/`)
- CronTool (`nanobot/agent/tools/cron.py`) — 将服务包装为 agent tool

**判断置信度**：中（独立包 + 类型导出 + 配置集成，但无接口抽象或多实现）

---

### Ontology 候选: Memory Consolidation (记忆合并)

**信号类型**：独立包导出 + 双处理器设计

**源码证据**：
- 双处理器设计：`Consolidator`（token 驱动）和 `Dream`（定时二阶段）在同一个文件中定义 ^[nanobot/agent/memory.py]
- `MemoryStore` 是纯文件 I/O 层 ^[nanobot/agent/memory.py:31]
- 配置控制：`DreamConfig` 控制 Dream 的间隔和参数 ^[nanobot/config/schema.py:34-59]
- 多实现信号：Consolidator 和 Dream 是两种不同的合并策略

**下属 Entity**：
- Memory System (`nanobot/agent/memory.py`)
- Session Management — Consolidator 通过 SessionManager 读取会话 ^[nanobot/agent/memory.py:214]
- Context Builder — 持有 MemoryStore ^[nanobot/agent/context.py:27]
- Prompt Templates — Dream 两阶段使用独立 prompt 模板

**判断置信度**：中（两种合并策略 + 配置控制 + 独立文件持久化，但无显式接口抽象）

---

### Ontology 候选: Sandbox Strategy (沙箱策略)

**信号类型**：注册机制 + 配置可替换

**源码证据**：
- 注册机制：`_BACKENDS` 字典，函数名约定 `_wrap_<name>` ^[nanobot/agent/tools/sandbox.py:48]
- 配置可替换：`tools.exec.sandbox` 可选择 `""`（无沙箱）或 `"bwrap"` ^[nanobot/config/schema.py:179]
- 统一接口：`wrap_command(sandbox, command, workspace, cwd) -> str` ^[nanobot/agent/tools/sandbox.py:51-55]
- 当前实现：`_bwrap()` — bubblewrap Linux namespace 隔离 ^[nanobot/agent/tools/sandbox.py:14]

**下属 Entity**：
- Sandbox Backend (`nanobot/agent/tools/sandbox.py`)
- ExecTool (`nanobot/agent/tools/shell.py`) — 调用 wrap_command

**判断置信度**：低（仅 1 个后端实现，但架构上预留了扩展点——字典注册 + 配置切换）

---

### Ontology 候选: Web Search Provider (Web 搜索提供者)

**信号类型**：配置可替换

**源码证据**：
- 配置可替换：`tools.web.search.provider` 可选择 `"brave"`, `"tavily"`, `"duckduckgo"`, `"searxng"`, `"jina"` ^[nanobot/config/schema.py:156]
- `WebSearchConfig` 包含 `api_key`, `base_url`, `max_results`, `timeout` ^[nanobot/config/schema.py:153-160]

**下属 Entity**：
- WebSearchTool (`nanobot/agent/tools/web.py`) — 使用 provider 配置选择搜索后端
- Config System — WebSearchConfig 定义

**判断置信度**：中（5 个配置选项，但无显式接口抽象——通过 if/else 在工具内部切换）

---

### Ontology 候选: Voice Transcription Provider (语音转录提供者)

**信号类型**：配置可替换

**源码证据**：
- 配置可替换：`channels.transcription_provider` 可选择 `"groq"` 或 `"openai"` ^[nanobot/config/schema.py:31]
- 实现切换：`BaseChannel.transcribe_audio()` 根据配置选择 `OpenAITranscriptionProvider` 或 `GroqTranscriptionProvider` ^[nanobot/channels/base.py:40-54]
- 独立实现：`nanobot/providers/transcription.py` 导出 `OpenAITranscriptionProvider` 和 `GroqTranscriptionProvider` ^[nanobot/channels/base.py:46,49]

**下属 Entity**：
- Chat Channel Interface — `transcribe_audio()` 使用该抽象 ^[nanobot/channels/base.py:40]
- Channel Manager — 根据配置解析 API key ^[nanobot/channels/manager.py:67-74]
- Transcription providers (`nanobot/providers/transcription.py`)

**判断置信度**：中（2 个实现 + 配置切换 + 独立的 transcription.py，但无显式接口 ABC）

---

### Ontology 候选: Message Bus / Event Decoupling (消息总线/事件解耦)

**信号类型**：独立包导出

**源码证据**：
- 独立目录：`nanobot/bus/`，导出 `MessageBus`, `InboundMessage`, `OutboundMessage`
- `MessageBus` 使用双 `asyncio.Queue` 实现 ^[nanobot/bus/queue.py:17-18]
- 所有 channel-agent 通信通过 bus ^[nanobot/channels/base.py:171]，agent 响应通过 bus ^[nanobot/agent/loop.py:442]

**下属 Entity**：
- Message Bus (`nanobot/bus/`)
- Chat Channel Interface — 所有 channel 的入站消息通过 bus 发送 ^[nanobot/channels/base.py:171]
- Agent Loop — 消费入站、发布出站 ^[nanobot/agent/loop.py:371, 442]

**判断置信度**：中（独立包 + 清晰的数据类型 + 整个架构基于它解耦，但无接口抽象或多种实现）

---

### Ontology 候选: Session Persistence (会话持久化)

**信号类型**：独立包导出

**源码证据**：
- 独立目录：`nanobot/session/`
- JSONL 文件格式：首行为 `_type: "metadata"`，后续为消息行 ^[nanobot/session/manager.py:190-201]
- 消息对齐逻辑：`get_history()` 从 user 消息开始 ^[nanobot/session/manager.py:43-46]
- Legacy 迁移：自动从旧路径迁移 ^[nanobot/session/manager.py:142-149]

**下属 Entity**：
- Session Management (`nanobot/session/`)
- Memory System — Consolidator 通过 SessionManager 获取会话 ^[nanobot/agent/memory.py:214]
- Agent Loop — 持有 SessionManager ^[nanobot/agent/loop.py:183]

**判断置信度**：中（独立包 + 独立存储格式 + 迁移逻辑，但无接口抽象）

---

### Ontology 候选: Subagent / Background Task Execution (子 Agent / 后台任务执行)

**信号类型**：独立包导出

**源码证据**：
- 独立模块：`nanobot/agent/subagent.py`
- 独立的工具集：子 agent 拥有自己的 ToolRegistry（不含 message/spawn/cron/mcp）^[nanobot/agent/subagent.py:15-19]
- 独立的系统提示：通过 `subagent_system_prompt.md` 模板
- 通信协议：通过 `channel="system"` 与主 loop 通信

**下属 Entity**：
- Subagent Manager (`nanobot/agent/subagent.py`)
- SpawnTool (`nanobot/agent/tools/spawn.py`) — 触发子 agent 的工具
- Agent Runner — 子 agent 使用独立的 AgentRunner ^[nanobot/agent/subagent.py]

**判断置信度**：中（独立管理器 + 独立工具集 + 独立通信协议，但无接口抽象或多实现）

---

## Part Three: 孤立 Entity（未找到 Ontology 归属）

- **Configuration System**：虽然被所有模块依赖，但它本身没有接口抽象或多实现——本质是 Pydantic schema 定义，不是"能力域"。
- **Context Builder**：纯函数式 prompt 构建器，没有可替换策略或接口抽象。它的行为完全由模板文件和引导文件驱动。
- **CLI Interface**：Typer 命令行接口，是产品层入口而非能力域。没有可替换的实现策略。
- **Heartbeat Service**：独立的周期性检查服务，但没有接口抽象或多实现。只有一个 HeartbeatService 类。
- **Nanobot Facade**：纯粹的外观模式，没有自己的能力域——它只是 AgentLoop 的高级封装。
- **Security (SSRF Protection)**：静态工具函数集合，没有接口抽象或配置可替换策略。
- **Prompt Templates**：资源层（Jinja2 模板文件），不是能力域。
- **Utilities**：跨模块共享的工具函数，不是能力域。
- **Bridge (WhatsApp)**：Node.js 辅助进程，属于 WhatsApp Channel 的实现细节，不构成独立能力域。
- **API Server**：aiohttp-based HTTP 服务器，单会话路由。没有接口抽象或多实现。
- **Skills System**：文件加载机制，无接口抽象或可替换策略。


# Hermes Agent — Architecture 维度

> 本文档从 Architecture 维度分析 Hermes Agent 的核心抽象、分层架构、数据流方向和关注点分离策略。

---

## 1. 核心抽象

### 1.1 AIAgent（中央编排器）

`AIAgent` 是整个系统的中央引擎，封装了单次会话的完整生命周期管理。所有入口点（CLI、Gateway、Batch Runner、ACP Server）均实例化 `AIAgent` 并调用其 `run_conversation()` 方法执行会话任务。^[run_agent.py:1-21]

其核心职责包括：
- **LLM 通信**：支持 OpenAI 风格的 Chat Completions 和 Anthropic 原生 Message API 两种协议，通过 provider 解析链自动选择和切换客户端。^[agent/process_bootstrap.py:81-100]
- **工具编排**：启动时通过集中式工具注册表 `get_tool_definitions()` 发现工具，运行时根据用户配置过滤可用工具，并将 LLM 返回的 function call 分发至 `handle_function_call()`。^[run_agent.py:121-127]
- **上下文管理**：动态构建系统提示词（system prompt），在 token 用量接近模型上下文窗口限制时自动触发上下文压缩。^[agent/prompt_builder.py:145-152]
- **会话状态与记忆管理**：集成本地记忆文件（`MEMORY.md`、`USER.md`）和 Honcho AI 原生记忆系统，支持跨会话状态持久化。^[hermes_cli/main.py:21-36]
- **迭代预算控制**：通过 `IterationBudget` 机制控制对话深度和子代理委托的上限。^[agent/iteration_budget.py:1-103]

### 1.2 ToolRegistry（工具注册表单例）

`ToolRegistry` 是集中式工具注册表单例，持有系统中所有可用工具的元数据和处理器，是工具发现的权威来源。^[tools/registry.py:151-167]

关键特征：
- **自注册模式**：每个工具模块在被导入时，通过 `registry.register()` 自行注册其 schema、handler、check_fn 等元数据。^[model_tools.py:5-9]
- **线程安全**：所有工具条目的快照和可用性检查缓存均为线程安全操作。^[tools/registry.py:77-108]
- **异步桥接**：通过 `_run_async()` 机制统一支持同步和异步工具处理器，在 CLI 主线程和 worker 线程中维护持久化事件循环。^[model_tools.py:83-102]

### 1.3 BaseEnvironment（执行环境抽象）

`BaseEnvironment` 是所有执行后端的抽象基类，定义了统一的 `execute()` 和 `cleanup()` 接口。^[tools/environments/base.py:213-222]

核心设计：
- **spawn-per-call 模型**：每次命令调用都启动全新的 `bash -c` 进程，但通过 session 快照机制维持跨调用的状态（CWD、环境变量、shell 变量）。^[tools/environments/base.py:3-7]
- **ProcessHandle 协议**：后端返回统一的 `ProcessHandle`（类似 `subprocess.Popen`）或 `_ThreadedProcessHandle`（SDK 类后端），提供统一的轮询和等待接口。^[tools/environments/base.py:187-200]
- **工厂模式**：通过 `_create_environment()` 工厂函数根据 `TERMINAL_ENV` 环境变量解析并实例化对应的后端类。^[tools/terminal_tool.py:534-585]

支持六种后端：Local（本地直接执行）、Docker（安全加固容器）、SSH（远程 ControlMaster 连接）、Modal（云端无服务器沙箱）、Daytona（云端开发工作区）、Singularity（HPC 容器）。^[tools/terminal_tool.py:534-585]

### 1.4 GatewayRunner（网关运行器）

`GatewayRunner` 是多平台消息网关的中央控制器，管理平台适配器的生命周期、会话映射和代理实例缓存。^[gateway/run.py:6-65]

核心抽象：
- **代理缓存**：维护 LRU 缓存（默认最大 128 个实例），由 `_AGENT_CACHE_MAX_SIZE` 限制容量，超过 `_AGENT_CACHE_IDLE_TTL_SECS`（1 小时）空闲的实例被淘汰。^[gateway/run.py:59-65]
- **并发守护**：使用 `_AGENT_PENDING_SENTINEL` 哨兵值防止同一用户的并发消息创建重复代理实例。^[gateway/run.py:18-19]
- **瞬态错误处理**：`_is_transient_network_error` 识别网络级异常，防止整个守护进程因平台特有超时而崩溃。^[gateway/run.py:143-184]

### 1.5 BasePlatformAdapter（平台适配器基类）

`BasePlatformAdapter` 定义消息平台适配器的抽象接口，包括消息发送、媒体处理、消息截断等方法。^[gateway/platforms/base.py:20-40]

每个适配器将平台特定协议规范化为统一的 `MessageEvent` 格式，GatewayRunner 再将事件路由到对应的 `AIAgent` 实例。支持 Telegram、Discord、Slack、WhatsApp、Matrix、飞书、微信、QQ 机器人等。^[gateway/platforms/base.py:55-77]

### 1.6 IterationBudget（迭代预算）

`IterationBudget` 管理对话中工具调用的最大步数限制，防止无限循环。默认预算 90 次迭代，可在所有子代理间共享分配。^[agent/iteration_budget.py:33-35]

子代理委托时（`delegate_task`），子代理从父代理继承一定比例的预算，并由 `MAX_DEPTH`（默认 1）限制递归深度。^[tools/delegate_tool.py:133-138]

### 1.7 Toolset（工具集）

Toolsets 是工具的逻辑分组机制，简化了启停相关能力组合的配置。^[toolsets.py:5-7]

支持组合模式：通过 `includes` 键递归地包含其他 toolset，实现嵌套组合。^[toolsets.py:240-246]

核心工具集包括：`web`（网页研究与提取）、`terminal`（命令执行和进程管理）、`file`（文件操作）、`browser`（Playwright 浏览器自动化）、`vision`（图像分析）、`code_execution`（沙箱代码执行）、`delegation`（子代理任务委托）、`mcp`（动态外部 MCP 工具）。^[toolsets.py:78-210]

### 1.8 Skill（技能）

Skill 是以 `SKILL.md` 为核心的程序性知识包，为代理提供逐步指令、参考材料、模板和辅助脚本。^[tools/skills_tool.py:9-13]

采用渐进式披露（Progressive Disclosure）模式：系统提示词中仅出现精简索引（Tier 0）；代理按需通过 `skill_view` 加载完整指令（Tier 1）；可进一步访问具体的参照文件和模板（Tier 2）。^[tools/skills_tool.py:52-67]

---

## 2. 分层架构

Hermes Agent 采用严格的三层架构设计：

### 2.1 第一层：用户界面层（User Interface Layer）

负责接收用户输入和呈现代理输出。包含四种主要入口点：

| 入口 | 实现文件 | 适用场景 | 会话持久化 |
|------|----------|----------|-----------|
| CLI | `cli.py`, `hermes_cli/main.py` | 交互式终端会话（含 TUI） | `~/.hermes/sessions/` |
| Gateway | `gateway/run.py` | 多平台消息（Telegram、Discord 等） | `~/.hermes/sessions/` |
| ACP Server | `acp_adapter/server.py` | IDE 集成（VS Code、Zed） | 客户端管理 |
| Web UI | `hermes_cli/web_server.py` | 浏览器仪表盘和聊天 | `~/.hermes/sessions/` |

^[cli.py:1-14], ^[gateway/run.py:1-14], ^[hermes_cli/main.py:1-44], ^[hermes_cli/web_server.py:1-5]

### 2.2 第二层：核心代理层（Core Agent Layer）

负责对话编排、上下文管理、工具调用分发和记忆管理。核心组件：

- `AIAgent` 类（`run_agent.py`）：对话循环的中枢引擎。^[run_agent.py:17-21]
- `agent/prompt_builder.py`：系统提示词构造，整合 persona（`SOUL.md`）、技能索引、项目上下文文件等。^[agent/prompt_builder.py:145-152]
- `model_tools.py`：工具定义获取和 `handle_function_call` 分发入口。^[model_tools.py:1-21]
- `agent/context_compressor.py`：上下文窗口超限时自动压缩历史消息。^[agent/context_compressor.py:1-41]
- `agent/auxiliary_client.py`：辅助 LLM 客户端，处理视觉分析、网页提取、上下文压缩等旁路任务。^[agent/auxiliary_client.py:1-41]
- `hermes_state.py`：SQLite 会话状态持久化（`SessionDB`）。^[hermes_state.py:1-37]

### 2.3 第三层：工具与执行层（Tool & Execution Layer）

负责将自然语言指令翻译为实际代码执行。核心组件：

- **工具系统**：`tools/registry.py`（注册表单例）、`toolsets.py`（工具集定义）、各工具模块（`tools/terminal_tool.py`、`tools/browser_tool.py`、`tools/file_operations.py`、`tools/web_tools.py` 等）。
- **执行环境**：`tools/environments/base.py`（抽象基类）及其六种具体实现（local、docker、ssh、modal、daytona、singularity）。
- **安全门控**：`tools/approval.py`（危险命令审批）、`agent/file_safety.py`（文件写入安全）、`agent/redact.py`（密钥脱敏）。

^[run_agent.py:122-132], ^[tools/terminal_tool.py:9-12], ^[tools/environments/base.py:213-222]

### 分层边界

层间通信遵循严格的单向依赖：上层可以依赖下层，下层不感知上层。具体体现：
- 用户界面层 → 实例化 `AIAgent` 并传入配置参数 → 核心代理层。^[cli.py:9-13]
- 核心代理层 → 调用 `model_tools.py` 的 `get_tool_definitions()` 和 `handle_function_call()` → 工具与执行层。^[run_agent.py:121-127]
- 核心代理层 → 通过 `_create_environment()` 工厂函数获取环境实例，但对具体后端实现无感知。^[tools/terminal_tool.py:534-585]

平台适配器层作为独立的横切关注点：Gateway 中的 `BasePlatformAdapter` 将外部消息协议规范化为内部 `MessageEvent`，GatewayRunner 再将事件路由到 `AIAgent`，代理本身无感知具体消息平台。^[gateway/run.py:471-480]

---

## 3. 数据流

### 3.1 整体数据流方向

系统整体遵循 **单向数据流** 模式：用户输入 → LLM 推理 → 工具调用 → 结果反馈 → 下一轮迭代，循环直至产生最终答案或预算耗尽。

```text
用户输入 → AIAgent.run_conversation()
         → _build_system_prompt()        # 构建系统提示词
         → assemble api_messages[]        # 组装API消息
         → apply_anthropic_cache_control() # 应用缓存控制
         → ContextCompressor.should_compress()?  # 检查是否需要压缩
         → compress_context() (if needed)        # 压缩上下文
         → interruptible_api_call()       # 调用LLM API
         → tool_calls in response?
            ├─ YES → _execute_tool_calls() → handle_function_call()
            │        → IterationBudget.consume()
            │        → 返回步骤"检查压缩"
            └─ NO  → _persist_session()  # 持久化会话
```

^[agent/conversation_loop.py:1-6], ^[agent/conversation_compression.py:15-18], ^[agent/iteration_budget.py:33-35]

### 3.2 工具调用数据流

工具调用遵循 "Think-Act-Observe" 模式：

1. **LLM 生成工具调用**：LLM 响应中携带 `tool_calls` 数组（JSON 参数）。
2. **参数修复**：`_repair_tool_call_arguments` 修复畸形 JSON（尾随逗号、未闭合括号等）。^[tests/run_agent/test_repair_tool_call_arguments.py:8-143]
3. **分发执行**：`handle_function_call()` 查询 `ToolRegistry.dispatch()`，路由到具体工具处理函数。^[model_tools.py:13]
4. **结果归一化**：工具返回的结果字符串被截断（如果超过 `max_result_size_chars`）。^[tools/registry.py:98-106]
5. **错误分类与恢复**：`classify_api_error` 对 API 错误进行分类，生成包含恢复提示的 `ClassifiedError` 对象。^[agent/error_classifier.py:70-81]

### 3.3 Gateway 消息路由数据流

Gateway 采用了事件驱动架构：

1. 平台适配器接收外部消息 → 规范化为 `MessageEvent`。^[gateway/platforms/base.py:55-77]
2. `GatewayRunner._handle_message()` 解析 `session_id`（基于平台和聊天上下文）。^[gateway/run.py:530-545]
3. 检查 `_running_agents` 缓存：命中则复用，未命中则创建新 `AIAgent`。^[gateway/run.py:550-565]
4. 附加 `GatewayStreamConsumer` 到代理的 `on_delta` 回调实现实时流式输出。^[gateway/stream_consumer.py:79-92]
5. 代理完成会话循环后，通过适配器的 `send_message` 将回复回传到消息平台。^[gateway/run.py:471-480]

### 3.4 子代理委托数据流

子代理以 **完全隔离** 的方式工作，父代理上下文仅见到委托调用和最终摘要：

1. `delegate_task` 接收 `goal` 和可选的 `context`、`toolsets` 参数。^[tools/delegate_tool.py:1012-1019]
2. 生成新的 `task_id`，创建独立的 `AIAgent` 实例（`skip_context_files=True`, `skip_memory=True`）。^[tools/delegate_tool.py:843-845]
3. 通过 `_strip_blocked_tools()` 移除受限工具（阻止递归委托、用户交互、共享记忆写入等）。^[tools/delegate_tool.py:718-724]
4. 批量模式下通过 `ThreadPoolExecutor` 并行执行多个子代理（默认最大并发数 3）。^[tools/delegate_tool.py:27-30]
5. 子代理完成后仅返回 JSON 摘要结果，中间推理和工具调用结果不返回父级。^[tools/delegate_tool.py:15-16]

### 3.5 ACP 协议数据流

IDE 集成通过 JSON-RPC over STDIO 通信：^[acp_adapter/server.py:39-39]

1. 客户端发送 `new_session` → `SessionManager.create_session()` 创建会话并持久化到 `SessionDB`。^[acp_adapter/session.py:209-222]
2. 客户端发送 `prompt` → `HermesACPAgent` 提取文本内容，恢复 `SessionState`，在 `ThreadPoolExecutor` 中执行代理循环。^[acp_adapter/server.py:86-86]
3. 通过 `acp_adapter.events` 回调捕获工具进度、思考块和助手消息，通过 `asyncio.run_coroutine_threadsafe` 发回 IDE。^[acp_adapter/events.py:96-101]

---

## 4. 关注点分离

### 4.1 消息协议与代理逻辑的分离

平台适配器层（`gateway/platforms/`）将 Telegram、Discord、Slack 等各异的消息协议封装在各自适配器中，对外暴露统一的 `MessageEvent`。`AIAgent` 本身完全无感知具体消息平台，仅处理统一的用户消息和会话上下文。^[gateway/platforms/base.py:20-40]

### 4.2 执行环境与工具逻辑的分离

`BaseEnvironment` 抽象执行位置，使得 `terminal_tool`、`read_file`、`write_file` 等工具可以一致地操作文件系统和执行命令，无论实际运行在本地、Docker 容器、远程 SSH 还是云端 Modal 沙箱中。^[tools/environments/base.py:19-21]

工具处理器不感知后端差异，环境选择由 `TERMINAL_ENV` 配置决定。^[tools/terminal_tool.py:9-12]

### 4.3 工具发现与工具执行的分离

工具注册表将工具元数据（schema、handler、可用性检查函数）与工具的实际分发执行解耦。每个工具模块通过自注册模式在导入时声明其接口，`model_tools.py` 仅负责触发发现和提供统一的分发 API。^[model_tools.py:5-9], ^[tools/registry.py:151-167]

### 4.4 安全门控与核心逻辑的分离

安全层作为独立的门控拦截点插入工具执行路径：

- **危险命令检测**：`tools/approval.py` 通过正则模式扫描命令中的破坏性操作，在命令到达执行环境之前拦截。^[tools/approval.py:3-9]
- **文件写入安全**：`agent/file_safety.py` 在 `write_file` 和 `patch` 操作之前检查目标路径，阻止对凭证文件和系统配置的修改。^[agent/file_safety.py:96]
- **密钥脱敏**：`agent/redact.py` 在日志和工具输出离开系统前对 API key 和 token 进行正则掩码。^[agent/redact.py:1-8]
- **技能扫描**：`tools/skills_guard.py` 对所有从 Skills Hub 下载的外部技能执行静态分析，检测数据外泄和提示注入模式。^[tools/skills_guard.py:3-9]

安全审批状态通过 `contextvars.ContextVar` 实现会话隔离，确保一个 Gateway 会话的审批不会影响其他会话。^[tools/approval.py:31-46]

### 4.5 系统提示词组装与代理核心逻辑的分离

系统提示词的各组成部分由 `agent/prompt_builder.py` 中的纯函数生成（persona 身份、记忆引导、技能索引、项目上下文文件、平台提示），与 `AIAgent` 的对话循环逻辑完全解耦。`_build_system_prompt()` 负责组装和缓存，但在检测到目录变更或上下文压缩后自动失效。^[run_agent.py:349-405], ^[agent/prompt_builder.py:1-5]

### 4.6 上下文压缩与对话循环的分离

`ContextCompressor` 独立于对话循环管理上下文窗口溢出。当 token 用量超过阈值（通常为窗口的 85%）时自动触发压缩，使用辅助 LLM 摘要中间轮次，同时保护对话头尾。压缩失败时有确定性回退方案，保留活跃任务和文件路径等连续性锚点。^[agent/context_compressor.py:12-17], ^[agent/context_compressor.py:108-113]

### 4.7 配置层级与运行时逻辑的分离

配置采用明确的优先级层级（CLI 参数 > `config.yaml` > `.env` > 系统默认值），配置加载集中在 `hermes_cli/config.py`。运行时消费方无需感知配置的最终来源。^[hermes_cli/config.py:5-6], ^[hermes_cli/config.py:133-134]

### 4.8 LLM Provider 与代理核心的分离

`agent/auxiliary_client.py` 提供 provider 解析链，将具体 LLM 提供商（OpenRouter、Anthropic、OpenAI 等）的选择逻辑抽象化。主代理通过 `AuxiliaryClient` 执行视觉分析、网页提取、上下文压缩等辅助任务，无需关心具体的后端模型。^[agent/auxiliary_client.py:7-24]

Provider 别名规范化（如 "google" 映射为 "gemini"）确保了路由的一致性。^[agent/auxiliary_client.py:131-162]

### 4.9 技能渐进式披露与提示词构造的分离

技能系统采用渐进式披露模式：`build_skills_system_prompt()` 仅在主提示词中注入技能名称和简短描述（Tier 0）；代理通过 `skills_list` 和 `skill_view` 工具按需获取完整内容（Tier 1-2），大幅降低主提示词的 token 消耗。^[agent/prompt_builder.py:170-176], ^[tools/skills_tool.py:52-67]

### 4.10 会话持久化与会话编排的分离

`SessionDB` 使用 SQLite（WAL 模式）独立管理会话和消息的持久化，提供 FTS5 全文检索和跨 profile 的会话发现。`AIAgent` 的对话循环通过 `_persist_session()` 增量持久化状态，但对话编排逻辑不依赖于具体的存储实现。^[hermes_state.py:9-15], ^[tools/session_search_tool.py:1-30]

---

## 5. 关联

### 与其他 AI Agent 框架的对比

与 LangChain/LangGraph 的 graph-based 编排不同，Hermes Agent 采用 **集中式循环编排** 模式 —— 所有控制流集中在 `AIAgent.run_conversation()` 中，通过 `IterationBudget` 和参数化的工具集配置来控制行为，而非定义显式的有向图。

与 CrewAI/AutoGen 的多代理协作范式不同，Hermes 的子代理委托采用 **隔离式层级委托** 模式 —— 子代理拥有完全独立的上下文和终端会话，仅向父代理返回最终摘要，零上下文成本。

与其他工具的通用工具集成方式不同，Hermes 采用 **自注册式工具发现** —— 工具模块在导入时自行注册到全局单例 `ToolRegistry`，避免了中心化配置文件和手动维护工具列表的开销。

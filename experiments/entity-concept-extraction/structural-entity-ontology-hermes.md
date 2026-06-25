# Hermes-Agent: Structural Entity & Ontology Extraction

> 源：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/`
> 提取日期：2026-06-20
> 版本：v0.9.0（来自 pyproject.toml）

---

## 第一部分：Structural Entity

---

### Entity: AIAgent -- 核心对话循环

**代码位置**：`run_agent.py`（根模块）
**这个模块解决什么问题**：管理完整的 agent 对话循环——组装系统提示、发送请求到 LLM provider、处理 tool call、执行 compressed context handoff、管理 conversation history。
**对外暴露什么**：
- `class AIAgent` ^[run_agent.py:535]：核心 agent 类，接收 model、max_iterations、enabled_toolsets 等参数
- `agent.chat(message)`：主入口，单次对话循环
- `agent.run_conversation(message)`：从 message 开始运行完整对话
- 构造函数接受 callbacks（clarify、sudo、approval）、platform/session_id 路由参数、provider/api_mode 选择
**它和谁交互**：
- 依赖 `model_tools`（tool 编排）^[run_agent.py:63-68]
- 依赖 `agent/memory_manager.py`（MemoryManager 编排 memory provider）^[run_agent.py:78]
- 依赖 `agent/context_compressor.py`（ContextCompressor 做 context compression）^[run_agent.py:94]
- 依赖 `agent/prompt_builder.py`（system prompt 组装）^[run_agent.py:81-97]
- 被 `cli.py`（HermesCLI）、`batch_runner.py`、`gateway/run.py`（GatewayRunner）、`environments/agent_loop.py`（HermesAgentLoop）调用
**为什么它是可分离的**：独立模块（`run_agent.py`），被 4 个不同入口消费（CLI、gateway、batch、RL），通过构造参数配置行为而非硬编码。

**关键机制**（源码可见）：
- **Tool-calling loop**：chat() 内部循环处理 tool_calls，直到 model 不再返回 tool_calls 或达到 max_iterations ^[run_agent.py:535+]
- **Context compression integration**：每次 API 响应后调用 compressor.update_from_response()，每轮后检查 compressor.should_compress()，触发时压缩消息列表并注入压缩摘要 ^[run_agent.py:94]
- **Memory prefetch fencing**：使用 `<memory-context>` XML fence 包裹 memory prefetch 结果，防止 model 将回忆上下文误认为用户指令 ^[agent/memory_manager.py:65-80]
- **Multi-provider credential pool**：通过 agent/credential_pool.py 支持同一 provider 的多个 API key 故障切换 ^[agent/credential_pool.py:1-39]
- **Interrupt handling**：工具调用前检查 `tools/interrupt.py` 的中断信号，允许用户 Ctrl+C 中断长时间运行的工具 ^[tools/terminal_tool.py:55]
- **SafeWriter**：透明 stdio wrapper 捕获 broken pipe 错误，防止 headless 部署时 OSError 崩溃 ^[run_agent.py:113-120]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py`（11510 行）
- 核心类型定义：`class AIAgent` ^[run_agent.py:535]

---

### Entity: Tool Registry -- 中心化工具注册与发现

**代码位置**：`tools/registry.py`
**这个模块解决什么问题**：提供单例注册中心，所有工具模块通过 `registry.register()` 自我注册 schema/handler/元数据，供 `model_tools.py` 查询。消除并行数据结构维护。
**对外暴露什么**：
- `class ToolRegistry` ^[tools/registry.py:100]：单例注册中心
- `registry.register(name, toolset, schema, handler, check_fn, ...)` ^[tools/registry.py:176-228]：工具注册入口
- `registry.deregister(name)` ^[tools/registry.py:229-249]：工具注销（MCP 动态刷新用）
- `registry.get_tool_names_for_toolset(toolset)` ^[tools/registry.py:144-149]
- `registry.get_registered_toolset_names()` ^[tools/registry.py:140-142]
- `registry.dispatch(name, args, task_id, ...)`：分发工具调用到对应 handler
- `discover_builtin_tools(tools_dir)` ^[tools/registry.py:56-73]：通过 AST 扫描发现自注册工具模块
- `class ToolEntry` ^[tools/registry.py:76-98]：单个工具的元数据容器
**它和谁交互**：
- 被所有 `tools/*.py` 文件在模块级调用（23 个工具文件）^[tools/ 目录]
- 被 `model_tools.py` 查询和分发 ^[model_tools.py]
- 被 `tools/mcp_tool.py` 用于动态注册/注销 MCP 工具
**为什么它是可分离的**：独立的 registry.py，无反向依赖，通过 import 链单向流动：`tools/registry.py <- tools/*.py <- model_tools.py <- run_agent.py`。

**关键机制**（源码可见）：
- **AST-based module discovery**：`_module_registers_tools()` 通过 AST 解析 .py 文件检测顶层 `registry.register(...)` 调用，避免导入未注册模块 ^[tools/registry.py:41-53]
- **Thread-safe snapshots**：所有读操作通过 `_snapshot_entries()` / `_snapshot_state()` 获取 RLock 保护的稳定快照，支持 Python 3.13+ free-threading ^[tools/registry.py:110-123]
- **Shadow prevention**：若同名工具已存在且 toolset 不同，拒绝注册（MCP-to-MCP 覆盖除外），防止插件/MCP 意外覆盖内置工具 ^[tools/registry.py:191-213]
- **Toolset alias system**：`register_toolset_alias()` 支持别名映射，解决 toolset 名称歧义 ^[tools/registry.py:151-170]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/registry.py`（482 行）
- 核心类型定义：`class ToolRegistry` ^[tools/registry.py:100]，`class ToolEntry` ^[tools/registry.py:76]

---

### Entity: Toolset System -- 工具分组与场景化组合

**代码位置**：`toolsets.py` + `toolset_distributions.py`
**这个模块解决什么问题**：定义工具的逻辑分组（toolset），支持组合继承（一个 toolset 可包含其他 toolset），支持按场景（research/coding/creative）和按平台（CLI/Telegram/Discord）启用/禁用不同工具集。
**对外暴露什么**：
- `_HERMES_CORE_TOOLS` ^[toolsets.py:31-63]：所有平台共享的核心工具列表（60+ 工具）
- `TOOLSETS` dict ^[toolsets.py:68+]：所有 toolset 定义（含 description、tools、includes）
- `get_toolset(name)` / `resolve_toolset(name)` / `get_all_toolsets()`：toolset 查询 API
- `validate_toolset(name)`：验证 toolset 名称有效性
- `TOOLSET_REQUIREMENTS` ^[toolsets.py]：toolset 的前置依赖检查
- `sample_toolsets_from_distribution(distribution)` ^[toolset_distributions.py]：按分布采样工具集
- `list_distributions()` ^[toolset_distributions.py]：列出所有预定义分布
**它和谁交互**：
- 被 `model_tools.py` 消费，用于 `get_tool_definitions()`
- 被 `batch_runner.py` 使用分布系统 ^[batch_runner.py:39-43]
- 被 `environments/` RL 环境使用分布系统 ^[environments/hermes_base_env.py:72-73]
**为什么它是可分离的**：纯数据模块，定义与消费分离。工具集定义与具体 tool 实现完全解耦。

**关键机制**（源码可见）：
- **Composition via includes**：toolset 可以通过 `includes: ["web", "terminal"]` 组合其他 toolset，resolve_toolset() 递归展开 ^[toolsets.py]
- **Platform-scoped toolset variants**：`hermes-cli`、`hermes-telegram` 等变体从 `_HERMES_CORE_TOOLS` 派生，通过显式的 include/exclude 列表实现平台差异化 ^[toolsets.py:31-63]
- **Distribution-based sampling**：`toolset_distributions.py` 支持多模态工具集分布，用于 batch runner 和 RL 训练时按比例采样不同工具组合 ^[toolset_distributions.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/toolsets.py`（~700 行），`/Users/yuanlimiao/Work/agent_harness/hermes-agent/toolset_distributions.py`
- 核心定义：`_HERMES_CORE_TOOLS` ^[toolsets.py:31]，`TOOLSETS = {...}` ^[toolsets.py:68]

---

### Entity: Model Tools Orchestration -- Tool 编排层

**代码位置**：`model_tools.py`
**这个模块解决什么问题**：薄编排层，触发工具模块发现（import 所有 tools/*.py）、提供 `get_tool_definitions()` / `handle_function_call()` 等公共 API，以及 sync-async 桥接基础设施。
**对外暴露什么**：
- `get_tool_definitions(enabled_toolsets, disabled_toolsets, quiet_mode)` ^[model_tools.py]：获取当前启用的工具 schema 列表
- `handle_function_call(function_name, function_args, task_id, user_task)` ^[model_tools.py]：分发工具调用
- `TOOL_TO_TOOLSET_MAP` ^[model_tools.py]：工具到 toolset 的映射表
- `TOOLSET_REQUIREMENTS` ^[model_tools.py]：toolset 依赖检查
- `check_tool_availability(quiet)` ^[model_tools.py]：检查工具依赖是否满足
- `get_all_tool_names()` / `get_toolset_for_tool(name)` / `get_available_toolsets()`
**它和谁交互**：
- 依赖 `tools/registry.py`（导入并触发发现）^[model_tools.py:29]
- 依赖 `toolsets.py` ^[model_tools.py:30]
- 被 `run_agent.py`、`cli.py`、`batch_runner.py`、`environments/agent_loop.py` 消费
**为什么它是可分离的**：单一的编排文件，是 registry 与 agent 之间的中间层。所有 agent 实例都通过它访问工具系统。

**关键机制**（源码可见）：
- **Persistent event loop for async tools**：使用长期存活的 event loop（而非每次 asyncio.run() 创建/销毁），防止 cached httpx/AsyncOpenAI client 在 dead loop 上 GC 时抛 "Event loop is closed" ^[model_tools.py:39-78]
- **Per-worker-thread event loops**：delegate_task 的 ThreadPoolExecutor 线程各自持有独立长生命周期 loop，避免争用主线程 loop ^[model_tools.py:59-78]
- **Tool discovery trigger**：导入时自动调用 `discover_builtin_tools()` 触发所有 tools/*.py 的 self-registration ^[model_tools.py:29]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/model_tools.py`（~600 行）

---

### Entity: Terminal Execution Environments -- 多后端命令执行

**代码位置**：`tools/environments/` 目录
**这个模块解决什么问题**：提供统一的命令执行抽象，支持 7 种执行后端的可替换切换——本地、Docker、SSH、Modal、Managed Modal、Daytona、Singularity。每个后端实现相同的 `BaseEnvironment` 接口。
**对外暴露什么**：
- `class BaseEnvironment(ABC)` ^[tools/environments/base.py:226]：所有后端的抽象基类
- `class ProcessHandle(Protocol)` ^[tools/environments/base.py:125]：进程句柄协议
- `class _ThreadedProcessHandle` ^[tools/environments/base.py:143]：SDK 后端适配器（Modal/Daytona）
- `LocalEnvironment` ^[tools/environments/local.py]
- `DockerEnvironment` ^[tools/environments/docker.py]
- `SshEnvironment` ^[tools/environments/ssh.py]
- `ModalEnvironment` ^[tools/environments/modal.py]
- `ManagedModalEnvironment` ^[tools/environments/managed_modal.py]
- `DaytonaEnvironment` ^[tools/environments/daytona.py]
- `SingularityEnvironment` ^[tools/environments/singularity.py]
- `FileSyncManager` ^[tools/environments/file_sync.py]：远程后端的文件同步
**它和谁交互**：
- 被 `tools/terminal_tool.py` 实例化和编排 ^[tools/terminal_tool.py]
- 被 `tools/code_execution_tool.py` 用于远程执行（file-based RPC）^[tools/code_execution_tool.py]
- 被 `tools/process_registry.py` 用于后台进程管理 ^[tools/process_registry.py]
**为什么它是可分离的**：独立目录 `tools/environments/`，拥有独立的 ABC 和多实现。用户通过 `TERMINAL_ENV` 环境变量选择后端。

**关键机制**（源码可见）：
- **Session snapshot**：首次命令时捕获 login shell 的 env vars/functions/aliases 到 snapshot 文件，后续命令 source 此文件而非重复 bash -l，大幅加快执行速度 ^[tools/environments/base.py:289-324]
- **Unified spawn-per-call model**：所有后端都是每次命令 spawn 一个新的 `bash -c` 进程，CWD 通过 in-band stdout marker（远程）或 temp file（本地）持久化 ^[tools/environments/base.py:1-6]
- **Stdin heredoc embedding**：Modal/Daytona 等 SDK 后端将 stdin 嵌入为 heredoc，而非 pipe ^[tools/environments/base.py:235]
- **Polymorphic ProcessHandle**：本地子进程用原生 Popen，SDK 后端用 `_ThreadedProcessHandle` 将阻塞调用包装为 subprocess 兼容接口 ^[tools/environments/base.py:143-209]
- **Interrupt-aware polling**：`_wait_for_process()` 在 poll loop 中检查 `is_interrupted()`，若收到中断信号立即 kill 进程 ^[tools/environments/base.py:382-451]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/environments/base.py`（579 行）
- 核心接口：`class BaseEnvironment(ABC)` ^[tools/environments/base.py:226]
- 实现列表：local.py, docker.py, ssh.py, modal.py, managed_modal.py, daytona.py, singularity.py

---

### Entity: Memory Provider System -- 可插拔持久记忆

**代码位置**：`agent/memory_provider.py` + `agent/memory_manager.py` + `plugins/memory/`
**这个模块解决什么问题**：提供跨 session 的持久记忆，内置提供 MEMORY.md/USER.md 文件存储，支持最多一个外部 memory provider plugin（如 Honcho 辩证记忆、Hindsight 等）。
**对外暴露什么**：
- `class MemoryProvider(ABC)` ^[agent/memory_provider.py:42]：memory provider 抽象基类
- `class MemoryManager` ^[agent/memory_manager.py:83]：编排器，管理内置 + 外部 provider
- `BuiltinMemoryProvider`（内置）：基于文件的 MEMORY.md / USER.md
- 8 个外部 plugin：honcho, hindsight, mem0, holographic, supermemory, openviking, byterover, retaindb ^[plugins/memory/ 目录]
- `discover_memory_providers()` ^[plugins/memory/__init__.py:122]：扫描 bundled + user-installed providers
- `load_memory_provider(name)` ^[plugins/memory/__init__.py:159]：按名称加载 provider 实例
**它和谁交互**：
- 被 `run_agent.py` 通过 MemoryManager 单点集成 ^[agent/memory_manager.py:12-17]
- 通过 `on_memory_write()` hook 与 `tools/memory_tool.py` 同步 ^[agent/memory_provider.py:223-231]
- 被 `hermes memory setup` CLI 命令用于交互式配置 ^[plugins/memory/__init__.py:322-406]
**为什么它是可分离的**：独立的 ABC 文件 + 独立 plugin 目录。provider 通过 config（`memory.provider`）选择，最多一个外部 provider。

**关键机制**（源码可见）：
- **Provider lifecycle hooks**：`initialize()` -> `prefetch()` per-turn -> `sync_turn()` per-turn -> `on_session_end()` -> `shutdown()`，覆盖完整的 session 生命周期 ^[agent/memory_provider.py:16-31]
- **Optional hooks for deep integration**：`on_pre_compress()`（压缩前提取信息）、`on_delegation()`（观察子 agent 工作）、`on_memory_write()`（镜像内置 memory 写入）^[agent/memory_provider.py:142-231]
- **Context fencing**：`build_memory_context_block()` 用 `<memory-context>` XML fence 包裹 prefetch 结果，防止 model 将回忆视为用户指令 ^[agent/memory_manager.py:65-80]
- **Single external provider enforcement**：MemoryManager 只允许一个外部 provider，防止 tool schema bloat 和 backend 冲突 ^[agent/memory_manager.py:8-10]
- **Dual-source discovery**：bundled（`plugins/memory/<name>/`）和 user-installed（`$HERMES_HOME/plugins/<name>/`），bundled 优先 ^[plugins/memory/__init__.py:66-97]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/memory_provider.py`（231 行），`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/memory_manager.py`，`/Users/yuanlimiao/Work/agent_harness/hermes-agent/plugins/memory/__init__.py`（407 行）
- 核心接口：`class MemoryProvider(ABC)` ^[agent/memory_provider.py:42]
- 实现列表：`plugins/memory/` 下 8 个子目录

---

### Entity: Context Engine -- 上下文压缩引擎

**代码位置**：`agent/context_engine.py` + `agent/context_compressor.py` + `plugins/context_engine/`
**这个模块解决什么问题**：当对话长度逼近 model token limit 时自动压缩上下文。内置 ContextCompressor 用辅助模型摘要中间轮次，第三方引擎（如 LCM）可通过 plugin 系统替换。
**对外暴露什么**：
- `class ContextEngine(ABC)` ^[agent/context_engine.py:32]：所有 context engine 的抽象基类
- `class ContextCompressor(ContextEngine)` ^[agent/context_compressor.py:185]：内置默认实现
- `discover_context_engines()` ^[plugins/context_engine/__init__.py:33]：扫描可用引擎
- `load_context_engine(name)` ^[plugins/context_engine/__init__.py:79]：按名称加载引擎实例
**它和谁交互**：
- 被 `run_agent.py` 在每轮后调用 `should_compress()` / `compress()` ^[run_agent.py:94]
- 被 `gateway/run.py` 在 messaging session 中使用
- 通过 `plugins/context_engine/` 发现机制与第三方引擎集成
**为什么它是可分离的**：独立的 ABC + 独立 plugin 目录。引擎通过 config（`context.engine`）选择，只有一个活跃。

**关键机制**（源码可见）：
- **Structured summary template**：压缩模板包含 Resolved/Pending question tracking、"Remaining Work"（非 active instruction）、handoff framing（"different assistant"）^[agent/context_compressor.py:16-18]
- **Token-budget tail protection**：不是按固定消息数保留尾部，而是按 token budget 保护最近的对话 ^[agent/context_compressor.py:14]
- **Scaled summary budget**：摘要 token budget 按压缩内容的比例计算（20%），有绝对上限防止超长摘要 ^[agent/context_compressor.py:51-53]
- **Tool output pruning pre-pass**：在 LLM 摘要化之前先对 tool output 做 pre-pass pruning，用简洁的单行描述替换大型 tool 结果，减少摘要化 cost ^[agent/context_compressor.py:63-80]
- **Summary failure cooldown**：摘要化失败后有 600 秒的冷却期，防止重复失败 ^[agent/context_compressor.py:60]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/context_engine.py`（184 行），`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/context_compressor.py`（1091 行）
- 核心接口：`class ContextEngine(ABC)` ^[agent/context_engine.py:32]

---

### Entity: Messaging Gateway -- 多平台消息网关

**代码位置**：`gateway/` 目录
**这个模块解决什么问题**：统一的消息收发网关，连接 20+ 消息平台（Telegram/Discord/Slack/WhatsApp/Signal 等），每个平台通过 adapter 集成，共享 session 管理、slash command 处理、cron delivery。
**对外暴露什么**：
- `class GatewayRunner` ^[gateway/run.py:538]：网关主循环，启动所有已配置 platform adapter
- `class SessionStore` ^[gateway/session.py:498]：gateway 会话持久化
- `class BasePlatformAdapter(ABC)` ^[gateway/platforms/base.py:813]：所有平台 adapter 的基类
- `class MessageEvent` / `class SendResult` ^[gateway/platforms/base.py]
- `class HookRegistry` ^[gateway/hooks.py:34]：事件 hook 系统（gateway:startup / session:start / agent:start 等）
- `delivery.py`：cron 结果向各平台投递
- `pairing.py`：DM pairing 安全机制
- `channel_directory.py`：频道目录管理
**它和谁交互**：
- 依赖 `run_agent.py`（AIAgent）处理消息
- 依赖 `cron/scheduler.py` 的 cron delivery
- 依赖 `hermes_state.py`（SessionDB）的 session 存储
- 被 `hermes_cli/main.py` 通过 `hermes gateway` 子命令启动
**为什么它是可分离的**：独立的 `gateway/` 目录，有自己的 main loop、session 管理、hook 系统。与 CLI 完全分离的入口路径。

**关键机制**（源码可见）：
- **20+ platform adapters**：telegram, discord, slack, whatsapp, signal, matrix, mattermost, homeassistant, dingtalk, feishu, wecom, weixin, sms, email, webhook, bluebubbles, qqbot, telegram_network ^[gateway/platforms/ 目录]
- **Event hook pipeline**：`gateway:startup` / `session:start` / `session:end` / `agent:start` / `agent:step` / `agent:end` / `command:*`，hooks 从 `~/.hermes/hooks/` 目录发现 ^[gateway/hooks.py:7-20]
- **DM pairing security**：防止未授权用户通过 DM 控制 agent ^[gateway/pairing.py]
- **Cron delivery resolution**：根据 cron job 的 origin/target 将 agent 响应投递到正确的 platform + chat_id ^[cron/scheduler.py:67-76]
- **Multi-session concurrency**：gateway 支持同时处理多个聊天会话，每个 chat_id 独立 session ^[gateway/session.py:498]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/run.py`（~1500 行）
- 核心接口：`class BasePlatformAdapter(ABC)` ^[gateway/platforms/base.py:813]（2133 行）
- 平台 adapter 列表：`gateway/platforms/` 下 20+ 个 .py 文件
- 扩展指南：`gateway/platforms/ADDING_A_PLATFORM.md`

---

### Entity: ACP Adapter -- Agent Client Protocol 服务器

**代码位置**：`acp_adapter/` 目录
**这个模块解决什么问题**：通过 Agent Client Protocol 将 Hermes Agent 暴露给 VS Code / Zed / JetBrains 等编辑器，实现编辑器内 agent 集成。
**对外暴露什么**：
- `acp_adapter/server.py`：ACP server 实现，处理 session CRUD、prompt 处理、tool call 代理
- `acp_adapter/entry.py`：入口点（`hermes-acp` CLI 命令）
- `acp_adapter/session.py`：`SessionManager` / `SessionState` ^[acp_adapter/session.py]
- `acp_adapter/auth.py`：provider 检测和认证 ^[acp_adapter/auth.py]
- `acp_adapter/permissions.py`：approval callback 适配 ^[acp_adapter/permissions.py]
- `acp_adapter/events.py`：ACP 事件回调（message/step/thinking/tool_progress）^[acp_adapter/events.py]
- `acp_adapter/tools.py`：工具能力暴露 ^[acp_adapter/tools.py]
**它和谁交互**：
- 依赖 `run_agent.py`（AIAgent）在 ThreadPoolExecutor 中运行 ^[acp_adapter/server.py:70]
- 通过 `acp` Python 包与编辑器通信 ^[acp_adapter/server.py:11-44]
- 被 `hermes acp` CLI 子命令启动
**为什么它是可分离的**：独立目录 `acp_adapter/`，有独立的 pyproject entry point（`hermes-acp`），可选依赖（`.[acp]` extra）。

**关键机制**（源码可见）：
- **Thread pool isolation**：每个 AIAgent 在 ThreadPoolExecutor 中运行，ACP server 保持异步 ^[acp_adapter/server.py:70]
- **Session lifecycle**：支持 session 创建/恢复/分叉/列表，model 和 mode 切换 ^[acp_adapter/server.py]
- **Approval callback bridge**：将 ACP 权限请求适配到 Hermes 的 approval 机制 ^[acp_adapter/permissions.py]
- **Provider detection**：自动检测可用的 LLM provider ^[acp_adapter/auth.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/acp_adapter/entry.py`
- 核心实现：`acp_adapter/server.py` ^[acp_adapter/server.py]
- ACP registry：`acp_registry/agent.json`（ACP 协议注册描述符）

---

### Entity: Cron Scheduler -- 定时任务调度

**代码位置**：`cron/` 目录
**这个模块解决什么问题**：内置的 cron 调度器，支持自然语言创建定时任务，任务由 AIAgent 在指定时间执行，结果投递到配置的消息平台。
**对外暴露什么**：
- `cron/scheduler.py` ^[cron/scheduler.py]：调度引擎（`tick()` 检查到期任务并执行）
- `cron/jobs.py` ^[cron/jobs.py]：任务存储和管理（`get_due_jobs()`, `mark_job_run()`, `save_job_output()`, `advance_next_run()`）
- `tools/cronjob_tools.py`：暴露给 agent 的 cron 管理工具（list/create/delete cron jobs）
**它和谁交互**：
- 被 `gateway/run.py` 通过后台线程每 60 秒调用 `tick()`
- 依赖 `run_agent.py`（AIAgent）执行任务
- 依赖 `gateway/delivery.py` 投递结果
- 通过 `cron/jobs.py` 读写 `~/.hermes/cron/jobs.json`
**为什么它是可分离的**：独立目录 `cron/`，有独立的数据存储（jobs.json），可选依赖（`.[cron]` extra）。

**关键机制**（源码可见）：
- **File-based tick lock**：`~/.hermes/cron/.tick.lock` 防止多进程并发执行 tick ^[cron/scheduler.py:63-64]
- **SILENT marker**：若 cron agent 响应以 `[SILENT]` 开头，跳过消息投递（仍保存本地审计）^[cron/scheduler.py:55-56]
- **Known delivery platform allowlist**：`_KNOWN_DELIVERY_PLATFORMS` frozenset 验证投递目标，防止 env var 枚举攻击 ^[cron/scheduler.py:45-50]
- **Croniter integration**：使用 croniter 解析 cron 表达式，计算下次执行时间 ^[cron/jobs.py:24-28]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/scheduler.py`
- 核心文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/jobs.py`

---

### Entity: SessionDB -- SQLite Session Store

**代码位置**：`hermes_state.py`
**这个模块解决什么问题**：提供基于 SQLite 的持久化 session 存储，含 FTS5 全文搜索，支持 CLI 和 gateway 的所有 session 数据（消息历史、token 使用、model 配置、cost 追踪）。
**对外暴露什么**：
- `class SessionDB` ^[hermes_state.py:115]：核心 session 数据库类
- FTS5 虚拟表实现全文搜索
- Schema versioning（当前 v6）和自动迁移
- Session source tag（'cli', 'telegram', 'discord', ...）过滤
- Compression-triggered session splitting（parent_session_id 链）
**它和谁交互**：
- 被 `cli.py`（HermesCLI）和 `gateway/`（GatewayRunner）使用
- 被 `agent/trajectory.py` 用于保存 trajectory
- 被 `hermes_cli/sessions` 子命令用于 session 浏览和搜索
**为什么它是可分离的**：独立的单文件模块（`hermes_state.py`，~1300 行），有自己的 schema 管理。

**关键机制**（源码可见）：
- **WAL mode**：支持 concurrent readers + one writer，满足 gateway 多平台并发需求 ^[hermes_state.py:12]
- **FTS5 full-text search**：跨所有 session 消息的快速文本搜索 ^[hermes_state.py:14]
- **Schema migration chain**：v1 -> v6 的逐步迁移，每步可回滚 ^[hermes_state.py:34]
- **Session splitting**：当 context compression 触发时，通过 parent_session_id 链连接分段 session ^[hermes_state.py:13]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/hermes_state.py`（~1300 行）
- 核心类型：`class SessionDB` ^[hermes_state.py:115]

---

### Entity: Hermes CLI -- 命令行界面

**代码位置**：`hermes_cli/` 目录 + `cli.py`
**这个模块解决什么问题**：完整的 CLI 系统——交互式聊天界面、多子命令、配置管理、模型选择、gateway 管理、session 浏览、皮肤引擎。
**对外暴露什么**：
- `class HermesCLI` ^[cli.py:1577]：交互式 TUI 聊天界面
- `hermes_cli/main.py`：入口点，所有 `hermes` 子命令 ^[hermes_cli/main.py]
- `hermes_cli/config.py`：`DEFAULT_CONFIG`, `OPTIONAL_ENV_VARS`, 配置迁移
- `hermes_cli/commands.py`：slash command 定义和 SlashCommandCompleter
- `hermes_cli/callbacks.py`：终端回调（clarify, sudo, approval）
- `hermes_cli/setup.py`：交互式设置向导
- `hermes_cli/skin_engine.py`：皮肤/主题引擎
- `hermes_cli/models.py`：模型目录和 provider 列表
- `hermes_cli/auth.py`：provider 凭证解析
- `hermes_cli/gateway.py`：gateway 管理子命令
- `hermes_cli/cron.py`：cron 管理子命令
- `hermes_cli/doctor.py`：诊断工具
- 等 30+ 个模块
**它和谁交互**：
- 依赖 `run_agent.py`（AIAgent）执行对话 ^[cli.py]
- 依赖 `gateway/run.py` 管理 gateway 生命周期 ^[hermes_cli/gateway.py]
- 依赖 `model_tools.py` 获取工具信息 ^[cli.py]
- 依赖 `hermes_state.py`（SessionDB）管理 session ^[cli.py]
**为什么它是可分离的**：独立包目录 `hermes_cli/`（50+ 模块），通过 `pyproject.toml` 注册为 `hermes` CLI entry point ^[pyproject.toml:118]。

**关键机制**（源码可见）：
- **Multiline TUI with prompt_toolkit**：支持多行编辑、slash-command 自动补全、conversation history、interrupt-and-redirect ^[cli.py:1577]
- **Streaming tool output**：实时显示工具执行输出 ^[agent/display.py]
- **Skin/theme engine**：可插拔的 CLI 视觉主题系统 ^[hermes_cli/skin_engine.py]
- **Config migration**：自动检测和迁移旧版本配置格式 ^[hermes_cli/config.py]
- **Provider credential resolution**：多层级凭证解析（env var -> .env -> config.yaml -> OAuth token）^[hermes_cli/auth.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/hermes_cli/main.py`
- 核心 TUI：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/cli.py`（~11000 行）

---

### Entity: MCP Client -- Model Context Protocol 集成

**代码位置**：`tools/mcp_tool.py`
**这个模块解决什么问题**：连接外部 MCP server（通过 stdio 或 HTTP/StreamableHTTP transport），发现其工具，注册到 Hermes 工具注册表，使 agent 可以像调用内置工具一样调用 MCP 工具。
**对外暴露什么**：
- MCP server 连接管理、tool discovery、tool 注册
- Stdio transport（command + args）和 HTTP transport（url + headers）
- Automatic reconnection with exponential backoff
- Sampling 支持（MCP server 可请求 LLM completion）
- Thread-safe 架构：dedicated background event loop
**它和谁交互**：
- 依赖 `tools/registry.py`（registry.register/deregister）^[tools/mcp_tool.py]
- 依赖 `mcp` Python 包（可选依赖 `.[mcp]` extra）
- 被 `model_tools.py` 在 tool discovery 时触发
**为什么它是可分离的**：独立文件（~1050 行），可选依赖，通过 config（`mcp_servers` key）配置。

**关键机制**（源码可见）：
- **Dedicated background event loop**：每个 MCP server 作为长期存活的 asyncio Task 运行，避免每次 tool call 重新连接 ^[tools/mcp_tool.py:56-59]
- **Thread-safe server lifecycle**：`_servers` 和 `_mcp_loop` 由 RLock 保护，支持 Python 3.13+ free-threading ^[tools/mcp_tool.py:65-69]
- **Shutdown coordination**：shutdown 时通知每个 server Task 退出其 `async with` block，确保 anyio cancel-scope cleanup 在同一 Task 中完成 ^[tools/mcp_tool.py:61-63]
- **Sampling support**：MCP server 可通过 `sampling/createMessage` 向 Hermes 请求 LLM completion，支持 model override、token cap、rate limiting ^[tools/mcp_tool.py:35-43]
- **Credential stripping**：返回给 LLM 的错误消息中自动剥离敏感凭证 ^[tools/mcp_tool.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/mcp_tool.py`（~1050 行）

---

### Entity: Delegate/Subagent System -- 子 Agent 委派

**代码位置**：`tools/delegate_tool.py`
**这个模块解决什么问题**：允许 agent 生成隔离的子 agent 实例，用于并行工作流。每个子 agent 有独立的 context、工具集和 terminal session，父 agent 只看到委派调用和摘要结果。
**对外暴露什么**：
- `delegate_task()` tool handler
- `DELEGATE_BLOCKED_TOOLS` ^[tools/delegate_tool.py:32-38]：子 agent 禁止使用的工具
- `MAX_DEPTH = 2` ^[tools/delegate_tool.py:53]：最大嵌套深度（父->子->孙拒绝）
- `_SUBAGENT_TOOLSETS` ^[tools/delegate_tool.py:44-49]：子 agent 可用的 toolset 列表
- `_get_max_concurrent_children()` ^[tools/delegate_tool.py:56-79]：并发度控制
**它和谁交互**：
- 依赖 `run_agent.py`（AIAgent）创建子 agent 实例 ^[tools/delegate_tool.py]
- 通过 `ThreadPoolExecutor` 实现并行子 agent ^[tools/delegate_tool.py]
- 通过 `memory_manager.on_delegation()` 让父 agent memory 观察子 agent 工作
**为什么它是可分离的**：独立文件，自包含的子 agent 生成逻辑。

**关键机制**（源码可见）：
- **Context isolation**：子 agent 获得全新 conversation（无父 history）、独立 task_id（独立 terminal session/file cache）、受限 toolset（blocked tools 强制移除）^[tools/delegate_tool.py:7-17]
- **Blocked tools**：delegate_task（禁止递归）、clarify（禁止用户交互）、memory（禁止写共享 MEMORY.md）、send_message（禁止跨平台副作用）、execute_code（子 agent 应逐步推理而非写脚本）^[tools/delegate_tool.py:32-38]
- **Depth limiting**：MAX_DEPTH=2，父（0）->子（1）->孙被拒绝 ^[tools/delegate_tool.py:53]
- **Concurrency control**：通过 delegation.max_concurrent_children config 控制并行度，默认 3 ^[tools/delegate_tool.py:52-79]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/delegate_tool.py`（~700 行）

---

### Entity: Code Execution Sandbox -- 编程式工具调用

**代码位置**：`tools/code_execution_tool.py`
**这个模块解决什么问题**：让 LLM 写 Python 脚本通过 RPC 调用 Hermes 工具，将多步工具链压缩为一次推理轮次。支持 local（Unix domain socket）和 remote（file-based RPC）两种 transport。
**对外暴露什么**：
- `execute_code()` tool handler ^[tools/code_execution_tool.py]
- `SANDBOX_ALLOWED_TOOLS` ^[tools/code_execution_tool.py:56-60]：沙箱内允许的工具白名单
- 两种 RPC transport：UDS（local）和 file-based（remote backend）
**它和谁交互**：
- 依赖 `model_tools.py`（handle_function_call）进行工具分发 ^[tools/code_execution_tool.py]
- 依赖 `tools/environments/`（remote 模式下通过 env.execute() 通信）^[tools/code_execution_tool.py]
- 被 `terminal_tool.py` 通过 env 接口间接使用
**为什么它是可分离的**：独立文件，自包含的沙箱执行逻辑，支持两种 transport 模式。

**关键机制**（源码可见）：
- **Dual transport architecture**：local 用 Unix domain socket RPC，remote 用文件轮询 RPC，自动根据执行环境选择 ^[tools/code_execution_tool.py:8-24]
- **Tool allowlisting**：沙箱内只允许 7 个工具（web_search, web_extract, read_file, write_file, ...），阻止危险操作 ^[tools/code_execution_tool.py:56-60]
- **Zero context cost**：只有脚本 stdout 返回给 LLM，中间工具结果永不进入 context window ^[tools/code_execution_tool.py:24-25]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/code_execution_tool.py`（~800 行）

---

### Entity: Process Registry -- 后台进程管理

**代码位置**：`tools/process_registry.py`
**这个模块解决什么问题**：内存中的后台进程注册表，跟踪通过 `terminal(background=true)` 生成的进程，提供 output buffering、状态轮询、blocking wait、进程 kill、崩溃恢复。
**对外暴露什么**：
- `class ProcessRegistry` ^[tools/process_registry.py:106]：核心注册表
- `process_registry.spawn(env, command, task_id)` ^[tools/process_registry.py]：生成后台进程
- `process_registry.poll(session_id)` / `process_registry.wait(session_id)` / `process_registry.kill(session_id)`
- Session-scoped tracking（gateway reset 保护）
- JSON checkpoint file 崩溃恢复
**它和谁交互**：
- 被 `tools/terminal_tool.py` 调用（spawn/poll/wait/kill）^[tools/terminal_tool.py]
- 依赖 `tools/environments/`（通过 env 接口执行命令）
- 通过 `tools/process_registry` 工具暴露给 agent
**为什么它是可分离的**：独立模块，自包含的进程生命周期管理。

**关键机制**（源码可见）：
- **Rolling output buffer**：200KB 滚动窗口缓冲后台进程输出 ^[tools/process_registry.py:5]
- **Session-scoped tracking**：进程按 session_id 分组，gateway reset 时清理过期 session 的进程
- **Crash recovery**：通过 JSON checkpoint 文件在重启后恢复进程状态 ^[tools/process_registry.py:9]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/process_registry.py`（~400 行）
- 核心类型：`class ProcessRegistry` ^[tools/process_registry.py:106]

---

### Entity: Batch Runner -- 并行批处理

**代码位置**：`batch_runner.py`
**这个模块解决什么问题**：跨数据集并行运行 agent，支持 multiprocessing、checkpointing 容错恢复、trajectory 保存、工具使用统计聚合。用于批量 trajectory 生成和评估。
**对外暴露什么**：
- `batch_runner.py` CLI（通过 `python batch_runner.py --dataset_file=... --batch_size=...`）
- `ALL_POSSIBLE_TOOLS` ^[batch_runner.py:54]：所有可能工具的集合
- Dataset loading/batching、checkpointing、tool stats aggregation
**它和谁交互**：
- 依赖 `run_agent.py`（AIAgent）^[batch_runner.py:38]
- 依赖 `toolset_distributions.py` ^[batch_runner.py:39-43]
- 依赖 `model_tools.py`（TOOL_TO_TOOLSET_MAP）^[batch_runner.py:44]
**为什么它是可分离的**：独立的单文件模块（~1100 行），通过 `multiprocessing.Pool` 实现并行。

**关键机制**（源码可见）：
- **Multiprocessing with Pool**：使用 `multiprocessing.Pool` 实现真正的并行批处理 ^[batch_runner.py:30]
- **Checkpointing for fault tolerance**：保存每个 batch 的处理状态，支持 `--resume` 恢复中断的运行 ^[batch_runner.py:11]
- **Tool stats normalization**：`_normalize_tool_stats()` 将所有可能工具的统计补齐，确保 HuggingFace datasets 加载 JSONL 时不出现 schema mismatch ^[batch_runner.py:60-80]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/batch_runner.py`（~1100 行）

---

### Entity: RL Environments -- 强化学习训练环境

**代码位置**：`environments/` 目录
**这个模块解决什么问题**：基于 Atropos RL 框架的训练环境，支持在 SWE-bench、Web Research、TerminalBench 等 benchmark 上训练 agent tool-calling 能力。通过 toolset distribution 采样和 tool call parser 支持多种 model。
**对外暴露什么**：
- `class HermesAgentBaseEnv(BaseEnv)` ^[environments/hermes_base_env.py:221]：所有环境的抽象基类
- `class HermesAgentLoop` ^[environments/agent_loop.py:119]：可复用的多轮 agent 引擎
- `class ToolContext` ^[environments/tool_context.py]：reward 函数的工具上下文
- SWE-bench 环境：`environments/hermes_swe_env/`
- Web Research 环境：`environments/web_research_env.py`
- Agentic OPD 环境：`environments/agentic_opd_env.py`
- Terminal Test 环境：`environments/terminal_test_env/`
- 11 个 tool call parser：`environments/tool_call_parsers/` ^[environments/tool_call_parsers/ 目录]
- 3 个 benchmark：tblite, terminalbench_2, yc_bench ^[environments/benchmarks/]
**它和谁交互**：
- 依赖 `atroposlib`（Atropos RL 框架）^[environments/hermes_base_env.py:50-61]
- 依赖 `model_tools.py`（tool definitions）^[environments/hermes_base_env.py:72]
- 依赖 `toolset_distributions.py`（分布采样）^[environments/hermes_base_env.py:73]
- 被 `rl_cli.py` 通过 CLI 入口启动
**为什么它是可分离的**：独立目录 `environments/`，可选依赖（`.[rl]` extra），通过 Atropos config 驱动。

**关键机制**（源码可见）：
- **Two-mode operation**：Phase 1 用 OpenAI server（标准 API），Phase 2 用 VLLM ManagedServer + client-side tool call parser ^[environments/hermes_base_env.py:5-8]
- **Per-group toolset/distribution resolution**：不同 rollout group 可使用不同工具集分布 ^[environments/hermes_base_env.py:6]
- **Tool call parsers for multiple model families**：deepseek_v3, glm45/47, hermes, kimi_k2, llama, longcat, mistral, qwen, qwen3_coder ^[environments/tool_call_parsers/ 目录]
- **Monkey patches for async safety**：`environments/patches.py` 确保 tool 在 Atropos event loop 内安全运行 ^[environments/hermes_base_env.py:47-48]
- **Tool thread pool resizing**：`resize_tool_pool()` 在运行时动态调整并发度 ^[environments/agent_loop.py:36-47]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/environments/hermes_base_env.py`
- 核心类型：`class HermesAgentBaseEnv(BaseEnv)` ^[environments/hermes_base_env.py:221]，`class HermesAgentLoop` ^[environments/agent_loop.py:119]

---

### Entity: Cloud Browser Providers -- 云端浏览器自动化

**代码位置**：`tools/browser_providers/` 目录 + `tools/browser_tool.py`
**这个模块解决什么问题**：通过云端浏览器服务（Browserbase 等）提供浏览器自动化能力，允许 agent 导航网页、截图、点击、输入等操作。
**对外暴露什么**：
- `class CloudBrowserProvider(ABC)` ^[tools/browser_providers/base.py:7]：所有浏览器后端的抽象基类
- Browserbase provider ^[tools/browser_providers/browserbase.py]
- BrowserUse provider ^[tools/browser_providers/browser_use.py]
- Firecrawl provider ^[tools/browser_providers/firecrawl.py]
- `tools/browser_tool.py`：浏览器工具 handler（browser_navigate, browser_snapshot, browser_click, ...）
- `tools/browser_camofox.py` + `tools/browser_camofox_state.py`：Camofox 本地浏览器集成
**它和谁交互**：
- 通过 `tools/browser_tool.py` 向 agent 暴露浏览器操作工具
- provider 选择通过 `config["browser"]["cloud_provider"]` 配置
**为什么它是可分离的**：独立子目录 `tools/browser_providers/`，拥有独立的 ABC 和多实现。

**关键机制**（源码可见）：
- **Provider registry pattern**：provider 在 `browser_tool._PROVIDER_REGISTRY` 中注册，用户通过 config 选择 ^[tools/browser_providers/base.py:11-13]
- **Session lifecycle**：`create_session()` -> use -> `close_session()` + `emergency_cleanup()`（atexit）^[tools/browser_providers/base.py:28-59]
- **CDP websocket**：provider 返回 CDP URL 给 agent-browser 连接 ^[tools/browser_providers/base.py:37]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/browser_providers/base.py`（59 行）
- 核心接口：`class CloudBrowserProvider(ABC)` ^[tools/browser_providers/base.py:7]
- 实现列表：browserbase.py, browser_use.py, firecrawl.py

---

### Entity: Skills System -- 渐进式技能系统

**代码位置**：`tools/skills_tool.py` + `skills/` 目录 + `optional-skills/` 目录
**这个模块解决什么问题**：progressive disclosure 技能系统——agent 在执行任务时按需加载技能指令。技能以 SKILL.md + YAML frontmatter 格式存储，遵循 agentskills.io 开放标准。
**对外暴露什么**：
- `tools/skills_tool.py`：skills_list（列出技能元数据）、skill_view（加载完整技能内容）、skill_manage
- `tools/skill_manager_tool.py`：技能管理工具
- `tools/skills_hub.py`：agentskills.io hub 集成（搜索、浏览、安装）
- `tools/skills_sync.py`：技能同步
- `tools/skills_guard.py`：技能安全守卫
- `skills/` 目录：26 个技能类别（apple, data-science, devops, gaming, github, mlops, ...）^[skills/ 目录]
- `optional-skills/` 目录：14 个可选技能类别（blockchain, health, security, ...）^[optional-skills/ 目录]
- `agent/skill_utils.py`：技能工具函数（frontmatter 解析、条件匹配）
- `agent/skill_commands.py`：技能 slash commands
**它和谁交互**：
- 被 `agent/prompt_builder.py` 注入到 system prompt ^[agent/prompt_builder.py]
- 被 `run_agent.py` 和 `gateway/` 消费
- 被 `hermes_cli/skills_hub.py` CLI 管理
**为什么它是可分离的**：独立的 `skills/` + `optional-skills/` 目录，技能与 agent 核心逻辑完全分离，遵循开放标准。

**关键机制**（源码可见）：
- **Three-tier progressive disclosure**：Tier 1 元数据（name ≤64 chars, description ≤1024 chars）-> Tier 2 完整指令（SKILL.md）-> Tier 3 关联文件（references/templates/assets）^[tools/skills_tool.py:9-13]
- **YAML frontmatter**：与 agentskills.io 标准兼容的前置元数据（name, description, version, license, platforms, prerequisites）^[tools/skills_tool.py:28-46]
- **Platform-gated skills**：技能可通过 `platforms: [macos]` 限制在特定 OS ^[tools/skills_tool.py:34-36]
- **Auto-skill creation**：agent 完成复杂任务后可自主创建技能 ^[tools/skill_manager_tool.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/skills_tool.py`
- 技能目录：`skills/`（26 类别），`optional-skills/`（14 类别）

---

### Entity: Trajectory Compressor -- 轨迹压缩器

**代码位置**：`trajectory_compressor.py`
**这个模块解决什么问题**：将完整的多轮 tool-calling 轨迹压缩为训练格式，去除冗余工具输出，保留关键推理链。用于生成下一代 tool-calling model 的训练数据。
**对外暴露什么**：
- `trajectory_compressor.py` CLI 工具
- 轨迹压缩/过滤/格式转换逻辑
**它和谁交互**：
- 消费 `run_agent.py` 和 `batch_runner.py` 生成的轨迹数据
- 产出用于训练的压缩轨迹格式
**为什么它是可分离的**：独立的单文件模块（~1700 行），独立的 CLI 入口。

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/trajectory_compressor.py`（~1700 行）

---

### Entity: Cloud Browser Providers -- 云端浏览器自动化

> （此 Entity 在前文已描述，此处重申以明确其在 Ontology 中的归属）

---

### Entity: Event Hook System -- 生命周期事件钩子

**代码位置**：`gateway/hooks.py` + `gateway/builtin_hooks/`
**这个模块解决什么问题**：轻量级事件驱动系统，在 agent/gateway 生命周期关键点触发用户可自定义的 handler。hooks 从 `~/.hermes/hooks/` 目录发现。
**对外暴露什么**：
- `class HookRegistry` ^[gateway/hooks.py:34]：发现、加载、触发 event hooks
- 事件类型：`gateway:startup`, `session:start`, `session:end`, `agent:start`, `agent:step`, `agent:end`, `command:*` ^[gateway/hooks.py:9-17]
- `gateway/builtin_hooks/boot_md.py`：内置 hook（gateway 启动时执行 `~/.hermes/BOOT.md`）
**它和谁交互**：
- 被 `gateway/run.py` 在关键生命周期点调用
- hook 目录结构：`HOOK.yaml`（元数据）+ `handler.py`（async def handle）^[gateway/hooks.py:75-78]
**为什么它是可分离的**：独立的 hook 注册和触发系统，用户可扩展。

**关键机制**（源码可见）：
- **Error isolation**：hook 中的错误被捕获和记录，但绝不阻塞主 pipeline ^[gateway/hooks.py:19]
- **Wildcard command matching**：`command:*` 事件匹配所有 slash command ^[gateway/hooks.py:17]
- **Builtin hook**：boot-md hook 在 gateway 启动时执行 `~/.hermes/BOOT.md` 中的指令 ^[gateway/builtin_hooks/boot_md.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/hooks.py`
- 核心类型：`class HookRegistry` ^[gateway/hooks.py:34]

---

### Entity: Credential Pool -- 多凭证故障切换

**代码位置**：`agent/credential_pool.py`
**这个模块解决什么问题**：为同一 LLM provider 管理多个 API key，支持基于速率限制和错误的自动故障切换，提高 agent 可用性。
**对外暴露什么**：
- 多凭证管理、故障切换逻辑
- 速率限制追踪（rate_limit_tracker.py）
- 错误分类和 failover reason 决策（error_classifier.py）
**它和谁交互**：
- 被 `run_agent.py`（AIAgent）在 API 调用时使用 ^[run_agent.py]
- 依赖 `hermes_cli/auth.py` 的 PROVIDER_REGISTRY 和 auth store ^[agent/credential_pool.py:17-35]
- 依赖 `agent/rate_limit_tracker.py` 追踪速率限制 ^[agent/rate_limit_tracker.py]
**为什么它是可分离的**：独立模块 `credential_pool.py` + `rate_limit_tracker.py` + `error_classifier.py`，与其他 agent 组件协作。

**关键机制**（源码可见）：
- **Persistent multi-credential pool**：同一 provider 的多个 API key 轮换 ^[agent/credential_pool.py:1]
- **Error classification**：`classify_api_error()` 区分速率限制、认证失败、服务器错误，决定是否 failover ^[agent/error_classifier.py]
- **Jittered backoff**：`jittered_backoff()` 在重试时添加随机抖动 ^[agent/retry_utils.py]

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/credential_pool.py`

---

### Entity: Web UI -- 前端界面

**代码位置**：`web/` 目录
**这个模块解决什么问题**：基于 React + TypeScript + Vite 的单页应用，提供 Hermes Agent 的 Web 界面。
**对外暴露什么**：
- React SPA（index.html + src/）
- Vite 构建配置
- eslint 配置
**它和谁交互**：
- 通过 `hermes_cli/web_server.py` 提供服务
- 与 gateway API 通信
**为什么它是可分离的**：独立的 `web/` 目录，独立的 package.json 和技术栈（React/TypeScript/Vite）。

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/web/package.json`

---

### Entity: Website/Docs -- 文档站点

**代码位置**：`website/` 目录
**这个模块解决什么问题**：基于 Docusaurus 的文档站点（hermes-agent.nousresearch.com/docs）。
**对外暴露什么**：
- Docusaurus 站点（docs/, src/, static/）
- 侧边栏配置（sidebars.ts）
**为什么它是可分离的**：独立的 `website/` 目录，独立的技术栈和构建系统。

**源码证据**：
- 入口文件：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/website/package.json`

---

## 第二部分：候选 Ontology 节点

---

### Ontology 候选: Execution Environment Backend

**信号类型**：接口+多实现 + 配置可替换
**源码证据**：
- 抽象接口：`class BaseEnvironment(ABC)` ^[tools/environments/base.py:226]
- 7 个具体实现：`LocalEnvironment` ^[tools/environments/local.py]，`DockerEnvironment` ^[tools/environments/docker.py]，`SshEnvironment` ^[tools/environments/ssh.py]，`ModalEnvironment` ^[tools/environments/modal.py]，`ManagedModalEnvironment` ^[tools/environments/managed_modal.py]，`DaytonaEnvironment` ^[tools/environments/daytona.py]，`SingularityEnvironment` ^[tools/environments/singularity.py]
- 配置可替换：用户通过 `TERMINAL_ENV` 环境变量选择后端（`local | docker | modal | managed_modal | daytona | ssh | singularity`）^[tools/terminal_tool.py:8-10]
- `FileSyncManager` ^[tools/environments/file_sync.py] 为远程后端提供文件同步
**下属 Entity**：
- Terminal Execution Environments
- Process Registry（后台进程在各后端内执行）
- Code Execution Sandbox（remote 模式通过 env.execute() 通信）
**判断置信度**：高（7 个实现 + 配置选择）

---

### Ontology 候选: Memory Provider Backend

**信号类型**：接口+多实现 + 配置可替换 + 注册机制
**源码证据**：
- 抽象接口：`class MemoryProvider(ABC)` ^[agent/memory_provider.py:42]
- 内置实现：`BuiltinMemoryProvider`（基于文件的 MEMORY.md/USER.md）
- 至少 8 个 plugin 实现：`plugins/memory/honcho/`，`plugins/memory/hindsight/`，`plugins/memory/mem0/`，`plugins/memory/holographic/`，`plugins/memory/supermemory/`，`plugins/memory/openviking/`，`plugins/memory/byterover/`，`plugins/memory/retaindb/` ^[plugins/memory/ 目录]
- 配置可替换：用户通过 `memory.provider` config key 选择（`honcho | hindsight | mem0 | ...`）^[plugins/memory/__init__.py:307-319]
- 注册机制：`plugins/memory/__init__.py` 提供 `discover_memory_providers()` ^[plugins/memory/__init__.py:122] 和 `load_memory_provider(name)` ^[plugins/memory/__init__.py:159]，通过 `register_memory_provider()` 注册 ^[plugins/memory/__init__.py:287-294]
**下属 Entity**：
- Memory Provider System（MemoryProvider ABC + MemoryManager + 所有 plugin）
- Built-in Memory（memory_tool.py）
**判断置信度**：高（9 个实现 + ABC + config 选择 + 注册机制）

---

### Ontology 候选: Context Engine

**信号类型**：接口+多实现 + 配置可替换 + 注册机制
**源码证据**：
- 抽象接口：`class ContextEngine(ABC)` ^[agent/context_engine.py:32]
- 内置实现：`class ContextCompressor(ContextEngine)` ^[agent/context_compressor.py:185]
- Plugin 发现：`plugins/context_engine/` 目录，`discover_context_engines()` ^[plugins/context_engine/__init__.py:33] 扫描可用引擎
- 配置可替换：用户通过 `context.engine` config key 选择（默认 `"compressor"`）^[agent/context_engine.py:11]
- 注册机制：`register_context_engine()` ^[plugins/context_engine/__init__.py:205-206]
**下属 Entity**：
- Context Engine（ContextEngine ABC + ContextCompressor）
- Context Engine Plugins（plugins/context_engine/ 发现系统）
**判断置信度**：中（内置 1 个实现 + plugin 框架已就绪，但当前 repo 内置 plugin 目录为空；信噪来自 ABC 设计和 config 驱动的选择机制）

---

### Ontology 候选: Messaging Platform Adapter

**信号类型**：接口+多实现
**源码证据**：
- 抽象接口：`class BasePlatformAdapter(ABC)` ^[gateway/platforms/base.py:813]
- 20+ 个具体实现：telegram ^[gateway/platforms/telegram.py]，discord ^[gateway/platforms/discord.py]，slack ^[gateway/platforms/slack.py]，whatsapp ^[gateway/platforms/whatsapp.py]，signal ^[gateway/platforms/signal.py]，matrix ^[gateway/platforms/matrix.py]，mattermost ^[gateway/platforms/mattermost.py]，homeassistant ^[gateway/platforms/homeassistant.py]，dingtalk ^[gateway/platforms/dingtalk.py]，feishu ^[gateway/platforms/feishu.py]，wecom ^[gateway/platforms/wecom.py]，weixin ^[gateway/platforms/weixin.py]，sms ^[gateway/platforms/sms.py]，email ^[gateway/platforms/email.py]，webhook ^[gateway/platforms/webhook.py]，bluebubbles ^[gateway/platforms/bluebubbles.py]，qqbot ^[gateway/platforms/qqbot.py]，telegram_network ^[gateway/platforms/telegram_network.py]，wecom_callback ^[gateway/platforms/wecom_callback.py]，api_server ^[gateway/platforms/api_server.py] ^[gateway/platforms/ 目录]
- 配置驱动：每个 platform 通过 `config.platforms[Platform.X].enabled` 和 token 启用 ^[gateway/platforms/ADDING_A_PLATFORM.md]
- 扩展指南：`gateway/platforms/ADDING_A_PLATFORM.md` 提供完整的新平台集成 checklist
**下属 Entity**：
- Messaging Gateway（GatewayRunner + SessionStore）
- Platform Adapters（20+ adapter 实现）
**判断置信度**：高（20+ 个实现 + ABC + 扩展指南）

---

### Ontology 候选: Cloud Browser Provider

**信号类型**：接口+多实现 + 配置可替换
**源码证据**：
- 抽象接口：`class CloudBrowserProvider(ABC)` ^[tools/browser_providers/base.py:7]
- 3 个具体实现：Browserbase ^[tools/browser_providers/browserbase.py]，BrowserUse ^[tools/browser_providers/browser_use.py]，Firecrawl ^[tools/browser_providers/firecrawl.py]
- 配置可替换：用户通过 `config["browser"]["cloud_provider"]` 选择 ^[tools/browser_providers/base.py:12-13]
- 注册入口：provider 在 `browser_tool._PROVIDER_REGISTRY` 中注册 ^[tools/browser_providers/base.py:11]
**下属 Entity**：
- Cloud Browser Providers
**判断置信度**：高（3 个实现 + ABC + config 选择）

---

### Ontology 候选: RL Environment

**信号类型**：接口+多实现
**源码证据**：
- 抽象基类：`class HermesAgentBaseEnv(BaseEnv)` ^[environments/hermes_base_env.py:221]
- 至少 4 个具体环境：`HermesSWEEnv` ^[environments/hermes_swe_env/hermes_swe_env.py]，`WebResearchEnv` ^[environments/web_research_env.py]，`AgenticOPDEnv` ^[environments/agentic_opd_env.py]，Terminal Test Env ^[environments/terminal_test_env/]
- 3 个 benchmark：tblite, terminalbench_2, yc_bench ^[environments/benchmarks/ 目录]
- 通过 Atropos config 选择具体环境
**下属 Entity**：
- RL Environments（HermesAgentBaseEnv + 各环境实现 + HermesAgentLoop）
**判断置信度**：高（5+ 个实现 + 基类 + config 驱动）

---

### Ontology 候选: Tool Call Parser

**信号类型**：多实现（针对不同 model family 的独立 parser）
**源码证据**：
- 独立目录：`environments/tool_call_parsers/`，包含 11 个 parser 文件 ^[environments/tool_call_parsers/ 目录]
- 11 个具体实现：hermes_parser ^[environments/tool_call_parsers/hermes_parser.py]，deepseek_v3_parser ^[environments/tool_call_parsers/deepseek_v3_parser.py]，deepseek_v3_1_parser ^[environments/tool_call_parsers/deepseek_v3_1_parser.py]，glm45_parser ^[environments/tool_call_parsers/glm45_parser.py]，glm47_parser ^[environments/tool_call_parsers/glm47_parser.py]，kimi_k2_parser ^[environments/tool_call_parsers/kimi_k2_parser.py]，llama_parser ^[environments/tool_call_parsers/llama_parser.py]，longcat_parser ^[environments/tool_call_parsers/longcat_parser.py]，mistral_parser ^[environments/tool_call_parsers/mistral_parser.py]，qwen_parser ^[environments/tool_call_parsers/qwen_parser.py]，qwen3_coder_parser ^[environments/tool_call_parsers/qwen3_coder_parser.py]
- 每个 parser 将特定 model 的非标准 tool call 输出解析为标准格式
**下属 Entity**：
- RL Environments（tool_call_parsers 是其子组件）
**判断置信度**：高（11 个实现 + 独立目录 + 每个 parser 独立可替换）

---

### Ontology 候选: Tool/Toolset Registration & Discovery

**信号类型**：注册机制 + 多实现
**源码证据**：
- 注册中心：`class ToolRegistry` ^[tools/registry.py:100]，`registry.register()` ^[tools/registry.py:176-228]
- 23 个工具模块通过 `registry.register()` 自注册 ^[tools/ 目录]
- 发现机制：`discover_builtin_tools()` ^[tools/registry.py:56-73] 通过 AST 扫描
- MCP 工具动态注册/注销：`tools/mcp_tool.py` 使用 `registry.register()` / `registry.deregister()` ^[tools/mcp_tool.py]
- 所有注册的工具按 toolset 分组，统一 schema 格式（OpenAI function calling 格式）
**下属 Entity**：
- Tool Registry
- Toolset System
- Model Tools Orchestration
- MCP Client（通过 registry 动态注册）
- 所有 tools/*.py 注册的工具模块
**判断置信度**：高（23+ 个注册调用 + 统一的 register() 入口 + 发现机制）

---

### Ontology 候选: Agent Skill (agentskills.io)

**信号类型**：注册机制 + 独立目录导出
**源码证据**：
- 技能目录：`skills/`（26 类别）+ `optional-skills/`（14 类别）^[skills/ 目录，optional-skills/ 目录]
- 技能格式遵循 agentskills.io 开放标准：YAML frontmatter + SKILL.md ^[tools/skills_tool.py:28-46]
- Progressive disclosure 架构：元数据 -> 完整指令 -> 关联文件 ^[tools/skills_tool.py:9-13]
- 发现机制：`agent/skill_utils.py` 提供 `iter_skill_index_files()`, `get_all_skills_dirs()` 等
- Skills Hub 集成：`tools/skills_hub.py`（搜索、浏览、安装来自 agentskills.io 的技能）
**下属 Entity**：
- Skills System（skills_tool + skill_manager_tool + skills_hub + skills_sync + skills_guard）
- skills/ + optional-skills/ 目录
- agent/skill_utils.py + agent/skill_commands.py
**判断置信度**：高（40+ 个技能类别 + 开放标准 + hub 集成 + 发现机制）

---

### Ontology 候选: LLM Provider/Model Routing

**信号类型**：配置可替换 + 多实现
**源码证据**：
- Provider 注册：`hermes_cli/auth.py` 的 `PROVIDER_REGISTRY`，`hermes_cli/providers.py`，`hermes_cli/runtime_provider.py` ^[hermes_cli/auth.py]
- Model 目录：`hermes_cli/models.py`（model catalog, provider model lists），`hermes_cli/codex_models.py` ^[hermes_cli/models.py]
- Model 切换 pipeline：`hermes_cli/model_switch.py`（shared CLI + gateway）^[hermes_cli/model_switch.py]
- Model 元数据：`agent/model_metadata.py`（context lengths, token estimation），`agent/models_dev.py`（models.dev registry 集成）^[agent/model_metadata.py]
- Smart routing：`agent/smart_model_routing.py` ^[agent/smart_model_routing.py]
- Provider adapters：`agent/anthropic_adapter.py` ^[agent/anthropic_adapter.py]，`agent/bedrock_adapter.py` ^[agent/bedrock_adapter.py]
- 通过 `hermes model` CLI 或 `/model` slash command 切换
**下属 Entity**：
- Hermes CLI（model 切换、provider 配置）
- Agent internals（model_metadata, anthropic_adapter, bedrock_adapter）
- Credential Pool（同一 provider 的多 key 管理）
**判断置信度**：中（多个模块协作但无统一 ABC；provider 通过 config 和 registry 实现多样性，而非通过接口继承）

---

## 第三部分：孤立 Entity（未找到 Ontology 归属）

---

### 孤立 Entity（未找到 Ontology 归属）

- **AIAgent (Core Agent Loop)**：原因是其作为顶层编排器，不实现任何可替换策略接口。AIAgent 消费所有其他 Entity，自身不构成"能力域"——它是 agent 框架本身，而非框架内的可替换组件。
- **SessionDB (SQLite Session Store)**：原因是当前只有一个实现（SQLite + FTS5），不存在多个 backend 实现。如果未来添加 PostgreSQL/Redis memory store，则可能形成 "Session Store Backend" Ontology 节点。
- **Hermes CLI**：原因是 CLI 是应用入口层，不定义可替换策略。其子模块（model switch、config、auth）虽然复杂，但分别属于其他 Ontology 节点。
- **Batch Runner**：原因是特定用例的工具（批处理），不定义接口也不被其他实现替换。
- **Trajectory Compressor**：原因是独立工具，不定义可替换接口。
- **Event Hook System**：原因是 hook 系统虽有扩展机制，但当前只有 1 个内置 hook（boot-md），无多实现信号。如果社区贡献 ≥2 个独立 hook，可能形成 "Lifecycle Hook" Ontology 节点。
- **ACP Adapter**：原因是单一协议的适配器，当前无多个 ACP 实现或可替换的编辑器集成后端。
- **Cron Scheduler**：原因是单一实现（file-based jobs.json + croniter），无多后端信号。
- **Web UI** / **Website/Docs**：原因是前端/文档层，不定义可替换后端接口。
- **Delegate/Subagent System**：原因是内建于 agent 的委派能力，不通过可替换接口提供。
- **Code Execution Sandbox**：原因是单一实现（UDS + file-based RPC），不通过 backend 接口替换。
- **Process Registry**：原因是单一的内存实现，不定义可替换存储后端。

---

## 附录：重要交叉引用

### Entity 同时匹配多个 Ontology 节点

- **Terminal Execution Environments** 同时匹配 "Execution Environment Backend"（直接归属）和 "Tool/Toolset Registration & Discovery"（terminal tool 注册在 tool registry）
- **MCP Client** 同时匹配 "Tool/Toolset Registration & Discovery"（通过 registry 动态注册工具）——其自身不构成独立 Ontology 节点（当前仅 1 个 MCP client 实现）
- **Memory Provider Plugins** 同时匹配 "Memory Provider Backend"（直接归属）和 "Tool/Toolset Registration & Discovery"（每个 provider 的 tool schema 通过 registry 注册）
- **RL Environments** 同时匹配 "RL Environment"（直接归属）和 "Tool Call Parser"（parser 是 environment 的子组件）
- **Cloud Browser Providers** 同时匹配 "Cloud Browser Provider"（直接归属）和 "Tool/Toolset Registration & Discovery"（browser_tool 注册在 tool registry）

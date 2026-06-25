# Codex Architecture 维度分析

## 1. 核心抽象

### 1.1 Codex（会话句柄）

`Codex` 是外部调用者与 Agent 引擎之间的公共 API 句柄。它持有三个异步通道：`tx_sub`（有界提交通道，容量 512）、`rx_event`（无界事件通道）和 `agent_status`（watch 通道，广播 Agent 状态）。调用者通过 `submit(op)` 方法将操作入队，通过 `next_event()` 方法阻塞等待 Agent 返回的 `Event`。^[codex-rs/core/src/session/mod.rs:148-154] ^[codex-rs/protocol/src/protocol.rs:125-133]

### 1.2 Session（会话编排器）

`Session` 是内部会话编排器，管理状态机、活动 Turn 和工具执行。它维护 `Mutex<SessionState>`（保护对话历史、Token 计数、已授权权限），`SessionConfiguration`（模型提供者、沙箱策略、工作目录的快照），以及 `SessionServices`（共享基础设施组件的依赖容器）。^[codex-rs/core/src/session/session.rs:21-44] ^[codex-rs/core/src/session/session.rs:46-110]

### 1.3 ThreadManager（线程生命周期管理器）

`ThreadManager` 是所有活跃 `CodexThread` 实例的顶层所有者，负责线程的 Spawn、Resume、Fork 三种生命周期操作。它通过内部的 `ThreadManagerState`（`Arc<RwLock<HashMap<ThreadId, Arc<CodexThread>>>>`）管理线程注册表，持有 `AuthManager`、`ModelsManager`、`McpManager` 等共享服务的引用，并将事件持久化委托给 `RolloutRecorder`。^[codex-rs/core/src/thread_manager.rs:172-175] ^[codex-rs/core/src/lib.rs:115-116]

### 1.4 CodexThread（对话线程）

`CodexThread` 是单个对话线程的核心表示，封装了 Turn 执行逻辑。它持有 `ContextManager`（管理对话历史和 Prompt 构建）、与 `ModelClient` 交互进行模型采样、调用 `ToolRouter` 分发工具调用。^[codex-rs/core/src/lib.rs:23-25] ^[codex-rs/core/src/codex_thread.rs:1-50]

### 1.5 TurnContext（Turn 级不变上下文）

`TurnContext` 封装了单次 Turn 所需的全部不可变上下文，包括模型信息、认证、特性标志、审批策略、沙箱策略、开发者指令、环境变量、时间戳和工具列表。这种隔离确保每个 Turn 独立、可重试，并发安全。^[codex-rs/core/src/session/turn_context.rs:55-106]

### 1.6 SessionTask（Turn 执行抽象）

`SessionTask` 是驱动 Turn 的 trait，定义了 `kind()`（返回 `TaskKind`）和 `run()`（核心执行逻辑）。具体实现包括：`RegularTask`（标准用户交互循环）、`ReviewTask`（代码审查子 Agent）、`CompactTask`（历史压缩）、`UserShellCommandTask`（直接执行用户 Shell 命令）。所有 Task 通过 `CancellationToken` 支持优雅中断。^[codex-rs/core/src/tasks/mod.rs:208-224] ^[codex-rs/core/src/tasks/mod.rs:57-62]

### 1.7 ModelClient（模型 API 客户端）

`ModelClient` 管理模型提供者的交互生命周期，负责创建 `ModelClientSession` 来进行流式响应。它构造 API 请求（包含 `x-codex-turn-state` 粘性路由头、W3C trace context、OpenAI-Beta 版本头），并支持 SSE 和 WebSocket 两种传输方式。^[codex-rs/core/src/lib.rs:179-180] ^[codex-rs/core/src/client.rs:133-149]

### 1.8 ToolRouter（工具路由器）

`ToolRouter` 是工具调度的入口点，根据会话参数、MCP 工具和动态工具构造。它将模型发出的工具调用路由到正确的 `CoreToolRuntime` 实现（内建工具或 MCP 服务器），并管理工具的并行执行策略。^[codex-rs/core/src/tools/router.rs:34-57]

### 1.9 ContextManager（上下文管理器）

`ContextManager` 管理对话历史的内存表示，负责记录的增删、规范化（格式一致性）、截断策略（适应模型上下文窗口），并为模型消费准备 `Prompt` 结构。^[codex-rs/core/src/context_manager/mod.rs:1-50]

### 1.10 Submission 与 Event（协议信封）

`Submission` 是提交队列上的信封，包含 UUID v7 唯一 ID、`Op` 操作和可选的 W3C 分布式追踪上下文。`Event` 是事件队列上的信封，`id` 字段回显触发该事件的 `Submission.id`，`msg` 是 `EventMsg` 枚举。^[codex-rs/protocol/src/protocol.rs:125-143] ^[codex-rs/protocol/src/protocol.rs:555-560]

---

## 2. 分层架构

### 2.1 整体分层

Codex 采用清晰的分层架构，从顶至底分为五大功能域：

```
用户界面层 (TUI / CLI Exec / App Server / Cloud Tasks)
         ↓ (所有界面通过 Submission/Event 协议与 Core 通信)
核心引擎层 (codex-core: Session, Thread, Turn, Context)
         ↓
执行与工具层 (ToolRouter, UnifiedExec, MCP, Sandbox)
         ↓
配置与模型管理层 (Config, ModelsManager, Auth)
         ↓
外部服务层 (Model API, MCP Servers, Cloud Backend)
```

^[codex-rs/Cargo.toml:1-121] ^[codex-rs/app-server/README.md:20-30]

### 2.2 用户界面层

包含四种执行模式入口：

| 模式 | 入口点 | 用途 | 事件处理 |
|------|--------|------|----------|
| TUI | `MultitoolCli` 无子命令 | 交互式终端会话 | `App` 结构体管理 UI 循环 |
| Exec | `Subcommand::Exec` | CI/CD、脚本、非交互 | `EventProcessor` 处理输出 |
| App Server | `Subcommand::AppServer` | IDE 集成（VS Code 等） | `codex-app-server` JSON-RPC 桥接 |
| MCP Server | `Subcommand::McpServer` | Codex 作为其他 Agent 的工具 | 暴露 Codex 能力为 MCP 工具 |

所有界面模式最终都汇聚到同一个 `ThreadManager` 进行线程生命周期管理。^[codex-rs/cli/src/main.rs:103-145] ^[codex-rs/tui/src/lib.rs:20-20] ^[codex-rs/exec/src/lib.rs:157-157]

### 2.3 核心引擎层（codex-core）

核心引擎是整个系统的中枢，包含以下关键模块：
- **session/** — 会话管理（mod.rs, session.rs, handlers.rs, turn.rs, turn_context.rs, review.rs）
- **tasks/** — Task 实现（regular.rs, review.rs, compact.rs, mod.rs）
- **state/** — 状态管理（mod.rs, turn.rs, service.rs）
- **tools/** — 工具系统（router.rs, registry.rs, orchestrator.rs, handlers/）
- **context_manager/** — 对话历史与上下文（mod.rs, history.rs, normalize.rs）
- **agent/** — 多 Agent 控制（control.rs, role.rs）
- **compact.rs / compact_remote.rs / compact_remote_v2.rs** — 历史压缩

^[codex-rs/core/src/lib.rs:1-197] ^[codex-rs/core/Cargo.toml:18-120]

### 2.4 执行与工具层

工具执行架构分为三个子层：
- **工具注册与路由**：`ToolRouter` → `ToolRegistry` → `CoreToolRuntime` trait
- **内建工具运行时**：Shell（`ShellCommandHandler`）、补丁（`ApplyPatchHandler`）、统一执行（`UnifiedExecProcessManager`）
- **外部工具集成**：通过 MCP 协议连接的 `McpManager`，工具名格式为 `mcp__{server_name}__toolname`

工具执行经过 `ToolOrchestrator` 统一管理审批和安全策略，支持并行执行和取消。^[codex-rs/core/src/tools/router.rs:34-57] ^[codex-rs/core/src/tools/orchestrator.rs:1-20] ^[codex-rs/codex-mcp/src/mcp/mod.rs:44-46]

### 2.5 配置与模型管理层

配置系统采用七层优先级合并模型（CLI 覆盖 > 仓库 > 目录树 > CWD > 用户全局 > 系统 > 管理员托管），通过 `ConfigLayerStack` 合并后存入 `Config` 结构体，并经过 `ConfigRequirements` 验证。模型管理通过 `ModelsManager` 实现远端获取、本地缓存（TTL + ETag）、最长前缀匹配和覆盖安全钳制。^[codex-rs/core/src/config/mod.rs:10-18] ^[codex-rs/models-manager/src/manager.rs:33-40] ^[codex-rs/app-server/tests/common/models_cache.rs:67-105]

---

## 3. 数据流

### 3.1 Submission/Event 队列模式（单向异步）

Codex 的核心数据流采用 **Submission Queue / Event Queue（SQ/EQ）** 模式，基于 `async-channel` 实现单向异步通信：

```
调用者 (TUI/CLI/AppServer)
    │
    │  submit(Op) → tx_sub (bounded, 512)
    │
    ▼
submission_loop (tokio spawn 的后台任务)
    │
    │  匹配 Op 变体 → dispatch_op() → Session
    │
    ▼
Session → ModelClient (API 调用) / ToolRouter (工具执行)
    │
    │  emit_event() → tx_event (unbounded)
    │
    ▼
调用者 ← next_event() ← rx_event
```

通道设计：提交队列为有界通道（容量 512），防止内存压力；事件队列为无界通道，永不阻塞 Agent 执行；Agent 状态通过 `tokio::sync::watch` 广播（只保留最新值）。^[codex-rs/protocol/src/protocol.rs:3-4] ^[codex-rs/core/src/session/mod.rs:1044-1065]

### 3.2 Turn 执行数据流

单个 Turn 的完整数据流（模型采样循环）：

```
1. TurnContext 构建 → Prompt 组装（含缓存前缀、指令、工具 Schema）
2. ModelClient.stream_responses(prompt) → SSE/WebSocket 流
3. 模型返回 delta → 映射为 ResponseEvent
   ├── AgentMessageDelta → 流式文本输出到 UI
   ├── ToolCall → ToolRouter.handle() → ToolRuntime
   │   ├── 内建工具：ShellRuntime / ApplyPatchRuntime
   │   └── MCP 工具：McpManager.call_tool()
   └── ToolOutput → 反馈给模型继续采样
4. TurnComplete → Token 计数、持久化、状态更新
```

采样循环持续执行直到模型不再发出工具调用，或被用户中断。^[codex-rs/core/src/session/turn.rs:135-142] ^[codex-rs/core/src/session/turn.rs:54-58] ^[codex-rs/core/src/lib.rs:179-184]

### 3.3 App Server 协议转换数据流

在 App Server 模式下，数据流经过 JSON-RPC 转换：

```
IDE Client → JSON-RPC Message
    → Transport (stdio/Unix Socket/WebSocket)
    → Serde Deserialization → ClientRequest Enum
    → Request Processor → Codex::submit(Op)
    → Core Agent 处理
    → EventMsg → apply_bespoke_event_handling
    → ServerNotification → JSON-RPC Response → IDE Client
```

^[codex-rs/app-server/README.md:22-30] ^[codex-rs/app-server-protocol/src/protocol/common.rs:176-189] ^[codex-rs/app-server/src/bespoke_event_handling.rs:135-150]

### 3.4 多 Agent 通信数据流

父子 Agent 之间的通信通过 `codex_delegate` 模块实现双向事件和操作转发：

```
Parent Session
    │  run_codex_thread_interactive()
    ▼
codex_delegate
    │  Codex::spawn(CodexSpawnArgs)
    ▼
Sub-Agent Session
    │  EventMsg → forward_events → 过滤/处理 → Parent (tx_sub)
    │  Op ← forward_ops ← Parent (rx_ops)
```

子 Agent 的审批请求会被过滤，仅将结果转发给父 Agent。^[codex-rs/core/src/codex_delegate.rs:68-156] ^[codex-rs/core/src/agent/control.rs:84-102]

### 3.5 持久化数据流

会话事件通过 `RolloutRecorder` 异步持久化到磁盘：

```
ContextManager.record_items() → RolloutRecorder
    → RolloutCmd::AddItems → mpsc channel
    → RolloutWriterTask (后台 tokio task)
    → write_all() → sessions/YYYY/MM/DD/rollout-TIMESTAMP-UUID.jsonl
```

冷 rollout 文件通过 Zstandard 压缩，并由 SQLite (`StateRuntime`) 索引用于快速发现和查询。^[codex-rs/rollout/src/recorder.rs:75-110] ^[codex-rs/rollout/src/compression.rs:24-31] ^[codex-rs/state/src/runtime.rs:109-141]

---

## 4. 关注点分离

### 4.1 协议层与业务逻辑分离

通信协议定义在独立的 `codex-protocol` crate 中，包含 `Op`、`EventMsg`、`Submission`、`Event` 等纯数据类型，不包含业务逻辑。业务逻辑全部集中在 `codex-core` 中，通过 `Codex` 结构体的通道接口与协议层交互。所有前端（TUI、Exec、AppServer、MCP Server）仅通过此协议与 Core 通信。^[codex-rs/protocol/src/protocol.rs:1-5] ^[codex-rs/app-server/README.md:22-23]

### 4.2 会话与 Turn 的隔离

- **会话级状态**：`SessionState`（对话历史、配置快照、已授权权限）跨 Turn 保持
- **Turn 级状态**：`TurnContext`（模型参数、沙箱策略、审批设置）每个 Turn 独立构建，Turn 之间互不干扰
- **活跃 Turn 状态**：`ActiveTurn`（`Mutex<Option<ActiveTurn>>`）保护当前正在执行的 Task，确保状态一致
- **取消机制**：`CancellationToken` 允许优雅中断正在执行的 Turn，不破坏会话完整性

^[codex-rs/core/src/session/session.rs:23-44] ^[codex-rs/core/src/session/turn_context.rs:55-106] ^[codex-rs/core/src/state/turn.rs:30-100]

### 4.3 工具执行的安全分层

安全策略与工具执行完全解耦：

- **配置层**：`PermissionProfile` 定义允许的沙箱模式（ReadOnly / WorkspaceWrite / DangerFullAccess）和网络策略
- **审批层**：`AskForApproval` 定义何时需要用户授权（Never / Granular），`ApprovalsReviewer` 决定审批路由（user / auto_review 子 Agent）
- **执行层**：`ToolOrchestrator` 统一处理审批检查、沙箱选择和被拒重试
- **平台层**：Linux 使用 Bubblewrap + Landlock，Windows 使用 Restricted Tokens + Private Desktops

^[codex-rs/core/src/config/mod.rs:87-104] ^[codex-rs/core/src/tools/orchestrator.rs:1-20] ^[codex-rs/core/src/exec_policy.rs:174-197]

### 4.4 配置的分层关注点分离

配置数据从 7 个来源合并（CLI → 仓库 → 目录树 → CWD → 用户全局 → 系统 → 管理员托管），每层只关注自己范围的设置。`ConfigLayerStack` 统一合并，`ConfigRequirements` 验证约束（如企业策略强制）。`ConfigLockfileToml` 确保会话可复现性。`Constrained<T>` 类型追踪值的来源和是否被策略锁定。^[codex-rs/core/src/config/mod.rs:10-18] ^[codex-rs/config/src/config_requirements.rs:144-165]

### 4.5 扩展机制的分层解耦

Codex 提供三层独立的扩展机制，互不耦合：

1. **Skills System**：定义在 `.codex/skills`、插件和内置 Core Skills 中的自然语言指令包，通过 `PluginsManager` 加载后注入到 Prompt 中。^[codex-rs/core-plugins/src/loader.rs:50-53] ^[codex-rs/core-plugins/src/manager.rs:42-48]

2. **Plugins System**：通过 Marketplace 分发的扩展包，可包含 Skills、MCP Servers、Hooks、App Connectors。插件存储在 `plugins/cache/{marketplace}/{name}/{version}/` 的本地缓存中。^[codex-rs/core-plugins/src/remote.rs:167-173] ^[codex-rs/core-plugins/src/store.rs:48-50]

3. **MCP（Model Context Protocol）**：通过 stdio 或 HTTP（SSE + JSON-RPC）与外部进程通信，格式为 `mcp__{server_name}__toolname`。`McpConnectionManager` 管理所有服务器连接的生命周期、工具发现和 OAuth 认证。^[codex-rs/codex-mcp/src/connection_manager.rs:1-15] ^[codex-rs/codex-mcp/src/mcp/mod.rs:44-46]

4. **Hooks System**：在 Agent 生命周期关键点（SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、Stop、PreCompact/PostCompact、SubagentStart/Stop、PermissionRequest）插入自定义逻辑。Hook 通过 stdin/stdout JSON 协议与外部进程通信，支持拦截、增强和决策。^[codex-rs/hooks/src/lib.rs:19-30] ^[codex-rs/hooks/src/engine/mod.rs:183-191]

### 4.6 持久化与运行时分离

持久化采用多层存储策略：
- **Rollout JSONL 文件**：记录完整会话事件（`sessions/YYYY/MM/DD/*.jsonl`），由后台 `RolloutWriterTask` 异步写入，冷文件 Zstandard 压缩
- **StateRuntime（SQLite）**：四库分离——`state_5.sqlite`（线程元数据）、`logs_2.sqlite`（追踪日志，10 MiB/1000 行上限）、`goals_1.sqlite`（目标与预算）、`memories_1.sqlite`（记忆提取与合并状态）
- **Memories System**：两阶段流水线——Phase 1 从 rollout 中提取摘要（GPT-5.4-mini），Phase 2 全局合并为结构化 Markdown 并注入 Prompt 上下文

^[codex-rs/state/src/runtime.rs:109-141] ^[codex-rs/rollout/src/recorder.rs:58-110] ^[codex-rs/ext/memories/src/extension.rs:49-69]

### 4.7 Cargo Workspace 的 Crate 级关注点分离

120+ 个 crate 按功能域组织，核心引擎 `codex-core` 通过依赖注入（`SessionServices`）使用各个专门化 crate，避免核心膨胀：

- **入口点**：`codex-cli`, `codex-tui`, `codex-exec`, `codex-app-server`, `codex-mcp-server`
- **核心逻辑**：`codex-core`, `codex-protocol`, `codex-config`, `codex-state`
- **平台集成**：`codex-linux-sandbox`, `codex-windows-sandbox`, `codex-network-proxy`
- **外部集成**：`codex-rmcp-client`, `codex-backend-client`, `codex-cloud-tasks`
- **扩展**：`codex-core-plugins`, `codex-hooks`, `codex-features`
- **工具**：约 30 个 `codex-utils-*` 工具 crate

所有入口点 → `codex-core` → 协议、配置、状态、工具、沙箱。^[codex-rs/Cargo.toml:2-121] ^[codex-rs/core/Cargo.toml:18-120] ^[AGENTS.md:66-69]

---

## 5. 关联

Codex 的架构与典型的 AI 编程 Agent 相比有以下独特特征：

1. **SQ/EQ 异步通道模式**：与大多数 Agent 框架的同步请求-响应模式不同，Codex 通过有界提交通道和无界事件通道实现了完全解耦的异步通信，支持中断、取消和流式输出。这类似于 Actor 模型中的消息传递模式。

2. **多 Agent 层级架构**：通过 `AgentControl` + `ThreadManager` 实现了树形父子 Agent 关系，子 Agent（Reviewer、Guardian、Explorer）通过角色配置（`AgentRoleConfig`）继承父配置并以工具调用的形式触发（`spawn_agent`、`send_message`、`wait_agent`），不同于传统的显式 API 调用方式。

3. **Turn 级配置隔离**：每个 Turn 通过 `TurnContext` 持有独立的模型参数、沙箱策略和审批设置，允许同一个会话中不同的 Turn 使用不同的安全级别和模型配置。这是比 Per-Session 配置更细粒度的设计。

4. **扩展体系的三层嵌套**：Skills（指令注入）⊂ Plugins（含 Skills、MCP、Hooks 的打包分发）⊂ MCP（外部工具协议），形成从静态指令到动态工具的逐级扩展梯度。

5. **SQLite 四库分离的持久化策略**：将线程元数据、日志、目标和记忆分别存储在不同的 SQLite 文件中，减少锁竞争并按数据生命周期独立管理，比单库方案更精细。

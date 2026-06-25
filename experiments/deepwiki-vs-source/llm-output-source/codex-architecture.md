# Codex Architecture 维度分析

> 源仓库：openai/codex（Rust + TypeScript monorepo）
> 分析范围：`codex-rs/` Rust workspace，包含 ~120 个子 crate

---

## 1. 核心抽象

### 1.1 Session（会话）

`Session` 是 Codex 最核心的运行时抽象，代表一个已初始化的模型 Agent 上下文。一个 Session 在任意时刻最多只能有一个活跃的 task，可被用户输入中断。^[codex-rs/core/src/session/session.rs:22-44]

Session 持有：
- **事件通道** (`tx_event: Sender<Event>`)：向客户端推送事件的发送端 ^[codex-rs/core/src/session/session.rs:27]
- **Agent 状态** (`agent_status: watch::Sender<AgentStatus>`)：通过 watch channel 广播当前 Agent 的运行状态 ^[codex-rs/core/src/session/session.rs:28]
- **输入队列** (`InputQueue`)：管理待处理的用户输入，保证 FIFO 顺序 ^[codex-rs/core/src/session/session.rs:40]
- **活跃 Turn** (`active_turn: Mutex<Option<ActiveTurn>>`)：当前正在执行的 Turn ^[codex-rs/core/src/session/session.rs:39]
- **服务集合** (`SessionServices`)：聚合外部依赖，包括 extension 注册表、Agent 控制、skills、MCP connection manager 等 ^[codex-rs/core/src/session/session.rs:41]
- **Session 配置** (`SessionConfiguration`)：模型提供者、权限策略、协作模式、personality 等 ^[codex-rs/core/src/session/session.rs:47-100]

### 1.2 CodexThread（线程）

`CodexThread` 是面向外部消费者的高级 API 句柄，封装了一个 Session 及其生命周期管理。外部代码通过 `CodexThread` 来操作线程和提交用户输入。^[codex-rs/core/src/codex_thread.rs:27-28]

`CodexThread` 暴露的核心能力：
- 提交用户输入 (`submit`) ^[codex-rs/core/src/codex_thread.rs:33]
- 中断正在运行的 turn (`interrupt`) ^[codex-rs/protocol/src/protocol.rs:502-504]
- 管理 thread 级别的设置覆盖 (`apply_settings`) ^[codex-rs/protocol/src/protocol.rs:425-469]
- 获取 thread 配置快照 (`ThreadConfigSnapshot`) ^[codex-rs/core/src/codex_thread.rs:54-75]

`ThreadConfigSnapshot` 冻结了 thread 级别的不可变配置：模型、service-tier、审批策略、权限 profile、workspace roots、personality、coordination mode、session source 等。^[codex-rs/core/src/codex_thread.rs:54-75]

### 1.3 Turn（轮次）

Turn 是 Codex 的工作单元。每次用户输入触发一个 Turn，Turn 的生命周期包括：
1. **TurnStarted** — Agent 开始处理 ^[codex-rs/protocol/src/protocol.rs:1226-1228]
2. **Agent 推理/消息/工具调用流** — 流式输出 Agent 消息、推理 token、工具调用事件 ^[codex-rs/protocol/src/protocol.rs:1243-1272]
3. **TurnComplete** — Agent 完成所有动作 ^[codex-rs/protocol/src/protocol.rs:1235-1237]

Turn 的核心上下文 `TurnContext` 包含：当前 turn 的 sub_id、模型选择、推理参数、工具路由器 (`ToolRouter`)、扩展数据等。^[codex-rs/core/src/session/turn.rs:1-67]

### 1.4 Submission / Event（SQ/EQ 协议）

Codex 内部使用 **SQ (Submission Queue) / EQ (Event Queue)** 模式进行异步通信：

- **Submission (SQ)**：客户端发出的请求，封装在 `Op` 枚举中 ^[codex-rs/protocol/src/protocol.rs:161-172]
- **Event (EQ)**：服务端产生的事件，封装在 `EventMsg` 枚举中 ^[codex-rs/protocol/src/protocol.rs:1187-1336]

`Op` 枚举包含约 20 种操作：`UserInput`、`Interrupt`、`ExecApproval`、`PatchApproval`、`Compact`、`ThreadSettings`、`Shutdown`、`RefreshMcpServers` 等。^[codex-rs/protocol/src/protocol.rs:501-650]

`EventMsg` 枚举包含约 30 种事件：`TurnStarted`、`TurnComplete`、`AgentMessage`、`AgentReasoning`、`ExecCommandBegin/End`、`McpToolCallBegin/End`、`WebSearchBegin/End`、`ElicitationRequest`、`GuardianAssessment`、`PatchApplyBegin/End`、`StreamError` 等。^[codex-rs/protocol/src/protocol.rs:1187-1336]

这种模式实现了请求和响应的解耦——同一个 Submission 可能产生多个异步 Event 流。

### 1.5 Tool（工具）

Tool 是 Agent 执行动作的抽象。`ToolRouter` 是工具调用的中央调度器，负责将模型的 function call 路由到正确的工具实现。^[codex-rs/core/src/tools/router.rs:25]

工具系统按来源分层：
- **内置工具**：`execute_command`、`read_files`、`write_file`、`apply_patch`、`web_search`、`view_image` 等，实现在 `codex-rs/core/src/tools/handlers/` 目录 ^[codex-rs/core/src/tools/handlers/]
- **MCP 工具**：通过 MCP 协议连接的外部工具，由 `McpConnectionManager` 管理 ^[codex-rs/codex-mcp/src/mcp_connection_manager.rs]
- **插件工具**：通过插件系统注册的扩展工具 ^[codex-rs/core-plugins/src/lib.rs]
- **动态工具**：运行时动态注册的工具 ^[codex-rs/protocol/src/dynamic_tools.rs]

`ToolOrchestrator` 驱动每个工具调用的核心流程：审批检查 -> 沙箱策略选择 -> 执行尝试 -> 失败后以更高沙箱级别重试。^[codex-rs/core/src/tools/orchestrator.rs:1-60]

### 1.6 Extension / Contributor（扩展/贡献者）

Extension 是 Codex 的插件化扩展系统，定义在 `codex-rs/ext/extension-api/` 中。扩展通过实现一系列 **Contributor trait** 来介入核心生命周期：^[codex-rs/ext/extension-api/src/contributors.rs:1-62]

| Contributor Trait | 作用 |
|---|---|
| `McpServerContributor` | 解析运行时 MCP 服务器配置 |
| `ContextContributor` | 在 prompt 组装时注入上下文片段 |
| `ThreadLifecycleContributor` | 介入 thread 启动/恢复/闲置/停止 |
| `TurnLifecycleContributor` | 介入 turn 开始/停止/错误/中止 |
| `TurnInputContributor` | 在 turn 输入前补充上下文 |
| `ToolLifecycleContributor` | 介入 tool 启动/完成 |
| `ToolContributor` | 注册额外工具执行器 |
| `ApprovalReviewContributor` | 参与审批审查流程 |
| `TokenUsageContributor` | 参与 token 使用统计 |
| `ConfigContributor` | 参与配置贡献 |

Extension 按功能组织在 `codex-rs/ext/` 下：goal、guardian、image-generation、mcp、memories、skills、web-search。^[codex-rs/ext/]

### 1.7 Thread Store（线程持久化）

`ThreadStore` trait 是存储中立的线程持久化接口。^[codex-rs/thread-store/src/lib.rs:1-5]

应用代码只应以 `ThreadId` 作为持久化句柄，具体实现负责将 ID 解析到本地 rollout 文件或远程存储。^[codex-rs/thread-store/src/lib.rs:1-5]

当前实现包括：
- `LocalThreadStore`：基于本地文件的持久化 ^[codex-rs/thread-store/src/local/]
- `InMemoryThreadStore`：内存实现，用于测试 ^[codex-rs/thread-store/src/in_memory.rs]

---

## 2. 分层架构

Codex 的 Rust workspace 按照严格的层级组织，各层通过 trait 抽象和消息传递进行解耦。

### 2.1 层级总览

```
┌─────────────────────────────────────────────────┐
│  Transport Layer                                 │
│  (app-server-transport: stdio/websocket/unix)     │
├─────────────────────────────────────────────────┤
│  App-Server Layer                                │
│  (app-server, app-server-protocol)               │
│  - MessageProcessor, ThreadStateManager          │
│  - RequestProcessors (per-route handlers)        │
├─────────────────────────────────────────────────┤
│  Core Layer                                      │
│  (core, core-api)                                │
│  - CodexThread, Session, Turn                    │
│  - ToolRouter, ToolOrchestrator                  │
│  - ContextManager, ExecPolicyManager             │
├─────────────────────────────────────────────────┤
│  Extension Layer                                 │
│  (ext/*: extension-api, mcp, guardian, goal,     │
│   skills, memories, web-search, image-gen)       │
├─────────────────────────────────────────────────┤
│  Protocol Layer                                  │
│  (protocol: items, models, protocol, approvals)  │
│  - 纯数据类型，零依赖                              │
├─────────────────────────────────────────────────┤
│  Infrastructure Layer                            │
│  (config, thread-store, rollout, state, exec)    │
│  - 持久化、配置、进程执行、沙箱                      │
├─────────────────────────────────────────────────┤
│  Model Provider / API Layer                      │
│  (codex-api, model-provider, backend-client)     │
│  - 与模型后端通信                                  │
└─────────────────────────────────────────────────┘
```

### 2.2 各层职责

**Transport Layer** (`app-server-transport`)：支持多种传输协议——标准输入输出 (stdio)、WebSocket、Unix domain socket。Transport 层负责连接的建立、认证和消息的序列化/反序列化。^[codex-rs/app-server/src/transport.rs]

**App-Server Layer**：
- `MessageProcessor` 是请求处理的中央调度器，收到 `ClientRequest` 后按请求类型分发给对应的 `RequestProcessor`。^[codex-rs/app-server/src/message_processor.rs:1-96]
- `ThreadStateManager` 管理活跃线程的运行时状态，维护事件订阅、中断队列、turn 状态等。^[codex-rs/app-server/src/thread_state.rs:1-80]
- 每种请求类型有独立的 Processor：`ThreadRequestProcessor`、`TurnRequestProcessor`、`ConfigRequestProcessor`、`McpRequestProcessor`、`SearchRequestProcessor` 等，位于 `request_processors/` 目录。^[codex-rs/app-server/src/request_processors/]

**Core Layer**：包含所有业务逻辑核心——Session 生命周期、Turn 执行、工具路由与编排、上下文管理、执行策略、沙箱决策等。`codex-core` 是当前最大的 crate，AGENTS.md 明确定义了"抵制向 codex-core 添加新代码"的原则，建议新功能放入独立 crate。^[codex-rs/AGENTS.md:75-83]

`core-api` 是对外暴露的公共门面，将 `codex-core` 和其依赖中的关键类型重新导出给外部消费者。^[codex-rs/core-api/src/lib.rs:1-60]

**Extension Layer**：基于 contributor trait 的扩展系统，允许在 thread/turn/tool 生命周期的关键节点注入行为。Extension 之间通过 trait 隔离，彼此不直接依赖。^[codex-rs/ext/extension-api/src/contributors.rs:1-110]

**Protocol Layer** (`protocol`)：定义跨层共享的数据类型——items（TurnItem 枚举）、models（ResponseItem、ContentItem）、protocol（Op、EventMsg、Submission）、approvals、permissions 等。这是 workspace 中最底层的 crate，确保所有上层组件使用统一的数据契约。^[codex-rs/protocol/src/lib.rs:1-32]

**Infrastructure Layer**：
- `config` crate：配置层叠加系统 (`ConfigLayerStack`)，支持 MDM > System > Enterprise Managed > User > Project > Session flags 六个优先级层，通过 TOML merge 实现最终配置。^[codex-rs/config/src/state.rs:239-270]
- `thread-store`：线程持久化抽象 ^[codex-rs/thread-store/src/lib.rs:1-5]
- `rollout`：将事件流持久化为 JSONL rollout 文件，并维护 SQLite 状态数据库 ^[codex-rs/rollout/src/lib.rs]
- `state`：SQLite 后端的 rollout 元数据镜像 ^[codex-rs/state/src/lib.rs:1-9]
- `exec-server`：跨环境的进程执行与文件系统操作抽象，支持本地执行和远程执行 ^[codex-rs/exec-server/src/lib.rs:26-61]

**Model Provider / API Layer**：封装与 OpenAI API（Responses API、Realtime API、Compaction API、Memories API）的通信，支持 WebSocket 和 SSE 传输。`ModelClient` 会话级别管理认证和连接状态，`ModelClientSession` turn 级别管理响应流。^[codex-rs/core/src/client.rs:1-80]

### 2.3 Crate 命名约定

所有 Rust crate 名以 `codex-` 为前缀。例如 `core` 文件夹对应的 crate 名为 `codex-core`。^[codex-rs/AGENTS.md:3-5]

---

## 3. 数据流

### 3.1 整体数据流向

Codex 的数据流是**单向的、事件驱动的管道**：

```
User Input (TUI/IDE/CLI)
    │
    ▼
┌──────────────────┐
│  App-Server      │  JSON-RPC over stdio/ws/unix
│  MessageProcessor│
└──────┬───────────┘
       │ Op::UserInput
       ▼
┌──────────────────┐
│  CodexThread     │
│  .submit()       │
└──────┬───────────┘
       │ turn start
       ▼
┌──────────────────┐
│  Session         │
│  → InputQueue    │
│  → Turn.execute()│
└──────┬───────────┘
       │ context assembly
       ▼
┌──────────────────┐
│  ModelClient     │  API call (Responses API via WebSocket/SSE)
│  → stream response│
└──────┬───────────┘
       │ response items (tool calls, messages)
       ▼
┌──────────────────┐
│  ToolRouter      │
│  → ToolOrchestrator│ → ExecServer
│  → ToolHandlers   │
└──────┬───────────┘
       │ tool output
       ▼
┌──────────────────┐
│  Event stream    │  EventMsg → TUI/IDE via App-Server
└──────────────────┘
```

### 3.2 SQ/EQ 异步解耦

请求（Submission）和响应（Event）通过 async channel 完全解耦：
- Session 内部使用 `async_channel::Sender<Event>` / `Receiver<Event>` 传递事件 ^[codex-rs/core/src/session/session.rs:27]
- 一个 Submission 可能触发多个 Event，客户端通过 `submission.id` 和 `event.correlation_id` 进行关联
- `Op::Interrupt` 可以在 Turn 执行过程中随时中止处理 ^[codex-rs/protocol/src/protocol.rs:502-504]

### 3.3 Turn 执行细节

1. 用户输入通过 `InputQueue` 排队，`InputQueue` 保证 FIFO 顺序 ^[codex-rs/core/src/session/input_queue.rs]
2. Turn 开始前执行 hooks（`run_pending_session_start_hooks`、`inspect_pending_input`）^[codex-rs/core/src/session/turn.rs:22-26]
3. ContextManager 组装模型上下文（历史消息 + 注入的 context fragments）^[codex-rs/core/src/context_manager/mod.rs:5-6]
4. `ModelClientSession` 打开 WebSocket 连接（支持 lazy 连接和 prewarm）并流式获取模型响应 ^[codex-rs/core/src/client.rs:11-13]
5. 响应的每个 `ResponseItem` 经过 `handle_output_item_done` 处理——对于 tool call 调用 `ToolRouter`，对于 message 发送 `AgentMessage` 事件 ^[codex-rs/core/src/session/turn.rs:48-53]
6. Tool 执行经过 `ToolOrchestrator` 的审批 -> 沙箱 -> 执行 -> 重试流水线 ^[codex-rs/core/src/tools/orchestrator.rs:45-60]
7. Turn 结束后运行 legacy hooks 和 turn stop hooks ^[codex-rs/core/src/session/turn.rs:24-26]

### 3.4 上下文注入流

模型上下文在每次 Turn 时由 `ContextManager` 组装。上下文片段（Contextual Fragments）由多个来源按特定顺序注入：
- `UserInstructions`：用户自定义指令 ^[codex-rs/core/src/context/user_instructions.rs]
- `EnvironmentContext`：运行环境信息（shell、workspace、git 状态等）^[codex-rs/core/src/context/environment_context.rs]
- `AppsInstructions`：启用的 App 指令 ^[codex-rs/core/src/context/apps_instructions.rs]
- `AvailableSkillsInstructions`：可用技能列表 ^[codex-rs/core/src/context/available_skills_instructions.rs]
- `AvailablePluginsInstructions`：可用插件列表 ^[codex-rs/core/src/context/available_plugins_instructions.rs]
- `PermissionsInstructions`：当前沙箱权限提示 ^[codex-rs/core/src/context/permissions_instructions.rs]
- `CollaborationModeInstructions`：协作模式指令 ^[codex-rs/core/src/context/collaboration_mode_instructions.rs]
- `PersonalitySpecInstructions`：Personality 定义 ^[codex-rs/core/src/context/personality_spec_instructions.rs]

所有注入必须实现 `ContextualUserFragment` trait，并有硬性大小上限。^[codex-rs/AGENTS.md:96-99]

---

## 4. 关注点分离

### 4.1 配置与运行时的分离

`Config` 和 `SessionConfiguration` 是两个不同概念：
- `Config` 是配置层的合并产物，包含所有用户可见的配置项 ^[codex-rs/core/src/config/mod.rs:1-59]
- `SessionConfiguration` 是 Session 运行时的配置快照，包含已经从 Config 解析并验证的、可直接使用的值 ^[codex-rs/core/src/session/session.rs:47-100]

配置层叠加 (`ConfigLayerStack`) 在启动时完成，Session 运行时不应再读取原始配置层。这确保了配置变更不会在 Turn 中间产生不一致。^[codex-rs/config/src/state.rs:239-270]

### 4.2 传输与业务逻辑的分离

App-Server 支持多种传输方式，但所有传输最终产生相同的 `ClientRequest` / `ServerNotification` 消息，业务逻辑完全与传输协议无关：
- `transport.rs` 处理连接建立、消息序列化 ^[codex-rs/app-server/src/transport.rs]
- `message_processor.rs` 处理路由分发，不感知底层传输 ^[codex-rs/app-server/src/message_processor.rs:1-96]

### 4.3 执行环境的抽象

`exec-server` 提供统一的 `Environment` 抽象，支持 `local` 和 `remote` 两种执行环境：
- `LocalFileSystem` / `RemoteFileSystem`：文件系统操作 ^[codex-rs/exec-server/src/local_file_system.rs] ^[codex-rs/exec-server/src/remote_file_system.rs]
- `LocalProcess` / `RemoteProcess`：进程执行 ^[codex-rs/exec-server/src/local_process.rs] ^[codex-rs/exec-server/src/remote_process.rs]
- `SandboxedFileSystem`：沙箱化文件系统 ^[codex-rs/exec-server/src/sandboxed_file_system.rs]

上层工具代码通过 `ExecutorFileSystem` trait 和 `ExecProcess` trait 操作，不区分本地还是远程。^[codex-rs/exec-server/src/lib.rs:26-61]

### 4.4 工具系统的关注点分离

工具系统内部有清晰的分工：
- **registry**：静态工具注册，定义 tool spec 和 schema ^[codex-rs/core/src/tools/registry.rs]
- **router**：运行时路由，根据 tool_name 和 namespace 找到对应 handler ^[codex-rs/core/src/tools/router.rs]
- **orchestrator**：执行流水线——审批、沙箱选择、执行、重试 ^[codex-rs/core/src/tools/orchestrator.rs:1-60]
- **parallel**：并行工具调用执行管理 ^[codex-rs/core/src/tools/parallel.rs]
- **sandboxing**：沙箱策略选择逻辑 ^[codex-rs/core/src/tools/sandboxing.rs]
- **handlers**：具体工具实现（每种工具一个 handler）^[codex-rs/core/src/tools/handlers/]
- **lifecycle**：工具生命周期通知（通知 extension contributor）^[codex-rs/core/src/tools/lifecycle.rs]

### 4.5 审批与安全的分离

执行审批采用多层安全模型：
1. **ExecPolicyManager**：基于规则的命令安全策略（白名单/黑名单）^[codex-rs/core/src/exec_policy.rs:1-60]
2. **配置中的审批策略** (`AskForApproval` 枚举)：控制何时需要用户审批 ^[codex-rs/protocol/src/protocol.rs:25-27]
3. **Guardian**：额外的安全审查层（自动审批/拒绝/需用户确认）^[codex-rs/ext/guardian/]
4. **SandboxManager**：沙箱策略选择（none / workspace-write / 全沙箱）^[codex-rs/sandboxing/]

每一层独立决策，互不耦合。

### 4.6 Thread Store 的存储中立设计

`ThreadStore` trait 将持久化逻辑与业务逻辑完全解耦。业务代码只依赖 `ThreadStore` trait，而非具体实现。^[codex-rs/thread-store/src/lib.rs:1-5]

`LiveThread` 封装运行时线程状态，`LiveThreadInitGuard` 确保线程有且仅被初始化一次。^[codex-rs/thread-store/src/live_thread.rs]

### 4.7 Core vs Core-API vs Core-Plugins vs Core-Skills

为控制 crate 大小和耦合度，核心功能被拆分到多个 crate：
- `codex-core`：主业务逻辑，但在刻意瘦身 ^[codex-rs/AGENTS.md:75-83]
- `codex-core-api`：公共门面，重新导出 core 和依赖的类型 ^[codex-rs/core-api/src/lib.rs:1-60]
- `codex-core-plugins`：插件管理（marketplace、安装、发现）^[codex-rs/core-plugins/src/lib.rs:1-40]
- `codex-core-skills`：技能系统（skill 定义、注入、渲染）^[codex-rs/core/src/skills/]

### 4.8 模块大小约束

AGENTS.md 规定了严格的模块大小指引：
- Rust 模块目标 500 行以下（不含测试）
- 单个文件超过 800 行时，新功能应放入新模块而非扩展现有文件 ^[codex-rs/AGENTS.md:52-57]

---

## 5. 关联

### 5.1 与典型 LLM Agent 架构的对比

- **LangChain / LangGraph**：采用显式的 Chain/Graph DAG 模型定义 Agent 流程；Codex 采用隐式的 Turn 循环 + Tool 路由模式，流程由模型自身的 tool calling 驱动，而非预定义的 DAG
- **Aider / Cline**：通常为单一进程模式，直接在进程中管理 session；Codex 采用 Client-Server 分离架构，app-server 作为后台守护进程，支持多客户端连接
- **Continue.dev**：IDE 插件模式，直接在编辑器进程内运行；Codex 通过独立的 app-server 进程实现 IDE 无关性

### 5.2 跨平台注意事项

Codex 在架构层面处理了跨平台差异：
- 沙箱：macOS 使用 Seatbelt，Linux 使用 landlock/namespace，Windows 使用 `WindowsSandboxLevel` 配置 ^[codex-rs/core/src/landlock.rs] ^[codex-rs/protocol/src/protocol.rs:25]
- 进程沙箱化通过 `SandboxManager` 统一抽象，各平台有独立实现 ^[codex-rs/sandboxing/]
- 文件系统路径统一使用 `AbsolutePathBuf` 和 `PathUri` 封装平台差异 ^[codex-rs/utils/absolute-path/] ^[codex-rs/utils/path-uri/]

---
type: entity
repo: codex-main
slug: app-server
problem: 如何提供多传输层 JSON-RPC 后端来管理 Agent 会话
generated: 2026-06-28
source_files:
  - codex-rs/app-server/src/lib.rs
  - codex-rs/app-server/src/transport.rs
  - codex-rs/app-server/src/message_processor.rs
---

# App Server

**代码位置**：codex-rs/app-server/
**这个模块解决什么问题**：
- 实现层：通过 `MessageProcessor` + 多传输层（stdio/WebSocket/Unix socket）的 JSON-RPC 服务端，为 Agent 会话提供创建、读写、中断、管理的统一后端
- 问题层：如何提供多传输层 JSON-RPC 后端来管理 Agent 会话
**对外暴露什么**：
- `MessageProcessor`：JSON-RPC 消息处理器，路由线程的创建/读取/启动/中断等请求 ^[codex-rs/app-server/src/message_processor.rs:26]
- `ConfigManager`：服务端配置管理器 ^[codex-rs/app-server/src/config_manager.rs:24]
- `ConnectionState`：传输层连接状态 ^[codex-rs/app-server/src/transport.rs:33]
- `RemoteControlPolicy`：远程控制策略（允许/禁止外部连接） ^[codex-rs/app-server/src/transport.rs:34]
- `TransportEvent`：传输层事件枚举 ^[codex-rs/app-server/src/transport.rs:35]
- `app_server_startup_lock_path`：服务启动锁路径 ^[codex-rs/app-server/src/transport.rs:38]
- 多传输层支持：`start_control_socket_acceptor`（Unix socket）、`start_websocket_acceptor`（WebSocket）、`start_stdio_connection`（stdio） ^[codex-rs/app-server/src/transport.rs:43-45]
- `CHANNEL_CAPACITY`：内部通道容量常量 ^[codex-rs/app-server/src/transport.rs:32]
**它和谁交互**：
- 使用 [[entities/core-agent-loop]] 的 Config 和 CodexThread 管理 Agent 会话 ^[codex-rs/app-server/src/lib.rs:10-11]
- 使用 [[entities/config-management]] 加载和分发配置 ^[codex-rs/app-server/src/lib.rs:5-7]
- 使用 [[entities/exec-server]] 的 EnvironmentManager ^[codex-rs/app-server/src/lib.rs:59]
- 使用 [[entities/rollout]] 的 state_db 管理会话持久化 ^[codex-rs/app-server/src/lib.rs:63]
- 被 `app-server-client` crate 调用
- 被 `app-server-daemon` crate 使用（后台守护进程模式）
**为什么它是可分离的**：独立的 crate + client/protocol/daemon 子 crate 族，清晰的 JSON-RPC 服务端架构

**关键机制**（源码可见）：
- **多传输层抽象**：支持 stdio（CLI 模式）、WebSocket（网络）、Unix domain socket（本机进程间通信）三种传输方式 ^[codex-rs/app-server/src/transport.rs:43-45]
- **JSON-RPC 路由**：`MessageProcessor` 处理 `ThreadStartParams`、`ThreadReadParams`、`ThreadResumeParams`、`TurnInterruptParams` 等标准请求类型 ^[codex-rs/app-server/src/message_processor.rs:26]
- **远程控制策略**：`RemoteControlPolicy` 支持 `start_remote_control` 配置，控制外部连接的安全策略 ^[codex-rs/app-server/src/transport.rs:34]
- **启动锁**：`acquire_app_server_startup_lock` 通过文件锁防止多个 app-server 实例同时运行 ^[codex-rs/app-server/src/transport.rs:37]
- **连接清理**：`ConnectionCleanupTasks` 管理连接断开时的资源清理 ^[codex-rs/app-server/src/connection_cleanup.rs:27]

**源码证据**：
- 入口文件：codex-rs/app-server/src/lib.rs
- 传输层：codex-rs/app-server/src/transport.rs:32-45
- 消息处理：codex-rs/app-server/src/message_processor.rs:26

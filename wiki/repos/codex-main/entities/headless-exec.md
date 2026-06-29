---
type: entity
repo: codex-main
slug: headless-exec
problem: 如何从命令行非交互式地运行 Agent 交互
generated: 2026-06-28
source_files:
  - codex-rs/exec/src/lib.rs
  - codex-rs/exec/src/cli.rs
  - codex-rs/exec/src/event_processor.rs
---

# Headless Exec

**代码位置**：codex-rs/exec/
**这个模块解决什么问题**：
- 实现层：通过 `Cli` + `Command` 枚举 + `EventProcessor` 模式，支持从命令行以非交互方式（--json/--human）运行 Agent，适用于脚本和 CI
- 问题层：如何从命令行非交互式地运行 Agent 交互
**对外暴露什么**：
- `Cli`：CLI 参数结构体 ^[codex-rs/exec/src/cli.rs:13]
- `Command`：子命令枚举（start/resume/review 等） ^[codex-rs/exec/src/cli.rs:14]
- `ReviewArgs`：审查参数 ^[codex-rs/exec/src/cli.rs:15]
- `InProcessAppServerClient`：进程内 App Server 客户端 ^[codex-rs/exec/src/lib.rs:19]
- `InProcessClientStartArgs`：客户端启动参数 ^[codex-rs/exec/src/lib.rs:20]
- `InProcessServerEvent`：服务端事件 ^[codex-rs/exec/src/lib.rs:21]
- 输出模式：`event_processor_with_human_output`（人类可读）和 `event_processor_with_jsonl_output`（机器可读 JSONL） ^[codex-rs/exec/src/lib.rs:9-10]
- `ServerRequest/ServerNotification`：App Server 的 JSON-RPC 请求/通知 ^[codex-rs/exec/src/lib.rs:23-24]
**它和谁交互**：
- 使用 [[entities/app-server]] 的 client 和 protocol（通过 InProcessAppServerClient 连接）
- 使用 [[entities/core-agent-loop]]（通过 App Server 间接启动 Agent 会话）
- 使用 [[entities/config-management]]（加载和覆盖配置）
**为什么它是可分离的**：独立的二进制/库 crate，CLI 前端层，与 Agent 核心通过 App Server 的 JSON-RPC 协议通信

**关键机制**（源码可见）：
- **进程内通信**：`InProcessAppServerClient` 在同一进程内启动 App Server，避免通过 socket 的开销，适用于 CLI 单次调用场景 ^[codex-rs/exec/src/lib.rs:19]
- **双输出模式**：人类可读模式（渲染 Markdown、进度提示）和 JSONL 模式（每行一个 JSON 事件，适合管道处理） ^[codex-rs/exec/src/lib.rs:9-10]
- **JSON-RPC 线程管理**：支持 `ThreadStart`、`ThreadResume`、`ThreadRead`、`TurnStart`、`TurnInterrupt` 等标准操作 ^[codex-rs/exec/src/lib.rs:38-50]
- **CLI 参数覆盖**：`CliConfigOverrides` 允许 CLI 参数覆盖配置文件中的设置 ^[codex-rs/exec/src/lib.rs:55]

**源码证据**：
- 入口文件：codex-rs/exec/src/lib.rs
- CLI 定义：codex-rs/exec/src/cli.rs:13-15
- 事件处理：codex-rs/exec/src/event_processor.rs

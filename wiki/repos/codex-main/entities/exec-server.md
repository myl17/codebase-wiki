---
type: entity
repo: codex-main
slug: exec-server
problem: 如何抽象跨本地/远程/沙箱环境的命令执行
generated: 2026-06-28
source_files:
  - codex-rs/exec-server/src/lib.rs
  - codex-rs/exec-server/src/environment.rs
  - codex-rs/exec-server/src/process.rs
---

# Exec Server

**代码位置**：codex-rs/exec-server/
**这个模块解决什么问题**：
- 实现层：通过统一的 `Environment` 抽象 + `ExecServerClient` 将命令执行从具体的本地/远程/沙箱后端解耦
- 问题层：如何抽象跨本地/远程/沙箱环境的命令执行
**对外暴露什么**：
- `Environment`：执行环境枚举（本地/远程） ^[codex-rs/exec-server/src/environment.rs:43-46]
- `EnvironmentManager`：环境管理器，负责创建和切换执行环境 ^[codex-rs/exec-server/src/environment.rs:47]
- `ExecServerClient`：执行服务器客户端，统一接口发起命令执行 ^[codex-rs/exec-server/src/client.rs:26]
- `ExecBackend`：命令执行后端 trait ^[codex-rs/exec-server/src/process.rs:54]
- `ExecProcess`：正在运行的执行进程句柄 ^[codex-rs/exec-server/src/process.rs:57-60]
- `ExecutorFileSystem`：跨环境的文件系统操作抽象 ^[codex-rs/exec-server/src/lib.rs:35]
- `ExecEnvPolicy`：执行环境策略（沙箱级别、文件系统限制等） ^[codex-rs/exec-server/src/protocol.rs:61]
- `FileSystemSandboxContext`：文件系统沙箱上下文 ^[codex-rs/exec-server/src/fs_sandbox.rs]
**它和谁交互**：
- 依赖 [[entities/sandbox-abstraction]]（sandboxing 提供底层沙箱实现）
- 依赖 [[entities/shell-escalation]]（特权命令提升执行）
- 被 [[entities/core-agent-loop]] 调用（Agent 执行工具时需要命令执行能力）
- 被 [[entities/app-server]] 引用（通过 EnvironmentManager 管理执行环境）
**为什么它是可分离的**：独立的 Rust crate，定义了清晰的 `Environment`/`ExecBackend`/`ExecutorFileSystem` 接口，可以替换后端实现

**关键机制**（源码可见）：
- **统一环境抽象**：`Environment` 枚举包含 LOCAL 和 REMOTE 两种环境，客户端无需感知底层差异 ^[codex-rs/exec-server/src/environment.rs:43-46]
- **进程生命周期**：`ExecProcess` 提供事件流（stdout/stderr delta、exit notification），支持流式输出 ^[codex-rs/exec-server/src/process.rs:57-60]
- **跨环境文件系统**：`ExecutorFileSystem` trait 统一了本地、远程、沙箱内文件操作（读目录、获取元数据、创建/删除/复制文件） ^[codex-rs/exec-server/src/lib.rs:35-42]
- **RPC 协议**：`exec-server` 定义了 client-server 通信协议，支持进程管理和文件系统操作的远程调用 ^[codex-rs/exec-server/src/protocol.rs:61-80]
- **沙箱文件系统**：`sandboxed_file_system` 模块将文件系统操作限制在沙箱根目录内 ^[codex-rs/exec-server/src/sandboxed_file_system.rs]

**源码证据**：
- 入口文件：codex-rs/exec-server/src/lib.rs
- 环境定义：codex-rs/exec-server/src/environment.rs:43-46
- 进程抽象：codex-rs/exec-server/src/process.rs:54-60

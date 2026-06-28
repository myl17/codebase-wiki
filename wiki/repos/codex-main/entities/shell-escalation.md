---
type: entity
repo: codex-main
slug: shell-escalation
problem: 如何安全地以提升权限执行 Shell 命令
generated: 2026-06-28
source_files:
  - codex-rs/shell-escalation/src/lib.rs
---

# Shell Escalation

**代码位置**：codex-rs/shell-escalation/
**这个模块解决什么问题**：
- 实现层：通过 `EscalateServer` 守护进程 + `EscalationDecision` 策略，将需要 sudo/管理员权限的命令升级后安全执行
- 问题层：如何安全地以提升权限执行 Shell 命令
**对外暴露什么**：
- `EscalateServer`：权限提升守护进程，监听 escalation 请求 ^[codex-rs/shell-escalation/src/unix.rs:17]
- `EscalationDecision`：提升决策（允许/拒绝/要求审批） ^[codex-rs/shell-escalation/src/unix.rs:20]
- `EscalationPolicy`：提升策略 trait，定义权限检查逻辑 ^[codex-rs/shell-escalation/src/unix.rs:22]
- `ShellCommandExecutor`：shell 命令执行器 trait ^[codex-rs/shell-escalation/src/unix.rs:31]
- `EscalationSession`：单次提升会话 ^[codex-rs/shell-escalation/src/unix.rs:21]
- `ResolvedPermissionProfile`：解析后的权限文件 ^[codex-rs/shell-escalation/src/unix.rs:29]
- `ESCALATE_SOCKET_ENV_VAR`：Unix socket 环境变量 ^[codex-rs/shell-escalation/src/unix.rs:5]
**它和谁交互**：
- 被 [[entities/exec-server]] 调用（需要提升权限时转发到 EscalateServer）
- 被 [[entities/core-agent-loop]] 间接使用（Agent 执行需要 sudo 的命令时）
- 与 [[entities/execpolicy]] 配合（escalation 前先经过策略检查）
**为什么它是可分离的**：独立的 crate，通过 Unix socket 通信，守护进程模式与主进程解耦

**关键机制**（源码可见）：
- **守护进程架构**：`EscalateServer` 作为独立进程运行，通过 Unix domain socket 接收提升请求，与主 Codex 进程隔离 ^[codex-rs/shell-escalation/src/unix.rs:17]
- **策略决策链**：`EscalationPolicy` trait 允许自定义权限检查逻辑，`EscalationSession` 封装单次提升的完整生命周期 ^[codex-rs/shell-escalation/src/unix.rs:21-22]
- **命令包装执行**：`main_execve_wrapper` 将命令包装后通过 execve 执行，确保权限提升不影响主进程安全 ^[codex-rs/shell-escalation/src/unix.rs:37-39]

**源码证据**：
- 入口文件：codex-rs/shell-escalation/src/lib.rs
- Unix 实现：codex-rs/shell-escalation/src/unix.rs

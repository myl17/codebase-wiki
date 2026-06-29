---
type: entity
repo: codex-main
slug: sandbox-abstraction
problem: 如何提供跨平台的可移植文件系统沙箱
generated: 2026-06-28
source_files:
  - codex-rs/sandboxing/src/lib.rs
  - codex-rs/sandboxing/src/manager.rs
  - codex-rs/sandboxing/src/bwrap.rs
---

# Sandbox Abstraction

**代码位置**：codex-rs/sandboxing/
**这个模块解决什么问题**：
- 实现层：通过 `SandboxManager` 抽象 + 平台特定后端（Linux: Landlock/bwrap, macOS: Seatbelt, Windows: windows-sandbox），对文件系统和命令执行实施可配置的沙箱策略
- 问题层：如何提供跨平台的可移植文件系统沙箱
**对外暴露什么**：
- `SandboxManager`：沙箱管理器，接收 `SandboxTransformRequest` 并返回转换后的命令 ^[codex-rs/sandboxing/src/manager.rs:15-18]
- `SandboxType`：沙箱类型枚举（None/Landlock/Seatbelt/Bubblewrap/Windows） ^[codex-rs/sandboxing/src/manager.rs:18]
- `SandboxCommand`：被沙箱包装后的命令 ^[codex-rs/sandboxing/src/manager.rs:14]
- `SandboxTransformRequest`：沙箱转换请求 ^[codex-rs/sandboxing/src/manager.rs:15]
- `SandboxablePreference`：用户对沙箱的偏好设置 ^[codex-rs/sandboxing/src/manager.rs:19]
- `get_platform_sandbox`：返回当前平台的推荐沙箱类型 ^[codex-rs/sandboxing/src/manager.rs:21]
- `compatibility_sandbox_policy_for_permission_profile`：向后兼容的沙箱策略转换 ^[codex-rs/sandboxing/src/manager.rs:20]
- Linux: `landlock` 基于 Landlock LSM 的沙箱 ^[codex-rs/sandboxing/src/landlock.rs]
- Linux: `bwrap` 基于 Bubblewrap 的容器化沙箱 ^[codex-rs/sandboxing/src/bwrap.rs]
- macOS: `seatbelt` 基于 macOS Sandbox 框架 ^[codex-rs/sandboxing/src/seatbelt.rs]
**它和谁交互**：
- 被 [[entities/exec-server]] 调用（在每个命令执行前进行沙箱转换）
- 被 [[entities/core-agent-loop]] 通过 exec-server 间接使用
- 依赖 [[entities/execpolicy]]（沙箱策略可以与执行策略组合）
**为什么它是可分离的**：独立的 crate，清晰的后端抽象，所有平台后端实现共同的 SandboxManager 接口

**关键机制**（源码可见）：
- **多后端抽象**：`SandboxManager` 封装了平台差异，调用方只需传入 `SandboxTransformRequest`，不感知底层沙箱技术 ^[codex-rs/sandboxing/src/manager.rs:15-18]
- **平台自动选择**：`get_platform_sandbox` 函数根据编译目标自动返回最佳沙箱类型 ^[codex-rs/sandboxing/src/manager.rs:21]
- **权限文件交叉**：`intersect_permission_profiles` 通过 `policy_transforms` 模块组合多个权限文件的限制 ^[codex-rs/sandboxing/src/policy_transforms.rs]
- **Landlock 规则集**：Linux 下基于 Landlock LSM 实现文件系统和网络访问控制的细粒度规则 ^[codex-rs/sandboxing/src/landlock.rs]
- **Bubblewrap 容器化**：`bwrap` 模块使用 Bubblewrap 创建最小化容器，提供进程级隔离 ^[codex-rs/sandboxing/src/bwrap.rs]

**源码证据**：
- 入口文件：codex-rs/sandboxing/src/lib.rs
- 沙箱管理器：codex-rs/sandboxing/src/manager.rs:14-21
- Bubblewrap 后端：codex-rs/sandboxing/src/bwrap.rs

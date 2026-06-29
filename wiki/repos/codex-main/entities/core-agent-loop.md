---
type: entity
repo: codex-main
slug: core-agent-loop
problem: 如何编排 AI Agent 的回合制交互循环
generated: 2026-06-28
source_files:
  - codex-rs/core/src/lib.rs
  - codex-rs/core/src/codex_thread.rs
  - codex-rs/core/src/session/mod.rs
  - codex-rs/core/src/agent/mod.rs
---

# Core Agent Loop

**代码位置**：codex-rs/core/
**这个模块解决什么问题**：
- 实现层：`CodexThread` 管理基于回合的 Agent 交互状态机，`session::Codex` 协调整体会话生命周期
- 问题层：如何编排 AI Agent 的回合制交互循环
**对外暴露什么**：
- `CodexThread`：线程级 Agent 会话对象 ^[codex-rs/core/src/codex_thread.rs:52-55]
- `ThreadConfigSnapshot`：线程配置快照，包含模型、审批策略、权限文件、工作区根目录等 ^[codex-rs/core/src/codex_thread.rs:55-75]
- `TurnContext`：回合上下文，从 session 模块暴露 ^[codex-rs/core/src/lib.rs:31]
- `AgentControl`：Agent 控制接口（注册、生成、状态管理） ^[codex-rs/core/src/agent/mod.rs:8]
- `BackgroundTerminalInfo`：后台终端信息 ^[codex-rs/core/src/lib.rs:25]
- `TryStartTurnIfIdleError`：自动空闲回合启动错误类型 ^[codex-rs/core/src/codex_thread.rs:79-115]
**它和谁交互**：
- 依赖 [[entities/tool-system]]（接收和执行工具调用）
- 依赖 [[entities/model-provider]]（通过 Provider trait 调用 LLM）
- 依赖 [[entities/exec-server]]（通过 EnvironmentManager 执行命令）
- 依赖 [[entities/hook-system]]（生命周期事件拦截）
- 依赖 [[entities/config-management]]（读取线程配置快照）
- 依赖 [[entities/rollout]]（持久化会话记录）
- 依赖 [[entities/execpolicy]]（执行策略检查）
**为什么它是可分离的**：`core` 是独立的 Rust library crate，包含 Agent 核心逻辑但不包含 UI、传输层或特定工具实现

**关键机制**（源码可见）：
- **回合状态机**：`CodexThread` 管理 Agent 的"空闲→执行→等待→完成"状态转换，通过 `try_start_turn_if_idle` 控制自动触发 ^[codex-rs/core/src/codex_thread.rs:52-115]
- **配置快照**：`ThreadConfigSnapshot` 在每次回合开始时冻结模型、权限、工作区等参数，保证回合内一致性 ^[codex-rs/core/src/codex_thread.rs:55-75]
- **Agent 注册与管控**：`agent::control` 模块提供 Agent 生成（spawn）、常驻管理（residency）、淘汰控制（eviction） ^[codex-rs/core/src/agent/control/spawn.rs]
- **会话生命周期**：`session::Codex` 协调整体会话从创建、配置、执行到销毁的全过程 ^[codex-rs/core/src/session/mod.rs:13-180]
- **多 Agent 版本支持**：`MultiAgentVersion` 类型通过 `ThreadConfigSnapshot` 中的 `session_source` 和 `forked_from_thread_id` 支持 Agent 分叉与派生 ^[codex-rs/core/src/codex_thread.rs:72-73]

**源码证据**：
- 入口文件：codex-rs/core/src/lib.rs
- 核心类型定义：codex-rs/core/src/codex_thread.rs:54-75
- 会话模块：codex-rs/core/src/session/mod.rs

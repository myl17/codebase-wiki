---
type: entity
repo: codex-main
slug: hook-system
problem: 如何在 Agent 生命周期的关键节点插入用户定义的行为拦截
generated: 2026-06-28
source_files:
  - codex-rs/hooks/src/lib.rs
  - codex-rs/hooks/src/registry.rs
  - codex-rs/hooks/src/engine.rs
  - codex-rs/hooks/src/types.rs
---

# Hook System

**代码位置**：codex-rs/hooks/
**这个模块解决什么问题**：
- 实现层：通过在 Agent 生命周期的 10 个关键事件点注册和执行用户定义的钩子脚本，实现对 Agent 行为的拦截和修改
- 问题层：如何在 Agent 生命周期的关键节点插入用户定义的行为拦截
**对外暴露什么**：
- `Hooks`：钩子注册表，管理所有钩子的注册、配置和执行 ^[codex-rs/hooks/src/registry.rs:71]
- `HooksConfig`：钩子配置 ^[codex-rs/hooks/src/registry.rs:72]
- `Hook`：单个钩子定义（名称、事件类型、匹配器、命令） ^[codex-rs/hooks/src/types.rs:76]
- `HookEvent`：钩子事件枚举 ^[codex-rs/hooks/src/types.rs:77]
- `HookPayload`：钩子执行时的负载数据 ^[codex-rs/hooks/src/types.rs:79]
- `HookResponse`：钩子执行后的响应 ^[codex-rs/hooks/src/types.rs:80]
- 10 个事件名称：PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, SessionStart, UserPromptSubmit, SubagentStart, SubagentStop, Stop ^[codex-rs/hooks/src/lib.rs:19-30]
- `PreToolUseRequest/Outcome`：工具使用前拦截 ^[codex-rs/hooks/src/events/pre_tool_use.rs:57-58]
- `PermissionRequestDecision`：权限请求决策 ^[codex-rs/hooks/src/events/permission_request.rs:52]
- `PostToolUseOutcome`：工具使用后处理结果 ^[codex-rs/hooks/src/events/post_tool_use.rs:54]
- `PreCompactOutcome/PostCompactRequest`：上下文压缩前后拦截 ^[codex-rs/hooks/src/events/compact.rs:48-51]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 在每个事件点触发钩子引擎）
- 与 [[entities/tool-system]] 配合（PreToolUse/PostToolUse 钩子在工具调用前后触发）
- 与 [[entities/plugin-system]] 配合（插件的钩子声明通过 PluginHookDeclaration 接入） ^[codex-rs/hooks/src/declarations.rs:14]
**为什么它是可分离的**：独立的 Rust crate，纯粹的钩子注册和执行引擎，不依赖任何特定的 Agent 实现

**关键机制**（源码可见）：
- **10 个生命周期事件**：覆盖从 UserPromptSubmit 到 Stop 的完整 Agent 生命周期，每个事件有独立的请求/响应类型 ^[codex-rs/hooks/src/lib.rs:19-30]
- **匹配器过滤**：`HOOK_EVENT_NAMES_WITH_MATCHERS` 定义了 8 个支持匹配器过滤的事件（工具名、压缩触发器等），非匹配器事件忽略 match 字段 ^[codex-rs/hooks/src/lib.rs:37-46]
- **命令执行引擎**：`engine` 模块通过外部命令执行钩子脚本，支持 `HookListEntry` 管理钩子列表和优先级 ^[codex-rs/hooks/src/engine.rs:17]
- **配置规则驱动**：`hook_states_from_stack` 从配置层解析钩子状态，支持多源配置合并 ^[codex-rs/hooks/src/config_rules.rs:13]
- **子 Agent 上下文**：`SubagentHookContext` 提供子 Agent 的钩子执行上下文，区分主 Agent 和子 Agent 的钩子行为 ^[codex-rs/hooks/src/events/common.rs:17]

**源码证据**：
- 入口文件：codex-rs/hooks/src/lib.rs
- 事件名称：codex-rs/hooks/src/lib.rs:19-30
- 钩子引擎：codex-rs/hooks/src/engine.rs
- 钩子类型：codex-rs/hooks/src/types.rs:76-80

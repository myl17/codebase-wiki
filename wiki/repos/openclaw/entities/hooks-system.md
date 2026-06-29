---
type: entity
repo: openclaw
slug: hooks-system
problem: "如何在 agent 生命周期的关键节点（启动、消息收发、会话变更）注入可扩展的事件处理器？"
generated: 2026-06-25
source_files:
  - src/hooks/
---

# Hooks System

**代码位置**：`src/hooks/`
**这个模块解决什么问题**：
- 实现层：事件驱动的扩展机制——从 bundled/managed/workspace 三个来源发现 hook 文件 → 按事件类型注册处理器 → 在生命周期关键点触发
- 问题层：如何在 agent 生命周期的关键节点（启动、消息收发、会话变更）注入可扩展的事件处理器？
**对外暴露什么**：
- `registerHook(eventKey, handler)` — 注册钩子处理器 ^[src/hooks/internal-hooks.ts:220]
- `triggerHook(event)` — 触发钩子事件 ^[src/hooks/internal-hooks.ts]
- `loadInternalHooks(config, opts)` — 发现、过滤、注册所有钩子 ^[src/hooks/loader.ts:79]
- `InternalHookEvent` 类型 — `{ type: "command"|"session"|"agent"|"gateway"|"message", action, sessionKey, context, timestamp, messages }` ^[src/hooks/internal-hook-types.ts:3]
- `HookEntry` — 钩子条目（Hook + parsed frontmatter + metadata + invocation policy） ^[src/hooks/types.ts:47]
- `HookSourcePolicy` — 来源策略（precedence 10-40, defaultEnableMode, override rules） ^[src/hooks/policy.ts]
**它和谁交互**：
- 依赖 [[entities/config-system]]（钩子启用/禁用配置）
- 被 [[entities/agent-runtime]] 在生命周期节点触发（agent:bootstrap, message:received 等）
- 被 [[entities/gateway]] 用于 webhook 处理（POST /hooks/wake, POST /hooks/agent）
- 被 [[entities/plugin-system]]（插件贡献的钩子）
**为什么它是可分离的**：纯事件驱动架构，通过注册/触发解耦

**关键机制**（源码可见）：
- 四个来源目录：`bundled/`（内置，如 session-memory, command-logger, boot-md） + managed + workspace + legacy config handlers ^[src/hooks/loader.ts]
- 三级过滤：enable state（配置禁用？）→ 运行时资格（OS、二进制可用性、环境变量、配置路径）→ 动态导入 ^[src/hooks/config.ts]
- 两层事件分发：通配符处理器（如 `"message"` 匹配所有 `message:*` 事件）+ 精确处理器（如 `"message:received"`） ^[src/hooks/internal-hooks.ts]
- 错误隔离：每个处理器的错误被捕获和记录，不影响其他处理器 ^[src/hooks/internal-hooks.ts]
- 生命周期事件类型：command（new）、session（start, end, patch）、agent（bootstrap, start, end）、gateway（startup, shutdown）、message（received, sent, transcribed, preprocessed） ^[src/hooks/internal-hook-types.ts]
- 工作区钩子安全提示：`maybeWarnTrustedHookSource()` 对 workspace hook 发出信任警告 ^[src/hooks/loader.ts]

**源码证据**：
- 入口文件：src/hooks/hooks.ts
- 内部钩子引擎：src/hooks/internal-hooks.ts
- 钩子加载器：src/hooks/loader.ts
- 类型定义：src/hooks/types.ts
- 策略管理：src/hooks/policy.ts
- Bundled 钩子：src/hooks/bundled/

**关联 Concept**：
- [[concepts/hooks-event-interception]]

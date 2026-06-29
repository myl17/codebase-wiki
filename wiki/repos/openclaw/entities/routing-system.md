---
type: entity
repo: openclaw
slug: routing-system
problem: "如何根据渠道、账户、对等体和组身份，将入站消息路由到正确的 agent 和会话？"
generated: 2026-06-25
source_files:
  - src/routing/
---

# Routing System

**代码位置**：`src/routing/`
**这个模块解决什么问题**：
- 实现层：通过 9 级优先级匹配（binding.peer → binding.guild+roles → binding.channel → default）解析路由绑定，生成会话键
- 问题层：如何根据渠道、账户、对等体和组身份，将入站消息路由到正确的 agent 和会话？
**对外暴露什么**：
- `resolveAgentRoute(params)` — 核心路由解析（~840 行） ^[src/routing/resolve-route.ts]
- `buildAgentMainSessionKey(agentId)` — 构建主会话键 `"agent:{id}:main"` ^[src/routing/session-key.ts]
- `buildAgentPeerSessionKey(...)` — 构建对等体会话键 ^[src/routing/session-key.ts]
- `resolveDefaultAgentId(cfg)` — 默认 agent ID 解析 ^[src/routing/resolve-route.ts]
- `AgentRouteBinding` 类型 — 路由绑定（agentId + match: channel, accountId, peer, guildId, teamId, roles） ^[src/routing/bindings.ts]
- `normalizeChannelId(raw)` — 渠道 ID 标准化 ^[src/channels/registry.ts]
**它和谁交互**：
- 依赖 [[entities/channel-system]]（渠道 ID 标准化）
- 依赖 [[entities/config-system]]（路由绑定配置）
- 依赖 [[entities/session-system]]（会话键构造）
- 被 [[entities/gateway]] 用于入站消息分发
- 被 [[entities/agent-runtime]] 用于会话键解析
**为什么它是可分离的**：纯路由解析逻辑，无副作用，通过缓存优化性能

**关键机制**（源码可见）：
- 9 级路由优先级：`binding.peer` → `binding.peer.parent` → `binding.peer.wildcard` → `binding.guild+roles` → `binding.guild` → `binding.team` → `binding.account` → `binding.channel` → `default` ^[src/routing/resolve-route.ts]
- 会话键 DM 范围：`main`（全局单会话）| `per-peer` | `per-channel-peer` | `per-account-channel-peer` ^[src/routing/session-key.ts]
- 路由缓存：`evaluatedBindingsCacheByCfg`（2000 条目）、`resolvedRouteCacheByCfg`（4000 条目） ^[src/routing/resolve-route.ts]
- 账户 ID 缓存：本地规范化缓存 512 条目 ^[src/routing/account-id.ts]
- 默认 agent ID：无绑定匹配时回退到 `resolveDefaultAgentId()` ^[src/routing/resolve-route.ts]
- 绑定评估：先评估所有匹配条件，第一个命中的绑定获胜

**源码证据**：
- 路由解析：src/routing/resolve-route.ts
- 会话键：src/routing/session-key.ts
- 账户 ID：src/routing/account-id.ts
- 绑定定义：src/routing/bindings.ts
- 账户查找：src/routing/account-lookup.ts

**关联 Concept**：
- [[concepts/session-lifecycle-management]]

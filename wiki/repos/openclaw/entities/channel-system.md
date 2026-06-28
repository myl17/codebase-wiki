---
type: entity
repo: openclaw
slug: channel-system
problem: "如何用统一的 adapter 接口抽象 25+ 消息平台（Telegram, Slack, Discord, WhatsApp 等），使同一 agent 可同时服务所有渠道？"
generated: 2026-06-25
source_files:
  - src/channels/
---

# Channel System

**代码位置**：`src/channels/`
**这个模块解决什么问题**：
- 实现层：通过 `ChannelPlugin` 类型定义 30+ 可选 adapter（config, pairing, outbound, security, messaging, threading, lifecycle 等），每个消息平台实现自己的 adapter 集合
- 问题层：如何用统一的 adapter 接口抽象 25+ 消息平台，使同一 agent 可同时服务所有渠道？
**对外暴露什么**：
- `ChannelPlugin<ResolvedAccount, Probe, Audit>` — 渠道插件完整契约类型（30+ adapter） ^[src/channels/plugins/types.plugin.ts:53-97]
- `ChannelMeta` — 用户可见元数据（label, blurb, docsPath, aliases, markdownCapable） ^[src/channels/plugins/types.core.ts]
- `ChannelCapabilities` — 渠道能力标志（chatTypes, polls, reactions, threads, media 等） ^[src/channels/plugins/types.core.ts]
- `ChannelAccountSnapshot` — 账户状态行（enabled, configured, connected, lastMessageAt） ^[src/channels/plugins/types.core.ts]
- `listChatChannels()` / `getChatChannelMeta()` — 内置渠道列表查询 ^[src/channels/registry.ts:16]
- `CHANNEL_IDS` — 内置渠道 ID 枚举（telegram, discord, slack, signal, whatsapp 等） ^[src/channels/ids.ts]
- `recordInboundSession(params)` — 入站消息会话记录 ^[src/channels/session.ts]
**它和谁交互**：
- 依赖 [[entities/plugin-sdk]]（通过 public types 暴露 adapter 契约）
- 依赖 [[entities/plugin-system]]（插件注册表提供渠道列表）
- 依赖 [[entities/routing-system]]（渠道到会话的路由映射）
- 依赖 [[entities/config-system]]（渠道配置段）
- 被所有渠道扩展（extensions/telegram, extensions/matrix, extensions/slack 等）实现
- 被 [[entities/gateway]] 用于渠道健康监控、网关方法注册
**为什么它是可分离的**：纯接口定义 + 注册表查询，不包含任何渠道具体实现

**关键机制**（源码可见）：
- 30+ adapter 分解：config→setup→pairing→security→gateway→outbound→status→messaging→threading→directory→lifecycle→doctor→streaming→agentPrompt→messageAction→allowlist→secrets→elevated→commands→resolver→heartbeat→agentTools→approvalCapability ^[src/channels/plugins/types.plugin.ts:53-97]
- 渠道注册表懒加载：从 `getActivePluginChannelRegistryFromState()` 获取，不直接导入渠道插件（避免拉入重型模块） ^[src/channels/registry.ts:28]
- 渠道 ID 双层体系：`ChatChannelId`（内置渠道）+ 插件注册的任意字符串 ID ^[src/channels/ids.ts]
- 出站适配器三种模式：direct（渠道直发）、gateway（通过网关）、hybrid（混合） ^[src/channels/plugins/types.adapters.ts]
- 渠道健康探针：每个渠道可选 `ChannelStatusAdapter` 提供连通性检测 ^[src/channels/plugins/types.core.ts]

**源码证据**：
- 核心类型：src/channels/plugins/types.plugin.ts
- 渠道能力标志：src/channels/plugins/types.core.ts
- 适配器类型：src/channels/plugins/types.adapters.ts
- 公共类型（暴露给 SDK）：src/channels/plugins/types.public.ts
- 注册表：src/channels/registry.ts
- 会话记录：src/channels/session.ts
- 边界规则：src/channels/AGENTS.md

**关联 Concept**：
- [[concepts/channel-abstraction-pattern]]

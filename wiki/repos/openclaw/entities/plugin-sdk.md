---
type: entity
repo: openclaw
slug: plugin-sdk
problem: "如何定义 core 与插件之间的公共契约，使第三方插件可以安全地扩展系统而不触及 core 内部实现？"
generated: 2026-06-25
source_files:
  - src/plugin-sdk/
---

# Plugin SDK

**代码位置**：`src/plugin-sdk/`
**这个模块解决什么问题**：
- 实现层：通过类型导出 + 工厂函数定义插件注册的完整契约，插件只能通过 `openclaw/plugin-sdk/*` 导入 core 功能
- 问题层：如何定义 core 与插件之间的公共契约，使第三方插件可以安全地扩展系统而不触及 core 内部实现？
**对外暴露什么**：
- `definePluginEntry(options)` — 非渠道插件注册工厂 ^[src/plugin-sdk/plugin-entry.ts:174-206]
- `defineSingleProviderPluginEntry(options)` — 单 provider 插件工厂（API-key 认证） ^[src/plugin-sdk/provider-entry.ts:100-168]
- `createChatChannelPlugin(options)` — 聊天渠道插件工厂 ^[src/plugin-sdk/core.ts:608]
- `Core` 类型集合：`OpenClawPluginApi`、`OpenClawPluginDefinition`、全系列 `Provider*` 类型 ^[src/plugin-sdk/core.ts:32-122]
- `ChannelContract` 轻量类型（零运行时）：`ChannelPlugin`、`BaseProbeResult`、`ChannelOutboundAdapter` 等 ^[src/plugin-sdk/channel-contract.ts:1-39]
- 运行时工具：`KeyedAsyncQueue`、`generateSecureToken`、`buildPluginConfigSchema` 等 ^[src/plugin-sdk/core.ts:154-179]
**它和谁交互**：
- 依赖 `src/channels/plugins/types.*.ts`（重新导出渠道契约类型）
- 依赖 `src/plugins/types.ts`（重新导出插件类型）
- 被所有核心渠道（src/telegram、src/discord 等）和扩展插件（extensions/）引用
- 被 [[entities/plugin-system]] 加载和验证
**为什么它是可分离的**：纯 type + factory 模块，零运行时状态，是 core 与插件之间的唯一合法边界

**关键机制**（源码可见）：
- 三层入口体系：`definePluginEntry`（通用）→ `defineSingleProviderPluginEntry`（provider 特化）→ 渠道专用工厂 ^[src/plugin-sdk/plugin-entry.ts:174]
- 窄导入路径：每个功能独立 subpath export，避免重型模块被意外加载 ^[src/plugin-sdk/AGENTS.md:25]
- `channel-contract.ts` 零运行时：仅纯类型 re-export，模块加载零成本 ^[src/plugin-sdk/channel-contract.ts:1-39]
- Provider 类型全生命周期：Auth→Catalog→Discovery→Config→Models→Runtime→Replay→Streaming→Diagnostics→Error ^[src/plugin-sdk/plugin-entry.ts:21-70]
- 无环依赖：禁止 SDK facade 之间的 back-edge re-export ^[src/plugin-sdk/AGENTS.md:33-34]

**源码证据**：
- 入口文件：src/plugin-sdk/core.ts
- 插件注册工厂：src/plugin-sdk/plugin-entry.ts
- Provider 工厂：src/plugin-sdk/provider-entry.ts
- 渠道契约：src/plugin-sdk/channel-contract.ts
- SDK 规则：src/plugin-sdk/AGENTS.md
- 导出清单：package.json（exports 字段，~100 个 subpath）

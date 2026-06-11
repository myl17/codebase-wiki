---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine]
motivated_by: [channel-isolation-decision]
sources:
  - src/channels/plugins/types.plugin.ts:53-94
---

# ChannelPlugin

`ChannelPlugin<ResolvedAccount>` 接口，统一 13+ Adapter（Messaging / Outbound / Lifecycle / Auth / Setup）。每个 IM 平台在 `extensions/` 下实现独立 npm 包，通过 `definePluginEntry` / `defineBundledChannelEntry` 注册，按需懒加载。二开时添加新平台只需实现接口并注册，不改动 core。
^[src/channels/plugins/types.plugin.ts:53-94]

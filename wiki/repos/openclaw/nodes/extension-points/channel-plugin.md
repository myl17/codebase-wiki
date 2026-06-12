---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine]
motivated_by: [channel-isolation-decision]
sources:
  - src/channels/plugins/types.plugin.ts:53-94
extracted_from:
  - architecture
  - extension-points
---

# ChannelPlugin

`ChannelPlugin<ResolvedAccount>` 接口，统一 13+ Adapter（Messaging / Outbound / Lifecycle / Auth / Setup）。每个 IM 平台在 `extensions/` 下实现独立 npm 包，通过 `definePluginEntry` / `defineBundledChannelEntry` 注册，按需懒加载。二开时添加新平台只需实现接口并注册，不改动 core。
^[src/channels/plugins/types.plugin.ts:53-94]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[openclaw/nodes/design-decisions/channel-isolation-decision]] — 该决策催生了此节点

**作用于**（targets）：
- [[openclaw/nodes/components/context-engine]] — 改动会波及此组件

**同属「插件系统」的其他仓库实例：**
- [[hermes-agent/nodes/extension-points/event-hooks]] — hermes-agent
- [[hermes-agent/nodes/extension-points/platform-adapter]] — hermes-agent
- [[hermes-agent/nodes/components/tool-registry]] — hermes-agent
- [[openclaw/nodes/extension-points/agent-harness]] — openclaw
- [[openclaw/nodes/extension-points/hook-system]] — openclaw
<!-- /generated -->

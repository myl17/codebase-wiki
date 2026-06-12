---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [ai-agent]
sources:
  - gateway/platforms/base.py:813-893
extracted_from:
  - extension-points
---

# BasePlatformAdapter

20+ 消息平台的抽象基类，统一消息收发、会话管理、媒体处理接口。新增平台只需继承实现，GatewayRunner 管理所有 adapter 生命周期并路由消息进出 AIAgent。与 OpenClaw ChannelPlugin 的差异：单一抽象基类继承 vs 13+ Adapter 接口组合。
^[gateway/platforms/base.py:813-893]

<!-- generated-wikilinks -->
## 关联

**作用于**（targets）：
- [[hermes-agent/nodes/components/ai-agent]] — 改动会波及此组件

**同属「插件系统」的其他仓库实例：**
- [[hermes-agent/nodes/extension-points/event-hooks]] — hermes-agent
- [[hermes-agent/nodes/components/tool-registry]] — hermes-agent
- [[openclaw/nodes/extension-points/agent-harness]] — openclaw
- [[openclaw/nodes/extension-points/channel-plugin]] — openclaw
- [[openclaw/nodes/extension-points/hook-system]] — openclaw
<!-- /generated -->

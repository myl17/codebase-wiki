---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [ai-agent]
sources:
  - gateway/platforms/base.py:813-893
---

# BasePlatformAdapter

20+ 消息平台的抽象基类，统一消息收发、会话管理、媒体处理接口。新增平台只需继承实现，GatewayRunner 管理所有 adapter 生命周期并路由消息进出 AIAgent。与 OpenClaw ChannelPlugin 的差异：单一抽象基类继承 vs 13+ Adapter 接口组合。
^[gateway/platforms/base.py:813-893]

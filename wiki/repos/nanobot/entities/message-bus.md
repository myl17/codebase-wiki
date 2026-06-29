---
type: entity
repo: nanobot
slug: message-bus
problem: 如何解耦 Chat Channel 和 Agent Core 之间的消息传递
generated: 2026-06-25
source_files:
  - nanobot/bus/events.py
  - nanobot/bus/queue.py
---

# Message Bus

**代码位置**：`nanobot/bus/`
**这个模块解决什么问题**：
- 实现层：基于 `asyncio.Queue` 的双向事件总线——Channel 推送 InboundMessage 到 inbound 队列，Agent 处理后推送 OutboundMessage 到 outbound 队列
- 问题层：如何解耦 Chat Channel 和 Agent Core 之间的消息传递
**对外暴露什么**：`MessageBus` 类（nanobot/bus/queue.py:8）、`InboundMessage` dataclass（nanobot/bus/events.py:9）、`OutboundMessage` dataclass（nanobot/bus/events.py:28）
**它和谁交互**：
- 被 [[entities/channel-system]] 调用（ChannelManager 从 outbound 队列消费消息，Channel 向 inbound 队列推送消息）
- 被 [[entities/agent-loop]] 调用（从 inbound 队列消费消息，向 outbound 队列推送响应）
- 被 [[entities/subagent-manager]] 调用（子 agent 完成时通过 system channel 注入结果）
**为什么它是可分离的**：纯队列抽象，无任何业务逻辑，可替换为其他消息中间件

**关键机制**（源码可见）：
- 方向隔离：`inbound: asyncio.Queue[InboundMessage]` 和 `outbound: asyncio.Queue[OutboundMessage]` 完全分离，Channel 只写 inbound 读 outbound，Agent 反之 ^[nanobot/bus/queue.py:17-18]
- Session Key：InboundMessage 通过 `session_key` 属性自动计算 `"channel:chat_id"` 作为会话标识，支持 `session_key_override` 做线程级会话隔离 ^[nanobot/bus/events.py:22-24]
- 流式元数据：通过 OutboundMessage 的 `metadata` 字典传递 `_stream_delta`、`_stream_end`、`_progress`、`_tool_hint` 等流式控制字段 ^[nanobot/bus/events.py:36]

**源码证据**：
- 入口文件：nanobot/bus/events.py、nanobot/bus/queue.py
- 核心类型/接口定义：`class MessageBus` ^[nanobot/bus/queue.py:8]

**关联 Concept**：
- [[concepts/session-lifecycle-management]]

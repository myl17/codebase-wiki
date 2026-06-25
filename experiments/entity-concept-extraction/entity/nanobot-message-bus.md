# MessageBus（nanobot）

## 是什么 / 边界
nanobot 的事件总线——基于 `asyncio.Queue` 的极简实现，将 Channel（消息收发）与 AgentLoop（编排）完全解耦。Channel 只操作 `publish_inbound()`/`consume_outbound()`，AgentLoop 只操作 `consume_inbound()`/`publish_outbound()`。两个单向队列，没有 topic、没有 filter、没有持久化。

**边界**：MessageBus 只负责消息的队列化传递，不做路由、不做转换、不做持久化。它不是消息中间件——就是两个 `asyncio.Queue`。

## 关键实现
- **inbound 队列**：Channel/Cron/Subagent → `publish_inbound()` → AgentLoop `consume_inbound()`
- **outbound 队列**：AgentLoop → `publish_outbound()` → Channel `consume_outbound()`
- **统一入站路径**：子 agent 完成后通过 `bus.publish_inbound(msg)` 注入结果、Cron 触发通过 `bus.publish_inbound()` 注入调度消息——与 IM 消息走完全相同的处理路径，AgentLoop 不需要区分来源
- **零配置**：`MessageBus()` 无需任何参数，不依赖外部服务

## 设计选择记录
- **维度**：Architecture
- **选择**：用 `asyncio.Queue` 将 Channel 和 Agent 核心完全解耦，入站消息不区分来源（IM/子 agent/Cron/Heartbeat）
- **替代方案**：直接方法调用（Channel 直接调用 AgentLoop 的方法处理消息），或使用完整消息队列中间件（Redis、RabbitMQ）
- **为什么有这个选择**：统一入站路径是 nanobot 最重要的架构简化之一——子 agent 结果和 Cron 触发不需要特殊处理路径，直接复用 IM 消息的消费管线。`asyncio.Queue` 零依赖、零配置、天然适配 asyncio 模型，对于单进程 agent 来说消息队列中间件是过度工程

# Evolve Signals — 2026-06-25 hermes-agent + openclaw

> 生成于 Step 3 问题空间匹配
> 来源：hermes-agent + openclaw 首次 ingest 的跨仓库对比
> **状态：已处理 (2026-06-25)** — 2/2 信号均为粒度不匹配，已追加子维度观察至 agent-loop-orchestration (信号1) 和 channel-abstraction-pattern (信号2)

---

## 信号 1：事件驱动的 Agent 生命周期扩展点

- **问题**：如何提供 Agent 生命周期的可扩展钩子系统
- **相关 Entity**：openclaw/hooks-system, hermes-agent/gateway-runner（gateway/hooks.py）, nanobot/agent-loop（AgentHook）
- **信号类型**：粒度不匹配
- **理由**：openclaw 的 hooks-system 是完整的独立子系统——四个来源目录 + 三级过滤 + 双层层事件匹配（通配符+精确）+ per-handler 错误隔离 + workspace 安全警告。hermes-agent 仅有 gateway 级别的轻量 hooks（gateway/hooks.py），nanobot 仅有 AgentHook 生命周期回调。三者的成熟度差距过大，openclaw 将其作为一等公民子系统，另两个作为附属回调。当前不适合独立建 Concept，可考虑作为 agent-loop-orchestration 或 subagent-orchestration 的子维度。若未来 hooks 在更多框架中演化为独立子系统，可 trigger Split。

---

## 信号 2：Channel↔Agent Core 消息传输层解耦

- **问题**：如何在 Channel 层和 Agent Core 之间插入异步消息总线以解耦
- **相关 Entity**：nanobot/message-bus, hermes-agent/gateway-runner, openclaw/gateway
- **信号类型**：粒度不匹配
- **理由**：仅 nanobot 将消息传输作为独立 entity（message-bus），通过 asyncio.Queue 实现 Channel↔Agent 的异步解耦。hermes-agent 和 openclaw 将消息流内嵌在 gateway-runner/gateway 中，不将其作为独立层。这可能说明"独立消息总线"不是此领域的普遍模式——gateway 统一处理消息流是主流做法。当前 message-bus 宜作为 session-lifecycle-management 或 channel-abstraction-pattern 的子维度存在。若未来更多框架引入独立消息总线层，可重新评估。

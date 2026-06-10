---
type: entity
category: 领域概念
---

# Context 压缩

对话上下文接近模型 context window 上限时，将中间历史 turns 用辅助 LLM 摘要压缩，以换取继续对话的容量。核心权衡：上下文容量 vs 历史信息保真度。

## 在各 repo 中的体现

- [[openclaw/dimensions/openclaw-performance-tradeoffs]] — 压缩参数：`BASE_CHUNK_RATIO=0.4`，`SAFETY_MARGIN=1.2`；摘要优先保留活跃任务状态和最后一次用户请求；`tool_result.details` 压缩前 strip
- [[openclaw/dimensions/openclaw-architecture]] — `src/context-engine/` 管理 `compact` 生命周期操作，支持可注册的 `ContextEngineFactory`
- [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] — 阈值 75% context window；结构化摘要模板 + token-budget tail 保护；失败冷却 600 秒防重试风暴

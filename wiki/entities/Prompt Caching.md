---
type: entity
category: 领域概念
---

# Prompt Caching

将 LLM 请求中的稳定前缀（system prompt、历史消息等）在 provider 侧缓存，后续 turn 命中缓存时跳过该部分的 token 计算，大幅降低多轮对话的 input token 成本（通常 ~75%）。代价是写入时有额外成本（约 1.25x），且需要维护 cache breakpoint 的位置稳定性。

## 在各 repo 中的体现

- [[openclaw/dimensions/openclaw-performance-tradeoffs]] — 通过 `OPENCLAW_CACHE_BOUNDARY` 标记切分 system prompt 稳定前缀与动态后缀，打 `cache_control: ephemeral`；支持 `1h` 长 TTL 配置
- [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] — `agent/prompt_caching.py` 采用 `system_and_3` 策略，最多 4 个 breakpoints；GatewayRunner 缓存 AIAgent 实例以跨消息保持 prefix 有效

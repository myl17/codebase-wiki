---
repo: hermes-agent
dimension: performance-tradeoffs
dimensions_version: v1.0
generated: 2026-06-09
---

# Hermes Agent — Performance Tradeoffs

## 1. Prompt Caching — 用延迟换成本

**文件**: `agent/prompt_caching.py:1-73`  
**策略**: `system_and_3` — 最多 4 个 cache breakpoints（Anthropic 上限）

```
Breakpoint 1: System prompt（跨 turn 稳定）
Breakpoints 2-4: 最后 3 条非 system 消息（滚动窗口）
```

| 权衡 | 说明 |
|---|---|
| **优化目标** | 多轮对话 input token 成本降低 ~75% |
| **牺牲** | 每次 turn 需 deep copy messages 并注入 `cache_control` markers |
| **TTL** | 默认 5 分钟（`5m`），换 1.25x 写入成本；可改为 `1h` 用于更激进缓存 ^[agent/prompt_caching.py:57-59] |
| **自动启用** | OpenRouter + Claude 模型自动启用，原生 Anthropic API 自动启用 ^[run_agent.py:809-812] |
| **Gateway 面** | GatewayRunner 缓存 AIAgent 实例以保持 prompt cache prefix 跨消息有效 ^[gateway/run.py:604-611] |

## 2. Context 压缩 — 用准确度换容量

**文件**: `agent/context_compressor.py:1-60`  
**阈值**: 75% 的模型 context window ^[agent/context_engine.py:59]

| 权衡 | 说明 |
|---|---|
| **优化目标** | 允许无限长对话不超 context window |
| **牺牲** | 中间 turns 被辅助（便宜）LLM 摘要压缩 → 信息保真度下降 |
| **压缩策略** | 结构化摘要模板 + token-budget tail 保护 + 工具输出修剪（先剪后摘要，节省 LLM 成本）^[agent/context_compressor.py:15-17] |
| **Summary budget** | 压缩内容的 20%，上限 12,000 tokens ^[agent/context_compressor.py:51-53] |
| **失败退避** | 摘要失败冷却 600 秒，防止重试风暴 ^[agent/context_compressor.py:60] |
| **用户通知** | 分层警告：85% 和 95% 阈值各通知一次（不注入 LLM，避免模型因压力提前放弃）^[run_agent.py:824-828] |

## 3. 并行工具执行 — 用复杂度换延迟

**文件**: `run_agent.py:214-311`  
**最大并行线程**: 8 workers ^[run_agent.py:237]

| 分类 | 工具 | 策略 |
|---|---|---|
| **永不并行** | `clarify` | 交互式工具，必须串行 ^[run_agent.py:214-216] |
| **安全并行** | `web_search`, `read_file`, `session_search`, `vision_analyze` 等 11 个 | 只读，无共享状态 ^[run_agent.py:219-231] |
| **路径范围并行** | `read_file`, `write_file`, `patch` | 当目标文件路径不同时可并行 ^[run_agent.py:233-234] |
| **破坏性命令** | terminal 命令中含 rm/mv/sed -i 等 | 标记为破坏性，串行执行 ^[run_agent.py:240-264] |

## 4. Smart Model Routing — 用预测准确度换成本

**文件**: `agent/smart_model_routing.py:62-118`

| 权衡 | 说明 |
|---|---|
| **优化目标** | 简单对话走便宜模型，降低平均 token 成本 |
| **牺牲** | 误判时简单对话被弱模型处理 → 质量下降 |
| **保守策略** | 仅 `< 160 字符、< 28 词、无代码块、无 URL、无复杂关键词` 的消息才路由到便宜模型 ^[agent/smart_model_routing.py:84-101] |
| **复杂关键词** | 45 个黑名单词（debug/implement/refactor/analyze/architecture/delegate 等）触发回主模型 ^[agent/smart_model_routing.py:11-46] |

## 5. Multi-Credential Pool — 用配置复杂度换可用性

**文件**: `agent/credential_pool.py`

| 权衡 | 说明 |
|---|---|
| **优化目标** | 同 provider 多 key 轮换 → rate limit 耗尽时自动切换 |
| **策略** | `fill_first`：先用第一个 key，耗尽切下一个 ^[agent/credential_pool.py:60] |
| **牺牲** | 需要管理多个 API key，配置和监控更复杂 |

## 6. Iteration Budget — 用能力上限换可控成本

**文件**: `run_agent.py:170-199`  
**默认**: 父 agent 90 轮，子 agent 50 轮 ^[run_agent.py:570] ^[run_agent.py:170-178]

| 权衡 | 说明 |
|---|---|
| **优化目标** | 防止 agent 在复杂任务上无限循环消耗 token |
| **grace call** | 耗尽后允许一次最终 API 调用（尽力产生文本响应）^[run_agent.py:815-821] |
| **execute_code 退款** | `IterationBudget.refund()` — 程序式工具调用的轮次不计入预算 ^[run_agent.py:198] |
| **不注入 LLM** | 预算耗尽不会提前给模型发送警告（之前的做法导致模型过早放弃）^[run_agent.py:818-820] |

## 7. Model Metadata 缓存 — 用过期风险换启动速度

**文件**: `run_agent.py:747-748` `agent/model_metadata.py`

| 权衡 | 说明 |
|---|---|
| **优化目标** | 避免每次启动阻塞调用 OpenAI-compatible API 获取 model metadata |
| **TTL** | 1 小时缓存 ^[run_agent.py:748] |
| **预热** | 后台线程 `threading.Thread(target=..., daemon=True)` 在 agent 初始化时启动 ^[run_agent.py:747] |

## 8. Rate Limit Tracking — 被动追踪而非主动限流

**文件**: `agent/rate_limit_tracker.py:1-51`  
**覆盖**: 12 个 `x-ratelimit-*` header（请求/分钟、请求/小时、token/分钟、token/小时 + 各自的 reset 时间）^[agent/rate_limit_tracker.py:8-20]

| 权衡 | 说明 |
|---|---|
| **策略** | 被动追踪 → 429 错误时切换 fallback，不做主动预限流 |
| **优势** | 充分利用每个 key 的配额，零浪费 |
| **代价** | 可能在耗尽边缘收到 429 → 该 turn 失败重试 |

## 9. Background Memory Prefetch — 用线程开销换延迟感知

**文件**: `agent/memory_manager.py` `agent/memory_provider.py:92-112`

| 权衡 | 说明 |
|---|---|
| **策略** | `queue_prefetch()` 在当前 turn 完成后后台触发，下一轮 `prefetch()` 返回缓存结果 ^[agent/memory_provider.py:106-112] |
| **优势** | 记忆回溯不阻塞 API 调用前的关键路径 |
| **代价** | 不是最新状态 — 上一轮的结果可能已过时 |

## 10. ACP Adapter 专用 Toolset — 用功能完备度换专注

**文件**: `toolsets.py:226-243`

| 权衡 | 说明 |
|---|---|
| **策略** | `hermes-acp` toolset 移除 messaging/audio/clarify UI 工具 |
| **优势** | 编码场景下的工具 schema 更小 → 更低的 token 开销和更精确的上下文 |
| **牺牲** | ACP 场景不提供完整 Hermes 功能（无法发送消息、TTS 等） |

---

## 性能权衡总览

| # | 优化维度 | 优化目标 | 牺牲 | 风险 |
|---|---|---|---|---|
| 1 | Prompt Caching | Input token 成本 ↓75% | Deep copy + marker 注入开销 | 5min TTL 过期后 miss |
| 2 | Context Compression | 无限长对话 | 中间信息保真度 ↓ | 重要上下文被摘要丢失 |
| 3 | 并行工具执行 | 多工具调用延迟 ↓ | 并发安全判断复杂度 | 工具间非显式依赖冲突 |
| 4 | Smart Model Routing | 简单对话成本 ↓ | 误判走弱模型 | 边界案例降质 |
| 5 | Credential Pool | Rate limit 可用性 ↑ | 多 key 管理复杂度 | key 耗尽时 429 重试延迟 |
| 6 | Iteration Budget | Token 成本可控 | 复杂任务可能被截断 | 未完成的工作丢失 |
| 7 | Metadata 缓存 | 启动速度 ↑ | 缓存过期信息不准确 | 新模型可能未被发现 |
| 8 | Rate Limit 追踪 | 配额利用率 ↑ | 无主动限流 | 429 错误时该轮浪费 |
| 9 | Memory Prefetch | 用户感知延迟 ↓ | 记忆可能过时 | 上一轮后新写入未反映 |
| 10 | ACP 精简 Toolset | Token 开销 ↓ | 功能不完整 | 编辑器中无法使用全功能 |

## 关联

- [[openclaw/dimensions/openclaw-performance-tradeoffs]]

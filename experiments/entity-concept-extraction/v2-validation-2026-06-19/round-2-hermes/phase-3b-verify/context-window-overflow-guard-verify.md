# Context Window Overflow Guard -- 验证报告

**验证时间**: 2026-06-19
**验证方法**: 以 wiki 维度页和节点页中记录的源码引用为基准，逐 claim 交叉比对
**验证范围**: 仅验证 wiki 中有对应引用的 claim；wiki 中无覆盖的细节标注为"不可验证"

---

## A. 格式完整性 Checklist

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Frontmatter (concept/generated/phase/instances) | ✅ | 字段齐全 |
| 标准化问题陈述 | ✅ | 一个明确的问题 |
| 核心关切 (4 条) | ✅ | 编号完整 |
| 实例矩阵表 | ✅ | openclaw + hermes-agent |
| 每个实例有独立分析节 | ✅ | 两个实例都有 |
| 每个实例有设计取向表 | ✅ | 都标注了满足/妥协的关切 |
| 权衡对比表 | ✅ | 8 行对比维度 |
| 关键源码引用表 | ✅ | 8 行引用 |
| 关联节 | ✅ | 链接到维度页和节点页 |

---

## B. 逐仓库逐 Claim 判定

### B1. openclaw

| # | Claim | Wiki 溯源 | 判定 | 修正建议 |
|---|-------|-----------|------|---------|
| 1 | `CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000` | openclaw-performance-tradeoffs.md:32 -- `CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000` | ✅ | -- |
| 2 | `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000` | openclaw-performance-tradeoffs.md:32 -- `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000` | ✅ | -- |
| 3 | 三源保守选择：modelsConfig / model 自报 / agentContextTokens | openclaw-performance-tradeoffs.md:32 -- "在 modelsConfig、model 自报、agentContextTokens 之间按优先级选最保守值" | ✅ | -- |
| 4 | 源码位置 `src/agents/context-window-guard.ts:4-81` | openclaw-performance-tradeoffs.md:32 -- `^[src/agents/context-window-guard.ts:4-81]` | ✅ | -- |
| 5 | `BASE_CHUNK_RATIO = 0.4` | openclaw-performance-tradeoffs.md:28 -- `BASE_CHUNK_RATIO = 0.4` | ✅ | -- |
| 6 | `MIN_CHUNK_RATIO = 0.15` | openclaw-performance-tradeoffs.md:28 -- `MIN_CHUNK_RATIO = 0.15` | ✅ | -- |
| 7 | `SAFETY_MARGIN = 1.2` (20% 缓冲) | openclaw-performance-tradeoffs.md:28 -- `SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差） | ✅ | -- |
| 8 | 源码位置 `src/agents/compaction.ts:19-40` | openclaw-performance-tradeoffs.md:28 -- `^[src/agents/compaction.ts:19-40]` | ✅ | -- |
| 9 | 压缩优先保留活跃任务状态、批处理进度、最后一次用户请求 | openclaw-performance-tradeoffs.md:28 -- "优先保留活跃任务状态、批处理进度、最后一次用户请求" | ✅ | -- |
| 10 | `tool_result.details` 在压缩前被 strip | openclaw-performance-tradeoffs.md:28 -- "`tool_result.details` 在压缩前被 strip" | ✅ | -- |
| 11 | ContextEngine 通过 `ContextEngineFactory` (exclusive slot) 注册 | openclaw-context-engine.md:15 -- "可注册的 `ContextEngineFactory`（exclusive 槽位，全局只能有一个活跃实现）" | ✅ | -- |
| 12 | CompactionProvider 分开注册 | openclaw-compaction-provider.md:15 -- "`registerCompactionProvider` 注册压缩/摘要后端" | ✅ | -- |
| 13 | 优先级：安全性 > 兼容性 > 经济性 | 实例矩阵表 row 1 | ⚠️ | Wiki 中无直接此优先级排序文字；是从设计取向推断的合理归纳，但标记为推断而非直接引用 |
| 14 | "硬下限 16,000 + 软警告 32,000" (实例矩阵表) | openclaw-performance-tradeoffs.md:32 | ✅ | -- |

### B2. hermes-agent

| # | Claim | Wiki 溯源 | 判定 | 修正建议 |
|---|-------|-----------|------|---------|
| 1 | ContextEngine ABC 定义在 `agent/context_engine.py:32-60` | hermes-agent-context-engine.md:14 -- `agent/context_engine.py:32-60` | ✅ | -- |
| 2 | 内置 Compressor / LCM 两种实现 | hermes-agent-context-engine.md:14 -- "内置 Compressor / LCM 两种实现" | ✅ | -- |
| 3 | 固定 75% 触发阈值 (`context_window * 0.75`) | hermes-agent-performance-tradeoffs.md:31 -- "75% 的模型 context window ^[agent/context_engine.py:59]" | ✅ | -- |
| 4 | 源码位置 `agent/context_engine.py:59` | hermes-agent-performance-tradeoffs.md:31 -- `^[agent/context_engine.py:59]` | ✅ | -- |
| 5 | 结构化摘要模板 | hermes-agent-performance-tradeoffs.md:37 -- "结构化摘要模板" | ✅ | -- |
| 6 | Token-budget tail 保护（保留最后 N 条消息） | hermes-agent-performance-tradeoffs.md:37 -- "token-budget tail 保护" | ✅ | -- |
| 7 | 工具输出修剪（先剪后摘要） | hermes-agent-performance-tradeoffs.md:37 -- "工具输出修剪（先剪后摘要，节省 LLM 成本）" | ✅ | -- |
| 8 | Summary budget = 20%, max 12,000 tokens | hermes-agent-performance-tradeoffs.md:38 -- "压缩内容的 20%，上限 12,000 tokens" | ✅ | -- |
| 9 | 源码位置 `agent/context_compressor.py:51-53` | hermes-agent-performance-tradeoffs.md:38 -- `^[agent/context_compressor.py:51-53]` | ✅ | -- |
| 10 | 失败冷却 600 秒 | hermes-agent-performance-tradeoffs.md:39 -- "摘要失败冷却 600 秒" | ✅ | -- |
| 11 | 源码位置 `agent/context_compressor.py:60` | hermes-agent-performance-tradeoffs.md:39 -- `^[agent/context_compressor.py:60]` | ✅ | -- |
| 12 | 85%/95% 分层告警（不注入 LLM） | hermes-agent-performance-tradeoffs.md:40 -- "分层警告：85% 和 95% 阈值各通知一次（不注入 LLM，避免模型因压力提前放弃）" | ✅ | -- |
| 13 | 源码位置 `run_agent.py:824-828` | hermes-agent-performance-tradeoffs.md:40 -- `^[run_agent.py:824-828]` | ✅ | -- |
| 14 | 实现类放入 `plugins/context_engine/<name>/` 目录 | hermes-agent-extension-points.md:112 -- "放入 `plugins/context_engine/<name>/` 目录" | ✅ | -- |
| 15 | 优先级：简单性 > 性能一致性 > 安全性 | 实例矩阵表 row 2 | ⚠️ | Wiki 中无此优先级排序文字；是从设计取向推断的合理归纳 |

---

## C. 核心关切验证

| 关切 # | 关切内容 | 是否在对比表体现 | 判定 |
|--------|---------|----------------|------|
| 1 | 压缩阈值选择（太早 vs 太晚） | 对比表行1 "触发策略" 体现了两者的不同阈值策略 | ✅ |
| 2 | Token 估算误差（安全余量） | 对比表行2 "安全余量" 直接对比 `SAFETY_MARGIN = 1.2` vs 隐含的 25% | ✅ |
| 3 | 多源保守选择 | 对比表行1 "触发策略" 体现了 openclaw 的多源选最保守值 vs hermes-agent 的固定 75% | ✅ |
| 4 | 经济代价（过早压缩浪费 LLM 调用） | 对比表行5 "压缩侧重" 中 openclaw 的可恢复性优先隐含了额外 LLM 调用成本；行8 "核心取舍" 中 openclaw "过度保守导致不必要压缩" | ✅ |

---

## D. 绝对化语言标记

| 位置 | 原文 | 类型 | 判定 |
|------|------|------|------|
| 实例矩阵表 openclaw 触发条件 | "**任何** model 不得低于此值" (hard floor 说明) | "任何" | ⚠️ 准确——硬下限就是 floor，语义上"任何 model"是合理的 |
| Design(权衡取向) openclaw | "**宁可**过度保守也**不允许**溢出" | "宁可/不允许" | ✅ 准确反映设计取向 |
| Design(权衡取向) hermes-agent | "**宁可**行为简单一致也**不做** model 级动态适配" | "宁可/不做" | ✅ 准确反映设计取向 |

无虚假绝对化语言。

---

## E. 权衡位置分类准确性

| 仓库 | Concept 中的权衡位置描述 | Wiki 维度页对应 | 判定 |
|------|------------------------|---------------|------|
| openclaw | 多源保守最小选择（硬下限 + 软警告 + 优先级 fallback） | openclaw-performance-tradeoffs.md: 在 "LLM Token 成本优化" 和 "Context Window Guard" 两节描述 | ✅ 分类一致 |
| hermes-agent | 固定 75% 阈值 | hermes-agent-performance-tradeoffs.md: 在 "Context 压缩" 节描述，阈值 75% | ✅ 分类一致 |

---

## F. 汇总计数

| 判定 | 数量 |
|------|------|
| ✅ 一致 | 23 |
| ⚠️ 推断（wiki 中无直接文字支撑但合理） | 2 |
| ❌ 错误 | 0 |
| 不可验证（wiki 中无覆盖的细节） | 0 |

**关键引用表中所有行号/常量值均与 wiki 维度页和节点页中的脚注一致。**

---

## 备注

- 所有常量值（16,000 / 32,000 / 0.4 / 0.15 / 1.2 / 75% / 20% / 12,000 / 600s）均在 wiki 维度页中有精确对应，无数值偏差。
- 实例矩阵表的 "优先级" 列是 Concept 作者从设计取向归纳出的推论，wiki 中无对应的文字声明，但不构成错误。
- openclaw 的 "失败处理" 在对比表中标记为 "未从文档中检出"，与 wiki 节点页一致——wiki 中的 compaction-provider 和 context-engine 节点页确实未提及压缩失败处理机制。

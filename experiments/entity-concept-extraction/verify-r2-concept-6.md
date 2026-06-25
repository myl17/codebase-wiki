# Concept 验证报告: context-compression-quality

**验证日期**: 2026-06-17
**源文件已读**:
- openclaw: `src/agents/compaction.ts` (44f7cba), `src/agents/compaction-planning.ts` (7fe647c), `src/agents/context-window-guard.ts` (d095cc3)
- hermes: `agent/context_engine.py` (79c31fb), `agent/context_compressor.py` (16db1be)

## 总体结论: 基本准确，2 处需修正

---

## 逐项验证

### openclaw 专项

#### 1. 摘要模型: 使用主 LLM（与执行任务的模型相同）

**Concept 页描述**: "主 LLM 直接摘要（`piGenerateSummary`），使用主对话模型本身"
**源码实际**: compaction.ts:15 — `generateSummary as agentGenerateSummary` from `./sessions/index.js`。函数 `generateSummary` 接收 `params.model`（即 ExtensionContext 的 model），不提供独立配置项。compaction.ts 无任何可配置的 summary model override。
**判定**: CORRECT（函数名已从 `piGenerateSummary` 变为 `agentGenerateSummary`，但本质相同——使用主 LLM）

#### 2. `maxHistoryShare` 默认值 = 0.5 (50%)

**Concept 页描述**: "消息超过 `maxHistoryShare * maxContextTokens`（默认 50%）时 prune"
**源码实际**: compaction-planning.ts:391: `defaultShare = isHandoff ? 0.2 : 0.5`, `maxHistoryShare = params.maxHistoryShare ?? defaultShare`
**判定**: CORRECT

#### 3. Token 预算分配策略

**Concept 页描述**: `BASE_CHUNK_RATIO`(0.4)/`MIN_CHUNK_RATIO`(0.15) 控制分块; `SAFETY_MARGIN`(1.2); `SUMMARIZATION_OVERHEAD_TOKENS = 4096`; `computeAdaptiveChunkRatio` 在平均消息 >10% context 时降级
**源码实际**: compaction-planning.ts:15-24 — 全部确认
**判定**: CORRECT

#### 4. Context Window Guard 硬阈值 ⚠ 需修正

**Concept 页描述**: "16,000 tokens 绝对下限，32,000 tokens 软警告"
**源码实际**: context-window-guard.ts:13-15:
```typescript
const CONTEXT_WINDOW_HARD_MIN_TOKENS = 4_000;
const CONTEXT_WINDOW_WARN_BELOW_TOKENS = 8_000;
const CONTEXT_WINDOW_HARD_MIN_RATIO = 0.1;
const CONTEXT_WINDOW_WARN_BELOW_RATIO = 0.2;
```
实际阈值 = `max(4000, context_length * 0.1)` 和 `max(8000, context_length * 0.2)`。

**16,000/32,000 仅对 160K context window 模型成立。** 对 200K 模型则为 20,000/40,000；对 32K 模型则为 4,000/8,000。Concept 页将动态比值结果表述为绝对常量，具有误导性。
**判定**: INACCURATE — 建议改为 "动态下限（max(4,000, context*10%)）和软警告（max(8,000, context*20%)），对典型 160K 模型分别为 16,000/32,000"

#### 5. 分块策略: 自适应 + tool call/result 边界对齐

**Concept 页描述**: "自适应分块比（大消息降为 0.15）+ tool call/result 边界对齐"
**源码实际**: compaction-planning.ts — `splitMessagesByTokenShare` 跟踪 `pendingToolCallIds`，在 `assistant` + `toolResult` 对之间不分割。`computeAdaptiveChunkRatio` 当 `avgRatio > 0.1` 时 reduce。
**判定**: CORRECT

#### 6. 摘要模板指令

**Concept 页描述**: "告知 LLM 必须保留什么（活跃任务、批处理进度、最后一次用户请求、决策及其理由、TODOs）"
**源码实际**: compaction.ts:56-64 — `MERGE_SUMMARIES_INSTRUCTIONS` 明确列出 6 项必须保留的内容
**判定**: CORRECT

#### 7. 失败退避

**Concept 页描述**: "3 次重试（500ms-5s 延迟 + 20% jitter）"
**源码实际**: compaction.ts:141-147 — `retryAsync` with `attempts: 3, minDelayMs: 500, maxDelayMs: 5000, jitter: 0.2`
**判定**: CORRECT

#### 8. 预处理: stripToolResultDetails

**Concept 页描述**: "安全机制: `tool_result.details` 在估算 token 和送入摘要前直接摘除"
**源码实际**: compaction-planning.ts:49 — `estimateMessagesTokens` 注释 "SECURITY: toolResult.details and runtime-context transcript entries must never enter LLM-facing compaction." 调用 `sanitizeCompactionMessages` → `stripToolResultDetails`
**判定**: CORRECT

---

### hermes 专项

#### 1. 压缩触发阈值: 50%（非 75%）✓

**Concept 页描述**: "ContextCompressor 的 `__init__` 中 `threshold_percent` 默认为 0.50（50%），不是 ABC 基类的 75%"
**源码实际**:
- `context_engine.py:59`: ABC 默认 `threshold_percent: float = 0.75`
- `context_compressor.py:674`: ContextCompressor `__init__` 参数 `threshold_percent: float = 0.50`
- `context_compressor.py:692`: `self.threshold_percent = threshold_percent`
- `context_compressor.py:713`: `self.threshold_tokens = max(int(self.context_length * threshold_percent), MINIMUM_CONTEXT_LENGTH)`

**判定**: CORRECT。ContexCompressor 明确覆盖 ABC 基类的 75% 为 50%。另外，`MINIMUM_CONTEXT_LENGTH` 为地板值——即使百分比计算低于此值也不会触发过早压缩。

#### 2. 摘要模型默认与主 LLM 相同 ✓

**Concept 页描述**: "默认情况下 `summary_model` 为空字符串——此时使用与主 LLM 相同的模型和 provider"
**源码实际**:
- `context_compressor.py:744`: `self.summary_model = summary_model_override or ""`
- `context_compressor.py:1512-1513`: `if self.summary_model: call_kwargs["model"] = self.summary_model` — 为空时不覆盖 model，`call_llm` 使用 runtime 的主 model/provider
**判定**: CORRECT

#### 3. Summary Budget = 20% 上限 12,000 ✓

**Concept 页描述**: "压缩内容的 20%，上限 12,000 tokens" 和 "max_summary_tokens = min(context_length * 0.05, 12000)"
**源码实际**:
- `context_compressor.py:158-161`: `_SUMMARY_RATIO = 0.20`, `_SUMMARY_TOKENS_CEILING = 12_000`, `_MIN_SUMMARY_TOKENS = 2000`
- `context_compressor.py:1021-1022`: `budget = int(content_tokens * _SUMMARY_RATIO)`, `return max(_MIN_SUMMARY_TOKENS, min(budget, self.max_summary_tokens))`
- `context_compressor.py:721-722`: `self.max_summary_tokens = min(int(self.context_length * 0.05), _SUMMARY_TOKENS_CEILING)`

**判定**: CORRECT。实际 budget 公式为 `max(2000, min(content_tokens * 0.20, max_summary_tokens))`，其中 `max_summary_tokens = min(context_length * 0.05, 12000)`。Concept 页的核心数字（20%, 12,000）完全准确。

#### 4. 600s 冷却硬编码，仅对 RuntimeError ✓

**Concept 页描述**: "600 秒冷却（不可恢复错误）/ 60 秒冷却（瞬时错误）"
**源码实际**:
- `context_compressor.py:164`: `_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600` — 硬编码常量
- `context_compressor.py:1528-1535`: `RuntimeError` → 600s 冷却
- `context_compressor.py:1587-1600`: `_is_model_not_found` (404/503) 或 summary_model != main → **自动 fallback 到主模型，不进入冷却**
- `context_compressor.py:1612-1617`: 其他未知错误若 summary_model != main → 同样尝试 fallback 主模型
- `context_compressor.py:1623`: 瞬时错误 (timeout/rate limit/network) → 60s 冷却
- `context_compressor.py:1620`: JSON decode/streaming close → 30s 冷却

**判定**: CORRECT。600s 确实是硬编码常量，仅对 RuntimeError（无 provider）使用。Concept 页对冷却分层的描述（RuntimeError→600s / 瞬时错误→60s）准确，但遗漏了 JSON decode/streaming close 的 30s 冷却——由于这属于瞬时错误的子类型，对核心理解无实质性影响。

#### 5. Tail budget = 10% context window ✓

**Concept 页描述**: "tail_token_budget = int(threshold_tokens * summary_target_ratio)，默认 50% * 20% = 10% 的 context window"
**源码实际**: `context_compressor.py:719`: `target_tokens = int(self.threshold_tokens * self.summary_target_ratio)`, `self.tail_token_budget = target_tokens`
**判定**: CORRECT

#### 6. 1.5x soft ceiling ✓

**Concept 页描述**: "walk backward 时允许超过 1.5x 软上限以避免切断大消息"
**源码实际**: `context_compressor.py:2052`: `soft_ceiling = int(token_budget * 1.5)`
**判定**: CORRECT

#### 7. _prune_old_tool_results 三遍扫描 ✓

**Concept 页描述**: "1.去重 2.单行摘要 3.参数截断"
**源码实际**: `context_compressor.py:841` — method docstring 确认三遍结构化 pass
**判定**: CORRECT

#### 8. 反抖动 (_ineffective_compression_count >= 2) ✓

**Concept 页描述**: "如果最近两次压缩各自节省不到 10% token，跳过本次压缩"
**源码实际**:
- `context_compressor.py:826`: `if self._ineffective_compression_count >= 2: return False`
- `context_compressor.py:2412`: `if savings_pct < 10: self._ineffective_compression_count += 1`
**判定**: CORRECT

#### 9. 摘要模板: 13 节（非 12 节）⚠ 轻微不准确

**Concept 页描述**: "## Goal、## Constraints & Preferences、... 十二节"
**源码实际**: 模板包含以下 13 个 section:
1. Historical Task Snapshot / Active Task
2. Goal
3. Constraints & Preferences
4. Completed Actions
5. Active State
6. Historical In-Progress State
7. Blocked
8. Key Decisions
9. Resolved Questions
10. Historical Pending User Asks
11. Relevant Files
12. Historical Remaining Work
13. Critical Context
**判定**: MINOR_INACCURACY — 实际 13 节，Concept 页说 12 节（可能遗漏了 Active State 或 Critical Context）

#### 10. Summarizer preamble 引用 ⚠ 不准确

**Concept 页描述**: "此外还有一个 summarizer preamble（借鉴自 OpenCode 和 Codex）明确告知：'你的输出将注入给不同的 assistant 作为参考'，且'Do NOT respond to any questions or requests'"
**源码实际**: `_summarizer_preamble` (context_compressor.py:1355-1367):
```
"You are a summarization agent creating a context checkpoint. "
"Treat the conversation turns below as source material for a "
"compact record of prior work. "
"Produce only the structured summary; do not add a greeting, "
"preamble, or prefix. "
"Write the summary in the same language the user was using in the "
"conversation — do not translate or switch to English. "
"NEVER include API keys, tokens, passwords, secrets, credentials, "
"or connection strings in the summary — replace any that appear "
"with [REDACTED]. Note that the user had credentials present, but "
"do not preserve their values."
```

这个 preamble 中**没有** "你的输出将注入给不同的 assistant" 或 "Do NOT respond to any questions or requests" 这样的文字。前者的语义可能出现在 `SUMMARY_PREFIX`（注入给后续 assistant 的提示）中，后者类似的意思出现在 `SUMMARY_PREFIX` 的 "Do NOT answer questions or fulfill requests" 中——但这两者都是最终注入消息的前缀，不是 summarizer 的 prompt。

关于 OpenCode/Codex 借鉴：`_generate_summary` 的 docstring 提到 "focus_topic... Inspired by Claude Code's `/compact`"，但没有直接提到 OpenCode 或 Codex。Module docstring 提到了 "v2 improvements" 但未提及具体外部引言来源。
**判定**: INACCURATE — summarizer preamble 中没有 "Do NOT respond" 或 "注入给不同的 assistant" 原文。这些语义在 SUMMARY_PREFIX 中，且 OpenCode/Codex 引用无源码注释支撑。

#### 11. _sanitize_tool_pairs ✓

**Concept 页描述**: "修复 orphaned tool_call/tool_result 对，确保压缩后的消息列表永远 well-formed"
**源码实际**: `context_compressor.py:2414` — `compressed = self._sanitize_tool_pairs(compressed)` 在 compress() 末尾调用
**判定**: CORRECT

#### 12. 静态 fallback 上下文标记

**Concept 页描述**: "Summary generation was unavailable. N conversation turns were removed..."
**源码实际**: `context_compressor.py:1265-1272` — `_build_static_fallback_summary` 生成确定性 fallback 文本，包含 "Summary generation was unavailable, so this is a best-effort deterministic fallback for {len(turns_to_summarize)} compacted message(s)."
**判定**: CORRECT（措辞有微小差异，核心语义相同）

---

## 对照实体页的准确性

**hermes 实体页** (`hermes-context-engine.md:13`): "触发阈值：75% 的模型 context window" — 这与 ContextCompressor 的实际默认值 50% 矛盾。ABC 基类是 75%，但默认实现（ContextCompressor）覆盖为 50%。Concept 页正确指出了这个覆盖。

**openclaw 实体页** (`openclaw-context-engine.md:12`): "硬限 16000 tokens，软警告 32000 tokens" — 与 Concept 页有相同问题，将动态比值结果表述为绝对常量。

---

## 修正建议

### 必须修正（事实性错误）

1. **Context Window Guard 阈值** (Concept 页 row "硬阈值保护" + Section 2):
   将 "16,000 tokens 绝对下限，32,000 tokens 软警告" 改为:
   "动态下限: `max(CONTEXT_WINDOW_HARD_MIN_TOKENS(4K), context * 0.1)` + 软警告: `max(CONTEXT_WINDOW_WARN_BELOW_TOKENS(8K), context * 0.2)`。对典型 160K 模型分别计算为 16K/32K"

2. **Summarizer preamble** (Concept 页 Section 4):
   删除 "借鉴自 OpenCode 和 Codex" 以及 '你的输出将注入给不同的 assistant' 和 'Do NOT respond to any questions or requests' 中的直接引号（这些不是源码原文）。改为准确描述 summarizer preamble 的实际措辞，并指明只对 SUMMARY_PREFIX（注入到最终消息中）使用 "Do NOT answer questions" 语义。

### 建议修正（轻微不准确）

3. **模板节数**: "十二节" → "十三节"
4. **static fallback 措辞**: 将 "Summary generation was unavailable. N conversation turns were removed to free context space but could not be summarized." 修正为与实际源码更接近的措辞。

---

## 验证通过的条目（无问题）

- openclaw: maxHistoryShare 默认 0.5、BASE_CHUNK_RATIO/MIN_CHUNK_RATIO/SAFETY_MARGIN/SUMMARIZATION_OVERHEAD_TOKENS、自适应分块、摘要指令、失败退避(retry 3x)、预处理(strip details)、分块对齐 tool call/result 边界、三层渐进降级
- hermes: threshold_percent=0.50（覆盖 ABC 的 0.75）、summary_model 默认空字符串=主模型、20% budget/12K cap、600s 硬编码冷却(RuntimeError)/60s(瞬态)、tail budget=10% context、1.5x soft ceiling、三遍工具输出剪枝、反抖动计数器、_sanitize_tool_pairs、确定性 fallback 摘要

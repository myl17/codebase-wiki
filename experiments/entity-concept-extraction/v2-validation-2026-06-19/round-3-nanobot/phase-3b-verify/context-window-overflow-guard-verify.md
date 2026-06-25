# 验证报告：context-window-overflow-guard

## 格式完整性
- [x] 问题陈述是"如何..."问题形式
- [x] 核心关切列表 >= 2 条（实际 4 条）
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段
- [x] 跨仓库对比表列数 = 仓库数（3 列）
- [x] 溯源表完整

---

## 逐仓库验证

### openclaw

**Claim 1**: "`CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000`  硬下限：任何 model 不得低于此值 / `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000`  软警告线：低于此值输出警告"

源码：`src/agents/context-window-guard.ts:4-5`
```typescript
export const CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000;
export const CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000;
```
判定：✅ 源码精确匹配

---

**Claim 2**: "守护逻辑在三类数据源之间按优先级取最保守（最小）值：1. modelsConfig 2. model 自报 3. agentContextTokens"

源码：`src/agents/context-window-guard.ts:22-57`
`resolveContextWindowInfo()` 函数：`fromModelsConfig` 优先，fallback 到 `fromModel`（model 自报），再 fallback 到 `defaultTokens`。然后 `agentContextTokens` 作为 cap——如果 `capTokens < baseInfo.tokens`，使用 capTokens（取 min）。
判定：✅ 多源保守选择逻辑正确，最终取所有数据源中的最小值

---

**Claim 3**: "`BASE_CHUNK_RATIO = 0.4` / `MIN_CHUNK_RATIO = 0.15` / `SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差）"

源码：`src/agents/compaction.ts:19-21`
```typescript
export const BASE_CHUNK_RATIO = 0.4;
export const MIN_CHUNK_RATIO = 0.15;
export const SAFETY_MARGIN = 1.2; // 20% buffer for estimateTokens() inaccuracy
```
判定：✅ 三个常量值精确匹配，注释明确标注 20% buffer

---

**Claim 4**: "压缩时优先保证可恢复性而非压缩率——优先保留活跃任务状态、批处理进度、最后一次用户请求"

源码：`src/agents/compaction.ts:24-37`（MERGE_SUMMARIES_INSTRUCTIONS）
```
"MUST PRESERVE:"
"- Active tasks and their current status (in-progress, blocked, pending)"
"- Batch operation progress (e.g., '5/17 items completed')"
"- The last thing the user requested and what was being done about it"
"- Decisions made and their rationale"
"- TODOs, open questions, and constraints"
```
判定：✅ 压缩指令明确要求保留任务状态、批处理进度、用户最后请求、决策等

---

**Claim 5**: "`tool_result.details` 在压缩前被 strip"

源码：`src/agents/compaction.ts:14`
```typescript
import { repairToolUseResultPairing, stripToolResultDetails } from "./session-transcript-repair.js";
```
判定：✅ `stripToolResultDetails` 已导入，用于压缩前清理工具输出

---

### hermes-agent

**Claim 1**: "`ContextEngine` 抽象基类（ABC），采用策略模式——实现类放入 `plugins/context_engine/<name>/` 目录"

源码：`agent/context_engine.py:1-9` + `:32`
- 模块 docstring：`"Third-party engines can replace it via the plugin system or by being placed in the plugins/context_engine/<name>/ directory."`
- `class ContextEngine(ABC)`
判定：✅ ABC 基类确认，策略目录路径与文档一致

---

**Claim 2**: "`agent/context_engine.py:59` 设置单一固定阈值：当前上下文的 token 估算值 >= model context_window * 0.75"

源码：`agent/context_engine.py:59`
```python
threshold_percent: float = 0.75
```
判定：✅ ABC 类级默认值为 0.75。需注意 `ContextCompressor.__init__` 的默认参数为 `threshold_percent: float = 0.50`（`agent/context_compressor.py:233`），实际运行时以 `__init__` 传入值为准。75% 是 ABC 类级默认值。

---

**Claim 3**: "结构化摘要模板 + tool output 修剪"（溯源表引用 `agent/context_compressor.py:15-17`）

源码：`agent/context_compressor.py:15-17`
```
# - Structured summary template with Resolved/Pending question tracking
# - Tool output pruning before LLM summarization (cheap pre-pass)
```
判定：⚠️ 溯源表引用的行号（15-17）是模块级 docstring 特性摘要，非实际实现。结构化摘要模板实现在 `:584-633`（`_template_sections` + `_generate_summary`），tool output 修剪实现在 `:333-465`（`_prune_old_tool_results`）。建议溯源表补充实际实现行号。

---

**Claim 4**: "Summary budget = 压缩内容的 20%，上限 12,000 tokens"

源码：`agent/context_compressor.py:51-53`
```python
_SUMMARY_RATIO = 0.20
_SUMMARY_TOKENS_CEILING = 12_000
```
判定：✅ 精确匹配

---

**Claim 5**: "失败冷却 600 秒"

源码：`agent/context_compressor.py:60`
```python
_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600
```
判定：✅ 精确匹配

---

**Claim 6**: "`run_agent.py:824-828` 85%/95% 分层告警（不注入 LLM）"

源码：`run_agent.py:824-828`（初始化注释）+ `run_agent.py:10688-10696`（实际实现）
- Line 827 注释：`"Tiered: fires at 85% and again at 95% of compaction threshold."`
- Lines 10685-10687 注释：`"Does not inject into messages"`
- Lines 10693-10696：实际 0.95 / 0.85 阈值判断
判定：⚠️ 溯源表仅引用 824-828（初始化注释），实际分层判断逻辑在 `:10688-10696`。建议溯源表补充实现行号。

---

### nanobot

**Claim 1**: "`agent/runner.py:552-697` 定义了四步在关键路径上自动执行的上下文治理管道"

源码：`agent/runner.py:102-107`（调用点） + `:552-697`（四个方法定义）
```python
# In main iteration loop (line 102), before _request_model (line 118):
messages = self._backfill_missing_tool_results(messages)
messages = self._microcompact(messages)
messages = self._apply_tool_result_budget(spec, messages)
messages_for_model = self._snip_history(spec, messages)
```
判定：✅ 四步定义在 552-697，在每次 iteration 的 LLM 调用前同步执行

---

**Claim 2**: "Backfill：检查前一轮响应的 tool_use 是否有对应的 tool_result，若缺失则补回"

源码：`agent/runner.py:552-591`
`_backfill_missing_tool_results()`：收集 assistant 消息中声明的 tool_call IDs 和 tool 消息中已 fulfill 的 IDs，对缺失项插入 synthetic error result。
判定：✅ 功能描述准确。`_BACKFILL_CONTENT = "[Tool result unavailable — call was interrupted or lost]"`（line 43）

---

**Claim 3**: "Microcompact：压缩 10 轮之前的 tool result 为摘要"

源码：`agent/runner.py:37` + `:593-617`
```python
_MICROCOMPACT_KEEP_RECENT = 10
```
判定：✅ 保留最近 10 个 compactable tool result，超出者被替换为摘要

---

**Claim 4**: "Tool Result Budget：对超长 tool result 按预算截断，保留头部"

源码：`agent/runner.py:619-638`
`_apply_tool_result_budget()` 对每个 tool 消息调用 `_normalize_tool_result()`，超过 `spec.max_tool_result_chars` 时 truncate。
判定：✅ 截断逻辑确认

---

**Claim 5**: "Snip History：按 token 预算从消息历史尾部裁剪老旧消息"

源码：`agent/runner.py:640-697`
`_snip_history()`：计算 `budget = context_window_tokens - max_output - _SNIP_SAFETY_BUFFER`，从尾部向前保留消息直到预算耗尽，对齐到 user message 边界。
判定：✅ 裁剪逻辑正确

---

**Claim 6**: "四步全部不可见，避免 LLM 感知压力后提前放弃或改变策略"

源码：`agent/runner.py:104-118`
Pipeline 在 `_request_model` 之前执行，LLM 收到的是处理后的 `messages_for_model`，原始 `messages` 保留用于后续迭代。
判定：✅ LLM 透明性设计正确

---

**Claim 7**: "任何一步的 bug 导致 LLM 收到损坏的上下文"

源码：`agent/runner.py:108-115`
```python
except Exception as exc:
    logger.warning("Context governance failed... using raw messages")
    messages_for_model = messages
```
判定：⚠️ 概念页描述"任何一步的 bug 或边界条件处理不当导致 LLM 收到损坏上下文"为架构风险分析。实际上异常已被 try/except 捕获并使用 fail-open 策略（回退到原始 messages）。但未被捕获的非抛异常 bug（如产生格式错误但不抛异常的输出）仍是合理的风险关注点。建议将描述从事实陈述改为风险分析措辞。

---

## 关切验证
- 关切 1（压缩阈值选择）：✅ 在对比表"触发策略"行有体现
- 关切 2（Token 估算误差）：✅ 在对比表"安全余量"行有体现
- 关切 3（多源保守选择）：✅ 在对比表"触发策略"和"核心取舍"行有体现
- 关切 4（经济代价）：✅ 在 openclaw 设计取向"接受妥协的关切"中有体现

## 追加完整性
- [x] 三个仓库在各节均有提及（实例矩阵、各节描述、对比表、选择指南、溯源表均完整覆盖 openclaw、hermes-agent、nanobot）

## 汇总
总 claim 数：18 | ✅：15 | ⚠️：3 | ❌：0
关键发现：
1. **hermes-agent context_compressor.py:15-17 行号不精确**：溯源表引用的是模块 docstring，结构化摘要模板实现在 `:584-633`，tool output 修剪实现在 `:333-465`。建议更新溯源表行号。
2. **hermes-agent run_agent.py:824-828 行号不完整**：85%/95% 分层告警的初始化注释在 824-828，但实际判断逻辑在 `:10688-10696`。建议溯源表补充实现行号。
3. **hermes-agent threshold_percent 双层默认值**：ABC 默认 0.75，ContextCompressor `__init__` 默认 0.50，实际以 `__init__` 传入值为准。概念页描述的 75% 是 ABC 类级默认值，建议加注运行时可覆盖。

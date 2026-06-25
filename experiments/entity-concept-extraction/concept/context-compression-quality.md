# context-compression-quality

## 问题陈述

如何在上下文压缩中平衡信息保真度和 token 节省？

跨仓库分析 openclaw、hermes 和 nanobot 的上下文压缩策略。openclaw 和 hermes 选择了**有损摘要**路线（依赖 LLM 生成摘要），而 nanobot 开创了完全不同的方向——**四层透明规则治理**，零 LLM 调用完成上下文清理。三者在触发条件、压缩方式、保护策略和预算分配上代表了从纯规则到 LLM 摘要的完整设计光谱。

## 核心对比

| 维度 | openclaw | hermes | nanobot |
|------|----------|--------|---------|
| 治理方式 | 主 LLM 直接摘要（`piGenerateSummary`） | 辅助 LLM 摘要（可配置便宜模型，默认同主模型） | **纯规则，零 LLM 调用** |
| 触发条件 | 消息超过 `maxHistoryShare * maxContextTokens`（默认 50%）时 prune | `prompt_tokens >= context_length * 0.50` 时 compress | **每轮 LLM 调用前无条件执行四层治理**（Backfill → Microcompact → Budget → Snip） |
| 硬阈值保护 | 动态下限 `max(4,000, context * 0.1)` + 软警告 `max(8,000, context * 0.2)`（对 160K 模型分别为 16,000/32,000） | `MINIMUM_CONTEXT_LENGTH` 地板值 | **Snip 预留 `max_output` + `_SNIP_SAFETY_BUFFER`（1024 tokens）**；无独立硬阈值 |
| 压缩前预处理 | `stripToolResultDetails`：摘除 `tool_result.details` | `_prune_old_tool_results`：工具输出替换为单行摘要 | **Backfill 修复 orphaned tool_use → Microcompact 替换旧工具输出 → Budget 截断单条超大结果** |
| 预算控制 | 通过 `BASE_CHUNK_RATIO`（0.4）/`MIN_CHUNK_RATIO`（0.15）控制分块 | 压缩内容的 20%，上限 12,000 tokens（`max_summary_tokens`） | **Snip 预算 = `context_window - max_output - 1024`**；无摘要产出预算 |
| 保护策略 | 优先保留活跃任务状态、批处理进度、最后一次用户请求 | head 消息（前 3 条）+ token-budget tail 保护 | **reverse walk 保留尾部 + user-turn 边界对齐 + 最小 4 条 fallback** |
| 失败退避 | 3 次重试（500ms-5s 延迟 + 20% jitter），然后渐进降级 | 600 秒冷却（不可恢复错误）/ 60 秒冷却（瞬时错误） | **异常时 skip 治理，直接使用原始消息（fail-open）** |
| 分块策略 | 自适应分块比（大消息降为 0.15）+ tool call/result 边界对齐 | 不分块：中间轮次直接送辅助 LLM | **不分块：单次 token 预算计算后 reverse walk 截断** |
| 迭代摘要 | 多 chunk 分别摘要后 merge（`summarizeInStages`） | 保留 `_previous_summary`，重新压缩时迭代更新 | **无摘要，无迭代** |

## 关键设计对比

### 1. 摘要生成：纯规则 vs LLM 摘要

**两者都使用 LLM 生成摘要，但有一个重要差异。**

openclaw 调用 `piGenerateSummary`（来自 `@mariozechner/pi-agent-core`），使用**主对话模型本身**（与执行任务的 LLM 是同一个）。`summarizeChunks()` 对分块后的消息逐块调用 LLM 摘要，必要时通过 `summarizeInStages()` 先对各 chunk 单独摘要再 merge。

hermes 的 `_generate_summary()` 通过 `call_llm()` 调用辅助 LLM。默认情况下 `summary_model` 为空字符串——此时使用与主 LLM **相同的模型和 provider**。但用户可通过配置 `auxiliary.compression.model` 指定一个便宜模型（如 gpt-4o-mini）。`call_llm()` 的 provider 解析链不因压缩任务而改变：OpenRouter、Nous Portal、Codex OAuth、Native Anthropic 等同样的链路。

**关键差异**：openclaw 的摘要不可脱离主 LLM（耦合在 provider 内），hermes 的摘要是可选解耦的（默认共享 provider，但 config 可拆分）。

### 2. 压缩触发条件

**两个仓库的触发阈值看似相似（都是 50% 左右），但语义不同。**

openclaw 的触发发生在 `pruneHistoryForContextShare()` 中：当估算 token 超过 `maxHistoryShare * maxContextTokens`（其中 `maxHistoryShare` 默认 0.5），开始丢弃最早的分块。这不是一个布尔条件而是一个**循环**：每轮丢弃最老的一个 chunk，修复 tool call/result 配对，重新估算，直到满足预算。此外 `context-window-guard.ts` 有动态下限 `max(CONTEXT_WINDOW_HARD_MIN_TOKENS(4,000), context * CONTEXT_WINDOW_HARD_MIN_RATIO(0.1))` 和软警告 `max(CONTEXT_WINDOW_WARN_BELOW_TOKENS(8,000), context * CONTEXT_WINDOW_WARN_BELOW_RATIO(0.2))`——对于典型 160K 模型分别计算为 16,000 和 32,000。

hermes 的 `should_compress()` 是一个**简单布尔判断**：`prompt_tokens >= threshold_tokens`（`threshold_tokens = max(context_length * 0.50, MINIMUM_CONTEXT_LENGTH)`）。注意 ContextCompressor 的 `__init__` 中 `threshold_percent` 默认为 **0.50（50%）**，不是 ABC 基类的 75%。触发后一次性执行完整的压缩管线（prune -> 确定 head/tail 边界 -> 摘要 -> 重组消息列表）。

**关键差异**：openclaw 是逐块渐进丢弃直到满足预算，hermes 是一次性全部压缩。

### 3. 预处理：strip details vs tool output pruning

两者都在 LLM 摘要前做预处理以减少输入大小，但粒度不同。

openclaw 的 `stripToolResultDetails()` 是一个**安全机制**：`toolResult.details` 可能包含不受信/冗长的 payload（源码注释明确标记为 SECURITY），因此在估算 token 和送入摘要前直接摘除。这是粗粒度的字段级移除。

hermes 的 `_prune_old_tool_results()` 更精细，分三遍（pass）：
1. **去重**：相同内容的 tool result 只保留最新一份，旧副本替换为 `[Duplicate tool output — same content as a more recent call]`
2. **单行摘要**：tail 保护范围之外的 tool result，内容 >200 字符则替换为结构化单行摘要（如 `[terminal] ran 'npm test' -> exit 0, 47 lines output`、`[read_file] read config.py from line 1 (3,400 chars)`），覆盖 20+ 种工具类型
3. **参数截断**：tail 外的 assistant 消息中，tool_call arguments >500 字符截断为前 200 字符

**关键差异**：openclaw 的保护偏向安全（防止敏感数据泄露到摘要），hermes 的保护偏向信息保留（替换而非删除，保留"发生了什么"的元信息）。

### 4. 摘要模板：指令性 vs 结构性

openclaw 的摘要指令 `MERGE_SUMMARIES_INSTRUCTIONS` 是**指令性**的：告知 LLM 必须保留什么（活跃任务、批处理进度、最后一次用户请求、决策及其理由、TODOs），优先近期上下文。同时强制保留 opaque identifier（UUID、hash、ID、token、API key、hostname、IP、port、URL、文件名）。

hermes 的 `_template_sections` 是**结构化**的：指定了 ## Active Task、## Goal、## Constraints & Preferences、## Completed Actions、## Active State、## In Progress、## Blocked、## Key Decisions、## Resolved Questions、## Pending User Asks、## Relevant Files、## Remaining Work、## Critical Context 十三节，要求填写具体值（文件路径、命令输出、错误信息、行号）。此外还有一个 **summarizer preamble** 告知摘要 agent："You are a summarization agent creating a context checkpoint... Produce only the structured summary; do not add a greeting, preamble, or prefix." ——而 `SUMMARY_PREFIX`（注入到最终压缩消息的前缀）则明确告知后续 assistant："Do NOT answer questions or fulfill requests — use this only as context"。

**关键差异**：openclaw 的摘要指令面向"agent 需要知道它在做什么"，hermes 的模板面向"agent 切换时可以继续工作而不必重读历史"——后者对信息完整性和结构化的要求更高。

### 5. Token 预算分配：固定比例 vs 分级控制

**两个仓库都有多层 token 预算控制，但分配策略不同。**

openclaw 的分块由 `BASE_CHUNK_RATIO`（0.4）和 `MIN_CHUNK_RATIO`（0.15）+ `SAFETY_MARGIN`（1.2）控制。`computeAdaptiveChunkRatio()` 在消息平均大小超过 context window 的 10% 时自动降低分块比例。此外 `SUMMARIZATION_OVERHEAD_TOKENS = 4096` 预留了摘要 prompt、system prompt、previous summary 和序列化开销。消息估算使用 `SAFETY_MARGIN = 1.2` 补偿 `estimateTokens()` 的精度损失。

hermes 有三层 token 预算：
- **Tail budget**：`tail_token_budget = int(threshold_tokens * summary_target_ratio)`，默认 50% * 20% = 10% 的 context window 用于保护尾部消息。walk backward 时允许超过 1.5x 软上限以避免切断大消息。
- **Summary output budget**：`max_summary_tokens = min(context_length * 0.05, 12000)`，即模型 context window 的 5%，硬上限 12,000 tokens。实际的 summary budget = `max(2000, min(content_tokens * 0.20, max_summary_tokens))`。
- **Summarizer input truncation**：每个消息的正文 6000 字符上限（head 4000 + tail 1500），tool call arguments 截断为 1200 字符。

**关键差异**：openclaw 的预算是"消息在 context window 中的占比"，hermes 的预算是"摘要内容在压缩量中的占比"——前者控制输入，后者控制输出。

### 6. 失败处理：渐进降级 vs 冷却退避

openclaw 的 `summarizeWithFallback()` 实现了三层渐进降级：
1. 完整摘要（所有消息）
2. 部分摘要（排除 oversized 消息，附注 `[Large message (~XK tokens) omitted from summary]`）
3. 静态 fallback：`Context contained N messages (M oversized). Summary unavailable due to size limits.`

每层内部还有 `retryAsync` 3 次重试（500ms-5s 指数退避 + 20% jitter）。失败时日志 warn 但不会阻止后续压缩尝试。

hermes 的失败处理分为三种情况：
- **RuntimeError（无 provider）**：600 秒冷却（硬编码常量 `_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600`）
- **瞬时错误（timeout/rate limit/network）**：60 秒冷却
- **summary model 不可用（404/503/model_not_found）**：自动 fallback 到主模型重试（不进入冷却）
- 所有尝试失败后，返回 None，调用方插入一个**静态 fallback 上下文标记**：`Summary generation was unavailable. N conversation turns were removed to free context space but could not be summarized.`

**关键差异**：openclaw 的失败处理偏向"尽快重试"，hermes 偏向"防止浪费（冷却）但保留自动恢复路径（fallback 主模型）"。

### 7. 反抖动（Anti-thrashing）

仅 hermes 实现了反抖动保护。`should_compress()` 检查 `_ineffective_compression_count >= 2`——如果最近两次压缩各自节省不到 10% token，跳过本次压缩并建议用户 `/new` 开启新会话或 `/compress <topic>` 聚焦压缩。这个机制防止了上下文接近饱和时无限循环压缩-只移除 1-2 条消息-再触发压缩的抖动。

openclaw 没有等效机制：`pruneHistoryForContextShare()` 每次被调用都会执行，不跟踪历史有效性。

### 8. nanobot 的四层透明规则治理

nanobot 完全不使用 LLM 做摘要，而是在每次 LLM 调用前执行四层渐进式规则清理（`runner.py:102-107`）。四层固定顺序执行，互为前置依赖：

```
Backfill → Microcompact → Budget → Snip
```

**Layer 1: Backfill（修复消息格式）**

`_backfill_missing_tool_results()` 扫描消息列表，找出 assistant 声明了 `tool_calls` 但没有对应 `tool` role 回复的孤立的 tool_call。每发现一个，紧跟在 assistant 消息后插入一条合成错误消息 `[Tool result unavailable — call was interrupted or lost]`。

这是 nanobot 独有的前置步骤。openclaw 和 hermes 都没有这一步——它们假定消息列表已经是 well-formed，直接在已有的消息上做压缩。但实际运行中，provider 中断、流截断、或中间件修改消息列表都可能产生孤立的 tool_use。Backfill 确保后续所有治理层面对的是合法消息序列，避免后续步骤因为缺 tool_result 而误判消息边界。

**Layer 2: Microcompact（定向旧工具输出替换）**

`_microcompact()` 只针对 7 种"可压缩"工具类型：`read_file`、`exec`、`grep`、`glob`、`web_search`、`web_fetch`、`list_dir`。这些工具的共同特征是输出量大且重复查看价值随时间衰减（一个 30 轮前 grep 的输出大概率不再被需要）。

硬编码规则：
- 保留最近 10 条紧凑型工具结果（`_MICROCOMPACT_KEEP_RECENT = 10`）
- 对更早的消息，如果内容超过 500 字符（`_MICROCOMPACT_MIN_CHARS`），替换为 `[tool_name result omitted from context]`
- 内容不足 500 字符的消息原样保留（小的工具输出占用空间小，不值得省略）

注意这不是摘要——不保留任何信息，只是标记"这里曾有输出但被移除了"。这是纯丢弃，不是压缩。

**Layer 3: Budget（单条超大结果截断）**

`_apply_tool_result_budget()` 通过 `_normalize_tool_result()` 对每条 tool result 逐一处理：
1. 调用 `maybe_persist_tool_result()` 将大结果持久化到 workspace 文件，内容替换为文件引用
2. 如果仍超过 `spec.max_tool_result_chars`，调用 `truncate_text()` 硬截断

这一层关注的是**单条消息的尺寸**，而非上下文窗口。它与 Microcompact 互补：Microcompact 处理的是旧消息（时间维度），Budget 处理的是单条大消息（空间维度）。

**Layer 4: Snip（尾部保留、头部丢弃）**

`_snip_history()` 是唯一涉及上下文窗口的层级：

1. **预算计算**：`budget = context_block_limit or (context_window_tokens - max_output - 1024)`。其中 `_SNIP_SAFETY_BUFFER = 1024` 为序列化、system prompt 等预留余量。
2. **提前退出**：如果 `estimate_prompt_tokens_chain()` 估算的总 token 在预算内，直接返回，不做任何修改。
3. **System 消息保持**：所有 system role 消息无条件保留，不计入 non-system 预算。
4. **Reverse walk 截断**：从消息列表尾部开始向前遍历，累加 token 数，直到超出 `remaining_budget` 时停止。保留的消息是消息列表中最新的连续 suffix。
5. **User-turn 边界对齐**：在保留的消息中，找到第一个 `role == "user"` 的消息，丢弃它之前的所有消息——保证 LLM 看到的消息序列从一个完整的 user 请求开始。
6. **合法性修复**：调用 `find_legal_message_start()` 确保保留的消息不以孤立的 tool_result 开头（tool_result 没有对应的 assistant tool_call 声明）。
7. **Fallback**：如果上述过程导致保留消息为空，保留最后 4 条非系统消息 + legal start 对齐。

关键细节——user-turn 边界对齐（`runner.py:684-688`）：
```python
if kept:
    for i, message in enumerate(kept):
        if message.get("role") == "user":
            kept = kept[i:]
            break
    start = find_legal_message_start(kept)
```
这确保 model 每次调用看到的消息序列都从一个 user 消息开始——不会出现以 assistant 的 tool_call 或孤立的 tool_result 开头的情况。openclaw 和 hermes 都没有做到这种粒度：openclaw 逐 chunk 丢弃，不保证边界；hermes 保护 head 的 3 条消息和 tail 预算，但也不保证截断点正好落在 user 消息。

**四层整体性质：**

- **确定性与透明性**：没有 LLM 参与，每层的行为可精确预测。调试时可以逐层检查中间产物。
- **零延迟零成本**：不产生额外的 API 调用。openclaw 和 hermes 的摘要都需要至少一次 LLM 调用，增加延迟和 token 成本。
- **无冷却需求**：hermes 需要 600 秒冷却防止浪费 token 做无效摘要，nanobot 不存在这个问题——规则计算成本可以忽略。
- **fail-open**：`runner.py:108-114` 中，四层治理的任一层抛异常，整个治理被跳过，直接用原始消息调用模型。这保证了治理永远不是阻塞 agent 运行的瓶颈。

## 设计取舍分析

### openclaw 的优势

- **安全性优先**：`stripToolResultDetails` 防止敏感 tool output 泄露到摘要 prompt，`IDENTIFIER_PRESERVATION_INSTRUCTIONS` 强制保留所有 opaque identifier
- **可恢复性**：摘要指令明确要求保留活跃任务状态、批处理进度和最后一次用户请求——agent 在压缩后可以直接续续工作而无需用户重新说明
- **自适应**：分块大小根据消息平均大小动态调整，大消息场景自动降低 chunk ratio 避免 chunk 超出 LLM context

### openclaw 的劣势

- **无解耦**：摘要与主 LLM 耦合——如果主 LLM 在处理任务的同时还要生成摘要，总延迟可能是 hermes 的两倍
- **无反抖动**：可能陷入无效压缩循环
- **粗粒度预处理**：仅 strip details，不像 hermes 那样保留工具调用的元信息

### hermes 的优势

- **可解耦的摘要模型**：默认与主 LLM 共享 provider 但可通过 config 拆分为便宜模型，允许用户用 gpt-4o-mini 做摘要而用 Claude Opus 做任务
- **结构化摘要模板**：12 节模板确保每次压缩输出格式一致，迭代更新时 merge 更可靠
- **多层保护**：dedup + 单行摘要 + 参数截断 + tail token budget + 反抖动 + 分层冷却
- **完整性**：`_sanitize_tool_pairs` 修复 orphaned tool_call/tool_result 对，确保压缩后的消息列表永远 well-formed

### hermes 的劣势

- **复杂度**：`_prune_old_tool_results` 三遍扫描 + 20+ 种工具类型的分支逻辑增加了维护成本
- **默认不节省**：summary model 默认为主模型（同 openclaw），需要用户主动配置才能省钱
- **硬编码常量**：600 秒冷却、200 字符最小内容阈值、3 条最小 tail 保护——这些参数不可通过 config 调整

### nanobot 的优势

- **零延迟零成本**：四层全部是规则计算，不产生额外的 LLM API 调用。openclaw 和 hermes 每次压缩至少产生一次 LLM 摘要调用（包括 prompt tokens + 输出 tokens 的费用）。
- **完全确定性**：没有 LLM 参与意味着同一输入永远产生同一输出。调试时可以直接检查每一层的中间产物，不需要分析"LLM 为什么生成这个摘要"。
- **fail-open 安全性**：任何一层抛异常都跳过整个治理，直接用原始消息调用模型（`runner.py:108-114`）。治理层永远不是阻断 agent 运行的瓶颈。
- **细粒度边界修复**：Backfill（修复 orphaned tool_use） + `find_legal_message_start`（修复 orphaned tool_result）确保消息序列始终保持 well-formed。这是 openclaw 和 hermes 都没有的系统性保障。
- **三层互补覆盖**：Microcompact（时间维度，旧消息丢弃）、Budget（空间维度，单条截断）、Snip（上下文维度，总量控制）各管一维，互不重叠。

### nanobot 的劣势

- **信息不可恢复**：Microcompact 直接丢弃旧工具输出为 `[tool_name result omitted from context]`——openclaw 和 hermes 的 LLM 摘要至少保留了"发生了什么"的语义信息，nanobot 彻底丢失。
- **过度依赖尾部局部性**：Snip 的 reverse walk 假设最有价值的信息在消息列表的最近端。如果 agent 需要在长远对话中回溯早期规划或决策（head 中的信息），nanobot 将完全失去这段上下文，而 hermes 的"保护 head + tail"策略可以覆盖。
- **无跨仓库知识累积**：openclaw 和 hermes 的 LLM 摘要可以被持久化并在后续压缩中迭代更新（`_previous_summary`），自动累积跨轮次知识。nanobot 的纯丢弃策略无法从被移除的消息中保留任何语义。
- **7 种紧凑型工具列表是硬编码**：`_COMPACTABLE_TOOLS` 是 `frozenset`，不可扩展。如果用户定义了产生大输出的自定义工具，Microcompact 无法覆盖。
- **Snip 预算计算依赖 `spec.context_window_tokens`**：如果调用方未设置此字段（默认 `None`），Snip 直接被跳过——整个上下文治理退化为仅 Backfill + Microcompact + Budget，没有总量控制。

### 什么时候纯规则治理比 LLM 摘要更合理

nanobot 的四层规则治理和 openclaw/hermes 的 LLM 摘要代表了设计光谱的两端。以下场景下纯规则治理更有优势：

| 场景 | 理由 |
|------|------|
| **高吞吐、短对话** | 每次 LLM 调用前都执行规则治理，而 openclaw/hermes 只在超阈值时触发摘要。nanobot 的 Microcompact 在 5-10 轮后就起作用，保持每条消息紧凑，防止上下文膨胀累积。每轮治理成本为零（无 API 调用）。 |
| **低延迟要求** | 摘要 LLM 调用增加 1-3 秒延迟（取决于模型和 context 大小）。nanobot 的四层规则全部是 O(n) 字符串/列表操作，延迟可忽略。 |
| **成本敏感部署** | openclaw 的主模型摘要消耗任务模型的 context tokens + output tokens；hermes 的辅助模型摘要消耗便宜模型的 tokens。nanobot 完全不产生额外费用。 |
| **可预测性 > 信息保真度** | 当 agent 的行为可调试性比信息完整性更重要时，确定性规则治理让每次运行可复现。LLM 摘要每次可能不同，增加行为不确定度。 |
| **工具调用密集** | Microcompact 精准覆盖 `read_file`/`exec`/`grep` 等高频大输出工具。这些工具的旧输出在多数场景下确实不再需要——规则丢弃的损失可控。 |

反过来，LLM 摘要更适合以下场景：

| 场景 | 理由 |
|------|------|
| **长对话、多阶段任务** | 需要跨阶段保留决策、约束、已完成工作的语义信息。LLM 摘要可以提取关键决策和上下文，纯丢弃会丢失这些。 |
| **复杂推理链** | agent 在对话早期建立了推理前提或分析框架，后期需要回溯。hermes 的"保护 head + tail"策略更适合这种场景。 |
| **跨轮次知识累积** | 迭代摘要可以自动合并新旧信息（如 hermes 的 `_previous_summary`），纯规则无此能力。 |

**三者的差异总结**：nanobot 是"最小化上下文以节省 token"的极致——不保存任何可通过工具重新获取的信息。openclaw 是"用摘要换取压缩比"——付出一次 LLM 调用的成本换取最大压缩率。hermes 在两者之间——用更便宜的可选辅助模型降低摘要成本，同时用结构化模板最大化摘要信息密度。

## 源码验证检查清单

- [x] openclaw 的 compaction 是否引入了额外的 LLM 调用来生成摘要？**是**。`summarizeChunks()` 调用 `piGenerateSummary()`，使用主对话模型生成摘要。不是纯规则压缩。
- [x] hermes 的辅助 LLM 摘要用的是什么模型（便宜模型）？与主 LLM 是否共享同一个 provider？**默认共享同一个模型和 provider**（`summary_model` 默认为空字符串，此时 `call_llm()` 使用主 runtime 的 model/provider）。可通过 config `auxiliary.compression.model` 指定便宜模型。provider 解析链不变（OpenRouter -> Nous Portal -> Codex OAuth -> Native Anthropic -> ...）。
- [x] 两个仓库的压缩触发条件是什么？openclaw：消息估算 token 超过 `maxHistoryShare * maxContextTokens`（默认 50%）时逐块丢弃；hermes：`prompt_tokens >= max(context_length * 0.50, MINIMUM_CONTEXT_LENGTH)`，注意实现是 50% 而非 ABC 基类的 75%。
- [x] hermes 的 600 秒冷却是真的 600 秒还是可配置的参数？**硬编码常量** `_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600`，不可配置。但仅对 RuntimeError（无 provider）使用全量冷却；瞬时错误使用 60 秒冷却；summary model 404/503 错误直接 fallback 主模型不进入冷却。
- [x] nanobot 的四层治理是否使用了 LLM？**否**。Backfill（纯规则插入合成错误）、Microcompact（纯规则替换）、Budget（纯规则截断）、Snip（纯规则 token 预算 + reverse walk）——四层全部是确定性算法，零 LLM 调用。
- [x] nanobot 的 Microcompact 覆盖哪些工具类型？保留多少条？**7 种硬编码工具**：`read_file`、`exec`、`grep`、`glob`、`web_search`、`web_fetch`、`list_dir`（`_COMPACTABLE_TOOLS` frozenset）。保留最近 10 条（`_MICROCOMPACT_KEEP_RECENT = 10`），内容 >500 字符（`_MICROCOMPACT_MIN_CHARS`）的旧消息替换为 `[tool_name result omitted from context]`。
- [x] nanobot 的 Snip 预算如何计算？token 预算 = `context_block_limit or (context_window_tokens - max_output - 1024)`。其中 `_SNIP_SAFETY_BUFFER = 1024`。System 消息无条件保留，non-system 消息 reverse walk 保留尾部直到超出预算。最终对齐到 user 消息边界 + `find_legal_message_start()` 修复 orphaned tool_result。
- [x] nanobot 的 Backfill 插入什么内容？插入合成 tool 消息 `[Tool result unavailable — call was interrupted or lost]`（`_BACKFILL_CONTENT` 常量）。插入位置在孤立的 assistant tool_use 声明之后、下一条消息之前。openclaw 和 hermes 没有等效步骤。
- [x] nanobot 治理失败时的行为？`runner.py:108-114` 中任一层抛异常则跳过整个治理，直接使用原始消息调用模型（fail-open）。不重试、不降级、不冷却。

## 关联实体

- [[openclaw-context-engine]] — openclaw 的 Context Engine
- [[hermes-context-engine]] — hermes 的 ContextCompressor
- [[nanobot-context-governance]] — nanobot 的四层透明规则治理

## 维度

Performance Tradeoffs

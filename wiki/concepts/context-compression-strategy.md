---
type: concept
concept: context-compression-strategy
problem: 如何在 LLM 上下文窗口有限的情况下自动压缩对话历史，保持关键信息的同时减少 token 消耗
concerns: [压缩保真度, 压缩成本（token/延迟）, Prompt Caching 兼容性]
repos: [nanobot, hermes-agent, openclaw, deepagents]
generated: 2026-06-25
---

# 上下文压缩策略

## 核心问题

LLM 的上下文窗口是有限资源。当 Agent 进行多轮工具调用（读文件、跑命令、改代码）时，对话历史会快速膨胀，直到超出模型限制或触发 API 错误。每个 Agent 框架都必须回答：如何在不丢失关键信息的前提下压缩历史？

根本张力在于**压缩保真度与成本的权衡**。最保真的方式是让另一个 LLM 阅读历史并生成结构化摘要——但这引入了额外的 token 成本和延迟，且摘要可能遗漏细节。最便宜的方式是纯规则修剪（丢弃老消息、截断长输出）——零额外成本但可能丢失关键上下文。三个框架在这条光谱上选择了不同的位置：nanobot 完全在规则侧，hermes-agent 在结构化 LLM 摘要侧，openclaw 居中。

第二个张力是 **Prompt Caching 兼容性**。压缩改变消息序列后，LLM provider 的缓存前缀（如 Anthropic 的 prompt caching）会失效。如果每次压缩后重建系统提示词缓存，可能产生比压缩节省更多的 token 消耗。hermes-agent 的 Agent 缓存机制和 openclaw 的 `ownsCompaction` 标志都在处理这个问题。

## 关切

- **压缩保真度**：压缩后关键决策、文件路径、错误信息、进行中任务是否完整保留
- **压缩成本（token/延迟）**：压缩过程本身消耗的 LLM 调用次数和 token 数，以及引入的延迟对用户体验的影响
- **Prompt Caching 兼容性**：压缩是否会破坏 provider 的缓存前缀，导致变相增加成本

## 各框架的解法

### nanobot

来源：[[repos/nanobot/entities/agent-runner]]
**解法**：完全启发性压缩，零 LLM 调用。"微压缩"将旧工具结果替换为一句话摘要，"历史裁剪"从后向前截断消息直到 token 预算内。
**实现**：
- 微压缩（_microcompact）：将超过最近 10 条（`_MICROCOMPACT_KEEP_RECENT`）的可压缩工具结果替换为 `[name result omitted from context]`，仅当内容超过 `_MICROCOMPACT_MIN_CHARS` 阈值 ^[nanobot/agent/runner.py:593-617]
- 快照式历史裁剪（_snip_history）：从后向前累加消息 token 直到预算用尽，保证从 user 消息开始、不破坏工具调用配对，预算 = context_window - max_output - safety_buffer ^[nanobot/agent/runner.py:640-697]
- 上下文治理管道：每次迭代依次执行 `_backfill_missing_tool_results` → `_microcompact` → `_snip_history`，三步顺序固定 ^[nanobot/agent/runner.py:89-107]
- 工具结果截断：`_normalize_tool_result` 按 `max_tool_result_chars` 截断单条结果（默认截断后 4000 + 尾部保留 1000）^[nanobot/agent/runner.py:619-638]
**权衡**：零额外 LLM 成本 + 零延迟 + 完全不影响 prompt caching。但保真度最低——微压缩的一行摘要完全丢失了旧工具结果的细节信息，裁剪可能截掉长对话中的关键早期上下文。适合短任务场景；长时间多文件工作可能丢失"之前读过哪个文件"等信息。

### hermes-agent

来源：[[repos/hermes-agent/entities/context-compressor]]
**解法**：三阶段压缩管线——工具结果启发性裁剪 → token 边界确定 → 调用廉价模型生成 11 字段结构化摘要。内建反震荡保护和迭代摘要模式。
**实现**：
- Phase 1 工具结果裁剪（无 LLM）：`_prune_old_tool_results()` 用启发性一句话摘要替换旧工具结果——如 `[terminal] ran \`npm test\` -> exit 0, 47 lines output`——同时去重、截断大参数 ^[agent/context_compressor.py:333]
- Phase 2 边界确定：保护头部 N 条消息（`protect_first_n=3`），按 token 预算保留尾部约 20K tokens 的近期上下文 ^[agent/context_compressor.py:827-926]
- Phase 3 结构化摘要（LLM）：`_generate_summary()` 生成 11 字段结构：Goal、Constraints & Preferences、Completed Actions（编号列表，含工具名和结果）、Active State、In Progress、Blocked、Key Decisions、Resolved Questions、Pending User Asks、Relevant Files、Remaining Work、Critical Context ^[agent/context_compressor.py:542-631]
- 反震荡保护：连续 2 次压缩各节省 <10% 时，指数退避（300s → 1800s → 3600s max），防止每轮只删 1-2 条消息的死循环 ^[agent/context_compressor.py:307-330]
- 迭代摘要：存在上轮摘要时使用 "update" 模式，合并新旧信息而非从头生成，保留已记录的决策和已完成动作 ^[agent/context_compressor.py:542-590]
- 压缩感知会话拆分：压缩后将旧消息移入子会话（`parent_session_id` 链），提示缓存可选择性保留 ^[agent/context_compressor.py:7066]
- 可插拔引擎：`ContextEngine` ABC 定义 5 个接口（`on_session_start`、`update_from_response`、`should_compress`、`compress`、`on_session_end`），支持运行时替换为自定义压缩器 ^[agent/context_engine.py:32]
**权衡**：保真度最高——11 字段结构化摘要完整记录关键决策、文件路径、进行中任务。但每次压缩消耗一次 LLM 调用（辅模型）和相应延迟。迭代摘要模式下后续压缩成本递减。反震荡保护防止了死循环但可能在极端情况下放弃压缩。压缩引入子会话链破坏简单缓存前缀，但 Agent 缓存机制在高层减轻了影响。

### openclaw

来源：[[repos/openclaw/entities/agent-runtime]]、`src/agents/compaction.ts`
**解法**：双层压缩架构——`compactEmbeddedPiSessionDirect` 负责触发、编排和会话管理；`@mariozechner/pi-coding-agent` 的 `generateSummary()` 负责每次 LLM 摘要生成。通过迭代摘要链（chunk → previousSummary → next chunk）和分阶段合并（N 段并行摘要 → prose 指令 merge）处理大规模历史。
**实现**：
- 迭代摘要链：`summarizeChunks()` 将历史消息按 token 预算分块，逐块调用 `generateSummary(chunk, previousSummary)`，每块摘要作为下一块的 previousSummary 传入，逐步累积覆盖全部历史 ^[src/agents/compaction.ts:292-341]
- MERGE_SUMMARIES_INSTRUCTIONS：当消息量过大时 `summarizeInStages()` 分 N 段独立摘要，再以 prose 指令合并。指令要求保留"活跃任务及状态、批量操作进度、用户最后请求及处理、决策及理由、TODO 和待解决问题、承诺和后续"——不是硬编码字段模板，而是自由文本 + 质量约束 ^[src/agents/compaction.ts:24-37, 444-508]
- 标识符保留策略：`strict | custom | off` 三档，strict 模式要求保留 UUID、hash、ID、token、hostname、IP、端口、URL、文件名等不透明标识符，不缩短不重建 ^[src/agents/compaction.ts:38-40, 71-82]
- 安全清理：`stripToolResultDetails()` 在摘要前剥离 `toolResult.details` 防止不可信内容注入 ^[src/agents/compaction.ts:105-109]
- 渐进式降级：完整摘要失败 → 排除超大消息做部分摘要 → 部分摘要也失败 → 回退到统计 `"Context contained N messages (M oversized). Summary unavailable."` ^[src/agents/compaction.ts:380-442]
- 可扩展指令：`customInstructions` 字符串 + `CompactionSummarizationInstructions`（identifierPolicy + identifierInstructions）拼接为最终 prompt ^[src/agents/compaction.ts:42-101]
- 触发守护：主循环中超时 + token >65% 触发，`MAX_TIMEOUT_COMPACTION_ATTEMPTS=3` 硬限制；压缩前后 hook 允许外部集成 ^[src/agents/pi-embedded-runner/run.ts:817-933]
- `ownsCompaction` 协调：标志区分内建/插件压缩，压缩后触发 `runPostCompactionSideEffects` ^[src/agents/pi-embedded-runner/compact.ts:1003-1007]
**权衡**：迭代摘要链使压缩随历史增长渐进累积，各 chunk 独立 LLM 调用避免单次超大 prompt。MERGE 指令以 prose 约束质量而非固定字段模板，摘要长度和粒度自适应。代价是 prose 指令依赖每轮 LLM 的输出纪律——可能漏掉某些维度（如"承诺和后续"易被省略），不如硬编码字段模板可靠。渐进式降级提供优雅降级路径，但最终 fallback 丢失全部语义。

### deepagents
来源：[[repos/deepagents/entities/summarization-middleware]]、[[repos/deepagents/entities/filesystem-middleware]]
**解法**：双层压缩架构——LLM 摘要压缩（SummarizationMiddleware）处理对话级压缩，工具结果驱逐（FilesystemMiddleware）处理单结果级压缩。支持三种触发策略和工具参数预截断优化。
**实现**：SummarizationMiddleware 支持 tokens/fraction/messages 三种触发策略，使用 LLM 生成摘要替换旧消息，完整历史 append 到 backend 的 `/conversation_history/{thread_id}.md`。触发时可组合多个条件，支持 ContextOverflowError 回退（未触发摘要但调用因上下文溢出失败时自动摘要）。链式摘要事件通过 `_summarization_event` 私有状态字段追踪，后续请求基于摘要+新消息重建有效消息列表。工具参数预截断在摘要前对旧消息中的 `write_file`/`edit_file` 大参数进行截断。模型感知默认值根据 `model.profile.max_input_tokens` 自动计算触发和保留阈值。FilesystemMiddleware 的 `TOOLS_EXCLUDED_FROM_EVICTION` 排除 ls/glob/grep/read_file（这些工具有自己的截断机制）。超大 HumanMessage 也可驱逐。 ^[deepagents/middleware/summarization.py:885-987, 170-207, 500-537, 646-733, 940-944; deepagents/middleware/filesystem.py:374-381, 430-451]
**权衡**：保真度中高——LLM 摘要保留关键决策和上下文，工具结果驱逐保留完整内容（写入文件系统）。压缩成本为一次 LLM 调用（可配置辅模型降低成本）。反震荡保护通过链式摘要事件（而非独立压缩）实现，优于独立压缩模式。但工具结果驱逐后依赖 Agent 自行 read_file 查看完整内容，增加了额外的工具调用。

## 对比

| 框架 | 压缩保真度 | 压缩成本（token/延迟） | Prompt Caching 兼容性 |
|------|------|------|------|
| nanobot | 低——规则裁剪丢旧消息细节，一行摘要信息量极少 | 零——无 LLM 调用，纯字符串替换和 token 估算 | 优——不改消息结构，缓存前缀不受影响 |
| hermes-agent | 高——11 字段结构化摘要保留决策、文件、进行中任务、阻塞项 | 中——每次压缩 1 次辅模型 LLM 调用 + 结构化模板 token；迭代模式后续成本递减 | 中——压缩引入子会话链；Agent 缓存机制在高层减轻影响；`protect_first_n` 保护前缀 |
| openclaw | 中——迭代摘要链 + prose 质量指令（MERGE 模板）；标识符保留策略防信息丢失 | 中——按需触发（超时+token>65%）而非主动监测；各 chunk 独立 LLM 调用可并行 | 中——`ownsCompaction` 协调内建/插件压缩；迭代摘要链不破坏消息结构 |
| deepagents | 中高——LLM 摘要 + 工具结果驱逐保存完整内容；链式摘要事件累积上下文 | 中——每次压缩一次 LLM 调用（辅模型可配）；工具参数预截断零成本；模型感知阈值减少不必要的压缩 | 中——链式摘要事件追踪；AnthropicPromptCachingMiddleware 在尾部，压缩不破坏前缀 |

## 演化记录

- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 deepagents（LLM 摘要 + 工具结果驱逐双层压缩）

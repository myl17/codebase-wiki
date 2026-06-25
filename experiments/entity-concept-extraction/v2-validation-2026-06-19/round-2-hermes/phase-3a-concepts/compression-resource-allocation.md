---
concept: compression-resource-allocation
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 在对话历史压缩中，如何分配压缩的资源预算——优先保证任务可恢复性还是用定量预算控制成本？

**问题陈述**：在对对话历史进行压缩时，如何决定压缩的资源分配策略——是优先保留任务可恢复性（让 agent 压缩后能继续执行未完成任务），还是用定量预算控制压缩成本（防止压缩本身消耗过多 token 和时间）？

**核心关切**：
- 关切 1：压缩后摘要必须保留足够信息使 agent 可恢复任务执行
- 关切 2：高压缩率必然损失细节——压缩率与保真度的零和关系
- 关切 3：工具输出通常冗长但对后续决策价值低，需特殊处理策略
- 关切 4：Token 估算存在固有误差——压缩参数需包含安全余量
- 关切 5：压缩失败后的冷却期——防止摘要失败触发重试风暴
- 关切 6：用户通知不能注入 LLM——避免模型因感知到上下文压力而提前放弃

---

## 已知权衡位置

### 位置 A：可恢复性优先压缩

**优先满足的关切**：关切 1（任务可恢复性）、关切 3（工具输出特殊处理）、关切 4（安全余量）

**接受妥协的关切**：关切 2（压缩率无硬约束，压缩可能不够激进）

**特征**：摘要指令不指定 token 预算上限，而是指定**内容优先级**——"保留 decisions、TODOs、open questions、constraints"。通过自适应分块（adaptive chunk ratio）动态决定每个 chunk 的大小，压缩激进程度由上下文窗口占比自动调节。压缩后额外注入 post-compaction 上下文刷新指令，强制 agent 重新加载工作区关键规则。

**关键机制**（源码可见）：
- 摘要指令 `MERGE_SUMMARIES_INSTRUCTIONS` 要求"Preserve decisions, TODOs, open questions, and any constraints" — 这些是任务可恢复性的最小信息单元（`compaction.ts:16-18`）
- `computeAdaptiveChunkRatio()` 根据平均消息大小动态调整 chunk 比例：当平均消息 > 10% context window 时，从 `BASE_CHUNK_RATIO = 0.4` 向 `MIN_CHUNK_RATIO = 0.15` 递减（`compaction.ts:129-148`）
- `SAFETY_MARGIN = 1.2`（20% buffer）应用于 `chunkMessagesByMaxTokens()`，补偿 `estimateTokens()` 的 `chars/4` 估算误差（`compaction.ts:13, 92-93`）
- `SUMMARIZATION_OVERHEAD_TOKENS = 4096` 预留空间给 summarization prompt、system prompt、序列化包裹层（`compaction.ts:81`）
- `tool_result.details` 在 token 估算和 LLM 摘要中均被 `stripToolResultDetails()` 剥离，防止冗长工具输出污染摘要，同时保护 token 预算（`compaction.ts:20-24, 174`）
- 摘要重试 3 次，指数退避（500ms-5000ms，jitter 0.2），非 AbortError 均重试（`compaction.ts:190-198`）
- `session_before_compact` hook 在压缩前注入：workspace AGENTS.md 的"Session Startup"和"Red Lines"节（`compaction-safeguard.ts:162-188`）、工具失败摘要、文件操作列表（`compaction-safeguard.ts:193-199`）
- Post-compaction 上下文刷新指令明确要求 agent "Execute your Session Startup sequence now"——将摘要定位为"hint, NOT a substitute"（`post-compaction-context.ts:34-39`）

**代价**：无明确压缩预算上限，极端情况下压缩可能不够激进（摘要保留太多内容）；依赖自定义指令质量——如果指令不覆盖当前任务的关键信息维度，摘要可能丢失关键上下文。

**已知实例**：openclaw

### 位置 B：定量预算压缩

**优先满足的关切**：关切 2（通过预算控制压缩程度）、关切 5（冷却期防重试风暴）、关切 6（用户通知不注入 LLM）

**接受妥协的关切**：关切 1（定量预算以固定比例分配，不按消息重要性区分配额——所有被压缩内容共享相同的 token 比例）、关切 3（工具输出处理后仍是通用占位符和简洁摘要，信息密度低于位置 A）

**特征**：摘要 token 预算为压缩内容的固定比例（20%），且有绝对上限（12,000 tokens）和下限（2,000 tokens）。压缩失败后有 600 秒冷却期。上下文压力通知只发用户，不注入消息流。引导段（handoff framing）明确将摘要定位为"背景参考，不是活跃指令"。

**关键机制**（源码可见）：
- 预算参数：`_SUMMARY_RATIO = 0.20`（压缩内容的 20%），`_SUMMARY_TOKENS_CEILING = 12_000`（绝对上限），`_MIN_SUMMARY_TOKENS = 2000`（下限）（`context_compressor.py:49-53`）
- `summary_target_ratio` 可在 config.yaml 中配置，运行时 clamp 到 `[0.10, 0.80]` 范围（`context_compressor.py:253`）
- 阈值与预算联动：summary_target_ratio 相对于 threshold_tokens 计算（`context_compressor.py:272`），而非相对于 context_length
- 失败冷却：`_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600`，超过冷却期后才允许重试压缩（`context_compressor.py:60`）
- Anti-thrashing：最近 2 次压缩各节省 <10% 则跳过压缩（`context_compressor.py:317-327`）
- Tool 输出预处理：`_prune_old_tool_results()` 将旧工具结果替换为单行摘要（如 `[terminal] ran \`npm test\` -> exit 0, 47 lines output`），用 token-budget 尾部保护取代固定消息数（`context_compressor.py:333-418`）
- 尾部保护参数可从 config.yaml 覆盖：`protect_first_n`（默认 3）、`protect_last_n`（默认 20）（`run_agent.py:1362-1363`）
- 压缩阈值可配：`compression.threshold` 默认 0.50（`run_agent.py:1360`）
- 引导段 `SUMMARY_PREFIX` 明确声明"handoff from a previous context window — treat it as background reference, NOT as active instructions"（`context_compressor.py:37-45`）
- 上下文压力预警：分层在 85%（orange）和 95%（red）的 compaction threshold 触发，通过 CLI print 和 status_callback 发给用户，**不注入 LLM 消息流**（`run_agent.py:10688-10706`）
- 预警去重：class-level dict `_context_pressure_last_warned` 跟踪每个 session 的最后警告层级和时间戳，`_CONTEXT_PRESSURE_COOLDOWN = 300` 秒内不重复警告（`run_agent.py:543-548, 10703-10705`）
- 预算耗尽不注入 LLM：`_budget_exhausted_injected = False`，之前注入预算警告的做法导致模型在复杂任务上过早放弃（`run_agent.py:820-821`）

**代价**：20% 配额不按消息重要性区分——一条包含关键架构决策的消息和一条日常确认消息共享相同的 token 比例分配，可能丢失关键上下文；且没有 post-compaction 恢复机制。预算上限（12,000）在超大上下文窗口（如 200K）上可能不够。

**已知实例**：hermes-agent

---

## 跨仓库对比

| | openclaw | hermes-agent |
|---|---|---|
| 权衡位置 | 可恢复性优先 | 定量预算 |
| 预算策略 | 无固定 token 预算；自适应 chunk 比例（0.15-0.4），由上下文窗口占比驱动 | 20% 压缩内容 token 预算，上限 12,000，下限 2,000 |
| 摘要指令核心 | "Preserve decisions, TODOs, open questions, and any constraints" | 结构化模板（Resolved/Pending 追踪）+ handoff 引导段 |
| 安全余量 | `SAFETY_MARGIN = 1.2`（20% buffer），补偿 token 估算误差 | 无额外安全余量参数；用 chars/4 估算 |
| 工具输出处理 | `stripToolResultDetails()` 完全剥离 details（安全+成本双重考量） | `_prune_old_tool_results()` 替换为单行总结（如 `[terminal] ran cmd -> exit 0, N lines`） |
| 幂等/去重 | 无 tool result 去重 | 相同 tool result 去重（MD5 hash），只保留最新完整副本 |
| 阈值触发 | 由 pi-ai 库内部的 context window guard 决定 | `threshold_percent = 0.75`（context_engine 默认）→ config.yaml 默认 0.50 |
| 压缩失败处理 | 重试 3 次（500ms-5s 指数退避）；失败时尝试 partial summarization | 600s 冷却期；连续 2 次无效压缩跳过 |
| Post-compaction | 注入上下文刷新指令（"Execute your Session Startup sequence now"） | 引导段将摘要定位为"background reference, NOT active instructions" |
| 用户通知 | 无分层预警机制（依赖底层 context window guard 的硬/软限制） | 分层预警（85%/95% of threshold），300s 去重，纯用户面，不注入 LLM |
| 迭代更新 | 前次摘要送入下次 `generateSummary()`，形成链式累积（`compaction.ts:176,188`） | `_previous_summary` 保存并在下次压缩迭代更新（`context_compressor.py:296`） |
| 优先满足的关切 | 关切 1（任务可恢复性）、关切 3（工具输出处理）、关切 4（安全余量） | 关切 2（预算控制）、关切 5（冷却期）、关切 6（用户通知不注入） |
| 接受妥协的关切 | 关切 2（无激进预算约束） | 关切 1（不按重要性区分配额）、关切 3（信息密度更低） |

---

## 选择指南

在以下场景优先选**位置 A（可恢复性优先）**：
- Agent 执行的是长跨度、多步骤任务（如大规模代码重构、跨仓库迁移），压缩后必须能从摘要中恢复任务状态
- 对话中包含大量关键决策点和约束信息——优先保留上下文完整性而非激进压缩
- Token 成本不是首要约束，上下文空间的利用效率比压缩效果更重要
- 有结构化的 workspace rules（如 AGENTS.md）可以通过 post-compaction 机制重新注入，辅助 agent 恢复状态

在以下场景优先选**位置 B（定量预算）**：
- 需要可预测的压缩成本——每次压缩消耗的 token 在固定范围内，不会因为摘要内容复杂度而剧烈波动
- 压缩失败的风险需要严格管控——冷却期防止摘要失败触发重试风暴耗尽 API 配额
- 系统在 gateway/多 session 环境下运行，上下文压力通知需要只发给用户而不污染 LLM 的消息流
- Agent 主要在对话式交互场景（而非长跨度任务执行）——中间轮次的信息丢失是可接受的

---

## 溯源

| 仓库 | 验证过的源码文件 | 关键行号 |
|------|----------------|---------|
| openclaw | `src/agents/compaction.ts` | 11-13（参数定义）, 16-18（摘要指令）, 20-24（tool details strip）, 81（overhead）, 92-93（安全余量应用）, 129-148（自适应 chunk ratio）, 190-198（重试逻辑） |
| openclaw | `src/agents/pi-extensions/compaction-safeguard.ts` | 162-188（workspace rules 注入）, 193-199（hook 事件处理）, 220-225（API key guard） |
| openclaw | `src/auto-reply/reply/post-compaction-context.ts` | 34-39（post-compaction 刷新指令） |
| hermes-agent | `agent/context_compressor.py` | 37-45（SUMMARY_PREFIX）, 49-53（预算常量）, 60（冷却期）, 230-276（__init__ 参数和阈值联动）, 296（迭代摘要）, 307-327（anti-thrashing）, 333-418（工具输出修剪去重） |
| hermes-agent | `agent/context_engine.py` | 32-60（ContextEngine ABC 定义）, 59（threshold_percent = 0.75） |
| hermes-agent | `run_agent.py` | 543-548（压力预警去重字典和冷却期）, 820-828（预算耗尽不注入+分层预警）, 10688-10709（85%/95% 分层预警发射）, 1357-1363（config.yaml 可配置参数） |

## 关联

- [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] — OpenClaw 压缩可恢复性优先设计
- [[openclaw/dimensions/openclaw-performance-tradeoffs]] — OpenClaw 性能权衡维度
- [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] — Hermes Agent 性能权衡维度

## 修复记录

**2026-06-19 验证修复**：
1. **❌ 补充 YAML frontmatter**：添加 `concept`、`generated`、`phase`、`instances` 字段，与另外两个 concept 页格式对齐。
2. **❌ 补充 `## 关联` 节**：添加 wikilink 关联到 openclaw 和 hermes-agent 的相关节点页和维度页。
3. **⚠️ 绝对化语言软化**：
   - "定量预算不考虑重要性排序，重要和不重要的信息获得相同的 token 配额" → "定量预算以固定比例分配，不按消息重要性区分配额"（wiki 确认 20% 配额存在但未确认公平分配行为）
   - "20% 配额不考虑消息的重要性——一条包含关键架构决策的消息和一条日常确认消息获得相同的 token 分配机会" → "20% 配额不按消息重要性区分——共享相同的 token 比例分配"
   - "宁愿摘要长一点也不能丢失上下文" → "优先保留上下文完整性而非激进压缩"（价值判断改为权衡描述）
4. **⚠️ wiki 覆盖范围说明**：Concept 中多处细节（`SUMMARIZATION_OVERHEAD_TOKENS = 4096`、重试 3 次 + 指数退避参数、`compaction-safeguard.ts` hook 行为、`post-compaction-context.ts` 刷新指令、`summary_target_ratio` clamp 范围、anti-thrashing 阈值、MD5 hash 去重等）在 wiki 维度页和节点页中均无独立覆盖。这些细节来自 deepwiki 文档或直接源码阅读，保留在 Concept 中但在此记录溯源差异。
5. **⚠️ 行号差异记录**：多处行号与 wiki 标注不一致（如 openclaw compaction 参数 wiki 归入 19-40 区域而 concept 分散到多行、hermes `_prune_old_tool_results` concept:333-418 vs wiki:15-17、`run_agent.py` 压力预警 concept:10688-10706 vs wiki:824-828）。这些差异来自不同文档的标注粒度不同，保留 Concept 侧标注。

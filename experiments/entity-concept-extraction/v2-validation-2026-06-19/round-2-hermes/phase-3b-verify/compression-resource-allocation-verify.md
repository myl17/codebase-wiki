# 验证报告：compression-resource-allocation

**验证时间**：2026-06-19
**验证方法**：以 wiki 维度页和节点页记录的源码引用为唯一基准，不访问原始源码
**待验证文件**：`experiments/entity-concept-extraction/v2-validation-2026-06-19/round-2-hermes/phase-3a-concepts/compression-resource-allocation.md`

---

## A. 格式完整性 Checklist

| 检查项 | 状态 | 说明 |
|--------|------|------|
| YAML frontmatter（concept/instances） | ❌ | **缺失 YAML frontmatter**。与另外两个 concept 页不同，本页缺少 `---` frontmatter 块（无 concept/generated/phase/instances 字段） |
| 标准化问题陈述 | ✅ | 明确的权衡问题：可恢复性 vs 定量预算 |
| 核心关切（6条） | ✅ | 6 条均具体、可验证 |
| 已知权衡位置 | ✅ | 位置 A（openclaw 可恢复性优先）+ 位置 B（hermes 定量预算） |
| 设计取向表（满足/妥协） | ✅ | 每个位置各有满足的关切与妥协的关切（内嵌于描述中） |
| 跨仓库对比表 | ✅ | 12 维度 x 2 仓库 |
| 选择指南 | ✅ | 4+4 条场景推荐 |
| 溯源表 | ✅ | 6 行引用（但合并了多个行号到一个单元格） |
| 关联（wikilink） | ❌ | **缺失关联节**。另外两个 concept 页有 `## 关联` 节含显式 wikilink，本页无 |

---

## B. 逐仓库逐 Claim 判定

### B1. openclaw Claims

#### Claim 1: `MERGE_SUMMARIES_INSTRUCTIONS` 要求"Preserve decisions, TODOs, open questions, and any constraints" 位于 `compaction.ts:16-18`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 语义确认**。`openclaw-compaction-recoverability-priority.md` 节点页描述："摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求——优先保证可恢复性而非压缩率"。wiki 引用 `src/agents/compaction.ts:19-40` 作为 sources，与 concept 的 16-18 相邻——摘要指令的具体措辞「Preserve decisions, TODOs, open questions, and any constraints」wiki 未逐字引用，但语义完全一致 |

#### Claim 2: `SAFETY_MARGIN = 1.2`（20% buffer）位于 `compaction.ts:13`，应用在 `compaction.ts:92-93`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 确认常量值但行号不同**。`openclaw-performance-tradeoffs.md` 维度页："`SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差）^[src/agents/compaction.ts:19-40]"。concept 页说参数定义在 11-13、应用在 92-93；wiki 将整个 compaction 参数区引用为 19-40。行号范围不一致——同一参数要么在 11-13 要么在 19-40 区域内 |

#### Claim 3: `BASE_CHUNK_RATIO = 0.4`，`MIN_CHUNK_RATIO = 0.15` 位于 `compaction.ts:129-148`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 确认常量值但行号不同**。`openclaw-performance-tradeoffs.md` 维度页："`BASE_CHUNK_RATIO = 0.4`、`MIN_CHUNK_RATIO = 0.15` ^[src/agents/compaction.ts:19-40]"。concept 页将这些值关联到 `computeAdaptiveChunkRatio()` 函数（129-148）；wiki 将其归入 19-40 的一般参数区 |

#### Claim 4: `SUMMARIZATION_OVERHEAD_TOKENS = 4096` 位于 `compaction.ts:81`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认此常量**。wiki 维度页和节点页均未提及 `SUMMARIZATION_OVERHEAD_TOKENS` 或 4096 值 |

#### Claim 5: `stripToolResultDetails()` 剥离 tool_result.details 位于 `compaction.ts:20-24, 174`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 确认**。`openclaw-compaction-recoverability-priority.md`："`tool_result.details` 在压缩前 strip，防止冗长工具输出污染摘要"。`openclaw-performance-tradeoffs.md`："tool_result.details 在压缩前被 strip" |

#### Claim 6: 摘要重试 3 次，指数退避（500ms-5000ms，jitter 0.2），非 AbortError 均重试 位于 `compaction.ts:190-198`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认重试参数**。wiki 确认了 compaction 机制的存在，但未描述重试次数、退避间隔、jitter 值 |

#### Claim 7: `session_before_compact` hook 注入 workspace AGENTS.md 的"Session Startup"和"Red Lines"节 位于 `compaction-safeguard.ts:162-188`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖此文件**。wiki 维度页和节点页均未提及 `compaction-safeguard.ts`。`openclaw-extension-points.md` 维度页列出了 28 个 hook 名，含 `before_compaction` 和 `after_compaction`，但未描述 hook handler 的具体行为 |

#### Claim 8: Post-compaction 上下文刷新指令位于 `post-compaction-context.ts:34-39`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖此文件**。wiki 未提及 `post-compaction-context.ts` |

#### Claim 9: 压缩重试的指数退避参数（500ms-5000ms, jitter 0.2）

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认**。wiki 未记录重试机制的具体参数 |

---

### B2. hermes-agent Claims

#### Claim 1: 预算参数 `_SUMMARY_RATIO = 0.20`、`_SUMMARY_TOKENS_CEILING = 12_000`、`_MIN_SUMMARY_TOKENS = 2000` 位于 `context_compressor.py:49-53`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 确认参数值但行号略有不同**。`hermes-agent-performance-tradeoffs.md` 维度页："Summary budget: 压缩内容的 20%，上限 12,000 tokens ^[agent/context_compressor.py:51-53]"。concept 页说 49-53，wiki 说 51-53——差值极小（差 2 行），wiki 未提及 `_MIN_SUMMARY_TOKENS = 2000` 下限值 |

#### Claim 2: 失败冷却 `_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600` 位于 `context_compressor.py:60`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-performance-tradeoffs.md` 维度页："摘要失败冷却 600 秒，防止重试风暴 ^[agent/context_compressor.py:60]" |

#### Claim 3: `summary_target_ratio` 可在 config.yaml 配置，clamp 到 `[0.10, 0.80]` 位于 `context_compressor.py:253`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认 clamp 范围**。wiki 确认了 20% 的预算比例存在，但未记录 config.yaml 可配性和 [0.10, 0.80] clamp 范围 |

#### Claim 4: `SUMMARY_PREFIX` 声明"handoff from a previous context window — treat it as background reference, NOT as active instructions" 位于 `context_compressor.py:37-45`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认此常量**。wiki 未提及 `SUMMARY_PREFIX` 或其具体措辞 |

#### Claim 5: anti-thrashing：最近 2 次压缩各节省 <10% 则跳过 位于 `context_compressor.py:317-327`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认 anti-thrashing 机制**。wiki 维度页描述了"失败退避 600 秒"但未提及连续无效压缩跳过逻辑 |

#### Claim 6: `_prune_old_tool_results()` 将旧工具结果替换为单行摘要 位于 `context_compressor.py:333-418`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 确认行为但行号不同**。`hermes-agent-performance-tradeoffs.md`："工具输出修剪（先剪后摘要，节省 LLM 成本）^[agent/context_compressor.py:15-17]"。concept 页说功能在 333-418，wiki 引用 15-17——行号相差极大，可能引用不同函数 |

#### Claim 7: 上下文压力预警分层在 85%（orange）和 95%（red）位于 `run_agent.py:10688-10706`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 确认行为但行号不同**。`hermes-agent-performance-tradeoffs.md`："分层警告：85% 和 95% 阈值各通知一次（不注入 LLM，避免模型因压力提前放弃）^[run_agent.py:824-828]"。concept 页说 10688-10709，wiki 说 824-828——同一文件但行号相差约 9800 行 |

#### Claim 8: 预警去重 `_CONTEXT_PRESSURE_COOLDOWN = 300` 位于 `run_agent.py:543-548`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认冷却值**。wiki 提到"各通知一次"但未明确 300 秒去重间隔 |

#### Claim 9: `_budget_exhausted_injected = False`（预算耗尽不注入 LLM）位于 `run_agent.py:820-821`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 语义确认**。`hermes-agent-performance-tradeoffs.md`："预算耗尽不会提前给模型发送警告（之前的做法导致模型过早放弃）^[run_agent.py:818-820]"。concept 页说 820-821，wiki 说 818-820——相邻行号，同一逻辑 |

#### Claim 10: context_engine 默认 `threshold_percent = 0.75` 位于 `context_engine.py:59`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-performance-tradeoffs.md`："阈值: 75% 的模型 context window ^[agent/context_engine.py:59]" |

#### Claim 11: config.yaml 默认 `compression.threshold = 0.50` 位于 `run_agent.py:1360`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认 config.yaml 默认值**。wiki 确认了 context_engine 的 75% 阈值，但未提及 config.yaml 中可覆盖为 0.50 的独立参数。需注意 0.75 和 0.50 是两个不同层级的阈值参数，可能均为正确 |

#### Claim 12: 相同 tool result 去重（MD5 hash），只保留最新完整副本

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认去重机制**。wiki 维度页描述"工具输出修剪"但未提及 MD5 hash 去重 |

---

## C. 关切验证

### 关切 1：压缩后摘要必须保留足够信息使 agent 可恢复任务执行

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 摘要指令指定内容优先级 + post-compaction 上下文刷新 | ✅ wiki 确认"优先保证可恢复性" |
| hermes-agent | 结构化模板（Resolved/Pending 追踪）+ handoff 引导段 | ⚠️ wiki 确认结构化摘要模板存在，但未确认 post-compaction 恢复机制 |

**跨仓库对比表体现**：✅ 第 3 行"摘要指令核心" + 第 8 行"Post-compaction"对应

### 关切 2：高压缩率必然损失细节——压缩率与保真度的零和关系

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 无固定 token 预算，允许保留更多细节 | ✅ wiki 确认无固定预算 |
| hermes-agent | 20% 预算 + 12,000 上限，主动约束压缩程度 | ✅ wiki 确认预算参数 |

**跨仓库对比表体现**：✅ 第 2 行"预算策略"直接对应

### 关切 3：工具输出通常冗长但对后续决策价值低，需特殊处理策略

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | stripToolResultDetails() 完全剥离 details | ✅ wiki 确认 strip |
| hermes-agent | _prune_old_tool_results() 替换为单行总结 | ⚠️ wiki 确认修剪但行号不同 |

**跨仓库对比表体现**：✅ 第 5 行"工具输出处理"直接对应

### 关切 4：Token 估算存在固有误差——压缩参数需包含安全余量

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | SAFETY_MARGIN = 1.2（20% buffer） | ✅ wiki 确认 |
| hermes-agent | 用 chars/4 估算，无额外安全余量 | ⚠️ wiki 未确认 chars/4 估算方式 |

**跨仓库对比表体现**：✅ 第 4 行"安全余量"直接对应

### 关切 5：压缩失败后的冷却期——防止摘要失败触发重试风暴

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 重试 3 次 + 指数退避 | ⚠️ wiki 未确认重试参数 |
| hermes-agent | 600s 冷却期 + anti-thrashing | ✅ wiki 确认 600s 冷却 |

**跨仓库对比表体现**：✅ 第 7 行"压缩失败处理"直接对应

### 关切 6：用户通知不能注入 LLM——避免模型因感知到上下文压力而提前放弃

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 无分层预警机制（依赖底层 context window guard） | ✅ wiki 确认 Context Window Guard 存在 |
| hermes-agent | 分层预警（85%/95%），300s 去重，纯用户面 | ✅ wiki 确认分层预警 + "不注入 LLM" |

**跨仓库对比表体现**：✅ 第 9 行"用户通知"直接对应

### 关切验证汇总

| 关切 | #1 | #2 | #3 | #4 | #5 | #6 |
|------|----|----|----|----|----|-----|
| 跨仓库对比有对应行 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 悬空（0 个） | -- | -- | -- | -- | -- | -- |

---

## D. 绝对化语言检查

| 位置 | 原文 | 判定 |
|------|------|------|
| 位置 A | "摘要指令不指定 token 预算上限" | ✅ 准确——wiki 确认无固定预算 |
| 位置 B | "定量预算不考虑重要性排序" | ⚠️ 推论性表述——wiki 未确认摘要模板是否含隐式优先级排序 |
| 位置 B | "重要和不重要的信息获得相同的 token 配额" | ⚠️ 同上——wiki 确认 20% 配额存在但未确认公平分配行为 |
| 跨仓库对比 | "摘要是'hint, NOT a substitute'"（openclaw） | ⚠️ wiki 未逐字引用此措辞 |
| 跨仓库对比 | "引导段...NOT as active instructions"（hermes） | ⚠️ wiki 未逐字引用 SUMMARY_PREFIX |
| 选择指南 | "宁愿摘要长一点也不能丢失上下文" | ⚠️ 价值判断——应表述为"优先保留上下文而非激进压缩" |

---

## E. 汇总计数

| 判定类别 | 数量 |
|----------|------|
| ✅（wiki 直接确认） | 9 |
| ⚠️（wiki 部分确认 / 未覆盖细节 / 合理推论但无法溯源） | 19 |
| ❌（wiki 矛盾） | 0 |
| 格式缺失 | 2（YAML frontmatter、关联节） |

### ⚠️ 清单

1. SAFETY_MARGIN 行号（concept:13 vs wiki:19-40）— 行号范围不一致
2. computeAdaptiveChunkRatio 行号（concept:129-148 vs wiki:19-40）— 行号不一致
3. SUMMARIZATION_OVERHEAD_TOKENS = 4096 — wiki 未确认
4. 重试 3 次 + 指数退避（500ms-5s, jitter 0.2）— wiki 未确认
5. compaction-safeguard.ts hook 行为 — wiki 未覆盖
6. post-compaction-context.ts 刷新指令 — wiki 未覆盖
7. _SUMMARY_RATIO/min/ceiling 精确行号（concept:49-53 vs wiki:51-53）— 差 2 行
8. _MIN_SUMMARY_TOKENS = 2000 — wiki 未确认下限
9. summary_target_ratio clamp [0.10, 0.80] — wiki 未确认
10. SUMMARY_PREFIX 具体措辞 — wiki 未确认
11. anti-thrashing 2 次 <10% 跳过 — wiki 未确认
12. _prune_old_tool_results 行号（concept:333-418 vs wiki:15-17）— 行号相差极大
13. 压力预警行号（concept:10688-10706 vs wiki:824-828）— 行号相差~9800 行
14. _CONTEXT_PRESSURE_COOLDOWN = 300 — wiki 未确认
15. config.yaml compression.threshold = 0.50 — wiki 未确认
16. MD5 hash 去重 — wiki 未确认
17. hermes 工具输出修剪行号差异 — wiki 引用 15-17 但 concept 引用 333-418
18. openclaw post-compaction "Execute your Session Startup sequence now" 措辞 — wiki 未逐字确认
19. hermes-agent 20% 配额"不考虑重要性排序" — wiki 未确认此行为特性

### 关键发现

1. **YAML frontmatter 缺失是最明显的格式问题**：另外两个 concept 页均有完整 frontmatter，本页缺少——应该补齐 `concept`、`generated`、`phase`、`instances` 字段
2. **关联节缺失**：另外两个 concept 页有显式 wikilink 网络，本页无——虽然内容中有内联 wikilink（位置 A 和 B 各有一个），但缺少标准化的 `## 关联` 节
3. **hermes-agent 行号差异显著**：`_prune_old_tool_results` wiki 引用 15-17 而 concept 引用 333-418；`run_agent.py` 压力预警 wiki 引用 824-828 而 concept 引用 10688-10706——这些差异跨越数百到近万行，需要直接读源码确认哪个正确
4. **openclaw 行号差异**：wiki 将所有 compaction 参数归入 19-40 区域，concept 页分散到多处（13、16-18、20-24、81、92-93、129-148、190-198）——concept 页的精度可能更高，但 wiki 无法印证
5. **concept 页细节深度再次超出 wiki 覆盖范围**：anti-thrashing 阈值、去重机制、clamp 范围、冷却值、SUMMARY_PREFIX 具体措辞——这些在 wiki 维度页和节点页中均未记录
6. **关切覆盖面完整**：6 条核心关切均在跨仓库对比表中有对应维度行，无悬空关切
7. **绝对化语言集中在对行为后果的定性判断**：特别是位置 B "定量预算不考虑重要性排序"的表述——这是一个对算法行为的强断言，wiki 无法验证此行为是否确实公平分配 token 配额

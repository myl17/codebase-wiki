# 验证报告：memory-retrieval-timing

**验证时间**：2026-06-19
**验证方法**：以 wiki 维度页和节点页记录的源码引用为唯一基准，不访问原始源码
**待验证文件**：`experiments/entity-concept-extraction/v2-validation-2026-06-19/round-2-hermes/phase-3a-concepts/memory-retrieval-timing.md`

---

## A. 格式完整性 Checklist

| 检查项 | 状态 | 说明 |
|--------|------|------|
| YAML frontmatter（concept/instances） | ✅ | concept + 2 instances (openclaw, hermes-agent) |
| 标准化问题陈述 | ✅ | 明确对比：Prompt 组装期批量注入 vs 后台异步预取 |
| 核心关切（5条） | ✅ | 新鲜度、确定性、用户感知延迟、多后端兼容、异步预取过时 |
| 已知权衡位置 | ✅ | 位置 A（openclaw）+ 位置 B（hermes-agent），各含机制、代价、实例 |
| 跨仓库对比表 | ✅ | 11 维度 x 2 仓库 |
| 选择指南 | ✅ | 8 条场景推荐 |
| 溯源表 | ✅ | 19 行引用，含仓库/文件/行号/内容 |
| 关联（wikilink） | ✅ | 6 个 wikilink |

---

## B. 逐仓库逐 Claim 判定

### B1. openclaw Claims

#### Claim 1: `registerMemoryCapability` exclusive 槽位位于 `src/plugins/memory-state.ts:170-174`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认精确行号**。`openclaw-memory-system.md` 节点页确认 "registerMemoryCapability 是 exclusive 槽位，全局只能有一个活跃实现"，`openclaw-architecture.md` 维度页确认 "独占槽位：registerContextEngine 和 registerMemoryCapability 全局只能有一个活跃实现，后注册者覆盖前者"。行为一致，但 wiki 仅引用 `src/memory-host-sdk/host/types.ts:1-30` 作为 sources，未引用 `src/plugins/memory-state.ts` 的具体行号 |

#### Claim 2: `buildMemoryPromptSection` 位于 `src/plugins/memory-state.ts:206-219`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖此函数**。wiki 节点页和维度页均未提及 `buildMemoryPromptSection` 函数名或 `memory-state.ts:206-219`。但 wiki 确认"记忆在 prompt 组装阶段注入，非实时查询"（openclaw-architecture.md 第 50 行），与该函数的语义角色一致 |

#### Claim 3: `buildMemorySection` 在 system prompt 组装中调用（`src/agents/system-prompt.ts:169-182`、`613-618`）

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖此调用**。wiki 节点页和维度页均未提及 `buildMemorySection` 或 `system-prompt.ts` 的相关行号。`openclaw-architecture.md` 的数据流图显示 "Context Engine (assemble: memory inject + history compact)"，确认记忆在 assemble 阶段注入，但未细化到函数级别 |

#### Claim 4: `buildMemorySystemPromptAddition` 位于 `src/context-engine/delegate.ts:74-87`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖此函数**。wiki 未提及 `context-engine/delegate.ts` 或 `buildMemorySystemPromptAddition` |

#### Claim 5: `MemorySearchManager` 接口位于 `src/memory-host-sdk/host/types.ts:68-94`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 行号范围不同**。`openclaw-memory-system.md` 节点页 `sources` 引用 `src/memory-host-sdk/host/types.ts:1-30`，concept 页引用 68-94。同一文件但行号不同：wiki 引用文件头部（1-30），concept 引用搜索接口定义（68-94）。两者引用同一文件的不同段落，可能均正确 |

#### Claim 6: memory capability 为 exclusive 槽位（全局唯一活跃实现）

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 明确确认**。`openclaw-memory-system.md`："registerMemoryCapability 是 exclusive 槽位，全局只能有一个活跃实现"。`openclaw-architecture.md`："独占槽位：registerContextEngine 和 registerMemoryCapability 全局只能有一个活跃实现，后注册者覆盖前者" |

#### Claim 7: 记忆作为 system prompt 的一部分在同一轮内保持稳定

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 语义确认**。`openclaw-memory-system.md`："记忆在 prompt 组装阶段注入，非实时查询"。`openclaw-architecture.md`："记忆在 prompt 组装阶段注入，非实时查询"。与 concept 页"同一轮内 system prompt 不变"一致 |

#### Claim 8: 两种 backend：`builtin`（SQLite + sqlite-vec）和 `qmd`（外部引擎）

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`openclaw-memory-system.md`："支持两种 backend：builtin（SQLite + sqlite-vec）和 qmd（外部引擎）"。`openclaw-architecture.md` 维度页同样描述 |

---

### B2. hermes-agent Claims

#### Claim 1: `queue_prefetch_all` 位于 `agent/memory_manager.py:197-206`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认精确行号**。`hermes-agent-memory-provider.md` 节点页 `sources` 仅引用 `agent/memory_manager.py:1-27`（文件头部）。wiki 维度页和节点页均未提及 `queue_prefetch_all` 函数名或具体行号。但 `hermes-agent-memory-provider.md` 正文描述"实现 MemoryProvider ABC"和"放入 plugins/memory/<name>/ 即可接入"，确认了预取机制所在的模块 |

#### Claim 2: `prefetch_all` 位于 `agent/memory_manager.py:178-195`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认精确行号**。同上，wiki 仅引用文件头部 1-27 |

#### Claim 3: `build_memory_context_block` 位于 `agent/memory_manager.py:65-80`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 部分确认**。`hermes-agent-architecture.md` 维度页自学习闭环数据流中提到 `build_memory_context_block() 注入记忆条目 ^[agent/memory_manager.py]`，确认了函数存在但未给出行号 |

#### Claim 4: `HindsightMemoryProvider.prefetch` 位于 `plugins/memory/hindsight/__init__.py:654-670`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖**。wiki 节点页和维度页均未提及 `HindsightMemoryProvider` 或其具体行号。wiki 仅提到"7 memory providers (Honcho/Mem0/Supermemory/...)"但未展开 hindsight provider |

#### Claim 5: `HindsightMemoryProvider.queue_prefetch` 位于 `plugins/memory/hindsight/__init__.py:672-713`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖**。同上，hindsight provider 细节不在 wiki 范围内 |

#### Claim 6: `prefetch_all` 调用点位于 `run_agent.py:8484-8488`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认精确行号**。`hermes-agent-ai-agent.md` 节点页 `sources` 引用 `run_agent.py:8130-8189`（run_conversation 入口），但未细化到 prefetch 调用点的行号 |

#### Claim 7: API-call 注入点位于 `run_agent.py:8561-8577`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖**。wiki 未提及此注入点的行号 |

#### Claim 8: 轮次收尾 `queue_prefetch_all` 位于 `run_agent.py:11233-11241`

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未覆盖**。wiki 未提及此调用点的行号 |

#### Claim 9: hermes-agent 内置必开启 + 最多 1 个外部 provider（增量式）

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 明确确认**。`hermes-agent-memory-provider.md` 节点页："约束：最多 1 个外部 provider，BuiltinMemoryProvider 始终启用不可移除，外部 provider 是加性的不替代内置存储。与 OpenClaw 的 exclusive 槽位（替换式）形成对比" |

#### Claim 10: 预取结果暂时性注入——API-call time only，不污染持久化 messages

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未确认注入持久化边界**。wiki 未描述记忆注入的持久化行为 |

---

## C. 关切验证

### 关切 1：新鲜度——实时检索可获取最新记忆

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 组装发生在 API 调用前，当前轮新增记忆不可见 | ✅ wiki 确认"非实时查询" |
| hermes-agent | 预取上一轮结束前入队，当前轮写入要到下一轮预取才可见 | ⚠️ wiki 确认预取机制存在但未明确"当前轮不可见"的代价 |

**跨仓库对比表体现**：✅ 第 4 行"新增记忆可见性"直接对应

### 关切 2：确定性——同一轮内多次 API 调用 prompt 保持一致

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | system prompt 在整轮不变，tool call 循环中记忆内容稳定 | ✅ wiki 确认"非实时查询"——支持确定性推论 |
| hermes-agent | 依赖后台预取线程完成度，若未完成本轮记忆缺失 | ⚠️ wiki 未确认此不确定性代价 |

**跨仓库对比表体现**：✅ 第 3 行"确定性"直接对应

### 关切 3：用户感知延迟——同步检索增加 TTFT

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 同步检索延迟叠加到 prompt 组装耗时 | ✅ wiki 确认 prompt 组装阶段注入（隐含同步检索） |
| hermes-agent | 检索在后台完成，API 调用路径只做缓存读取 | ⚠️ wiki 确认预取机制但未量化延迟优势 |

**跨仓库对比表体现**：✅ 第 5 行"用户感知延迟"直接对应

### 关切 4：多后端兼容——不同内存后端延迟差异巨大

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | promptBuilder 统一抽象——所有后端输出 string[] | ✅ wiki 确认 MemorySearchManager 接口 + builtin/qmd backend |
| hermes-agent | 每个 provider 独立管理线程和缓存 | ✅ wiki 确认 7 种 provider + 内置+外部架构 |

**跨仓库对比表体现**：✅ 第 6 行"多后端处理"、第 7 行"后端数量约束"对应

### 关切 5：异步预取的过时问题——预取结果反映上一轮状态

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | N/A（此关切主要针对预取模式） | ✅ 不适用 |
| hermes-agent | 预取用的 query 是上一轮用户消息，不含当前轮上下文 | ⚠️ wiki 未明确此过时问题 |

**跨仓库对比表体现**：✅ 第 4 行"新增记忆可见性" + 第 3 行"确定性"间接对应

### 关切验证汇总

| 关切 | #1 | #2 | #3 | #4 | #5 |
|------|----|----|----|----|-----|
| 跨仓库对比有对应行 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 悬空（0 个） | -- | -- | -- | -- | -- |

---

## D. 绝对化语言检查

| 位置 | 原文 | 判定 |
|------|------|------|
| openclaw 代价 | "无异步预取机制：每次 prompt 组装都是同步检索" | ✅ 可接受——wiki 确认"非实时查询" |
| hermes-agent 代价 | "预取用的 query 是上一轮的用户消息，不包含当前轮上下文" | ⚠️ wiki 未确认此具体时序逻辑 |
| hermes-agent 过渡推断 | "若上一轮预取线程未完成（网络延迟、API 超时），prefetch 最多等 3 秒后放弃，本轮无记忆注入" | ⚠️ wiki 未确认 3 秒超时值和放弃后行为 |
| 选择指南 | "两者都不保证当前轮写入的记忆当前轮可见" | ✅ 准确——wiki 对两种模式的描述均支持此结论 |
| 选择指南 | "两者均不满足" | ⚠️ 语言稍绝对——某些场景下（如本轮未写入记忆），openclaw 的检索可能命中刚写入的内容 |

---

## E. 汇总计数

| 判定类别 | 数量 |
|----------|------|
| ✅（wiki 直接确认） | 10 |
| ⚠️（wiki 部分确认 / 未覆盖细节 / 合理推论但无法溯源） | 16 |
| ❌（wiki 矛盾） | 0 |

### ⚠️ 清单

1. `memory-state.ts:170-174` — wiki 未引用此文件/行号
2. `memory-state.ts:206-219` (buildMemoryPromptSection) — wiki 未覆盖
3. `system-prompt.ts:169-182, 613-618` (buildMemorySection) — wiki 未覆盖
4. `delegate.ts:74-87` (buildMemorySystemPromptAddition) — wiki 未覆盖
5. `types.ts:68-94` vs wiki 的 1-30 — 行号范围不同（同一文件不同段落）
6. `memory_manager.py:197-206` (queue_prefetch_all) — wiki 仅引用 1-27
7. `memory_manager.py:178-195` (prefetch_all) — wiki 仅引用 1-27
8. `memory_manager.py:65-80` (build_memory_context_block) — wiki 提及函数名但无行号
9. `hindsight/__init__.py:654-670, 672-713` — wiki 未覆盖
10. `run_agent.py:8484-8488` — wiki 未覆盖
11. `run_agent.py:8561-8577` — wiki 未覆盖
12. `run_agent.py:11233-11241` — wiki 未覆盖
13. openclaw LegacyContextEngine pass-through (legacy.ts:38-54) — wiki 未覆盖
14. hermes-agent "预取结果暂时性注入不污染持久化" — wiki 未确认
15. hermes-agent "最多等 3 秒后放弃" — wiki 未确认
16. "两者均不满足"的绝对化表述 — 需降级

### 关键发现

1. **概念页的溯源精度显著高于 wiki 节点页**：concept 页的 19 行溯源引用中，仅 4 行被 wiki 节点页以相同粒度确认。concept 页对源码细节的掌握（具体函数名、精确行号、调用时序）远超 wiki 节点页当前记录
2. **wiki 对宏观架构确认度高，对函数级细节覆盖不足**：wiki 确认了 openclaw 的 exclusive 槽位、prompt 组装阶段注入、MemorySearchManager 接口，以及 hermes-agent 的内置+外部架构、预取机制存在性——但对具体函数的行号和内部实现没有记录
3. **hermes-agent 预取时序的精确行号无法验证**：`queue_prefetch_all`、`prefetch_all`、API-call 注入点、轮次收尾调用点——这些行号在 wiki 中无对应记录，需要直接读源码验证
4. **行号范围差异需注意**：concept 页 `types.ts:68-94` vs wiki `types.ts:1-30`——同一文件不同段落，可能均为正确但需确认
5. **关切覆盖面完整**：5 条核心关切均在跨仓库对比表中有对应维度行，无悬空关切
6. **concept 页对 wiki 形成了有效补充**：许多函数级细节（buildMemoryPromptSection、queue_prefetch_all 时序、hindsight provider 实现）是 wiki 未覆盖但 concept 页提供了详细文档的——这正是 concept 页应有的价值

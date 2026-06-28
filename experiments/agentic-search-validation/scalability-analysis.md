# Step 3 搜索策略的可扩展性分析

> 分析日期：2026-06-28
> 触发问题：(1) Agentic search 在 500-1000 Concept 规模下是否可扩展？(2) 有什么外部证据？(3) 检索策略应该如何设计？(4) 如何验证？

---

## 一、先回答：你为什么不需要 embedding

你的判断是对的，但理由比我之前想的更充分。不只是"Concept 变化频繁所以 re-embedding 成本高"——

### 1.1 CORE-Bench (2026, 180K+ 查询) 的关键发现

**语义嵌入模型在短关键词查询上会崩溃。** CORE-Bench 评测了 180,000+ 条真实 agentic 检索查询，发现一个反直觉的结果：

> 当查询是 `"auth flow"`, `"user service"`, `"handle error"` 这样的短关键词时，几乎所有语义嵌入模型的 nDCG@10 都降到接近零。

而 Agent 生成的查询正是这种短关键词形式。CORE-Bench 的作者直接说：

> "Semantic search's 90% recall claim can turn into 90% poison in the agent ecosystem."

**这对我们意味着什么：** 你的 problem space 条目是"如何让主 Agent 委托后台子 Agent 执行复杂任务"这种中等长度的中文问题陈述。如果你从中提取关键词做 grep（"子代理"、"委托"、"隔离执行"），grep 会做精确字符串匹配。如果换成 embedding 搜索，模型需要理解"子代理委派"和"subagent orchestration"之间的语义关系——而 CORE-Bench 说，在短查询场景下，embedding 模型的精度反而更低。

### 1.2 SWE-Explore (2026, 848 issues, 203 repos) 的关键发现

**Agentic 搜索碾压经典检索。** SWE-Explore 把多种检索方法放在同一个基准上比较：

| 检索方法 | HitFile (找到正确文件) | 下游修复率 |
|---------|---------------------|----------|
| Oracle（理论上限） | — | 59.7% |
| **Agentic (Claude Code, Codex, OpenHands)** | **64-67%** | **48-50%** |
| AutoCodeRover | — | 44.7% |
| TF-IDF | — | 26.0% |
| BM25（经典关键词检索） | 7.9% | 12.7% |
| Random | — | 4.7% |

Agentic search 的 HitFile 是 BM25 的 **8 倍**。这不是小幅领先——这是代差。

**但也要诚实地看局限：** Agentic 方法的行级召回率仍然只有 15-19%（找到正确文件后，定位到精确代码行的能力）。不过在你的场景中，匹配粒度是整个 Concept 页（文件级），不需要精确到行——所以这个局限不伤害你。

### 1.3 Sense Benchmark (2026, 6 repos, 5 方法对比)

最接近你场景的对照实验——在陌生代码库中找答案：

| 方法 | 公平性 | 质量 | Token 效率 |
|------|--------|------|-----------|
| Sense（符号图 + embedding） | 81.3% | 85.4% | 10,896 tok |
| Probe（tree-sitter + ripgrep） | 77.7% | 84.8% | 12,119 tok |
| **Baseline (grep/find/read)** | **77.2%** | **84.2%** | **12,716 tok** |
| Serena（LSP 驱动） | 75.2% | 83.4% | 14,800 tok |
| GitNexus（图数据库） | 74.9% | 84.5% | 12,964 tok |

**纯 grep 基线与最先进方法的差距只有 4 个百分点。** 而且纯 grep 不需要索引、不需要 embedding pipeline、不需要维护向量数据库。代价是多消耗 ~16% 的 token——这个 trade-off 在你当前规模下完全可以接受。

### 1.4 你的场景 vs 代码搜索场景：为什么 token bloat 批评对你不太适用

grep 在代码搜索中被批评的核心原因是 **token bloat**——grep 返回整个文件（几百到几千行），LLM 必须从大量噪音中提取信号。Semble 的数据很能说明问题：

> grep+read 消耗 32,000 tokens 的召回率（0.583），还不如 Semble 消耗 2,000 tokens 的召回率（0.938）。

**但这个批评在你的场景中被大幅削弱了：**

| 维度 | 代码搜索 | 你的 Concept 匹配 |
|------|---------|------------------|
| 单文件大小 | 300-3000 行源码 | 10 行 frontmatter + ~60 行正文 |
| 搜索空间 | 数百万行 | 500-1000 个 Concept × 70 行 = 35,000-70,000 行 |
| 命中后的读取量 | 整个文件（可能 500+ 行垃圾） | head -10 精确命中（~8 行全是信号） |
| 语义鸿沟 | "authentication" ≠ "login_handler" | LLM 写的 problem 字段，词汇一致性高 |
| 迭代轮数 | 10-20 轮 grep → read → grep | 1-2 轮 grep → read |

**核心差异：你搜索的不是源码，是 LLM 自己写的、结构化良好的 frontmatter。** 这些 problem 字段使用一致的术语（因为同一个 LLM 写的），单条长度短（~110 字符），信息密度极高。grep 在这种语料上的 precision 远高于在源码上的 precision。

---

## 二、外部证据汇总：agentic search 到底行不行？

### 2.1 正方：agentic search 有坚实的实验支撑

| 证据 | 来源 | 核心结论 |
|------|------|---------|
| Agentic 搜索碾压 BM25 8 倍 | SWE-Explore (2026) | HitFile 65% vs 7.9%，下游修复率 50% vs 13% |
| 纯 grep 基线接近 SOTA | Sense Benchmark (2026) | grep 77.2% vs 最佳 81.3%，差距仅 4pp |
| 短查询下语义模型崩溃 | CORE-Bench (2026) | Embedding 模型在 agent 生成的短查询上 nDCG 降到接近零 |
| RL 训练的 grep agent 匹配前沿模型 | SWE-grep, Cognition (2025) | 4 轮 × 8 并行工具调用，F1 匹配 Sonnet 4.5，速度快 10 倍 |
| Anthropic 内部测试 | Claude Code 团队 (2025) | agentic search "dramatically outperformed all other approaches" |

### 2.2 反方：纯 grep 在规模化时有真实成本

| 证据 | 来源 | 核心结论 |
|------|------|---------|
| grep token 消耗是语义搜索的 50 倍 | Semble (2025) | 32K tok (grep) vs 2K tok (Semble) 达到相同召回率 |
| 语义搜索减少 40% token + 65% 工具调用 | Zilliz (2025) | SWE-bench 30 任务对照实验 |
| grep + 语义搜索比纯 grep 准确率高 12.5% | Cursor (2025) | 自定义 embedding 模型，生产环境 A/B 测试 |

### 2.3 综合判断

**对于你的具体场景（匹配 ~15 条问题陈述到 500-1000 个 Concept frontmatter），agentic grep 是合适的。** 原因：

1. **你的搜索空间不是源码** —— frontmatter 的信息密度是源码的 10-50 倍，grep 的 token bloat 问题被大幅压缩
2. **你的查询不是短关键词** —— 每条问题空间条目是一句完整的中文问题陈述，比 CORE-Bench 崩溃的 `"auth flow"` 要长得多、信息量大得多
3. **你控制词汇** —— 所有 Concept 的 problem 字段由同一个 LLM 用同一套术语体系编写，语义鸿沟远小于异构代码库
4. **规模上限已知** —— 即使 1000 个 Concept，frontmatter 扫描也只需 ~20K tokens。后续 keyword grep 策略可以在不牺牲准确率的前提下把深读步数控制在常数级别
5. **外部基准支撑** —— SWE-Explore 证明 agentic search 在数百个仓库上有效；Sense 证明纯 grep 接近 SOTA；CORE-Bench 证明 embedding 在 agent 查询上反而更差

**grep 真正的弱点（巨大源码文件的全量读取、10-20 轮迭代搜索）在你的场景中恰好被规避了。** 这解释了为什么 Phase 1-4 的 22 条查询全部 Recall@3 = 1.00 且零假阳性。

---

## 三、检索策略设计

### 3.1 策略不应该只有一个

当前 SKILL.md Step 3 的无条件"扫描所有 frontmatter"在 16 个 Concept 时是最优的（零遗漏，token 成本可忽略）。但随着规模增长，必须在"零遗漏"和"常量 token 成本"之间做权衡。

### 3.2 建议的三级策略

```
Step 3 开始前先执行规模检测：

  CONCEPT_COUNT=$(ls wiki/concepts/*.md 2>/dev/null | wc -l)
  SEED_ENTRY_COUNT=$(grep -c "^|" seeds/master.md 2>/dev/null || echo 0)
```

#### 策略 A：全量 frontmatter 扫描（CONCEPT_COUNT ≤ 50）

**当前策略，保持不变。** 零遗漏，token 成本 < 3% 上下文。

```
1. for f in wiki/concepts/*.md; do head -10 "$f"; done
2. 从 seeds/master.md 中 grep 与本次 problem-map 关键词相关的条目
   （不 cat 全文——按需 grep）
3. 对 LLM 判断相关的 Concept 深读全文
```

#### 策略 B：关键词 grep 预筛（50 < CONCEPT_COUNT ≤ 500）

**Phase 1-4 验证过的策略。** Recall@3 = 1.00，零假阳性。

```
1. 从 problem-map 每条条目的"问题名"中提取 2-3 个核心关键词
   - 关键词选择原则：
     a. 选中文技术术语，不选连接词（"如何""的""一个"）
     b. 选概念名词，不选动词（"子代理" 优于 "委托"）
     c. 如果中文术语有英文对应，也加入英文变体
   - 每条的示例：
     "如何让主Agent委托后台子Agent执行复杂任务"
     → 关键词：子代理 subagent 隔离执行
     "如何在LLM上下文窗口有限时自动压缩对话历史"
     → 关键词：上下文压缩 摘要 summarization

2. 对每条条目，grep 这些关键词在 wiki/concepts/*.md 的 problem 字段：
   grep -l "关键词1\|关键词2" wiki/concepts/*.md

3. 合并所有条目的命中文件列表，去重
   （Phase 2 实验证明这能把 grep 次数减少 82%）

4. 对去重后的每个 Concept 做 head -10 读取 frontmatter
   （不是读全文——先读 frontmatter 确认匹配）

5. 对确认匹配的 Concept 深读全文
```

#### 策略 C：多轮搜索 + 人工标注回退（CONCEPT_COUNT > 500）

```
1. 执行策略 B
2. 对未匹配的条目，做第二轮"关联搜索"：
   - 用已匹配 Concept 的 concerns 字段中的术语扩展关键词
   - 例如：已匹配 subagent-orchestration → 提取 concerns
     ["并行执行 vs 顺序执行", "隔离性 vs 共享上下文", "同步 vs 异步"]
     → 扩展关键词：并行 隔离 同步 异步
3. 仍无法匹配的条目：
   - 标记为"待人工审核"
   - 不是系统失败——有些条目确实不对应任何已有 Concept
   - C 类（待观察）和真正的 N（无匹配）在这个阶段都需要人工确认
```

### 3.3 master.md 的特殊处理

当前 `cat seeds/master.md` 在规模化时必然崩溃（500 仓库 → 8,500 行 → 133K tokens）。**这不依赖于选择哪种搜索策略——master.md 的结构性问题必须独立解决。**

方案（从简到繁）：
1. **最简单**：Step 3 提示词中把"已有种子库：seeds/master.md"改为"对 seeds/master.md 做关键词 grep（用 problem-map 中的关键词），只读匹配行"
2. **中期**：master.md 按仓库分文件存储（`seeds/by-repo/<name>.md`），Step 3 按需读取新仓库可能相关的已有仓库条目
3. **远期**：Concept 页 frontmatter 中增加 `seeds:` 反向索引字段，Step 3 从 Concept frontmatter 扫描中同时获得种子信息

### 3.4 提示词应该如何表述

当前提示词（SKILL.md 第 319 行）：

```
- 已有 Concept 页：先扫描 `wiki/concepts/` 下所有 `.md` 的 frontmatter
  （文件名 + problem 字段）做初筛
```

建议改为：

```
- 已有 Concept 页：
  **规模检测**：先运行 `ls wiki/concepts/*.md | wc -l` 获得 Concept 总数

  **若 ≤ 50 个**：`head -10` 所有 Concept 的 frontmatter 一次性入眼，全量语义匹配

  **若 50-500 个**：
    1. 从 problem-map 每条条目的"问题名"中提取 2-4 个核心技术关键词
       （选概念名词，不选连接词和通用动词）
    2. 用这些关键词 grep wiki/concepts/*.md 的 frontmatter：
       `grep -l "关键词1\|关键词2\|..." wiki/concepts/*.md`
    3. 合并所有条目的命中文件去重
    4. 只对去重后的 Concept 做 `head -10` 确认匹配，匹配的深读全文

  **若 > 500 个**：
    1. 先执行 50-500 策略
    2. 未匹配条目用已匹配 Concept 的 concerns 字段扩展关键词，做第二轮 grep
    3. 仍无匹配的标为"待人工审核"

- 已有种子库：
  **不读 seeds/master.md 全文。**
  用 problem-map 中的关键词 grep seeds/master.md，只读匹配行：
  `grep -i "关键词" seeds/master.md`
```

---

## 四、验证方案

### 4.1 为什么当前验证不够

| 已验证 | 未验证 |
|--------|--------|
| Phase 1-4: keyword grep 在 22 条查询上 Recall@3=1.00 ✅ | keyword grep 在 500 Concept 噪声中的假阳性率 ❓ |
| Phase 5: 全量 frontmatter 扫描在 16 Concept 上零遗漏 ✅ | 模型从 500 个 frontmatter 中选出相关项的能力 ❓ |
| Phase 2: 批量去重减少 82% grep ✅ | 多轮搜索策略的有效性 ❓ |
| Phase 3: 边界情况（词汇陷阱）通过 ✅ | 500 个相似 Concept 时的语义混淆风险 ❓ |

### 4.2 建议的三阶段验证

#### 阶段 1：噪声压力测试（低成本，高信号）

**目标**：验证 keyword grep 在大量"干扰 Concept"存在时是否产生假阳性。

**方法**：
1. 生成 500 个"干扰 frontmatter"——从真实 Concept 的 problem 字段做词汇变体生成（同义词替换、语序调整、增加无关问题空间），混入真实 16 个 Concept
2. 复用 Phase 1 的 22 条查询，看 keyword grep 是否仍然只命中正确的 Concept，不命中干扰项
3. 测量：Recall@3、假阳性率、grep 命中数/总文件数

**成本**：一个 subagent，约 20K tokens。

#### 阶段 2：全量 frontmatter 扫描的注意力衰减测试

**目标**：验证当模型需要在 500 个 problem 字段中做语义匹配时，是否出现"大海捞针"效应。

**方法**：
1. 准备 500 个干扰 frontmatter（同阶段 1）
2. 用 `head -10` 全部 516 个 frontmatter 注入上下文
3. 让模型从 11 条 deepagents 问题空间条目做匹配
4. 与 Phase 5 ground truth（16 Concept 时的匹配结果）对比，看是否有遗漏或新增假阳性

**成本**：一个 subagent，约 50K tokens。

#### 阶段 3：模拟规模化 ingest（高成本，最真实）

**目标**：端到端验证 Step 3 在规模化场景下的完整行为。

**方法**：
1. 用脚本批量生成 500 个 Concept 页（基于真实 Concept 做结构变体，problem 字段来自不同的问题空间领域）
2. 对一个新仓库（如第 5 个仓库）执行完整 Step 3
3. 对比 ground truth（在 16 Concept 下的匹配结果）vs 500 Concept 下的匹配结果
4. 测量：匹配一致率、新增假阳性、遗漏的正确匹配、token 消耗、工具调用次数

**成本**：一个完整的 ingest subagent，约 150-200K tokens。

### 4.3 如果验证暴露了问题

| 问题 | 应对 |
|------|------|
| keyword grep 假阳性率 > 10% | 增加 frontmatter 确认步骤（grep 命中 → 必须读 frontmatter 验证） |
| 全量扫描注意力衰减导致漏匹配 | 切换到策略 B（keyword grep 预筛），不让模型在 500 个候选中做全局匹配 |
| 多轮搜索仍无法匹配 | 接受这个边界——某些条目确实没有对应 Concept，人工审核是可接受的回退 |
| token 成本超预期 | 收紧关键词选择策略（更少关键词、更精确） |

---

## 五、总结

### 5.1 回答你的四个判断

| 你的判断 | 验证结果 |
|---------|---------|
| "不应该用 embedding" | ✅ 正确。CORE-Bench 证明短查询下 embedding 会崩溃，且你的语料词汇一致、变化频率高，embedding 维护成本不值得 |
| "agentic search 应该能覆盖 1000 个仓库" | ⚠️ 方向正确但需要细化。Agentic grep 在你的场景中有独特的优势（frontmatter 信息密度高、词汇一致、不需要行级精度），但需要策略分级 + master.md 改造 + 验证后确认 |
| "grep 直接操作文件，速度快" | ✅ 正确。grep 本身是 I/O bound，500 个文件 grep 不超过 1 秒。瓶颈从来不是 grep 速度，是 LLM 处理 grep 结果的质量 |
| "需要有外部依据" | ✅ 找到了。SWE-Explore、CORE-Bench、Sense Benchmark、SWE-grep 四个独立来源从不同角度支撑了 agentic search 在中等规模检索中的有效性 |

### 5.2 关键行动项

1. **立即**：修改 SKILL.md Step 3，加入规模检测和三级策略选择
2. **立即**：修改 master.md 的访问方式（从 `cat` 全文改为 `grep` 按需）
3. **短期**：执行验证阶段 1（噪声压力测试），确认 keyword grep 在 500 干扰中的假阳性率
4. **中期**：执行验证阶段 2（注意力衰减测试），确认模型的大海捞针能力上限
5. **长期**：当 Concept 数触及 50 时，阶段 3 的规模化模拟成为必要

### 5.3 一个诚实的提醒

**没有外部研究直接测试"500 个 LLM 编写的 frontmatter + keyword grep + 语义匹配"这种精确组合。** 最接近的是：
- SWE-Explore：证明了 agentic search 优于经典检索，但测试的是源码搜索而非 frontmatter 匹配
- CORE-Bench：证明了短查询下 embedding 比 grep 差，但这是代码检索而非概念匹配
- Sense Benchmark：证明了纯 grep 接近 SOTA，但只有 6 个仓库

**外部证据给了我们信心说"这个方向是对的"，但不能替代我们自己的规模化验证。** Phase 1-4 的 22 条 100% 准确率是一个很好的起点——但 500 条干扰中的表现才是真正的考验。

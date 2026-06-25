# Codebase-Wiki 项目全景、共识结论与优化路线

> 整合日期：2026-06-20（第二版，含与 GPT 多轮讨论后的共识）
> **项目阶段定性：已从 Prompt Engineering 阶段进入 Knowledge Representation 阶段。**

---

## 一、项目创建背景

### 1.1 灵感来源

核心思想来自 **Andrej Karpathy 的 LLM Wiki 模式**（2026-04）：LLM 不只是做 RAG（每次查询临时从原始文档检索），而是**增量地构建和维护一个持久化的 wiki**——读取源、提取关键信息、整合进已有页面、更新交叉引用、标记新旧矛盾。知识编译一次然后持续保鲜，不是每次查询都重新推导。

```
Raw Sources → 代码仓库（不可变，LLM 只读）
The Wiki    → LLM 拥有并维护的所有 markdown
The Schema  → 告诉 LLM 怎么结构化、什么约定、什么流程
```

人机分工：**LLM 写一切、人读、人给方向、LLM 继续。** 不是人批准 LLM 的每一步产出。

### 1.2 要解决的问题

代码仓库中隐含大量架构知识（设计意图、扩展边界、模块间的隐式契约），但这些知识分散在源码、注释、CLAUDE.md、AGENTS.md 中，无法被系统化地对比和累积。

### 1.3 核心管线设计

```
Source → Summary（5 维度提取，理解仓库）
  → Entity（Component + ExtensionPoint 节点页，可定位的结构单元）
  → Concept（跨仓库归一化概念，知识累积的主战场）
  → Insights（按需：Comparison / Overview / Synthesis）
```

### 1.4 关键设计原则

1. **知识累积性优先。** 每次 ingest 和查询的产出都归档为 wiki 页面。
2. **wikilink 网络就是图。** 不维护与 wikilink 重复的结构化图谱数据。
3. **规模决定复杂度。** 当前规模不提前建设自动化归一化管线。
4. **Concept 页是主战场。** 跨仓库知识的真正累积发生在这里。
5. **Obsidian 是浏览器。** 人读、导航、发现关联；LLM 背后维护内容。

---

## 二、架构演进时间线

| 时间 | 事件 | 意义 |
|------|------|------|
| 06/07 | Karpathy LLM Wiki 模式引入，`/analyze` 管线初建 | 项目起点 |
| 06/10 | 图谱设计：四类节点 + 五阶段归一化管线 | 首次系统化设计 |
| 06/11 | GPT 深入讨论 Concept 角色——首次指出 "Concept 可能只是索引" | 奠定了基础反思 |
| 06/11-13 | **架构评审（关键转折点）**——砍掉 graph.yaml、"Type × Scope" 正交、Concept 只用索引+别名+准入三问 | 大幅减重 |
| 06/13 | **回退 DesignDecision**——Entity 只保留 Component + ExtensionPoint | 认知模型清理 |
| 06/13 | Concept/Comparison/Synthesis 定义为深度光谱 | Insight 统一框架 |
| 06/14-16 | **DeepWiki vs Source 实验**（8 轮） | 输入源选择的实验基础 |
| 06/16-17 | **Entity-Concept 提取 V2**（三轮增量，per-Concept agent + 验证） | Concept 流程的实验基础 |
| 06/19 | **V2 管线完整复现验证**（五维度对比历史基线） | 流程可复现性确认 |
| 06/20 | 与 GPT 多轮讨论 → 定位根本问题在 Knowledge Model 层 | **阶段拐点** |

---

## 三、实验结论（已确认，不再争议）

### 3.1 DeepWiki vs Source Code

1. **DeepWiki 的价值是阅读半径更大，不是产出质量更高。** 对复杂 monorepo 覆盖了 Source 完全遗漏的子系统。对简洁项目边际提升 < 5%。
2. **DeepWiki 是描述性的，不是分析性的。** 盲区：设计意图、架构纪律、接口级细节。
3. **两者互补，不是替代。** 理想路径：DeepWiki 广度预扫描 → Source 关键接口深读 → 结合产出。
4. **P0 是改 `/analyze` prompt。** Source 实验对 OpenClaw (+195%) 证明改 prompt 本身是最大杠杆。

### 3.2 Entity-Concept 提取 V2

1. **压缩链是 Concept 错误的根源。** 源码 → 维度页 → Entity 页 → 种子库 → Concept 页，每步压缩丢失关键细节。
2. **强制源码验证消除全部分类错误。** skill-injection 错误率 67% → 0%。Phase 3b 发现虚构文件路径和函数名。
3. **Phase 3b 独立验证不是可选项，是必需品。** 第二轮发现 17 个错误/不精确。
4. **per-Concept 独立上下文窗口是必要的。**
5. **增量流程正确追加不破坏已有内容。**

### 3.3 新 `/analyze` 流程验证

1. **对抗式评审有效。** 独立上下文、独立读源码，不被提取 agent 的思路污染。
2. **Agent 自审不可靠。** 声称"检查了所有子目录"但 `hermes_cli/` 零覆盖——系统性问题。
3. **"与最常规做法有什么不同"作为因果引导有效。** 比开放式提示产出的权衡数多 2.6×。
4. **Phase 1 作为 Phase 2 的 checklist 有效。** 基于子系统清单逐项检查比开放探索覆盖度更高。

---

## 四、7 个核心问题：解决状态与结论

### 问题 1：Entity 到底是什么？ ✅ 已解决

**结论：Entity 必须是 Structural Object，不能是 Semantic Object。**

这是软件分析领域（Architecture Recovery、Reverse Engineering、Static Analysis、Code Property Graph、Repository Mining）几十年的共识。Entity 是：

```
Package / Module / Directory / File / Class / Function / Interface
```

而 **不能** 是：

```
Planning / Memory / Plugin / Permission / Context Engine
```

后者是 **Capability / Role / Concern / Pattern**——全部是语义层的，会漂。

**关键洞察**：之所以同一个仓库每次提取出不同 Entity（`MemoryManager` → `Persistent Memory` → `Conversation State` → `State Store`），是因为没有固定 **Observation Unit**。Observation Unit 一旦变化，后面的全部统计和抽取都会变化。

**解决方案**：
```
Structural Entity（100% 稳定）
  ↓
Semantic Role（作为 Entity 的属性，不是独立 Entity）
```

Role 是属性，不是 Entity。`src/memory/` 是一个 Structural Entity，它的 Role 是 `Memory`。Role 由 LLM 标注，可能有概率漂移，但 Structure 来自代码，永远不会漂。

### 问题 2：Concept 是知识还是索引？ ✅ 已解决（修正了之前的结论）

**修正后的结论：Concept 不是"索引"，而是 "Ontology Class"。之前说"Concept 只是索引"是不够准确的。**

真正的问题是：我们目前把三层混在了一起：

| 层 | 职责 | 示例 |
|----|------|------|
| **Alias（术语）** | 同一概念的多种命名 | `Memory`、`Conversation Memory`、`Persistent Memory`、`Scratchpad` |
| **Ontology Class（概念类）** | 真正的抽象类别 | `Persistent State` |
| **Knowledge View（知识页）** | 面向用户的知识组织 | 对比表、选择指南、权衡分析 |

我们现在的 Concept 页同时承担了这三种职责，所以越来越复杂和不稳定。

**解决方案**：将 Alias（术语收敛）、Ontology Class（概念定义）、Knowledge View（面向用户的页面）分离为三个独立层。

### 问题 3：Ontology 是否可稳定恢复？ 🔄 重新框定

**新结论：完全自动、一次性、稳定恢复一个 Framework Ontology 几乎做不到。但增量收敛（Incremental Ontology Induction）可以做到。**

这是 Ontology Learning 领域几十年没有彻底解决的问题——抽象不是唯一的，不同 Prompt、不同模型、不同 Temperature 都会变化。

**但是**，成熟系统的 Ontology 从来不是一次性 Recover 出来的，而是 **Grow（长出来）** 的。Linux Kernel、Kubernetes、MITRE ATT&CK——都是经过多年、多版本、持续演化而成。

**关键转变**：
- ❌ 错误目标：让模型 10 次提取完全一样
- ✅ 正确目标：让 Ontology 10 次之后越来越稳定（收敛）

**稳定性来自三个约束**：

1. **Structural Constraint（结构约束）**：不直接让模型输出抽象概念，而是先恢复 Structural Entity，然后回答"这些 Entity 在解决什么问题？"——抽象空间大幅缩小。
2. **Cross-Repository Constraint（跨仓库约束）**：已有 Ontology 约束新仓库的归入——新仓库看到已有 `Memory` 节点下面已经挂了 `Conversation State` 和 `Persistent Context`，就不会重新创造 `Session Knowledge`。
3. **Evolution Constraint（演化约束）**：每次新增仓库不重新生成 Ontology，而是做 Diff → Merge。

**升级后的实验设计——Ontology Agreement Experiment**：
- 同一仓库跑 N 次，统计 Inter-run Agreement（Jaccard / F1 / ARI / NMI）
- 跨模型比较（Claude / GPT / Gemini / Qwen / DeepSeek）
- 不只看一致率，还看**收敛速度**——迭代几次后稳定

### 问题 4：用户角色是什么？ ✅ 已确认

**结论：Framework Builder。** 但需要补充关键洞察：

Framework Builder 真正需要的不只是"是什么"，更是 **"为什么"**：

| 需要 | 形式 |
|------|------|
| Design Decisions | 为什么选 X 不选 Y |
| Tradeoffs | 满足了什么、牺牲了什么 |
| Alternatives | 还有哪些被考虑过的方案 |
| Rationale | 在什么约束条件下做的决策 |

这与 ADR（Architecture Decision Record）实践完全一致。Concept 页的"选择指南"和"权衡位置"节是朝正确方向走的，但整体产出体系需要围绕这个需求重新组织。

### 问题 5：分类前置 → 全量对比？ ✅ 已解决

**结论：Never classify first. Normalize first.**

```
❌ 错误路径：Repository → Category → Concept
✅ 正确路径：Repository → Entity → Concept → Category
```

Category 是聚类结果，不是输入。这与 GraphRAG 等系统的做法一致。分类是动态演化的——随着仓库增加，分类自然聚合。

### 问题 6：Presentation Layer 分离？ ✅ 已确认

**结论：View 永远不是知识，只是 Projection。View 不应该参与 Extraction。**

四层模型：
```
Repository → Structural Facts → Semantic Concepts → Knowledge Views
```

Knowledge Views（用户动态查看时动态生成的 wiki 页面）是 Presentation Layer，不产生新知识，只负责组织已有知识。

### 问题 7：五个维度还要不要？ ✅ 已解决（保留但重新定义）

**结论：不要砍，但要重新定义。** 软件分析领域的一致经验：**固定分析模板比自由分析稳定得多。**

重新映射：

| 当前维度 | Framework Builder 维度 | 核心问题 |
|---------|----------------------|---------|
| Architecture | **Topology** | 子系统怎么连接？数据怎么流动？ |
| Extension Points | **Variation Point** | 设计轴上扩展边界划在哪里？ |
| Performance Tradeoffs | **Constraint** | 在什么约束条件下做的权衡？ |
| Dependency Strategy | **Boundary** | 什么自己做、什么依赖外部？ |
| Testing Philosophy | **Reliability Strategy** | 怎么保证正确性和可恢复性？ |

---

## 五、最重要的新认知：我们跳过了 Ontology 层

### 5.1 当前流程缺少的关键层

这是本轮讨论最重要的发现。我们当前的流程：

```
Repository → Entity（混合结构+语义）→ Concept
```

**跳过了 Ontology 层**，直接从 Entity 跨到 Concept。这就是为什么总感觉"缺了一些东西"。

### 5.2 正确的新四层模型

```
Layer 1: Structural Entity（代码事实，100% 稳定）
    ↓
Layer 2: Framework Ontology（能力域骨架，定义 Universe）
    ↓
Layer 3: Design Knowledge Unit（每个 Ontology 节点下的设计知识）
    ↓
Layer 4: Knowledge Views（面向用户的动态页面）
```

**Layer 2（Ontology）不承担知识积累**，它承担两个更基础的职责：

1. **定义分析边界（Universe）**：告诉系统"一个 Framework 通常有哪些能力域"。没有它，你无法判断是否漏分析了某个领域（Recall 不可测）。
2. **提供稳定的锚点（Anchor）**：让不同仓库关于同一能力域的设计知识能够稳定汇聚，而不是随着命名和抽象层次漂移。

**Layer 3（Design Knowledge Unit）才是真正积累知识的地方**。在 Ontology 的每个节点（如 `Memory`）下，提取设计知识：Persistence 怎么做、Retrieval 怎么做、Compression 怎么做、Eviction 怎么做。每个设计知识下面再挂具体的仓库实现案例。

### 5.3 为什么之前总是感觉 Concept 不稳定？

因为我们把不同层级的内容混在了同一个 Concept 里。例如 `skill-injection-granularity`：

```
Skill          ← 属于 Ontology 层（能力域）
Injection      ← 属于 Design Knowledge 层（设计问题）
Granularity    ← 属于 Tradeoff 层（权衡维度）
```

三层混在一起 → 每次提取在不同层级着陆 → 当然不稳定。

### 5.4 Ontology 是 Evolution，不是 Extraction

这是最关键的范式转变：

| 错误模型 | 正确模型 |
|---------|---------|
| 新仓库 → 提取 Ontology | 新仓库 → 检查是否改变已有 Ontology |
| 每次从零抽象 | 在已有体系上做增量判断 |
| 评估 Recovery Rate | 评估 Ontology 是否收敛 |

Ontology 的维护应该像 Git：
```
Ontology V1 → 新仓库 → Diff → Merge → Ontology V2
```
而不是：
```
新仓库 → 重新生成 → Ontology V2
```

**本体维护 agent 只做四种决策**：

| 操作 | 含义 | 触发条件 |
|------|------|---------|
| **Match** | 新仓库的能力归入已有本体节点 | 与已有本体节点描述的是同一个能力域 |
| **Add** | 确实出现了一个新的能力域 | 已有本体中找不到对应节点，且通过了 ≥2 个核心关切验证 |
| **Split** | 已有本体节点过于宽泛，需要拆分 | 该节点下积累了 ≥3 个明显不同的设计子问题 |
| **Merge / Rename** | 两个本体节点实际表达同一个能力域 | 跨仓库对比发现语义重复 |

---

## 六、优化路线图

### 阶段一：验证新模型的可行性（立即）

**实验 1：Ontology Agreement Experiment**

- 选 5-10 个 AI agent 框架
- 每个独立跑 ≥ 5 次
- 只提取一级能力域（不是 Entity、不是 Concept）
- 统计 Inter-run Agreement（Jaccard / F1）和收敛速度
- 跨模型比较（Claude / GPT 至少两个模型）
- **回答：Framework Ontology 是否可以稳定恢复？是否经过几轮迭代后收敛？**

**实验 2：Structural Entity 稳定性对比**

- 同一个仓库
- Path A：纯 Structural Entity（Module/Package/Class）
- Path B：混合 Entity（当前做法）
- 各跑 3 次，比较命名稳定性和 downstream Concept 质量

### 阶段二：重建知识模型（短期，依赖阶段一结果）

**2.1 将 Entity 固化为 Structural Entity**

- 修改 `/analyze` 的 Entity 提取 prompt：只提取 Module/Package/Class 级别的代码对象
- Semantic Role 作为属性挂到 Structural Entity 上（frontmatter 增加 `role:` 字段）
- 现有 Entity 页做一次迁移：拆分为 Structural Entity + Role

**2.2 引入 Ontology 层**

- 新目录：`wiki/ontology/` —— 存放 Framework Ontology 节点
- 每个 Ontology 节点定义：能力域名、核心关切、下属 Design Knowledge 列表
- 初始 Ontology 由实验 1 的结果归纳而来（不是人工规定）
- 实现 Ontology Maintainer agent（只做 Match/Add/Split/Merge 四件事）

**2.3 重新定义 Concept（Design Knowledge Unit）**

- Concept 不再直接面对 Entity，而是挂在 Ontology 节点下
- 每个 Concept 回答：在 `Memory` 这个能力域下，`Persistence` 这个设计问题上有哪些已知的权衡位置
- 分离三层：Alias → Ontology Class → Knowledge View

### 阶段三：调整产出体系（中期）

**3.1 重新定义五个维度**

- Architecture → Topology
- Extension Points → Variation Point
- Performance Tradeoffs → Constraint
- Dependency Strategy → Boundary
- Testing Philosophy → Reliability Strategy
- 维度指南 (`schema/dimensions.md`) 同步更新

**3.2 分离 Presentation Layer**

- Knowledge Views 作为独立的生成层
- `/query` 动态生成 Views，不参与 Extraction 管线
- Views 格式由用户的查询意图决定（对比表、设计空间地图、决策记录）

**3.3 将分类后置**

- 移除 `/analyze` 中的分类前置假设
- Category 由聚类自然产生，不作为 Concept 提取的前置过滤

### 阶段四：流程工程化（长期）

- Ontology Maintainer 固化为独立 skill
- Ontology 版本化管理（每次 Match/Add/Split/Merge 记录变更）
- 建立证据驱动的决策方法：每个核心设计决策至少参考 3 个以上成熟项目或研究工作

---

## 七、问题解决状态总览

| # | 问题 | 状态 | 结论摘要 |
|---|------|------|---------|
| 1 | Entity 的定义 | ✅ 已解决 | Structural Object（Module/Package/Class），Role 是属性 |
| 2 | Concept 是知识还是索引 | ✅ 已解决 | 是 Ontology Class，需与 Alias 和 Knowledge View 分离 |
| 3 | Ontology 可稳定恢复 | 🔄 重新框定 | 一次性恢复做不到，增量收敛可以；需实验验证收敛速度 |
| 4 | 用户角色 | ✅ 已确认 | Framework Builder，需要 Design Decisions/Tradeoffs/Rationale |
| 5 | 分类前置矛盾 | ✅ 已解决 | Category 后置，由聚类产生 |
| 6 | Presentation Layer 分离 | ✅ 已确认 | View 是 Projection，不参与 Extraction |
| 7 | 五个维度 | ✅ 已解决 | 保留但重新定义为 Topology/Variation/Constraint/Boundary/Reliability |
| 🆕 | 缺少 Ontology 层 | 🔴 **核心发现** | 这是之前所有问题的根因——跳过了 Ontology 直接从 Entity 到 Concept |

---

## 八、附录：关键文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 项目 CLAUDE.md | `CLAUDE.md` | 架构、管线、设计原则 |
| 执行方案 | `docs/design/execution-plan.md` | 人机分工、回退 DesignDecision、Concept 定位 |
| Concept 角色与边界 | `docs/design/concept-role-and-limitations.md` | Concept 是索引不是消歧，准入三问 |
| Dimension-Node 脱耦 | `docs/design/dimension-node-decoupling-analysis.md` | frontmatter 边表、graph.py 派生 |
| DeepWiki vs Source 实验 | `experiments/deepwiki-vs-source/EXPERIMENT.md` | 8 轮实验设计与结论 |
| 最终实验报告 | `experiments/deepwiki-vs-source/evaluation/final-comparison-report.md` | 内容质量与 Concept 提取价值 |
| Concept 提取 V2 | `experiments/entity-concept-extraction/CONCEPT-EXTRACTION-V2.md` | V2 流程定义 |
| V2 评估报告 | `experiments/entity-concept-extraction/evaluation-report.md` | 旧 vs 新流程对比 |
| V2 管线验证 | `experiments/entity-concept-extraction/v2-validation-2026-06-19/README.md` | 五维度 vs 历史基线 |
| 新流程验证 | `experiments/deepwiki-vs-source/evaluation/new-flow-validation.md` | 5 agent 串行 + 对抗式评审 |
| GPT 讨论 06-10 | `docs/research/gpt-concept分析.md` | 首次 Concept 角色讨论 |
| GPT 讨论 06-13 | `docs/research/gpt-concept深入分析-0613.md` | Concept = 索引不是知识 |
| Karpathy 原文 | `docs/research/karpathy-llm-wiki-gist.md` | LLM Wiki 模式原始配方 |

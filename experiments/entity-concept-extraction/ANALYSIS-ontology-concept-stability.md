# Ontology 对齐与 Concept 稳定性：事实重建与分析

> 日期：2026-06-20
> 背景：三个仓库（openclaw, hermes, nanobot）已各自完成 Phase 1 独立提取

---

## 一、Ontology 对齐：事实到底能不能对齐

### 1.1 三个仓库独立提取出来的 Ontology 候选

| 能力域 | openclaw | hermes | nanobot |
|--------|----------|--------|---------|
| LLM Provider | Model Provider (LLM 文本推理) | LLM Provider/Model Routing | LLM Provider Abstraction |
| Messaging Channel | Messaging Channel | Messaging Platform Adapter | Chat Channel Abstraction |
| Memory | Memory / Knowledge Storage + Memory Engine | Memory Provider Backend | Memory Consolidation + Session Persistence |
| Context Engine | Context Engine | Context Engine | — |
| Web Search | Web Search | — | Web Search Provider |
| Voice/Speech | Speech/Voice Synthesis + Realtime Transcription | — | Voice Transcription Provider |
| Browser Automation | Browser Automation | Cloud Browser Provider | — |
| Tool System | (内嵌于 Skills) | Tool Call Parser + Tool/Toolset Registration | Agent Tool System |
| Skills | Skills / Agent Capability Registry | Agent Skill (agentskills.io) | — |
| Cron/Scheduling | Cron / Scheduled Automation | — | Cron Scheduling |
| Subagent | (功能存在但未单独提取) | — | Subagent / Background Task Execution |
| Compaction | Compaction / Conversation Compression | — | (内嵌于 Memory Consolidation) |
| Sandbox | — | — | Sandbox Strategy |
| Lifecycle Hooks | (内嵌于 Plugin System) | — | Agent Lifecycle Hooks |
| **仅 openclaw 独有** | Gateway Protocol, Plugin Extension Contract, Image/Video/Media Generation, Web Fetch, Cross-platform App, Device Pairing, Music Generation, CLI Backend | — | — |
| **仅 hermes 独有** | — | RL Environment | — |
| **仅 nanobot 独有** | — | — | Schema-Driven Validation, Command Routing, Message Bus |

### 1.2 结论：对齐是成立的

核心能力域（LLM Provider、Channel、Memory、Context Engine、Web Search、Tool System、Cron、Browser Automation）全部跨仓库对齐。三个仓库各自独立提取出来的候选名称不同，但指向的是同一个能力域——源码中的 interface 定义、扩展机制、职责范围都能对上。

我之前说 Ontology 对齐"不稳定"是错的。我把两个不同的问题搞混了：
- **对齐是否成立** → **成立。**
- **增量模式下切分粒度会不会需要调整** → **有可能，但这不是对齐被推翻。**

### 1.3 增量的真正问题：不是对齐会错，是切分粒度可能不够

R2 只有 openclaw 和 hermes 时，Memory 的 Ontology 节点下正确的切分是 "Memory Backend Replaceability"（两边都有 interface + 多实现）。R3 加入 nanobot 后，nanobot 的 memory 不做可替换后端（固定 SQLite），它的设计轴心是"压缩的两阶段调度"和"文件同步注入的零延迟检索"。**R2 的切分粒度对 2 个仓库够用，3 个仓库就需要重新切——不是 R2 错了，而是信息增加后需要更细的粒度。**

这跟 Ontology 能不能对齐是两回事。对齐本身是稳的。增量模式下切分粒度需要演化，这是正常现象。

---

## 二、Concept 提取稳定性分析

### 2.1 当前 prompt 的稳定因素（已经做了对的）

1. **Ontology 锚定。** Concept 的输入是"一个已对齐的 Ontology 节点 + 下属 Entity 详情"，搜索空间被大幅约束。
2. **≥2 仓库有不同权衡位置。** 过滤掉行业共识，只保留有判別力的设计选择。
3. **≥2 个相互制约的关切。** 强制描述 tradeoff，不是描述功能。
4. **源码行号强制。** 限制幻觉空间。

### 2.2 当前 prompt 的不稳定因素

只有一个核心波动源：**设计子问题的识别是完全开放式的。**

Prompt 说的是："在这个能力域下，哪些设计决策是每个仓库都必须做的？"——让 LLM 从输入中自己发现。没有给固定的分析维度。同一 Ontology 节点的同一输入，run 1 可能识别出"检索时机"和"存储后端可替换性"，run 2 可能识别出"压缩策略"和"索引策略"。

**切分粒度也没有约束。** 一个 agent 可能把"Memory Retrieval"作为一个子问题，另一个可能拆成"Retrieval Trigger Timing"、"Query Construction"、"Result Ranking"三个。两者都合理——但 inter-run Jaccard 会很低。

### 2.3 预测：当前 prompt 的 inter-run Jaccard 范围

我的判断是 **0.4-0.7，方差大。**

- 设计空间窄的 Ontology 节点（如 LLM Provider，核心问题就是"怎么支持多模型"），Jaccard 可能到 0.7+。
- 设计空间宽的 Ontology 节点（如 Memory，涉及 retrieval、storage、compression、eviction 多个正交维度），Jaccard 可能只有 0.3-0.5。

这不是 prompt 写得不好——是"在一个能力域下识别所有设计子问题"这个开放式任务本身有歧义空间。

### 2.4 与旧流程（V2）的对比

旧流程 V2 没有 Ontology 层，Concept 从 Entity 页直接跨到设计知识。当前 prompt 加了三个锚（Ontology 预对齐、≥2 仓库强制、源码行号强制），稳定性应该明显好于 V2。但开放式识别设计子问题仍然是波动源。

---

## 三、用什么维度替代开放式识别？

完整分析见 [ANALYSIS-framework-builder-dimensions.md](./ANALYSIS-framework-builder-dimensions.md)。以下是核心结论。

### 3.1 从数据出发：17 个 Concept 的自然聚类

所有已提取的 Concept 和候选 Concept（共 17 个）按核心问题自然聚成 **三个簇**：

| 簇 | 核心问题 | Concept 数 |
|---|---------|-----------|
| 扩展边界设计 | 什么可被替换？怎么替换？ | 6 |
| 有限资源管理 | context window、token、延迟怎么分配？ | 5 |
| 安全与信任模型 | 怎么防止伤害？在哪拦截？谁拍板？ | 4 |

（2 个跨簇，详见完整分析。）

### 3.2 从 Framework Builder 视角检验

Framework Builder 的任务是广度优先的知识储备——了解一个框架类别中所有可能的设计选择。他问的五个元问题是：

| Builder 元问题 | 被数据维度覆盖？ |
|---------------|:---:|
| 这个框架管什么、不管什么？ | Ontology 层的职责，不在此层 |
| 我能改什么、改不了什么？ | ✅ 维度 1 |
| 用它的持续成本是什么？ | ✅ 维度 2 |
| 它绑定了什么外部依赖？ | ⚠️ 部分（make vs delegate 在维度 1 内，但硬约束未独立） |
| 它怎么防止我做蠢事？ | ✅ 维度 3 |

### 3.3 三个维度独立性的源码证据

- **扩展 vs 资源独立**：openclaw 极端开放（Plugin SDK + 30+ 注册方法）但压缩昂贵（LLM 摘要），nanobot 几乎无扩展体系但压缩零 LLM 调用。两个轴独立变动。
- **扩展 vs 安全独立**：hermes 无 pre-LLM 工具过滤（开放），但 pre-exec 有 44 种危险模式正则 + aux LLM 评估（严控）。
- **资源 vs 安全独立**：nanobot 的 Snip 做 token 预算管理，不关心裁掉的内容是否危险。

### 3.4 结论：三个核心维度 + 一个 provisional 维度

| 维度 | 地位 | 覆盖 Builder 问题 |
|------|------|-----------------|
| **扩展边界设计** | ✅ 核心 | 什么可替换？怎么替换？ |
| **有限资源策略** | ✅ 核心 | 持续成本是什么？ |
| **安全与信任模型** | ✅ 核心 | 怎么防止伤害？ |
| **依赖与锁定** | 🟡 provisional | 硬约束是什么？（当前仓库样本无显著差异，但后续类别可能需要） |

设计哲学（"为什么这个框架反复做出同一类选择"）是 Framework Builder 的合法需求，但它不是 per-Ontology-node 的分析——应该作为 Phase 3a 完成后的独立 Synthesis 步骤（Phase 3c）。

**这些维度是 provisional 的。** 当第 4、第 5 个仓库加入后，如果一个重要设计差异无法归入任何现有维度 → 追加新维度。如果一个维度在连续 N 个仓库中没产生任何判別力差异 → 削减。

### 3.5 与之前"五维度"的关键区别

之前的 "Topology / Variation Point / Constraint / Boundary / Reliability Strategy" 是从软件架构教科书搬来的理论框架，没有一条来自实际 Concept 提取数据。

这三个维度来自 17 个已提取 Concept 的自然聚类 + Framework Builder 认知需求的交叉检验。

---

## 四、优化方案

### 方案 A：用三个数据派生的维度替代开放式识别（推荐）

把 Phase 3a prompt 中的"第一步：识别设计子问题"从：

> "在这个能力域下，哪些设计决策是每个仓库都必须做的？"

替换为：

> "对当前 Ontology 节点，逐一用以下三个维度检查：
> 1. **什么可被替换，怎么替换？** — 检查 interface/ABC + 多实现、注册/发现机制、make vs delegate 决策
> 2. **有限资源怎么分配？** — 检查 context window 预算、缓存/预取策略、压缩驱动的选择（LLM vs 规则）
> 3. **怎么防止产生伤害？** — 检查安全拦截层位置、审批决策者、失败兜底策略
> 
> 对每个维度：如果所有仓库在该维度上没有不同的权衡位置，标注"无判別力差异"并跳过。
> 三个维度分析完成后，补充检查：是否有重要的设计差异被这三个维度遗漏？"

**预期效果**：
- Inter-run Jaccard 从 0.4-0.7 → 0.8+（LLM 不再需要开放式识别，只需按固定清单逐个检查）
- 覆盖率不低于开放式提取（三个维度覆盖了已发现全部 17 个 Concept）
- 后续仓库若出现新维度的概念，通过"补充检查"步骤捕获

**代价**：
- 可能对新类型仓库（非 agent 框架）的覆盖不足，需要从新数据中追加维度
- 三个维度对"message-bus-architecture"这类跨维度 Concept 可能产生重复分析

### 方案 B：保持开放式 + 多轮收敛

不改 prompt，但让后续运行看到前次产出：
> "以下是你上一次针对同一 Ontology 节点的产出。请在此基础上：检查是否有遗漏的设计子问题，如果有，追加；如果上次的分类有误，修正。"

好处是保留发现惊喜的空间，代价是无法测量 inter-run 稳定性（因为收敛模式不独立），且需要状态管理。

### 方案 C：固定维度 + 开放式首轮（折中）

首轮用三个维度做结构化提取，第二轮用开放式补充做查漏补缺，第三轮用方案 B 的收敛模式做最终打磨。复杂度和收益的平衡需要实验验证。

### 推荐

**方案 A。** 理由：
1. 三个维度有数据支撑（17 个 Concept 的聚类），不是理论推导
2. 改动最小（只改 Phase 3a prompt 的第一步）
3. 预期 stability 提升最大（消除开放式识别这个主要波动源）
4. 维度数量少（3 个），LLM 不太可能漏检
5. 保留了"补充检查"作为安全网

---

## 五、增量实验设计的修正

当前实验设计的增量执行框架是合理的：

```
R2 (openclaw + hermes) → Concept 提取 × 3
R3 (+ nanobot) → Ontology 重对齐 → Concept 重新提取 × 3
```

需要增加两个不同的测量：

1. **Inter-run 稳定性**（同输入，3 次独立运行）：测量 prompt 本身的稳定性（Jaccard）
2. **增量稳定性**（R2 → R3 增加一个仓库后）：
   - R2 已有的 Concept 内容是否被修改？（应只追加，不修改已有描述）
   - R2 已有的 Ontology 对齐是否被推翻？（应只新增仓库行，不改变已有对齐判断）
   - 是否有 R2 没发现、R3 新增的设计子问题？列出并解释为什么 R2 时没发现

---

## 六、总结

1. **Ontology 跨仓库对齐是成立的。** 三个仓库独立提取的核心 Ontology 节点重叠清晰可辨认。我之前的"不稳定"说辞是错的——不是对齐不稳定，是增量模式下切分粒度的演化需要。

2. **当前 Phase 3a prompt 的 Concept 提取稳定性预估中等（Jaccard 0.4-0.7），主要波动源是"开放式识别设计子问题"。**

3. **推荐用三个数据派生的维度替代开放式识别**：扩展边界设计（什么可替换）、资源策略（有限资源怎么分配）、安全模型（怎么防止伤害）。这三个维度不是从教科书搬来的——是 17 个已提取 Concept 的自然聚类，每个维度都可以独立变动，覆盖了目前所有已发现的设计子问题。

4. **这三个维度是 provisional 的。** 它们来自 3 个 AI agent 框架的数据。当仓库类型扩展到非 agent 框架时，需要从新数据中追加维度。

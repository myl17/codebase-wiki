# Concept 的角色、机制与边界

> 基于 `docs/analysis/2026-06-11-codebase-wiki-architecture-review.md` 的分析与推演，澄清 Concept 体系到底解决什么问题、不解决什么问题。

---

## 一、Concept 不是传统知识图谱的「实体消歧」

### 传统消歧

传统知识图谱的 Entity Resolution：

```
多个指称 → 判定指向同一实体 → 合并为一个规范化节点

"纽约" / "New York" / "NYC" → 同一个 city 实体 → 只有一个节点保留
```

合并是最终操作。消歧 = 确认同一性 + 去重。

### codebase-wiki 的 Concept 映射

```
openclaw:exec-approval ──embodies──→  Concept: 人机审批协议  ←──embodies── hermes-agent:approval-system
```

两个 node **绝不合并**。它们是不同仓库、不同语言、不同接口的两个代码单元。合并它们等于丢失所有差异信息，而这些差异正是 `/compare` 的核心产出。

Concept 在这里做的不是消歧，是**归类（Concept Mapping）**。更准确的名字是「术语收敛」而非「实体消歧」。

---

## 二、没有 Concept 时会发生什么

### 问题：跨仓库孤岛

假设 ingest 了 5 个仓库，每个 ~15 个节点。没有 Concept：

```
repo A: 15 nodes    repo B: 15 nodes    repo C: 15 nodes
全部独立，零跨仓库连接
```

架构师想知道"各仓库都是怎么做审批的"，他必须：
1. 先知道自己要找的东西大概是"审批"相关的
2. 去 repo A 的 node 里找到一个叫 `exec-approval` 的节点
3. 去 repo B 的 node 里找到一个叫 `approval-system` 的节点
4. 去 repo C 的 node 里发现它叫 `command-gate`
5. 自己判断这三个说的是不是同一回事

他查不了的原因恰好是他想知道的：他不知道不同仓库叫法不同。

### 问题：术语漂移

更重要的是，ingest repo C 的 LLM 是独立工作的。它不知道 repo A 和 B 已经各自有了审批相关的节点和术语。它可能：
- 发明第三个名字 `command-gate`
- 或者干脆不认为这个东西值得提取为一个 node

每多 ingest 一个仓库，术语就多一个变体。孤岛持续扩大，且是不可逆的累积。

---

## 三、Concept 实际做了什么

### 本质上：术语收敛机制

Concept 体系保证一件事：**新增节点必须先用已有词汇表匹配，匹配不到才能提议新词。**

```
新节点产出后:

1. LLM 读 _index.md 全文 —— 40 行，4 个 Concept 及其别名
2. 匹配: "接口+多实现+注册机制" → 别名列命中 "扩展注册机制" → concept: 插件系统
   无匹配 → concept_candidate: <提议名>（暂不入索引，攒批待人工确认）
```

这不是消歧，这是**用索引约束 LLM 的命名行为**。每少一个重复命名，`/compare` 就少一个需要人工发现的「其实这两个说的是一回事」。

### 别名列 = 零基础设施的术语对齐

```markdown
| Concept | 别名/曾用名 | 定义 | 实例数 |
|---------|------------|------|--------|
| 人机审批协议 | Approval Protocol, Exec Guard, 命令门控 | ... | 2 |
```

LLM 看到节点叫 `exec-approval`，翻索引时在别名列找到 `Exec Guard`——匹配成功。不需要 embedding、不需要规则引擎。别名列本身就是对齐机制，且别名本身是知识（"这个模式在不同社区被叫什么"）。

### 跨仓库遍历的唯一桥梁

`graph.py query` 做跨仓库查询时，遍历路径是：

```
openclaw:exec-approval ──embodies──→ 人机审批协议 ←──embodies── hermes-agent:approval-system
```

Concept 是这条路径上唯一的汇聚点。两个 node 之间没有直连边（设计原则："两个具体实例永远不直接连接"）。没有 Concept 这个中间节点，遍历就不可达。

### `/compare` 的输入前提

`compare` 产出"OpenClaw 用 5 层同步门控 vs Hermes 用 3 层交互式审批"这种有判别力的差异——这个结论的前提是**你已经知道两者在讲同一件事**。Concept 的 `embodies` 边就是那个"同一件事"的声明。

---

## 四、Concept 不解决什么

### 不解决 node 数量膨胀

这是一个明确的设计空白。架构评审讨论了 20 仓库 ≈ 300 节点，但结论是：

> 300 个节点、几十个 Concept——一次 LLM 调用读完整个概念索引绰绰有余。

这个讨论是针对检索基础设施的规模判断（不需要 embedding ANN），不是说 300 个 node 页对人来说不构成认知负担。实际上：

- 每个 repo ~15 个 node 页，随仓库数**线性增长**
- 同 Concept 下挂 8 个实例时，每个 node 页底部的 `## 关联` 区块列出 8 个同概念兄弟——信息量递减
- 去重测试（验证标准 3）是质量门控不是数量预算——没有"每 repo 最多 N 个 node"的硬约束

没有任何机制阻止一个 repo 提出 30 个弱 node。

### 不合并节点

Node 始终独立存在，保留原始命名。不同仓库对同一 Concept 的实例分别叫 `memory-system` 和 `memory-provider`，这是**故意的**——命名差异本身就是对比信息（"这个概念在不同仓库里怎么落地"）。

### Concept 不做自动重命名

当一个 node 匹配到 Concept 后，node 的 slug 不变。`exec-approval` 不会变成 `审批协议` 或 `approval-protocol`。变更的是 frontmatter 里填了 `concept:` 字段，以及由此产生的图边。命名差异保留在 node 层，由 Concept 的别名列来捕获。

---

## 五、「图谱很小是健康状态」的真实含义

架构评审 §4.9：

> 分诊后索引仅 6-8 个 Concept，"图谱很小"是健康状态（参照 Wikontic：图小 20 倍、信息保留 86%）。概念体系的价值密度比节点数量重要——归一化锚点被污染的代价是后续所有仓库的归一化跟着歪。

这句话里的"图谱"指的是**Concept 体系本身**，不是整个 graph.json。

### 两层不同的规模约束

| 层 | 规模 | 约束 | 逻辑 |
|----|------|------|------|
| **Node** | 随仓库线性增长（20 仓库 ≈ 300 node） | 三步验证（连通性+受众问题+去重）——质量门槛，非数量上限 | 按 repo 目录组织，看单个 repo 时只看到 ~15 个 |
| **Concept** | 收敛到远小于 Node 总数的稳定集（目标 6-8 个，长期 < 20 个） | 准入三问——硬性质量门槛，且要求多实例才准入 | 全局唯一索引，被污染的代价是所有仓库的归一化跟着歪 |

### 骨架与肉

Concept 与 Node 的理想数量关系：

```
Concept : Node ≈ 1 : 15 ~ 1 : 30

6-8 个 Concept 锚定 ~300 个 Node → 健康
50 个 Concept 锚定 ~300 个 Node → 归一化失效（每个 Node 几乎是独立 Concept）
```

如果 Concept 和 Node 数量接近，说明你没有在归并任何东西——你只是在给每个 Node 贴了一个唯一的 Concept 标签，那 Concept 体系就形同虚设。

准入三问的第二问（"跨仓库汇合能得出有差异的结论吗"）正是这个逻辑的机制保证：**单实例不能成为 Concept**。每个 Concept 必须至少被两个 repo 的节点指向。这确保了 Concept 数量不随 repo 线性增长，而是收敛到一个远小于 Node 总数的稳定集。

---

## 六、总结

| 问题 | Concept 的答案 |
|------|---------------|
| 传统实体消歧（合并） | ❌ 不做。Node 保持独立 |
| 术语漂移（新仓库发明新名字指代老问题） | ✅ 别名列 + LLM 终判强制收敛 |
| 跨仓库遍历无路径 | ✅ embodies 边提供汇聚锚点 |
| `/compare` 不知道谁跟谁是可比的 | ✅ Concept 声明"讲的是一件事" |
| Node 数量爆炸 | ❌ 不解决。验证门控是质量门槛不是数量预算 |
| Concept 自身的膨胀 | ✅ 准入三问 + 多实例要求控制到远小于 Node 总数 |

# Dimension 页与 Node 页的脱耦设计、节点提取与实体消歧

> 基于 `docs/analysis/2026-06-11-codebase-wiki-architecture-review.md`（代码优化的实际依据）

---

## 一、Dimension 页与 Node 页的关系：脱耦但连线

### 1.1 原始设计的问题

原始设计文档（`docs/design/codebase-knowledge-graph-design.md`）的诊断被架构评审全盘接受：

> **Entity 扁平化。** `[[插件系统]]`（子系统级能力）与 `[[单例模式]]`（函数级技法）在同一 namespace 中是平等节点。
> **无边类型。** wikilink 不表达方向、语义、置信度。
> **归一化无锚点。** 不同 Agent 在不同维度页标注同一事物时无约束。

根本原因是：**一个 dimension 页不是图谱节点——它是几十个节点的叙事容器。** 把 entity wikilink 撒在叙事行文里，等于把结构化数据溶解在了自由文本。

### 1.2 架构评审的修正方案

架构评审对原始设计的处方提出了四项批判，其中最关键的修正落在**存储模型**上。

**原始设计的问题**：L2 图谱存为独立 `graph.yaml`，L3 跨仓库概念存为独立 `concepts.yaml`。

架构评审的批判：

> graph.yaml + concepts.yaml 独立存储引入**叙事层与图谱层双写漂移**：LLM 改了叙事忘改 yaml（或反之），设计文档未给出任何同步机制，lint 事后也无法裁决哪边是事实。这等于把 wiki 变成需要 DBA 的数据库。

**修正方案（建议 1 + 建议 5）**：

- 节点不存 `graph.yaml`，而是成为 wiki 页面本身：`wiki/repos/<repo>/nodes/<type>/<slug>.md`
- 节点页的 frontmatter 携带结构化数据（`node_type`、`scope`、`concept`、`targets`、`motivated_by`、`sources`、`extracted_from`）
- body 是人话描述 + provenance——Obsidian 可读可点
- `graph.py build` 扫描所有 frontmatter，**派生**出 `graph.json`
- **规则：叙事页 + 节点页 frontmatter 是唯一事实源。任何图谱文件必须由脚本生成。**

这就是脱耦的核心：

```
dimension 页（叙事层）              node 页（结构化实体）
    L1                                    L2
  markdown 自由文本               markdown + frontmatter 边表
  给人读，给 LLM 读                给人读，给程序遍历
       │                                    │
       │  用 [[wikilink]] 引用 node 页        │  用 extracted_from 记录来源维度
       │  （做导航，不是图谱边）               │  （做溯源，可审计）
       └────────────← →──────────────────────┘
                        │
                 graph.py build
                 （派生，不是独立存储）
                        │
                        ↓
                 graph.json
                 （只读派生文件，错了改 frontmatter 重 build）
```

**脱耦但不失联**：dimension 页引用 node 页、node 页记录来自哪个维度、graph.py 自动生成双向的 `## 关联` 区块和 Mermaid 决策链。

### 1.3 为什么用 node 页面而不是独立 yaml

架构评审给出了明确理由：

> 每个节点同时是图谱数据（脚本读 frontmatter 即得边表）和 wiki 页面（Obsidian 可读可点，Dataview 可查询）。图谱对人可审阅、可纠错——直接缓解 spec 已知风险"LLM 提取质量不稳定"。

> 这是 karpathy 模式的延续（"entity pages, concept pages" 本是 llm-wiki 原生构件），只是给代码场景加上类型化 frontmatter——收紧约定，不更换架构。

---

## 二、三种 Node 的提取方式

### 2.1 节点类型设计

架构评审**保留**了原始设计的四类节点分类，因为它的受众绑定是有价值的：

| 节点类型 | 绑定受众 | 对应问题 |
|---------|---------|---------|
| Component | 二开人员 | 改这里会波及什么？ |
| ExtensionPoint | 二开人员 | 这里怎么扩展？ |
| DesignDecision | 架构师 | 为什么这样设计？ |
| Concept | 架构师 | 不同仓库同一问题怎么做？ |

> 它优于通用四类（Concept/Decision/Mechanism/Artifact），因为 ExtensionPoint ↔ 二开者、DesignDecision ↔ 架构师是与目标用户的一比一映射。

### 2.2 不同节点类型的提取路径

架构评审没有按自动化程度来分类提取方式，而是按**提取信号**区分：

**Component**：
- 提取信号：独立目录 + 入口文件 + 独立职责
- 实例：`src/context-engine/`、`src/cron/`、`src/memory-host-sdk/`

**ExtensionPoint**：
- 提取信号：interface + 多实现 / `register*` 方法 / hook 签名 / 配置 schema
- 实例：`ChannelPlugin<ResolvedAccount>`（13+ Adapter 实现）、`OpenClawPluginApi`（25 个 register 方法）、28 个 hook

**DesignDecision**：
- 提取信号：文档或注释中存在 "选 X 不选 Y 因为 Z" 的因果链
- 实例："5 层同步门控 pipeline 而非异步审计"、"Memory 在 prompt 组装时注入而非实时查询"

### 2.3 两步分离：提取宽松、验证严格

这是 `graph-schema.md` Step 3.5 的核心机制：

**提取（宽松）**：
- 在维度页中有具名的代码边界
- 具备三种 node_type 之一的典型结构特征
- 不设上限，宁可多提

**验证（严格）——三项测试全部通过才写入节点页**：

| # | 测试 | 内容 | 设计意图 |
|---|------|------|---------|
| 1 | **连通性测试** | 节点必须有至少一条边（`concept` / `concept_candidate` / `targets` / `motivated_by` 任一非空） | 孤立节点在图谱中没有遍历价值，等同于复述维度页内容 |
| 2 | **受众问题测试** | 节点必须能直接回答"波及什么？""怎么扩展？""为什么这样设计？"之一 | 问不出来 = 对图谱无贡献 |
| 3 | **去重测试** | 节点不能是另一节点的属性 | 例：某组件的"独占注册槽位"是该 Component 的属性，不是独立 ExtensionPoint |

### 2.4 哪些东西故意不入图

架构评审明确排除的三类：

- 函数名、类名、文件路径（实现细节，留在叙事文本里当 provenance）
- 教科书模式——单例、懒加载、退避。任何仓库都有，汇合无信息量
- 工具/库名——Vitest、pytest。package.json 一眼可见，不需要 LLM 沉淀

### 2.5 Type × Scope 二维体系

架构评审把原始设计的 L1-L4 金字塔（单轴）改成了两个正交字段：

| 字段 | 用途 | 词表 |
|------|------|------|
| `node_type` | **管边的合法性**（谁可以连谁） | Component / ExtensionPoint / DesignDecision |
| `scope` | **只管展示与排序**（不参与连边合法性判断） | system / subsystem / component |

> L1-L4 金字塔把抽象程度、归一化可行性、连边合法性压进一根轴，导致"同层才连边"的别扭规则。改为两个正交字段后，砍掉了跨层禁连规则。

Scope 的判定标准是**替换爆炸半径测试**：

> 假设把这个节点代表的东西删除或彻底替换，最小重写单元是什么？

- `system`：主数据流必经路径上且不可替换的 / 约束某类操作全部实例的
- `subsystem`：有独立目录+接口边界的能力单元，删除失去一项能力但其余照常
- `component`：能力单元内部的一个机制，删除退化一个行为

关键判例："调用了其他子系统"不等于爆炸半径大。一个调度器调用了任务、agent、消息通道，但删除它只需要重写它自己 → `subsystem`，不是 `system`。

---

## 三、实体消歧（归一化）

### 3.1 问题的特殊性

架构评审指出，代码仓库场景的归一化比自然语言文本场景更困难，因为实体有两个截然不同的层次：

- **仓库作者发明的名字**：`ChannelPlugin`、`registerMemoryCapability`、`StateGraph` → 仓库特有
- **跨仓库通用概念**：插件系统、Context 压缩、审批协议 → 可比但对齐困难

gpt-concept分析.md 的核心论点：归一化难题正源于这种**类型的类型**——你必须先分清楚"这是仓库特产还是通用模式"，才能做消歧。

### 3.2 架构评审的方案：概念索引 + LLM 终判

架构评审（建议 4）大幅简化了原始设计的方案：

**归一化的唯一锚点**：`wiki/entities/_index.md`

```markdown
| Concept | 别名/曾用名 | 一句话定义 | 实例数 |
|---------|------------|-----------|--------|
| 插件系统 | Plugin System, 扩展注册机制 | 注册 API 或 manifest 解耦核心与扩展 | 2 |
| Context 压缩 | Context Compression, compact | 上下文超限时的有损压缩策略 | 2 |
```

**归一化流程（ingest 中的一个步骤）**：

```
新节点产出后:

1. LLM 读 _index.md 全文
   （当前 4 个 Concept，不到 50 行；预计 20 仓库时 50-100 行）

2. LLM 匹配既有 Concept（含别名列）
   例：节点描述含"接口+多实现+注册方法"
     → 命中 alias "扩展注册机制" → concept: 插件系统
   无匹配 → 节点页标 concept_candidate: <提议名>

3. 人工确认候选批 → 过准入三问 → 新 Concept 入 _index.md

4. 反向轻量回溯：
   LLM 基于已有节点页回答："存量 repo 有没有类似这个新 Concept 的节点？"
```

### 3.3 为什么不用五阶段管线

架构评审对原始设计中的 blocking/embedding/matchers 方案给出了明确的拒绝理由：

> **规模错配。** 五阶段管线解决规模问题，本项目瓶颈是本体问题。Blocking/embedding 的价值在 O(n×m) 不可承受时才显现。20 仓库 × 每仓库约 15 节点 ≈ 300 节点、几十个 Concept——一次 LLM 调用读完整个概念索引绰绰有余，且全索引判断质量高于 embedding 预筛（无漏召回）。

> **matchers.yaml 是过早固化。** 签名规则应是归一化经验的沉淀产物，不是起点。设计文档方向 D 自认 Concept signature 会随新仓库演进——那为什么现在就要写死？

> **这正是 karpathy 原始配方（"LLM reads the index first... works surprisingly well at moderate scale, avoids embedding-based RAG infrastructure"）应用于归一化。**

### 3.4 别名列：零基础设施的消歧

架构评审指出，`_index.md` 的别名列本身就是归一化机制，且别名本身是知识：

> **别名列是零基础设施的归一化机制**，且别名本身是知识（"这个概念在不同社区叫什么"）。

例：一个节点名叫 "compact"、"context compression"，LLM 读索引时在别名列看到这两个都在 `Context 压缩` 下—匹配成功。不需要 embedding、不需要 matchers.yaml。

### 3.5 准入三问：消歧的质量门控

候选概念从 `concept_candidate` 升级为正式 Concept 前，必须**同时通过**三问（§4.8）：

| # | 测试 | 含义 | 通过 | 拒绝 |
|---|------|------|------|------|
| 1 | **问题测试** | 直接回答某个二开/架构师问题吗？ | `插件系统` → "怎么扩展" | `单例模式` → 不对应任何选型/二开问题 |
| 2 | **判别测试** | 跨仓库汇合能得出有差异的结论吗？ | `Context 压缩` → 阈值/策略/失败处理各家不同 | `分层架构` → 谁都有，汇合无信息量 |
| 3 | **沉淀测试** | 知识需读代码才能获得吗？ | `契约测试` → 须读 test infra 才发现 | `Vitest` → package.json 即得 |

**配套机制**：
- ingest 时 LLM **只能标 `concept_candidate`**，不能直接写 `concept:`。"标注"与"准入"拆为两个动作，门槛设在归一化步骤。
- 实现技法类词汇（单例、懒加载、退避）在叙事中保留为普通文本，不入概念体系。
- lint 不再检查"缺 entity 链接"，改为检查 `concept_candidate` 积压数量（`check_candidate_backlog`）。

### 3.6 存量 entity 分诊：准入三问的首次实战

架构评审 §4.9 逐页审计了 17 个存量 entity，执行分诊：

| 处置 | 对象 | 动作 |
|------|------|------|
| **保留为 Concept** | 插件系统、Context 压缩、Prompt Caching、并行工具执行、契约测试、性能预算 | 入 `_index.md`，补别名列 |
| **重新概念化** | OpenTelemetry → `可观测性集成` | 改名重写定义，原名进别名列 |
| **降级出局** | 单例模式、懒加载、指数退避、Vitest、TS monorepo | 删除 entity 页，叙事 wikilink 改回纯文本 |
| **观察名单** | 分层架构、优雅降级、故障隔离 | 暂不入索引，第 3-5 个仓库出现有判别力的变体时再准入 |

**结果**：17 个 → 合格 ~6 个，合格率约 1/3。

> 根因：旧规则（"凡属架构模式/技术栈/领域概念的词汇，首次出现时标记"）只有召回导向、没有精度门槛——标注永远是"安全"动作，滥标无惩罚。06-10 spec 的三层边界只挡住类名/函数名，挡不住"正确类别里的低价值成员"。

### 3.7 建立在本体质量之上的归一化

架构评审的核心理念：

> **先有合格的锚点，再有归一化；先验证查询价值，再扩建基础设施。**

> 概念体系的价值密度比节点数量重要——归一化锚点被污染的代价是后续所有仓库的归一化跟着歪。

---

## 四、总结

架构评审所做的工作，本质上是一次**减重**：原始设计把图谱理解成了需要独立存储和工业管线的数据库，架构评审把它重新理解为**带类型约束的 wiki 页面网络**。

| 维度 | 原始设计 | 架构评审 |
|------|---------|---------|
| Node 存储 | 独立 graph.yaml | wiki 页面 frontmatter |
| 图谱数据 | 独立事实源 | 派生文件（graph.py build） |
| 边数量 | 6 种 | 3 种起步 |
| 抽象层级 | L1-L4 单轴 | Type × Scope 正交 |
| 归一化 | 五阶段管线（阻塞→规则→embedding→LLM→重规范化） | 概念索引 + LLM 终判 + 别名列表 |
| 消歧锚点 | matchers.yaml 签名规则 | _index.md 别名 + 准入三问 |
| 价值验证 | Phase 5 排在最后 | Step 0 前置 |
| 维护成本 | 双 yaml 需同步 | 修改 frontmatter 重 build 即可 |

脱耦的本质，也是在这次减重中定型的：**dimension 页（叙事）和 node 页（结构化实体）从"存在不同文件格式中"的脱耦，变成了"同一格式（markdown）、不同页面、不同职责"的脱耦。** 脱耦在，但双写漂移被机制性地消除了。

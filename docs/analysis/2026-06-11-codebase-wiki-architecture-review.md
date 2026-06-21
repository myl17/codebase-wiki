# Codebase Wiki 方案分析与优化建议

**日期**:2026-06-11
**状态**:已确认
**性质**:对 `docs/codebase-knowledge-graph-design.md` 的全面评估与修订方案
**输入材料**:
- `docs/superpowers/specs/2026-06-07-codebase-wiki-design.md`(项目原始 spec)
- `docs/superpowers/specs/2026-06-09-manifest-hash-split-and-provenance-snippet.md`
- `docs/superpowers/specs/2026-06-10-entity-nodes-design.md`
- `docs/codebase-knowledge-graph-design.md`(最新图谱设计,本文评估对象)
- `docs/karpathy-llm-wiki-gist.md`(灵感原型)
- `docs/gpt-concept分析.md`(本体设计讨论)
- `schema/dimensions.md`、`schema/CLAUDE.md`、`wiki/` 现存实态(2 仓库、17 entity 页)

---

## 一、项目演进脉络与目标重梳

### 1.1 三个阶段

| 阶段 | 文档 | 核心机制 | 解决的问题 |
|------|------|---------|-----------|
| 维度叙事 | 06-07 spec | 5 维度提取 + 行级 provenance + compare 视图 | 跨仓库知识可对比 |
| 扁平 entity | 06-10 spec | 叙事中内联 entity wikilink,三类标签 | 概念级跨仓库关联 |
| 类型化图谱 | 06-11 设计文档 | 4 节点 6 边 + 三层图谱 + 五阶段归一化 | entity 扁平化、无边类型、归一化无锚点 |

### 1.2 不变的核心定位

Codebase Wiki 是**架构师用 LLM 进行跨项目代码研究的工具**,目标用户是二开开发者与架构师。区别于通用 llm-wiki 的四项护城河,在三个阶段中始终成立,本方案不触碰:

1. **维度表**(`schema/dimensions.md`)——代码仓库专属提取框架,保证跨仓库可比;
2. **行级 provenance**(`^[file:line]`)——每个 claim 可回溯源码;
3. **delta.py 增量机制**——文件级变更检测 + core/impl/config 分层;
4. **compare 一等功能**——按 category/dimension 组织,不随仓库数爆炸。

### 1.3 与通用 llm-wiki 的本质差异

Karpathy 原文处理的是**自然语言源**(文章、论文、章节),实体边界靠 LLM 语义判断;代码仓库场景的特殊性在于:

- **源材料自带结构**(目录、类型系统、import 图),部分提取可程序化;
- **实体有两个截然不同的层次**:仓库作者发明的名字(StateGraph、Todo)与跨仓库通用概念(Execution Control)——通用 llm-wiki 无此分裂,代码场景的归一化难题正源于此(gpt-concept分析.md 的核心论点);
- **受众问题高度收敛**:"怎么扩展 / 为什么这样设计 / 改这里波及什么 / 各家怎么做"四类问题覆盖绝大多数查询,知识结构应该围绕这四问设计,而非追求百科全书式完备。

---

## 二、对最新设计文档的评估

### 2.1 诊断正确

设计文档第一节对现状的三个判断全部成立,本方案全盘接受:

1. **Entity 扁平化**——`[[插件系统]]`(子系统级能力)与 `[[单例模式]]`(函数级技法)同处一个 namespace;
2. **无边类型**——wikilink 不表达方向、语义、置信度;
3. **归一化无锚点**——不同 Agent 在不同维度页标注同一事物时无约束。

"一个 dimension 页不是图谱节点,而是几十个节点的叙事容器"的根因分析尤其准确。

### 2.2 处方剂量过重——四项批判

**批判 1:规模错配。** Apple Saga(数十亿事实)与 Wikontic 的方案被移植到 2 仓库、17 entity 的个人工具上。Embedding ANN 索引、matchers.yaml、周期批量重规范化,是在本体未经数据验证前就建的工业级机器。20 仓库 × 每仓库约 15 节点 ≈ 300 节点、几十个 Concept——一次 LLM 调用读完整个概念索引绰绰有余,且全索引判断质量高于 embedding 预筛(无漏召回)。06-10 spec 自己写过"repo 数量有限时不需要 embedding",仓库数未变,结论却反转。

**批判 2:背离 karpathy 模式的根基。** llm-wiki 成立的前提是"维护成本近零——LLM 改的就是 markdown"。graph.yaml + concepts.yaml 独立存储引入**叙事层与图谱层双写漂移**:LLM 改了叙事忘改 yaml(或反之),设计文档未给出任何同步机制,lint 事后也无法裁决哪边是事实。这等于把 wiki 变成需要 DBA 的数据库。本项目已确立的反双写哲学(schema/CLAUDE.md:"没有 status 字段,staleness 在查询时计算")恰好反对这种设计。

**批判 3:本体未经验证就硬化。** 6 种边 + 严格类型约束 + "语义边只连同层"全部来自先验推演。gpt-concept分析.md 的警告直接适用:"不要急着设计庞大 Ontology,会失败"。且"同层才连边"与现实矛盾——System 级决策约束 Component 级组件是最常见、最有查询价值的关系;设计文档自己的 Mermaid 示例(`单人自托管 → motivates → 5层同步门控`)也无法自洽地说明两个决策"同层"。

**批判 4:价值验证顺序颠倒。** 四种知识发现(影响发现、决策溯源、同模式发现、盲区发现)是图谱的全部价值假设,却被排在实施路径 Phase 5——最后验证。若走完 Phase 1-4 才发现"图遍历不比 LLM 直接读 dimension 页好",前四个 Phase 全部沉没。

### 2.3 成熟部分

设计文档第九节(Obsidian 定位:叙事浏览器而非图谱可视化器)是全文最成熟的部分:wikilink 降级为导航、Mermaid 局部子图嵌入维度页、查询输出叙事化——低成本高价值,本方案照单全收并扩展(见建议 6)。

---

## 三、现存 Entity 质量审计

优化方案不能默认现存 entity 质量合格——逐页审计 17 个 entity 后,问题分四类:

| 问题 | 实例 | 危害 |
|------|------|------|
| 抽象层级混杂 | `插件系统` 与 `单例模式`/`指数退避`/`懒加载` 同标"架构模式" | 实现技法对架构师零信息量;正是设计文档诊断的扁平化,但根因是准入标准缺失而非 wikilink 机制 |
| 教科书概念无区分度 | `分层架构`、`优雅降级`、`故障隔离` | 任何非玩具仓库都"有",实例列表随仓库数线性膨胀成超级 hub,汇合结论是废话 |
| 工具名当概念 | `Vitest`、`并行 CI`、`TypeScript monorepo` | package.json 一眼可见的事实,不是需要 LLM 沉淀的知识 |
| 单实例概念过多 | 17 个中 9 个仅 1 个 repo 实例 | Concept 的意义是跨仓库汇合锚点,单实例暂时只是开销 |

**合格的约 6 个**:`插件系统`、`Context 压缩`、`Prompt Caching`、`并行工具执行`、`契约测试`、`性能预算`。共同特征:双仓库实例 + 实例间有可行动差异 + 直接对应受众问题。合格率约 1/3。

**根因**:`schema/CLAUDE.md` 现行规则("凡属架构模式/技术栈/领域概念的词汇,首次出现时标记")只有召回导向、没有精度门槛——标注永远是"安全"动作,滥标无惩罚。06-10 spec 的三层边界只挡住类名/函数名,挡不住"正确类别里的低价值成员"。

---

## 四、优化方案

### 建议 1:保留四类节点,用「节点页 frontmatter + 结构化区块」承载,不建独立 graph.yaml

**保留**:Component / ExtensionPoint / DesignDecision / Concept 四分类。它优于 gpt-concept分析.md 的通用四类(Concept/Decision/Mechanism/Artifact),因为 ExtensionPoint↔二开者、DesignDecision↔架构师是与 spec 目标用户的一比一映射,通用分类丢失了受众绑定。

**改变**:节点不存 graph.yaml,而是成为 wiki 页面:

```
wiki/repos/openclaw/
  dimensions/*.md              # 叙事页,现状不变
  nodes/
    channel-plugin.md          # ExtensionPoint 节点
    tool-policy.md             # Component 节点
    sync-gating-decision.md    # DesignDecision 节点
```

节点页模板:

```yaml
---
node_type: ExtensionPoint            # Component | ExtensionPoint | DesignDecision
scope: subsystem                     # system | subsystem | component(见建议 2)
concept: 插件系统                     # embodies 边 → wiki/entities/
targets: [tool-policy]               # targets 边 → 同 repo nodes/
motivated_by: [sync-gating-decision] # motivates 边的反向记录
sources:
  - src/channels/plugins/types.plugin.ts:53-94
---

# ChannelPlugin

人话描述:这是什么、怎么用、二开从哪切入。
^[src/channels/plugins/types.plugin.ts:53-94]
```

**理由**:
- 每个节点同时是图谱数据(脚本读 frontmatter 即得边表)和 wiki 页面(Obsidian 可读可点,Dataview 可查询)。图谱对人可审阅、可纠错——直接缓解 spec 已知风险"LLM 提取质量不稳定";
- 解决设计文档未回答的同步问题:dimension 页**引用**节点页(`[[openclaw/nodes/channel-plugin]]`),叙事与节点是链接关系而非复制关系;
- 是 karpathy 模式的延续("entity pages, concept pages" 本是 llm-wiki 原生构件),只是给代码场景加上类型化 frontmatter——收紧约定,不更换架构。

**与现存结构的关系**:`wiki/entities/`(分诊后)即 Concept 节点层(跨仓库),`nodes/` 是 repo 内实例层。"Concept 是类型、Component/ExtensionPoint 是实例"这一设计文档的关键区分,用目录结构而非双 yaml 表达。

### 建议 2:Type × Scope 二维替代 L1-L4 单轴

L1-L4 金字塔把抽象程度、归一化可行性、连边合法性压进一根轴,导致"同层才连边"的别扭规则和无查询价值的层级判定成本。改为两个正交字段:

- **`node_type` 管边的合法性**:embodies 只能从实例节点指向 Concept,motivates 只能从 DesignDecision 出发。lint 可程序化校验;
- **`scope` 只管展示与排序**(system | subsystem | component):compare 矩阵和影响分析按 scope 排序输出,**不参与连边合法性判断**——砍掉跨层禁连规则。词表只留三值,Feature/Implementation 级按 06-10 spec 本就不入图。

**归一化可行性不再需要独立轴表达**:`concept:` 字段填没填,本身就是归一化状态。可比性是归一化的**结果**,不是节点的先验属性。

### 建议 3:边从 6 种砍到 3 种起步

| 边 | 承载 | 入选理由 |
|---|------|---------|
| `embodies`(实例 → Concept) | `concept:` 字段 | 跨仓库对比的唯一桥梁;提取成本低 |
| `targets`(ExtensionPoint → Component) | `targets:` 字段 | "改这个 hook 波及哪个子系统"——二开者最高频问题;可从代码结构提取 |
| `motivates`(DesignDecision → 节点) | `motivated_by:` 字段 | "为什么存在"——架构师核心问题;无它则 DesignDecision 是孤岛 |

**砍掉**:
- `realizes`:与 embodies 语义重叠,合并为统一的 `concept:` 字段,类型差异由 node_type 表达;
- `constrains`:先用 motivates 决策页的描述文本覆盖(带 provenance),独立成边待"影响发现"查询验证后再评估;
- `alternative_to`:提取难度最高且多数仓库无 ADR 可挖,遇到有完整 ADR 的仓库再加。

**演进纪律复用维度表成功经验**:边 schema 写进 `schema/graph-schema.md`,前 20 仓库只增不改,新边类型须由真实查询需求驱动。

### 建议 4:归一化用「概念索引 + LLM 终判」替代五阶段管线

新增 `wiki/entities/_index.md` 作为归一化唯一锚点:

```markdown
# Concept Index

| Concept | 别名/曾用名 | 一句话定义 | 实例数 |
|---------|------------|-----------|--------|
| 插件系统 | Plugin System, 扩展注册机制 | 注册 API 或 manifest 解耦核心与扩展 | 3 |
| Context 压缩 | Context Compression, compact | 上下文超限时的有损压缩策略 | 2 |
```

归一化流程(ingest 的一个步骤):

```
新节点产出后:
1. LLM 读 _index.md 全文(<20 仓库时预计 50-100 行)
2. 匹配既有 Concept(含别名)→ 经准入三问(见 4.8)→ 填 concept: 字段,必要时补别名
   无匹配 → 节点页标 concept_candidate: <名>,攒批
3. 人工确认候选批 → 过准入三问 → 新 Concept 入索引
   → 反向轻量回溯:"存量 repo 有没有类似节点?"(LLM 基于已有节点页直接回答)
```

**理由**:
- 五阶段管线解决规模问题,本项目瓶颈是本体问题。Blocking/embedding 的价值在 O(n×m) 不可承受时才显现;
- 这正是 karpathy 原始配方("LLM reads the index first... works surprisingly well at moderate scale, avoids embedding-based RAG infrastructure")应用于归一化;
- **别名列是零基础设施的归一化机制**,且别名本身是知识("这个概念在不同社区叫什么");
- matchers.yaml 是过早固化——签名规则应是归一化经验的沉淀产物,不是起点(设计文档方向 D 自认 Concept signature 会随新仓库演进);
- 方向 D(Concept 拆分/合并)保留为**人工触发的 maintenance pass**:`/lint` 在某 Concept 实例数 ≥5 且定义含糊时提示,人发起、LLM 执行,无需 cron。

**退路**:五阶段管线保留为 50+ 仓库扩展预案。触发条件:概念索引超 ~300 行或归一化错误率明显上升。届时迁移零成本——锚点与数据格式不变,只加预筛层。

### 建议 5:图谱数据派生而非存储

**规则**:叙事页 + 节点页 frontmatter 是唯一事实源;任何图谱 yaml/json 必须由脚本生成。

```
scripts/graph.py build      # 扫 frontmatter → wiki/graph/graph.json(派生物)
scripts/graph.py query --impact tool-policy    # 影响发现遍历
scripts/graph.py mermaid openclaw architecture # 生成维度页局部子图
scripts/lint.py             # 新增:边类型合法性 / targets 悬空 / concept 未注册
```

双写漂移问题从机制上消除:frontmatter 错了改 frontmatter,graph.json 重新 build。与项目既有反双写哲学(无 status 字段)一致。Mermaid 块是唯一允许嵌入页面的派生物(Obsidian 原生渲染需要),带 `<!-- generated -->` 标记,lint 校验其与 graph.json 一致性。

### 建议 6:Obsidian 三界面照单全收,增加第四界面

设计文档第九节全盘接受:① dimension 页 wikilink 降级为导航;② Mermaid 局部子图嵌入维度页(`## 决策链` 区块,由 graph.py 派生);③ `/query` 输出为带 provenance 的遍历路径叙事。

**新增界面 ④ 节点详情页**:用户在 Mermaid 图看到 `ChannelPlugin`,可经 `[[openclaw/nodes/channel-plugin]]` 跳到定义、来源行号、关联决策。原设计中此跳转无处可去(graph.yaml 不可打开)。

### 建议 7:落地排序——价值验证前置

| 步骤 | 内容 | 退出标准 |
|------|------|---------|
| **Step 0**(半天) | 手工为 openclaw 写 5-8 个节点页,对比"只给 dimension 页"vs"加节点页"回答"改 ToolPolicy 波及什么"的质量 | 若节点页无明显增益,**整个图谱方向重新评估**——半天买到最重要的信息 |
| **Step 1**(1-2 天) | `schema/graph-schema.md`(3 节点 + 3 边 + scope 词表 + 准入三问 + 节点页模板);**存量 entity 分诊 pass**(见 4.9);`_index.md` 从分诊幸存者初始化;lint 新增 3 规则 | schema 可执行,索引干净 |
| **Step 2**(2-3 天) | `/analyze` 增加节点抽取子步骤;openclaw / hermes-agent 回填 pass(从现有 dimension 页提取,不重读源码) | 2 仓库节点页齐备 |
| **Step 3**(1-2 天) | graph.py 三子命令;`/query` 增加图遍历分支(涉及"影响/为什么/哪些仓库也这样"时走 graph.py,否则走原检索升级链) | 四类受众问题可走图回答 |
| **Step 4**(持续) | 每 ingest 新仓库跑归一化;第 5 个仓库后回顾:边类型够否、Concept 需否拆分、embedding 到触发条件否 | — |

对照原 Phase:Phase 1≈Step 1,Phase 2≈Step 2,Phase 5 提前融入 Step 3,Phase 3 缩减为建议 4 轻量流程,Phase 4 的周期重规范化与反向扫描降级为人工触发。

### 4.8 Concept 准入三问(写入 graph-schema.md,提取与归一化强制执行)

候选概念须**同时通过**三问才能入 `_index.md`:

| # | 测试 | 通过示例 | 拒绝示例 |
|---|------|---------|---------|
| 1 | **问题测试**:直接回答某个二开/架构师问题吗? | `插件系统` →"这框架怎么二开" | `单例模式` → 不对应任何选型/二开问题 |
| 2 | **判别测试**:在此锚点上跨仓库汇合,能得出有差异的结论吗? | `Context 压缩` → 阈值/策略/失败处理各家不同 | `分层架构` → 谁都有,汇合无信息量 |
| 3 | **沉淀测试**:其知识需读代码才能获得吗? | `契约测试` → 须读 test infra 才能发现 | `Vitest` → package.json 即得 |

配套机制:
- ingest 时 LLM 只能标 **candidate**,正式入索引须过三问——"标注"与"准入"拆为两个动作,门槛设在归一化步骤;
- 实现技法类词汇(单例、懒加载、退避)在叙事中保留为普通文本,不入概念体系;
- lint 规则 `check_missing_entity_links`(催促多标)与准入门槛(控制滥标)方向相互打架,改为检查 `concept_candidate` 积压数量。

### 4.9 存量 17 entity 分诊表(Step 1 执行)

| 处置 | 对象 | 动作 |
|------|------|------|
| **保留为 Concept** | 插件系统、Context 压缩、Prompt Caching、并行工具执行、契约测试、性能预算(+ 行为驱动测试待议) | 入 `_index.md`,补别名列 |
| **重新概念化** | OpenTelemetry → `可观测性集成`;并行 CI → 并入 `测试基础设施` 类锚点(待议) | 改名重写定义,原名进别名列 |
| **降级出局** | 单例模式、懒加载、指数退避、Vitest、TypeScript monorepo | 删除 entity 页,叙事 wikilink 改回纯文本 |
| **观察名单** | 分层架构、优雅降级、故障隔离 | 暂不入索引;第 3-5 个仓库出现有判别力的变体差异时再准入 |

此 pass 同时是准入三问的首次实战校准——若三问对 17 个的裁决与直觉不符,先修标准再前进。

**预期**:分诊后索引仅 6-8 个 Concept,"图谱很小"是健康状态(参照 Wikontic:图小 20 倍、信息保留 86%)。概念体系的价值密度比节点数量重要——归一化锚点被污染的代价是后续所有仓库的归一化跟着歪。

---

## 五、对设计文档各章节的处置总表

| 设计文档章节 | 处置 | 对应建议 |
|---|---|---|
| §1 问题诊断 | **全盘接受** | — |
| §2 四类节点 | 接受分类;否决 L1-L4 单轴,改 Type × Scope | 1, 2 |
| §3 六种边 | 砍到 3 种起步,类型约束保留但简化 | 3 |
| §4 三层图谱架构 | 否决双 yaml 存储,改节点页 + 派生 | 1, 5 |
| §5 双路并行产出 | 接受理念,同源性由 frontmatter 机制保证 | 1, 5 |
| §6 五阶段归一化 | 降级为概念索引 + LLM 终判;原方案留作 50+ 仓库预案 | 4 |
| §7 四个增量方向 | A 简化、B 保留(接 delta.py)、C/D 降级为人工触发 | 4 |
| §8 与现有方案对比 | 参照系保留,定位修正:本项目对标的是"中等规模策展型知识库",非工业 KG | — |
| §9 Obsidian 定位 | **全盘接受** + 新增节点详情页界面 | 6 |
| §10 实施路径 | 重排:价值验证前置(Step 0) | 7 |
| §11 设计原则 | 原则 1/2/5 保留;原则 3(同层连边)废除;原则 4(blocking)降级为远期预案 | 2, 4 |

---

## 六、核心理念

设计文档诊断对、消费界面对,但把"图谱"理解成了需要独立存储和工业管线的数据库。本方案把图谱重新理解为**带类型约束的 wiki 页面网络**——结构化程度足以支撑程序遍历(frontmatter 即边表),形态上仍是 karpathy 模式的 markdown wiki,维护成本仍然近零。

配合 Concept 准入三问与存量分诊,确保图谱从第一天起就建在被策展过的本体之上:**先有合格的锚点,再有归一化;先验证查询价值,再扩建基础设施。**

# Codebase-Wiki 全面分析

> 分析日期：2026-06-13 | 当前覆盖仓库：openclaw、hermes-agent | 分支：feat/graph-wikilinks

## 一、项目定位

codebase-wiki 是一个**代码仓库知识提取与结构化 wiki 系统**，目标是将代码仓库的隐性架构知识转化为可查询、可对比、可遍历的结构化知识库。核心理念是：**维度页给人读，图谱节点给程序遍历，两者同源但分路产出。**

目前已覆盖 2 个仓库（OpenClaw、Hermes Agent），均归类为 `ai-agent-frameworks`。

---

## 二、目录结构

```
codebase-wiki/
├── schema/                     # 知识提取的 Schema 定义
│   ├── CLAUDE.md               # LLM 操作规范（wikilink 规则、页面元数据、维护文件管理）
│   ├── dimensions.md           # 5 维度的提取指南
│   └── graph-schema.md         # 图谱节点/边类型定义、准入规则、scope 定义
├── scripts/                    # 核心 Python 工具链
│   ├── delta.py                # 文件变更检测（SHA256 差分）
│   ├── manifest.py             # 摄取状态管理（.manifest.json + per-repo .hashes.json）
│   ├── graph.py                # 知识图谱构建、查询、Mermaid 生成、wikilink 更新
│   ├── lint.py                 # 11 条 wiki 健康检查规则
│   └── eval.py                 # 质量评分（覆盖率/溯源率/新鲜度）
├── skills/                     # Claude Code slash command 定义
│   ├── code-ingest/SKILL.md    # /analyze — 代码仓库摄取
│   ├── code-query/SKILL.md     # /query — 知识查询（含图遍历）
│   ├── code-compare/SKILL.md   # /compare — 跨仓库对比
│   └── code-lint/SKILL.md      # /lint — wiki 健康检查
├── wiki/                       # Obsidian vault（知识库内容）
│   ├── repos/<repo>/
│   │   ├── <repo>-overview.md                 # 概览页
│   │   ├── dimensions/<repo>-<dim>.md         # 5 个维度叙事页
│   │   ├── nodes/
│   │   │   ├── components/<repo>-<slug>.md    # Component 节点
│   │   │   ├── extension-points/<repo>-<slug>.md  # ExtensionPoint 节点
│   │   │   └── design-decisions/<repo>-<slug>.md  # DesignDecision 节点
│   │   └── .hashes.json                       # 文件哈希（增量检测用）
│   ├── entities/               # 跨仓库 Concept 定义
│   │   ├── _index.md           # Concept 索引表（准入三问筛选后的归一化锚点）
│   │   └── *.md                # 各 Concept 定义页
│   ├── views/                  # 对比视图
│   │   └── categories/<category>.md
│   ├── graph/graph.json        # 程序化图谱数据
│   ├── index.md                # 总索引
│   ├── log.md                  # 操作日志
│   └── hot.md                  # 当前活跃状态
├── tests/                      # Pytest 测试（5 个文件覆盖核心逻辑）
├── docs/                       # 设计文档
│   └── codebase-knowledge-graph-design.md  # 图谱设计全文
└── .manifest.json              # 全局清单（repo 列表、分类、版本号）
```

---

## 三、知识提取流程（/analyze）

### 3.1 核心管线

```
源码仓库 → delta.py(文件变更) → 5维度叙事提取 → 节点提取(3.5步) → 图谱构建 → wikilink更新
```

### 3.2 各步骤详解

**Step 1 — delta.py 文件分类**
- 扫描仓库全部文件，跳过 `node_modules`、`.git`、`dist` 等已知噪声目录
- 支持 `.codebase-wikiignore` 自定义排除
- 按三层分类：`core`（README、入口文件）、`config`（package.json、CI 配置）、`impl`（源码）
- 用 SHA256 做增量检测，跳过 >1MB 的二进制文件

**Step 2 — 初始理解**
- 读取所有 `core` 层文件，形成仓库的全局心智模型

**Step 3 — 五维度叙事提取**
- 按 `schema/dimensions.md` 的 5 个固定维度逐个分析：
  1. **Architecture** — 核心抽象、数据流方向、关注分离
  2. **Extension Points** — 插件系统、hooks、注册机制、接口契约
  3. **Performance Tradeoffs** — 优化了什么、牺牲了什么、为什么
  4. **Dependency Strategy** — 外部依赖态度、核心依赖可替换性
  5. **Testing Philosophy** — 测试金字塔、行为 vs 实现、CI 策略
- 每条事实声明必须带 provenance：`^[文件路径:行号-行号]`
- 用户逐维度确认后才写入

**Step 3.5 — 节点提取（图层面）**
- 两阶段分离：提取（宽松）→ 验证（严格）
- 节点类型：`Component`（可定位结构单元）、`ExtensionPoint`（二开入口）、`DesignDecision`（因果链决策）
- 三项验证：连通性测试（必须有边）、受众问题测试（必须能回答具体问题）、去重测试（不能是其他节点的属性）
- Scope 赋值（爆炸半径测试）：`system` / `subsystem` / `component`
- 自动匹配已有 Concept 或标记 `concept_candidate`

**Step 4-6 — 收尾**
- 写 overview.md、更新 manifest、更新 index/log/hot

### 3.3 知识提取的设计特点

| 特性 | 实现 |
|------|------|
| **增量更新** | delta.py 的 SHA256 哈希对比 + per-repo `.hashes.json` |
| **Provenance** | 每条声明必须标注 `^[文件:行号]`，lint 检测遗漏 |
| **版本管理** | manifest 全局 `dimensions_version` 追踪 schema 演进，自动标记过期页面 |
| **分类体系** | manifest 的 `categories` 字段按领域分组仓库 |
| **质量门控** | 用户逐维度确认后才写入，lint 自动检测 11 条规则 |

---

## 四、图谱设计

### 4.1 三层架构

```
L3: Shared Graph（跨仓库归一化）
    概念节点(Concept) + embodies/realizes 跨仓库边
    ↓
L2: Repo Graph（单仓库内部图）
    三类型节点(Component/ExtensionPoint/DesignDecision)
    + 内部边(targets/motivates/constrains/alternative_to)
    ↓
L1: Dimension 页（人类叙事）
    自由文本、wikilink 交叉引用、内嵌 Mermaid 子图
```

### 4.2 节点类型

| 节点类型 | 含义 | 提取方式 | 受众问题 |
|---------|------|---------|---------|
| **Component** | 系统中可定位的结构单元 | 程序化（目录/类/import） | 改这里会波及什么？ |
| **ExtensionPoint** | 二开可操作的定制入口 | 中自动化（接口+多实现/register*/hook） | 这里怎么扩展？ |
| **DesignDecision** | 明确因果链的架构选择 | LLM 推理（文档/注释/commit 中的"选X不选Y因为Z"） | 为什么这样设计？ |
| **Concept** | 跨仓库通用模式/范式 | 归一化流程（embodies 边的汇集点） | 不同仓库同一问题怎么做？ |

### 4.3 边类型（起步集）

| 边 | 方向 | 语义 | 数据来源 | 当前状态 |
|----|------|------|---------|---------|
| **embodies** | 实例 → Concept | 此节点是概念的实例化 | frontmatter `concept:` | ✅ 已实现 |
| **targets** | ExtPoint → Component | 此扩展点作用于该组件 | frontmatter `targets:` | ✅ 已实现 |
| **motivates** | DesignDecision → 节点 | 此决策催生了该节点 | frontmatter `motivated_by:` | ✅ 已实现 |
| constrains | DesignDecision → Component | 此决策限制了组件行为 | — | 待引入 |
| alternative_to | DesignDecision ↔ DesignDecision | 同一问题的备选方案 | — | 待引入 |

### 4.4 图的程序化实现（graph.py）

`graph.py` 是整个图谱系统的核心引擎，四个功能：

1. **`build`** — 扫描所有 `nodes/` 目录的 frontmatter，构建 `{nodes, edges}` 结构并写入 `graph.json`
2. **`query --impact`** — 图遍历查询，找到与指定节点直接关联的所有节点
3. **`mermaid`** — 生成 Mermaid LR 图，支持指定中心节点和跳数（hops），内嵌到 overview.md
4. **`--update-wikilinks`** — 自动生成三类 generated section：
   - 节点页 `## 关联`（按边类型分组的 wikilink 网络，附中文关系标签）
   - 维度页 `**本维度提取的节点：**`（反向链接，来源为 `extracted_from` 字段）
   - Overview 页 `## 决策链`（Mermaid 图）

### 4.5 Concept 归一化机制

**准入三问**（`graph-schema.md`）：
1. **问题测试** — 直接回答某个二开/架构师问题？
2. **判别测试** — 跨仓库汇合能得出有差异的结论？还是任何仓库都"有"？
3. **沉淀测试** — 知识需读代码才能获得？还是 README 一眼可见？

当前已注册的 Concept：**插件系统**、**Context 压缩**、**人机审批协议**、**可替换记忆后端**（4个）。

**两层候选机制**：
- `concept_candidate` — 节点 frontmatter 标记，待归一化 pass 后升级（当前积压：任务编排、无消息主动触发、声明式行为定制）
- 观察名单 — 候选未通过判别测试的（"任何仓库都有"，如分层架构、优雅降级）

---

## 五、代码实现分析

### 5.1 核心脚本（~1400 行 Python）

| 脚本 | 行数 | 职责 | 关键设计决策 |
|------|------|------|-------------|
| `delta.py` | 226 | 文件变更检测 + 层级分类 | SHA256 哈希、3 层分类器、`.codebase-wikiignore` 支持 |
| `manifest.py` | 172 | 摄取状态管理 | `HashStore` 分离 per-repo 哈希、`ManifestManager` 管理全局清单 |
| `graph.py` | 434 | 图谱构建/查询/渲染 | 前端 matter 解析器支持行内列表+块列表两种语法、边分组逻辑、idempotent 更新 |
| `lint.py` | 440 | 11 条健康检查 | 3 级 severity（ERROR/WARN/INFO）、wikilink 路径解析双策略 |
| `eval.py` | 131 | 质量评分 | 覆盖/溯源/新鲜度三个维度的量化评分 |

### 5.2 Frontmatter 解析

`graph.py` 和 `lint.py` 中有两套独立的 frontmatter 解析器，均支持：
- 标量值：`key: value`
- 行内列表：`key: [a, b, c]`
- 块列表：`key:\n  - a\n  - b`

### 5.3 Wikilink 路径解析约定

- 以 `views/` 或 `insights/` 开头的链接从 `wiki/` 根目录解析
- 其余链接从 `wiki/repos/` 解析
- 不区分大小写，目标文件不带 `.md` 后缀

### 5.4 测试覆盖

5 个测试文件覆盖核心功能：
- `test_graph.py` — 图谱构建、边类型、查询、Mermaid、wikilink 更新、幂等性（10 个测试）
- `test_delta.py` — 文件分类逻辑
- `test_manifest.py` — 清单管理
- `test_lint.py` — 规则检查
- `test_eval.py` — 质量评分

---

## 六、质量保障体系

### 6.1 Lint 规则（11 条）

| # | 规则 | 级别 | 检查内容 |
|---|------|------|---------|
| 1 | `check_broken_wikilinks` | ERROR | wikilink 目标文件不存在 |
| 2 | `check_stale_dimensions` | ERROR | 页面版本与 manifest 全局版本不一致 |
| 3 | `check_graph_edge_types` | ERROR | 边类型约束违规（非 ExtensionPoint 有 targets；DesignDecision 有 concept） |
| 4 | `check_graph_dangling_edges` | ERROR | targets/motivated_by 指向不存在的节点 |
| 5 | `check_concept_registered` | ERROR | concept 字段值不在 `entities/_index.md` 中 |
| 6 | `check_orphan_pages` | WARN | 页面未被任何其他页面引用 |
| 7 | `check_missing_provenance` | WARN | 维度页无 provenance 引用 |
| 8 | `check_empty_pending` | WARN | pending 维度超过 30 天未处理 |
| 9 | `check_candidate_backlog` | WARN | concept_candidate 积压 ≥ 3 个 |
| 10 | `check_missing_category` | INFO | repo 未分配分类 |
| 11 | `check_views_freshness` | INFO | 对比视图的源页面有更新 |

### 6.2 Eval 评分（3 维）

- **Coverage**（覆盖率）：已完成维度的比例均值
- **Provenance**（溯源率）：维度页中有 provenance 标注的比例
- **Freshness**（新鲜度）：非过期页面的比例

---

## 七、设计亮点

1. **叙事与图谱分离**。Dimension 页是给人读的 markdown，图谱节点是给程序遍历的 frontmatter 结构化数据。两者同源（都从代码仓库提取）但不同产出。避免了"把结构化图谱数据溶解在自由文本中"的根本问题。

2. **Concept 作为跨仓库锚点**。两个 repo 的同类节点不直接连接，而是通过共同指向的 Concept 节点间接关联。这保持了 repo 图的独立性，同时实现了跨仓库的可比性。

3. **Blocking 优先的归一化策略**。节点类型 + 层级是免费的 blocking key，把实体链接的复杂度从 O(n×m) 降到常数级。

4. **两步分离的节点验证**。提取宽松（不遗漏候选），验证收紧（连通性+受众问题+去重三项测试）。只有通过验证的候选才成为正式节点。

5. **Generated Section 的 idempotent 更新**。`graph.py --update-wikilinks` 通过标记块（`<!-- generated-wikilinks -->`）实现可重复运行的 wikilink 更新，不破坏手写内容。

6. **Obsidian 定位为叙事浏览器**。Obsidian 负责三个消费界面（叙事页阅读、Mermaid 决策链渲染、wikilink 导航），而图谱的遍历和推理由 `graph.py` 程序化完成。

---

## 八、当前局限与未完成部分

对照 `docs/design/codebase-knowledge-graph-design.md` 的设计蓝图，进度如下：

| 设计组件 | 当前状态 |
|---------|---------|
| L1 Dimension 页 | ✅ 已实现 |
| L2 Repo Graph (graph.json) | ✅ 已实现 |
| 3 种边（embodies/targets/motivates） | ✅ 已实现 |
| Mermaid 决策链嵌入 | ✅ 已实现（内嵌于 overview + 维度页） |
| Wikilink 自动更新 | ✅ 已实现 |
| L3 Shared Graph 独立文件层 | ❌ Concept 目前只在 `entities/_index.md`，无独立 `concepts.yaml` |
| constrains / alternative_to 边 | ❌ 待引入 |
| 规则匹配器（matchers.yaml） | ❌ 未实现 |
| Embedding 索引 + ANN 检索 | ❌ 未实现 |
| 归一化漏斗（规则→Embedding→LLM 三级） | ❌ 未实现 |
| 周期批量重规范化 | ❌ 未实现 |
| `/query` 图遍历 | ⚠️ 基础实现（`--impact`），未集成归一化 |
| Delta → 边失效检测 | ❌ 未实现 |
| 新 Concept 回溯存量 repo | ❌ 未实现 |

**当前阶段**：Phase 2（单 repo 图谱产出）已完成，Phase 3（跨 repo 归一化自动化）尚未启动。

---

## 九、数据规模快照（截至 2026-06-13）

| 指标 | 数值 |
|------|------|
| 覆盖仓库 | 2（openclaw、hermes-agent） |
| 维度页 | 10（每 repo 5 维度） |
| 图谱节点 | 27（openclaw: 17, hermes-agent: 10） |
| 图谱边 | 25（embodies: 10, targets: 10, motivates: 5） |
| 已注册 Concept | 4 |
| 候选积压 | 3 |
| 对比视图 | 1（ai-agent-frameworks） |
| Lint 规则 | 11 |
| 测试用例 | 约 20+ |
| 核心代码量 | ~1400 行 Python + ~300 行 SKILL.md |

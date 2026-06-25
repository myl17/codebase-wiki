# /ingest — Code Repository Ingest

从源码仓库提取结构知识，逐步演化进 wiki。

## Trigger

```
/ingest <repo-path> [<repo-name>] [--verify] [--full]
```

- `<repo-path>`：源码目录（只读）
- `<repo-name>`：wiki 中的标识符，默认取 `<repo-path>` 的最后一段目录名
- `--verify`：开启 Step 5 独立验证（默认关闭）
- `--full`：强制全量重新提取（跳过增量检测）

When the user asks to analyze, ingest, or add a code repository to the wiki.

### 多仓库并行

当用户一次指定多个仓库时：

```
Step 1+2 并行（每个仓库独立 agent，同时进行）
  agent-1: repo-A → Entity 提取 → 问题空间映射
  agent-2: repo-B → Entity 提取 → 问题空间映射
  agent-3: repo-C → Entity 提取 → 问题空间映射

全部完成后汇总：

Step 3  问题空间匹配（需要多仓库信息，统一处理）
  → 所有仓库的 problem-map + 已有种子库 + 已有 Concept 页
  → 产出候选清单（此时才有跨仓库对比数据，才有 A/B/D 类）

Step 4-6 继续
```

**并行 vs 串行的分界线：是否需要跨仓库信息。**
- Entity 提取（Step 1）：只看单仓库源码 → 可并行
- 问题空间映射（Step 2）：只看单仓库 entity 页 → 可并行
- 问题空间匹配（Step 3）：需要对比其他仓库 → 必须等全部完成

### Re-ingest（增量更新）

对已 ingest 过的仓库再次运行。增量检测不是优化——没有它，每次 re-ingest 都要全量重读 500 个仓库的源码，token 成本不可接受。

#### `.ingest-state.json` 格式

存放在 wiki 项目内：`wiki/repos/<name>/.ingest-state.json`（与 `entities/`、`overview.md` 同级，不污染源码仓库）。

```json
{
  "repo": "<name>",
  "source_path": "<源码目录绝对路径>",
  "last_ingest": "<ISO 8601 timestamp>",
  "files": {
    "<repo-relative-path>": "<SHA-256 hex>",
    ...
  },
  "entity_map": {
    "<entity-slug>": ["<file-path>", ...]
  }
}
```

- `source_path`：源码目录路径。如果用户移动了仓库位置，路径变了也算"需要重新检测"。
- `files`：所有被 ingest 读取过的源码文件的 SHA-256 哈希。不是仓库全部文件——只记录 Step 1 实际读了哪些。
- `entity_map`：每个 entity 依赖哪些源码文件。变更检测时用来做逆向映射：文件变了 → 哪些 entity 受影响。

#### Step 0 — 增量检测

```
你的任务是对 <仓库名> 做增量检测，确定哪些内容需要重新提取。

## 输入

- 源码目录：<源码路径>
- 上次 ingest 快照：wiki/repos/<仓库名>/.ingest-state.json

## 检测逻辑

1. 如果 wiki/repos/<仓库名>/.ingest-state.json 不存在：
   → 报告"首次 ingest"，触发全量管线（Step 1-6）

2. 读取 .ingest-state.json，比较 source_path：
   - 如果 source_path 与当前源码目录不同 → 路径已移动，触发全量 re-ingest
   - 相同 → 继续

3. 提取 files 字典，对每个路径计算当前文件内容的 SHA-256，与快照值比对
4. 记录变更文件列表

5. 如果无变更：
   → 报告"无变更"，结束。不执行后续步骤。

6. 如果新增了上次快照中不存在的文件（仓库新增了文件）：
   → 读这些新文件，判断是否包含新的独立模块（entity）
   → 如果有，也标记为受影响的 entity

7. 根据变更文件列表 + entity_map 做逆向映射：
   → 每个 entity 依赖的文件是否在变更列表中？
   → 是：该 entity 标记为"受影响"，需要重新提取

8. 输出：
   - 变更文件：<N> 个
   - 受影响 entity：<列表>
   - 新增 entity 候选：<列表>（如有）
```

#### Step 1（增量模式）

只重新提取受影响的 entity + 新增 entity 候选。未受影响的 entity 页保留不动。

overview.md 始终刷新——entity 列表可能变了（新增/删除），tags 描述可能过时。

#### 快照更新

Step 6 收尾时，用本次 ingest 实际读取的文件列表和 SHA-256 覆写 `.ingest-state.json`。

---

## 管线总览

```
Step 1  Entity 提取
        输入：源码目录
        输出：wiki/repos/<name>/entities/<slug>.md（每个 Entity 一文件）
              wiki/repos/<name>/overview.md

Step 2  Entity 问题空间映射
        输入：Entity 页 + 按需读源码
        输出：seeds/<name>-problem-map.md

★ 暂停点 1（用户确认问题空间列表完整性）

Step 3  问题空间匹配
        输入：problem-map + 种子库 + 已有 Concept 页
        输出：seeds/<name>-candidates.md
              docs/evolve-signals/<date>-<name>.md（D 类信号）

★ 暂停点 2（用户确认候选清单 + 能力域覆盖表）

Step 4  Concept 写作（per-Concept 独立 agent）
        输入：candidates.md 中 A/B 类条目
        输出：wiki/concepts/<slug>.md（新建或追加）

Step 5  [可选，--verify] 独立验证 + 修复
        输入：Step 4 产物
        输出：验证报告 → 修复后的 Concept 页

Step 6  种子库更新 + 演化报告落地
        输入：problem-map + candidates.md
        输出：seeds/master.md 更新
              wiki/log.md + wiki/hot.md 更新

★ 暂停点 3（用户看 ingest 总结，决定是否触发 /evolve-apply）
```

暂停点之外，LLM 自主执行。

---

## Step 1：Entity 提取

运行以下提示词：

```
你的任务是从 <仓库名> 源码中提取所有 Structural Entity。

## 输入源

源码目录：<源码路径>
唯一信息来源，不使用训练数据中的先验知识。

## 工作方式

自己决定读哪些文件。广泛探索直到全面理解仓库结构。
判断标准：一个模块是否有独立的职责边界、对外接口、可以被单独理解和替换？

## 每个 Entity 输出为独立文件

路径：wiki/repos/<仓库名>/entities/<slug>.md

格式：

---
type: entity
repo: <仓库名>
slug: <slug>
problem: <问题层一句话，"如何..."形式>
generated: <YYYY-MM-DD>
source_files:
  - <repo-relative-path>
---

# <Entity 名称>

**代码位置**：<目录/包路径>
**这个模块解决什么问题**：
- 实现层：<这个仓库的具体做法，一句话>
- 问题层：<同 frontmatter problem 字段，"如何..."形式>
**对外暴露什么**：<关键类/函数/接口，含文件路径:行号>
**它和谁交互**：
- 依赖 [[entities/<slug>]]（<一句说明>）
- 被 [[entities/<slug>]] 调用（<一句说明>）
（同仓库 entity wikilink；外部库用纯文本）
**为什么它是可分离的**：<独立目录？独立接口？独立包？>

**关键机制**（源码可见）：
- <机制 1>：<描述> ^[文件路径:行号]
- <机制 2>：...

**源码证据**：
- 入口文件：<路径>
- 核心类型/接口定义：<路径:行号>

## 额外输出：仓库总览

路径：wiki/repos/<仓库名>/overview.md

内容：
- 这个仓库是什么（一段落）
- 核心子系统列表，**每项用 wikilink**：`- [[repos/<仓库名>/entities/<slug>]]`
- 明确不做什么

## 核心约束

1. 每条事实声明必须有 ^[文件路径:行号]
2. 每个 Entity 独立文件，不合并
3. 广泛探索，不遗漏独立目录或独立包
```

---

## Step 2：Entity 问题空间映射

运行以下提示词：

```
你的任务是把 <仓库名> 的所有 Entity 页翻译成问题空间条目。

## 你在为谁翻译

Framework Builder——正在研究一类框架设计空间的人，
需要知道：这个问题是构建同类框架时都必须回答的吗？
这个仓库在这个问题上做了什么选择？

## 输入

- Entity 页：wiki/repos/<仓库名>/entities/*.md
- 源码目录：<源码路径>（Entity 页"问题层"描述不够清晰时按需补读）
- 不要读已有种子库或其他仓库结果，独立处理

## 对每个 Entity 做两件事

1. 判断"问题层"的问题是否值得进入候选：
   构建同类框架的人，在这个问题上必须做出设计选择吗？
   → 是：生成一条问题空间条目
   → 否（实现细节 / 仅此仓库特有）：跳过，末尾附注理由

2. 补充这个仓库的解法和关切

## 输出格式

路径：seeds/<仓库名>-problem-map.md

每条问题空间条目：

---
## <问题名>（"如何..."形式）

**问题陈述**：<为什么构建同类框架的人都必须面对这个问题，一句话>
**核心关切**：
- 关切 1：<相互制约的需求，一句话>
- 关切 2：...
**<仓库名> 的解法**：<一句话>
**源码证据**：<文件路径:行号>
**来源 Entity**：<Entity slug>
**层级**：架构决策 / 技术选型
```

---

## ★ 暂停点 1：问题空间完整性确认

Step 2 完成后展示以下摘要并等待用户确认：

```
本次提取到 <N> 个问题空间，来自 <M> 个 Entity：

| 问题空间                      | 来源 Entity       | 层级     |
|-------------------------------|-------------------|----------|
| 如何...                       | <entity-slug>     | 架构决策 |
| ...                           | ...               | ...      |

跳过的 Entity（<K> 个，属于实现细节）：
- <slug>：<原因>

是否有遗漏的能力域？确认后继续 Step 3。
```

用户可以：指出遗漏 → LLM 补充提取后更新 problem-map → 再继续。
用户不响应则自动继续。

---

## Step 3：问题空间匹配

运行以下提示词：

```
你的任务是把 <仓库名> 的问题空间映射结果和已有 Concept 页比对，产出候选清单。

## 输入

- 新仓库问题空间映射：seeds/<仓库名>-problem-map.md
- 已有种子库：seeds/master.md
- 已有 Concept 页：先扫描 `wiki/concepts/` 下所有 `.md` 的 frontmatter（文件名 + problem 字段）做初筛；对可能相关的条目，读全文的"核心问题"和"关切"节以判断准则②

## 判定准则

对每条问题空间条目，判断四种情况（见下）。
新建或追加时，必须通过以下准则检验（单源定义见 `schema/concept-criteria.md`）：

硬门槛（三条必须全部满足）：

① 多方案
   至少两个不同仓库以明显不同的方式解决了同一个问题。
   注意：如果分析后一个方案在所有 trade-off 维度上都优于另一个，
   说明这不是真正的设计权衡，不成立。

② 独立设计空间
   这个问题无法被某个已有问题空间完全覆盖——
   合并进去后，它自身的讨论维度会消失，Framework Builder
   在这个问题上的决策价值会损失。

③ 持续存在的 Trade-off
   不同方案之间的权衡没有银弹——
   满足关切 A 会增大满足关切 B 的成本，反之亦然。

辅助判断（不满足不否决，影响优先级）：

④ 可持续扩展
   新仓库未来仍可能在这个问题上贡献新的解法。
   如果长期无新仓库加入，触发"降级"演化建议。

## Few-shot 示例

### 示例领域 1：AI Agent 框架

输入 Entity（跨仓库）：
- OpenClaw: Agent（YAML配置）, Workflow（显式编排）, Memory（外部上下文注入）,
            ToolTimeout（YAML配置每个工具的超时时间）
- HermesAgent: Agent（@agent装饰器）, EventBus（事件驱动协同）,
               Memory（内部状态同步）, ToolTimeout（per-toolset超时设置）

正例——"Agent 定义方式"：
① 至少两仓库不同方案：配置驱动 vs 装饰器驱动。✅
② 独立设计空间：评价维度是声明式便捷性 vs 编程灵活性，
   不与"多Agent协作"共享评价维度。✅
③ 持续 Trade-off：配置简单但灵活性低 vs 编程自由但门槛高，无银弹。✅
④ 可持续扩展：新框架仍会在这个问题上做不同选择。✅
决策：✅ 新建 Concept 页 agent-definition-style

反例 1——失败在 ①：仅单一仓库
候选分组"HermesAgent 的 SafeWriter 管道保护"：
① 多方案：❌ 仅 HermesAgent 有此实现，其他仓库无对应 Entity。
决策：❌ 进种子库待观察，不成立 Concept

反例 2——失败在 ②：不是独立设计空间
候选分组"工具执行超时配置"：
① 多方案：OpenClaw 用 YAML 配置每个工具超时，HermesAgent 用 per-toolset 超时。✅
② 独立设计空间：❌ "超时配置"是"工具执行安全与控制"这个已有问题空间的一个子维度。
   合并进去后不会损失讨论维度。
决策：❌ 不成立，作为"工具执行安全"Concept 的子维度处理

反例 3——失败在 ③：没有真正的 Trade-off
候选分组"日志结构化格式"：
① 多方案：OpenClaw 用纯文本格式，HermesAgent 用结构化 JSON + 自动脱敏。✅
② 独立设计空间：日志格式有自己的评价维度。✅
③ 持续 Trade-off：❌ 结构化 JSON 在所有关切上都优于纯文本，
   这不是相互制约的权衡，而是一个方案尚未演化到位。
决策：❌ 不成立，纯文本格式作为历史条目记录

反例 4——失败在 ④（辅助判断）
候选分组"Agent 进程启动顺序"：
① ✅ ② ✅ ③ ✅
④ 可持续扩展：⚠️ 随着异步运行时普及，这个问题空间可能很快收敛。
决策：⚠️ 暂时建页，演化信号文件中标注"低扩展预期"

### 示例领域 2：嵌入式数据库

输入 Entity（跨仓库）：
- SQLite: B-Tree（存储结构）, WAL（预写日志）
- LevelDB: LSM-Tree（存储结构）, MemTable+SSTable（写入流水线）
- RocksDB: ColumnFamily, Compaction（压缩策略）, BloomFilter

正例——"存储引擎核心数据结构"：
① B-Tree vs LSM-Tree，设计哲学完全不同。✅
② 独立于持久化策略的评价维度。✅
③ 读优化 vs 写优化，经典无银弹权衡。✅
决策：✅ 新建 Concept 页 storage-engine-data-structure

反例——失败在 ①：
候选分组"Bloom Filter 过滤策略"：
① ❌ 仅 RocksDB 有 BloomFilter。
决策：❌ 进种子库待观察

## 四种情况处理

情况 A — 命中现有问题空间
  和某个已有 Concept 页的核心问题是同一个问题
  动作：标记"追加到 <slug>"

情况 B — 新问题空间，通过三条硬门槛
  动作：标记"新建 Concept 页"，附三条准则各一句判断理由

情况 C — 待观察
  目前只有一个仓库面对这个问题
  动作：进种子库，不升级

情况 D — 演化信号
  与已有 Concept 部分重叠但不完全命中
  动作：记录演化信号，不进入本次写作

## 输出

文件 1：seeds/<仓库名>-candidates.md
  每条：情况类型 / 问题名 / 目标 slug（A类）或新建名称（B类）/ 判断理由

  末尾附能力域覆盖表（人工核查用）：
  | 能力域 | <仓库1> | <仓库2> | <新仓库> |
  |--------|--------|--------|--------|
  | <能力域> | ✅/— | ✅/— | ✅/— |

文件 2：docs/evolve-signals/<YYYY-MM-DD>-<仓库名>.md
  仅 D 类信号，每条：
  - 问题：<名称>
  - 相关 Concept：<slug>
  - 信号类型：粒度不匹配 / 候选合并
  - 理由：<一句话>
```

---

## ★ 暂停点 2：候选清单确认

Step 3 完成后展示：

```
候选 Concept 清单：

  A 类（追加到已有页面）：<N> 条
    - <problem-name> → [[<slug>]]
    ...

  B 类（新建 Concept 页）：<N> 条
    - <problem-name>（新建 <slug>）
      理由：①<一句> ②<一句> ③<一句>
    ...

  C 类（待观察）：<N> 条
  D 类（演化信号）：<N> 条，已写入 docs/evolve-signals/

能力域覆盖表：
| 能力域     | 仓库 A | 仓库 B | 新仓库 |
|------------|--------|--------|--------|
| ...        | ...    | ...    | ...    |

是否调整？确认后继续 Step 4。
```

用户可以：否决某个 B 类新建 / 手动升级某个 C 类 / 调整 slug 命名。
用户不响应则自动继续。

---

## Step 4：Concept 写作

对 candidates.md 中每个 A/B 类条目，各启动一个独立 agent：

```
你负责写或更新一个 Concept 页。每次只处理一个 Concept。

## 读者是谁

Framework Builder——正在研究这类框架设计空间的人。
不需要判断哪个最好，需要建立完整的设计空间地图：
在这个设计问题上，不同框架做了什么选择，每个选择的代价是什么。

## 输入

- 候选清单中的单条条目（情况 A 或 B）
- 该条目原文：seeds/<仓库名>-candidates.md
- 若情况 A：现有 Concept 页 wiki/concepts/<slug>.md
- 源码目录（必须读源码验证，不能只凭映射结果写）

## 强制规则

1. 每个声明必须有源码证据 ^[文件路径:行号]
2. 情况 A（追加）：只添加新仓库内容，不修改已有仓库内容
3. Concept 名称格式：<能力域>-<决策维度>（小写 kebab-case）
4. 对比表聚焦关切之间的张力，不是功能列表

## 输出

路径：wiki/concepts/<slug>.md

---
type: concept
concept: <slug>
problem: <核心问题，一句话>
concerns: [<关切1>, <关切2>]
repos: [<仓库列表>]
generated: <YYYY-MM-DD>
---

# <Concept 名>

## 核心问题

<为什么构建同类框架的人都必须回答这个问题>
<不同解法之间的根本张力是什么>

## 关切

<各关切之间如何相互制约>

## 各框架的解法

### <仓库名>

来源：[[repos/<仓库名>/entities/<entity-slug>]]
**解法**：<一句话>
**实现**：<关键机制> ^[文件路径:行号]
**权衡**：满足了哪些关切，代价是什么

[每个仓库一节]

## 对比

| 框架 | 关切 A | 关切 B | 关切 C |
|------|--------|--------|--------|

## 演化记录

- <YYYY-MM-DD>：初建，包含 <仓库名>
- <YYYY-MM-DD>：新增 <仓库名>

## 后置动作

写完本页后，到每个来源 entity 页（`wiki/repos/<name>/entities/<slug>.md`）末尾追加反向链接。
如果该 entity 已被其他 concept 引用过，在已有列表后追加一项；如果没有，新建列表：

```
**关联 Concept**：
- [[concepts/<this-slug>]]
```

注意：一个 entity 可能关联多个 concept——比如 MemoryManager 同时涉及 memory-backend-replaceability 和 state-synchronization。追加时不要覆盖已有条目。
```

---

## Step 5：验证 + 修复（`--verify` 开启时）

```
## 验证 agent

输入：wiki/concepts/<slug>.md + 对应仓库源码

对每个仓库的解法，逐一检查：
1. 源码证据是否存在（路径:行号能找到）
2. 描述是否和源码一致（不夸大、不遗漏关键约束）
3. 对比表的判断是否有源码支撑

输出验证报告：
  ✅ 准确
  ⚠️ <描述>：部分不准确，可修复
  ❌ <描述>：严重错误，需重写

---

## 修复 agent

输入：验证报告 + wiki/concepts/<slug>.md + 源码

只修复 ⚠️ 或 ❌ 的部分。
不改动验证通过的内容。
每次修改附修改理由。
```

---

## Step 6：种子库更新 + 快照保存

```
完成本次 ingest 的收尾工作。

## 输入

- 问题空间映射：seeds/<仓库名>-problem-map.md
- 候选清单：seeds/<仓库名>-candidates.md
- 已有种子库：seeds/master.md（如不存在则跳过）
- 源码目录：<源码路径>

## 五项操作

1. 合并种子库
   把 <仓库名> 所有问题空间条目（A/B/C 类均进入）追加到 seeds/master.md
   标注来源仓库和情况类型

2. 确认演化信号文件
   检查 docs/evolve-signals/<YYYY-MM-DD>-<仓库名>.md 是否存在且完整
   （Step 3 已生成，这里只做完整性确认）

3. 更新 wiki/index.md
   - Repos 节：新增或更新 <仓库名> 行（格式见维护文件规范）
   - Concepts 节：按格式刷新 Concept 表格（新增/更新的 Concept 行同步）

4. 覆盖写入 wiki/hot.md：
   # Hot Context
   **Last operation:** ingest <仓库名> — <Entity数量> entities, <Concept数量> concepts
   **Active repos:** <当前所有已 ingest 仓库，逗号分隔>
   **Concept pages:** <N>
   **Pending evolve signals:** <K>（docs/evolve-signals/）

5. 追加 wiki/log.md：
   [<YYYY-MM-DD HH:MM>] ingest <仓库名> — <Entity数量> entities, <Concept数量> concepts updated/created

6. 覆写 wiki/repos/<仓库名>/.ingest-state.json：
   用本次 ingest 实际读取的文件列表及其 SHA-256 覆写快照。
   source_path 写入当前源码目录路径。
```

---

## ★ 暂停点 3：ingest 完成总结

Step 6 完成后展示：

```
ingest <仓库名> 完成：
  - <M> 个 Entity 提取
  - <N> 个 Concept 页更新/新建
  - <K> 条演化信号写入 docs/evolve-signals/<date>-<name>.md

建议下一步：
  1. 触发 /evolve-apply 处理 <K> 条演化信号
  2. 继续 ingest 下一个仓库：<建议仓库名>
  3. 深挖当前 Concept：/query <slug>
```

---

## 文件结构规范

```
wiki/
  repos/
    <name>/
      .ingest-state.json    ← Step 6 维护（增量快照）
      overview.md           ← Step 1 产物（新建或覆写）
      entities/             ← Step 1 产物
        <slug>.md
  concepts/                 ← Step 4 产物
    <slug>.md

seeds/
  <name>-problem-map.md     ← Step 2 产物
  <name>-candidates.md      ← Step 3 产物
  master.md                 ← Step 6 维护

docs/
  evolve-signals/
    <YYYY-MM-DD>-<name>.md  ← Step 3 产物（D 类信号）
```

## 维护文件规范

以下三个文件 LLM 会在 ingest / query / compare / evolve 后自动维护。
格式必须严格遵守——`/query` 的 Level 1 index scan 和 `/lint` 的检查都依赖这些格式。

### wiki/index.md

**角色**：wiki 目录页。`/query` 检索升级链 Level 1 的第一个读取目标——LLM 用它判断"有没有相关页面值得深入"。

**格式**：

```markdown
# Codebase Wiki

## Repos

- [[<name>/overview]] — <一句话描述> — topics: <逗号分隔> — last ingest: <YYYY-MM-DD>

## Concepts

| 问题 | 页面 | 覆盖仓库 |
|------|------|----------|
| <problem 一句话> | [[concepts/<slug>]] | <repo>, <repo> |
| ... | ... | ... |

## Views

- [[views/<filename>]] — <描述> — <YYYY-MM-DD>

## Insights

- [[insights/<filename>]] — <标题> — <YYYY-MM-DD>
```

### wiki/log.md

**角色**：操作日志。`/lint` 检查最后一次操作时间等。

**格式**（只追加，不修改已有行）：

```
[YYYY-MM-DD HH:MM] <操作> <详情>
```

### wiki/hot.md

**角色**：热点上下文。每次操作覆盖写入。`/lint` 检查 stale 状态时快速读取。

**格式**：

```markdown
# Hot Context

**Last operation:** <最近一次操作及结果>
**Active repos:** <当前所有已 ingest 仓库，逗号分隔>
**Concept pages:** <N>
**Pending evolve signals:** <K>
```

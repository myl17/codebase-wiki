# Ingest Pipeline 全链路重制设计

**日期**：2026-06-22  
**状态**：待实现  
**背景**：基于近期实验（entity-concept-extraction/）和两轮 GPT/DeepSeek 概念讨论的结果，对整个 ingest 管线进行全链路重制。

---

## 一、核心变化总结

| 维度 | 旧设计 | 新设计 |
|------|--------|--------|
| Ontology 层 | 独立提取，单仓库判断能力域 | 删除，由 Step 3 的能力域覆盖表取代 |
| Entity 提取 | 仅描述实现 | 增加"问题层"字段（抽象问题，"如何..."形式） |
| Step 2 产物 | 设计选择草稿 | 问题空间映射（problem-map） |
| 过滤视角 | 架构师 + 二次开发者 | Framework Builder |
| 维度约束 | 三个固定维度（可替换性/资源策略/安全） | 删除，不预设维度 |
| Concept 判定准则 | 三条 | 四条（①②③硬门槛 + ④辅助） |
| Few-shot | 无 | 两个跨领域示例 + 四类反例 |
| 演化机制 | 无 | `/evolve-apply`：merge / split / redirect |
| 验证步骤 | 默认开启 | 默认关闭，`--verify` 开启 |

---

## 二、管线总览

```
/ingest <repo-path> [<repo-name>] [--verify]

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

/evolve-apply <signal-file> [--operation merge|split|redirect] [--from <slug>] [--to <slug>]
```

---

## 二-a、用户参与点设计

ingest 流程有三个天然暂停点。原则：**LLM 写、人读、人给方向、LLM 继续。不是人批准每一步产出。**

暂停点之外，LLM 自主执行。

---

### 暂停点 1：Step 2 完成后

**目的**：发现 Entity 提取遗漏。

用户看到的是问题空间语言（"如何..."），比模块列表更容易判断覆盖度。

LLM 展示：

```
本次提取到 <N> 个问题空间，来自 <M> 个 Entity：

| 问题空间                      | 来源 Entity       | 层级     |
|-------------------------------|-------------------|----------|
| 如何管理记忆后端的可替换性    | memory-manager    | 架构决策 |
| 如何控制工具执行的安全边界    | approval-system   | 架构决策 |
| 如何处理上下文窗口压缩        | context-engine    | 架构决策 |
| ...                           | ...               | ...      |

跳过的 Entity（<K> 个，属于实现细节）：
- <slug>：<原因>

是否有遗漏的能力域？确认后继续 Step 3。
```

用户可以：指出遗漏 → LLM 补充提取后更新 problem-map → 再继续。
默认行为：用户不响应则继续。

---

### 暂停点 2：Step 3 完成后

**目的**：用户主导 Concept 粒度决策。

LLM 展示候选清单摘要 + 能力域覆盖表：

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
| 记忆管理   | ✅     | ✅     | ✅     |
| 工具执行   | ✅     | —      | ✅     |
| ...        | ...    | ...    | ...    |

是否调整？确认后继续 Step 4。
```

用户可以：否决某个 B 类新建 / 手动升级某个 C 类 / 调整 slug 命名。
默认行为：用户不响应则继续。

---

### 暂停点 3：Step 6 完成后

**目的**：用户决定后续方向。

LLM 展示 ingest 总结：

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

用户给方向，LLM 执行。

---

## 三、关键概念定义

### Entity
源码中可独立定位的模块——有明确边界、对外接口、可以被单独理解和替换。
每个 Entity 有两层问题描述：
- **实现层**：这个仓库的具体做法
- **问题层**：构建同类框架时必须面对的抽象问题（"如何..."形式）

### Concept（问题空间）
所有同类系统都必须回答的设计问题，没有唯一最优解，因为它涉及多个相互制约的关切，不同系统对这些关切的优先级排序不同，因此落在了不同的权衡位置上。

Concept 不是直接提取出来的，而是从多仓库 Entity 的问题层演化出来，通过四条准则筛选。

### Framework Builder
Concept 的读者。正在研究一类框架设计空间的人，目标是建立"这类框架在哪些维度上有不同选择，每个选择的代价是什么"的知识地图。不是在解决具体项目约束，而是在做知识储备。

---

## 四、完整提示词

### Step 1：Entity 提取

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

### <Entity 名称>

**代码位置**：<目录/包路径>
**这个模块解决什么问题**：
- 实现层：<这个仓库的具体做法，一句话>
- 问题层：<构建同类框架时必须面对的抽象问题，一句话，"如何..."形式>
**对外暴露什么**：<关键类/函数/接口，含文件路径:行号>
**它和谁交互**：<依赖的其他模块 / 被谁调用>
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
- 这个仓库是什么（一段话）
- 核心子系统列表（wikilink 到各 Entity 页）
- 明确不做什么

## 核心约束

1. 每条事实声明必须有 ^[文件路径:行号]
2. 每个 Entity 独立文件，不合并
3. 广泛探索，不遗漏独立目录或独立包
```

---

### Step 2：Entity 问题空间映射

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

### Step 3：问题空间匹配

```
你的任务是把 <仓库名> 的问题空间映射结果和已有 Concept 页比对，产出候选清单。

## 输入

- 新仓库问题空间映射：seeds/<仓库名>-problem-map.md
- 已有种子库：seeds/master.md
- 已有 Concept 页：wiki/concepts/（只读文件名和首行 problem 字段）

## 判定准则

对每条问题空间条目，判断四种情况（见下）。
新建或追加时，必须通过以下准则检验：

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

### Step 4：Concept 写作（per-Concept 独立 agent）

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
concept: <slug>
problem: <核心问题，一句话>
concerns:
  - <关切 1>
  - <关切 2>
repos: [<仓库列表>]
---

# <Concept 名>

## 核心问题

<为什么构建同类框架的人都必须回答这个问题>
<不同解法之间的根本张力是什么>

## 关切

<各关切之间如何相互制约>

## 各框架的解法

### <仓库名>

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
```

---

### Step 5（`--verify` 开启时）：验证 + 修复

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

### Step 6：种子库更新 + 演化报告落地

```
完成本次 ingest 的收尾工作。

## 输入

- 问题空间映射：seeds/<仓库名>-problem-map.md
- 候选清单：seeds/<仓库名>-candidates.md
- 已有种子库：seeds/master.md

## 三项操作

1. 合并种子库
   把 <仓库名> 所有问题空间条目（A/B/C 类均进入）追加到 seeds/master.md
   标注来源仓库和情况类型

2. 确认演化信号文件
   检查 docs/evolve-signals/<YYYY-MM-DD>-<仓库名>.md 是否存在且完整
   （Step 3 已生成，这里只做完整性确认）

3. 更新维护文件
   wiki/log.md 追加：
     [<timestamp>] ingest <仓库名> — <Entity数量> entities, <Concept数量> concepts updated/created
   wiki/hot.md 覆盖写入当前状态
```

---

## 五、`/evolve-apply` 提示词

### 操作 A：合并（Merge）

```
你的任务是把两个 Concept 页合并为一个。

## 输入

- 被合并页：wiki/concepts/<slug-A>.md
- 合并目标页：wiki/concepts/<slug-B>.md
- 合并理由：<来自演化信号文件的描述>

## 判断确认（执行前必须检查）

合并是否成立，必须满足：
- <slug-A> 讨论的问题是 <slug-B> 讨论问题的一个子维度
- 合并后 <slug-A> 的内容在 <slug-B> 页面内能被完整表达
- <slug-A> 没有 <slug-B> 没有的独立关切或对比维度

任意一条不满足，停止操作，说明原因。

## 执行步骤

1. 把 <slug-A> 中各仓库的解法合并进 <slug-B> 对应位置
2. 更新 <slug-B> 的对比表，纳入 <slug-A> 引入的维度
3. 更新 <slug-B> 的演化记录，注明合并来源和日期
4. 把 <slug-A>.md 改写为重定向页：

   ---
   redirect_to: <slug-B>
   reason: <一句话>
   date: <YYYY-MM-DD>
   ---
   # <slug-A 原标题>
   > 此页面已合并至 [[<slug-B>]]。原因：<reason>

5. 更新 seeds/master.md，相关条目标注 merged_into: <slug-B>
6. 追加 wiki/log.md：[<timestamp>] evolve merge <slug-A> → <slug-B>

## 不修改

<slug-B> 中已有仓库的内容，只追加不覆盖。
```

### 操作 B：拆分（Split）

```
你的任务是从现有 Concept 页中拆分出一个新的子 Concept 页。

## 输入

- 源页面：wiki/concepts/<slug-src>.md
- 拆分子议题：<子议题名称>
- 拆分理由：<来自演化信号文件的描述>

## 判断确认（执行前必须检查）

拆分是否成立，必须满足：
- 子议题下已有 ≥2 个仓库的不同方案，且方案间有真实 trade-off
- 子议题独立成页后仍能通过四条准则的①②③
- 拆分后的子议题不是源页面某个方案的单独描述

任意一条不满足，停止操作，说明原因。

## 执行步骤

1. 新建 wiki/concepts/<new-slug>.md
   包含从源页面剥离的相关仓库解法、关切、对比表
   演化记录注明"拆分自 [[<slug-src>]] on <date>"

2. 更新源页面：
   - 移除已迁移的详细内容
   - 保留摘要（一句话）并加 wikilink 到新页面
   - 演化记录注明"拆分出 [[<new-slug>]] on <date>"

3. 更新 seeds/master.md，相关条目标注 split_to: <new-slug>
4. 追加 wiki/log.md：[<timestamp>] evolve split <slug-src> → <new-slug>
```

### 操作 C：重定向（Redirect）

```
你的任务是为一个 Concept 页建立重定向别名。

## 输入

- 目标页：wiki/concepts/<slug-target>.md
- 别名名称：<alias-name>
- 理由：<为什么这两个名字指向同一个问题空间>

## 执行步骤

1. 新建 wiki/concepts/<alias-slug>.md：

   ---
   redirect_to: <slug-target>
   reason: <一句话>
   date: <YYYY-MM-DD>
   ---
   # <alias-name>
   > 此名称重定向至 [[<slug-target>]]。原因：<reason>

2. 追加 wiki/log.md：[<timestamp>] evolve redirect <alias-slug> → <slug-target>

## 不修改目标页的任何内容
```

---

## 六、其他 Skills 的适配需求

以下三个已有 skill 与新架构不兼容，需要同步改造，不能直接沿用：

### `/query` — 需要改动（部分失效）

失效点：
1. **Graph traversal 整节**：依赖 `wiki/repos/*/nodes/` 目录和 `graph.py` 脚本，
   以及旧节点类型（DesignDecision / Component）。新架构无 nodes/ 目录，无 graph.py。
   替代方案：沿 wikilink 网络遍历（Entity 页 → Concept 页 → 其他 Entity 页）。
2. **Insight 归档的 sources 字段**：现在指向 `dimensions/*.md`，
   新架构应改为指向 `entities/*.md` 和 `concepts/*.md`。
3. **选项 B"补充现有维度页"**：新架构无维度页，
   应改为"补充现有 Entity 页或 Concept 页"。

保留不变：Retrieval Escalation Chain、Archival Decision 机制（询问用户是否存档）。

### `/compare` — 需要重写（整体失效）

整个 skill 基于五维度页（`wiki/repos/<repo>/dimensions/<dim>.md`）+ `.manifest.json`
版本比对，新架构删除五维度。

新定位：给定多个仓库名或一个问题关键词，找到相关 Concept 页，
把各 Concept 页的对比表汇总输出。Concept 页内置的对比表已经覆盖了原 `/compare`
的核心功能，`/compare` 退化为"跨 Concept 汇总视图"的生成器。

### `/lint` — 需要部分更新

基础 wikilink 完整性检查仍然有效。
失效点：
- "维度版本比对"规则（依赖 `dimensions_version` frontmatter 和 `.manifest.json`）
- "provenance 覆盖率"规则（依赖旧维度页格式）

需要新增：
- Entity 页 frontmatter 合规检查（必须有 `repo`、`slug` 字段）
- Concept 页 frontmatter 合规检查（必须有 `concept`、`problem`、`repos` 字段）
- Concept 页 `## 演化记录` 存在性检查

---

## 七、待优化项（本次设计不覆盖）

- Few-shot 反例的具体内容需要优化——当前示例中反驳理由有些牵强，后续单独迭代
- seeds/master.md 的具体格式规范未定义
- `/evolve-apply` 的人工确认交互流程（逐条确认 vs 批量确认）未设计
- Step 3 能力域覆盖表的标准能力域列表未定义（当前由 LLM 自行归纳）
- `/ingest --resume` 中断恢复机制未设计（三个暂停点使得这个需求更重要）

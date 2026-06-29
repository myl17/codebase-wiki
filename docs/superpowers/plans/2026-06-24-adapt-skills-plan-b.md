# Skills 适配新架构 — Plan B

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `/query`、`/compare`、`/lint` 三个 skill 从旧的五维度体系适配到新的 Entity → Concept 架构。

**Architecture:** 三个 skill 各自独立修改，互不依赖。`/query` 部分修改，`/compare` 整体重写，`/lint` 规则替换。

**前置条件:** Plan A 已完成（新目录结构、新 SKILL.md、旧文件已清理）。

## Global Constraints

- SKILL.md 使用中文书写正文
- 不引入新脚本
- Insight 归档机制保留，存档对象从 dimension 页改为 entity/concept 页

---

### Task 1：修改 `/query`（`skills/code-query/SKILL.md`）

#### 这个 skill 是做什么的

`/query` 是一个知识问答工具。用户问一个问题——比如"hermes-agent 的消息通道怎么扩展的？"——`/query` 从 wiki 里找答案，给出带源码证据的回答。

**工作方式是两级策略：**

1. **先判断是不是"结构性问题"**——问的是"某物波及什么""某物为什么这样设计""哪些仓库也有某物"——这类问题 wikilink 网络能直接解答。顺着 entity → concept → entity 的链接走一圈就够了。

2. **不是结构性问题，走 Retrieval Escalation Chain（检索升级链）**——这是一个"从便宜到贵"的渐进搜索策略：
   - Level 1（最便宜）：读 `wiki/index.md`，找有没有相关页面
   - Level 2：在候选页面里 grep 关键词，找到具体段落
   - Level 3（最贵）：全文读相关页面，综合分析
   - **核心原则**：不在前一级确认不够之前就升级到下一级。这个设计是为了省 token——不该每次回答问题都把所有 wiki 页全读一遍。

3. 答完后问用户"这个答案值得存档吗？"——有价值的分析写回 wiki，不消失在聊天里。

#### 新架构下为什么失效

- 结构性问题依赖 `python scripts/graph.py query` + `wiki/repos/*/nodes/` 目录。nodes/ 已删，graph.py 已废。
- 存档对象是"维度页"——旧架构概念。应改为 entity 页或 concept 页。
- Insight frontmatter 有 `dimensions_version` 字段——新架构无此概念。

#### 保留不动

- Retrieval Escalation Chain（Level 1/2/3 逻辑）——完全不改，它不依赖旧架构的任何组件
- Archival Decision 机制（问用户是否存档）
- `--repo` 过滤器

#### 需要改什么

**改动 1：Graph Traversal 整节替换**

旧内容：依赖 graph.py + nodes/ 的遍历逻辑。
新内容：沿 wikilink 网络遍历——利用 entity/concept 页 frontmatter 的 `type` 和 `problem` 字段快速定位相关页面。

**改动 2：Archival Decision 选项 B**

旧："补充现有维度页" → 新："补充现有 Entity 页或 Concept 页"

**改动 3：Insight frontmatter**

删除 `dimensions_version`，`sources` 从 `dimensions/*.md` 改为 `entities/*.md` 和 `concepts/*.md`

---

**Files:**
- Modify: `skills/code-query/SKILL.md`

**Implementation:**

- [ ] **Step 1: 替换 Graph Traversal 整节**

定位 `## Graph Traversal` 到 `## Retrieval Escalation Chain` 之间的全部内容（含两个标题），替换为：

```markdown
## Wikilink 遍历（结构性问题优先）

如果问题匹配以下模式，先做 wikilink 遍历，而不是走 Retrieval Escalation Chain：

- "X 会影响什么" / "改 X 会波及哪些" / "X 的影响范围"
- "为什么有 X" / "X 为什么这样设计"
- "哪些仓库也有 X" / "X 在不同仓库有什么不同做法"

### 为什么这类问题走 wikilink 遍历就够了

因为 entity 页之间通过 concept 页互相连接——entity → concept → 其他 entity。
顺着这个网络走，你看到的是"其他仓库在同类问题上做了什么不同选择"，
这正是结构性问题要的答案。

### 遍历步骤

1. 从问题中识别关键词，扫描 `wiki/repos/*/entities/` 和 `wiki/concepts/`：
   ```bash
   # 按关键词找 entity 页（读 frontmatter 的 problem: 字段）
   grep -rl "problem:" wiki/repos --include="*.md" | head -20
   # 按关键词找 concept 页（读 frontmatter）
   grep -rl "type: concept" wiki/concepts --include="*.md" 2>/dev/null | head -20
   ```
   （以上命令从 wiki 根目录执行。读候选文件的前 10 行 frontmatter，判断 `problem:` 字段是否匹配问题。）

2. 读目标页面，沿其中的 wikilink 展开：
   - entity 页 → 末尾的 `**关联 Concept**：[[concepts/<slug>]]`
   - concept 页 → "各框架的解法"节中每仓库的 `来源：[[repos/<name>/entities/<slug>]]`
   - overview 页 → 子系统列表中的 `[[repos/<name>/entities/<slug>]]`

3. 跨仓库问题：直接找 concept 页。Concept 页的"各框架的解法"节和"对比"表
   已经汇聚了所有仓库的不同做法，无需逐个读 entity 页。

### 遍历输出格式

```
## 影响发现：<问题名>

**相关 Concept**：[[concepts/<slug>]]
<concept frontmatter 的 problem 字段>

**各框架的做法**：
- [[repos/<repo>/entities/<slug>]]：<解法一句话>
- [[repos/<repo>/entities/<slug>]]：<解法一句话>

**核心张力**：<从 concept 对比表提炼，不同做法之间的 trade-off>

遍历路径：<entity> → <concept> → <其他 entity>
```

如果找不到匹配的页面，降级到 Retrieval Escalation Chain（下节）。
```

- [ ] **Step 2: 修改 Archival Decision 选项 B**

定位 `## Archival Decision (always ask)` 节，修改选项 B：

旧：
```
- B: 补充现有维度页（发现了现有页面的补充或修正）
```
新：
```
- B: 补充现有页面（发现了现有 Entity 页或 Concept 页的补充或修正）
```

选项 B 的执行说明改为：
```markdown
### If user chooses B:
Append to the relevant Entity page (`wiki/repos/<name>/entities/<slug>.md`)
or Concept page (`wiki/concepts/<slug>.md`) under a `## 补充` section. Append log entry.
```

- [ ] **Step 3: 修改 Insight frontmatter**

定位 `### If user chooses C:` 下的 frontmatter 示例：

改 `sources:` 示例从 `dimensions/*.md` 改为新路径，删除 `dimensions_version`：

```yaml
---
title: <descriptive title>
type: insight
query: "<original question verbatim>"
generated: <date>
sources: ["wiki/concepts/memory-backend-replaceability.md", "wiki/repos/nanobot/entities/memory-manager.md"]
provenance_repos: ["nanobot", "hermes-agent"]
---
```

- [ ] **Step 4: 验证**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
# 确认旧引用已清除
grep -n "graph.py\|nodes/\|dimensions_version\|维度页" skills/code-query/SKILL.md
# 应无任何输出
```

- [ ] **Step 5: Commit**

```bash
git add skills/code-query/SKILL.md
git commit -m "feat: adapt /query to new architecture — wikilink traversal, update archival targets"
```

---

### Task 2：重写 `/compare`（`skills/code-compare/SKILL.md`）

#### 这个 skill 是做什么的

`/compare` 把多个仓库在同一个问题上的不同做法摆在一起对比。比如"openclaw、hermes-agent、nanobot 在记忆管理上各有什么取舍？"

#### 旧工作方式（完全失效）

按"仓库 × 五维度"做全矩阵——读每个仓库的五个 dimension 文件、对同一维度并排。靠 `.manifest.json` 的 `categories`、`dimensions_version` 版本比对。新架构删除了所有这些组件。

#### 新工作方式：对比升级链

核心思路和 `/query` 的 Retrieval Escalation Chain 一致——从便宜到贵，只在上一级无法满足时才升级。

**Level 1 — Concept 页（最便宜，已预计算）**
Concept 页的 `## 对比` 节就是跨仓库对比表——ingest 时已经写好。如果用户的对比请求正好落在一个已有 Concept 的覆盖范围内（通过 frontmatter `repos:` 和 `problem:` 匹配），直接提取展示即可。不读源码。

**Level 2 — Entity 页（中等成本）**
当 Concept 页没覆盖到某个对比点时（比如新仓库刚 ingest、Concept 还没演化），但多个仓库有 entity 的 `problem:` 字段指向同一类问题——读 entity 页的"这个模块解决什么问题"和"关键机制"，提取对比信息。

判断 Level 1 是否足够的信号：
- 指定仓库的 Concept 交集为空 → 降级到 Level 2
- 用户加了 `--concept` 关键词但无匹配 → 降级到 Level 2（按关键词搜 entity 的 `problem:`）

**Level 3 — 源码（最贵，最后手段）**
Concept 没覆盖、entity 页也找不到相关模块时，按用户的关键词直接读指定仓库的源码，做现场对比。这是最贵的路径——必须先在指定仓库源码里 grep 定位、再读关键代码段——读之前先告知用户估算范围，获得确认。

**对比结果必须标注信息来源**：无论来自哪一级，输出开头要写明：

```
> 信息来源：<来源>
> - Concept：已有预计算结果
> - Entity：从 Entity 页提取
> - 源码：从仓库源码现场分析
```

#### 触发语法

支持任意数量仓库 + 可选关键词过滤：

```
/compare <repo1> <repo2> [<repo3> ...]
/compare --concept <keyword>
/compare <repo1> <repo2> ... --concept <keyword>
```

示例：
```
/compare hermes-agent nanobot openclaw
/compare --concept memory
/compare hermes-agent openclaw --concept agent
```

---

**Files:**
- Modify: `skills/code-compare/SKILL.md` — 完整覆写

**Implementation:**

- [ ] **Step 1: 覆写 SKILL.md**

完整内容：

````markdown
# /compare — Cross-Repo Comparison

给定仓库名或设计问题关键词，按升级链找最便宜可用的信息来源做对比。

## Trigger

```
/compare <repo1> <repo2> [<repo3> ...]
/compare --concept <keyword>
/compare <repo1> <repo2> ... --concept <keyword>
```

示例：
```
/compare hermes-agent nanobot openclaw
/compare --concept memory
/compare hermes-agent openclaw --concept agent
```

## 对比升级链

从便宜到贵。只在上一级无法满足时升级。必须在开头标注信息来源。

```
Level 1 → Concept 页对比表（预计算，直接展示）
  ↓ 无覆盖
Level 2 → Entity 页（同一类 problem 字段的 entity 对比）
  ↓ 无覆盖
Level 3 → 源码（按关键词现场分析，最贵）
```

### Level 1 — Concept 页（最便宜）

**前提：** Concept 页的 `## 对比` 节是 ingest 时 LLM 验证过的预计算结果。

**操作：**

1. 扫描 `wiki/concepts/` 下所有 `.md`，逐一读 frontmatter（前 10 行）：
   - 如果指定了仓库名：检查 `repos:` 是否包含**所有**指定仓库。保留完全覆盖的。
   - 如果指定了 `--concept <keyword>`：检查 `concept:` 或 `problem:` 是否含关键词。
   - 两者都指定：取交集。
2. 对每个匹配的 Concept 页，读 `## 对比` 节和 `## 核心问题` 节。
3. 有匹配 → 聚合展示，信息来源标注 `Concept`，流程结束。
4. 无匹配 → 降级到 Level 2。告知用户：
   ```
   Concept 页未覆盖此对比维度。降级到 Entity 页查找。
   ```

### Level 2 — Entity 页（中等成本）

**前提：** 虽然没有匹配的 Concept 页，但多个仓库的 entity 可能都面对同一个抽象问题（通过 frontmatter 的 `problem:` 字段可判断）。比如 openclaw 的 memory 模块和 nanobot 的 memory 模块——都有 `problem: "如何管理记忆后端的可替换性"`，说明它们在同一个问题空间里。

**操作：**

1. 按搜索目标列出所有 entity 页：
   - 指定仓库：读 `wiki/repos/<name>/entities/` 下所有 `.md` 的 frontmatter
   - 指定 `--concept`：grep 所有 entity 页 frontmatter 的 `problem:` 字段
   ```bash
   grep -rl "problem:" wiki/repos --include="*.md"
   ```
   （从 wiki 根目录执行）

2. 把 `problem:` 字段相同或高度相似的 entity 归为一组。

3. 对每组，读每个 entity 页的：
   - `**这个模块解决什么问题**` 的"实现层"和"问题层"
   - `**关键机制**` 列表
   - `**对外暴露什么**`

4. 生成对比：同一问题下，各仓库的解法、机制、取舍。

5. 有匹配 → 聚合展示，信息来源标注 `Entity`，流程结束。

6. 无匹配 → 降级到 Level 3。告知用户：
   ```
   Entity 页也未覆盖此对比维度。需降级到源码搜索（最贵）。
   将按关键词在指定仓库源码中搜索，继续？
   ```

### Level 3 — 源码（最贵，最后手段）

**前提：** Concept 没覆盖、entity 也没对应模块。只能直接读源码。

**操作：**

1. 先告知用户估算范围：
   ```
   对比维度未被任何 Concept 或 Entity 页覆盖。
   将按关键词搜索所有指定仓库的源码。继续？
   ```

2. 获得确认后，在每个指定仓库源码中按关键词搜索：
   ```bash
   grep -rn "<keyword>" <repo-path> --include="*.py" --include="*.ts" --include="*.go" | head -30
   ```

3. 读关键代码段，提取每个仓库在这个问题上的：
   - 核心机制
   - 设计取舍
   - 和其他仓库的差异

4. 生成对比，信息来源标注 `源码`。

### 输出格式（所有 Level 统一）

```markdown
> 信息来源：<Concept / Entity / 源码>

## <对比维度>

**问题**：<一句话，这个维度问的是什么>

### <仓库名 A>

来源：<concept slug / entity slug / 源码路径:行号>
- **解法**：<一句话>
- **关键机制**：<具体做法>
- **取舍**：<满足了什么、代价是什么>

### <仓库名 B>

...

### 核心差异

<一句话归纳各仓库在这个维度上的根本张力>
```

多个对比维度连续排列，中间用 `---` 分割。

## 输出后

### 询问是否存档

对比完成后，问用户：

> **这个对比需要归档吗？**
> - A: 不归档（临时查看）
> - B: 存入 wiki/views/
> - C: 发起 `/ingest <repo>` 将对比发现的问题空间纳入 Concept 演化

如果选 B，写入 `wiki/views/<YYYY-MM-DD>-compare-<slug>.md`：

```yaml
---
type: view
repos: [<仓库列表>]
concepts: [<concept-slug列表>]
generated: <YYYY-MM-DD>
source_level: <Concept | Entity | 源码>
sources: ["wiki/concepts/<slug>.md", ...]
---
```

追加 `wiki/log.md`：`[<timestamp>] compare <仓库列表> — <N> dimensions`

### 对比后主动检查 Concept 结构

对比展示完成后，LLM 应主动审视所涉及 Concept 页的结构质量：

1. 这个 Concept 页是否覆盖了差异很大的子议题？（→ 建议拆分）
2. 两个 Concept 页是否在讨论本质相同的问题，只是粒度不同？（→ 建议合并）
3. 对比中发现的跨仓库模式，是否没有被任何 Concept 覆盖？（→ 建议新建）

如有发现，主动向用户提问：
> **发现 Concept 结构问题：**
> - "memory-management" 覆盖了压缩策略和后端可替换性两个独立子议题。是否拆分为两个 Concept？
> - "tool-timeout" 和 "tool-execution-safety" 讨论的是同一个设计问题。是否合并？

**用户同意后，LLM 当场执行演化操作（调用 `/evolve-apply` 的逻辑），不需要用户切换命令。**
````

- [ ] **Step 2: 验证**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
# 确认旧引用已清除
grep -n "manifest\|dimensions_version\|categories\|五维度" skills/code-compare/SKILL.md
# 应无任何输出
```

- [ ] **Step 3: Commit**

```bash
git add skills/code-compare/SKILL.md
git commit -m "feat: rewrite /compare — three-level comparison escalation chain"
```

---
### Task 3：修改 `/lint`（`skills/code-lint/SKILL.md`）

#### 这个 skill 是做什么的

`/lint` 是 wiki 健康检查——找错误（broken wikilink、缺必填字段）、给健康分、建议怎么修。

#### 旧工作方式

1. 跑 `python scripts/lint.py` 检查 wikilink 完整性（A 页链到 B 页，B 页文件在不在？）
2. 跑 `python scripts/eval.py` 检查维度页覆盖率、新鲜度、provenance 覆盖率
3. 分类汇报 ERROR/WARN/INFO，给出修复建议

#### 新架构下为什么失效

- `eval.py` 的 Coverage/Freshness 完全基于旧维度页和 `.manifest.json`——新架构无此概念
- 旧错误类型 `check_stale_dimensions` 不存在了
- 新架构引入了两种新页面类型（entity 页、concept 页），各有自己的 frontmatter 必填字段和结构要求，旧检查规则不知道这些

#### 保留

- `lint.py` 调用（wikilink 完整性检查仍然有效）
- ERROR/WARN/INFO 三级汇报格式
- `--fix` 标志（仅自动修复 INFO 级）

#### 删除

- `eval.py` 调用
- `check_stale_dimensions` 操作建议

#### 新增

- Entity 页 frontmatter 必填字段检查（`type`、`repo`、`slug`、`problem`、`generated`）
- Concept 页 frontmatter 必填字段检查（`type`、`concept`、`problem`、`concerns`、`repos`、`generated`）
- Concept 页 `## 演化记录` 节存在性检查
- Entity → Concept 反向链接检查（concept 的 repos 里有某仓库，该仓库的 source entity 末尾应有回链）

---

**Files:**
- Modify: `skills/code-lint/SKILL.md`

**Implementation:**

- [ ] **Step 1: 删除 eval.py 步骤，替换为 frontmatter 检查**

定位 `### Step 2 — Run eval.py`，整节替换为：

```markdown
### Step 2 — Frontmatter 合规检查

扫描所有 entity 页和 concept 页，检查必填字段。

**Entity 页** (`wiki/repos/*/entities/*.md`) 每个文件必须有：
- `type: entity`
- `repo:` — 所属仓库名
- `slug:` — entity 标识符
- `problem:` — 问题层描述，"如何..."形式
- `source_files:` — 来源文件列表（至少一个）
- `generated:` — 生成日期

缺任意一个 → `[ERROR] entity_missing_frontmatter`

**Concept 页** (`wiki/concepts/*.md`) 每个文件必须有：
- `type: concept`
- `concept:` — concept 标识符
- `problem:` — 核心问题，一句话
- `concerns:` — 关切列表（可为空数组 `[]`）
- `repos:` — 仓库列表
- `generated:` — 生成日期

缺任意一个 → `[ERROR] concept_missing_frontmatter`

**Concept 页结构检查：**
必须包含 `## 演化记录` 节。缺失 → `[WARN] concept_missing_evolution_log`

**Entity → Concept 反向链接检查：**
对每个 concept 页，取 `repos:` 列表中的仓库，检查对应来源 entity 页
文件末尾是否有 `**关联 Concept**：[[concepts/<slug>]]`。
缺失 → `[WARN] entity_missing_concept_backlink`
```

- [ ] **Step 2: 更新健康分指标**

定位 `### Step 3 — Report findings`，把原来基于 eval.py 的 Coverage/Freshness 指标替换为：

```markdown
**健康分：**
- Wikilink 完整性：X%（broken links / total links）
- Entity frontmatter 合规率：X%
- Concept frontmatter 合规率：X%
- Concept 演化记录覆盖率：X%
```

- [ ] **Step 3: 更新操作建议**

定位 `### Step 4 — Prioritize action`，删除 `check_stale_dimensions` 相关行，替换为：

```markdown
### Step 4 — 操作建议

- `check_broken_wikilinks` → 检查对端文件是否存在。若指向旧 `nodes/` 或 `dimensions/` 
  路径，是遗留链接，直接删除
- `entity_missing_frontmatter` → 补全对应 entity 页的 frontmatter 字段
- `concept_missing_frontmatter` → 补全对应 concept 页的 frontmatter 字段

WARN 级：
- `concept_missing_evolution_log` → 在 concept 页末尾追加 `## 演化记录` 节
  （至少一条初建记录）
- `entity_missing_concept_backlink` → 在 entity 页末尾追加
  `**关联 Concept**：[[concepts/<slug>]]`

Never auto-fix errors without user confirmation. Auto-fix only INFO-level issues with `--fix`.
```

- [ ] **Step 4: 验证**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
# 确认旧引用已清除
grep -n "eval.py\|dimensions_version\|check_stale_dimensions\|Coverage.*%\|Freshness" skills/code-lint/SKILL.md
# 确认新规则已写入
grep -n "entity_missing_frontmatter\|concept_missing_frontmatter\|演化记录\|concept_backlink" skills/code-lint/SKILL.md
```

- [ ] **Step 5: Commit**

```bash
git add skills/code-lint/SKILL.md
git commit -m "feat: adapt /lint to new architecture — frontmatter checks, remove eval.py"
```

---

## 自查清单

- [x] `/query` — 每个改动前先讲了 skill 的功能和工作方式
- [x] `/query` — Graph Traversal 替换为 wikilink 遍历（不依赖 graph.py、nodes/）
- [x] `/query` — Retrieval Escalation Chain 完全保留不动
- [x] `/query` — Archival Decision 选项 B 改为 entity/concept 页
- [x] `/query` — Insight frontmatter 删除 `dimensions_version`
- [x] `/compare` — 完整重写，先讲旧工作方式为何失效、新工作方式是什么
- [x] `/compare` — trigger 支持任意数量仓库（不限于两个）
- [x] `/compare` — 三级对比升级链：Concept → Entity → 源码
- [x] `/compare` — Level 2 通过 entity `problem:` 字段匹配同一问题空间的 entity
- [x] `/compare` — Level 3 读源码前先告知用户估算范围并获得确认
- [x] `/compare` — 所有输出统一标注信息来源（Concept / Entity / 源码）
- [x] `/compare` — bash 命令中使用相对路径（wiki/...），不写死本地绝对路径
- [x] `/lint` — 先讲功能和工作方式，再讲改动
- [x] `/lint` — 删除 eval.py 调用
- [x] `/lint` — 新增 entity/concept frontmatter 合规检查（ERROR 级）
- [x] `/lint` — 新增 concept 演化记录检查（WARN 级）
- [x] `/lint` — 新增 entity → concept 反向链接检查（WARN 级）
- [x] 三个 skill 均不引入新脚本

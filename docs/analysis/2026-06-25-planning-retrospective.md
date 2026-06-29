# Plan A/B/C 制定过程中的设计决策复盘

> 记录从旧五维度体系迁移到 Entity → Problem Space → Concept 管线过程中，每个关键设计决策的上下文、争论点和最终结论。

---

## 一、架构级决策

### 1.1 从五维度到 Entity+Concept：为什么推倒重来

**背景**：旧架构用五个固定维度（可替换性、资源策略、安全等）给每个仓库的所有模块打标签。Ingest = 按维度分类写 dimension 页。

**问题**：
- 固定维度无法适应不同领域的仓库（AI Agent 框架 vs 嵌入式数据库，关心的维度完全不同）
- 维度是预设的，不是从源码中涌现的——LLM 被框死在五个维度里，看不到真正的设计空间
- 跨仓库知识散落在各自的 dimension 页里，没有聚合点——想做对比需要手动翻五个维度 × N 个仓库的文件

**新架构核心思路**：
1. **Entity** = 源码中可独立定位的模块。两层描述："实现层"（这个仓库的具体做法）+ "问题层"（构建同类框架时都必须回答的抽象问题，"如何..."形式）
2. **Problem Space Mapping** = 把单仓库 entity 翻译成跨仓库的问题空间条目。翻译者是 Framework Builder 视角——"这个问题是构建同类框架时必须做出设计选择吗？"
3. **Concept** = 跨仓库的设计问题，通过四条准则筛选，汇聚各仓库的不同解法+对比表

**关键洞察**：不从"分类"出发，从"问题"出发。Entity 的"问题层"字段是整个管线的翻译桥梁。

### 1.2 Framework Builder 作为唯一读者角色

**旧架构**：三个角色视角——架构师、二次开发者、维护者。同一份知识要对三个不同的读者说话，导致维度设计多而不精。

**新架构**：只保留 Framework Builder——正在研究一类框架设计空间的人。目标是建立"这类框架在哪些维度上有不同选择，每个选择的代价是什么"，不是在解决具体项目约束，而是在做知识储备。

**影响**：Step 2 的翻译标准变清晰了——"这个问题是构建同类框架的人必须做出设计选择的吗？"不是就跳过。

### 1.3 四条准则的由来

**背景**：GPT 和 DeepSeek 两轮概念讨论（`docs/research/` 下的分析文档）中反复验证了一个问题——什么情况下一个跨仓库的"问题空间"值得成为独立 Concept 页？

**结论**：三条硬门槛 + 一条辅助判断：

| # | 准则 | 含义 |
|---|------|------|
| ① | 多方案 | ≥2 个仓库以明显不同的方式解决同一问题。一个方案在所有维度优于另一个则不成立 |
| ② | 独立设计空间 | 无法被已有问题空间完全覆盖——合并进去会损失决策价值 |
| ③ | 持续 Trade-off | 没有银弹——满足关切 A 会增大满足关切 B 的成本 |
| ④ | 可持续扩展 | 辅助判断，不满足不否决，影响优先级。长期无新仓库加入触发降级信号 |

**反例比正例更重要**：Step 3 的 few-shot 里设计了四个反例（单仓库、子维度被覆盖、无真实 trade-off、扩展性差），每个反例对应一条准则的边界情况。

---

## 二、Wikilink 网络设计

### 2.1 Wikilink 就是图——不需要单独维护图谱数据

**讨论**：要不要维护一份结构化的图谱数据（JSON/图谱数据库）来做 Graph Traversal？

**结论**：不需要。三类 wikilink 各自有明确的语义：

```
entity → entity    （同仓库内，"它和谁交互"节）
entity → concept   （Step 4 后置反向链接，"关联 Concept"）
concept → entity   （"各框架的解法"中每个仓库的来源链接）
overview → entity  （仓库总览的子系统列表）
```

Obsidian Graph View 里看到的就是这个 wikilink 网络。`/query` 的结构性问题（"改 X 会波及哪些"）顺着 entity → concept → entity 的路径走一圈就回答了。

**关键原则**："Wikilink 有语义。每个 wikilink 从'这里在提到什么，那个东西有独立页面'出发，不是为凑图而加。"

### 2.2 反向链接的回补机制

**问题**：Concept 页有 `来源：[[repos/<name>/entities/<slug>]]`，从 concept 能走到 entity。但从 entity 往回走呢？

**解决**：Step 4 的**后置动作**——写完 concept 页后，自动到每个来源 entity 页末尾追加反向链接。注意一个 entity 可能关联多个 concept（如 MemoryManager 同时涉及 memory-backend-replaceability 和 state-synchronization），用列表追加而非覆盖。

### 2.3 Wikipedia 风格的重定向页

**Merge 的特殊处理**：被合并的 Concept 页不删除，改写为重定向页：

```yaml
---
redirect_to: <slug-B>
reason: <一句话>
date: <YYYY-MM-DD>
---
```

类比 Wikipedia：旧页面保留，告诉来的读者"你要找的内容在这里"。已有 wikilink 不会断。

---

## 三、增量更新设计

### 3.1 为什么增量更新是基础设施而非优化

**核心论点**："没有 delta tracking，每次 ingest 全量重读 500 个仓库源码的 token 成本不可接受。"这被写入了 CLAUDE.md 原则 7。

**实现**：`.ingest-state.json`（SHA-256 content hash + entity→file 逆向映射）

### 3.2 快照文件放哪：为什么不能放在源码目录

**争论点**：最初快照文件路径写的是 `<源码路径>/.ingest-state.json`。

**被纠正**：源码目录不可变（CLAUDE.md 原则："Raw Sources → 代码仓库（不可变，LLM 只读）"）。把管理文件写进别人的仓库污染了源码，违背只读原则。

**最终位置**：`wiki/repos/<name>/.ingest-state.json`——在 wiki 项目自己的目录下，与 `entities/`、`overview.md` 同级。

**额外考虑**：加了 `source_path` 字段记录源码目录路径。用户移动仓库位置后，路径变了也触发全量 re-ingest。

### 3.3 文件→Entity 的逆向映射

**设计**：`.ingest-state.json` 中的 `entity_map` 记录 `{entity-slug: [file-path, ...]}`。变更检测时逆向映射：哪些文件变了 → 哪些 entity 受影响 → 只重提取这些 entity。

**数据来源**：从 Entity 页 frontmatter 的 `source_files` 字段提取。这也是为什么 `source_files` 被设为必填字段（`/lint` 会检查）。

---

## 四、维护文件设计

### 4.1 三个维护文件的职责分离

| 文件 | 角色 | 写模式 | 谁写 |
|------|------|--------|------|
| `wiki/index.md` | 路由页，`/query` Level 1 的入口 | 增量更新各节 | ingest/compare/query/evolve 各自维护对应节 |
| `wiki/log.md` | 审计日志，不可修改 | 只追加 | 每次操作后追加一行 |
| `wiki/hot.md` | 快速恢复上下文 | 覆盖写入 | ingest/evolve 完成后刷新 |

**设计原则**：index.md 不列全部 content/view/insight——500 个 concept 时仍然 < 600 行。LLM 读 index.md 后沿 wikilink 做语义路由。搜索靠 frontmatter + grep，不靠全量列表。（CLAUDE.md 原则 4）

### 4.2 index.md 的 Repos 节不设单一 Category

**旧设计**：`<类别>` 列。**被纠正**：CLAUDE.md 原则 12 规定"仓库用 GitHub topics 做多标签，不设单一 category"。

**最终格式**：`topics: ai-agent, python, event-driven`

### 4.3 hot.md 的维护规则

每次 ingest / evolve 完成后覆盖写入。compare / query 存档后也可更新 Last operation，但 Pending evolve signals 数保持不变。

---

## 五、Skill 设计

### 5.1 五个 Skill 的职责边界

| Skill | 职责 | 一句话 |
|-------|------|--------|
| `/ingest` | 从源码到 wiki | Entity 提取 → 问题空间映射 → Concept 写作 |
| `/query` | 回答问题 | wikilink 遍历 + 检索升级链 + insight 存档 |
| `/compare` | 多仓库对比 | Concept → Entity → 源码 三级升级链 |
| `/lint` | 健康检查 | wikilink 完整性 + frontmatter 合规 + 演化记录 |
| `/evolve-apply` | Wikipedia 演化 | merge / split / redirect，前置判断 + 用户确认 |

**原则**（CLAUDE.md 原则 10）："Skill 是 LLM 的能力，不只是用户要记的命令。各 skill 职责独立，不互相合并。"

### 5.2 对比升级链（Compare Escalation Chain）

**设计**：和 `/query` 的检索升级链同构——从便宜到贵：

```
Level 1 → Concept 页对比表（预计算，直接展示）
  ↓ 无覆盖
Level 2 → Entity 页（同一类 problem 字段的 entity 对比）
  ↓ 无覆盖
Level 3 → 源码（按关键词现场分析，最贵）
```

每级输出必须标注信息来源（Concept / Entity / 源码）。Level 3 读源码前先告知用户估算范围并确认。

### 5.3 `/evolve-apply` 的前置判断

**为什么需要**：演化信号是在 ingest 过程中产生的——当时 LLM 的上下文有限。到实际执行时，wiki 状态可能已经变了（用户手动改过、别的 ingest 更新过、之前的 evolve 操作改变了结构）。每个操作在执行前必须重新检查条件是否成立。

**三种操作的前置判断**：
- **Merge**：子维度关系 + 不会损失独立讨论价值 + 目标页覆盖被合并页的所有关切
- **Split**：子议题 ≥2 个仓库不同方案 + 方案间有真实 trade-off + 独立后能通过 ①②③
- **Redirect**：目标页存在

`--skip-check` 允许跳过前置判断，但需要二次警告确认。

### 5.4 Skill 之间的操作传递

**讨论**：Skill 之间如何衔接？比如用户在 `/compare` 中发现了 concept 结构问题，怎么触发 `/evolve-apply`？

**过度设计的陷阱**：最初在三个 skill 的 SKILL.md 里都写了"嵌套调用"说明文档——"用户在 skill A 中说 X，LLM 暂停 A、执行 evolve、回到 A"。

**被纠正**：Claude Code 的 Skill 工具 + system prompt 已经自动处理 skill 匹配。用户说什么，匹配到哪个 skill，就加载哪个。上一个 skill 的状态还在上下文里，LLM 自然衔接。不需要在 SKILL.md 里写"嵌套调用文档"。

**但需要保留**：`wiki/log.md` 的触发来源记录格式——`[触发: /compare 对话中]`——这是跨 skill 协作时需要统一遵守的数据格式，让审计日志可追溯。

### 5.5 意图识别表的删除

**讨论过的冗余**："用户说什么 → 识别为什么 → 执行什么"的三列表格。

**结论**：这是框架层面的事。Claude Code 根据 `## Trigger` 和 system prompt 自动完成 skill 匹配。在 SKILL.md 里写"意图识别表"是过度设计。只保留干净的 `## Trigger` 部分即可。

---

## 六、Frontmatter 设计

### 6.1 为模型扫描优化

**设计原则**（CLAUDE.md 原则 13）：Frontmatter 为模型设计。模型读前 10 行即可判断文件类型和内容，不必读全文。

**Entity frontmatter**：
```yaml
type: entity
repo: <name>
slug: <slug>
problem: <问题层，"如何..."形式>
generated: <YYYY-MM-DD>
source_files:
  - <repo-relative-path>
```

**Concept frontmatter**：
```yaml
type: concept
concept: <slug>
problem: <核心问题，一句话>
concerns: [<关切1>, <关切2>]
repos: [<仓库列表>]
generated: <YYYY-MM-DD>
```

**关键字段**：`type` 让模型知道这是什么类型的页面。`problem` 让 `/query` Level 1 扫描时直接判断相关性。`repos` 让 `/compare` 快速匹配覆盖仓库。

### 6.2 `source_files` 的双重用途

1. **lint 检查**：entity 必须声明来源文件（完整性）
2. **增量检测**：entity_map 的数据来源（见 3.3）

### 6.3 `concerns` 的格式统一

**最初有两种写法**：inline `[a, b]` 和 block list。**统一为** inline——与 CLAUDE.md 的格式规范一致，`/lint` 的 frontmatter 解析也只需要处理一种格式。

---

## 七、多仓库并行

### 7.1 并行 vs 串行的分界线

**原则**（CLAUDE.md 原则 9）："是否需要跨仓库信息"
- Step 1（Entity 提取）：只看单仓库源码 → 可并行
- Step 2（问题空间映射）：只看单仓库 entity 页 → 可并行
- Step 3（问题空间匹配）：需要对比其他仓库 → 必须等全部 Step 2 完成

### 7.2 批量 ingest 的暂停点处理

多仓库并行时，暂停点仍然在每个仓库的 Step 2 和 Step 3 之后。但 Step 3 需要等所有仓库的 Step 2 完成才能统一执行——因为此时才有跨仓库对比数据，才有 A/B/D 类分类。

---

## 八、被反复纠正的设计错误

这些是用户多次指出、最终写入 CLAUDE.md 作为原则的问题：

| # | 错误 | 纠正 | CLAUDE.md 原则 |
|---|------|------|---------------|
| 1 | 用"当前只有 3 个仓库所以简单方案够用"论证设计决策 | 每个决策必须回答"500 个仓库还能工作吗？" | 原则 1：规模假设 |
| 2 | 建议合并 `/evolve-apply` 进 `/ingest` 以减少命令数 | Skill 职责由功能决定，不由数据量决定 | 原则 10：Skill 独立 |
| 3 | 把 `.ingest-state.json` 放在源码目录下 | wiki 项目自己的目录，不污染源码 | 原则 7：增量更新 |
| 4 | 用 grep 全文扫描做语义搜索 | index.md 路由 → wikilink 遍历 → frontmatter 定位 → LLM 判断相关性 | 原则 8：搜索 |
| 5 | 在 SKILL.md 里写"意图识别表"和"嵌套调用"文档 | 框架自动处理，不需要手动写路由逻辑 | （本文第五节） |
| 6 | index.md 用单一 `<类别>` 列 | GitHub topics 做多标签 | 原则 12 |
| 7 | Entity frontmatter 缺 `source_files` | 增量检测必须依赖，补回 | 原则 7 |
| 8 | Concept `concerns` 用 block list | 统一 inline 格式，与 CLAUDE.md 一致 | 原则 13 |

---

## 九、项目亮点

可对外讲的：

1. **"Wikilink 网络就是图"**——不维护单独的结构化图谱，三类 wikilink（entity↔entity, entity→concept, concept→entity）各自有明确的语义。Obsidian Graph View 直接可视化。

2. **"从问题出发，不从分类出发"**——Entity 的"问题层"是翻译桥梁，Concept 是汇聚点。不是给模块贴标签然后按标签分类，而是让 LLM 发现"这些不同的模块其实在回答同一个问题"。

3. **Four Criteria 作为 Concept 的质量门槛**——三条硬门槛（多方案 + 独立设计空间 + 持续 Trade-off）确保每个 Concept 页都有真实的跨仓库对比价值。四条准则来自 GPT + DeepSeek 两轮概念讨论的反复验证。

4. **Wikipedia 风格的知识演化**——merge/split/redirect 不是一次性提取完美 concept，是靠有规则的持续演化。前置判断机制防止演化操作的级联错误。

5. **对比升级链**——Concept → Entity → 源码三级，从便宜到贵，只在上一级无法满足时才升级。和 `/query` 的检索升级链同构设计。

6. **增量更新作为基础设施**——per-repo SHA-256 快照 + 文件→entity 逆向映射，500 个仓库 re-ingest 不需要全量重读。

7. **Frontmatter 为模型设计**——模型读前 10 行就能判断文件类型、问题域、覆盖仓库，不需要读全文。

8. **Skill 调用模型**——不是命令驱动的工具集合，而是 LLM 根据自然语言自动路由的能力矩阵。同时保持 Skill 间职责独立。

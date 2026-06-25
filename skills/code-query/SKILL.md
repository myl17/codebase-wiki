# /query — Knowledge Query

Answer questions using the wiki knowledge base. Follow the retrieval escalation chain — start cheap, escalate only as needed.

## Trigger

```
/query <question>
/query --repo react,vue <question>
```

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

## Retrieval Escalation Chain

Follow in order. Stop at the level that gives a confident answer.

### Level 1 — Index Scan (cheapest)
Read `wiki/index.md`. Do any listed pages match the question topic? If yes, proceed to Level 2 on those pages. If no relevant pages found, proceed to Level 3.

### Level 2 — Grep Targeted Sections
Use grep or keyword search to find paragraphs in candidate pages matching key terms from the question. Find specific `^[file:line]` provenance references. Can the question be answered now? If yes, synthesize. If no, proceed to Level 3.

### Level 3 — Full Page Read (most expensive, last resort)
Read the full content of relevant pages. Synthesize a comprehensive answer.

**Never skip levels. Never read full pages when Level 1-2 suffices.**

If `--repo` is specified, only read wiki pages for those repos.

## Answer Format

Provide a clear answer with:
- The main finding
- Key evidence with provenance: `^[file:line]` references from the wiki pages you read
- Confidence level: High / Medium / Low

## Archival Decision (always ask)

After answering, always ask the user:

> **这个分析值得存入 wiki 吗？**
> - A: 不存档（答案已在现有页面，只是汇总）
> - B: 补充现有页面（发现了现有 Entity 页或 Concept 页的补充或修正）
> - C: 新建 Insight 页（综合分析有独立价值）

### If user chooses B:
Append to the relevant Entity page (`wiki/repos/<name>/entities/<slug>.md`)
or Concept page (`wiki/concepts/<slug>.md`) under a `## 补充` section. Append log entry.

### If user chooses C:
Write `wiki/insights/<YYYY-MM-DD>-<slug>.md` with this frontmatter (use single-line JSON arrays):
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
Then write the analysis body. Add wikilinks for each path in `sources:`.
Append to `wiki/log.md`: `[<timestamp>] insight created — <slug>`
Update `wiki/index.md` under `## Insights`.

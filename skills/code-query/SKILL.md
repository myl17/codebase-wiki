# /query — Knowledge Query

Answer questions using the wiki knowledge base. Follow the retrieval escalation chain — start cheap, escalate only as needed.

## Trigger

```
/query <question>
/query --repo react,vue <question>
```

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
> - B: 补充现有维度页（发现了现有页面的补充或修正）
> - C: 新建 Insight 页（综合分析有独立价值）

### If user chooses B:
Append to the relevant dimension page under a `## 补充` section. Append log entry.

### If user chooses C:
Write `wiki/insights/<YYYY-MM-DD>-<slug>.md` with this frontmatter (use single-line JSON arrays):
```yaml
---
title: <descriptive title>
type: insight
query: "<original question verbatim>"
generated: <date>
sources: ["wiki/repos/react/dimensions/architecture.md"]
provenance_repos: ["react"]
dimensions_version: v1.0
---
```
Then write the analysis body. Add wikilinks for each path in `sources:`.
Append to `wiki/log.md`: `[<timestamp>] insight created — <slug>`
Update `wiki/index.md` under `## Insights`.

# /query — Knowledge Query

Answer questions using the wiki knowledge base. Follow the retrieval escalation chain — start cheap, escalate only as needed.

## Trigger

```
/query <question>
/query --repo react,vue <question>
```

## Graph Traversal (check BEFORE the escalation chain for structural questions)

If the question matches any of these patterns, use graph traversal **first**:

- "改 X 会波及什么" / "X 的影响范围" / "impact of changing X"
- "为什么有 X" / "X 为什么存在" / "why does X exist / why designed this way"
- "哪些仓库也有 X" / "which repos implement X" / cross-repo same-pattern questions

### Graph traversal steps

1. Map the concept/component name in the question to a node slug in `wiki/repos/*/nodes/`
   (list the directory if unsure)
2. Run:
   ```bash
   python scripts/graph.py query --wiki wiki --repo <repo> --impact <slug>
   ```
3. For each related node returned, read its node page (`wiki/repos/<repo>/nodes/<slug>.md`)
   — node pages are short; reading all related ones is cheap
4. For cross-repo questions, find the shared Concept in the output (`→ <concept>` suffix),
   then grep other repos' nodes/ for the same `concept:` value
5. Format the answer as a traversal narrative (below)

### Graph traversal output format

```
## 影响发现：<node name>

**直接关联节点**（targets / motivates 边）：

- **<node-id>** [<node_type>, <scope>]
  <one-line description from the node page>
  ^[source from node page]

**决策来源**（motivates 反向追溯）：

- <DesignDecision node>：<why this decision created the queried node>

**跨仓库同模式**（embodies → Concept ← embodies）：

- <other-repo node> also embodies <Concept> — key difference: <difference>

遍历路径：
  <node-id> ←edge─ <related-id> ─edge→ <related-id>
```

If graph.py returns no results or the node cannot be identified, fall through to the
retrieval escalation chain below.

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

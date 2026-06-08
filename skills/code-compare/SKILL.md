# /compare — Cross-Repo Comparison

Generate or refresh a comparison matrix across repos in a category, organized by dimension.

## Trigger

```
/compare --category frontend-frameworks
/compare --category frontend-frameworks --dimension extension-points
/compare --repos react,vue,solid --dimension architecture
```

## Execution Protocol

### Step 1 — Find repos

If `--category` specified: read `.manifest.json` → `categories.<category>` for the list of repos.
If `--repos` specified: use the explicit list.

### Step 2 — Identify dimension(s)

If `--dimension` specified: work on that one dimension.
If not specified: generate a full matrix across all 5 dimensions.

### Step 3 — Read wiki pages (not source code)

First, read `.manifest.json` to get the global `dimensions_version`.

For each repo × dimension combination:
- Read `wiki/repos/<repo>/dimensions/<dimension>.md`
- If the file doesn't exist: record `— (未分析)` for that cell
- Compare the page's frontmatter `dimensions_version` against the manifest's global `dimensions_version`. If they differ, the page is stale — record content but mark cell with `⚠️ stale`

Do NOT rely on frontmatter `status: stale` — that field is never written. Staleness is always derived from the manifest version comparison.

Do NOT re-read source code. The comparison reads wiki pages only.

### Step 4 — Generate comparison matrix

For a category × dimension view, output a markdown table:

```markdown
| | React | Vue | Solid |
|---|---|---|---|
| **Architecture** | ... | ... | ... |
| **Extension Points** | ... ⚠️ | ... | — (未分析) |
```

For a repos × single-dimension view, write prose comparing the specific dimension across repos, with cross-repo wikilinks.

### Step 5 — Write to wiki/views/

For category view: `wiki/views/categories/<category>.md`
For dimension view: `wiki/views/dimensions/<dimension>.md`

Page frontmatter (use a single-line JSON array for `sources` so the simple key:value parser in lint.py can read it):
```yaml
---
type: view
category: <category>
dimension: <dimension>
generated: <date>
sources: ["wiki/repos/react/dimensions/architecture.md","wiki/repos/vue/dimensions/architecture.md"]
---
```

Each repo name in the matrix must link to its overview: `[[react/overview]]`.

### Step 6 — Update wiki/index.md and wiki/log.md

Add entry under `## Views` in `wiki/index.md`.
Append to `wiki/log.md`.

### Step 7 — Ask about insight archival

> **这个对比分析值得存为 insight 吗？**

If yes: write `wiki/insights/<date>-<slug>.md` (same format as /query).

# Wiki Maintenance Rules

These rules apply to ALL LLM operations that write to the `wiki/` directory.

## Double-Link Rules

| Situation | Action |
|-----------|--------|
| Dimension page mentions another repo's same dimension | ✅ Build `[[vue/dimensions/extension-points]]` |
| overview points to its own dimension pages | ✅ Build `[[react/dimensions/architecture]]` |
| insight page points to source dimension pages | ✅ Build wikilinks for every path in `sources:` frontmatter |
| views/ compare page links each repo | ✅ Link each repo name to its `overview.md` |
| Inside a code block (``` or inline code) | ❌ Never build wikilinks |
| Inside a provenance reference `^[file:line]` | ❌ Keep as plain text |
| 行文中提到架构模式（如事件驱动、分层架构、插件注册表） | ✅ 用 `[[概念名]]` 内联标记，例：`[[事件驱动]]` |
| 行文中提到技术栈（如 Python asyncio、TypeScript monorepo） | ✅ 用 `[[概念名]]` 内联标记，例：`[[TypeScript monorepo]]` |
| 行文中提到领域概念（如 Context 压缩、Memory Provider） | ✅ 用 `[[概念名]]` 内联标记，例：`[[Context 压缩]]` |
| 具体类名、函数名、文件路径 | ❌ 不标 entity wikilink，保持纯文本 |
| Associative concept that "might be related" | ❌ Only build links that are definitively meaningful |

## Required Page Sections

Every `wiki/repos/<name>/dimensions/<dim>.md` page must end with:

```
## 关联

- [[<same-category-repo>/dimensions/<dim>]]   (for each other repo in same category)
```

Every `wiki/repos/<name>/overview.md` must link to each of its dimension pages.

Entity wikilink 规则：dimension 页正文中，凡属于架构模式/技术栈/领域概念的词汇，首次出现时用 `[[概念名]]` 标记。同一概念在同一页面只标一次（首次出现）。overview 页不标 entity wikilink。

## Provenance Format

Every factual claim in a dimension page must end with a provenance reference:

```
React uses a work-loop scheduler that can be interrupted. ^[packages/scheduler/src/forks/Scheduler.js:147-203]
```

Format: `^[<relative-path-from-repo-root>:<line-start>-<line-end>]`

Pages without any provenance references trigger `[WARN] check_missing_provenance` in lint.

## Frontmatter (required on every wiki/repos/ page)

```yaml
---
repo: react
dimension: architecture        # or "overview"
dimensions_version: v1.0       # version of schema/dimensions.md at write time
generated: 2026-06-08
---
```

Note: there is no `status` field. Staleness is computed at query time by comparing `dimensions_version` in the page against the global value in `.manifest.json`. Never write `status: stale` — it creates a manual field that goes out of sync.

## Log Entries

After every `/analyze`, `/query` (if archived), `/compare`, append to `wiki/log.md`:

```
[2026-06-08T14:23:00Z] analyze react — dimensions: architecture, extension-points
[2026-06-08T15:01:00Z] compare frontend-frameworks — dimension: extension-points
```

## wiki/hot.md

After every operation, overwrite `wiki/hot.md` with:

```markdown
# Hot Context

**Active repos:** react, vue  
**Last operation:** analyze react — 2 dimensions completed (architecture, extension-points), 3 pending  
**Stale dimensions:** 0
```

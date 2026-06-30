# Wiki Maintenance Rules

These rules apply to ALL LLM operations that write to the `wiki/` directory.

## One-Time Setup

When using this vault for the first time, complete the following one-time configuration in Obsidian (auto-saved on exit, permanent):

**1. Exclude maintenance files** (Settings → Files & Links → Excluded files, one per line):

```
hot.md
log.md
index.md
.ingest-state.json
```

**2. Color groups** (Graph View → Gear → Groups, create 2 groups):

| Query | Color | Maps to |
|-------|-------|---------|
| `path:repos` | 🟠 Orange | Repo overviews / Entities |
| `path:concepts` | 🔵 Blue | Concepts |

## Double-Link Rules

| Situation | Action |
|-----------|--------|
| Entity page mentions same-repo entity | ✅ Build `[[entities/<slug>]]` |
| Entity page mentions associated Concept | ✅ Build `[[concepts/<slug>]]` (in the end-of-file `**Associated Concepts**` list) |
| Concept page cites source entity | ✅ Build `[[repos/<name>/entities/<slug>]]` |
| Overview page points to entity | ✅ Build `[[repos/<name>/entities/<slug>]]` |
| Inside a code block (``` or inline code) | ❌ Never build wikilinks |
| Inside a provenance reference `^[file:line]` | ❌ Keep as plain text |
| Concrete class names, function names, file paths | ❌ Don't wikilink; keep as plain text |
| Associative concept that "might be related" | ❌ Only build links that are definitively meaningful |

## Provenance Format

Every factual claim must end with a provenance reference:

```
React uses a work-loop scheduler that can be interrupted. ^[packages/scheduler/src/forks/Scheduler.js:147-203]
```

Format: `^[<relative-path-from-repo-root>:<line-start>-<line-end>]`

Pages without any provenance references trigger `[WARN] check_missing_provenance` in lint.

## Frontmatter

Entity pages (`wiki/repos/<name>/entities/<slug>.md`):
```yaml
---
type: entity
repo: <name>
slug: <slug>
problem: <one-sentence problem description, "how to..." form>
generated: <YYYY-MM-DD>
source_files:
  - <repo-relative-path>
---
```

Concept pages (`wiki/concepts/<slug>.md`):
```yaml
---
type: concept
concept: <slug>
problem: <core problem, one sentence>
concerns: [<concern1>, <concern2>]
repos: [<repo-list>]
generated: <YYYY-MM-DD>
---
```

## Log Entries

After every `/ingest`, `/query` (if archived), `/compare`, append to `wiki/log.md`:

```
[2026-06-25T14:23:00Z] ingest hermes-agent — 8 entities, 3 concepts updated/created
[2026-06-25T15:01:00Z] compare hermes-agent, openclaw — concept: tool-execution-safety
```

## wiki/hot.md

After every operation, overwrite `wiki/hot.md` with:

```markdown
# Hot Context

**Last operation:** ingest <repo-name> — <Entity count> entities, <Concept count> concepts
**Active repos:** <comma-separated>
**Concept pages:** <N>
**Pending evolve signals:** <K> (evolve-signals/)
```

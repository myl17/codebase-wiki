# Wiki Maintenance Rules

These rules apply to ALL LLM operations that write to the `wiki/` directory.

## One-Time Setup

首次使用本 vault 时，在 Obsidian 中完成以下一次性配置（退出时自动保存，永久生效）：

**1. 排除维护文件**（Settings → Files & Links → Excluded files，一行一个）：

```
hot.md
log.md
index.md
.ingest-state.json
```

**2. 颜色分组**（Graph View → 齿轮 → Groups，创建 2 个分组）：

| Query | 颜色 | 对应 |
|-------|------|------|
| `path:repos` | 🟠 橙 | 仓库概览 / Entity |
| `path:concepts` | 🔵 蓝 | Concept |

## Double-Link Rules

| Situation | Action |
|-----------|--------|
| Entity 页提到同仓库其他 entity | ✅ Build `[[entities/<slug>]]` |
| Entity 页提到关联 Concept | ✅ Build `[[concepts/<slug>]]`（在末尾 `**关联 Concept**` 列表） |
| Concept 页引用来源 entity | ✅ Build `[[repos/<name>/entities/<slug>]]` |
| overview 页指向 entity | ✅ Build `[[repos/<name>/entities/<slug>]]` |
| Inside a code block (``` or inline code) | ❌ Never build wikilinks |
| Inside a provenance reference `^[file:line]` | ❌ Keep as plain text |
| 具体类名、函数名、文件路径 | ❌ 不标 wikilink，保持纯文本 |
| Associative concept that "might be related" | ❌ Only build links that are definitively meaningful |

## Provenance Format

Every factual claim must end with a provenance reference:

```
React uses a work-loop scheduler that can be interrupted. ^[packages/scheduler/src/forks/Scheduler.js:147-203]
```

Format: `^[<relative-path-from-repo-root>:<line-start>-<line-end>]`

Pages without any provenance references trigger `[WARN] check_missing_provenance` in lint.

## Frontmatter

Entity 页（`wiki/repos/<name>/entities/<slug>.md`）：
```yaml
---
type: entity
repo: <name>
slug: <slug>
problem: <问题层一句话，"如何..."形式>
generated: <YYYY-MM-DD>
source_files:
  - <repo-relative-path>
---
```

Concept 页（`wiki/concepts/<slug>.md`）：
```yaml
---
type: concept
concept: <slug>
problem: <核心问题，一句话>
concerns: [<关切1>, <关切2>]
repos: [<仓库列表>]
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

**Last operation:** ingest <仓库名> — <Entity数量> entities, <Concept数量> concepts
**Active repos:** <逗号分隔>
**Concept pages:** <N>
**Pending evolve signals:** <K>（evolve-signals/）
```

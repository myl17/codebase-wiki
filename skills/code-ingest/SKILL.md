# /analyze — Code Repository Ingest

Analyze a code repository and populate `wiki/repos/<name>/` with structured knowledge extracted per the dimensions schema.

## Trigger

```
/analyze <repo-path>
/analyze <repo-path> --dimensions extension-points,architecture
/analyze <repo-path> --resume
```

## Step-by-Step Protocol

### Step 1 — Run delta.py

```bash
python scripts/delta.py <repo-path> --manifest .manifest.json --repo <repo-name>
```

Parse the JSON output. Split files into three buckets:
- `core` layer files → READ ALL of these now
- `config` layer files → note but don't read yet
- `impl` layer files → note for later, read only as needed per dimension

Tell the user: "I see N files (X core, Y config, Z impl). This is a [brief description from README]. I'll now analyze it per the dimensions schema."

### Step 2 — Initial Understanding

Read all `core` layer files. Form a clear mental model of:
- What this project does
- Its primary programming language and runtime
- Rough architecture shape

Tell the user your initial read and ask if there's a specific dimension they want to start with, or continue sequentially.

### Step 3 — Dimension-by-Dimension Extraction

For each dimension in `schema/dimensions.md` (or the subset specified with `--dimensions`):

1. Read the dimension description from `schema/dimensions.md`
2. Read relevant `impl` files as needed (follow imports, search for keywords)
3. Draft the dimension wiki page in your response
4. Tell the user your findings and ask: "Anything you want me to adjust or go deeper on before I write this?"
5. After user confirmation, write the file to `wiki/repos/<name>/dimensions/<dimension-slug>.md`

**Every factual claim must end with `^[file:line-start-line-end]`.**

Wiki page format:
```yaml
---
repo: <name>
dimension: <slug>
dimensions_version: v1.0
generated: <ISO date>
---
```

Followed by the extracted knowledge.

Followed by:
```markdown
## 关联

- [[<other-repo-in-same-category>/dimensions/<dimension-slug>]]
```
(Only add links to repos that have already been analyzed — do not build broken links.)

### Step 4 — Write overview.md

After all dimensions are done, write `wiki/repos/<name>/overview.md`:
- 2-3 paragraph architectural summary
- Link to each dimension page: `[[react/dimensions/architecture]]`
- Frontmatter with `dimension: overview`

### Step 5 — Update Manifest

First, save the delta output to a temp file (delta was already run in Step 1):

```bash
python scripts/delta.py <repo-path> --manifest .manifest.json --repo <repo-name> > /tmp/delta-<repo-name>.json
```

Then update the manifest with completed/pending dims and the current file hashes:

```bash
python scripts/manifest.py update <repo-name> \
  --completed architecture,extension-points \
  --pending performance-tradeoffs \
  --timestamp <ISO8601-now> \
  --delta-json /tmp/delta-<repo-name>.json \
  --manifest .manifest.json
```

Also run `manifest.py add` first if this is a new repo:
```bash
python scripts/manifest.py add ./raw/repos/<name> --key <name> --category <category> --manifest .manifest.json
```

The `--delta-json` flag merges current file hashes into the manifest so future runs of `delta.py` can detect actual changes incrementally.

### Step 6 — Update wiki/index.md, wiki/log.md, wiki/hot.md

**wiki/index.md** — add entry under `## Repos`:
```markdown
- [[react/overview]] — React — frontend-frameworks — last analyzed: 2026-06-08
```

**wiki/log.md** — append:
```
[<timestamp>] analyze <repo-name> — dimensions: <list>
```

**wiki/hot.md** — overwrite with current active repo and summary (see schema/CLAUDE.md format).

## Resume Mode

With `--resume`: read `dimensions_completed` from manifest and skip those. Start from the first entry in `dimensions_pending`.

## Quality Bar

- No claim without `^[file:line]` provenance
- No wikilinks to files that don't exist yet
- Staged review: user confirms each dimension before it's written

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

### Step 3.5 — Node Extraction (graph layer)

After all dimension pages are written, extract structured nodes into `wiki/repos/<name>/nodes/`.
Follow `schema/graph-schema.md` strictly — extraction and validation are **two separate steps**.

**Extraction (permissive, gather candidates):**

For each identifiable Component / ExtensionPoint / DesignDecision in the dimension pages:
- Component: independent directory + entry file + distinct responsibility
- ExtensionPoint: interface + multiple implementations / register* methods / hook signatures / config schema
- DesignDecision: a "chose X over Y because Z" causal chain in docs/comments/commits

**Validation (strict — a candidate becomes a node page ONLY if it passes ALL three):**

1. **Connectivity**: the node must have at least one edge (`concept` / `concept_candidate` /
   `targets` / `motivated_by` non-empty), OR be a DesignDecision referenced by another
   node's `motivated_by`. Orphan nodes have no traversal value.
2. **Audience question**: the node must directly answer one of —
   "改这里波及什么？" (Component) / "这里怎么扩展？" (ExtensionPoint) / "为什么这样设计？" (DesignDecision).
3. **Deduplication**: the node must not be a property of another node
   (e.g. an exclusive registration slot is a property of its Component, not a separate node).

**Scope assignment (blast-radius test, see schema for full criteria):**

> If this thing were deleted or fully replaced, what is the minimal rewrite unit?

- `system`: on the hot path with no replacement mechanism / constrains ALL instances of an operation class / non-interface-replaceable dependency
- `subsystem`: a bounded capability unit (own directory + registration/config switch + interface-only dependents); deleting it loses one capability, everything else runs
- `component`: a mechanism inside a capability unit (single file/class); deleting it degrades one behavior

Caution: "calls other subsystems" ≠ blast radius. A scheduler calling tasks/agents/channels
is still `subsystem` if deleting it only requires rewriting itself.

**Concept mapping:**

- If the node matches a Concept in `wiki/entities/_index.md` (check names AND aliases), set `concept:`
- If no match but it could be a cross-repo concept, set `concept_candidate: <proposed name>` —
  do NOT add to _index.md without passing the three-question admission test
- If neither, leave both empty only when the node is repo-specific AND has other edges

**Do not extract:**
- Functions, class names, file paths (implementation details)
- Textbook patterns present in every codebase (singleton, lazy-loading, retry)
- Tool/library names visible in package.json without reading code

After writing nodes, verify:
```bash
python scripts/lint.py --wiki wiki --manifest .manifest.json
python scripts/graph.py build --wiki wiki --out wiki/graph/graph.json
```
Fix any `[ERROR] check_graph_*` findings before proceeding to Step 4.

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

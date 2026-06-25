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

**Extraction order** (per `schema/dimensions.md`):
- Architecture MUST be completed first.
- Extension Points MUST be completed second.
- Remaining dimensions (Performance Tradeoffs, Dependency Strategy, Testing Philosophy) in any order.

Phase 2 dimensions MUST use the subsystem inventory from Architecture + Extension Points
as their coverage checklist. For Phase 2 dimensions, iterate through every subsystem in the
inventory — never skip a subsystem without reading its source code first.

For EACH dimension, follow this sub-process:

#### 3a. Exhaustive Exploration → Candidate List

Do NOT draft a wiki page directly. First, output a candidate list. Each item:
```
N. Subsystem — tradeoff/pattern name
   Claim: [one sentence]
   Evidence: ^[file:line-line]
```

After the candidate list, complete a self-review checklist. You MUST list the actual
file paths you read — do not check a box if you haven't read those files:

```
□ Checked every subsystem in the Architecture + Extension Points inventory?
  Files actually read: [list paths]
□ Any source directories not covered?
□ Does every candidate include a clear sacrifice/rationale (not just a mechanism description)?
□ All provenance line numbers are from files actually read (not inferred)?
```

#### 3b. Adversarial Review (Independent Subagent)

Dispatch a separate subagent for review. Use this prompt template:

```
You are a fact-checker. Verify the candidate list below.

## Candidate List
[paste full candidate list from step 3a]

## A. Provenance Verification
For every item, go back to the source repository at [repo-path] and verify the
file:line references:
- ✅ Correct: code at those lines implements the described logic
- ⚠️ Imprecise: lines are offset, or code is only partially related
- ❌ Fabricated: no corresponding logic found

## B. Coverage Completeness
Take the subsystem inventory from Architecture + Extension Points. For each
subsystem, check whether the candidate list covers it. For any uncovered
subsystem: go into its source directory and confirm whether a tradeoff actually
exists there. Report any omissions.

## C. Self-Review Honesty
Check the self-review checklist at the end of the candidate list. Cross-reference
against your findings from Section B. Was the agent honest about which directories
it actually checked?
```

The adversarial review subagent has its own independent context window — it does
NOT share the main agent's context. This is what makes the review effective.

#### 3c. Fix

Receive the adversarial review results. Fix all ⚠️ and ❌ items. Add any
omissions the reviewer found. Each fix must include new source evidence.

#### 3d. User Confirmation → Write

Present the final candidate list to the user. After confirmation, write the
dimension wiki page.

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

**User feedback loop:** If the user says "expand on this section" or "add this direction",
modify the affected items and re-run adversarial review (3b) only on the changed items.

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

**Provenance tracking:**

- Set `extracted_from:` to list the dimension slug(s) this node was extracted from
  (e.g. `extracted_from: [architecture, extension-points]`). This enables `graph.py` to
  write reverse links from dimension pages back to nodes, and gives each node auditability
  — readers can trace a node back to the narrative that produced it.

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
python scripts/graph.py build --wiki wiki --out wiki/graph/graph.json --update-wikilinks
```
Fix any `[ERROR] check_graph_*` findings before proceeding to Step 4.

`--update-wikilinks` 自动为所有 node 页生成 `## 关联` 区块（按边类型分组的 wikilink 网络），
并为 overview.md 嵌入 `## 决策链` Mermaid 图。Obsidian graph view 将不再出现孤点。

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

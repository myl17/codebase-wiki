# V2 Pipeline Validation Experiment -- 2026-06-19

## Purpose

Validate the redesigned V2 entity-concept extraction pipeline against the historical 2026-06-17 baseline. The V2 pipeline introduces three key changes:

1. **Incremental multi-round ingest.** Instead of extracting all three repos in one pass, the pipeline ingests repos one at a time (openclaw, then hermes-agent, then nanobot). Each round carries forward the accumulated seed library and upgrades qualifying entries to cross-repo Concept pages.
2. **Five standardized phases per round.** Phase 1 (design choice extraction) -> Phase 2 (axis positioning) -> Phase 3a (Concept page generation) -> Phase 3b (source verification) -> Phase 3d (seed library merge). The phased structure enforces consistent output format and source traceability at every step.
3. **Mandatory source fidelity.** Every design choice and Concept instance must reference exact file paths with start-end line numbers. Phase 3b explicitly verifies each claim against source code before the entry enters the seed library.

The experiment compares this V2 output against the 2026-06-17 historical results across five dimensions: Concept coverage, classification accuracy, source fidelity, incremental completeness, and format compliance.

## Methodology

### Pipeline phases

Each round executes the same five-phase sequence on a single repository:

| Phase | Output | Description |
|-------|--------|-------------|
| Phase 1 | `phase-1-design-choices.md` | Independent extraction of architecture-level design choices from the repo's dimension narratives and node pages. No cross-repo comparison at this stage. |
| Phase 2 | `phase-2-axis-positioning.md` | Each design choice is positioned on a normalized axis (e.g., "同步串行 Pipeline" for openclaw's tool gating). Prepares entries for cross-repo alignment. |
| Phase 3a | `phase-3a-concepts/*.md` | When two or more repos have entries on the same axis, a Concept page is generated with instance matrix, trade-off analysis, and source references. |
| Phase 3b | `phase-3b-verify/*.md` | Each Concept page's source claims are verified against actual code. File paths, line numbers, and mechanism descriptions are cross-checked. |
| Phase 3d | `phase-3d-seed-library.md` | The merged seed library: all design choices from all repos accumulated so far, with upgrade status (pending vs upgraded to Concept), cross-references, and reverse-check annotations. |

### Round schedule

| Round | Repo ingested | Accumulated repos |
|-------|--------------|-------------------|
| Round 1 | openclaw | openclaw |
| Round 2 | hermes-agent | openclaw + hermes-agent |
| Round 3 | nanobot | openclaw + hermes-agent + nanobot |

Phases 3a and 3b only run starting from Round 2 (need at least two repos for cross-repo Concept generation). Phase 3c (fixes after verification) and the comparison report are produced after all rounds complete.

## Round-by-round results

### Round 1 -- openclaw only

- **Input:** openclaw's 5 dimension narratives + 17 node pages
- **Phase 1:** 22 design choices extracted independently
- **Seed library:** 22 entries, all status "仅 openclaw -- 待观察" (single-repo, pending second repo for Concept upgrade)
- **Concepts generated:** 0 (single repo, no cross-repo comparison possible)

### Round 2 -- hermes-agent added

- **Input:** openclaw seed library (22 entries) + hermes-agent's 5 dimension narratives + 12 node pages
- **Phase 1:** 21 new design choices extracted from hermes-agent
- **Seed library:** 44 entries total -- 12 upgraded to Concept, 11 openclaw-only pending, 21 hermes-agent-only pending
- **Phase 3a:** 12 complete Concept pages generated, each with instance matrix and source references
- **Phase 3b:** All 12 Concept pages verified against source code

The 12 Concept pages cover: tool-security-gating, approval-blocking-mechanism, proactive-trigger-path (seed only), context-window-overflow-guard, compression-resource-allocation, prompt-cache-boundary, memory-retrieval-timing, context-engine-pluggability, lifecycle-hook-granularity, global-capability-coexistence, im-platform-adapter-granularity, optional-dependency-layering, dependency-version-locking.

### Round 3 -- nanobot added

- **Input:** Round 2 seed library (44 entries) + nanobot's 5 dimension narratives
- **Phase 1:** 14 new design choices extracted from nanobot
- **Seed library:** 58 entries total -- 19 upgraded to Concept, 8 openclaw-only pending, 18 hermes-agent-only pending, 13 nanobot-only pending
- **New Concept axes identified:** 7 additional axes involving nanobot (proactive-trigger-path, agent-scheduling-mechanism, tool-discovery-mechanism, mcp-integration-pattern, llm-api-sdk-strategy, channel-sdk-isolation, plus one more). These exist as seed library entries with all three repos' instances; full Concept pages pending round 4 generation.
- **Phase 3a/3b:** Not yet executed for the 7 nanobot-involving Concepts (Concept pages from round 2 do not yet contain nanobot instances).

### Cumulative metrics

| Metric | Round 1 | Round 2 | Round 3 |
|--------|---------|---------|---------|
| Design choices (seed library) | 22 | 44 | 58 |
| Upgraded to Concept | 0 | 12 | 19 |
| Single-repo pending | 22 | 32 | 39 |
| Complete Concept pages | 0 | 12 | 12 |
| Verified Concept pages | 0 | 12 | 12 |

Note: The 7 additional Concepts identified in Round 3 have seed library entries with full three-repo instance matrices but await round 4 for complete Concept page generation with source verification.

## Key findings from comparison

The comparison report (`comparison/vs-historical.md`) evaluates V2 results against the 2026-06-17 historical baseline across five dimensions:

### 1. Concept coverage (improved)

- V2: 19 Concept axes (12 with complete pages + 7 with seed library entries), 58 seed library entries
- Historical: 10 Concept pages, ~78 seed library entries
- V2 decomposition granularity is finer: historical results merge multiple sub-problems into coarse Concepts (e.g., context-compression-quality bundled triggering, resource allocation, and governance), while V2 splits them into independent axes (context-window-overflow-guard, compression-resource-allocation, prompt-cache-boundary). This enables more precise cross-repo comparison positions.

### 2. Classification accuracy (improved)

- V2 axis definitions are more precise. Each Concept title explicitly names the trade-off dimension (e.g., "统一管道还是分层可调节" vs historical's generic "dangerous-operation-prevention").
- nanobot is correctly positioned as an infrastructure-level security philosophy (isolation at OS/network/filesystem layer), distinct from openclaw/hermes's operation-level approval gating. This is a dimension the historical results missed entirely.

### 3. Source fidelity (significantly improved)

| Indicator | V2 | Historical |
|-----------|----|------------|
| File path + line number coverage | 12/12 Concepts (100%) | ~6/10 Concepts (60%) |
| Line number precision | Exact start-end ranges | Mixed: some exact, some estimated |
| Code snippet embedding | Common (source block citations) | Rare |
| Verifiability | Every key claim traceable to source line | Medium: some claims rely on project terminology alone |

V2 achieves the standard that every key mechanism description has a verifiable method name + exact line numbers. Historical results suffer from "line number fabrication" risk in places (e.g., `runner.py:89-320` as an estimated range) and inconsistent source referencing across Concepts.

### 4. Incremental completeness (good)

- Seed library level: Every design entry fully preserves existing repo descriptions, traceability, and cross-references when a new repo is appended. No description was overwritten or degraded across rounds.
- Concept page level: Round 2 Concept pages contain complete openclaw + hermes-agent instance matrices. nanobot instances are organized in the seed library and await subsequent round ingestion into corresponding Concept pages.

### 5. Format compliance (significantly improved)

| Metric | V2 | Historical |
|--------|----|------------|
| "如何..." question format | 58/58 seed entries, 12/12 Concepts (100%) | ~45/78 seed entries (~58%), 5/10 Concepts (50%) |
| `{domain}-{dimension}` slug format | 12/12 Concepts (100%) | 10/10 Concepts (100%) |
| Consistent frontmatter | All Concepts | None |
| Standardized page structure | All Concepts | Inconsistent |

Historical results had half of their Concept pages starting with English or declarative sentences instead of the standardized "如何..." question format. V2 enforces this uniformly.

## Directory structure

```
v2-validation-2026-06-19/
├── README.md                          # This file
├── comparison/
│   └── vs-historical.md               # Detailed five-dimension comparison vs 2026-06-17 baseline
├── round-1-openclaw/
│   ├── phase-1-design-choices.md      # 22 design choices extracted from openclaw
│   ├── phase-2-axis-positioning.md    # Axis positioning for each choice
│   ├── phase-3a-concepts/             # Empty (single repo, no cross-repo Concepts)
│   ├── phase-3b-verify/               # Empty
│   ├── phase-3c-fixed/                # Empty
│   └── phase-3d-seed-library.md       # 22 entries, all openclaw-only pending
├── round-2-hermes/
│   ├── phase-1-design-choices.md      # 21 design choices extracted from hermes-agent
│   ├── phase-2-axis-positioning.md    # Cross-repo axis alignment
│   ├── phase-3a-concepts/             # 12 Concept pages (openclaw + hermes-agent)
│   │   ├── approval-blocking-mechanism.md
│   │   ├── compression-resource-allocation.md
│   │   ├── context-engine-pluggability.md
│   │   ├── context-window-overflow-guard.md
│   │   ├── dependency-version-locking.md
│   │   ├── global-capability-coexistence.md
│   │   ├── im-platform-adapter-granularity.md
│   │   ├── lifecycle-hook-granularity.md
│   │   ├── memory-retrieval-timing.md
│   │   ├── optional-dependency-layering.md
│   │   ├── prompt-cache-boundary.md
│   │   └── tool-security-gating.md
│   ├── phase-3b-verify/               # 12 verification reports (one per Concept)
│   │   └── ...verify.md
│   ├── phase-3c-fixed/                # Empty
│   └── phase-3d-seed-library.md       # 44 entries: 12 Concept, 11 openclaw, 21 hermes
└── round-3-nanobot/
    ├── phase-1-design-choices.md      # 14 design choices extracted from nanobot
    ├── phase-2-axis-positioning.md    # Three-repo axis alignment
    ├── phase-3a-concepts/             # Empty (pending round 4 for nanobot-involving Concepts)
    ├── phase-3b-verify/               # Empty
    ├── phase-3c-fixed/                # Empty
    └── phase-3d-seed-library.md       # 58 entries: 19 Concept, 8 openclaw, 18 hermes, 13 nanobot
```

## Next steps

1. **Round 4 -- Concept page completion.** Generate complete Concept pages for the 7 nanobot-involving axes that currently exist only as seed library entries (proactive-trigger-path, agent-scheduling-mechanism, tool-discovery-mechanism, mcp-integration-pattern, llm-api-sdk-strategy, channel-sdk-isolation, and the remaining one). Run phase-3b verification on all.
2. **Backfill nanobot instances.** Add nanobot instances to the 5 shared Concept pages that have nanobot contributions (tool-security-gating, lifecycle-hook-granularity, context-window-overflow-guard, prompt-cache-boundary, optional-dependency-layering).
3. **Production wiki sync.** Once all Concept pages pass phase-3b verification, sync them into `wiki/concept/` and update the seed library into the production wiki structure.

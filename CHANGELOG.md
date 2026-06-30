# Changelog

All notable changes to codebase-wiki will be documented in this file.

## [0.2.0] — 2026-06-30

### Added

- **All skill files translated to English**: 6 commands (~1800 lines) + 2 schema files
- **CI/CD**: GitHub Actions workflow (pytest + lint.py) on push and PR
- **Marketplace submission**: submitted to `kossakovsky/cc-plugins` community marketplace
- **category/tags/keywords** in marketplace.json for cc-plugins compliance

### Changed

- **Plugin structure flattened**: `skills/code-*/SKILL.md` → `commands/*.md` (matches standard plugin layout)
- Removed `.claude/commands/` symlink layer
- Obsolete `.claude/settings.json` removed from tracking

### Fixed

- LICENSE and CONTRIBUTING.md: GitHub username `miaoyuanli` → `myl17`
- `wiki/.obsidian/workspace.json`: removed 25 distractor file references
- `requirements.txt`: removed unused `pyyaml` dependency
- README: Karpathy link fixed to point to original Gist

### Removed

- Demo wiki content (18 concepts, 98 entities) — shipped as clean framework skeleton

## [0.1.0] — 2026-06-29

### Initial Public Release

First public release of the codebase-wiki Claude Code plugin.

#### Core Architecture

- **Entity → Problem Space → Concept pipeline**: replace the old fixed five-dimension extraction system
- **Wikilink network**: entity ↔ concept links form the knowledge graph — no separate graph data structure
- **Evolution layer**: Wikipedia-style merge / split / redirect for concept pages
- **Incremental re-ingest**: SHA-256 content hashing via `.ingest-state.json` for delta detection
- **Quality gate**: mandatory `/completion-gate` validation before any write operation completes

#### Skills (6)

| Skill | Description |
|-------|-------------|
| `/ingest` | 6-step pipeline: entity extraction → problem space mapping → concept matching → concept writing → verification → snapshot |
| `/query` | Wikilink traversal + 3-level retrieval escalation (Concept → Entity → Source) |
| `/compare` | Cross-repo comparison with 3-level upgrade chain and knowledge freshness checks |
| `/lint` | Full wiki health: wikilink integrity, frontmatter, repo consistency, orphans, provenance, pipeline file placement |
| `/evolve-apply` | Signal-driven or manual concept evolution: merge, split, redirect |
| `/completion-gate` | Shared quality gate with 4-section non-negotiable checklist |

#### Knowledge Base

- 5 repos ingested: nanobot, hermes-agent, openclaw, deepagents, codex-main
- 98 entity pages
- 18 concept pages covering AI agent framework architecture
- 94 seed candidates awaiting second-repo promotion
- 1 comparison view (hermes-agent vs openclaw)

#### Infrastructure

- `scripts/lint.py`: 6 health checks with 5-strategy wikilink resolution
- `tests/test_lint.py`: 16 pytest tests
- `hooks/session-start.sh`: injects wiki status summary at session start
- `schema/concept-criteria.md`: 4 admission criteria with few-shot examples
- Multi-repo parallel ingest support (Steps 1-2 per-repo, Step 3 cross-repo)
- Scalability validated: Strategy C (layered grep) works at 1018 concept scale

#### Design Decisions

- No separate graph database — wikilinks ARE the graph
- Concept pages are the main knowledge accumulation unit
- `index.md` is a routing page, not a full catalog (scales to 500+ concepts)
- All tests/validation must run in subagents, not main context
- Skills are independent by responsibility, never merged for convenience

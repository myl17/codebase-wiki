# codebase-wiki

> **A growing markdown directory maintained by LLM — not a graph database.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](CHANGELOG.md)

codebase-wiki is a **code knowledge accumulation system** built on the [Karpathy LLM Wiki](https://github.com/karpathy/llm_wiki) pattern, distributed as a [Claude Code](https://claude.ai/code) plugin. Instead of building a separate graph database with a type system, it maintains a **growing directory of markdown files** linked together via `[[wikilinks]]`. The wikilink network **is** the graph — Obsidian Graph View shows it, and the LLM traverses it when answering queries.

Each time you ingest a code repository, the LLM reads the source, extracts structural modules (**Entities**), maps them to cross-repo design questions (**Problem Spaces**), and writes or updates **Concept** pages with comparison tables and evolution records. Knowledge is compiled once and kept fresh — not re-derived on every query.

## Why codebase-wiki?

**For framework builders and developers who study design spaces across multiple codebases.**

- You maintain or study multiple frameworks in the same domain (e.g., AI agent frameworks)
- You want to understand how different codebases solve the same design problems
- You need design rationale, trade-offs, and source evidence — not just API docs
- You want a living knowledge base that grows with each new repo, not one-off analysis

## Architecture

```
Raw Sources    →  Code repositories (immutable, LLM reads only)
The Wiki       →  LLM-owned markdown (wiki/ directory)
The Schema     →  Convention & process rules (schema/ + CLAUDE.md)
The Skills     →  Claude Code skills — the LLM's operating manual (skills/)
```

## Pipeline

```
Source → Entity (locatable module with independent responsibility boundary)
  → Problem Space Mapping (translate single-repo entities into cross-repo "how to..." questions)
  → Concept (cross-repo design space with per-framework solutions + comparison tables)
  → Insights (on-demand: /query archive / /compare archive)

Evolution layer:
  → /evolve-apply (Wikipedia-style merge / split / redirect for Concept pages)
```

## Quick Start

### Prerequisites

- [Claude Code](https://claude.ai/code) (the CLI tool)
- Python 3.10+ (for the `lint.py` health check script)
- [Obsidian](https://obsidian.md/) (optional — for Graph View visualization)

### Installation

1. **Add the marketplace and install:**

   ```
   /plugin marketplace add myl17/codebase-wiki
   /plugin install codebase-wiki@codebase-wiki
   ```

   Or install from a local clone:
   ```bash
   git clone https://github.com/myl17/codebase-wiki.git
   /plugin marketplace add ./codebase-wiki
   /plugin install codebase-wiki@codebase-wiki
   ```

2. **Install Python dependencies** (for lint health checks):
   ```bash
   pip install -r requirements.txt
   ```

### First Ingest

```
/ingest /path/to/your/repo my-repo-name
```

The LLM will:
1. Extract structural **Entities** from the source code
2. Map each entity to a **Problem Space** (cross-repo design question)
3. Match against existing **Concepts** or create new ones
4. Write/update Concept pages with comparison tables, wikilinks, and source provenance

After ingest completes, open the `wiki/` directory in Obsidian to see the knowledge graph.

## Skills

| Skill | What it does | Type |
|-------|-------------|------|
| `/ingest` | Extract entities → map problem spaces → write concept pages | Write |
| `/query` | Answer questions via wikilink traversal + retrieval escalation | Read |
| `/compare` | Cross-repo comparison on concepts: Concept → Entity → Source | Read |
| `/lint` | Full wiki health check: wikilinks, frontmatter, orphans, provenance | Read |
| `/evolve-apply` | Wikipedia-style concept evolution: merge / split / redirect | Write |
| `/completion-gate` | Quality gate — runs automatically before any write operation completes | Gate |

Skills are independent by responsibility, not merged for convenience. Each skill's `SKILL.md` is the LLM's operating manual (currently in Chinese; English translation is planned for v0.2.0).

## Current Knowledge Base

| Metric | Value |
|--------|-------|
| Ingested repos | 5 (nanobot, hermes-agent, openclaw, deepagents, codex-main) |
| Entity pages | 98 |
| Concept pages | 18 |
| Pending evolve signals | 3 |
| Comparison views | 1 |
| Lint status | 0 errors |

**Covered domain:** AI Agent framework architecture patterns (agent loop orchestration, context compression, channel abstraction, session management, system prompt assembly, memory management, tool lifecycle, provider abstraction, subagent orchestration, security, execution approval, skills/plugins, autonomous scheduling, configuration, execution isolation, middleware composition, hooks/events, MCP protocol integration).

## Project Structure

```
codebase-wiki/
├── wiki/                    # The knowledge base (markdown + wikilinks)
│   ├── concepts/            # Cross-repo design space pages
│   ├── repos/               # Per-repo entity pages + overviews
│   ├── views/               # Archived comparison results
│   ├── index.md             # Routing page (entry point for LLM navigation)
│   ├── log.md               # Append-only operation log
│   └── hot.md               # Quick context recovery (last operation, status)
├── skills/                  # Claude Code skills (LLM operating manuals)
│   ├── code-ingest/
│   ├── code-query/
│   ├── code-compare/
│   ├── code-lint/
│   ├── code-evolve/
│   └── code-completion-gate/
├── schema/                  # Conventions & criteria
│   ├── CLAUDE.md            # Wiki maintenance rules
│   └── concept-criteria.md  # Concept admission criteria (4 gates)
├── scripts/
│   └── lint.py              # Wiki health check tool (6 checks)
├── tests/
│   └── test_lint.py         # pytest tests for lint
├── seeds/                   # Candidate problem spaces awaiting second repo
├── evolve-signals/          # Pending concept evolution operations
├── hooks/                   # Claude Code session hooks
├── .claude-plugin/          # Plugin marketplace metadata
├── CLAUDE.md                # Project rules & design principles
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## Design Principles

1. **Scale-first.** Every decision must answer: "Does this still work with 500 repos and 500 concepts?"
2. **The wikilink network is the graph.** No separate graph data structure — wikilinks ARE the edges.
3. **Concept pages are the main battlefield.** Cross-repo knowledge accumulates here — new repos update existing concepts' instance lists and comparison tables.
4. **Incremental update is infrastructure, not optimization.** SHA-256 content hashing via `.ingest-state.json` enables delta detection.
5. **Knowledge freshness is a closed loop.** Any read operation that finds stale data must offer to fix it, then regenerate affected output.
6. **Evolution is built-in.** Concepts are not frozen — Wikipedia-style merge/split/redirect handles drift as more repos arrive.
7. **Skills are independent by function, not current scale.** Each has a distinct responsibility boundary.

## Requirements

- **Claude Code** — the LLM runtime that executes the skills
- **Python 3.10+** — for `scripts/lint.py` health checks
- **Obsidian** (optional) — for visualizing the wikilink graph

## License

MIT © [myl17](https://github.com/myl17)

---

*Inspired by [Andrej Karpathy's LLM Wiki](https://github.com/karpathy/llm_wiki) pattern. Built for the [Claude Code](https://claude.ai/code) ecosystem.*

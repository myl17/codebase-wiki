# codebase-wiki

> **A growing markdown directory maintained by LLM — not a graph database.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](CHANGELOG.md)

codebase-wiki is a [Claude Code](https://claude.ai/code) plugin that turns source code repositories into a **living, cross-referenced knowledge base**. It implements the [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern by Andrej Karpathy — knowledge is compiled at ingest time and continuously maintained, not re-derived per query.

Each time you ingest a repo, the LLM reads the source, extracts structural modules (**Entities**), maps them to cross-repo design questions (**Problem Spaces**), and writes or updates **Concept** pages with comparison tables, wikilinks, and source provenance. The `[[wikilink]]` network **is** the graph — open it in [Obsidian](https://obsidian.md/) and you see the knowledge structure directly.

## What it does

```
Your source repos  →  LLM reads code, extracts structure
                   →  Maps modules to design questions
                   →  Writes & maintains cross-referenced markdown pages
                   →  You browse, query, compare, and evolve the wiki
```

**Not** a vector database. **Not** a graph database. **No** separate graph schema to maintain. Just a directory of markdown files linked by `[[wikilinks]]` that the LLM owns, writes, and keeps fresh.

## Installation

### Prerequisites

- [Claude Code](https://claude.ai/code)
- Python 3.10+ (`pip install -r requirements.txt` — only needed for the `lint` health check)
- [Obsidian](https://obsidian.md/) (optional — for Graph View)

### Install

```
/plugin marketplace add myl17/codebase-wiki
/plugin install codebase-wiki@codebase-wiki
```

Or clone and register locally:

```bash
git clone https://github.com/myl17/codebase-wiki.git
/plugin marketplace add ./codebase-wiki
/plugin install codebase-wiki@codebase-wiki
```

### First ingest

```
/ingest /path/to/your/repo my-repo-name
```

The LLM extracts entities, maps problem spaces, and writes Concept pages. Afterward, open `wiki/` in Obsidian to see the graph. Ingest a second repo in the same domain and it will **update existing Concept pages** with comparisons — this is where the knowledge compounds.

## Skills

| Skill | What it does |
|-------|-------------|
| `/ingest` | Read source code → extract entities → map problem spaces → write/update concept pages |
| `/query` | Answer questions via wikilink traversal + 3-level retrieval escalation |
| `/compare` | Cross-repo comparison: Concept → Entity → Source code |
| `/lint` | Full wiki health check: wikilinks, frontmatter, orphans, provenance, repo consistency |
| `/evolve-apply` | Wikipedia-style concept evolution: merge, split, redirect |
| `/completion-gate` | Quality gate — runs automatically before any write operation completes |

Each skill's `SKILL.md` is the LLM's operating manual (currently in Chinese; English translation planned for v0.2.0).

## How it works

```
Source → Entity (locatable module with independent responsibility boundary)
  → Problem Space Mapping (translate single-repo entities into cross-repo "how to..." questions)
  → Concept (cross-repo design space with per-framework solutions + comparison tables)
  → Insights & Views (on-demand: /query archives, /compare snapshots)

Evolution layer:
  → /evolve-apply (Wikipedia-style merge / split / redirect for Concept pages as more repos arrive)
```

**Key design decisions:**

- **Scale-first.** Every decision answers: "Does this still work with 500 repos and 500 concepts?"
- **Wikilinks are the graph.** No separate graph data structure — `[[wikilinks]]` ARE the edges.
- **Concepts accumulate.** Cross-repo knowledge lives in Concept pages — each new repo updates existing comparisons.
- **Incremental by default.** SHA-256 content hashing (`.ingest-state.json`) skips unchanged entities on re-ingest.
- **Knowledge stays fresh.** Any read that finds stale wiki data must fix it before regenerating output.
- **Evolution built in.** Concepts aren't frozen — merge/split/redirect handles drift as more repos arrive.

## Demo wiki

This repository ships with an example wiki produced by ingesting 5 AI agent frameworks. It's included so you can browse a real knowledge base before running your own ingest:

```
wiki/
├── concepts/           18 cross-framework design pages
│                       (agent-loop, context-compression, tool-lifecycle,
│                        provider-abstraction, security, sandboxing, MCP, …)
├── repos/              5 repos × 98 entity pages
│   ├── nanobot/
│   ├── hermes-agent/
│   ├── openclaw/
│   ├── deepagents/
│   └── codex-main/
└── views/              1 comparison snapshot (hermes-agent vs openclaw)
```

Open `wiki/` in Obsidian with Graph View to see the wikilink network. Delete the demo content and start fresh if you prefer — the plugin works on any codebase.

## Project structure

```
codebase-wiki/
├── skills/              Claude Code skills — the LLM's operating manual
├── schema/              Conventions & criteria the LLM follows
├── wiki/                Where YOUR knowledge base lives
├── scripts/lint.py      Wiki health checker (6 structural checks)
├── tests/test_lint.py   pytest suite
├── hooks/               Claude Code session hooks
└── .claude-plugin/      Marketplace metadata
```

## Requirements

- Claude Code (the runtime)
- Python 3.10+ (for `scripts/lint.py`)
- Obsidian (optional — wikilink graph visualization)

## License

MIT © [myl17](https://github.com/myl17)

---

*Built on the [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern. For the [Claude Code](https://claude.ai/code) ecosystem.*

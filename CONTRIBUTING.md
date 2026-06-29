# Contributing to codebase-wiki

Thanks for your interest in contributing!

## Project Philosophy

codebase-wiki is a **LLM-maintained knowledge base** — the LLM writes everything, humans curate direction. This has implications for contributions:

- **Skill files** (`skills/*/SKILL.md`) are LLM operating manuals written in Chinese. Changes here should be tested with actual ingest/query runs.
- **Schema files** (`schema/`) define conventions the LLM follows. Changes affect all downstream operations.
- **Wiki content** (`wiki/`) is LLM-generated and maintained. Manual edits are discouraged — use `/ingest` and `/evolve-apply` instead.
- **Scripts** (`scripts/`) are human-written tools (Python). Standard code review applies.

## Development Setup

```bash
git clone https://github.com/miaoyuanli/codebase-wiki.git
cd codebase-wiki
pip install -r requirements.txt
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

- Python scripts: follow PEP 8
- Skill files: follow the existing structure in each SKILL.md
- All tests and validation must run in subagents (per project rules)

## Reporting Issues

When reporting bugs, please include:
1. The skill or command that produced the issue
2. Relevant wiki state (concept page content, log entries)
3. Expected vs actual behavior

## Pull Requests

1. Branch from `master`
2. Ensure `pytest tests/` passes
3. Ensure `python scripts/lint.py --wiki wiki/` returns 0 errors
4. Update CHANGELOG.md under `[Unreleased]`

## Language

- User-facing documentation (README, CHANGELOG, CONTRIBUTING): English
- Skill files (LLM instructions): Chinese (English translation planned for v0.2.0)
- Schema files: Chinese with English header comments

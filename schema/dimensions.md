# Codebase Extraction Dimensions

**Version:** v1.0  
**Evolution policy:** First 20 repos — add only, never modify existing dimensions. New dimensions leave existing repos with `status: pending`.

---

## Dimension 1: Architecture

- What are the core abstractions? (component, module, entity, layer)
- Data flow direction? (unidirectional / bidirectional / event-driven)
- How is concern separation achieved? Where are layer boundaries?

**Key files to look at:** README, package entry (index.js / main.rs / __init__.py), any files named `core/`, `architecture`, `design`.

---

## Dimension 2: Extension Points

- Does a plugin system exist? Where is the entry file?
- Where are hooks / middleware / interceptors designed?
- Which layer is the easiest entry point for framework customization?
- Is there an official extension protocol (interfaces / types / conventions)?

**Key files to look at:** Files named `plugin*`, `middleware*`, `hook*`, `extend*`, `register*`.

---

## Dimension 3: Performance Tradeoffs

- What has been optimized? (startup time / runtime perf / memory)
- What has been sacrificed? What is the rationale for that tradeoff?
- Where in the code is the tradeoff visible? (specific file and lines)

**Key files to look at:** Benchmark files, files with names like `scheduler*`, `cache*`, `pool*`, commit messages mentioning perf.

---

## Dimension 4: Dependency Strategy

- Attitude toward external dependencies? (minimize / embrace ecosystem / in-house)
- Replaceability of core dependencies? Is the replacement cost high?
- Are there peer dependency or optional dependency designs?

**Key files to look at:** `package.json`, `go.mod`, `Cargo.toml`, `requirements.txt`, `pyproject.toml`.

---

## Dimension 5: Testing Philosophy

- Ratio of unit / integration / e2e tests?
- Does testing target behavior or implementation details?
- Any specialized test tooling or test conventions?

**Key files to look at:** `__tests__/`, `tests/`, `spec/`, jest/vitest config, CI pipeline definitions.

---

## Adding New Dimensions

Add a new `## Dimension N: <Name>` section here. Bump `dimensions_version` in `.manifest.json` by minor version. For repos already analyzed, `manifest.py` will mark the new dimension as `pending`.

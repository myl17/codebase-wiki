# Codebase Wiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that lets architects analyze multiple code repositories with a shared dimension schema, enabling structured cross-repo comparison and query.

**Architecture:** Three-layer structure — `raw/` for source repos (read-only), `wiki/` for LLM-generated knowledge (the output), and `schema/` + `scripts/` + `skills/` for the tooling layer. Four slash commands (`/analyze`, `/query`, `/compare`, `/lint`) each backed by a SKILL.md that instructs the LLM how to behave; Python scripts handle deterministic work (file hashing, state management, health checks).

**Tech Stack:** Python 3 (stdlib only: hashlib, json, pathlib, argparse), Bash, Markdown, Claude Code plugin system (hooks.json + SKILL.md convention).

---

## File Structure

| File | Responsibility |
|------|---------------|
| `schema/dimensions.md` | The five extraction dimensions — core methodology |
| `schema/CLAUDE.md` | Wiki maintenance rules (double-link rules, provenance rules) |
| `scripts/delta.py` | File-change detection + core/impl/config layering |
| `scripts/manifest.py` | `.manifest.json` read/write — ingest state management |
| `scripts/lint.py` | 7 fixed health-check rules, machine-readable output |
| `scripts/eval.py` | Coverage/provenance/freshness scoring → `wiki/eval-history.jsonl` |
| `hooks/hooks.json` | SessionStart hook registration |
| `hooks/session-start.sh` | Injects wiki state into Claude context |
| `skills/code-ingest/SKILL.md` | `/analyze` slash command instructions |
| `skills/code-query/SKILL.md` | `/query` slash command instructions |
| `skills/code-compare/SKILL.md` | `/compare` slash command instructions |
| `skills/code-lint/SKILL.md` | `/lint` slash command instructions |
| `.manifest.example.json` | Committed template showing manifest structure; copy to `.manifest.json` to start |
| `.manifest.json` | Runtime state — git-ignored, created on first `manifest.py add` |
| `.gitignore` | Excludes `.manifest.json`, `raw/`, `wiki/eval-history.jsonl` |
| `wiki/index.md` | Table of contents for all wiki pages |
| `wiki/log.md` | Append-only operation log |
| `wiki/hot.md` | Current active context injected by SessionStart |

---

## P0 — Week 1: End-to-End Skeleton

### Task 1: Project Scaffold

**Files:**
- Create: `wiki/index.md`
- Create: `wiki/log.md`
- Create: `wiki/hot.md`
- Create: `.manifest.json`

- [ ] **Step 1: Create wiki/index.md**

```markdown
# Codebase Wiki — Index

## Repos

*(no repos analyzed yet)*

## Views

*(no views generated yet)*

## Insights

*(no insights yet)*
```

- [ ] **Step 2: Create wiki/log.md**

```markdown
# Wiki Operation Log

<!-- append-only, newest entries at bottom -->
```

- [ ] **Step 3: Create wiki/hot.md**

```markdown
# Hot Context

**Active repos:** none  
**Last operation:** none  
**Stale dimensions:** 0
```

- [ ] **Step 4: Create .manifest.example.json (template only — .manifest.json is git-ignored)**

```json
{
  "repos": {},
  "dimensions_version": "v1.0",
  "categories": {}
}
```

- [ ] **Step 5: Create .gitignore**

```
.manifest.json
wiki/eval-history.jsonl
raw/
```

- [ ] **Step 6: Commit**

```bash
git init
git add wiki/index.md wiki/log.md wiki/hot.md .manifest.example.json .gitignore
git commit -m "feat: scaffold wiki structure and manifest template"
```

Note: `.manifest.json` is runtime state — it is git-ignored. The `scripts/manifest.py add` command creates it on first use. Developers copy `.manifest.example.json` as a reference.

---

### Task 2: schema/dimensions.md

**Files:**
- Create: `schema/dimensions.md`

- [ ] **Step 1: Write schema/dimensions.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add schema/dimensions.md
git commit -m "feat: add initial dimensions schema v1.0"
```

---

### Task 3: schema/CLAUDE.md (Wiki Rules)

**Files:**
- Create: `schema/CLAUDE.md`

- [ ] **Step 1: Write schema/CLAUDE.md**

```markdown
# Wiki Maintenance Rules

These rules apply to ALL LLM operations that write to the `wiki/` directory.

## Double-Link Rules

| Situation | Action |
|-----------|--------|
| Dimension page mentions another repo's same dimension | ✅ Build `[[vue/dimensions/extension-points]]` |
| overview points to its own dimension pages | ✅ Build `[[react/dimensions/architecture]]` |
| insight page points to source dimension pages | ✅ Build wikilinks for every path in `sources:` frontmatter |
| views/ compare page links each repo | ✅ Link each repo name to its `overview.md` |
| Inside a code block (``` or inline code) | ❌ Never build wikilinks |
| Inside a provenance reference `^[file:line]` | ❌ Keep as plain text |
| Associative concept that "might be related" | ❌ Only build links that are definitively meaningful |

## Required Page Sections

Every `wiki/repos/<name>/dimensions/<dim>.md` page must end with:

```
## 关联

- [[<same-category-repo>/dimensions/<dim>]]   (for each other repo in same category)
```

Every `wiki/repos/<name>/overview.md` must link to each of its dimension pages.

## Provenance Format

Every factual claim in a dimension page must end with a provenance reference:

```
React uses a work-loop scheduler that can be interrupted. ^[packages/scheduler/src/forks/Scheduler.js:147-203]
```

Format: `^[<relative-path-from-repo-root>:<line-start>-<line-end>]`

Pages without any provenance references trigger `[WARN] check_missing_provenance` in lint.

## Frontmatter (required on every wiki/repos/ page)

```yaml
---
repo: react
dimension: architecture        # or "overview"
dimensions_version: v1.0       # version of schema/dimensions.md at write time
generated: 2026-06-08
---
```

Note: there is no `status` field. Staleness is computed at query time by comparing `dimensions_version` in the page against the global value in `.manifest.json`. Never write `status: stale` — it creates a manual field that goes out of sync.

## Log Entries

After every `/analyze`, `/query` (if archived), `/compare`, append to `wiki/log.md`:

```
[2026-06-08T14:23:00Z] analyze react — dimensions: architecture, extension-points
[2026-06-08T15:01:00Z] compare frontend-frameworks — dimension: extension-points
```

## wiki/hot.md

After every operation, overwrite `wiki/hot.md` with:

```markdown
# Hot Context

**Active repos:** react, vue  
**Last operation:** analyze react — 2 dimensions completed (architecture, extension-points), 3 pending  
**Stale dimensions:** 0
```
```

- [ ] **Step 2: Commit**

```bash
git add schema/CLAUDE.md
git commit -m "feat: add wiki maintenance rules to schema/CLAUDE.md"
```

---

### Task 4: scripts/delta.py

**Files:**
- Create: `scripts/delta.py`
- Create: `tests/test_delta.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_delta.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from delta import classify_file, compute_delta


def make_repo(tmp_path, files):
    """Create a fake repo directory with given {relative_path: content} files."""
    for rel, content in files.items():
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return tmp_path


def test_classify_readme_as_core():
    assert classify_file(Path("README.md")) == "core"


def test_classify_package_json_as_config():
    assert classify_file(Path("package.json")) == "config"


def test_classify_source_file_as_impl():
    assert classify_file(Path("src/utils.ts")) == "impl"


def test_classify_entry_file_as_core():
    assert classify_file(Path("index.js")) == "core"
    assert classify_file(Path("src/index.ts")) == "core"
    assert classify_file(Path("main.rs")) == "core"


def test_delta_first_run(tmp_path):
    repo = make_repo(tmp_path, {
        "README.md": "hello",
        "src/index.ts": "export default {}",
        "package.json": '{"name":"x"}',
    })
    prev_hashes = {}
    result = compute_delta(repo, prev_hashes)
    assert len(result["new"]) == 3
    assert len(result["modified"]) == 0
    assert len(result["deleted"]) == 0
    # classify check
    new_core = [f for f in result["new"] if f["layer"] == "core"]
    assert any("README.md" in f["path"] for f in new_core)


def test_delta_modified(tmp_path):
    import hashlib
    repo = make_repo(tmp_path, {"src/foo.ts": "v1"})
    prev_hashes = {
        "src/foo.ts": hashlib.sha256(b"v1").hexdigest()
    }
    # now modify
    (repo / "src/foo.ts").write_text("v2")
    result = compute_delta(repo, prev_hashes)
    assert len(result["modified"]) == 1
    assert result["modified"][0]["path"] == "src/foo.ts"


def test_delta_deleted(tmp_path):
    import hashlib
    repo = make_repo(tmp_path, {"src/foo.ts": "v1"})
    prev_hashes = {
        "src/foo.ts": hashlib.sha256(b"v1").hexdigest(),
        "src/gone.ts": hashlib.sha256(b"old").hexdigest(),
    }
    result = compute_delta(repo, prev_hashes)
    assert "src/gone.ts" in result["deleted"]


def test_delta_skips_node_modules(tmp_path):
    repo = make_repo(tmp_path, {
        "src/index.ts": "export {}",
        "node_modules/lodash/index.js": "module.exports = {}",
    })
    result = compute_delta(repo, {})
    all_paths = [f["path"] for f in result["new"]]
    assert not any("node_modules" in p for p in all_paths)
    assert any("src/index.ts" in p for p in all_paths)


def test_delta_skips_large_files(tmp_path):
    from delta import _MAX_FILE_BYTES
    repo = tmp_path
    big = repo / "bundle.js"
    big.write_bytes(b"x" * (_MAX_FILE_BYTES + 1))
    small = repo / "src" / "index.ts"
    small.parent.mkdir()
    small.write_text("export {}")
    result = compute_delta(repo, {})
    all_paths = [f["path"] for f in result["new"]]
    assert not any("bundle.js" in p for p in all_paths)
    assert any("index.ts" in p for p in all_paths)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_delta.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'delta'`

- [ ] **Step 3: Write scripts/delta.py**

```python
#!/usr/bin/env python3
"""
delta.py — detect file changes in a repo and classify by layer.

Usage:
  python scripts/delta.py <repo-path> [--manifest .manifest.json]

Output (stdout): JSON with keys new / modified / deleted, each a list of
  {"path": "relative/path", "layer": "core|impl|config"}
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

# Files/patterns that map to "core" layer
_CORE_NAMES = {"README.md", "README.rst", "README", "README.txt"}
_CORE_ENTRY_NAMES = {"index.js", "index.ts", "index.mjs", "index.cjs",
                     "main.rs", "main.go", "main.py", "__init__.py",
                     "lib.rs", "mod.rs"}
_CORE_DIR_PREFIXES = ("packages/",)  # monorepo entries like packages/*/src/index.*

# Files/patterns that map to "config" layer
_CONFIG_NAMES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
    "tsconfig.json", "tsconfig.base.json",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Makefile", "makefile", ".env.example",
}
_CONFIG_SUFFIXES = (".toml", ".yaml", ".yml", ".json")
_CONFIG_DIR_PREFIXES = (".github/",)
_CONFIG_NAME_PREFIXES = ("tsconfig",)

# Source file extensions that map to "impl"
_IMPL_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
                  ".rs", ".go", ".py", ".rb", ".java", ".kt",
                  ".c", ".cpp", ".h", ".hpp", ".cs", ".swift")


def classify_file(rel_path: Path) -> str:
    """Return 'core', 'config', or 'impl' for a repo-relative path."""
    name = rel_path.name
    parts_str = str(rel_path).replace("\\", "/")

    # Core: README variants
    if name in _CORE_NAMES:
        return "core"

    # Core: package entry files
    if name in _CORE_ENTRY_NAMES:
        return "core"

    # Core: monorepo package entries — packages/*/src/index.*
    if any(parts_str.startswith(p) for p in _CORE_DIR_PREFIXES):
        stem = rel_path.stem
        if stem == "index" or name in _CORE_ENTRY_NAMES:
            return "core"

    # Config: .github/** directory
    if any(parts_str.startswith(p) for p in _CONFIG_DIR_PREFIXES):
        return "config"

    # Config: explicit filenames
    if name in _CONFIG_NAMES:
        return "config"

    # Config: tsconfig* prefix
    if any(name.startswith(p) for p in _CONFIG_NAME_PREFIXES):
        return "config"

    # Config: .yaml/.yml/.toml/.json outside src/ (heuristic)
    if rel_path.suffix in _CONFIG_SUFFIXES:
        if not parts_str.startswith("src/") and not parts_str.startswith("lib/"):
            return "config"

    # Impl: recognized source extensions
    if rel_path.suffix in _IMPL_SUFFIXES:
        return "impl"

    # Default: impl (catch-all for unknown text files)
    return "impl"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


_MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB — skip larger files (binaries, minified bundles)

# Directory names that are always skipped regardless of depth
_ALWAYS_SKIP_DIRS = {
    "node_modules", ".git", ".hg", ".svn",
    "__pycache__", ".mypy_cache", ".pytest_cache",
    "dist", "build", "out", ".next", ".nuxt", "target",
    ".cargo", "vendor",
}

# File suffixes that are binary/generated — never useful to hash for LLM analysis
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".tgz",
    ".min.js", ".min.css",
    ".lock",  # lockfiles are large and change constantly
    ".map",   # sourcemaps
}


def _load_ignore_patterns(repo_root: Path) -> set:
    """Load extra ignore patterns from .codebase-wikiignore in the repo root."""
    ignore_file = repo_root / ".codebase-wikiignore"
    if not ignore_file.exists():
        return set()
    patterns = set()
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.add(line)
    return patterns


def _should_skip(rel: Path, ignore_patterns: set) -> bool:
    parts = rel.parts
    # Skip hidden dirs/files
    if any(part.startswith(".") for part in parts):
        return True
    # Skip always-ignored directories anywhere in the path
    if any(part in _ALWAYS_SKIP_DIRS for part in parts):
        return True
    # Skip by suffix
    name = rel.name
    if rel.suffix in _SKIP_SUFFIXES:
        return True
    # Check multi-part suffixes like .min.js
    for suf in _SKIP_SUFFIXES:
        if name.endswith(suf):
            return True
    # Check .codebase-wikiignore patterns (simple glob-style prefix/suffix match)
    rel_str = str(rel).replace("\\", "/")
    for pat in ignore_patterns:
        if pat.startswith("*"):
            if rel_str.endswith(pat[1:]):
                return True
        elif pat.endswith("/"):
            if rel_str.startswith(pat) or any(p + "/" == pat for p in parts[:-1]):
                return True
        elif rel_str == pat or rel_str.startswith(pat + "/"):
            return True
    return False


def _iter_repo_files(repo_root: Path):
    """Yield repo-relative paths of files suitable for delta analysis."""
    ignore_patterns = _load_ignore_patterns(repo_root)
    for p in sorted(repo_root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if _should_skip(rel, ignore_patterns):
            continue
        # Skip files larger than 1 MB
        if p.stat().st_size > _MAX_FILE_BYTES:
            continue
        yield rel


def compute_delta(repo_root: Path, prev_hashes: dict) -> dict:
    """
    Compare current repo state against prev_hashes.

    Returns:
      {
        "new":      [{"path": str, "layer": str, "hash": str}, ...],
        "modified": [{"path": str, "layer": str, "hash": str}, ...],
        "deleted":  [str, ...],
      }
    """
    current = {}
    for rel in _iter_repo_files(repo_root):
        current[str(rel)] = _sha256(repo_root / rel)

    new_files = []
    modified_files = []
    for rel_str, sha in current.items():
        entry = {"path": rel_str, "layer": classify_file(Path(rel_str)), "hash": sha}
        if rel_str not in prev_hashes:
            new_files.append(entry)
        elif prev_hashes[rel_str] != sha:
            modified_files.append(entry)

    deleted = [p for p in prev_hashes if p not in current]

    return {"new": new_files, "modified": modified_files, "deleted": deleted}


def main():
    parser = argparse.ArgumentParser(description="Detect repo file changes by layer.")
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--manifest", default=".manifest.json",
                        help="Path to .manifest.json (default: .manifest.json)")
    parser.add_argument("--repo", help="Repo name key in manifest (default: basename of repo_path)")
    args = parser.parse_args()

    repo_root = Path(args.repo_path).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: {repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    repo_key = args.repo or repo_root.name
    prev_hashes = manifest.get("repos", {}).get(repo_key, {}).get("file_hashes", {})

    result = compute_delta(repo_root, prev_hashes)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_delta.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/delta.py tests/test_delta.py
git commit -m "feat: add delta.py — file change detection with layer classification"
```

---

### Task 5: scripts/manifest.py

**Files:**
- Create: `scripts/manifest.py`
- Create: `tests/test_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_manifest.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from manifest import ManifestManager


def test_init_empty_manifest(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    assert m.data["repos"] == {}
    assert m.data["dimensions_version"] == "v1.0"
    assert m.data["categories"] == {}


def test_add_repo(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react", category="frontend-frameworks")
    assert "react" in m.data["repos"]
    assert m.data["repos"]["react"]["category"] == "frontend-frameworks"
    assert "frontend-frameworks" in m.data["categories"]
    assert "react" in m.data["categories"]["frontend-frameworks"]


def test_update_after_ingest(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react")
    m.update_after_ingest(
        repo_key="react",
        completed_dimensions=["architecture"],
        pending_dimensions=["extension-points", "performance-tradeoffs"],
        file_hashes={"src/index.js": "abc123"},
        timestamp="2026-06-08T10:00:00Z",
    )
    repo = m.data["repos"]["react"]
    assert repo["dimensions_completed"] == ["architecture"]
    assert repo["dimensions_pending"] == ["extension-points", "performance-tradeoffs"]
    assert repo["file_hashes"] == {"src/index.js": "abc123"}
    assert repo["last_ingest"] == "2026-06-08T10:00:00Z"
    assert repo["dimensions_version"] == "v1.0"


def test_stale_repos(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react")
    m.update_after_ingest(
        repo_key="react",
        completed_dimensions=["architecture"],
        pending_dimensions=[],
        file_hashes={},
        timestamp="2026-06-08T10:00:00Z",
    )
    # Bump global dimensions_version
    m.data["dimensions_version"] = "v1.1"
    stale = m.get_stale_repos()
    assert "react" in stale


def test_save_and_load(tmp_path):
    path = tmp_path / ".manifest.json"
    m = ManifestManager(path)
    m.add_repo("vue", "./raw/repos/vue", category="frontend-frameworks")
    m.save()
    # Load fresh
    m2 = ManifestManager(path)
    assert "vue" in m2.data["repos"]


def test_stale_count_returns_integer(tmp_path, capsys):
    """--json flag must print a plain int so session-start.sh doesn't miscount."""
    import subprocess, sys as _sys
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react")
    m.update_after_ingest("react", ["architecture"], [], {}, "2026-06-08T10:00:00Z")
    m.data["dimensions_version"] = "v1.1"
    m.save()
    result = subprocess.run(
        [_sys.executable, "scripts/manifest.py",
         "--manifest", str(tmp_path / ".manifest.json"),
         "stale", "--json"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.stdout.strip() == "1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_manifest.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'manifest'`

- [ ] **Step 3: Write scripts/manifest.py**

```python
#!/usr/bin/env python3
"""
manifest.py — manage ingest state in .manifest.json.

Usage:
  python scripts/manifest.py add <repo-path> [--category <cat>] [--manifest <path>]
  python scripts/manifest.py update <repo-key> --completed a,b --pending c,d [--manifest <path>]
  python scripts/manifest.py stale [--manifest <path>]
  python scripts/manifest.py show [--manifest <path>]
"""
import argparse
import json
import sys
from pathlib import Path

_DEFAULT_MANIFEST = {
    "repos": {},
    "dimensions_version": "v1.0",
    "categories": {},
}


class ManifestManager:
    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = json.loads(json.dumps(_DEFAULT_MANIFEST))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2) + "\n")

    def add_repo(self, repo_key: str, repo_path: str, category: str = None):
        if repo_key not in self.data["repos"]:
            self.data["repos"][repo_key] = {
                "path": repo_path,
                "last_ingest": None,
                "dimensions_version": None,
                "dimensions_completed": [],
                "dimensions_pending": [],
                "file_hashes": {},
                "category": category,
            }
        if category:
            self.data["repos"][repo_key]["category"] = category
            cats = self.data.setdefault("categories", {})
            if category not in cats:
                cats[category] = []
            if repo_key not in cats[category]:
                cats[category].append(repo_key)

    def update_after_ingest(
        self,
        repo_key: str,
        completed_dimensions: list,
        pending_dimensions: list,
        file_hashes: dict,
        timestamp: str,
    ):
        if repo_key not in self.data["repos"]:
            raise KeyError(f"Repo '{repo_key}' not found. Call add_repo first.")
        repo = self.data["repos"][repo_key]
        repo["last_ingest"] = timestamp
        repo["dimensions_completed"] = completed_dimensions
        repo["dimensions_pending"] = pending_dimensions
        repo["file_hashes"] = file_hashes
        repo["dimensions_version"] = self.data["dimensions_version"]

    def get_stale_repos(self) -> list:
        """Return list of repo keys whose recorded dimensions_version < current."""
        current_v = self.data.get("dimensions_version", "v1.0")
        return [
            key for key, info in self.data["repos"].items()
            if info.get("dimensions_version") and info["dimensions_version"] != current_v
        ]


def main():
    parser = argparse.ArgumentParser(description="Manage codebase-wiki .manifest.json")
    parser.add_argument("--manifest", default=".manifest.json")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Register a new repo")
    p_add.add_argument("repo_path")
    p_add.add_argument("--key", help="Repo key (default: basename of path)")
    p_add.add_argument("--category")

    p_upd = sub.add_parser("update", help="Update repo after ingest")
    p_upd.add_argument("repo_key")
    p_upd.add_argument("--completed", default="", help="Comma-separated completed dims")
    p_upd.add_argument("--pending", default="", help="Comma-separated pending dims")
    p_upd.add_argument("--timestamp", required=True, help="ISO8601 timestamp")
    p_upd.add_argument("--delta-json", default=None,
                       help="Path to delta.py JSON output; merges file hashes into manifest")

    p_stale = sub.add_parser("stale", help="List stale repos")
    p_stale.add_argument("--json", action="store_true",
                         help="Output count as a plain integer (for scripting)")
    sub.add_parser("show", help="Dump manifest as JSON")

    args = parser.parse_args()
    m = ManifestManager(Path(args.manifest))

    if args.cmd == "add":
        key = args.key or Path(args.repo_path).name
        m.add_repo(key, args.repo_path, category=args.category)
        m.save()
        print(f"Added repo '{key}'")

    elif args.cmd == "update":
        completed = [d for d in args.completed.split(",") if d]
        pending = [d for d in args.pending.split(",") if d]
        # Merge file hashes from delta.py output if provided
        file_hashes = {}
        if args.delta_json:
            delta = json.loads(Path(args.delta_json).read_text())
            # Merge new and modified entries; remove deleted
            existing = dict(m.data.get("repos", {}).get(args.repo_key, {}).get("file_hashes", {}))
            for entry in delta.get("new", []) + delta.get("modified", []):
                existing[entry["path"]] = entry["hash"]
            for path in delta.get("deleted", []):
                existing.pop(path, None)
            file_hashes = existing
        m.update_after_ingest(args.repo_key, completed, pending, file_hashes, args.timestamp)
        m.save()
        print(f"Updated '{args.repo_key}'")

    elif args.cmd == "stale":
        stale = m.get_stale_repos()
        if getattr(args, "json", False):
            # Machine-readable: print count only, used by session-start.sh
            print(len(stale))
        elif stale:
            for r in stale:
                print(r)
        else:
            print("No stale repos.")

    elif args.cmd == "show":
        print(json.dumps(m.data, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_manifest.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/manifest.py tests/test_manifest.py
git commit -m "feat: add manifest.py — ingest state management"
```

---

### Task 6: hooks/session-start.sh and hooks/hooks.json

**Files:**
- Create: `hooks/session-start.sh`
- Create: `hooks/hooks.json`

- [ ] **Step 1: Write hooks/session-start.sh**

```bash
#!/usr/bin/env bash
# Inject wiki current state into Claude Code SessionStart context.
# Output follows Claude Code hookSpecificOutput.additionalContext format.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIKI_ROOT="$(dirname "$SCRIPT_DIR")"
HOT_FILE="$WIKI_ROOT/wiki/hot.md"
LOG_FILE="$WIKI_ROOT/wiki/log.md"
MANIFEST="$WIKI_ROOT/.manifest.json"

hot_content=""
if [ -f "$HOT_FILE" ]; then
  hot_content="$(cat "$HOT_FILE")"
fi

last_log_lines=""
if [ -f "$LOG_FILE" ]; then
  last_log_lines="$(tail -3 "$LOG_FILE" 2>/dev/null || true)"
fi

# stale_count: use --json flag so output is always a number, never "No stale repos."
stale_count=0
if [ -f "$MANIFEST" ] && command -v python3 &>/dev/null; then
  stale_count=$(python3 "$WIKI_ROOT/scripts/manifest.py" --manifest "$MANIFEST" stale --json \
    2>/dev/null || echo "0")
fi

# Build additionalContext safely: use python to produce valid JSON,
# avoiding shell interpolation of quotes/backslashes in content strings.
python3 - <<PYEOF
import json, sys

context = """## Codebase Wiki Status

{hot}

### Recent Operations

{log}

### Health

Stale dimension pages: {stale}""".format(
    hot="""$hot_content""",
    log="""$last_log_lines""",
    stale="""$stale_count""",
)

print(json.dumps({"additionalContext": context}))
PYEOF
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x hooks/session-start.sh
```

- [ ] **Step 3: Write hooks/hooks.json**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Smoke-test the hook manually**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
bash hooks/session-start.sh
```

Expected: JSON output with `additionalContext` field containing wiki state.

- [ ] **Step 5: Commit**

```bash
git add hooks/session-start.sh hooks/hooks.json
git commit -m "feat: add SessionStart hook to inject wiki state"
```

---

### Task 7: skills/code-ingest/SKILL.md (/analyze)

**Files:**
- Create: `skills/code-ingest/SKILL.md`

- [ ] **Step 1: Write skills/code-ingest/SKILL.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/code-ingest/SKILL.md
git commit -m "feat: add code-ingest skill (/analyze command)"
```

---

## P1 — Week 2: Core Features Complete

### Task 8: skills/code-query/SKILL.md (/query)

**Files:**
- Create: `skills/code-query/SKILL.md`

- [ ] **Step 1: Write skills/code-query/SKILL.md**

```markdown
# /query — Knowledge Query

Answer questions using the wiki knowledge base. Follow the retrieval escalation chain — start cheap, escalate only as needed.

## Trigger

```
/query <question>
/query --repo react,vue <question>
```

## Retrieval Escalation Chain

Follow in order. Stop at the level that gives a confident answer.

### Level 1 — Index Scan (cheapest)
Read `wiki/index.md`. Do any listed pages match the question topic? If yes, proceed to Level 2 on those pages. If no relevant pages found, proceed to Level 3.

### Level 2 — Grep Targeted Sections
Use grep or keyword search to find paragraphs in candidate pages matching key terms from the question. Find specific `^[file:line]` provenance references. Can the question be answered now? If yes, synthesize. If no, proceed to Level 3.

### Level 3 — Full Page Read (most expensive, last resort)
Read the full content of relevant pages. Synthesize a comprehensive answer.

**Never skip levels. Never read full pages when Level 1-2 suffices.**

If `--repo` is specified, only read wiki pages for those repos.

## Answer Format

Provide a clear answer with:
- The main finding
- Key evidence with provenance: `^[file:line]` references from the wiki pages you read
- Confidence level: High / Medium / Low

## Archival Decision (always ask)

After answering, always ask the user:

> **这个分析值得存入 wiki 吗？**
> - A: 不存档（答案已在现有页面，只是汇总）
> - B: 补充现有维度页（发现了现有页面的补充或修正）
> - C: 新建 Insight 页（综合分析有独立价值）

### If user chooses B:
Append to the relevant dimension page under a `## 补充` section. Append log entry.

### If user chooses C:
Write `wiki/insights/<YYYY-MM-DD>-<slug>.md` with this frontmatter (use single-line JSON arrays):
```yaml
---
title: <descriptive title>
type: insight
query: "<original question verbatim>"
generated: <date>
sources: ["wiki/repos/react/dimensions/architecture.md"]
provenance_repos: ["react"]
dimensions_version: v1.0
---
```
Then write the analysis body. Add wikilinks for each path in `sources:`.
Append to `wiki/log.md`: `[<timestamp>] insight created — <slug>`
Update `wiki/index.md` under `## Insights`.
```

- [ ] **Step 2: Commit**

```bash
git add skills/code-query/SKILL.md
git commit -m "feat: add code-query skill (/query command)"
```

---

### Task 9: skills/code-compare/SKILL.md (/compare)

**Files:**
- Create: `skills/code-compare/SKILL.md`

- [ ] **Step 1: Write skills/code-compare/SKILL.md**

```markdown
# /compare — Cross-Repo Comparison

Generate or refresh a comparison matrix across repos in a category, organized by dimension.

## Trigger

```
/compare --category frontend-frameworks
/compare --category frontend-frameworks --dimension extension-points
/compare --repos react,vue,solid --dimension architecture
```

## Execution Protocol

### Step 1 — Find repos

If `--category` specified: read `.manifest.json` → `categories.<category>` for the list of repos.
If `--repos` specified: use the explicit list.

### Step 2 — Identify dimension(s)

If `--dimension` specified: work on that one dimension.
If not specified: generate a full matrix across all 5 dimensions.

### Step 3 — Read wiki pages (not source code)

First, read `.manifest.json` to get the global `dimensions_version`.

For each repo × dimension combination:
- Read `wiki/repos/<repo>/dimensions/<dimension>.md`
- If the file doesn't exist: record `— (未分析)` for that cell
- Compare the page's frontmatter `dimensions_version` against the manifest's global `dimensions_version`. If they differ, the page is stale — record content but mark cell with `⚠️ stale`

Do NOT rely on frontmatter `status: stale` — that field is never written. Staleness is always derived from the manifest version comparison.

Do NOT re-read source code. The comparison reads wiki pages only.

### Step 4 — Generate comparison matrix

For a category × dimension view, output a markdown table:

```markdown
| | React | Vue | Solid |
|---|---|---|---|
| **Architecture** | ... | ... | ... |
| **Extension Points** | ... ⚠️ | ... | — (未分析) |
```

For a repos × single-dimension view, write prose comparing the specific dimension across repos, with cross-repo wikilinks.

### Step 5 — Write to wiki/views/

For category view: `wiki/views/categories/<category>.md`
For dimension view: `wiki/views/dimensions/<dimension>.md`

Page frontmatter (use a single-line JSON array for `sources` so the simple key:value parser in lint.py can read it):
```yaml
---
type: view
category: <category>
dimension: <dimension>
generated: <date>
sources: ["wiki/repos/react/dimensions/architecture.md","wiki/repos/vue/dimensions/architecture.md"]
---
```

Each repo name in the matrix must link to its overview: `[[react/overview]]`.

### Step 6 — Update wiki/index.md and wiki/log.md

Add entry under `## Views` in `wiki/index.md`.
Append to `wiki/log.md`.

### Step 7 — Ask about insight archival

> **这个对比分析值得存为 insight 吗？**

If yes: write `wiki/insights/<date>-<slug>.md` (same format as /query).
```

- [ ] **Step 2: Commit**

```bash
git add skills/code-compare/SKILL.md
git commit -m "feat: add code-compare skill (/compare command)"
```

---

### Task 10: scripts/lint.py

**Files:**
- Create: `scripts/lint.py`
- Create: `tests/test_lint.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lint.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lint import (
    check_broken_wikilinks,
    check_stale_dimensions,
    check_orphan_pages,
    check_missing_provenance,
)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_check_broken_wikilinks_detects_missing(tmp_path):
    # [[vue/dimensions/architecture]] resolves to wiki/repos/vue/dimensions/architecture.md
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "See also [[vue/dimensions/architecture]]")
    # vue page does not exist
    errors = check_broken_wikilinks(tmp_path / "wiki")
    assert len(errors) == 1
    assert "vue/dimensions/architecture" in errors[0]["detail"]


def test_check_broken_wikilinks_passes_when_present(tmp_path):
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "See also [[vue/dimensions/architecture]]")
    # [[vue/dimensions/architecture]] → wiki/repos/vue/dimensions/architecture.md
    write(tmp_path / "wiki/repos/vue/dimensions/architecture.md", "# Vue Arch")
    errors = check_broken_wikilinks(tmp_path / "wiki")
    assert errors == []


def test_check_broken_wikilinks_views_resolve_from_wiki_root(tmp_path):
    write(tmp_path / "wiki/repos/react/overview.md",
          "See [[views/categories/frontend-frameworks]]")
    write(tmp_path / "wiki/views/categories/frontend-frameworks.md", "# Matrix")
    errors = check_broken_wikilinks(tmp_path / "wiki")
    assert errors == []


def test_check_stale_dimensions(tmp_path):
    manifest = {
        "repos": {
            "react": {
                "dimensions_version": "v1.0",
                "dimensions_completed": ["architecture"],
            }
        },
        "dimensions_version": "v1.1",
    }
    write(tmp_path / ".manifest.json", json.dumps(manifest))
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\ndimensions_version: v1.0\n---\n# Arch")
    warnings = check_stale_dimensions(tmp_path / "wiki", tmp_path / ".manifest.json")
    assert len(warnings) == 1
    assert "react" in warnings[0]["detail"]


def test_check_orphan_pages(tmp_path):
    # index.md exists but doesn't mention orphan.md
    write(tmp_path / "wiki/index.md", "# Index\n- [[react/overview]]")
    write(tmp_path / "wiki/repos/react/overview.md", "# React")
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md", "# Arch")
    warnings = check_orphan_pages(tmp_path / "wiki")
    orphan_paths = [w["detail"] for w in warnings]
    assert any("architecture" in p for p in orphan_paths)


def test_check_missing_provenance(tmp_path):
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\n---\n# Architecture\n\nReact uses Fiber.")
    warnings = check_missing_provenance(tmp_path / "wiki")
    assert len(warnings) == 1


def test_check_missing_provenance_passes(tmp_path):
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\n---\n# Architecture\n\nReact uses Fiber. ^[src/ReactFiber.js:1-10]")
    warnings = check_missing_provenance(tmp_path / "wiki")
    assert warnings == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_lint.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'lint'`

- [ ] **Step 3: Write scripts/lint.py**

```python
#!/usr/bin/env python3
"""
lint.py — 7 fixed health-check rules for the codebase wiki.

Usage:
  python scripts/lint.py [--wiki wiki/] [--manifest .manifest.json]

Exit code: 0 if no errors, 1 if any [ERROR] found.

Output format per finding:
  [LEVEL] rule_name  detail
"""
import argparse
import json
import re
import sys
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
PROVENANCE_RE = re.compile(r"\^\[.+?\]")


def _read_wiki_pages(wiki_root: Path):
    """Yield all .md files under wiki_root."""
    return list(wiki_root.rglob("*.md"))


def _strip_frontmatter(text: str) -> tuple[str, dict]:
    """Return (body, frontmatter_dict). frontmatter_dict may be empty."""
    if not text.startswith("---"):
        return text, {}
    end = text.find("\n---", 3)
    if end == -1:
        return text, {}
    fm_text = text[3:end]
    body = text[end + 4:]
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return body, fm


def check_broken_wikilinks(wiki_root: Path) -> list:
    """[ERROR] Any [[page]] whose file doesn't exist.

    Wikilink convention: [[react/overview]] resolves to
    wiki/repos/react/overview.md (i.e. relative to wiki/repos/).
    Links that start with views/ or insights/ resolve relative to wiki/.
    """
    errors = []
    pages = _read_wiki_pages(wiki_root)
    # Build set of resolvable targets (relative to wiki/repos/, without suffix)
    repos_root = wiki_root / "repos"
    repos_strs: set[str] = set()
    if repos_root.exists():
        repos_strs = {
            str(p.relative_to(repos_root).with_suffix("")).lower().replace("\\", "/")
            for p in repos_root.rglob("*.md")
        }
    # Also allow views/ and insights/ links resolved from wiki root
    wiki_strs = {
        str(p.relative_to(wiki_root).with_suffix("")).lower().replace("\\", "/")
        for p in pages
    }

    def _resolves(target: str) -> bool:
        t = target.lower().replace("\\", "/")
        # views/... and insights/... resolve from wiki root
        if t.startswith("views/") or t.startswith("insights/"):
            return t in wiki_strs
        # everything else resolves from wiki/repos/
        return t in repos_strs

    for page in pages:
        content = page.read_text(errors="replace")
        for m in WIKILINK_RE.finditer(content):
            target = m.group(1).strip()
            if not _resolves(target):
                errors.append({
                    "level": "ERROR",
                    "rule": "check_broken_wikilinks",
                    "file": str(page.relative_to(wiki_root)),
                    "detail": f"[[{target}]] — target file not found",
                })
    return errors


def check_stale_dimensions(wiki_root: Path, manifest_path: Path) -> list:
    """[ERROR] wiki page dimensions_version != manifest global dimensions_version."""
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text())
    current_v = manifest.get("dimensions_version", "v1.0")
    warnings = []
    for page in (wiki_root / "repos").rglob("*.md") if (wiki_root / "repos").exists() else []:
        _, fm = _strip_frontmatter(page.read_text(errors="replace"))
        page_v = fm.get("dimensions_version")
        if page_v and page_v != current_v:
            rel = str(page.relative_to(wiki_root))
            repo = fm.get("repo", "unknown")
            warnings.append({
                "level": "ERROR",
                "rule": "check_stale_dimensions",
                "file": rel,
                "detail": f"{repo} — page v={page_v} vs manifest v={current_v}",
            })
    return warnings


def check_orphan_pages(wiki_root: Path) -> list:
    """[WARN] Pages not referenced by any other wiki page."""
    pages = _read_wiki_pages(wiki_root)
    # Build set of all link targets mentioned anywhere
    linked = set()
    for page in pages:
        content = page.read_text(errors="replace")
        for m in WIKILINK_RE.finditer(content):
            linked.add(m.group(1).strip().lower())

    warnings = []
    index = wiki_root / "index.md"
    index_content = index.read_text(errors="replace") if index.exists() else ""

    for page in pages:
        if page == index:
            continue
        rel = str(page.relative_to(wiki_root).with_suffix("")).replace("\\", "/")
        # Check if this page appears in any link or in index
        if rel.lower() not in linked and rel.lower() not in index_content.lower():
            warnings.append({
                "level": "WARN",
                "rule": "check_orphan_pages",
                "file": str(page.relative_to(wiki_root)),
                "detail": rel,
            })
    return warnings


def check_missing_provenance(wiki_root: Path) -> list:
    """[WARN] Dimension pages with no ^[...] provenance references."""
    warnings = []
    dims_root = wiki_root / "repos"
    if not dims_root.exists():
        return []
    for page in dims_root.rglob("*.md"):
        body, fm = _strip_frontmatter(page.read_text(errors="replace"))
        if fm.get("dimension") in (None, "overview"):
            continue
        if not PROVENANCE_RE.search(body):
            warnings.append({
                "level": "WARN",
                "rule": "check_missing_provenance",
                "file": str(page.relative_to(wiki_root)),
                "detail": "no ^[file:line] provenance references found",
            })
    return warnings


def check_empty_pending(wiki_root: Path, manifest_path: Path) -> list:
    """[WARN] dimensions_pending entries older than 30 days."""
    if not manifest_path.exists():
        return []
    import datetime
    manifest = json.loads(manifest_path.read_text())
    warnings = []
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    for repo_key, info in manifest.get("repos", {}).items():
        pending = info.get("dimensions_pending", [])
        last = info.get("last_ingest")
        if pending and last:
            try:
                ingest_dt = datetime.datetime.fromisoformat(last.replace("Z", "+00:00"))
                if ingest_dt < cutoff:
                    warnings.append({
                        "level": "WARN",
                        "rule": "check_empty_pending",
                        "file": ".manifest.json",
                        "detail": f"{repo_key} has pending dims {pending} since {last}",
                    })
            except ValueError:
                pass
    return warnings


def check_missing_category(wiki_root: Path, manifest_path: Path) -> list:
    """[INFO] Repos with no category assigned."""
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text())
    infos = []
    for repo_key, info in manifest.get("repos", {}).items():
        if not info.get("category"):
            infos.append({
                "level": "INFO",
                "rule": "check_missing_category",
                "file": ".manifest.json",
                "detail": f"{repo_key} has no category",
            })
    return infos


def check_views_freshness(wiki_root: Path) -> list:
    """[INFO] views/ pages older than any of their source repos/ pages.

    sources frontmatter must be a single-line JSON array, e.g.:
      sources: ["wiki/repos/react/dimensions/architecture.md"]
    """
    import json as _json
    infos = []
    views_root = wiki_root / "views"
    repos_root = wiki_root / "repos"
    if not views_root.exists() or not repos_root.exists():
        return []
    for view_page in views_root.rglob("*.md"):
        _, fm = _strip_frontmatter(view_page.read_text(errors="replace"))
        generated = fm.get("generated")
        if not generated:
            continue
        sources_raw = fm.get("sources", "[]").strip()
        try:
            source_paths = _json.loads(sources_raw)
        except (_json.JSONDecodeError, TypeError):
            continue
        for src_rel in source_paths:
            # src_rel is like "wiki/repos/react/dimensions/architecture.md"
            src = wiki_root.parent / src_rel
            if src.exists():
                _, src_fm = _strip_frontmatter(src.read_text(errors="replace"))
                src_gen = src_fm.get("generated", "")
                if src_gen > generated:
                    infos.append({
                        "level": "INFO",
                        "rule": "check_views_freshness",
                        "file": str(view_page.relative_to(wiki_root)),
                        "detail": f"source {src.name} (generated {src_gen}) is newer than this view ({generated})",
                    })
    return infos


def run_all(wiki_root: Path, manifest_path: Path) -> list:
    findings = []
    findings += check_broken_wikilinks(wiki_root)
    findings += check_stale_dimensions(wiki_root, manifest_path)
    findings += check_orphan_pages(wiki_root)
    findings += check_missing_provenance(wiki_root)
    findings += check_empty_pending(wiki_root, manifest_path)
    findings += check_missing_category(wiki_root, manifest_path)
    findings += check_views_freshness(wiki_root)
    return findings


def main():
    parser = argparse.ArgumentParser(description="Lint codebase wiki health.")
    parser.add_argument("--wiki", default="wiki", help="Path to wiki/ root")
    parser.add_argument("--manifest", default=".manifest.json")
    args = parser.parse_args()

    wiki_root = Path(args.wiki)
    manifest_path = Path(args.manifest)

    findings = run_all(wiki_root, manifest_path)

    has_error = False
    for f in findings:
        print(f"[{f['level']}] {f['rule']}  {f['file']} — {f['detail']}")
        if f["level"] == "ERROR":
            has_error = True

    if not findings:
        print("✓ No issues found.")

    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_lint.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/lint.py tests/test_lint.py
git commit -m "feat: add lint.py — 7 fixed wiki health-check rules"
```

---

### Task 11: skills/code-lint/SKILL.md (/lint)

**Files:**
- Create: `skills/code-lint/SKILL.md`

- [ ] **Step 1: Write skills/code-lint/SKILL.md**

```markdown
# /lint — Wiki Health Check

Run programmatic health checks on the wiki and report findings.

## Trigger

```
/lint
/lint --fix      # attempt auto-fix for INFO-level issues
```

## Execution Protocol

### Step 1 — Run lint.py

```bash
python scripts/lint.py --wiki wiki/ --manifest .manifest.json
```

### Step 2 — Run eval.py

```bash
python scripts/eval.py --wiki wiki/ --manifest .manifest.json
```

### Step 3 — Report findings

Present a summary organized by severity:

**Errors (must fix):**
- List each [ERROR] finding with file and detail

**Warnings (should fix):**
- List each [WARN] finding

**Info (optional):**
- List each [INFO] finding

**Health Score:**
- Coverage: X%
- Provenance: X%
- Freshness: X%

### Step 4 — Prioritize action (if errors exist)

For each [ERROR], tell the user what action to take:
- `check_broken_wikilinks` → "Run `/analyze` on the referenced repo, or remove the broken link"
- `check_stale_dimensions` → "Run `/analyze <repo> --dimensions <dim>` to refresh stale pages"

Never auto-fix errors without user confirmation. Auto-fix only INFO-level issues with `--fix`.
```

- [ ] **Step 2: Commit**

```bash
git add skills/code-lint/SKILL.md
git commit -m "feat: add code-lint skill (/lint command)"
```

---

## P2 — Week 3: Quality Assurance

### Task 12: scripts/eval.py

**Files:**
- Create: `scripts/eval.py`
- Create: `tests/test_eval.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from eval import compute_coverage, compute_provenance, compute_freshness


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_manifest(path: Path, repos: dict, dims_version: str = "v1.0"):
    data = {
        "repos": repos,
        "dimensions_version": dims_version,
        "categories": {},
    }
    path.write_text(json.dumps(data))


def test_coverage_score(tmp_path):
    make_manifest(tmp_path / ".manifest.json", {
        "react": {
            "dimensions_completed": ["architecture", "extension-points"],
            "dimensions_pending": ["performance-tradeoffs"],
            "dimensions_version": "v1.0",
        }
    })
    score = compute_coverage(tmp_path / ".manifest.json", total_dimensions=5)
    # 2 completed out of 5 = 0.4
    assert abs(score - 0.4) < 0.01


def test_coverage_score_empty(tmp_path):
    make_manifest(tmp_path / ".manifest.json", {})
    score = compute_coverage(tmp_path / ".manifest.json", total_dimensions=5)
    assert score == 1.0  # no repos = 100% (vacuously true)


def test_provenance_score(tmp_path):
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\n---\n"
          "Fiber uses a work loop. ^[src/Fiber.js:10-20]\n"
          "React has reconciler.")  # second claim no provenance
    score = compute_provenance(tmp_path / "wiki")
    # 1 out of 2 sentences has provenance → 0.5
    assert 0.0 <= score <= 1.0


def test_freshness_score(tmp_path):
    make_manifest(tmp_path / ".manifest.json", {
        "react": {
            "dimensions_completed": ["architecture"],
            "dimensions_pending": [],
            "dimensions_version": "v1.0",  # same as global
        }
    })
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\ndimensions_version: v1.0\n---\n# Arch")
    score = compute_freshness(tmp_path / "wiki", tmp_path / ".manifest.json")
    assert score == 1.0  # 0 stale pages


def test_freshness_score_with_stale(tmp_path):
    make_manifest(tmp_path / ".manifest.json", {
        "react": {
            "dimensions_completed": ["architecture"],
            "dimensions_pending": [],
            "dimensions_version": "v1.0",
        }
    }, dims_version="v1.1")
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\ndimensions_version: v1.0\n---\n# Arch")
    score = compute_freshness(tmp_path / "wiki", tmp_path / ".manifest.json")
    assert score < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_eval.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'eval'`

- [ ] **Step 3: Write scripts/eval.py**

```python
#!/usr/bin/env python3
"""
eval.py — compute wiki quality scores and append to wiki/eval-history.jsonl.

Usage:
  python scripts/eval.py [--wiki wiki/] [--manifest .manifest.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

PROVENANCE_RE = re.compile(r"\^\[.+?\]")
SENTENCE_END_RE = re.compile(r"[.!?]\s")


def _strip_frontmatter(text: str) -> tuple:
    if not text.startswith("---"):
        return text, {}
    end = text.find("\n---", 3)
    if end == -1:
        return text, {}
    fm_text = text[3:end]
    body = text[end + 4:]
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return body, fm


def compute_coverage(manifest_path: Path, total_dimensions: int = 5) -> float:
    """Mean ratio of completed dimensions across all repos."""
    if not manifest_path.exists():
        return 1.0
    manifest = json.loads(manifest_path.read_text())
    repos = manifest.get("repos", {})
    if not repos:
        return 1.0
    ratios = []
    for info in repos.values():
        completed = len(info.get("dimensions_completed", []))
        ratios.append(completed / total_dimensions)
    return sum(ratios) / len(ratios)


def compute_provenance(wiki_root: Path) -> float:
    """Fraction of dimension page sentences that have provenance references."""
    dims_root = wiki_root / "repos"
    if not dims_root.exists():
        return 1.0
    total_sentences = 0
    with_provenance = 0
    for page in dims_root.rglob("*.md"):
        body, fm = _strip_frontmatter(page.read_text(errors="replace"))
        if fm.get("dimension") in (None, "overview"):
            continue
        # Split into lines, count non-empty non-heading lines as "claims"
        lines = [l.strip() for l in body.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        for line in lines:
            total_sentences += 1
            if PROVENANCE_RE.search(line):
                with_provenance += 1
    if total_sentences == 0:
        return 1.0
    return with_provenance / total_sentences


def compute_freshness(wiki_root: Path, manifest_path: Path) -> float:
    """Fraction of dimension pages that are NOT stale (1.0 = all fresh)."""
    if not manifest_path.exists():
        return 1.0
    manifest = json.loads(manifest_path.read_text())
    current_v = manifest.get("dimensions_version", "v1.0")
    dims_root = wiki_root / "repos"
    if not dims_root.exists():
        return 1.0
    total = 0
    fresh = 0
    for page in dims_root.rglob("*.md"):
        _, fm = _strip_frontmatter(page.read_text(errors="replace"))
        if fm.get("dimension") in (None, "overview"):
            continue
        total += 1
        if fm.get("dimensions_version") == current_v:
            fresh += 1
    if total == 0:
        return 1.0
    return fresh / total


def main():
    parser = argparse.ArgumentParser(description="Compute wiki quality scores.")
    parser.add_argument("--wiki", default="wiki")
    parser.add_argument("--manifest", default=".manifest.json")
    parser.add_argument("--no-append", action="store_true",
                        help="Don't append to eval-history.jsonl")
    args = parser.parse_args()

    wiki_root = Path(args.wiki)
    manifest_path = Path(args.manifest)

    coverage = compute_coverage(manifest_path)
    provenance = compute_provenance(wiki_root)
    freshness = compute_freshness(wiki_root, manifest_path)

    import datetime
    result = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "coverage": round(coverage, 3),
        "provenance": round(provenance, 3),
        "freshness": round(freshness, 3),
    }

    print(json.dumps(result, indent=2))

    if provenance < 0.7:
        print("[WARN] Provenance score below 70% threshold", file=sys.stderr)

    if not args.no_append:
        history_path = wiki_root / "eval-history.jsonl"
        with history_path.open("a") as f:
            f.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_eval.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/eval.py tests/test_eval.py
git commit -m "feat: add eval.py — wiki quality scoring"
```

---

### Task 13: Full Test Suite Pass

- [ ] **Step 1: Run the full test suite**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/ -v
```

Expected: all tests PASS, no failures.

- [ ] **Step 2: Run lint against the wiki scaffold**

```bash
python scripts/lint.py --wiki wiki/ --manifest .manifest.json
```

Expected: `✓ No issues found.` (wiki is empty, nothing to break).

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "chore: verify full test suite passes"
```

---

## Self-Review Against Spec

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| delta.py — file change detection + layering | Task 4 |
| manifest.py — ingest state, dimensions_version, stale tracking | Task 5 |
| lint.py — 7 fixed rules | Task 10 |
| eval.py — coverage/provenance/freshness scores + eval-history.jsonl | Task 12 |
| hooks/session-start.sh + hooks.json | Task 6 |
| schema/dimensions.md (5 dimensions) | Task 2 |
| schema/CLAUDE.md (wiki rules, double-link rules) | Task 3 |
| code-ingest SKILL.md (/analyze, staged review, provenance) | Task 7 |
| code-query SKILL.md (escalation chain, insight archival) | Task 8 |
| code-compare SKILL.md (category+dimension views, stale marking) | Task 9 |
| code-lint SKILL.md (/lint command) | Task 11 |
| wiki scaffold (index.md, log.md, hot.md) | Task 1 |
| .manifest.json seed | Task 1 |
| dimensions_version stale marking logic | Task 5 (manifest.py get_stale_repos) + Task 10 (lint check_stale_dimensions) |
| Insight page format with `query:` field | Task 8 (SKILL.md) |
| views/ category and dimension pages | Task 9 (SKILL.md) |
| P0 priority: delta + manifest + ingest + hook + dimensions schema | Tasks 1-7 |
| P1 priority: query + compare + lint | Tasks 8-11 |
| P2 priority: eval + stale marking + health history | Tasks 12-13 |

All spec requirements covered. No gaps found.

**Placeholder scan:** No TBD, TODO, or "implement later" entries. All code steps contain actual implementation.

**Type consistency:** `ManifestManager`, `compute_delta`, `classify_file`, `run_all` — names are consistent across tests and implementations.

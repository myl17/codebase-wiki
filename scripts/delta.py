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
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from manifest import HashStore

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
    parser.add_argument("--wiki", default="wiki",
                        help="Path to wiki root (default: wiki)")
    parser.add_argument("--repo", help="Repo key (default: basename of repo_path)")
    args = parser.parse_args()

    repo_root = Path(args.repo_path).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: {repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    repo_key = args.repo or repo_root.name
    store = HashStore(Path(args.wiki), repo_key)
    prev_hashes = store.load()

    result = compute_delta(repo_root, prev_hashes)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

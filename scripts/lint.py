#!/usr/bin/env python3
"""
lint.py — wiki health-check rules for the Entity→Concept architecture.

Usage:
  python scripts/lint.py [--wiki wiki/]

Exit code: 0 if no errors, 1 if any [ERROR] found.

Output format per finding:
  [LEVEL] rule_name  detail
"""
import argparse
import re
import sys
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
PROVENANCE_RE = re.compile(r"\^\[.+?\]")


def _read_wiki_pages(wiki_root: Path):
    """Yield all .md files under wiki_root."""
    return list(wiki_root.rglob("*.md"))


def _strip_frontmatter(text: str) -> tuple:
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

    Wikilink resolution (new architecture):
    - [[repos/<name>/entities/<slug>]] → wiki/repos/<name>/entities/<slug>.md
    - [[repos/<name>/overview]]        → wiki/repos/<name>/overview.md
    - [[concepts/<slug>]]              → wiki/concepts/<slug>.md
    - [[views/<filename>]]             → wiki/views/<filename>.md
    - [[insights/<filename>]]          → wiki/insights/<filename>.md
    """
    errors = []
    pages = _read_wiki_pages(wiki_root)

    # Build resolvable targets relative to wiki/
    wiki_strs = {
        str(p.relative_to(wiki_root).with_suffix("")).lower().replace("\\", "/")
        for p in pages
    }

    def _resolves(target: str) -> bool:
        t = target.lower().replace("\\", "/")
        return t in wiki_strs

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


def check_orphan_pages(wiki_root: Path) -> list:
    """[WARN] Pages not referenced by any other wiki page (excluding maintenance files)."""
    maintenance_files = {"hot.md", "log.md", "index.md"}
    pages = [p for p in _read_wiki_pages(wiki_root)
             if p.name not in maintenance_files]

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
        if rel.lower() not in linked and rel.lower() not in index_content.lower():
            warnings.append({
                "level": "WARN",
                "rule": "check_orphan_pages",
                "file": str(page.relative_to(wiki_root)),
                "detail": rel,
            })
    return warnings


def check_missing_provenance(wiki_root: Path) -> list:
    """[WARN] Entity/Concept pages with no ^[...] provenance references.

    Checks entity pages (wiki/repos/*/entities/*.md) and
    concept pages (wiki/concepts/*.md). Skips redirect pages.
    """
    warnings = []
    for page in _read_wiki_pages(wiki_root):
        body, fm = _strip_frontmatter(page.read_text(errors="replace"))
        page_type = fm.get("type", "")

        # Only check entity and concept pages
        if page_type not in ("entity", "concept"):
            continue

        # Skip redirect pages
        if fm.get("redirect_to"):
            continue

        if not PROVENANCE_RE.search(body):
            warnings.append({
                "level": "WARN",
                "rule": "check_missing_provenance",
                "file": str(page.relative_to(wiki_root)),
                "detail": "no ^[file:line] provenance references found",
            })
    return warnings


def check_views_freshness(wiki_root: Path) -> list:
    """[INFO] views/ pages older than any of their source pages.

    sources frontmatter must be a single-line JSON array, e.g.:
      sources: ["wiki/concepts/memory-backend.md","wiki/repos/nanobot/entities/memory.md"]
    """
    import json as _json
    infos = []
    views_root = wiki_root / "views"
    if not views_root.exists():
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


def run_all(wiki_root: Path) -> list:
    findings = []
    findings += check_broken_wikilinks(wiki_root)
    findings += check_orphan_pages(wiki_root)
    findings += check_missing_provenance(wiki_root)
    findings += check_views_freshness(wiki_root)
    return findings


def main():
    parser = argparse.ArgumentParser(description="Lint codebase wiki health.")
    parser.add_argument("--wiki", default="wiki", help="Path to wiki/ root")
    args = parser.parse_args()

    wiki_root = Path(args.wiki)

    findings = run_all(wiki_root)

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

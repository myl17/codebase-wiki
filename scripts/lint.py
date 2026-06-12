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

    Wikilink convention: [[react/overview]] resolves to
    wiki/repos/react/overview.md (i.e. relative to wiki/repos/).
    Links that start with views/ or insights/ resolve relative to wiki/.
    """
    errors = []
    pages = _read_wiki_pages(wiki_root)
    # Build set of resolvable targets (relative to wiki/repos/, without suffix)
    repos_root = wiki_root / "repos"
    repos_strs = set()
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
    repos_root = wiki_root / "repos"
    pages = list(repos_root.rglob("*.md")) if repos_root.exists() else []
    for page in pages:
        _, fm = _strip_frontmatter(page.read_text(errors="replace"))
        page_v = fm.get("dimensions_version")
        if page_v and page_v != current_v:
            rel = str(page.relative_to(wiki_root))
            # Derive repo from path (wiki/repos/<repo>/...) as fallback
            repo = fm.get("repo") or page.relative_to(repos_root).parts[0]
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
        dim_val = fm.get("dimension")
        # Skip overview pages; also skip if no dimension key but not in a dimensions/ dir
        if dim_val == "overview":
            continue
        if dim_val is None and "dimensions" not in page.parts:
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
    findings += check_graph_edge_types(wiki_root)
    findings += check_graph_dangling_edges(wiki_root)
    findings += check_concept_registered(wiki_root)
    findings += check_candidate_backlog(wiki_root)
    return findings


def _parse_node_frontmatter(text: str) -> dict:
    """Minimal frontmatter parser for node pages (scalars, inline lists, block lists)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_text = text[3:end]
    fm = {}
    current_list = None
    for line in fm_text.splitlines():
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val == "":
                current_list = []
                fm[key] = current_list
            elif val.startswith("[") and val.endswith("]"):
                current_list = None
                inner = val[1:-1].strip()
                fm[key] = [x.strip() for x in inner.split(",")] if inner else []
            else:
                current_list = None
                fm[key] = val
        else:
            current_list = None
    return fm


def _iter_node_pages(wiki_root: Path):
    """Yield (repo, node_file, frontmatter) for all node pages."""
    repos_root = wiki_root / "repos"
    if not repos_root.exists():
        return
    for nodes_dir in sorted(repos_root.glob("*/nodes")):
        repo = nodes_dir.parent.name
        for node_file in sorted(nodes_dir.glob("*/*.md")):
            yield repo, node_file, _parse_node_frontmatter(node_file.read_text(errors="replace"))


def _as_list(value) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    return value


def check_graph_edge_types(wiki_root: Path) -> list:
    """[ERROR] node_type/edge-type constraint violations.

    Rules (per schema/graph-schema.md):
    - Only ExtensionPoint nodes may have `targets`
    - DesignDecision nodes may not have `concept` (decisions are edge sources via motivates)
    """
    errors = []
    for repo, node_file, fm in _iter_node_pages(wiki_root):
        ntype = fm.get("node_type", "")
        slug = node_file.stem

        if _as_list(fm.get("targets")) and ntype != "ExtensionPoint":
            errors.append({
                "level": "ERROR",
                "rule": "check_graph_edge_types",
                "file": str(node_file.relative_to(wiki_root)),
                "detail": f"{repo}:{slug} has `targets` but node_type is {ntype!r} (only ExtensionPoint allowed)",
            })
        if fm.get("concept") and ntype == "DesignDecision":
            errors.append({
                "level": "ERROR",
                "rule": "check_graph_edge_types",
                "file": str(node_file.relative_to(wiki_root)),
                "detail": f"{repo}:{slug} DesignDecision cannot have `concept`",
            })
    return errors


def check_graph_dangling_edges(wiki_root: Path) -> list:
    """[ERROR] targets / motivated_by pointing to non-existent node pages."""
    def _repo_slug(repo: str, stem: str) -> str:
        prefix = f"{repo}-"
        return stem[len(prefix):] if stem.startswith(prefix) else stem

    errors = []
    slugs_by_repo = {}
    for repo, node_file, _ in _iter_node_pages(wiki_root):
        slugs_by_repo.setdefault(repo, set()).add(_repo_slug(repo, node_file.stem))

    for repo, node_file, fm in _iter_node_pages(wiki_root):
        slug = _repo_slug(repo, node_file.stem)
        for field in ("targets", "motivated_by"):
            for ref in _as_list(fm.get(field)):
                if ref not in slugs_by_repo.get(repo, set()):
                    errors.append({
                        "level": "ERROR",
                        "rule": "check_graph_dangling_edges",
                        "file": str(node_file.relative_to(wiki_root)),
                        "detail": f"{repo}:{slug} {field} → {ref!r} does not exist in nodes/",
                    })
    return errors


def check_concept_registered(wiki_root: Path) -> list:
    """[ERROR] concept field value not present in wiki/entities/_index.md."""
    index_path = wiki_root / "entities" / "_index.md"
    if not index_path.exists():
        return []

    registered = set()
    for line in index_path.read_text(errors="replace").splitlines():
        if line.startswith("|") and not line.startswith("| Concept") and not line.startswith("|--"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 2 and cols[1]:
                registered.add(cols[1])

    errors = []
    for repo, node_file, fm in _iter_node_pages(wiki_root):
        concept = fm.get("concept", "")
        if isinstance(concept, str) and concept and concept not in registered:
            errors.append({
                "level": "ERROR",
                "rule": "check_concept_registered",
                "file": str(node_file.relative_to(wiki_root)),
                "detail": f"concept {concept!r} not found in entities/_index.md",
            })
    return errors


def check_candidate_backlog(wiki_root: Path, threshold: int = 3) -> list:
    """[WARN] A repo has >= threshold unconfirmed concept_candidate nodes."""
    counts = {}
    for repo, node_file, fm in _iter_node_pages(wiki_root):
        cand = fm.get("concept_candidate", "")
        if isinstance(cand, str) and cand:
            counts.setdefault(repo, []).append(node_file.stem)

    warnings = []
    for repo, candidates in sorted(counts.items()):
        if len(candidates) >= threshold:
            warnings.append({
                "level": "WARN",
                "rule": "check_candidate_backlog",
                "file": f"repos/{repo}/nodes/",
                "detail": f"{repo} has {len(candidates)} unconfirmed concept_candidate(s): {candidates} — run normalization pass",
            })
    return warnings


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

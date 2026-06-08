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

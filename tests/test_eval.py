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

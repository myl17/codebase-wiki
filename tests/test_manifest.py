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

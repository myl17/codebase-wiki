# tests/test_manifest.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from manifest import ManifestManager, HashStore


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
        timestamp="2026-06-08T10:00:00Z",
    )
    repo = m.data["repos"]["react"]
    assert repo["dimensions_completed"] == ["architecture"]
    assert repo["dimensions_pending"] == ["extension-points", "performance-tradeoffs"]
    assert repo["last_ingest"] == "2026-06-08T10:00:00Z"
    assert repo["dimensions_version"] == "v1.0"


def test_stale_repos(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react")
    m.update_after_ingest(
        repo_key="react",
        completed_dimensions=["architecture"],
        pending_dimensions=[],
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
    m.update_after_ingest("react", ["architecture"], [], "2026-06-08T10:00:00Z")
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


def test_hashstore_load_missing(tmp_path):
    store = HashStore(tmp_path / "wiki", "react")
    assert store.load() == {}


def test_hashstore_save_and_load(tmp_path):
    store = HashStore(tmp_path / "wiki", "react")
    store.save({"src/index.ts": "abc123"})
    assert store.load() == {"src/index.ts": "abc123"}
    assert (tmp_path / "wiki" / "repos" / "react" / ".hashes.json").exists()


def test_hashstore_merge_delta(tmp_path):
    store = HashStore(tmp_path / "wiki", "react")
    store.save({"src/old.ts": "aaa", "src/gone.ts": "bbb"})
    delta = {
        "new": [{"path": "src/new.ts", "layer": "impl", "hash": "ccc"}],
        "modified": [{"path": "src/old.ts", "layer": "impl", "hash": "ddd"}],
        "deleted": ["src/gone.ts"],
    }
    store.merge_delta(delta)
    result = store.load()
    assert result == {"src/old.ts": "ddd", "src/new.ts": "ccc"}


def test_add_repo_no_file_hashes(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("vue", "./raw/repos/vue")
    assert "file_hashes" not in m.data["repos"]["vue"]


def test_update_after_ingest_no_file_hashes(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react")
    m.update_after_ingest(
        repo_key="react",
        completed_dimensions=["architecture"],
        pending_dimensions=["extension-points"],
        timestamp="2026-06-09T10:00:00Z",
    )
    repo = m.data["repos"]["react"]
    assert "file_hashes" not in repo
    assert repo["dimensions_completed"] == ["architecture"]


def test_migrate_moves_hashes_to_hashstore(tmp_path):
    import subprocess, sys as _sys
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    manifest_path = tmp_path / ".manifest.json"
    manifest_path.write_text(json.dumps({
        "repos": {
            "react": {
                "path": "./raw/repos/react",
                "last_ingest": "2026-06-09T10:00:00Z",
                "dimensions_completed": ["architecture"],
                "dimensions_pending": [],
                "file_hashes": {"src/index.ts": "abc123"},
                "category": None,
                "dimensions_version": "v1.0",
            }
        },
        "dimensions_version": "v1.0",
        "categories": {},
    }))
    result = subprocess.run(
        [_sys.executable, "scripts/manifest.py",
         "--manifest", str(manifest_path),
         "migrate", "--wiki", str(wiki_root)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, result.stderr
    hashes_path = wiki_root / "repos" / "react" / ".hashes.json"
    assert hashes_path.exists()
    assert json.loads(hashes_path.read_text()) == {"src/index.ts": "abc123"}
    updated = json.loads(manifest_path.read_text())
    assert "file_hashes" not in updated["repos"]["react"]

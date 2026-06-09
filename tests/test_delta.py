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


def test_delta_reads_from_hashstore(tmp_path):
    """delta.py CLI 应从 wiki/repos/<name>/.hashes.json 读取上次 hashes。"""
    import hashlib, subprocess, sys as _sys, json
    repo = make_repo(tmp_path / "repo", {"src/index.ts": "v1"})
    wiki_root = tmp_path / "wiki"
    store_path = wiki_root / "repos" / "myrepo" / ".hashes.json"
    store_path.parent.mkdir(parents=True)
    store_path.write_text(json.dumps({
        "src/index.ts": hashlib.sha256(b"v1").hexdigest()
    }))
    (repo / "src" / "index.ts").write_text("v2")
    result = subprocess.run(
        [_sys.executable, "scripts/delta.py", str(repo),
         "--wiki", str(wiki_root), "--repo", "myrepo"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert len(data["modified"]) == 1
    assert data["modified"][0]["path"] == "src/index.ts"
    assert len(data["new"]) == 0

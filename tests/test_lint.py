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
    check_missing_entity_links,
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


def test_check_missing_entity_links_warns_when_no_entity_links(tmp_path):
    # dimension page with only repo cross-links, no entity wikilinks (no /-less links)
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\n---\n"
          "# Arch\n\nSee [[vue/dimensions/architecture]].")
    warnings = check_missing_entity_links(tmp_path / "wiki")
    assert len(warnings) == 1
    assert warnings[0]["rule"] == "check_missing_entity_links"
    assert "architecture" in warnings[0]["file"]


def test_check_missing_entity_links_passes_when_entity_link_present(tmp_path):
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\n---\n"
          "# Arch\n\nUses [[事件驱动]] pattern. ^[src/core.js:1-10]")
    warnings = check_missing_entity_links(tmp_path / "wiki")
    assert warnings == []


def test_check_missing_entity_links_skips_overview(tmp_path):
    write(tmp_path / "wiki/repos/react/overview.md",
          "---\nrepo: react\ndimension: overview\n---\n"
          "# Overview\n\nLinks to [[react/dimensions/architecture]].")
    warnings = check_missing_entity_links(tmp_path / "wiki")
    assert warnings == []

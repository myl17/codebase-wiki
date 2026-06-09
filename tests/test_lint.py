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
    check_missing_code_snippet,
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


def test_check_missing_code_snippet_warns(tmp_path):
    """有 ^[file:line] 但没有后跟 [!source] callout 时报 WARN。"""
    wiki = tmp_path / "wiki"
    page = wiki / "repos" / "react" / "dimensions" / "architecture.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\nrepo: react\ndimension: architecture\ndimensions_version: v1.0\ngenerated: 2026-06-09\n---\n"
        "React uses fiber. ^[src/ReactFiber.js:1-10]\n"
        "No callout after this provenance.\n"
    )
    findings = check_missing_code_snippet(wiki)
    assert len(findings) == 1
    assert findings[0]["level"] == "WARN"
    assert findings[0]["rule"] == "check_missing_code_snippet"


def test_check_missing_code_snippet_passes_with_callout(tmp_path):
    """provenance 后紧跟 [!source] callout 时不报 WARN。"""
    wiki = tmp_path / "wiki"
    page = wiki / "repos" / "react" / "dimensions" / "architecture.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\nrepo: react\ndimension: architecture\ndimensions_version: v1.0\ngenerated: 2026-06-09\n---\n"
        "React uses fiber. ^[src/ReactFiber.js:1-10]\n"
        "\n"
        "> [!source]- ReactFiber.js:1-5\n"
        "> ```js\n"
        "> function createFiber() {}\n"
        "> ```\n"
    )
    findings = check_missing_code_snippet(wiki)
    assert findings == []


def test_check_missing_code_snippet_skips_overview(tmp_path):
    """overview 页没有 provenance，不应误报。"""
    wiki = tmp_path / "wiki"
    page = wiki / "repos" / "react" / "overview.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\nrepo: react\ndimension: overview\ndimensions_version: v1.0\ngenerated: 2026-06-09\n---\n"
        "Overview without any provenance.\n"
    )
    findings = check_missing_code_snippet(wiki)
    assert findings == []

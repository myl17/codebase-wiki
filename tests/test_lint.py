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


# ---- graph structure lint rules ----

def test_check_invalid_edge_type_targets(tmp_path):
    """Component 不能有 targets 字段（targets 只属于 ExtensionPoint）。"""
    write(tmp_path / "wiki/repos/openclaw/nodes/bad.md",
          "---\nnode_type: Component\nscope: subsystem\ntargets:\n  - other\n---\n# Bad\n")
    from lint import check_graph_edge_types
    errors = check_graph_edge_types(tmp_path / "wiki")
    assert len(errors) == 1
    assert "bad" in errors[0]["detail"]


def test_check_dangling_targets(tmp_path):
    """targets 指向不存在的节点页时报错。"""
    write(tmp_path / "wiki/repos/openclaw/nodes/ep.md",
          "---\nnode_type: ExtensionPoint\nscope: subsystem\ntargets:\n  - nonexistent\n---\n# EP\n")
    from lint import check_graph_dangling_edges
    errors = check_graph_dangling_edges(tmp_path / "wiki")
    assert len(errors) == 1
    assert "nonexistent" in errors[0]["detail"]


def test_check_concept_not_registered(tmp_path):
    """concept 字段的值不在 _index.md 时报错。"""
    write(tmp_path / "wiki/entities/_index.md",
          "# Concept Index\n\n| Concept | 别名 | 定义 | 实例数 |\n|---|---|---|---|\n| 插件系统 | Plugin System | desc | 1 |\n")
    write(tmp_path / "wiki/repos/openclaw/nodes/ep.md",
          "---\nnode_type: ExtensionPoint\nscope: subsystem\nconcept: 未注册概念\n---\n# EP\n")
    from lint import check_concept_registered
    errors = check_concept_registered(tmp_path / "wiki")
    assert len(errors) == 1
    assert "未注册概念" in errors[0]["detail"]


def test_check_concept_registered_passes(tmp_path):
    write(tmp_path / "wiki/entities/_index.md",
          "# Concept Index\n\n| Concept | 别名 | 定义 | 实例数 |\n|---|---|---|---|\n| 插件系统 | Plugin System | desc | 1 |\n")
    write(tmp_path / "wiki/repos/openclaw/nodes/ep.md",
          "---\nnode_type: ExtensionPoint\nscope: subsystem\nconcept: 插件系统\n---\n# EP\n")
    from lint import check_concept_registered
    errors = check_concept_registered(tmp_path / "wiki")
    assert errors == []


def test_check_candidate_backlog_warns_when_many(tmp_path):
    """当某个 repo 的 nodes/ 下积压 >=3 个 concept_candidate 时应报警。"""
    for i in range(3):
        write(tmp_path / f"wiki/repos/openclaw/nodes/ep{i}.md",
              f"---\nnode_type: ExtensionPoint\nscope: subsystem\n"
              f"concept_candidate: 候选概念{i}\n---\n# EP{i}\n")
    from lint import check_candidate_backlog
    warnings = check_candidate_backlog(tmp_path / "wiki")
    assert len(warnings) == 1
    assert "openclaw" in warnings[0]["detail"]


def test_check_candidate_backlog_ok_when_few(tmp_path):
    for i in range(2):
        write(tmp_path / f"wiki/repos/openclaw/nodes/ep{i}.md",
              f"---\nnode_type: ExtensionPoint\nscope: subsystem\n"
              f"concept_candidate: 候选{i}\n---\n# EP{i}\n")
    from lint import check_candidate_backlog
    warnings = check_candidate_backlog(tmp_path / "wiki")
    assert warnings == []

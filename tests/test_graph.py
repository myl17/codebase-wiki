#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from graph import build_graph


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_node(tmp: Path, repo: str, slug: str, frontmatter: str, body: str = "# Node"):
    write(
        tmp / f"wiki/repos/{repo}/nodes/{slug}.md",
        f"---\n{frontmatter}\n---\n\n{body}\n"
    )


def test_build_graph_returns_nodes_and_edges(tmp_path):
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\n"
              "concept: 插件系统\ntargets:\n  - tool-policy")

    g = build_graph(tmp_path / "wiki")

    assert len(g["nodes"]) == 2
    node_ids = {n["id"] for n in g["nodes"]}
    assert "openclaw:tool-policy" in node_ids
    assert "openclaw:channel-plugin" in node_ids


def test_build_graph_targets_edge(tmp_path):
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\n"
              "targets:\n  - tool-policy")

    g = build_graph(tmp_path / "wiki")

    edges = g["edges"]
    assert any(
        e["type"] == "targets"
        and e["from"] == "openclaw:channel-plugin"
        and e["to"] == "openclaw:tool-policy"
        for e in edges
    )


def test_build_graph_embodies_edge(tmp_path):
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\nconcept: 插件系统")

    g = build_graph(tmp_path / "wiki")

    assert any(
        e["type"] == "embodies"
        and e["from"] == "openclaw:channel-plugin"
        and e["to"] == "concept:插件系统"
        for e in g["edges"]
    )


def test_build_graph_motivated_by_edge(tmp_path):
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")

    g = build_graph(tmp_path / "wiki")

    assert any(
        e["type"] == "motivates"
        and e["from"] == "openclaw:sync-gate"
        and e["to"] == "openclaw:tool-policy"
        for e in g["edges"]
    )


def test_build_graph_inline_list_syntax(tmp_path):
    """frontmatter 中 targets: [a, b] 行内列表语法也要支持。"""
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "ep",
              "node_type: ExtensionPoint\nscope: component\n"
              "targets: [tool-policy]\nmotivated_by: [sync-gate]")

    g = build_graph(tmp_path / "wiki")

    assert any(e["type"] == "targets" and e["to"] == "openclaw:tool-policy"
               for e in g["edges"])
    assert any(e["type"] == "motivates" and e["from"] == "openclaw:sync-gate"
               for e in g["edges"])


def test_query_impact_direct(tmp_path):
    """Nodes targeted by or motivated_by the queried node should appear."""
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")
    make_node(tmp_path, "openclaw", "exec-approval",
              "node_type: ExtensionPoint\nscope: component\n"
              "targets:\n  - tool-policy\n"
              "motivated_by:\n  - sync-gate")

    from graph import query_impact
    result = query_impact(tmp_path / "wiki", "openclaw", "tool-policy")

    ids = {r["id"] for r in result}
    assert "openclaw:sync-gate" in ids
    assert "openclaw:exec-approval" in ids


def test_query_impact_excludes_unrelated(tmp_path):
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "context-engine",
              "node_type: Component\nscope: subsystem")

    from graph import query_impact
    result = query_impact(tmp_path / "wiki", "openclaw", "tool-policy")

    ids = {r["id"] for r in result}
    assert "openclaw:context-engine" not in ids

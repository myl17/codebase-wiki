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


_TYPE_DIR = {"Component": "components", "ExtensionPoint": "extension-points", "DesignDecision": "design-decisions"}

def make_node(tmp: Path, repo: str, slug: str, frontmatter: str, body: str = "# Node", type_dir: str = None, explicit_path: str = None):
    if explicit_path:
        write(
            tmp / f"wiki/repos/{repo}/{explicit_path}",
            f"---\n{frontmatter}\n---\n\n{body}\n"
        )
        return
    if type_dir is None:
        for ntype, dname in _TYPE_DIR.items():
            if f"node_type: {ntype}" in frontmatter:
                type_dir = dname
                break
        else:
            type_dir = "components"  # fallback
    write(
        tmp / f"wiki/repos/{repo}/nodes/{type_dir}/{repo}-{slug}.md",
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


def test_generate_mermaid_contains_nodes(tmp_path):
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")

    from graph import generate_mermaid
    result = generate_mermaid(tmp_path / "wiki", "openclaw",
                              center_slug="tool-policy", hops=1)

    assert "graph LR" in result
    assert "sync_gate" in result
    assert "tool_policy" in result
    assert "motivates" in result


def test_generate_mermaid_hops_limit(tmp_path):
    """hops=1 时距中心 2 跳的节点不应出现。"""
    make_node(tmp_path, "openclaw", "a",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "b",
              "node_type: ExtensionPoint\nscope: component\ntargets: [a]")
    make_node(tmp_path, "openclaw", "c-decision",
              "node_type: DesignDecision\nscope: system")
    # c-decision motivates b → b is 1 hop from a, c-decision is 2 hops
    make_node(tmp_path, "openclaw", "b2",
              "node_type: ExtensionPoint\nscope: component\n"
              "targets: [a]\nmotivated_by: [c-decision]")

    from graph import generate_mermaid
    result = generate_mermaid(tmp_path / "wiki", "openclaw",
                              center_slug="a", hops=1)

    assert "openclaw_b[" in result or "openclaw_b " in result


def test_update_wikilinks_writes_node_sections(tmp_path):
    """--update-wikilinks 应为每节点页写入 ## 关联 区块。"""
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\n"
              "concept: 插件系统\ntargets:\n  - tool-policy")
    make_node(tmp_path, "openclaw", "overview",
              f"---\nrepo: openclaw\ndimension: overview\n---\n\n# Overview\n",
              body="", explicit_path="openclaw-overview.md")

    from graph import build_graph, update_wikilinks, _GEN_WIKILINKS_START, _GEN_MERMAID_START
    g = build_graph(tmp_path / "wiki")
    update_wikilinks(tmp_path / "wiki", g)

    tp = (tmp_path / "wiki/repos/openclaw/nodes/components/openclaw-tool-policy.md").read_text()
    assert _GEN_WIKILINKS_START in tp
    assert "设计原因" in tp
    assert "[[openclaw/nodes/design-decisions/openclaw-sync-gate]]" in tp

    # Verify the "催生了" section header (for DesignDecisions that motivate others)
    # does NOT appear — tool-policy is a Component, not a DesignDecision
    after_gen = tp[tp.index(_GEN_WIKILINKS_START):]
    assert "**催生了**" not in after_gen

    cp = (tmp_path / "wiki/repos/openclaw/nodes/extension-points/openclaw-channel-plugin.md").read_text()
    assert _GEN_WIKILINKS_START in cp
    assert "[[openclaw/nodes/components/openclaw-tool-policy]]" in cp

    ov = (tmp_path / "wiki/repos/openclaw/openclaw-overview.md").read_text()
    assert _GEN_MERMAID_START in ov
    assert "graph LR" in ov


def test_update_wikilinks_idempotent(tmp_path):
    """第二次运行应替换旧区块，不重复。"""
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\n"
              "targets:\n  - tool-policy")
    make_node(tmp_path, "openclaw", "overview",
              "---\nrepo: openclaw\ndimension: overview\n---\n\n# Overview\n",
              body="", explicit_path="openclaw-overview.md")

    from graph import build_graph, update_wikilinks, _GEN_WIKILINKS_START
    wiki = tmp_path / "wiki"
    g = build_graph(wiki)
    update_wikilinks(wiki, g)
    update_wikilinks(wiki, g)  # second run

    tp = (tmp_path / "wiki/repos/openclaw/nodes/extension-points/openclaw-channel-plugin.md").read_text()
    assert tp.count(_GEN_WIKILINKS_START) == 1


def test_dimension_links_from_extracted_from(tmp_path):
    """extracted_from 字段应生成维度页到节点页的反向链接。"""
    wiki = tmp_path / "wiki"

    # node pages in type subdirectories
    write(wiki / "repos/openclaw/nodes/components/openclaw-tool-policy.md",
          "---\nnode_type: Component\nscope: subsystem\n"
          "extracted_from:\n  - architecture\n---\n\n# ToolPolicy\n")
    write(wiki / "repos/openclaw/nodes/extension-points/openclaw-channel-plugin.md",
          "---\nnode_type: ExtensionPoint\nscope: subsystem\n"
          "extracted_from:\n  - architecture\n  - extension-points\n---\n\n# ChannelPlugin\n")
    # dimension page
    write(wiki / "repos/openclaw/dimensions/openclaw-architecture.md",
          "---\nrepo: openclaw\ndimension: architecture\n---\n\n# Architecture\n\nKey components.\n")

    from graph import build_graph, update_wikilinks, _GEN_DIM_LINKS_START
    g = build_graph(wiki)
    update_wikilinks(wiki, g)

    arch = (wiki / "repos/openclaw/dimensions/openclaw-architecture.md").read_text()
    assert _GEN_DIM_LINKS_START in arch
    assert "[[openclaw/nodes/components/openclaw-tool-policy]]" in arch
    assert "[[openclaw/nodes/extension-points/openclaw-channel-plugin]]" in arch


def test_write_obsidian_graph_config(tmp_path):
    """应写出带 colorGroups 的 graph.json。"""
    from graph import write_obsidian_graph_config
    import json
    config_path = tmp_path / ".obsidian" / "graph.json"
    write_obsidian_graph_config(config_path)
    assert config_path.exists()
    cfg = json.loads(config_path.read_text())
    assert len(cfg["colorGroups"]) == 6
    queries = {g["query"] for g in cfg["colorGroups"]}
    assert "path:nodes/components" in queries
    assert "path:nodes/extension-points" in queries
    assert "path:nodes/design-decisions" in queries
    assert "path:dimensions" in queries
    assert "overview" in queries
    assert "path:entities" in queries

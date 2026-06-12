#!/usr/bin/env python3
"""
graph.py — derive and query the codebase knowledge graph from node page frontmatter.

Usage:
  python scripts/graph.py build [--wiki wiki/] [--out wiki/graph/graph.json]
  python scripts/graph.py query --impact <node-slug> --repo <repo> [--wiki wiki/]
  python scripts/graph.py mermaid <repo> [--center SLUG] [--hops 2] [--wiki wiki/]
"""
import argparse
import json
from pathlib import Path


def _parse_value(val: str):
    """Parse a scalar or inline-list frontmatter value."""
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [x.strip() for x in inner.split(",")]
    return val


def _parse_frontmatter(text: str) -> tuple:
    """Return (frontmatter_dict, body). Supports scalars, inline lists, and block lists."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end]
    body = text[end + 4:]

    fm = {}
    current_list = None

    for line in fm_text.splitlines():
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                current_list = []
                fm[key] = current_list
            else:
                current_list = None
                fm[key] = _parse_value(val)
        else:
            current_list = None

    return fm, body


def _as_list(value) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    return value


def build_graph(wiki_root: Path) -> dict:
    """Scan all nodes/ pages and return {nodes: [...], edges: [...]}."""
    nodes = []
    edges = []

    nodes_dirs = sorted((wiki_root / "repos").glob("*/nodes"))
    for nodes_dir in nodes_dirs:
        repo = nodes_dir.parent.name
        for node_file in sorted(nodes_dir.glob("*.md")):
            slug = node_file.stem
            node_id = f"{repo}:{slug}"
            fm, _ = _parse_frontmatter(node_file.read_text())

            nodes.append({
                "id": node_id,
                "repo": repo,
                "slug": slug,
                "node_type": fm.get("node_type", ""),
                "scope": fm.get("scope", ""),
                "concept": fm.get("concept", "") if isinstance(fm.get("concept", ""), str) else "",
                "concept_candidate": fm.get("concept_candidate", "") if isinstance(fm.get("concept_candidate", ""), str) else "",
                "sources": _as_list(fm.get("sources")),
                "extracted_from": _as_list(fm.get("extracted_from")),
            })

            concept = fm.get("concept", "")
            if isinstance(concept, str) and concept:
                edges.append({
                    "type": "embodies",
                    "from": node_id,
                    "to": f"concept:{concept}",
                })

            for t in _as_list(fm.get("targets")):
                edges.append({
                    "type": "targets",
                    "from": node_id,
                    "to": f"{repo}:{t}",
                })

            for d in _as_list(fm.get("motivated_by")):
                edges.append({
                    "type": "motivates",
                    "from": f"{repo}:{d}",
                    "to": node_id,
                })

    return {"nodes": nodes, "edges": edges}


def query_impact(wiki_root: Path, repo: str, slug: str) -> list:
    """Return all nodes directly related to repo:slug via any edge type."""
    g = build_graph(wiki_root)
    target_id = f"{repo}:{slug}"
    related_ids = set()

    for edge in g["edges"]:
        if edge["from"] == target_id:
            related_ids.add(edge["to"])
        if edge["to"] == target_id:
            related_ids.add(edge["from"])

    node_map = {n["id"]: n for n in g["nodes"]}
    return [node_map[nid] for nid in sorted(related_ids) if nid in node_map]


def generate_mermaid(wiki_root: Path, repo: str,
                     center_slug: str = None, hops: int = 2) -> str:
    """Generate a Mermaid LR graph snippet for a repo's nodes.

    If center_slug is given, only include nodes within `hops` edges of it.
    """
    g = build_graph(wiki_root)
    repo_nodes = {n["id"]: n for n in g["nodes"] if n["repo"] == repo}

    if center_slug:
        center_id = f"{repo}:{center_slug}"
        visited = {center_id}
        frontier = {center_id}
        for _ in range(hops):
            next_frontier = set()
            for edge in g["edges"]:
                if edge["from"] in frontier and edge["to"] not in visited:
                    next_frontier.add(edge["to"])
                if edge["to"] in frontier and edge["from"] not in visited:
                    next_frontier.add(edge["from"])
            visited |= next_frontier
            frontier = next_frontier
        relevant_ids = visited
    else:
        relevant_ids = set(repo_nodes.keys())

    def _mermaid_id(node_id: str) -> str:
        return node_id.replace(":", "_").replace("-", "_").replace(" ", "_")

    def _label(node_id: str) -> str:
        if node_id in repo_nodes:
            n = repo_nodes[node_id]
            return f'"{n["slug"]}<br/>{n["node_type"]}"'
        concept_name = node_id.replace("concept:", "")
        return f'"concept:{concept_name}"'

    lines = ["graph LR"]
    seen_edges = set()
    for edge in g["edges"]:
        frm, to, etype = edge["from"], edge["to"], edge["type"]
        if frm not in relevant_ids and to not in relevant_ids:
            continue
        # Only render edges where at least one endpoint is in this repo
        if frm not in repo_nodes and to not in repo_nodes:
            continue
        key = (frm, to, etype)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        lines.append(
            f"    {_mermaid_id(frm)}[{_label(frm)}] -->|{etype}| {_mermaid_id(to)}[{_label(to)}]"
        )

    return "\n".join(lines)


# ---- generated section markers ----
_GEN_WIKILINKS_START = "<!-- generated-wikilinks -->"
_GEN_WIKILINKS_END = "<!-- /generated -->"
_GEN_MERMAID_START = "<!-- generated-mermaid -->"
_GEN_MERMAID_END = "<!-- /generated-mermaid -->"
_GEN_DIM_LINKS_START = "<!-- generated-dimension-links -->"
_GEN_DIM_LINKS_END = "<!-- /generated-dimension-links -->"


def _strip_generated_section(text: str, start: str, end: str) -> str:
    """Remove a generated section (and surrounding blank lines) from text."""
    # Handle both block-at-end (no trailing content) and block-in-middle.
    idx_start = text.find(start)
    if idx_start == -1:
        return text
    idx_end = text.find(end, idx_start)
    if idx_end == -1:
        return text
    # Strip leading blank lines before the start marker
    while idx_start > 0 and text[idx_start - 1] == "\n":
        idx_start -= 1
    # Strip trailing newline after end marker
    idx_end += len(end)
    if idx_end < len(text) and text[idx_end] == "\n":
        idx_end += 1
    return text[:idx_start] + text[idx_end:]


def _update_page_section(path: Path, start: str, end: str, new_block: str):
    """Idempotently replace a generated section in a markdown file.

    If the file already has a section delimited by `start`...`end`, replace it.
    Otherwise, append the block at the end.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text() if path.exists() else ""
    text = _strip_generated_section(text, start, end)
    text = text.rstrip()
    text = text + "\n\n" + start + "\n" + new_block.rstrip() + "\n" + end + "\n"
    path.write_text(text)


def update_wikilinks(wiki_root: Path, g: dict):
    """Write ## 关联 blocks to node pages and Mermaid to overview pages.

    Node pages get wikilinks grouped by edge type with relationship labels.
    Overview pages get a repo-level Mermaid diagram.
    """
    node_map = {n["id"]: n for n in g["nodes"]}
    edge_index: dict[str, list[dict]] = {}  # node_id → [edge dicts]
    for e in g["edges"]:
        edge_index.setdefault(e["from"], []).append(e)
        edge_index.setdefault(e["to"], []).append(e)

    repos = sorted({n["repo"] for n in g["nodes"]})
    nodes_dir = wiki_root / "repos"

    for repo in repos:
        repo_nodes = {n["id"]: n for n in g["nodes"] if n["repo"] == repo}

        # --- per-node wikilinks ---
        for node_id, node in sorted(repo_nodes.items()):
            slug = node["slug"]
            page_path = nodes_dir / repo / "nodes" / f"{slug}.md"
            edges = edge_index.get(node_id, [])

            # Group edges by direction+type for labeling
            motivated_by = []  # DesignDecisions that motivate this node
            motivates_out = []  # this DesignDecision motivates others
            targets_out = []   # this ExtensionPoint targets Components
            targeted_by = []   # Components targeted by ExtensionPoints
            same_concept = []  # nodes in other repos with same concept

            for e in edges:
                etype = e["type"]
                if etype == "motivates":
                    if e["to"] == node_id:
                        motivated_by.append(e["from"])
                    else:
                        motivates_out.append(e["to"])
                elif etype == "targets":
                    if e["from"] == node_id:
                        targets_out.append(e["to"])
                    else:
                        targeted_by.append(e["from"])
                elif etype == "embodies":
                    # find siblings (same concept, different repo)
                    concept = e["to"]  # concept:<name>
                    for ee in g["edges"]:
                        if ee["type"] == "embodies" and ee["to"] == concept and ee["from"] != node_id:
                            same_concept.append(ee["from"])

            lines = []
            if motivated_by:
                lines.append("**设计原因**（motivates）：")
                for did in sorted(set(motivated_by)):
                    n = node_map.get(did)
                    label = f"该决策催生了此节点" if n else ""
                    lines.append(f"- [[{did.replace(':', '/nodes/')}]] — {label}")
                lines.append("")
            if motivates_out:
                lines.append("**催生了**（被此决策 motivates）：")
                for nid in sorted(set(motivates_out)):
                    lines.append(f"- [[{nid.replace(':', '/nodes/')}]]")
                lines.append("")
            if targets_out:
                lines.append("**作用于**（targets）：")
                for nid in sorted(set(targets_out)):
                    n = node_map.get(nid)
                    label = f"改动会波及此组件" if n else ""
                    lines.append(f"- [[{nid.replace(':', '/nodes/')}]] — {label}")
                lines.append("")
            if targeted_by:
                lines.append("**被以下扩展点作用于**（被 targets）：")
                for nid in sorted(set(targeted_by)):
                    lines.append(f"- [[{nid.replace(':', '/nodes/')}]]")
                lines.append("")
            if same_concept:
                concept_val = node.get("concept", "")
                lines.append(f"**同属「{concept_val}」的其他仓库实例：**")
                for nid in sorted(set(same_concept)):
                    n = node_map.get(nid)
                    label = n["repo"] if n else ""
                    lines.append(f"- [[{nid.replace(':', '/nodes/')}]] — {label}")
                lines.append("")

            if lines:
                _update_page_section(page_path, _GEN_WIKILINKS_START, _GEN_WIKILINKS_END,
                                     "## 关联\n\n" + "\n".join(lines).rstrip())

        # --- per-repo dimension→node links ---
        # Reverse-index: (repo, dim_slug) → list of node slugs
        dim_links: dict[tuple, list] = {}
        for n in g["nodes"]:
            for dim in n.get("extracted_from", []) or []:
                dim_links.setdefault((n["repo"], dim), []).append(n["slug"])

        for (repo, dim_slug), node_slugs in dim_links.items():
            dim_path = nodes_dir / repo / "dimensions" / f"{repo}-{dim_slug}.md"
            if not dim_path.exists():
                continue
            node_map = {n["id"]: n for n in g["nodes"]}
            lines = []
            for slug in sorted(node_slugs):
                n = node_map.get(f"{repo}:{slug}", {})
                ntype = n.get("node_type", "")
                lines.append(f"- [[{repo}/nodes/{slug}]] — {ntype}")
            _update_page_section(dim_path, _GEN_DIM_LINKS_START, _GEN_DIM_LINKS_END,
                                 "**本维度提取的节点：**\n\n" + "\n".join(lines))

        # --- per-repo Mermaid in overview ---
        mermaid = generate_mermaid(wiki_root, repo)
        overview_path = nodes_dir / repo / "overview.md"
        _update_page_section(overview_path, _GEN_MERMAID_START, _GEN_MERMAID_END,
                             "## 决策链\n\n```mermaid\n" + mermaid + "\n```")
        print(f"graph.py wikilinks: {repo} — {len(repo_nodes)} node pages + overview Mermaid")


def _cmd_build(args):
    wiki_root = Path(args.wiki)
    g = build_graph(wiki_root)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n")
    print(f"graph.py build: {len(g['nodes'])} nodes, {len(g['edges'])} edges → {out_path}")
    if args.update_wikilinks:
        update_wikilinks(wiki_root, g)


def _cmd_query(args):
    wiki_root = Path(args.wiki)
    results = query_impact(wiki_root, args.repo, args.impact)
    if not results:
        print(f"No related nodes found for {args.repo}:{args.impact}")
        return
    print(f"\n## Impact: {args.repo}:{args.impact}\n")
    scope_order = {"system": 0, "subsystem": 1, "component": 2}
    for n in sorted(results, key=lambda x: scope_order.get(x.get("scope", ""), 9)):
        scope_tag = f"[{n['scope']}]" if n.get("scope") else ""
        concept_tag = f" → {n['concept']}" if n.get("concept") else ""
        print(f"  {n['id']}  {n['node_type']} {scope_tag}{concept_tag}")


def _cmd_mermaid(args):
    print(generate_mermaid(Path(args.wiki), args.repo,
                           center_slug=args.center, hops=args.hops))


def main():
    parser = argparse.ArgumentParser(description="Codebase wiki graph operations.")
    sub = parser.add_subparsers(dest="cmd")

    p_build = sub.add_parser("build", help="Scan node pages, write graph.json")
    p_build.add_argument("--wiki", default="wiki")
    p_build.add_argument("--out", default="wiki/graph/graph.json")
    p_build.add_argument("--update-wikilinks", action="store_true",
                         help="Write ## 关联 wikilink blocks to node pages + Mermaid to overview")

    p_query = sub.add_parser("query", help="Graph traversal queries")
    p_query.add_argument("--wiki", default="wiki")
    p_query.add_argument("--impact", required=True, metavar="SLUG",
                         help="Show all nodes related to REPO:SLUG")
    p_query.add_argument("--repo", required=True)

    p_mermaid = sub.add_parser("mermaid", help="Generate Mermaid subgraph snippet")
    p_mermaid.add_argument("repo")
    p_mermaid.add_argument("--wiki", default="wiki")
    p_mermaid.add_argument("--center", default=None, metavar="SLUG",
                           help="Center node slug; if omitted, render whole repo")
    p_mermaid.add_argument("--hops", type=int, default=2)

    args = parser.parse_args()
    if args.cmd == "build":
        _cmd_build(args)
    elif args.cmd == "query":
        _cmd_query(args)
    elif args.cmd == "mermaid":
        _cmd_mermaid(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

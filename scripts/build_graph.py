#!/usr/bin/env python3
"""Build graph.json and graph.html from wikilinks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, DIRS, get_wiki_root
from wiki_common import build_page_index, extract_wikilinks, markdown_files, page_title, parse_frontmatter, read_text, write_text

TYPE_COLORS = {
    "entity": "#e74c3c",
    "concept": "#3498db",
    "comparison": "#2ecc71",
    "query": "#f39c12",
    "synthesis": "#9b59b6",
    "skill": "#16a085",
    "candidate": "#8e44ad",
}

DIR_TYPE = {
    DIRS["实体"]: "entity",
    DIRS["概念"]: "concept",
    DIRS["对比"]: "comparison",
    DIRS["查询"]: "query",
    DIRS["问题索引"]: "question",
    DIRS["技能"]: "skill",
    DIRS["候选"]: "candidate",
    DIRS["投资体系"]: "synthesis",
    DIRS["AI与自动化"]: "synthesis",
    DIRS["香港行动"]: "synthesis",
    DIRS["知识库运营"]: "synthesis",
}


def page_type(path: Path, root: Path, meta: dict[str, str]) -> str:
    if meta.get("type"):
        return meta["type"].strip()
    top = str(path.relative_to(root).parent).replace("\\", "/")
    return DIR_TYPE.get(top, top)


def page_summary(body: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith(">"):
            return line[:120]
    return ""


def build_graph(root: Path) -> tuple[list[dict], list[dict]]:
    page_index = build_page_index(root, ALL_PAGE_DIRS)
    pages: dict[str, dict] = {}
    inbound: dict[str, int] = defaultdict(int)

    for path in markdown_files(root, ALL_PAGE_DIRS):
        content = read_text(path)
        meta, body = parse_frontmatter(content)
        rel = str(path.relative_to(root)).replace("\\", "/")
        links = extract_wikilinks(content)
        pages[path.stem] = {
            "id": path.stem,
            "title": page_title(path, meta),
            "path": rel,
            "type": page_type(path, root, meta),
            "summary": page_summary(body),
            "links": links,
        }
        for link in links:
            target = page_index.get(link)
            if target:
                inbound[target.stem] += 1

    nodes = []
    edges = []
    seen_edges: set[tuple[str, str]] = set()
    for stem, data in sorted(pages.items()):
        outlinks = [page_index[link].stem for link in data["links"] if link in page_index]
        if inbound.get(stem, 0) == 0 and not outlinks:
            continue
        node_type = data["type"]
        nodes.append({
            "id": stem,
            "label": data["title"],
            "path": data["path"],
            "group": node_type,
            "size": max(8, min(40, 8 + inbound.get(stem, 0) * 3)),
            "color": TYPE_COLORS.get(node_type, "#95a5a6"),
            "summary": data["summary"],
            "inbound": inbound.get(stem, 0),
            "outbound": len(outlinks),
        })
        for target in outlinks:
            edge = (stem, target)
            if edge not in seen_edges:
                seen_edges.add(edge)
                edges.append({"from": stem, "to": target})
    return nodes, edges


def render_html(nodes: list[dict], edges: list[dict]) -> str:
    payload = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Knowledge Compiler graph</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; line-height: 1.5; }}
    code, pre {{ background: #f4f4f4; padding: 2px 4px; border-radius: 4px; }}
    .node {{ margin: 8px 0; }}
  </style>
</head>
<body>
  <h1>Knowledge Compiler 知识图谱</h1>
  <p>节点：{len(nodes)}，边：{len(edges)}</p>
  <h2>节点</h2>
  <ul>
    {''.join(f'<li class="node"><strong>{n["label"]}</strong> <code>{n["path"]}</code> 入链 {n["inbound"]} / 出链 {n["outbound"]}</li>' for n in nodes)}
  </ul>
  <h2>原始数据</h2>
  <pre>{payload}</pre>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build wiki graph")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    nodes, edges = build_graph(root)
    meta_dir = root / "_meta"
    write_text(meta_dir / "graph.json", json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2))
    write_text(meta_dir / "graph.html", render_html(nodes, edges))

    print("知识图谱已生成")
    print(f"- 节点: {len(nodes)}")
    print(f"- 边: {len(edges)}")
    print("- 输出: _meta/graph.json, _meta/graph.html")


if __name__ == "__main__":
    main()

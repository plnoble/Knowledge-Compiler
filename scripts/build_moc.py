#!/usr/bin/env python3
"""Generate index.md as a Map of Content for wiki-kb."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, RAW, get_wiki_root
from wiki_common import extract_wikilinks, markdown_files, page_title, parse_frontmatter, read_text, today, write_text


DIR_LABELS = {
    "实体": "人物、机构、产品、指数",
    "概念": "思想、框架、模型",
    "对比": "并排分析",
    "合成": "综合结论",
    "查询": "问答记录",
    "技能": "可复用判断框架",
    "候选": "项目想法",
}


def collect_pages(root: Path) -> list[dict]:
    pages = []
    inbound = Counter()
    raw_pages = []
    for path in markdown_files(root, ALL_PAGE_DIRS + ["问题索引"]):
        content = read_text(path)
        raw_pages.append((path, content))
        for link in extract_wikilinks(content):
            inbound[Path(link).stem] += 1

    for path, content in raw_pages:
        meta, body = parse_frontmatter(content)
        rel = str(path.relative_to(root)).replace("\\", "/")
        top = path.relative_to(root).parts[0]
        summary = ""
        for line in body.splitlines():
            clean = line.strip()
            if clean and not clean.startswith("#") and not clean.startswith(">"):
                summary = clean[:80]
                break
        pages.append({
            "path": rel,
            "stem": path.stem,
            "title": page_title(path, meta),
            "dir": top,
            "type": meta.get("type", ""),
            "status": meta.get("status", ""),
            "confidence": meta.get("confidence", ""),
            "inbound": inbound.get(path.stem, 0),
            "summary": summary,
        })
    return pages


def build_moc(root: Path) -> str:
    pages = collect_pages(root)
    by_dir: dict[str, list[dict]] = {}
    for page in pages:
        by_dir.setdefault(page["dir"], []).append(page)
    for items in by_dir.values():
        items.sort(key=lambda p: (-p["inbound"], p["title"]))

    raw_counts = {}
    for key, rel in RAW.items():
        directory = root / rel
        raw_counts[key] = len(list(directory.glob("*.md"))) if directory.is_dir() else 0

    lines = [
        "# wiki-kb 索引",
        "",
        f"> 自动生成：{today()}",
        "",
        "## 总览",
        "",
        f"- 知识页：{len(pages)}",
        f"- 收件箱：{raw_counts.get('收件箱', 0)}",
        f"- 待审：{raw_counts.get('待审', 0)}",
        "",
        "## 核心页面",
        "",
    ]
    top_pages = sorted(pages, key=lambda p: (-p["inbound"], p["title"]))[:10]
    if top_pages:
        for page in top_pages:
            lines.append(f"- [[{page['stem']}]]（{page['dir']}/，入链 {page['inbound']}）")
    else:
        lines.append("- 暂无页面")

    lines += ["", "## 分类导航", ""]
    for directory in ALL_PAGE_DIRS + ["问题索引"]:
        items = by_dir.get(directory, [])
        lines.append(f"### {directory}")
        if directory in DIR_LABELS:
            lines.append(f"> {DIR_LABELS[directory]}")
        if not items:
            lines.append("- （暂无）")
        else:
            for page in items:
                meta_bits = []
                if page["confidence"]:
                    meta_bits.append(f"confidence: {page['confidence']}")
                if page["status"]:
                    meta_bits.append(f"status: {page['status']}")
                suffix = f" — {'; '.join(meta_bits)}" if meta_bits else ""
                summary = f"：{page['summary']}" if page["summary"] else ""
                lines.append(f"- [[{page['stem']}]]{suffix}{summary}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build wiki-kb MOC index")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    parser.add_argument("--print", action="store_true", help="Print without writing index.md")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    content = build_moc(root)
    if args.print:
        print(content, end="")
        return
    write_text(root / "index.md", content)
    print("MOC 已生成：index.md")


if __name__ == "__main__":
    main()

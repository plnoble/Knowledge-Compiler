#!/usr/bin/env python3
"""Generate confidence report and optionally fill missing confidence fields."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import CHECK_DIRS, get_wiki_root
from wiki_common import ensure_frontmatter, extract_wikilinks, markdown_files, parse_frontmatter, read_text, today, write_text


def calculate_confidence(meta: dict[str, str], body: str, links: list[str]) -> str:
    sources = meta.get("sources", "").strip()
    has_sources = bool(sources and sources not in {"[]", "null", "None"})
    text_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#") and not line.strip().startswith(">")
    ]
    status = meta.get("status", "").lower()
    if status in {"wip", "seed"} and not has_sources:
        return "quarantine"
    if not has_sources and len(text_lines) < 3:
        return "quarantine"
    if not has_sources or len(text_lines) < 8:
        return "low"
    if len(links) >= 4 and len(text_lines) >= 20:
        return "high"
    return "medium"


def build_report(root: Path, fix: bool = False) -> tuple[str, int]:
    rows = []
    counts: Counter[str] = Counter()
    changed = 0

    for path in markdown_files(root, CHECK_DIRS):
        content = read_text(path)
        meta, body = parse_frontmatter(content)
        links = extract_wikilinks(content)
        current = meta.get("confidence", "").lower()
        suggested = calculate_confidence(meta, body, links)
        final = current or suggested
        counts[final] += 1
        rel = str(path.relative_to(root)).replace("\\", "/")
        rows.append((rel, current or "(missing)", suggested, len(links), len(body.splitlines())))

        if fix and not current:
            defaults = {
                "title": meta.get("title", path.stem),
                "created": meta.get("created", today()),
                "updated": meta.get("updated", today()),
                "type": meta.get("type", path.parent.name),
                "tags": meta.get("tags", "[]"),
                "sources": meta.get("sources", "[]"),
                "confidence": suggested,
            }
            new_content, did_change = ensure_frontmatter(content, defaults)
            if did_change:
                write_text(path, new_content)
                changed += 1

    lines = [
        "# 置信度检查报告",
        "",
        f"> 生成时间：{today()}",
        "",
        "## 分布",
        "",
    ]
    for key in ["high", "medium", "low", "quarantine"]:
        lines.append(f"- {key}: {counts.get(key, 0)}")
    lines += ["", "## 页面明细", "", "| 页面 | 当前 | 建议 | 链接数 | 行数 |", "| --- | --- | --- | ---: | ---: |"]
    for rel, current, suggested, link_count, line_count in rows:
        lines.append(f"| `{rel}` | {current} | {suggested} | {link_count} | {line_count} |")
    if not rows:
        lines.append("| （无页面） |  |  | 0 | 0 |")
    return "\n".join(lines) + "\n", changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Check wiki confidence")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    parser.add_argument("--fix", action="store_true", help="Fill missing confidence fields")
    parser.add_argument("--print", action="store_true", help="Print only, do not write report")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    report, changed = build_report(root, fix=args.fix)
    print(report, end="")
    if args.fix:
        print(f"已回填 confidence 字段：{changed} 页")
    if not args.print:
        write_text(root / "_meta" / "confidence-report.md", report)
        print("报告已保存：_meta/confidence-report.md")


if __name__ == "__main__":
    main()

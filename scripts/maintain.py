#!/usr/bin/env python3
"""Conservative maintenance for wiki-kb pages."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, CHECK_DIRS, get_wiki_root
from wiki_common import extract_wikilinks, markdown_files, parse_frontmatter, read_text, render_frontmatter, today, write_text


def add_missing_sources(root: Path, limit: int, dry_run: bool) -> int:
    changed = 0
    for path in markdown_files(root, CHECK_DIRS):
        if changed >= limit:
            break
        content = read_text(path)
        meta, body = parse_frontmatter(content)
        if not meta:
            continue
        if meta.get("sources"):
            continue
        meta["sources"] = "[]"
        meta["updated"] = meta.get("updated", today())
        changed += 1
        if not dry_run:
            write_text(path, render_frontmatter(meta, body))
    return changed


def inbound_counts(root: Path) -> Counter:
    counts: Counter[str] = Counter()
    stems = {path.stem for path in markdown_files(root, ALL_PAGE_DIRS + ["问题索引"])}
    for path in markdown_files(root, ALL_PAGE_DIRS + ["问题索引"]):
        for link in extract_wikilinks(read_text(path)):
            target = Path(link).stem
            if target in stems:
                counts[target] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Maintain wiki-kb metadata")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    parser.add_argument("--limit", type=int, default=500, help="Maximum pages to update")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    changed = add_missing_sources(root, args.limit, args.dry_run)
    inbound = inbound_counts(root)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}维护完成")
    print(f"- 补齐 sources 字段：{changed} 页")
    print("- 入链最高页面：")
    for name, count in inbound.most_common(10):
        print(f"  - [[{name}]]：{count}")
    if not inbound:
        print("  - 暂无入链")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Low-risk automatic fixes for Knowledge Compiler health issues."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, CHECK_DIRS, DIRS, ensure_dirs, get_wiki_root
from wiki_common import build_page_index, ensure_frontmatter, extract_wikilinks, markdown_files, read_text, today, write_text

DIR_TYPE = {
    DIRS["实体"]: "entity",
    DIRS["概念"]: "concept",
    DIRS["对比"]: "comparison",
    DIRS["查询"]: "query",
    DIRS["技能"]: "skill",
    DIRS["候选"]: "candidate",
    DIRS["投资体系"]: "synthesis",
    DIRS["AI与自动化"]: "synthesis",
    DIRS["香港行动"]: "synthesis",
    DIRS["知识库运营"]: "synthesis",
}


def defaults_for(path: Path, root: Path) -> dict[str, str]:
    top = str(path.relative_to(root).parent).replace("\\", "/")
    return {
        "title": path.stem,
        "created": today(),
        "updated": today(),
        "type": DIR_TYPE.get(top, top),
        "tags": "[]",
        "sources": "[]",
        "confidence": "low",
    }


def fix_frontmatter(root: Path, dry_run: bool) -> int:
    changed = 0
    for path in markdown_files(root, CHECK_DIRS):
        content = read_text(path)
        new_content, did_change = ensure_frontmatter(content, defaults_for(path, root))
        if did_change:
            changed += 1
            if not dry_run:
                write_text(path, new_content)
    return changed


def find_broken_links(root: Path) -> list[tuple[str, str]]:
    page_index = build_page_index(root, ALL_PAGE_DIRS + [DIRS["问题索引"]])
    broken = []
    for path in markdown_files(root, ALL_PAGE_DIRS + [DIRS["问题索引"]]):
        rel = str(path.relative_to(root)).replace("\\", "/")
        for link in extract_wikilinks(read_text(path)):
            if link not in page_index:
                broken.append((rel, link))
    return broken


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix low-risk wiki health issues")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    if not args.dry_run:
        ensure_dirs(root)
    frontmatter_count = fix_frontmatter(root, dry_run=args.dry_run)
    broken = find_broken_links(root)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}健康修复完成")
    print(f"- 补齐 frontmatter：{frontmatter_count} 页")
    print(f"- 断链线索：{len(broken)} 条（未自动改写）")
    for rel, link in broken[:20]:
        print(f"  - `{rel}` -> [[{link}]]")
    if len(broken) > 20:
        print(f"  - ... 还有 {len(broken) - 20} 条")


if __name__ == "__main__":
    main()

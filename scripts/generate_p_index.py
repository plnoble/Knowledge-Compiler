#!/usr/bin/env python3
"""Generate lightweight P-index question pages for uncovered wiki pages."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import DIRS, get_wiki_root
from wiki_common import markdown_files, page_title, parse_frontmatter, read_text, today, write_text

DEFAULT_SOURCE_DIRS = ["概念", "实体"]
INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def safe_filename(value: str) -> str:
    cleaned = "".join("-" if ch in INVALID_FILENAME_CHARS else ch for ch in value)
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    cleaned = cleaned.strip(".-")
    return cleaned or "question"


def existing_question_text(question_dir: Path) -> str:
    parts = []
    if question_dir.is_dir():
        for path in sorted(question_dir.glob("*.md")):
            parts.append(read_text(path))
    return "\n".join(parts)


def is_covered(page: Path, root: Path, question_text: str) -> bool:
    stem = page.stem
    rel = str(page.relative_to(root).with_suffix("")).replace("\\", "/")
    return f"[[{stem}]]" in question_text or f"[[{rel}]]" in question_text


def render_question(title: str, page_stem: str, source_rel: str) -> str:
    question = f"什么是 {title}？"
    return f"""---
title: {question}
created: {today()}
updated: {today()}
type: question
status: draft
tags: [问题索引]
answer_quality: draft
related: [[{page_stem}]]
---

# {question}

## 可回答的问题

- {question}

## 当前答案入口

- [[{page_stem}]]

## 维护提示

- 来源页面：`{source_rel}`
- 当答案稳定后，补充更具体的变体问题，并把 `answer_quality` 从 `draft` 调整为 `partial` 或 `stable`。
"""


def generate(root: Path, limit: int, dry_run: bool) -> dict[str, int]:
    question_dir = root / DIRS["问题索引"]
    question_dir.mkdir(parents=True, exist_ok=True)
    question_text = existing_question_text(question_dir)

    source_files = markdown_files(root, DEFAULT_SOURCE_DIRS)
    generated = 0
    skipped = 0

    for page in source_files:
        if generated >= limit:
            break
        if is_covered(page, root, question_text):
            skipped += 1
            continue

        meta, _ = parse_frontmatter(read_text(page))
        title = page_title(page, meta)
        filename = safe_filename(f"什么是-{title}") + ".md"
        target = question_dir / filename
        if target.exists():
            skipped += 1
            continue

        source_rel = str(page.relative_to(root)).replace("\\", "/")
        content = render_question(title, page.stem, source_rel)
        if not dry_run:
            write_text(target, content)
            question_text += "\n" + content
        print(f"generated {target.relative_to(root)} -> [[{page.stem}]]")
        generated += 1

    return {"generated": generated, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate P-index question pages")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    parser.add_argument("--limit", type=int, default=20, help="Maximum question pages to create")
    parser.add_argument("--dry-run", action="store_true", help="Print planned files without writing")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    result = generate(root, max(args.limit, 0), args.dry_run)
    prefix = "DRY_RUN" if args.dry_run else "P_INDEX_OK"
    print(f"{prefix} generated={result['generated']} skipped={result['skipped']}")


if __name__ == "__main__":
    main()

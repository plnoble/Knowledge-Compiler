#!/usr/bin/env python3
"""Merge an approved semantic review draft into a manual page with backup."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ARCHIVE_BACKUPS, get_wiki_root, normalize_rel_path, resolve_vault_path
from wiki_common import parse_frontmatter, read_text, render_frontmatter, today, write_text


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def extract_section(body: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s+|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def ensure_manual_frontmatter(content: str, fallback_title: str) -> tuple[dict[str, str], str]:
    meta, body = parse_frontmatter(content)
    if not meta:
        meta = {
            "title": fallback_title,
            "type": "synthesis",
            "created": today(),
        }
        body = content
    meta["updated"] = today()
    meta["last_verified"] = today()
    meta["review_after"] = (date.today() + timedelta(days=90)).isoformat()
    return meta, body


def merge(root: Path, draft: Path, allow_review: bool = False) -> Path:
    text = read_text(draft)
    meta, body = parse_frontmatter(text)
    status = meta.get("status", "").lower()
    if status != "approved" and not allow_review:
        raise PermissionError("draft status must be approved; pass --allow-review to override")

    target_rel = normalize_rel_path(meta.get("target_path", "").strip())
    if not target_rel:
        raise ValueError("draft missing target_path")
    target = root / target_rel
    target.parent.mkdir(parents=True, exist_ok=True)

    backup_dir = root / ARCHIVE_BACKUPS / "review-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backup_dir / f"{stamp}-{target.name}"
        shutil.copy2(target, backup)
        existing = read_text(target)
    else:
        existing = f"# {target.stem}\n"

    manual_meta, manual_body = ensure_manual_frontmatter(existing, target.stem)
    source_summary = extract_section(body, "来源摘要")
    manual_update = extract_section(body, "手册更新建议")
    risk = extract_section(body, "风险与边界")
    source = meta.get("inbox_source", "")
    block = f"""

## 待审合并 {today()} - {meta.get('title', draft.stem)}

### 来源

- `{source}`
- `{rel_to_root(root, draft)}`

### 来源摘要

{source_summary or '（无摘要）'}

### 手册更新建议

{manual_update or '（无手册更新建议）'}

### 风险与边界

{risk or '（无风险边界记录）'}
"""
    write_text(target, render_frontmatter(manual_meta, manual_body.rstrip() + block))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge approved semantic review content into a manual page")
    parser.add_argument("draft", help="Approved semantic review draft")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    parser.add_argument("--allow-review", action="store_true", help="Allow merging a draft that is still status: review")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    draft = resolve_vault_path(root, args.draft)
    try:
        target = merge(root, draft, args.allow_review)
    except (PermissionError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(2)
    print(f"MERGE_OK target={rel_to_root(root, target)}")


if __name__ == "__main__":
    main()

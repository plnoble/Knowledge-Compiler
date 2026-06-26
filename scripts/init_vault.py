#!/usr/bin/env python3
"""Initialize a wiki-kb vault structure."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import DIRS, META_FILES, RAW, ensure_dirs, get_wiki_root
from wiki_common import today, write_text


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    write_text(path, content)
    return True


def load_manifest(path: Path) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}


def ensure_manifest(path: Path) -> bool:
    data = load_manifest(path)
    changed = False
    if not data:
        data = {"version": 1, "created": today()}
        changed = True
    for key, default in {
        "sources": {},
        "hashes": {},
        "address_map": {},
    }.items():
        if key not in data or not isinstance(data[key], dict):
            data[key] = default
            changed = True
    if changed or not path.exists():
        write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return True
    return False


def index_template() -> str:
    sections = "\n\n".join(f"## {name}\n\n- （暂无）" for name in DIRS)
    return f"# wiki-kb Index\n\n{sections}\n"


def schema_template() -> str:
    return """# wiki-kb Schema

## Core Page Fields

- `title`: human-readable page title.
- `created`: YYYY-MM-DD creation date.
- `updated`: YYYY-MM-DD update date.
- `type`: entity, concept, comparison, synthesis, query, skill, candidate, question, or source.
- `tags`: short topic labels.
- `sources`: source links or local raw paths.
- `confidence`: low, medium, high.

## Review Flow

Drafts generated from raw material go to `raw/待审/` with `status: review`.
After human review, set `status: approved` or `status: rejected`.
"""


def personal_context_template() -> str:
    return """# Personal Context

This file guides semantic compilation. Keep it short and factual.

## Interests

- Investment frameworks, risk controls, and tool ideas.
- Codex and AI automation workflows.
- Hong Kong actions that match my own travel, account-opening, and planning interests.

## Not Interested

- Generic travel lists unrelated to my saved sources.
- Unreviewed financial buy/sell recommendations.

## Default Boundaries

- Investment content is educational: explain strategy, conditions, risks, and checklists.
- Official knowledge pages require review before merge.
- Deep Research is gap-triggered, not automatic for every source.
"""


def init_vault(root: Path) -> dict[str, int]:
    root.mkdir(parents=True, exist_ok=True)

    managed_dirs = [*DIRS.values(), *RAW.values(), "_meta", "_archive/review-backups"]
    before_dirs = {rel: (root / rel).exists() for rel in managed_dirs}
    ensure_dirs(root)
    (root / "_archive" / "review-backups").mkdir(parents=True, exist_ok=True)
    created_dirs = sum(1 for rel, existed in before_dirs.items() if not existed and (root / rel).is_dir())

    created_files = 0
    created_files += write_if_missing(root / "SCHEMA.md", schema_template())
    created_files += write_if_missing(root / "index.md", index_template())
    created_files += write_if_missing(root / "log.md", f"# 操作日志\n\n## [{today()}] 初始化 wiki-kb vault\n")
    created_files += write_if_missing(root / META_FILES["hot"], "# 热缓存\n\n暂无热缓存。\n")
    created_files += write_if_missing(root / META_FILES["agenda"], "# 研究议程\n\n- [ ] 处理 `raw/收件箱/` 中的新资料。\n")
    created_files += write_if_missing(root / "_meta" / "personal-context.md", personal_context_template())
    created_files += ensure_manifest(root / META_FILES["manifest"])

    return {"created_dirs": int(created_dirs), "created_files": int(created_files)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a wiki-kb vault")
    parser.add_argument("--root", "--wiki-root", help="Vault root; defaults to detected wiki root")
    parser.add_argument("--print", action="store_true", dest="print_paths", help="Print created structure")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    result = init_vault(root)

    print(f"INIT_OK root={root}")
    print(f"created_dirs={result['created_dirs']}")
    print(f"created_files={result['created_files']}")
    if args.print_paths:
        for rel in [*DIRS.values(), *RAW.values(), "_meta"]:
            print(f"dir {rel}")
        for rel in ["SCHEMA.md", "index.md", "log.md", *META_FILES.values()]:
            print(f"file {rel}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Migrate an old wiki-kb vault into the 0-7 Knowledge Compiler layout."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import (
    ARCHIVE_BACKUPS,
    ARCHIVE_FINISHED_PROJECTS,
    ARCHIVE_SOURCES,
    ARCHIVE_STALE_KNOWLEDGE,
    AREA_AI_AUTOMATION,
    AREA_HONG_KONG,
    AREA_INVESTMENT,
    AREA_UNCLASSIFIED_SYNTHESIS,
    DAILY_DIR,
    INBOX_PENDING,
    INBOX_REVIEW,
    LEGACY_MAP,
    LEGACY_MANUAL_MAP,
    PROJECT_ACTIVE,
    PROJECT_CANDIDATES,
    PROJECT_PAUSED,
    RESOURCE_COMPARISON,
    RESOURCE_CONCEPT,
    RESOURCE_ENTITY,
    RESOURCE_P_INDEX,
    RESOURCE_QUERY,
    SKILLS_ROOT,
    TEMPLATES_DIR,
    ensure_dirs,
    normalize_rel_path,
    rel_to_root,
)
from wiki_common import read_text, write_text


@dataclass(frozen=True)
class MovePlan:
    source: Path
    target: Path


DIRECTORY_RULES = [
    # Previous 0-6 compile-knowledge layout.
    ("3 - Resources（资源）/实体", RESOURCE_ENTITY),
    ("3 - Resources（资源）/概念", RESOURCE_CONCEPT),
    ("3 - Resources（资源）/对比", RESOURCE_COMPARISON),
    ("3 - Resources（资源）/查询", RESOURCE_QUERY),
    ("3 - Resources（资源）/问题索引", RESOURCE_P_INDEX),
    ("3 - Resources（资源）/技能", SKILLS_ROOT),
    ("1 - Projects（项目）/候选", PROJECT_CANDIDATES),
    ("1 - Projects（项目）/活跃项目", PROJECT_ACTIVE),
    ("1 - Projects（项目）/已暂停", PROJECT_PAUSED),
    ("4 - Archives（归档）/已归档来源", ARCHIVE_SOURCES),
    ("4 - Archives（归档）/已结束项目", ARCHIVE_FINISHED_PROJECTS),
    ("4 - Archives（归档）/过时知识", ARCHIVE_STALE_KNOWLEDGE),
    ("4 - Archives（归档）/系统备份", ARCHIVE_BACKUPS),
    ("5 - Templates（模板）", TEMPLATES_DIR),
    ("6 - Daily（日记）", DAILY_DIR),

    # English v1/v2 raw source paths.
    ("raw/inbox", INBOX_PENDING),
    ("raw/articles", INBOX_PENDING),
    ("raw/papers", INBOX_PENDING),
    ("raw/transcripts", INBOX_PENDING),
    ("raw/assets", INBOX_PENDING),
    ("raw/review", INBOX_REVIEW),
    ("raw/processed", ARCHIVE_SOURCES),

    # Old raw/Chinese source paths.
    ("raw/收件箱", INBOX_PENDING),
    ("raw/论文", INBOX_PENDING),
    ("raw/笔记", INBOX_PENDING),
    ("raw/资产", INBOX_PENDING),
    ("raw/待审", INBOX_REVIEW),
    ("raw/已归档", ARCHIVE_SOURCES),
    ("实体", RESOURCE_ENTITY),
    ("概念", RESOURCE_CONCEPT),
    ("对比", RESOURCE_COMPARISON),
    ("查询", RESOURCE_QUERY),
    ("问题索引", RESOURCE_P_INDEX),
    ("技能", SKILLS_ROOT),
    ("候选", PROJECT_CANDIDATES),
    ("日记", DAILY_DIR),
    ("_archive", ARCHIVE_BACKUPS),
]


OLD_DIRS_FOR_CLEANUP = [
    "3 - Resources（资源）/技能/待审",
    "3 - Resources（资源）/技能",
    "3 - Resources（资源）/问题索引",
    "3 - Resources（资源）/查询",
    "3 - Resources（资源）/对比",
    "3 - Resources（资源）/概念",
    "3 - Resources（资源）/实体",
    "3 - Resources（资源）",
    "1 - Projects（项目）/候选",
    "1 - Projects（项目）/活跃项目",
    "1 - Projects（项目）/已暂停",
    "1 - Projects（项目）",
    "4 - Archives（归档）/已归档来源",
    "4 - Archives（归档）/已结束项目",
    "4 - Archives（归档）/过时知识",
    "4 - Archives（归档）/系统备份/review-backups",
    "4 - Archives（归档）/系统备份",
    "4 - Archives（归档）",
    "5 - Templates（模板）",
    "6 - Daily（日记）",
    "raw/inbox",
    "raw/articles",
    "raw/papers",
    "raw/transcripts",
    "raw/assets",
    "raw/review",
    "raw/processed",
    "raw/收件箱",
    "raw/论文",
    "raw/笔记",
    "raw/资产",
    "raw/待审",
    "raw/已归档",
    "raw",
    "实体",
    "概念",
    "对比",
    "查询",
    "问题索引",
    "技能/待审",
    "技能",
    "候选",
    "日记",
    "合成",
    "_archive/review-backups",
    "_archive",
]


def synthesis_target(rel: Path) -> str:
    name = rel.as_posix()
    if name == "投资策略手册.md":
        return f"{AREA_INVESTMENT}/{rel.name}"
    if name == "Codex操作手册.md":
        return f"{AREA_AI_AUTOMATION}/{rel.name}"
    if name == "香港行动指南.md":
        return f"{AREA_HONG_KONG}/{rel.name}"
    return f"{AREA_UNCLASSIFIED_SYNTHESIS}/{name}"


def unique_target(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def plan_directory(root: Path, old_rel: str, new_rel: str) -> list[MovePlan]:
    source_dir = root / old_rel
    if not source_dir.is_dir():
        return []
    plans: list[MovePlan] = []
    for source in sorted(path for path in source_dir.rglob("*") if path.is_file()):
        rel = source.relative_to(source_dir)
        plans.append(MovePlan(source, root / new_rel / rel))
    return plans


def build_plan(root: Path) -> list[MovePlan]:
    plans: list[MovePlan] = []
    for old_rel, new_rel in DIRECTORY_RULES:
        plans.extend(plan_directory(root, old_rel, new_rel))

    synthesis_dir = root / "合成"
    if synthesis_dir.is_dir():
        for source in sorted(path for path in synthesis_dir.rglob("*") if path.is_file()):
            rel = source.relative_to(synthesis_dir)
            plans.append(MovePlan(source, root / synthesis_target(rel)))

    deduped: list[MovePlan] = []
    seen_sources: set[Path] = set()
    for plan in plans:
        if plan.source not in seen_sources:
            seen_sources.add(plan.source)
            deduped.append(plan)
    return deduped


def move_files(plans: list[MovePlan]) -> int:
    moved = 0
    for plan in plans:
        if not plan.source.exists():
            continue
        target = unique_target(plan.target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(plan.source), str(target))
        moved += 1
    return moved


def rewrite_markdown_text(text: str) -> str:
    updated = text
    for old, new in LEGACY_MANUAL_MAP.items():
        updated = updated.replace(old, new)
    for old, new in sorted(LEGACY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if old in LEGACY_MANUAL_MAP:
            continue
        updated = updated.replace(f"[[{old}/", f"[[{new}/")
        if old.startswith("raw/") or old.startswith("_archive") or old.isascii() or (old[:1].isdigit() and old[1:4] == " - "):
            updated = updated.replace(f"{old}/", f"{new}/")
    return updated


def looks_like_path(value: str) -> bool:
    return "/" in value and not value.startswith(("http://", "https://"))


def rewrite_json_paths(value: Any) -> Any:
    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, item in value.items():
            new_key = normalize_rel_path(key) if looks_like_path(key) else key
            rewritten[new_key] = rewrite_json_paths(item)
        return rewritten
    if isinstance(value, list):
        return [rewrite_json_paths(item) for item in value]
    if isinstance(value, str) and looks_like_path(value):
        return normalize_rel_path(value)
    return value


def rewrite_files(root: Path) -> int:
    changed = 0
    for path in sorted(root.rglob("*.md")):
        text = read_text(path)
        rewritten = rewrite_markdown_text(text)
        if rewritten != text:
            write_text(path, rewritten)
            changed += 1

    manifest = root / "_meta" / "manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = None
        if data is not None:
            rewritten_data = rewrite_json_paths(data)
            if rewritten_data != data:
                write_text(manifest, json.dumps(rewritten_data, ensure_ascii=False, indent=2) + "\n")
                changed += 1
    return changed


def clean_empty_old_dirs(root: Path) -> int:
    cleaned = 0
    for rel in sorted(OLD_DIRS_FOR_CLEANUP, key=lambda item: item.count("/"), reverse=True):
        path = root / rel
        if path.is_dir():
            try:
                path.rmdir()
                cleaned += 1
            except OSError:
                pass
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate an old vault into the Knowledge Compiler 0-7 layout")
    parser.add_argument("--root", "--wiki-root", required=True, help="Vault root")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true", help="Print the move plan without writing")
    action.add_argument("--apply", action="store_true", help="Apply the migration")
    args = parser.parse_args()

    root = Path(args.root)
    plans = build_plan(root)

    if args.dry_run:
        print(f"MIGRATE_PLAN root={root} moves={len(plans)}")
        for plan in plans:
            print(f"MOVE {rel_to_root(root, plan.source)} -> {rel_to_root(root, plan.target)}")
        return

    ensure_dirs(root)
    moved = move_files(plans)
    rewritten = rewrite_files(root)
    cleaned = clean_empty_old_dirs(root)
    print(f"MIGRATE_OK root={root} moved={moved} rewritten={rewritten} cleaned_dirs={cleaned}")


if __name__ == "__main__":
    main()

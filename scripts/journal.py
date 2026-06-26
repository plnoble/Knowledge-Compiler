#!/usr/bin/env python3
"""
journal.py — 日记管理器

用法：
  python3 scripts/journal.py              # 创建或打开今天的日记
  python3 scripts/journal.py --date 2026-06-20   # 指定日期
  python3 scripts/journal.py --extract   # 从最近日记提炼值得沉淀的内容（打印建议）
  python3 scripts/journal.py --list      # 列出最近 10 篇日记
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import get_wiki_root, DIRS

JOURNAL_DIR = DIRS["日记"]

JOURNAL_TEMPLATE = """\
---
title: {date} 日记
created: {date}
updated: {date}
type: journal
tags: [日记]
---

# {date}

## 今日

## 想法 / 碎片

## 值得沉淀到知识库的内容
<!-- 如果这里有值得整理的内容，告诉 Minis：「从日记提炼知识 {date}」 -->
"""


def find_wiki_root(args) -> Path:
    return get_wiki_root(override=getattr(args, "wiki_root", None))


def get_journal_path(root: Path, target_date: date) -> Path:
    journal_dir = root / JOURNAL_DIR
    journal_dir.mkdir(parents=True, exist_ok=True)
    return journal_dir / f"{target_date.isoformat()}.md"


def create_or_open(root: Path, target_date: date) -> Path:
    """创建当天日记（如不存在），返回路径。"""
    path = get_journal_path(root, target_date)
    if not path.exists():
        content = JOURNAL_TEMPLATE.format(date=target_date.isoformat())
        path.write_text(content, encoding="utf-8")
        print(f"✅ 日记已创建: {JOURNAL_DIR}/{path.name}")
    else:
        print(f"📖 日记已存在: {JOURNAL_DIR}/{path.name}")
    return path


def list_journals(root: Path, count: int = 10) -> None:
    """列出最近 N 篇日记。"""
    journal_dir = root / JOURNAL_DIR
    if not journal_dir.exists():
        print("📭 日记目录不存在")
        return

    journals = sorted(journal_dir.glob("????-??-??.md"), reverse=True)
    if not journals:
        print("📭 还没有日记")
        return

    print(f"📚 最近 {min(count, len(journals))} 篇日记：\n")
    today = date.today()
    for j in journals[:count]:
        try:
            j_date = date.fromisoformat(j.stem)
            delta = (today - j_date).days
            age = "今天" if delta == 0 else f"{delta} 天前"
        except ValueError:
            age = ""
        size = j.stat().st_size
        print(f"  {j.stem}  ({age}, {size} 字节)")


def extract_insights(root: Path, days: int = 7) -> None:
    """扫描最近 N 天日记，找出「值得沉淀」部分，打印提炼建议。"""
    journal_dir = root / JOURNAL_DIR
    if not journal_dir.exists():
        print("📭 日记目录不存在")
        return

    cutoff = date.today() - timedelta(days=days)
    candidates = []

    for j in sorted(journal_dir.glob("????-??-??.md"), reverse=True):
        try:
            j_date = date.fromisoformat(j.stem)
        except ValueError:
            continue
        if j_date < cutoff:
            break

        content = j.read_text(encoding="utf-8")
        # 找「值得沉淀」段落
        if "值得沉淀" in content:
            lines = content.split("\n")
            in_section = False
            section_lines = []
            for line in lines:
                if "值得沉淀" in line and line.startswith("#"):
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("#"):
                        break
                    if line.strip() and not line.startswith("<!--"):
                        section_lines.append(line)

            non_empty = [l for l in section_lines if l.strip()]
            if non_empty:
                candidates.append((j.stem, non_empty))

    if not candidates:
        print(f"📭 最近 {days} 天日记中没有标记「值得沉淀」的内容")
        return

    print(f"\n💡 最近 {days} 天日记中值得沉淀的内容：\n")
    for j_date_str, lines in candidates:
        print(f"  📅 {j_date_str}:")
        for line in lines[:5]:
            print(f"     {line}")
        if len(lines) > 5:
            print(f"     ... 还有 {len(lines) - 5} 行")
        print()

    print("📝 建议操作：")
    print(f"   告诉 Minis：「从日记提炼知识 {candidates[0][0]}」")
    print("   Minis 会读取日记内容，提炼实体和概念，走正常加工流程")


def main():
    parser = argparse.ArgumentParser(description="日记管理器")
    parser.add_argument("--wiki-root", help="wiki 根目录路径")
    parser.add_argument("--date", help="目标日期（YYYY-MM-DD），默认今天")
    parser.add_argument("--list", action="store_true", help="列出最近 10 篇日记")
    parser.add_argument("--extract", action="store_true", help="从最近 7 天日记提炼知识建议")
    parser.add_argument("--days", type=int, default=7, help="提炼范围（天数），默认 7")
    args = parser.parse_args()

    root = get_wiki_root(override=args.wiki_root)

    if args.list:
        list_journals(root)
        return

    if args.extract:
        extract_insights(root, days=args.days)
        return

    # 默认：创建/确认今天的日记
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ 日期格式错误: {args.date}，请使用 YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = date.today()

    path = create_or_open(root, target_date)
    print(f"\n💡 提示：在日记底部「值得沉淀」段落记录值得整理的内容")
    print(f"   之后告诉 Minis：「从日记提炼知识 {target_date}」即可触发加工")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Report pages whose review date is due without modifying those pages."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, get_wiki_root
from wiki_common import markdown_files, parse_frontmatter, read_text, today, write_text


SCAN_DIRS = ALL_PAGE_DIRS + ["合成"]


def parse_date(value: str) -> date | None:
    value = value.strip().strip('"')
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def collect_due(root: Path) -> list[dict[str, str]]:
    due: list[dict[str, str]] = []
    today_date = date.today()
    for path in markdown_files(root, SCAN_DIRS):
        meta, _ = parse_frontmatter(read_text(path))
        review_after = parse_date(meta.get("review_after", ""))
        if review_after and review_after <= today_date:
            due.append(
                {
                    "rel": str(path.relative_to(root)).replace("\\", "/"),
                    "title": meta.get("title", path.stem).strip('"'),
                    "review_after": review_after.isoformat(),
                    "validity": meta.get("validity", "unspecified"),
                }
            )
    return sorted(due, key=lambda item: (item["review_after"], item["rel"]))


def render_report(due: list[dict[str, str]]) -> str:
    lines = [
        "# 过时复查报告",
        "",
        f"> generated: {today()}",
        "",
        "复查动作只建议，不自动删除或重写正式页面。",
        "",
        "## 处理选项",
        "",
        "- 保留 / 降级 / 合并 / 归档",
        "",
        "## 到期页面",
        "",
    ]
    if not due:
        lines.append("- 暂无到期页面。")
    else:
        for item in due:
            lines.append(
                f"- [[{Path(item['rel']).stem}]] `{item['rel']}` review_after={item['review_after']} validity={item['validity']}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report stale wiki pages that need review")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    due = collect_due(root)
    report_path = root / "_meta" / "stale-review.md"
    write_text(report_path, render_report(due))
    print(f"STALE_REVIEW_OK due={len(due)} report=_meta/stale-review.md")


if __name__ == "__main__":
    main()

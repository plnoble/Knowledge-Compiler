#!/usr/bin/env python3
"""Detect explicit contradiction markers and simple conflicting numeric claims."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, get_wiki_root
from wiki_common import markdown_files, parse_frontmatter, read_text, write_text


def explicit_contradictions(root: Path) -> list[tuple[str, str]]:
    findings = []
    pattern = re.compile(r"^>\s*\[!(?:矛盾|contradiction)\](.*)$", re.IGNORECASE | re.MULTILINE)
    for path in markdown_files(root, ALL_PAGE_DIRS):
        content = read_text(path)
        meta, _ = parse_frontmatter(content)
        rel = str(path.relative_to(root)).replace("\\", "/")
        if meta.get("contradictions") not in (None, "", "[]"):
            findings.append((rel, f"frontmatter contradictions: {meta['contradictions']}"))
        for match in pattern.finditer(content):
            findings.append((rel, match.group(1).strip() or "[!矛盾]"))
    return findings


def numeric_claims(root: Path) -> dict[str, list[tuple[str, str]]]:
    claim_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    pattern = re.compile(r"(\d+(?:\.\d+)?\s*(?:%|年|月|天|倍|万|亿|元|美元|人|次))")
    for path in markdown_files(root, ALL_PAGE_DIRS):
        rel = str(path.relative_to(root)).replace("\\", "/")
        for line in read_text(path).splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("---"):
                continue
            for value in pattern.findall(clean):
                claim_index[value].append((rel, clean[:160]))
    return {value: claims for value, claims in claim_index.items() if len({path for path, _ in claims}) > 1}


def build_report(root: Path) -> str:
    explicit = explicit_contradictions(root)
    repeated_numbers = numeric_claims(root)
    lines = [
        "# 矛盾检测报告",
        "",
        "## 显式矛盾标注",
        "",
        f"- 共 {len(explicit)} 处",
    ]
    for rel, summary in explicit[:50]:
        lines.append(f"- `{rel}`: {summary}")
    if len(explicit) > 50:
        lines.append(f"- ... 还有 {len(explicit) - 50} 处")

    lines += [
        "",
        "## 重复数字声明（人工复核线索）",
        "",
        f"- 共 {len(repeated_numbers)} 个重复数字值",
    ]
    for value, claims in list(repeated_numbers.items())[:20]:
        lines.append(f"### {value}")
        for rel, claim in claims[:5]:
            lines.append(f"- `{rel}`: {claim}")
    if not explicit and not repeated_numbers:
        lines += ["", "未发现显式矛盾或明显重复数字线索。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect wiki contradictions")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    parser.add_argument("--save", action="store_true", help="Save report to _meta/contradictions-report.md")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    report = build_report(root)
    print(report, end="")
    if args.save:
        write_text(root / "_meta" / "contradictions-report.md", report)
        print("报告已保存：_meta/contradictions-report.md")


if __name__ == "__main__":
    main()

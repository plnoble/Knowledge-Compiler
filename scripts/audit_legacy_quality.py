#!/usr/bin/env python3
"""Create a first-pass quality audit for legacy generated resource pages."""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, os.path.dirname(__file__))
from wiki_common import read_text, write_text
from wiki_dirs import (
    RESOURCE_COMPARISON,
    RESOURCE_CONCEPT,
    RESOURCE_ENTITY,
    get_wiki_root,
    rel_to_root,
)


AREA_KEYWORDS = {
    "投资体系": ["投资", "网格", "ETF", "估值", "仓位", "策略", "基金", "股票", "债券", "资产", "收益", "风险"],
    "AI与自动化": ["AI", "Codex", "Claude", "自动化", "Agent", "prompt", "workflow", "模型", "工具", "脚本"],
    "香港行动": ["香港", "开户", "港股", "银行", "旅游", "签证", "保险", "券商"],
    "知识库运营": ["知识库", "Obsidian", "笔记", "检索", "索引", "MOC", "模板", "整理"],
}


def pick_evenly(files: list[Path], count: int) -> list[Path]:
    if count <= 0:
        return []
    if len(files) <= count:
        return files
    positions = [round(index * (len(files) - 1) / (count - 1)) for index in range(count)]
    result: list[Path] = []
    seen: set[int] = set()
    for position in positions:
        if position not in seen:
            seen.add(position)
            result.append(files[position])
    for path in files:
        if len(result) >= count:
            break
        if path not in result:
            result.append(path)
    return result[:count]


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def title_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower())


def detect_areas(blob: str) -> list[str]:
    lower_blob = blob.lower()
    matches = []
    for area, keywords in AREA_KEYWORDS.items():
        if any(keyword.lower() in lower_blob for keyword in keywords):
            matches.append(area)
    return matches


def collect_titles(files: list[Path]) -> Counter[str]:
    titles: Counter[str] = Counter()
    for path in files:
        text = read_text(path)
        page_title = frontmatter(text).get("title") or path.stem
        key = title_key(page_title)
        if key:
            titles[key] += 1
    return titles


def inspect_page(root: Path, kind: str, path: Path, duplicate_titles: set[str]) -> dict[str, Any]:
    text = read_text(path)
    fm = frontmatter(text)
    nonempty_lines = [line for line in text.splitlines() if line.strip()]
    wikilinks = re.findall(r"\[\[([^\]]+)\]\]", text)
    headings = re.findall(r"^#{1,6}\s+", text, re.M)
    sources = fm.get("sources", "")
    has_sources = bool(sources and sources not in {"[]", "null", "None"}) or "来自 [[" in text or "source:" in text.lower()
    confidence = fm.get("confidence", "missing")
    page_title = fm.get("title") or path.stem

    flags = []
    if not has_sources:
        flags.append("来源缺失")
    if confidence in {"missing", "low", "quarantine"}:
        flags.append("低/缺置信度")
    if len(nonempty_lines) < 12:
        flags.append("内容偏短")
    if len(headings) < 2:
        flags.append("结构不足")
    if title_key(page_title) in duplicate_titles:
        flags.append("疑似重名")
    if not wikilinks:
        flags.append("缺少链接")

    areas = detect_areas(f"{page_title}\n{text[:2000]}")
    if areas:
        flags.append("可映射到 " + "、".join(areas[:2]))

    if "来源缺失" in flags and ("内容偏短" in flags or "结构不足" in flags):
        suggestion = "补源后重编译"
    elif "疑似重名" in flags:
        suggestion = "合并/去重"
    elif areas and kind == "概念":
        suggestion = "进入对应 Areas 复核"
    elif not has_sources:
        suggestion = "降置信度并补源"
    else:
        suggestion = "保留待复核"

    return {
        "kind": kind,
        "path": rel_to_root(root, path),
        "sources": "有" if has_sources else "无",
        "confidence": confidence,
        "lines": len(nonempty_lines),
        "links": len(wikilinks),
        "flags": "；".join(flags) if flags else "未见明显问题",
        "suggestion": suggestion,
    }


def build_report(root: Path, report_date: str, samples: list[tuple[str, list[Path], int]]) -> tuple[str, dict[str, int]]:
    all_files = [path for _kind, files, _count in samples for path in files]
    duplicate_titles = {key for key, count in collect_titles(all_files).items() if count > 1}

    rows: list[dict[str, Any]] = []
    for kind, files, count in samples:
        for path in pick_evenly(files, count):
            rows.append(inspect_page(root, kind, path, duplicate_titles))

    summary = {
        "sampled": len(rows),
        "missing_sources": sum(1 for row in rows if row["sources"] == "无"),
        "low_confidence": sum(1 for row in rows if "低/缺置信度" in row["flags"]),
        "short_or_weak": sum(1 for row in rows if "内容偏短" in row["flags"] or "结构不足" in row["flags"]),
        "area_candidates": sum(1 for row in rows if "可映射到" in row["flags"]),
        "recompile": sum(1 for row in rows if row["suggestion"] == "补源后重编译"),
    }

    lines = [
        "---",
        "title: 旧知识质量抽样报告",
        "type: audit-report",
        "status: review",
        f"created: {report_date}",
        "scope: legacy-resources-sample",
        "---",
        "",
        f"# 旧知识质量抽样报告 - {report_date}",
        "",
        "## 范围",
        "",
        "本报告只读抽样旧知识页，不直接修改正式 Resources、Areas、Projects 或 Skills。",
        "",
    ]
    for kind, files, count in samples:
        lines.append(f"- {kind}：抽样 {min(count, len(files))}/{len(files)} 页")
    lines.extend(
        [
            "",
            "## 总览",
            "",
            f"- 抽样总数：{summary['sampled']} 页",
            f"- 来源缺失：{summary['missing_sources']} 页",
            f"- 低/缺置信度：{summary['low_confidence']} 页",
            f"- 内容偏短或结构不足：{summary['short_or_weak']} 页",
            f"- 可映射到 Areas：{summary['area_candidates']} 页",
            f"- 建议补源后重编译：{summary['recompile']} 页",
            "",
            "## 判定口径",
            "",
            "- 来源完整：frontmatter `sources` 非空，或正文存在明确来源链接。",
            "- 可用结构：至少有正文、标题层级和基本链接，能被后续 Area 汇总引用。",
            "- 个人价值：优先看是否能进入投资体系、AI与自动化、香港行动或知识库运营。",
            "- 处理原则：旧页先视为待验证知识；高价值主题从原始来源重新编译，低来源页先降置信度或补源。",
            "",
            "## 抽样明细",
            "",
            "| 类型 | 文件 | 来源 | 置信度 | 行数 | 链接 | 标记 | 建议 |",
            "|---|---|---:|---|---:|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['kind']} | `{row['path']}` | {row['sources']} | {row['confidence']} | "
            f"{row['lines']} | {row['links']} | {row['flags']} | {row['suggestion']} |"
        )
    lines.extend(
        [
            "",
            "## 下一步建议",
            "",
            "1. 先处理投资体系、AI与自动化、香港行动三个高价值方向的旧页。",
            "2. 对来源缺失但有价值的旧页，标记为 `confidence: low` 和 `needs_source: true` 后补源。",
            "3. 对能追溯到原始文章的主题，从 `0 - Inbox/待处理` 或已归档来源重新走 Inbox -> Resources，生成 Source Coverage Map 与 Impact Review。",
            "4. 每批重审输出先进入 `0 - Inbox/待审/`，通过后再更新正式 Resources 或 Areas。",
            "",
        ]
    )
    return "\n".join(lines), summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit legacy generated Resources with a deterministic sample")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    parser.add_argument("--concept-count", type=int, default=30)
    parser.add_argument("--entity-count", type=int, default=10)
    parser.add_argument("--comparison-count", type=int, default=5)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output", help="Output report path, vault-relative or absolute")
    args = parser.parse_args()

    root = get_wiki_root(args.root)
    samples = [
        ("概念", sorted((root / RESOURCE_CONCEPT).glob("*.md")), args.concept_count),
        ("实体", sorted((root / RESOURCE_ENTITY).glob("*.md")), args.entity_count),
        ("对比", sorted((root / RESOURCE_COMPARISON).glob("*.md")), args.comparison_count),
    ]
    report, summary = build_report(root, args.date, samples)

    output = Path(args.output) if args.output else root / "_meta" / f"legacy-quality-audit-{args.date}.md"
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text(output, report)
    print(
        "AUDIT_OK "
        f"path={rel_to_root(root, output)} "
        f"sampled={summary['sampled']} "
        f"missing_sources={summary['missing_sources']} "
        f"low_confidence={summary['low_confidence']} "
        f"area_candidates={summary['area_candidates']}"
    )


if __name__ == "__main__":
    main()

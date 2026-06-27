#!/usr/bin/env python3
"""Promote a candidate suggestion from a semantic review draft."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import DIRS, get_wiki_root, resolve_vault_path
from wiki_common import parse_frontmatter, read_text, slugify, today, write_text


FIELD_RE = re.compile(r"^-\s*([a-zA-Z_]+):\s*(.*)$")


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def parse_candidates(body: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    sections = re.split(r"^###\s+候选\s+\d+\s*$", body, flags=re.MULTILINE)
    for section in sections[1:]:
        data: dict[str, str] = {}
        for line in section.splitlines():
            match = FIELD_RE.match(line.strip())
            if match:
                data[match.group(1)] = match.group(2).strip()
        if data.get("name"):
            candidates.append(data)
    return candidates


def render_card(data: dict[str, str], source: str, draft_rel: str) -> str:
    name = data.get("name", "未命名候选")
    kind = data.get("candidate_kind", "workflow")
    fit = data.get("personal_fit", "medium")
    cost = data.get("validation_cost", "medium")
    evidence = data.get("evidence_count", "1")
    why = data.get("why", "从语义待审稿中提升。")
    return f"""---
title: 候选：{name}
created: {today()}
updated: {today()}
type: candidate
status: suggested
candidate_kind: {kind}
evidence_count: {evidence}
linked_knowledge: []
personal_fit: {fit}
validation_cost: {cost}
sources: [{source}]
---

# 候选：{name}

## 核心机会

{why}

## 证据来源

- `{source}`
- `{draft_rel}`

## 需要验证的假设

1. 这个候选是否解决真实、重复出现的问题？
2. 现有知识是否足够支撑第一版？
3. 验证成本是否匹配个人优先级？

## 项目评估

- 解决什么问题：{why}
- 个人匹配度：{fit}
- 证据数量：{evidence}
- 验证成本：{cost}
- 潜在价值：待评估
- 下一步最小验证动作：用 30 分钟写出最小检查清单或手动流程。
- 是否已有类似候选：待检索

## 状态更新

- {today()}：从语义待审稿提升为 suggested 候选卡。
"""


def promote(root: Path, draft: Path, index: int) -> Path:
    text = read_text(draft)
    meta, body = parse_frontmatter(text)
    candidates = parse_candidates(body)
    if index < 1 or index > len(candidates):
        raise IndexError(f"candidate index {index} out of range")
    data = candidates[index - 1]
    source = data.get("source") or meta.get("inbox_source", "")

    output_dir = root / DIRS["候选"]
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = slugify(data.get("name", "candidate"), "candidate") + ".md"
    output = output_dir / filename
    counter = 2
    while output.exists():
        output = output_dir / f"{Path(filename).stem}-{counter}.md"
        counter += 1
    write_text(output, render_card(data, source, rel_to_root(root, draft)))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a candidate suggestion from a semantic review draft")
    parser.add_argument("draft", help="Semantic review draft path")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    parser.add_argument("--index", type=int, default=1, help="1-based candidate suggestion index")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    draft = resolve_vault_path(root, args.draft)
    try:
        output = promote(root, draft, args.index)
    except (IndexError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(2)
    print(f"CANDIDATE_OK file={rel_to_root(root, output)}")


if __name__ == "__main__":
    main()

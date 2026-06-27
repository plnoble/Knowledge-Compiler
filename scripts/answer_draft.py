#!/usr/bin/env python3
"""Create a review-gated query draft from a knowledge-backed answer."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_common import append_log_top, slugify, today, write_text
from wiki_dirs import RAW, RESOURCE_QUERY, get_wiki_root, rel_to_root


def unique_answer_path(review_dir: Path, stem: str) -> Path:
    base = review_dir / f"{stem}.answer.md"
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = review_dir / f"{stem}.answer-{index}.md"
        if not candidate.exists():
            return candidate
        index += 1


def yaml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    escaped = [value.replace('"', '\\"') for value in values]
    return "[" + ", ".join(f'"{value}"' for value in escaped) + "]"


def render_answer_draft(question: str, answer: str, sources: list[str], target_path: str) -> str:
    title = question.strip()[:60] or "未命名问题"
    return f"""---
title: 问答沉淀：{title}
created: {today()}
updated: {today()}
type: query
status: review
workflow: answer-review
target_path: {target_path}
review_decision: pending
tags: [待审, answer-review, 查询]
sources: {yaml_list(sources)}
confidence: low
---

# 问答沉淀待审：{title}

## 问题

{question.strip()}

## 回答

{answer.strip()}

## 库内已有

- 待审：列出回答中来自个人知识库的已知事实、链接和原始来源。

## 推断建议

- 待审：列出基于库内资料推断出的行动建议，并说明推断链条。

## 外部补充

- 待审：列出回答中来自外部常识、临时搜索或模型补充的内容；未验证前不得写入正式查询页。

## 仍需研究

- 待审：列出会影响答案准确性的缺口、时效问题和冲突点。

## 审阅决定

- [ ] 批准沉淀到 `1 - Resources（资源）/查询/`
- [ ] 需要补充来源
- [ ] 需要 Deep Research
- [ ] 不保存
"""


def create_answer_draft(root: Path, question: str, answer: str, sources: list[str], title: str | None = None) -> Path:
    review_dir = root / RAW["待审"]
    review_dir.mkdir(parents=True, exist_ok=True)
    stem_source = title or question
    stem = slugify(stem_source, "answer")
    review_path = unique_answer_path(review_dir, stem)
    target_path = f"{RESOURCE_QUERY}/{stem}.md"
    write_text(review_path, render_answer_draft(question, answer, sources, target_path))
    append_log_top(
        root,
        "问答沉淀待审",
        [
            f"- review: `{rel_to_root(root, review_path)}`",
            f"- target: `{target_path}`",
        ],
    )
    return review_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a review-only query draft from an answer")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    parser.add_argument("--question", required=True, help="Original user question")
    parser.add_argument("--answer", required=True, help="Answer to preserve for review")
    parser.add_argument("--source", action="append", default=[], help="Related vault source path; repeatable")
    parser.add_argument("--title", help="Optional title/slug seed")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    review = create_answer_draft(root, args.question, args.answer, args.source, args.title)
    stem = review.name.split(".answer", 1)[0]
    print(f"ANSWER_DRAFT_OK review_file={rel_to_root(root, review)} target_path={RESOURCE_QUERY}/{stem}.md")


if __name__ == "__main__":
    main()

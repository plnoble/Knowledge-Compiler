#!/usr/bin/env python3
"""Create a semantic review draft from an inbox source."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import RAW, get_wiki_root
from wiki_common import append_log_top, slugify, today, write_text


DOMAIN_RULES = [
    {
        "domain": "投资体系",
        "manual": "合成/投资策略手册.md",
        "keywords": [
            "理财",
            "投资",
            "网格",
            "ETF",
            "基金",
            "仓位",
            "资产",
            "板块",
            "收益",
            "风险",
            "finance",
            "financial",
            "grid",
            "strategy",
            "portfolio",
            "position",
            "allocation",
            "asset",
            "market",
            "risk",
            "fund",
            "rebalancing",
        ],
        "risk": "不构成投资建议；只沉淀策略原理、适用条件、风险、参数和检查清单。",
        "questions": ["这个策略适合什么市场环境？", "它的主要风险和失效条件是什么？"],
        "candidate": ("自动网格策略工具", "software", "medium", "medium"),
    },
    {
        "domain": "AI与自动化",
        "manual": "合成/Codex操作手册.md",
        "keywords": ["codex", "openai", "agent", "ai", "llm", "prompt", "workflow", "automation", "debug", "调试", "自动化"],
        "risk": "工具技巧具有时效性；需要记录版本、适用界面和复查日期。",
        "questions": ["这个技巧解决什么 Codex 操作问题？", "它适用于哪些任务和限制？"],
        "candidate": ("Codex工作流自动化", "workflow", "medium", "low"),
    },
    {
        "domain": "香港与出行",
        "manual": "合成/香港行动指南.md",
        "keywords": ["香港", "开户", "旅游", "行程", "港卡", "交通", "签注", "购物", "路线", "hong kong", "hk", "bank account", "travel", "itinerary"],
        "risk": "开户、交通和旅行信息具有时效性；需要复查日期和个人兴趣匹配。",
        "questions": ["这条信息能支持香港哪类行动？", "步骤、限制和证件要求是什么？"],
        "candidate": ("香港行动候选", "trip", "high", "medium"),
    },
]


def resolve_source(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def keyword_matches(lowered_text: str, keyword: str) -> bool:
    lowered_keyword = keyword.lower()
    if lowered_keyword.isascii() and any(char.isalnum() for char in lowered_keyword):
        pattern = rf"(?<![a-z0-9]){re.escape(lowered_keyword)}(?![a-z0-9])"
        return re.search(pattern, lowered_text) is not None
    return lowered_keyword in lowered_text


def choose_domain(text: str) -> dict:
    lowered = text.lower()
    best_rule = DOMAIN_RULES[-1]
    best_score = -1
    for rule in DOMAIN_RULES:
        score = sum(1 for keyword in rule["keywords"] if keyword_matches(lowered, keyword))
        if score > best_score:
            best_rule = rule
            best_score = score
    if best_score <= 0:
        return {
            "domain": "知识管理",
            "manual": "合成/个人知识手册.md",
            "keywords": [],
            "risk": "缺少明确领域；先保守沉淀为个人知识管理素材。",
            "questions": ["这份资料回答了什么个人问题？", "它应该更新哪个已有主题？"],
            "candidate": ("知识库改进候选", "workflow", "medium", "low"),
        }
    return best_rule


def sentence_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "（原文为空，需人工补充摘要。）"
    return cleaned[:180] + ("..." if len(cleaned) > 180 else "")


def unique_review_path(review_dir: Path, stem: str) -> Path:
    base = review_dir / f"{stem}.semantic.md"
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = review_dir / f"{stem}.semantic-{index}.md"
        if not candidate.exists():
            return candidate
        index += 1


def render_candidate(rule: dict, source_rel: str) -> str:
    name, kind, fit, cost = rule["candidate"]
    return f"""### 候选 1
- name: {name}
- candidate_kind: {kind}
- status: suggested
- evidence_count: 1
- personal_fit: {fit}
- validation_cost: {cost}
- source: {source_rel}
- why: 这份资料暴露了可工具化、可行动化或可复用的机会；先建议待审，不直接创建候选卡。
"""


def render_review(source: Path, source_rel: str, hash_key: str, text: str, rule: dict) -> str:
    title = source.stem.replace("-", " ").replace("_", " ").strip() or source.stem
    p_questions = "\n".join(f"- {q}" for q in rule["questions"])
    candidate = render_candidate(rule, source_rel)
    return f"""---
title: 语义编译：{title}
created: {today()}
updated: {today()}
type: source
status: review
workflow: semantic-compile
domain: {rule['domain']}
target_path: {rule['manual']}
merge_mode: append-section
review_decision: pending
tags: [待审, semantic-compile, {rule['domain']}]
sources: [{source_rel}]
confidence: low
inbox_source: {source_rel}
source_hash: {hash_key}
---

# 语义编译待审：{title}

## 来源摘要

{sentence_summary(text)}

## 核心知识

- 待 AI/人工审阅：提炼这份资料真正改变的知识，而不是复制原文。
- 优先识别可复用框架、适用条件、边界、反例和个人相关性。

## 知识更新建议

- 检查 `index.md` 和相关页面；同主题优先更新旧页，不重复创建。
- 若新增概念或实体，保持 `status: review`，批准后再入正式目录。

## 手册更新建议

- target_path: `{rule['manual']}`
- merge_mode: `append-section`
- 建议写入：当前结论、操作步骤、适用场景、风险/限制、来源索引。

## P-index 问题

{p_questions}

## Deep Research 缺口

- 仅当发现冲突、关键概念缺定义、时效信息或多次重复但未成熟的主题时触发。
- 当前建议：先人工判断是否存在缺口；不要因为每篇资料都自动研究。

## 候选卡建议

{candidate}

## 风险与边界

- {rule['risk']}
- 正式知识页、手册页和候选卡都需要审阅后再写入。

## 审阅决定

- [ ] 批准知识更新
- [ ] 批准手册合并
- [ ] 批准候选卡建议
- [ ] 需要 Deep Research
- [ ] 退回重做

## 原文

{text.rstrip()}
"""


def compile_source(root: Path, source: Path) -> Path:
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    raw = source.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    hash_key = "sha256:" + hashlib.sha256(raw).hexdigest()
    rule = choose_domain(text)

    review_dir = root / RAW["待审"]
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = unique_review_path(review_dir, slugify(source.stem, "source"))
    source_rel = rel_to_root(root, source)
    write_text(review_path, render_review(source, source_rel, hash_key, text, rule))
    append_log_top(root, "语义编译待审稿", [f"- source: `{source_rel}`", f"- review: `{rel_to_root(root, review_path)}`"])
    return review_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a semantic review draft from an inbox source")
    parser.add_argument("source", help="Source file path, absolute or relative to wiki root")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    try:
        review = compile_source(root, resolve_source(root, args.source))
    except FileNotFoundError as exc:
        print(f"ERROR source_not_found {exc}", file=sys.stderr)
        sys.exit(2)
    print(f"COMPILE_OK review_file={rel_to_root(root, review)}")


if __name__ == "__main__":
    main()

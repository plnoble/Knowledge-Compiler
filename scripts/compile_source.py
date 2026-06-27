#!/usr/bin/env python3
"""Create a semantic review draft and coverage map from an inbox source."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import (
    AREA_AI_AUTOMATION,
    AREA_HONG_KONG,
    AREA_INVESTMENT,
    AREA_KB_OPS,
    RAW,
    get_wiki_root,
    rel_to_root,
    resolve_vault_path,
)
from wiki_common import append_log_top, detect_source_kind, slugify, today, write_text


DOMAIN_RULES = [
    {
        "domain": "投资体系",
        "manual": f"{AREA_INVESTMENT}/投资策略手册.md",
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
        "manual": f"{AREA_AI_AUTOMATION}/Codex操作手册.md",
        "keywords": ["codex", "openai", "agent", "ai", "llm", "prompt", "workflow", "automation", "debug", "调试", "自动化"],
        "risk": "工具技巧具有时效性；需要记录版本、适用界面和复查日期。",
        "questions": ["这个技巧解决什么 Codex 操作问题？", "它适用于哪些任务和限制？"],
        "candidate": ("Codex工作流自动化", "workflow", "medium", "low"),
    },
    {
        "domain": "香港行动",
        "manual": f"{AREA_HONG_KONG}/香港行动指南.md",
        "keywords": ["香港", "开户", "旅游", "行程", "港卡", "交通", "签注", "购物", "路线", "hong kong", "hk", "bank account", "travel", "itinerary"],
        "risk": "开户、交通和旅行信息具有时效性；需要复查日期和个人兴趣匹配。",
        "questions": ["这条信息能支持香港哪类行动？", "步骤、限制和证件要求是什么？"],
        "candidate": ("香港行动候选", "trip", "high", "medium"),
    },
]


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
            "domain": "知识库运营",
            "manual": f"{AREA_KB_OPS}/个人知识手册.md",
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


def coverage_path_for(review_path: Path) -> Path:
    if review_path.name.endswith(".semantic.md"):
        return review_path.with_name(review_path.name.replace(".semantic.md", ".coverage.md"))
    return review_path.with_suffix(".coverage.md")


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


def render_impact_review(rule: dict) -> str:
    return f"""## Impact Review / 影响面审查

### 可能新增的 Resources

- 待审：根据 Source Coverage Map 提炼新的实体、概念、对比、查询或问题索引。

### 可能更新的 Resources

- 待审：检索同主题 Resources 后确认是否更新已有页面，避免重复造页。

### 可能影响的 Areas

- `{rule['manual']}`：批准后按新增结论、更新结论、冲突结论、过时内容和仍需研究的问题合并。

### 可能影响的 Projects

- 待审：若候选卡建议被批准，再进入 `3 - Projects（项目）/候选/`。

### 可能影响的 Skills

- 待审：若资料改变适用场景、判断步骤、反例或失效条件，再进入 `4 - Skills（技能）/待审/`。

### 冲突或过时内容

- 待审：发现冲突时标记 `[!矛盾]`；发现过时内容时建议移入或关联 `5 - Archives（归档）/过时知识/`。

### 不更新原因

- 待审：若重复、证据不足、个人相关性低、时效不明或质量不足，在这里记录不沉淀原因。

### 仍需研究的问题

- 待审：只列出会影响正式知识判断的问题，不把泛泛好奇心变成研究任务。
"""


def render_review(source: Path, source_rel: str, hash_key: str, text: str, rule: dict, source_kind: str) -> str:
    title = source.stem.replace("-", " ").replace("_", " ").strip() or source.stem
    p_questions = "\n".join(f"- {q}" for q in rule["questions"])
    candidate = render_candidate(rule, source_rel)
    impact_review = render_impact_review(rule)
    return f"""---
title: 语义编译：{title}
created: {today()}
updated: {today()}
type: source
status: review
workflow: semantic-compile
source_kind: {source_kind}
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

{impact_review}

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


def source_points(text: str) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip(" -\t")]
    points: list[str] = []
    for line in lines:
        if line.startswith("#"):
            continue
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned:
            points.append(cleaned[:160] + ("..." if len(cleaned) > 160 else ""))
        if len(points) >= 20:
            break
    return points or ["（原文为空或无法抽取；需人工确认是否有可沉淀信息。）"]


def render_coverage(source: Path, source_rel: str, review_rel: str, hash_key: str, text: str, rule: dict, source_kind: str) -> str:
    rows = "\n".join(
        f"| {point.replace('|', '/')} | 待审 | {rule['manual']} | 需审阅后确认是否沉淀 |"
        for point in source_points(text)
    )
    title = source.stem.replace("-", " ").replace("_", " ").strip() or source.stem
    return f"""---
title: Source Coverage Map：{title}
created: {today()}
updated: {today()}
type: source-coverage
status: review
workflow: source-coverage
source_kind: {source_kind}
domain: {rule['domain']}
inbox_source: {source_rel}
source_hash: {hash_key}
related_review: {review_rel}
target_path: {rule['manual']}
tags: [待审, coverage-map, {rule['domain']}]
---

# Source Coverage Map：{title}

| 原文要点 | 是否沉淀 | 目标 Resource | 未处理原因 |
| --- | --- | --- | --- |
{rows}
"""


def compile_source(root: Path, source: Path) -> Path:
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    raw = source.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    hash_key = "sha256:" + hashlib.sha256(raw).hexdigest()
    rule = choose_domain(text)
    source_kind = detect_source_kind(source, text)

    review_dir = root / RAW["待审"]
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = unique_review_path(review_dir, slugify(source.stem, "source"))
    source_rel = rel_to_root(root, source)
    review_rel = rel_to_root(root, review_path)
    coverage_path = coverage_path_for(review_path)
    write_text(review_path, render_review(source, source_rel, hash_key, text, rule, source_kind))
    write_text(coverage_path, render_coverage(source, source_rel, review_rel, hash_key, text, rule, source_kind))
    append_log_top(
        root,
        "语义编译待审稿",
        [
            f"- source: `{source_rel}`",
            f"- review: `{review_rel}`",
            f"- coverage: `{rel_to_root(root, coverage_path)}`",
        ],
    )
    return review_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a semantic review draft and Source Coverage Map")
    parser.add_argument("source", help="Source file path, absolute or relative to wiki root")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    try:
        review = compile_source(root, resolve_vault_path(root, args.source))
    except FileNotFoundError as exc:
        print(f"ERROR source_not_found {exc}", file=sys.stderr)
        sys.exit(2)
    print(f"COMPILE_OK review_file={rel_to_root(root, review)} coverage_file={rel_to_root(root, coverage_path_for(review))}")


if __name__ == "__main__":
    main()

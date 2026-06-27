#!/usr/bin/env python3
"""
deep_research.py — Deep Research 联网研究助手 v3

工作流：
  1. 接收研究主题（由用户或 Minis AI 提供）
  2. 接收 AI 联网搜索结果（通过 --result-file 或 stdin）
  3. 与知识库现有内容做差异分析（BM25 搜索）
  4. 生成结构化研究报告，写入 0 - Inbox/待处理/
  5. 打印后续加工建议

注意：联网搜索本身由 Minis AI 完成，本脚本负责：
  - 初始化研究任务（生成研究议程）
  - 接收搜索结果并整合
  - 写入 Inbox + 日志

用法：
  # 模式1：初始化研究任务（打印议程，Minis AI 去搜索）
  python3 scripts/deep_research.py "MCP 协议最新进展"

  # 模式2：整合搜索结果（Minis AI 搜索完成后调用）
  python3 scripts/deep_research.py "MCP 协议最新进展" --result-file /path/to/results.md

  # 模式3：通过 stdin 接收结果
  echo "搜索结果内容..." | python3 scripts/deep_research.py "MCP 协议最新进展" --from-stdin
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import get_wiki_root, DIRS, RAW, META_FILES


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def find_wiki_root() -> Path:
    return get_wiki_root()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_raw = parts[1].strip()
            body = parts[2].lstrip("\n")
            for line in fm_raw.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
    return meta, body


def append_log(wiki_root: Path, entry: str) -> None:
    log_path = wiki_root / "log.md"
    today = date.today().isoformat()
    block = f"\n## [{today}] {entry}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(block)


# ──────────────────────────────────────────────
# BM25 差异分析（简化版）
# ──────────────────────────────────────────────

def find_related_pages(wiki_root: Path, query: str, limit: int = 5) -> list[tuple[str, Path]]:
    """
    用简单的关键词匹配找出与查询相关的已有页面。
    如果安装了 rank_bm25，使用 BM25；否则退回关键词计数。
    """
    query_terms = set(query.lower().split())
    if len(query_terms) < 2:
        query_terms = set(query.lower())

    search_dirs = [
        wiki_root / DIRS["概念"],
        wiki_root / DIRS["实体"],
        wiki_root / DIRS["技能"],
    ]

    scored = []
    for d in search_dirs:
        if not d.exists():
            continue
        for md_file in d.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8").lower()
                score = sum(content.count(term) for term in query_terms)
                if score > 0:
                    rel = str(md_file.relative_to(wiki_root)).replace("\\", "/")
                    scored.append((score, rel, md_file))
            except Exception:
                pass

    scored.sort(reverse=True)
    return [(rel, path) for _, rel, path in scored[:limit]]


# ──────────────────────────────────────────────
# 生成研究议程（模式1）
# ──────────────────────────────────────────────

def generate_research_agenda(query: str, wiki_root: Path) -> None:
    """打印研究议程，指导 Minis AI 进行联网搜索。"""
    related = find_related_pages(wiki_root, query)

    print(f"\n📋 Deep Research 议程：{query}\n")
    print("=" * 60)
    print("\n建议搜索策略（请 Minis AI 执行联网搜索）：\n")
    print(f"  1. 主题概览: \"{query} 最新进展 2024\"")
    print(f"  2. 深度内容: \"{query} 详解 原理\"")
    print(f"  3. 实践案例: \"{query} 实践 案例 经验\"")
    print(f"  4. 比较分析: \"{query} vs 替代方案\"")

    if related:
        print(f"\n已有相关知识（搜索时注意差异）：")
        for rel, _ in related:
            print(f"  - [[{Path(rel).stem}]]（{rel}）")
    else:
        print(f"\n知识库中暂无 \"{query}\" 相关内容，新知识将直接入库。")

    print(f"\n搜索完成后，运行：")
    print(f"  python3 scripts/deep_research.py \"{query}\" --result-file <结果文件>")
    print(f"  或: Minis AI 直接调用工作流 6（Deep Research）")


# ──────────────────────────────────────────────
# 整合搜索结果，写入 inbox（模式2/3）
# ──────────────────────────────────────────────

def write_research_report(
    query: str,
    result_content: str,
    wiki_root: Path,
) -> Path:
    """整合搜索结果，生成结构化研究报告写入 Inbox。"""
    today = date.today().isoformat()
    today_compact = date.today().strftime("%Y%m%d")

    # 找相关已有页面
    related = find_related_pages(wiki_root, query)

    # 生成文件名
    query_slug = query.lower().replace(" ", "-")
    query_slug = "".join(c for c in query_slug if c.isalnum() or c == "-")
    filename = f"research-{query_slug}-{today_compact}.md"

    # 差异分析提示
    if related:
        diff_note = "与现有知识的差异分析（请 AI 加工时填写）：\n"
        for rel, path in related:
            try:
                existing = path.read_text(encoding="utf-8")
                _, body = parse_frontmatter(existing)
                excerpt = body[:200].strip()
                diff_note += f"\n- [[{Path(rel).stem}]]: {excerpt[:100]}...\n"
            except Exception:
                pass
    else:
        diff_note = "知识库中暂无相关内容，所有内容均为新知识。\n"

    report = f"""---
title: Research: {query}
created: {today}
updated: {today}
type: research
status: 收件箱
source_kind: other
tags: [research, 收件箱]
sources: []
research_query: {query}
---

# Research: {query}

<!-- 来源：Deep Research 联网搜索
     加工时：请提炼核心发现，识别实体和概念，决定创建或更新哪些知识页。 -->

## 研究摘要

（3-5 句话核心发现——请 AI 加工时填写）

## 搜索结果原文

{result_content}

---

## 与现有知识库的对比

{diff_note}

## 相关已有页面

{"".join(f"- [[{Path(rel).stem}]] ({rel})\\n" for rel, _ in related) if related else "- 暂无相关页面"}

## 建议加工方向

<!-- AI 加工时根据内容决定 -->
- 建议新增页面：（待分析）
- 建议更新页面：{"、".join(f"[[{Path(rel).stem}]]" for rel, _ in related[:3]) if related else "（暂无）"}
"""

    # 写入 Inbox/待处理/
    inbox_dir = wiki_root / RAW["收件箱"]
    inbox_dir.mkdir(parents=True, exist_ok=True)
    output_path = inbox_dir / filename
    output_path.write_text(report, encoding="utf-8")

    return output_path


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deep Research 联网研究助手")
    parser.add_argument("query", help="研究主题")
    parser.add_argument("--wiki-root", help="wiki 根目录路径（默认自动检测）")
    parser.add_argument("--result-file", help="包含搜索结果的 Markdown 文件路径")
    parser.add_argument("--from-stdin", action="store_true", help="从 stdin 读取搜索结果")
    parser.add_argument("--agenda-only", action="store_true", help="仅打印研究议程，不写入文件")
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root) if args.wiki_root else find_wiki_root()

    # 模式1：仅生成议程
    if args.agenda_only or (not args.result_file and not args.from_stdin):
        generate_research_agenda(args.query, wiki_root)

        # 同时创建一个"研究中"占位文件
        today_compact = date.today().strftime("%Y%m%d")
        query_slug = args.query.lower().replace(" ", "-")
        query_slug = "".join(c for c in query_slug if c.isalnum() or c == "-")
        placeholder_name = f"research-{query_slug}-{today_compact}.md"

        inbox_dir = wiki_root / RAW["收件箱"]
        inbox_dir.mkdir(parents=True, exist_ok=True)
        placeholder_path = inbox_dir / placeholder_name

        if not placeholder_path.exists():
            placeholder_content = f"""---
title: Research: {args.query}
created: {date.today().isoformat()}
type: research
status: researching
source_kind: other
tags: [research, inbox]
research_query: {args.query}
---

# Research: {args.query}

<!-- 研究进行中，等待 Minis AI 完成联网搜索后填充内容。 -->
"""
            placeholder_path.write_text(placeholder_content, encoding="utf-8")
            print(f"\n✅ 研究任务已初始化: {RAW['收件箱']}/{placeholder_name}")
        return

    # 模式2/3：整合搜索结果
    result_content = ""
    if args.from_stdin:
        result_content = sys.stdin.read().strip()
        if not result_content:
            print("❌ stdin 内容为空")
            sys.exit(1)
    elif args.result_file:
        result_path = Path(args.result_file)
        if not result_path.exists():
            print(f"❌ 结果文件不存在: {result_path}")
            sys.exit(1)
        result_content = result_path.read_text(encoding="utf-8")

    output_path = write_research_report(args.query, result_content, wiki_root)
    rel_path = output_path.relative_to(wiki_root)

    print(f"\n✅ 研究报告已写入: {rel_path}")
    print(f"\n📝 下一步（加工）：")
    print(f"   告诉 Minis：「加工 {rel_path} 这篇文章」")
    print(f"   AI 会提取实体和概念，生成待审稿到 {RAW['待审']}/")

    # 写日志
    append_log(wiki_root, f"Deep Research: {args.query} → {rel_path}")


if __name__ == "__main__":
    main()

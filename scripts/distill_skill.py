#!/usr/bin/env python3
"""
distill_skill.py — Skill 蒸馏器 v3

从 1-3 篇高置信度 Resources 知识页提炼「可复用判断框架」。
生成 Skill 草稿存入 4 - Skills（技能）/待审/，等待人工审阅。

用法：
  python3 scripts/distill_skill.py "1 - Resources（资源）/概念/资产配置.md"
  python3 scripts/distill_skill.py --wiki-root /path/to/wiki "1 - Resources（资源）/概念/etf.md"
  python3 scripts/distill_skill.py --list-candidates   # 列出可蒸馏的高质量页面
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import DIRS, get_wiki_root, resolve_vault_path


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
    """append log entry to log.md（新条目前插到顶部）。"""
    log_path = wiki_root / "log.md"
    today = date.today().isoformat()
    block = f"## [{today}] {entry}\n"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        first_h2 = existing.find("\n## [")
        if first_h2 >= 0:
            content = existing[:first_h2 + 1] + block + "\n" + existing[first_h2 + 1:]
        else:
            content = existing.rstrip() + "\n\n" + block
    else:
        content = f"# 操作日志\n\n{block}"
    log_path.write_text(content, encoding="utf-8")


def infer_domain(tags: str, page_type: str, content: str) -> str:
    """从标签和内容推断 Skill 领域。"""
    invest_keywords = ["etf", "投资", "基金", "估值", "指数", "资产", "配置", "收益", "风险"]
    ai_keywords = ["agent", "llm", "ai", "知识", "自动化", "模型", "prompt", "工具"]
    content_lower = (tags + content).lower()
    invest_score = sum(1 for k in invest_keywords if k in content_lower)
    ai_score = sum(1 for k in ai_keywords if k in content_lower)
    if invest_score > ai_score:
        return "investment"
    elif ai_score > 0:
        return "ai-automation"
    return "knowledge-management"


# ──────────────────────────────────────────────
# 核心：生成 Skill 草稿模板
# ──────────────────────────────────────────────

def generate_skill_draft(
    sources: list[tuple[Path, dict, str]],
    wiki_root: Path,
    skill_name: str,
) -> str:
    """
    根据来源页面内容生成 Skill 草稿 Markdown。
    注意：实际内容由 Minis AI 填充，这里生成带「占位提示」的结构化模板，
    供 AI 在对话中直接填写，或作为 Minis 调用 LLM 时的输出格式。
    """
    today = date.today().isoformat()

    # 收集来源信息
    source_refs = []
    domain_votes = []
    all_content = ""
    for src_path, meta, body in sources:
        rel = str(src_path.relative_to(wiki_root)).replace("\\", "/")
        source_refs.append(rel)
        domain_votes.append(infer_domain(meta.get("tags", ""), meta.get("type", ""), body[:500]))
        all_content += body + "\n\n"

    domain = max(set(domain_votes), key=domain_votes.count) if domain_votes else "knowledge-management"
    domain_tag_map = {
        "investment": "投资",
        "ai-automation": "AI与自动化",
        "knowledge-management": "知识管理",
    }
    domain_tag = domain_tag_map.get(domain, domain)

    sources_yaml = "[" + ", ".join(f"{s}" for s in source_refs) + "]"
    wikilinks = "\n".join(
        f"- [[{p.stem}]]"
        for p, _, _ in sources
    )

    # 提取来源内容摘要，给 AI 参考
    source_excerpts = ""
    for src_path, meta, body in sources:
        excerpt = body[:600].strip()
        source_excerpts += f"\n<!-- 来源：{src_path.stem}\n{excerpt}\n-->\n"

    return f"""---
title: Skill：{skill_name}
created: {today}
updated: {today}
type: skill
domain: {domain}
tags: [skill, {domain_tag}]
sources: {sources_yaml}
confidence: medium
status: review
---

# Skill：{skill_name}

<!-- AI 填写说明：根据以下来源内容，提炼可复用的判断框架。
     聚焦「判断规则」而非知识摘要。规则必须有来源支撑，零幻觉。

《 M3 可证伪质量标准（ljskill-knowledge 引进）》
好的 Skill 规则必须：
  ✅ 可证伪：《PE < 15 时考虑买入》（有数值，可验证）
  ✅ 场景具体：《适用于成熟稳定型指数，不适用于行业 ETF》
  ❌ 不是鸡汤：《要长期持有》、《要有耐心》（无法指导决策）

{source_excerpts}-->

一句话说明这个 Skill 解决什么判断问题。

## 判断规则（正向信号）

> ⚠️ 每条规则必须可证伪！恢复：《X 时做 Y》形式，有具体数值或判断条件

- 规则 1：当出现 X 时，表明 Y（来源：[[{sources[0][0].stem if sources else "来源页面"}]]）
- 规则 2：...
- 规则 3：...

## 反模式（负向信号）

- 误判 1：当看到 A 时，不要误以为 B，因为...
- 误判 2：...

## 能力边界

- **适用场景**：（具体条件，不是“永远适用”）
- **不适用场景**：（具体例外）
- **不确定区域**：需要更多数据或人工判断的情况

## 关键数据点

- 数据/阈值 1（来源：[[来源页面]]）
- 数据/阈值 2

## 可证伪性自检（审阅前请确认）

- [ ] 每条规则都有具体数值或可验证的条件？
- [ ] 没有《要努力》、《要耐心》这种鸡汤表述？
- [ ] 场景是具体的，而非《永远适用》？
- [ ] 每条规则都有知识页支撑？

## 来源知识

{wikilinks}
"""


# ──────────────────────────────────────────────
# 候选页面列表
# ──────────────────────────────────────────────

def list_skill_candidates(wiki_root: Path) -> None:
    """列出可蒸馏的高质量页面（confidence: high/medium，已通过）。"""
    print("📚 可蒸馏的高质量知识页面：\n")

    search_dirs = [wiki_root / DIRS["概念"], wiki_root / DIRS["实体"]]
    candidates = []

    for d in search_dirs:
        if not d.exists():
            continue
        for md_file in d.glob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            confidence = meta.get("confidence", "").lower()
            status = meta.get("status", "approved").lower()
            if confidence in ("high", "medium") and status == "approved":
                line_count = len(body.splitlines())
                candidates.append((confidence, line_count, md_file, meta))

    # 按质量排序
    candidates.sort(key=lambda x: (0 if x[0] == "high" else 1, -x[1]))

    for confidence, lines, path, meta in candidates:
        rel = path.relative_to(wiki_root)
        icon = "🟢" if confidence == "high" else "🟡"
        title = meta.get("title", path.stem)
        print(f"  {icon} {rel}  （{confidence}，{lines} 行）- {title}")

    if not candidates:
        print("  ⚠️  未找到高质量知识页面。请先加工并通过一些文章。")


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="从知识页蒸馏 Skill 草稿")
    parser.add_argument("sources", nargs="*", help="来源知识页路径（相对于 wiki 根目录）")
    parser.add_argument("--wiki-root", help="wiki 根目录路径（默认自动检测）")
    parser.add_argument("--name", help="Skill 名称（默认从来源文件名推断）")
    parser.add_argument("--list-candidates", action="store_true", help="列出可蒸馏的高质量页面")
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root) if args.wiki_root else find_wiki_root()

    if args.list_candidates:
        list_skill_candidates(wiki_root)
        return

    if not args.sources:
        print("❌ 请指定至少一个来源知识页路径。")
        print(f"   用法: python3 scripts/distill_skill.py \"{DIRS['概念']}/etf.md\"")
        print("   或: python3 scripts/distill_skill.py --list-candidates")
        sys.exit(1)

    # 解析来源文件
    source_data = []
    for src_str in args.sources[:3]:  # 最多 3 个来源
        src_path = resolve_vault_path(wiki_root, src_str)
        if not src_path.exists():
            print(f"❌ 文件不存在: {src_path}")
            sys.exit(1)
        text = src_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)

        # 检查质量
        confidence = meta.get("confidence", "").lower()
        status = meta.get("status", "").lower()
        if confidence not in ("high", "medium"):
            print(f"⚠️  {src_path.name} 置信度为 {confidence!r}，建议使用 medium 以上的页面")
        if status not in ("approved", ""):
            print(f"⚠️  {src_path.name} 状态为 {status!r}，建议使用已审阅通过的页面")

        source_data.append((src_path, meta, body))
        print(f"✅ 读取来源: {src_path.name}")

    # 推断 Skill 名称
    if args.name:
        skill_name = args.name
    elif len(source_data) == 1:
        skill_name = source_data[0][1].get("title", source_data[0][0].stem)
    else:
        # 从多个来源文件名组合
        skill_name = "-".join(p.stem for p, _, _ in source_data[:2])

    # 生成文件名
    skill_filename = skill_name.lower().replace(" ", "-").replace("：", "-").replace(":", "-")
    skill_filename = "".join(c for c in skill_filename if c.isalnum() or c == "-")

    # 输出路径 — Resources/技能/待审/
    skill_review_dir = wiki_root / DIRS["技能待审"]
    skill_review_dir.mkdir(parents=True, exist_ok=True)
    output_path = skill_review_dir / f"{skill_filename}.md"

    if output_path.exists():
        print(f"⚠️  文件已存在: {output_path}")
        answer = input("覆盖? [y/N]: ").strip().lower()
        if answer != "y":
            print("已取消。")
            sys.exit(0)

    # 生成草稿
    draft = generate_skill_draft(source_data, wiki_root, skill_name)
    output_path.write_text(draft, encoding="utf-8")

    print(f"\n✅ Skill 草稿已生成: {DIRS['技能待审']}/{skill_filename}.md")
    print(f"\n📝 下一步：")
    print(f"   1. 在 Obsidian 中打开 {DIRS['技能待审']}/{skill_filename}.md")
    print(f"   2. 根据注释中的来源内容，填写判断规则、反模式和能力边界")
    print(f"   3. 检查可证伪性自检清单（文件底部）")
    print(f"   4. 删除注释块（<!-- ... -->)）")
    print(f"   5. 将 frontmatter 中的 status: review 改为 status: approved")
    print(f"   6. Skill 即正式生效，可在后续加工中引用")

    # 写日志
    sources_list = ", ".join(f"[[{p.stem}]]" for p, _, _ in source_data)
    append_log(wiki_root, f"蒸馏 Skill 草稿: [[{DIRS['技能待审']}/{skill_filename}]]（来源: {sources_list}）")


if __name__ == "__main__":
    main()

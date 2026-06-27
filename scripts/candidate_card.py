#!/usr/bin/env python3
"""
candidate_card.py — Knowledge Compiler 候选项目卡生成器

从 Resources 知识页生成候选项目卡，存入 Projects 候选。

用法：
  python3 scripts/candidate_card.py "1 - Resources（资源）/概念/智能代理记忆.md"
  python3 scripts/candidate_card.py --name "知识图谱可视化工具" "1 - Resources（资源）/概念/知识图谱.md"
  python3 scripts/candidate_card.py --idea "构建一个自动蒸馏 Skill 的工具"  # 纯想法，无需来源页
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_common import append_log_top
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


def update_index_candidates(wiki_root: Path, page_name: str, summary: str) -> None:
    """在 index.md 候选分类下添加条目。"""
    index_path = wiki_root / "index.md"
    if not index_path.exists():
        return
    entry_line = f"- [[{DIRS['候选']}/{page_name}]] — {summary}\n"
    content = index_path.read_text(encoding="utf-8")
    section_header = "## 候选"
    if section_header in content:
        insert_pos = content.index(section_header) + len(section_header)
        nl_pos = content.index("\n", insert_pos)
        content = content[: nl_pos + 1] + entry_line + content[nl_pos + 1 :]
    else:
        content += f"\n{section_header}\n{entry_line}"
    index_path.write_text(content, encoding="utf-8")


def infer_domain_tags(content: str) -> list[str]:
    """从内容推断领域标签。"""
    invest_keywords = ["etf", "投资", "基金", "估值", "指数", "资产", "配置", "收益", "风险"]
    ai_keywords = ["agent", "llm", "ai", "知识", "自动化", "模型", "prompt", "工具"]
    content_lower = content.lower()
    tags = ["candidate"]
    if any(k in content_lower for k in invest_keywords):
        tags.append("投资")
    if any(k in content_lower for k in ai_keywords):
        tags.append("AI与自动化")
    if len(tags) == 1:
        tags.append("知识管理")
    return tags


# ──────────────────────────────────────────────
# 生成候选卡模板
# ──────────────────────────────────────────────

def generate_candidate_card(
    project_name: str,
    sources: list[tuple[Path, dict, str]],
    wiki_root: Path,
    idea_text: str = "",
) -> str:
    """生成候选项目卡 Markdown，带 AI 填写提示注释。"""
    today = date.today().isoformat()

    source_refs = []
    wikilinks_lines = []
    skill_links_lines = []
    all_content = idea_text

    for src_path, meta, body in sources:
        rel = str(src_path.relative_to(wiki_root)).replace("\\", "/")
        source_refs.append(rel)
        wikilinks_lines.append(f"- [[{src_path.stem}]] - 支撑方式待填写")
        all_content += " " + body[:400]

    # 查找相关 Skill
    skills_dir = wiki_root / DIRS["技能"]
    if skills_dir.exists():
        for skill_file in list(skills_dir.glob("*.md"))[:3]:
            skill_meta, _ = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
            if skill_meta.get("status", "").lower() == "approved":
                skill_links_lines.append(f"- [[{DIRS['技能']}/{skill_file.stem}]]")

    tags = infer_domain_tags(all_content)
    sources_yaml = "[" + ", ".join(source_refs) + "]" if source_refs else "[]"

    knowledge_section = "\n".join(wikilinks_lines) if wikilinks_lines else "- （待填写：相关知识页）"
    skills_section = "\n".join(skill_links_lines) if skill_links_lines else "- （暂无相关 Skill）"

    # 生成来源摘要注释
    source_context = ""
    if sources:
        source_context = "<!-- 来源知识摘要（AI 参考）：\n"
        for src_path, meta, body in sources:
            source_context += f"\n{src_path.stem}:\n{body[:400].strip()}\n"
        source_context += "\n-->\n\n"
    elif idea_text:
        source_context = f"<!-- 用户原始想法：\n{idea_text}\n-->\n\n"

    return f"""---
title: 候选：{project_name}
created: {today}
updated: {today}
type: candidate
status: incubating
tags: [{', '.join(tags)}]
sources: {sources_yaml}
---

# 候选：{project_name}

{source_context}<!-- AI 填写说明：根据上方来源内容和用户想法，填写以下各节。
     聚焦「核心问题」和「需要验证的假设」，这是候选卡最有价值的部分。
     来源知识支撑要具体，说明每个知识页如何支撑这个项目。-->

一句话说明这个项目要解决什么问题，或创造什么价值。

## 核心问题

这个项目要回答或解决什么？（用一个清晰的问题句表达）

## 现有知识支撑

{knowledge_section}

## 需要验证的假设

1. 假设A：...（验证方式：...，验证成本：低/中/高）
2. 假设B：...（验证方式：...，验证成本：低/中/高）
3. 假设C：...（验证方式：...，验证成本：低/中/高）

## 初步研究议程

- 待研究问题1（优先级：高）
- 待研究问题2（优先级：中）
- 待研究问题3（优先级：低）

## 相关 Skill

{skills_section}

## 状态更新

- {today}：创建候选卡
"""


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="生成候选项目卡")
    parser.add_argument("sources", nargs="*", help="来源知识页路径（相对于 wiki 根目录）")
    parser.add_argument("--root", "--wiki-root", dest="wiki_root", help="wiki 根目录路径（默认自动检测）")
    parser.add_argument("--name", help="项目名称（默认从来源页推断）")
    parser.add_argument("--idea", help="直接提供想法文字，不需要来源页")
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root) if args.wiki_root else find_wiki_root()

    if not args.sources and not args.idea:
        print("❌ 请指定来源知识页路径，或用 --idea 提供想法文字。")
        print(f"   用法: python3 scripts/candidate_card.py \"{DIRS['概念']}/etf.md\"")
        print("   或: python3 scripts/candidate_card.py --idea '构建知识图谱工具'")
        sys.exit(1)

    # 解析来源文件
    source_data = []
    for src_str in (args.sources or [])[:3]:
        src_path = resolve_vault_path(wiki_root, src_str)
        if not src_path.exists():
            print(f"❌ 文件不存在: {src_path}")
            sys.exit(1)
        text = src_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        source_data.append((src_path, meta, body))
        print(f"✅ 读取来源: {src_path.name}")

    # 推断项目名称
    if args.name:
        project_name = args.name
    elif args.idea:
        # 从 idea 取前 15 个字符
        project_name = args.idea[:15].strip()
    elif len(source_data) == 1:
        project_name = source_data[0][1].get("title", source_data[0][0].stem)
    else:
        project_name = "-".join(p.stem for p, _, _ in source_data[:2])

    # 生成文件名
    filename = project_name.lower().replace(" ", "-").replace("：", "-").replace(":", "-")
    filename = "".join(c for c in filename if c.isalnum() or c == "-")
    if not filename:
        filename = "candidate-" + date.today().isoformat()

    # 输出路径
    candidates_dir = wiki_root / DIRS["候选"]
    candidates_dir.mkdir(parents=True, exist_ok=True)
    output_path = candidates_dir / f"{filename}.md"

    if output_path.exists():
        print(f"⚠️  文件已存在: {output_path}")
        answer = input("覆盖? [y/N]: ").strip().lower()
        if answer != "y":
            print("已取消。")
            sys.exit(0)

    # 生成候选卡
    card = generate_candidate_card(
        project_name=project_name,
        sources=source_data,
        wiki_root=wiki_root,
        idea_text=args.idea or "",
    )
    output_path.write_text(card, encoding="utf-8")

    # 更新 index.md
    update_index_candidates(wiki_root, filename, project_name)

    print(f"\n✅ 候选卡已生成: {DIRS['候选']}/{filename}.md")
    print(f"\n📝 下一步：")
    print(f"   1. Minis AI 会根据注释中的来源内容填写各节内容")
    print(f"   2. 或在 Obsidian 中手动编辑候选卡")
    print(f"   3. 当项目启动时，将 status: incubating 改为 status: active")

    # 写日志
    sources_str = ", ".join(f"[[{p.stem}]]" for p, _, _ in source_data)
    log_entry = f"生成候选卡: [[{DIRS['候选']}/{filename}]]（项目: {project_name}"
    if sources_str:
        log_entry += f"，来源: {sources_str}"
    log_entry += "）"
    append_log_top(wiki_root, "生成候选卡", [f"- {log_entry}"])


if __name__ == "__main__":
    main()

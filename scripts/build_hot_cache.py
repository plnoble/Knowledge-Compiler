#!/usr/bin/env python3
"""
build_hot_cache.py — Knowledge Compiler 热缓存生成器

生成 _meta/hot.md：
  - ~500 字的「近期上下文」快照，每次会话从这里读起
  - 最常被引用 TOP 10（Loop 1：引用计数）
  - 最新加工记录（从 log.md 提取）
  - 活跃研究方向（从 _meta/research-agenda.md 提取）
  - 待审积压提醒

格式对齐 claude-obsidian WIKI.md hot.md 规范。

用法：
  python3 scripts/build_hot_cache.py [--root /path]
"""

import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import (
    get_wiki_root, ALL_PAGE_DIRS, RAW, META_FILES, CHECK_DIRS
)


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


def count_inbound_references(root: Path, page_dirs: list[str]) -> Counter:
    """
    Loop 1：统计每个页面的入站引用次数。
    扫描所有知识页中的 [[wikilink]]，统计每个目标被引用多少次。
    """
    inbound = Counter()
    all_md = []
    for d in page_dirs:
        dp = root / d
        if dp.is_dir():
            all_md.extend(dp.glob("*.md"))

    for md_file in all_md:
        try:
            content = md_file.read_text(encoding="utf-8")
            # 去掉 frontmatter 再扫描
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2]
            for link in re.findall(r'\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]', content):
                target = link.strip()
                if target:
                    inbound[target] += 1
        except Exception:
            pass

    return inbound


def get_top_referenced(root: Path, page_dirs: list[str], limit: int = 10) -> list[tuple[str, int, Path]]:
    """返回引用次数最多的页面列表 [(页面名, 引用数, 路径)]。"""
    inbound = count_inbound_references(root, page_dirs)
    if not inbound:
        return []

    # 建立页面名 → 路径映射
    page_index = {}
    for d in page_dirs:
        dp = root / d
        if dp.is_dir():
            for f in dp.glob("*.md"):
                page_index[f.stem] = f

    results = []
    for name, count in inbound.most_common(limit * 2):
        if name in page_index:
            results.append((name, count, page_index[name]))
        if len(results) >= limit:
            break

    return results


def get_recent_log_entries(root: Path, limit: int = 5) -> list[str]:
    """从 log.md 提取最近 N 条记录（## [日期] 格式）。"""
    log_path = root / "log.md"
    if not log_path.exists():
        return []

    content = log_path.read_text(encoding="utf-8")
    entries = re.findall(r'^## \[(\d{4}-\d{2}-\d{2})\].*$', content, re.MULTILINE)
    # 从头部读（log.md 新记录在最前）
    seen = []
    for line in content.splitlines():
        if re.match(r'^## \[\d{4}-\d{2}-\d{2}\]', line):
            seen.append(line.lstrip("# ").strip())
        if len(seen) >= limit:
            break
    return seen


def get_active_research(root: Path) -> list[str]:
    """从 _meta/research-agenda.md 提取 pending 状态的研究议题。"""
    agenda_path = root / META_FILES["agenda"]
    if not agenda_path.exists():
        return []

    content = agenda_path.read_text(encoding="utf-8")
    pending = []
    for line in content.splitlines():
        # 匹配 - [ ] 或 - pending: 开头的行
        if re.match(r'^-\s*\[\s*\]\s+', line) or "status: pending" in line.lower():
            clean = re.sub(r'^-\s*\[\s*\]\s+', '', line).strip()
            if clean:
                pending.append(clean)
        if len(pending) >= 3:
            break
    return pending


def get_review_queue_count(root: Path) -> int:
    """统计 Inbox 待审文件数。"""
    review_dir = root / RAW["待审"]
    if not review_dir.exists():
        return 0
    return len(list(review_dir.glob("*.md")))


def get_inbox_count(root: Path) -> int:
    """统计 Inbox 待处理文件数。"""
    inbox_dir = root / RAW["收件箱"]
    if not inbox_dir.exists():
        return 0
    return len(list(inbox_dir.glob("*.md")))


def get_total_pages(root: Path) -> dict[str, int]:
    """统计各目录页面数。"""
    counts = {}
    for d in ALL_PAGE_DIRS:
        dp = root / d
        counts[d] = len(list(dp.glob("*.md"))) if dp.is_dir() else 0
    return counts


def build_hot_cache(root: Path) -> str:
    """生成 hot.md 内容。"""
    today = date.today().isoformat()

    # 收集数据
    top_pages = get_top_referenced(root, ALL_PAGE_DIRS, limit=10)
    recent_logs = get_recent_log_entries(root, limit=5)
    active_research = get_active_research(root)
    review_count = get_review_queue_count(root)
    inbox_count = get_inbox_count(root)
    page_counts = get_total_pages(root)
    total_pages = sum(page_counts.values())

    # ── 构建 hot.md ──
    lines = [
        "---",
        "type: meta",
        "title: 热缓存",
        f"updated: {today}",
        "---",
        "",
        "# 近期上下文",
        "",
        f"## 最后更新",
        f"{today}",
        "",
    ]

    # 知识库规模
    lines += [
        "## 知识库规模",
        f"总页面：**{total_pages}** 页",
        "",
    ]
    for d, cnt in page_counts.items():
        if cnt > 0:
            lines.append(f"- {d}/：{cnt} 页")
    lines.append("")

    # 最近操作记录
    lines += ["## 近期操作"]
    if recent_logs:
        for entry in recent_logs:
            lines.append(f"- {entry}")
    else:
        lines.append("- （暂无记录）")
    lines.append("")

    # 最常被引用 TOP 页面（Loop 1）
    lines += ["## 🔥 最常被引用（核心知识）"]
    if top_pages:
        for name, count, path in top_pages:
            rel = path.relative_to(root)
            dir_name = rel.parent.name
            lines.append(f"- [[{name}]]（{dir_name}/，被引用 {count} 次）")
    else:
        lines.append("- （知识页较少，暂无引用统计）")
    lines.append("")

    # 活跃研究方向（Loop 3）
    lines += ["## 🔬 活跃研究方向"]
    if active_research:
        for topic in active_research:
            lines.append(f"- {topic}")
    else:
        lines.append("- （无进行中的研究议题）")
    lines.append("")

    # 待处理提醒
    lines += ["## ⚡ 待处理提醒"]
    reminders = []
    if inbox_count > 0:
        reminders.append(f"📥 {RAW['收件箱']}/ 有 **{inbox_count}** 篇待加工")
    if review_count > 0:
        reminders.append(f"⏳ {RAW['待审']}/ 有 **{review_count}** 篇待审阅")
    if not reminders:
        reminders.append("✅ 无积压，状态良好")
    for r in reminders:
        lines.append(f"- {r}")
    lines.append("")

    # 阅读指引（给 Minis 的说明）
    lines += [
        "## 📖 如何使用",
        f"- 加工新文章：告诉 AI「加工 {RAW['收件箱']}/文件名.md」",
        "- 提问：告诉 Minis「[你的问题]」，Minis 先读此缓存再检索知识页",
        "- 审阅：在 Obsidian 改 frontmatter status: approved，再运行 wiki.sh review",
        "",
    ]

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成热缓存 _meta/hot.md")
    parser.add_argument("--root", "--wiki-root", dest="wiki_root", help="wiki 根目录路径")
    parser.add_argument("--print", action="store_true", help="打印到终端而不写文件")
    args = parser.parse_args()

    root = get_wiki_root(override=args.wiki_root)
    content = build_hot_cache(root)

    if args.print:
        print(content)
        return

    # 写入 _meta/hot.md
    meta_dir = root / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    hot_path = meta_dir / "hot.md"
    hot_path.write_text(content, encoding="utf-8")

    total_lines = content.count("\n") + 1
    print(f"✅ 热缓存已更新: _meta/hot.md（{total_lines} 行）")
    print(f"   知识总量：{sum(v for v in get_total_pages(root).values())} 页")

    inbox = get_inbox_count(root)
    review = get_review_queue_count(root)
    if inbox > 0:
        print(f"   📥 待加工：{inbox} 篇")
    if review > 0:
        print(f"   ⏳ 待审阅：{review} 篇")


if __name__ == "__main__":
    main()

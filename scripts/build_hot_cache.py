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


def get_unresolved_conflicts(root: Path, limit: int = 5) -> list[str]:
    """Collect pages that appear to contain unresolved conflict markers."""
    conflicts: list[str] = []
    scan_dirs = list(dict.fromkeys([*ALL_PAGE_DIRS, RAW["\u5f85\u5ba1"]]))
    for d in scan_dirs:
        dp = root / d
        if not dp.is_dir():
            continue
        for md_file in sorted(dp.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lowered = content.lower()
            if "[!\u77db\u76fe]" in content or "[!contradiction]" in lowered:
                rel = str(md_file.relative_to(root)).replace("\\", "/")
                conflicts.append(rel)
            if len(conflicts) >= limit:
                return conflicts
    return conflicts


def get_recent_connections(root: Path, limit: int = 5) -> list[str]:
    """Extract recent relationship/link hints from log.md."""
    log_path = root / "log.md"
    if not log_path.exists():
        return []
    content = log_path.read_text(encoding="utf-8", errors="replace")
    connections: list[str] = []
    relation_markers = ["\u94fe\u63a5", "\u5173\u7cfb", "\u5173\u8054", "->", "\u2194", "related"]
    for line in content.splitlines():
        clean = line.strip(" -")
        if not clean:
            continue
        has_link = "[[" in clean and "]]" in clean
        has_relation_word = any(marker in clean for marker in relation_markers)
        if has_link and has_relation_word:
            connections.append(clean)
        if len(connections) >= limit:
            break
    return connections


def build_bias_and_gap_notes(inbox_count: int, review_count: int, total_pages: int, top_pages: list[tuple[str, int, Path]], active_research: list[str]) -> list[str]:
    notes: list[str] = []
    if inbox_count > 30:
        notes.append(f"\u5f85\u5904\u7406\u5df2\u6709 {inbox_count} \u7bc7\uff0c\u8f93\u5165\u901f\u5ea6\u53ef\u80fd\u8d85\u8fc7\u7f16\u8bd1\u901f\u5ea6\uff1b\u5efa\u8bae\u964d\u4f4e\u526a\u85cf\u6807\u51c6\u6216\u5206\u6279\u5904\u7406\u3002")
    if review_count > 20:
        notes.append(f"\u5f85\u5ba1\u5df2\u6709 {review_count} \u7bc7\uff0c\u6b63\u5f0f\u5e93\u66f4\u65b0\u53ef\u80fd\u88ab\u5ba1\u9605\u961f\u5217\u5361\u4f4f\u3002")
    if total_pages > 20 and not top_pages:
        notes.append("\u9875\u9762\u6570\u91cf\u5df2\u7ecf\u589e\u957f\uff0c\u4f46\u7f3a\u5c11\u9ad8\u8fde\u63a5\u8282\u70b9\uff1b\u9700\u8981\u52a0\u5f3a Relationship Discovery \u548c wikilink \u5efa\u8bae\u3002")
    if active_research:
        notes.append("\u7814\u7a76\u8bae\u7a0b\u4e2d\u4ecd\u6709\u672a\u5173\u95ed\u95ee\u9898\uff1b\u4f18\u5148\u5904\u7406\u4f1a\u5f71\u54cd\u6b63\u5f0f\u7ed3\u8bba\u7684\u95ee\u9898\u3002")
    if not notes:
        notes.append("\u6682\u65e0\u660e\u663e\u8f93\u5165\u504f\u79d1\uff1b\u7ee7\u7eed\u89c2\u5bdf\u9ad8\u9891\u4e3b\u9898\u3001\u4f4e\u8fde\u63a5\u9875\u9762\u548c\u672a\u89e3\u51b3\u51b2\u7a81\u3002")
    return notes


def build_hot_cache(root: Path) -> str:
    """Generate hot.md as a Knowledge Compiler status dashboard."""
    current_day = date.today().isoformat()

    top_pages = get_top_referenced(root, ALL_PAGE_DIRS, limit=10)
    recent_logs = get_recent_log_entries(root, limit=5)
    active_research = get_active_research(root)
    review_count = get_review_queue_count(root)
    inbox_count = get_inbox_count(root)
    page_counts = get_total_pages(root)
    total_pages = sum(page_counts.values())
    conflicts = get_unresolved_conflicts(root)
    recent_connections = get_recent_connections(root)
    bias_notes = build_bias_and_gap_notes(inbox_count, review_count, total_pages, top_pages, active_research)

    resource_counts = [(d, cnt) for d, cnt in page_counts.items() if d.startswith("1 - Resources") and cnt > 0]
    area_counts = [(d, cnt) for d, cnt in page_counts.items() if d.startswith("2 - Areas") and cnt > 0]

    lines = [
        "---",
        "type: meta",
        "title: Knowledge Compiler \u72b6\u6001\u4eea\u8868\u76d8",
        f"updated: {current_day}",
        "managed_by: compile-knowledge",
        "---",
        "",
        "# Knowledge Compiler \u72b6\u6001\u4eea\u8868\u76d8",
        "",
        "## \u6700\u540e\u66f4\u65b0",
        f"{current_day}",
        "",
        "## \u77e5\u8bc6\u5e93\u89c4\u6a21",
        f"\u603b\u9875\u9762\uff1a**{total_pages}** \u9875",
        f"\u5f85\u5904\u7406\uff1a**{inbox_count}** \u7bc7",
        f"\u5f85\u5ba1\uff1a**{review_count}** \u7bc7",
        "",
    ]

    lines += ["## \u6700\u8fd1\u5904\u7406\u8bb0\u5f55"]
    if recent_logs:
        for entry in recent_logs:
            lines.append(f"- {entry}")
    else:
        lines.append("- \uff08\u6682\u65e0\u8bb0\u5f55\uff09")
    lines.append("")

    inbox_dir_name = RAW["\u6536\u4ef6\u7bb1"]
    review_dir_name = RAW["\u5f85\u5ba1"]

    lines += ["## \u5f85\u5904\u7406\u4e0e\u5f85\u5ba1\u79ef\u538b"]
    if inbox_count or review_count:
        if inbox_count:
            lines.append(f"- `{inbox_dir_name}/`\uff1a{inbox_count} \u7bc7\u5f85\u7f16\u8bd1")
        if review_count:
            lines.append(f"- `{review_dir_name}/`\uff1a{review_count} \u7bc7\u5f85\u5ba1\u9605")
    else:
        lines.append("- \u5f53\u524d\u6ca1\u6709\u660e\u663e\u79ef\u538b\u3002")
    lines.append("")

    lines += ["## \u6d3b\u8dc3 Resources / Areas"]
    if top_pages:
        lines.append("### \u9ad8\u8fde\u63a5 Resources")
        for name, count, path in top_pages:
            rel = path.relative_to(root)
            lines.append(f"- [[{name}]]\uff08{rel.parent}/\uff0c\u88ab\u5f15\u7528 {count} \u6b21\uff09")
    else:
        lines.append("- \u6682\u65e0\u9ad8\u8fde\u63a5\u9875\u9762\uff1b\u65b0\u5e93\u9700\u8981\u7ee7\u7eed\u79ef\u7d2f\u5173\u7cfb\u3002")
    if resource_counts or area_counts:
        lines.append("")
        lines.append("### \u9875\u9762\u5206\u5e03")
        for d, cnt in [*resource_counts, *area_counts]:
            lines.append(f"- {d}/\uff1a{cnt} \u9875")
    lines.append("")

    lines += ["## \u672a\u89e3\u51b3\u51b2\u7a81"]
    if conflicts:
        for rel in conflicts:
            lines.append(f"- `{rel}`")
    else:
        lines.append("- \u6682\u65e0\u663e\u5f0f `[!\u77db\u76fe]` \u6216 `[!contradiction]` \u6807\u8bb0\u3002")
    lines.append("")

    lines += ["## \u8fd1\u671f\u91cd\u8981\u65b0\u8fde\u63a5"]
    if recent_connections:
        for entry in recent_connections:
            lines.append(f"- {entry}")
    else:
        lines.append("- \u6682\u65e0\u53ef\u4ece\u65e5\u5fd7\u8bc6\u522b\u7684\u65b0\u8fde\u63a5\uff1b\u6444\u5165\u65f6\u8bf7\u8865\u5145 Relationship Discovery\u3002")
    lines.append("")

    lines += ["## \u53ef\u80fd\u7684\u8f93\u5165\u504f\u79d1\u4e0e\u77e5\u8bc6\u7a7a\u767d"]
    for note in bias_notes:
        lines.append(f"- {note}")
    lines.append("")

    lines += ["## \u5982\u4f55\u4f7f\u7528\u8fd9\u4e2a\u4eea\u8868\u76d8"]
    lines.append("- \u8bfb\uff0c\u4e0d\u8981\u624b\u5199\uff1b\u5b83\u662f AI \u7ef4\u62a4\u7684\u8de8\u4f1a\u8bdd\u72b6\u6001\u3002")
    lines.append("- \u6bcf\u6b21\u5f00\u59cb\u52a0\u5de5\u524d\u5148\u770b\u6700\u8fd1\u5904\u7406\u8bb0\u5f55\u3001\u672a\u89e3\u51b3\u51b2\u7a81\u548c\u8f93\u5165\u504f\u79d1\u3002")
    lines.append("- \u51b2\u7a81\u548c\u5f85\u5ba1\u79ef\u538b\u4f18\u5148\u7ea7\u9ad8\u4e8e\u7ee7\u7eed\u526a\u85cf\u65b0\u8d44\u6599\u3002")
    lines.append("")

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

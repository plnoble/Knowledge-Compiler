#!/usr/bin/env python3
"""Wiki 知识库健康检查脚本。

用法: python3 health_check.py [--root /path/to/wiki]
输出 Markdown 报告到 stdout，可重定向到文件。
"""
import os, re, sys
from datetime import datetime

WIKI_ROOT = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
PAGE_DIRS = ["entities", "concepts", "comparisons", "queries", "synthesis"]
RAW_DIRS  = ["articles", "processed", "papers", "transcripts", "assets"]
REQUIRED_FIELDS = ["title", "created", "updated", "type", "tags"]
MAX_LINES = 200
MIN_OUTLINKS = 2


def find_pages(root):
    """构建 {page_name: filepath} 索引。包含页面目录 + raw/ 子目录。"""
    pages = {}
    scan_dirs = PAGE_DIRS + [os.path.join("raw", d) for d in RAW_DIRS]
    for d in scan_dirs:
        dp = os.path.join(root, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if f.endswith(".md"):
                # 页面目录优先，不覆盖已有条目
                name = f[:-3]
                if name not in pages:
                    pages[name] = os.path.join(dp, f)
    return pages


def strip_frontmatter(content):
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:]
    return content


def extract_wikilinks(content):
    """提取 [[wikilink]] 目标，处理 [[page|alias]] 和 [[page#heading]]。"""
    body = strip_frontmatter(content)
    raw = re.findall(r'\[\[([^\]]+)\]\]', body)
    result = []
    for link in raw:
        target = link.split("|")[0].split("#")[0].strip()
        if target:
            result.append(target)
    return result


def check_frontmatter(content):
    issues = []
    if not content.startswith("---"):
        return ["missing frontmatter"]
    end = content.find("\n---", 3)
    if end == -1:
        return ["unclosed frontmatter"]
    fm = content[3:end]
    for field in REQUIRED_FIELDS:
        if not re.search(rf'^{field}\s*:', fm, re.MULTILINE):
            issues.append(f"missing: {field}")
    return issues


def main():
    root = WIKI_ROOT
    if "--root" in sys.argv:
        idx = sys.argv.index("--root")
        if idx + 1 < len(sys.argv):
            root = sys.argv[idx + 1]

    if not os.path.isdir(root):
        print(f"Error: wiki root not found: {root}", file=sys.stderr)
        sys.exit(1)

    pages = find_pages(root)
    total_pages = len(pages)

    # ---- 统计 ----
    dir_stats = {}
    raw_stats = {}
    for d in PAGE_DIRS:
        dp = os.path.join(root, d)
        dir_stats[d] = len([f for f in os.listdir(dp) if f.endswith(".md")]) if os.path.isdir(dp) else 0
    for d in RAW_DIRS:
        dp = os.path.join(root, "raw", d)
        raw_stats[d] = len(os.listdir(dp)) if os.path.isdir(dp) else 0

    # ---- 扫描：页面目录（检查格式/大小/链接） ----
    broken_links = {}
    format_issues = {}
    oversized = {}
    low_outlink = {}
    total_links = 0

    # 构建页面目录索引（用于格式/大小/出站检查）
    # 排除 sources/（源摘要模板天然无入站链接，不应计入孤儿/出站评分）
    CHECK_DIRS = [d for d in PAGE_DIRS if d != "sources"]
    page_index = {}
    for d in CHECK_DIRS:
        dp = os.path.join(root, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if f.endswith(".md"):
                page_index[f[:-3]] = os.path.join(dp, f)

    for name, filepath in page_index.items():
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        links = extract_wikilinks(content)
        total_links += len(links)

        broken = sorted(set(l for l in links if l not in pages))
        if broken:
            broken_links[filepath] = broken

        issues = check_frontmatter(content)
        if issues:
            format_issues[filepath] = issues

        line_count = content.count("\n") + 1
        if line_count > MAX_LINES:
            oversized[filepath] = line_count

        if len(links) < MIN_OUTLINKS:
            low_outlink[filepath] = len(links)

    total_pages = len(page_index)  # 只统计页面目录

    # ---- 孤儿页检测（没有任何页面链接到的页面） ----
    linked_pages = set()
    for name, filepath in page_index.items():
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        for link in extract_wikilinks(content):
            linked_pages.add(link)
    orphan_pages = sorted(set(page_index.keys()) - linked_pages)

    # ---- 评分 ----
    total_broken   = sum(len(v) for v in broken_links.values())
    total_format   = len(format_issues)
    total_oversize = len(oversized)
    total_low_out  = len(low_outlink)

    score = 100.0
    if total_links > 0:
        score -= min(30, (total_broken / total_links) * 100)
    if total_pages > 0:
        score -= min(20, (total_format   / total_pages) * 100)
        score -= min(10, (total_oversize / total_pages) * 100)
        score -= min(10, (total_low_out  / total_pages) * 100)
        score -= min(10, (len(orphan_pages) / total_pages) * 100)
    score = max(0, round(score))

    # ---- 输出 ----
    print("# 知识库健康检查报告")
    print()
    print(f"## 检查时间")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print(f"## 目录统计")
    for d in PAGE_DIRS:
        print(f"- {d}/: {dir_stats[d]} 页")
    for d in RAW_DIRS:
        print(f"- raw/{d}/: {raw_stats[d]} 条")
    print(f"- **总页面数: {total_pages}**")
    print()
    print(f"## 链接状态")
    print(f"- 总链接数: {total_links}")
    print(f"- 断链数: {total_broken}")
    if broken_links:
        print(f"- 断链详情 (前 30):")
        shown = 0
        for fp, links in sorted(broken_links.items()):
            rel = os.path.relpath(fp, root)
            for link in links:
                if shown >= 30:
                    print(f"  - ... 还有 {total_broken - shown} 个断链")
                    break
                print(f"  - `{rel}` → [[{link}]]")
                shown += 1
            if shown >= 30:
                break
    print()
    print(f"## 格式检查")
    correct = total_pages - total_format
    print(f"- 格式正确: {correct}/{total_pages} ({correct*100//max(1,total_pages)}%)")
    if format_issues:
        print(f"- 问题页面 (前 20):")
        for fp, issues in list(format_issues.items())[:20]:
            rel = os.path.relpath(fp, root)
            print(f"  - `{rel}`: {', '.join(issues)}")
    print()
    print(f"## 页面大小 (> {MAX_LINES} 行)")
    print(f"- 超标: {total_oversize}")
    if oversized:
        for fp, lines in sorted(oversized.items(), key=lambda x: -x[1])[:10]:
            rel = os.path.relpath(fp, root)
            print(f"  - `{rel}`: {lines} 行")
    print()
    print(f"## 出站链接 (< {MIN_OUTLINKS} 个)")
    print(f"- 不足: {total_low_out}")
    print()
    print(f"## 孤儿页（无入站链接）")
    print(f"- 孤儿页数: {len(orphan_pages)}")
    if orphan_pages:
        # 只显示 wip 和非 wip 的统计
        wip_orphans = [p for p in orphan_pages if True]  # 简化，全部显示
        print(f"- 孤儿页列表 (前 20):")
        for p in orphan_pages[:20]:
            rel = os.path.relpath(page_index[p], root)
            print(f"  - `{rel}`")
    print()
    print(f"## 置信度 + 零幻觉")
    # 统计置信度和来源
    conf_counts = {"high": 0, "medium": 0, "low": 0, "quarantine": 0}
    sourced = 0
    for name, filepath in page_index.items():
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # 来源检查
        if re.search(r'sources:\s*\[(?!\])', content):
            sourced += 1
        # 置信度检查
        fm_match = re.search(r'confidence:\s*(\S+)', content)
        if fm_match:
            level = fm_match.group(1)
            if level in conf_counts:
                conf_counts[level] += 1
    
    sourced_pct = sourced * 100 // max(1, total_pages)
    print(f"- 来源覆盖: {sourced}/{total_pages} ({sourced_pct}%)")
    print(f"- 🟢 high: {conf_counts['high']} | 🟡 medium: {conf_counts['medium']}")
    print(f"- 🟠 low: {conf_counts['low']} | 🔴 quarantine: {conf_counts['quarantine']}")
    print()
    print(f"## 总体评估")
    print(f"**健康度: {score}%**")


if __name__ == "__main__":
    main()

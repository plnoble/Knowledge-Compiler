#!/usr/bin/env python3
"""会话记忆生成器：创建 _meta/hot-cache.md，为下次会话提供上下文。

用法: python3 build_hot_cache.py [--root /path/to/wiki]
"""
import os, re, sys
from datetime import datetime, timedelta
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

DIRS = ["entities", "concepts", "comparisons", "queries", "synthesis"]
now = datetime.now()
today = now.strftime("%Y-%m-%d")


def strip_fm(c):
    if c.startswith("---"):
        e = c.find("\n---", 3)
        if e != -1:
            return c[e+4:]
    return c


def extract_links(body):
    raw = re.findall(r'\[\[([^\]]+)\]\]', body)
    return [l.split("|")[0].split("#")[0].strip()
            for l in raw if l.split("|")[0].split("#")[0].strip()]


def main():
    print("生成会话记忆...")

    # 1. 读取 log.md 最后 10 条
    log_path = os.path.join(WIKI, "log.md")
    log_entries = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # 按 ## [ 分割，取最后 10 条
        entries = re.split(r'(?=^## \[)', content, flags=re.MULTILINE)
        log_entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## [")]
        log_entries = log_entries[-10:]

    # 2. 最近修改的页面（24 小时内）
    recent_pages = []
    for d in DIRS:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith(".md"):
                continue
            fp = os.path.join(dp, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(fp))
            if mtime > now - timedelta(hours=24):
                recent_pages.append((mtime, d, f[:-3]))
    recent_pages.sort(reverse=True)

    # 3. 知识空白：wip 占位页
    wip_pages = []
    empty_pages = []
    for d in ["entities", "concepts", "comparisons"]:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith(".md"):
                continue
            fp = os.path.join(dp, f)
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            if "tags: [wip]" in content or "tags: [wip," in content:
                wip_pages.append(f"{d}/{f[:-3]}")
            body = strip_fm(content)
            text_lines = [l.strip() for l in body.split("\n")
                         if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("---")]
            if len(text_lines) < 3:
                empty_pages.append(f"{d}/{f[:-3]}")

    # 4. 生成 hot-cache.md
    out = []
    out.append("# Hot Cache — 会话记忆")
    out.append(f"\n> 自动生成于 {now.strftime('%Y-%m-%d %H:%M')}。下次会话开始时先读此文件。")
    out.append("")

    # 最近操作
    out.append("## 最近操作")
    if log_entries:
        for entry in log_entries[-5:]:
            # 只取标题行
            lines = entry.split("\n")
            out.append(lines[0])
    else:
        out.append("- 无记录")
    out.append("")

    # 最近修改
    out.append("## 最近 24 小时修改的页面")
    if recent_pages:
        for mtime, d, name in recent_pages[:20]:
            out.append(f"- `{d}/{name}` ({mtime.strftime('%H:%M')})")
    else:
        out.append("- 无修改")
    out.append("")

    # 知识空白
    out.append("## 知识空白")
    out.append(f"- wip 占位页: {len(wip_pages)} 个")
    out.append(f"- 内容稀少页面: {len(empty_pages)} 个")
    if wip_pages:
        out.append("\n### 待填充的 wip 页面（前 20）")
        for p in wip_pages[:20]:
            out.append(f"- `{p}`")
    out.append("")

    # 快速统计
    page_counts = {}
    total_links = 0
    for d in DIRS:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        count = len([f for f in os.listdir(dp) if f.endswith(".md")])
        page_counts[d] = count
    
    out.append("## 快速统计")
    for d, c in page_counts.items():
        out.append(f"- {d}/: {c}")
    out.append(f"- **总计: {sum(page_counts.values())} 页**")
    out.append("")

    # 写入
    cache_path = os.path.join(WIKI, "_meta", "hot-cache.md")
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    
    print(f"  最近操作: {len(log_entries)} 条")
    print(f"  最近修改: {len(recent_pages)} 个页面")
    print(f"  wip 占位: {len(wip_pages)} 个")
    print(f"  内容稀少: {len(empty_pages)} 个")
    print(f"\n已保存: _meta/hot-cache.md")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""维护脚本：补充高频页面的 sources 字段。

用法: python3 maintain.py [--limit N]
"""
import os, re, sys
from datetime import datetime
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

RAW_DIR = os.path.join(WIKI, "raw", "articles")
PROCESSED_DIR = os.path.join(WIKI, "raw", "processed")
PAGE_DIRS = ["entities", "concepts", "comparisons", "queries"]
LIMIT = 500
if "--limit" in sys.argv:
    idx = sys.argv.index("--limit")
    if idx + 1 < len(sys.argv):
        LIMIT = int(sys.argv[idx + 1])
today = datetime.now().strftime("%Y-%m-%d")


def main():
    print("=" * 50)
    print("Wiki-KB 维护：补充 sources 字段")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 1. 加载所有页面
    pages = {}
    for d in PAGE_DIRS:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith(".md"):
                continue
            name = f[:-3]
            path = os.path.join(dp, f)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            fm = {}
            if content.startswith("---"):
                end = content.find("\n---", 3)
                if end != -1:
                    for line in content[3:end].split("\n"):
                        if ":" in line:
                            k, _, v = line.partition(":")
                            fm[k.strip()] = v.strip()
            body = content[end+4:] if end != -1 else content
            links = re.findall(r'\[\[([^\]]+)\]\]', body)
            links = [l.split("|")[0].split("#")[0].strip() for l in links if l.split("|")[0].split("#")[0].strip()]
            pages[name] = {"path": path, "type": d, "fm": fm, "content": content, "links": links}

    # 2. 计算入站链接
    inbound = defaultdict(int)
    inbound_sources = defaultdict(set)
    for name, data in pages.items():
        for link in data["links"]:
            if link in pages:
                inbound[link] += 1
                inbound_sources[link].add(name)

    # 3. 加载 raw 文件名集合（articles + processed）
    raw_files = set()
    for rd in [RAW_DIR, PROCESSED_DIR]:
        if os.path.isdir(rd):
            raw_files.update(f[:-3] for f in os.listdir(rd) if f.endswith(".md"))

    # 4. 找出高频被引用但缺少 sources 的页面
    todo = []
    for name, data in pages.items():
        current_sources = data["fm"].get("sources", "")
        has_sources = current_sources and current_sources not in ("[]", "")
        if inbound[name] >= 2 and not has_sources:
            matched = []
            if name in raw_files:
                matched.append(f"raw/articles/{name}.md")
            # 也检查 processed
            if os.path.exists(os.path.join(PROCESSED_DIR, f"{name}.md")):
                matched.append(f"raw/processed/{name}.md")
            title = data["fm"].get("title", "")
            for rf in raw_files:
                if title and title in rf:
                    matched.append(f"raw/articles/{rf}.md")
            for link_page in inbound_sources[name]:
                if link_page in raw_files:
                    matched.append(f"raw/articles/{link_page}.md")
            todo.append({
                "name": name, "path": data["path"], "content": data["content"],
                "fm": data["fm"], "inbound": inbound[name],
                "matched": list(set(matched))[:3],
            })

    todo.sort(key=lambda x: -x["inbound"])
    if LIMIT:
        todo = todo[:LIMIT]

    print(f"  待补充: {len(todo)} 个高频页面\n")

    count = 0
    for i, item in enumerate(todo, 1):
        content = item["content"]
        if item["matched"]:
            sources_str = ", ".join(item["matched"])
        else:
            sources_str = ""

        if "sources:" in content:
            if sources_str:
                content = re.sub(r'sources:\s*\[?\]?', f'sources: [{sources_str}]', content)
        else:
            if sources_str:
                content = re.sub(r'(confidence:\s*\S+)', f'sources: [{sources_str}]\n\\1', content)
            else:
                content = re.sub(r'(confidence:\s*\S+)', f'sources: []  # TODO: 需补充来源\n\\1', content)

        with open(item["path"], "w", encoding="utf-8") as f:
            f.write(content)
        count += 1

        if i % 100 == 0:
            matched_str = "有匹配" if item["matched"] else "无匹配"
            print(f"  进度: {i}/{len(todo)} ({matched_str})")

    matched_count = sum(1 for t in todo if t["matched"])
    print(f"\n  ✅ 补充完成: {count} 个页面（其中 {matched_count} 个找到匹配来源）")


if __name__ == "__main__":
    main()

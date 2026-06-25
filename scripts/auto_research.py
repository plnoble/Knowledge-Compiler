#!/usr/bin/env python3
"""自主研究助手：识别知识空白，生成研究议程，建议搜索查询。

用法: python3 auto_research.py [--root /path/to/wiki]
输出: _meta/research-agenda.md
"""
import os, re, sys
from datetime import datetime
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

DIRS = ["entities", "concepts", "comparisons", "queries", "synthesis"]
PAGE_DIRS = ["entities", "concepts", "comparisons", "queries"]
today = datetime.now().strftime("%Y-%m-%d")


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
    print("=== 自主研究助手 ===\n")

    # 1. 加载所有页面
    pages = {}  # name -> {path, type, content, links, is_wip, line_count}
    for d in DIRS:
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
            body = strip_fm(content)
            links = extract_links(body)
            is_wip = "tags: [wip]" in content or "tags: [wip," in content
            text_lines = [l.strip() for l in body.split("\n")
                         if l.strip() and not l.strip().startswith("#")
                         and not l.strip().startswith("---")
                         and not l.strip().startswith("> [!")]
            line_count = len(text_lines)
            pages[name] = {
                "path": path, "type": d.rstrip("s"), "content": content,
                "links": links, "is_wip": is_wip, "line_count": line_count,
                "dir": d
            }

    # 2. 计算入站链接
    inbound = defaultdict(int)
    for name, data in pages.items():
        for link in data["links"]:
            if link in pages:
                inbound[link] += 1

    # 3. 识别知识空白
    # 3a. wip 页面（按入站链接排序 = 重要性）
    wip_pages = []
    for name, data in pages.items():
        if data["is_wip"] and data["dir"] in PAGE_DIRS:
            wip_pages.append({
                "name": name, "type": data["type"],
                "inbound": inbound.get(name, 0),
                "outbound": len(data["links"]),
            })
    wip_pages.sort(key=lambda x: -x["inbound"])

    # 3b. 内容稀少页面（<5 行正文，非 wip）
    sparse_pages = []
    for name, data in pages.items():
        if (not data["is_wip"] and data["dir"] in PAGE_DIRS
            and data["line_count"] < 5 and data["line_count"] > 0):
            sparse_pages.append({
                "name": name, "type": data["type"],
                "inbound": inbound.get(name, 0),
                "lines": data["line_count"],
            })
    sparse_pages.sort(key=lambda x: -x["inbound"])

    # 3c. 孤儿页面（无入站链接，非 wip，有内容）
    orphans = []
    for name, data in pages.items():
        if (data["dir"] in PAGE_DIRS and not data["is_wip"]
            and data["line_count"] >= 5 and inbound.get(name, 0) == 0):
            orphans.append({
                "name": name, "type": data["type"],
                "lines": data["line_count"],
            })
    orphans.sort(key=lambda x: -x["lines"])

    # 3d. 高价值空白（被多次引用但不存在的页面 = 断链目标）
    missing_targets = defaultdict(int)
    for name, data in pages.items():
        for link in data["links"]:
            if link not in pages:
                missing_targets[link] += 1
    high_value_gaps = sorted(missing_targets.items(), key=lambda x: -x[1])

    # 4. 生成研究议程
    out = []
    out.append("# 研究议程 — 知识空白分析")
    out.append(f"\n> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    out.append(f"> 总页面: {len(pages)} | wip: {len(wip_pages)} | 稀少: {len(sparse_pages)} | 孤儿: {len(orphans)}")
    out.append("")

    # 高优先级：被多次引用的 wip 页面
    out.append("## 🔴 高优先级：被引用的 wip 页面")
    out.append("\n这些页面被其他页面引用，填充后能显著提升知识网络连通性。")
    out.append("")
    high_priority = [p for p in wip_pages if p["inbound"] >= 2][:30]
    if high_priority:
        for i, p in enumerate(high_priority, 1):
            out.append(f"{i}. **[[{p['name']}]]** ({p['type']}) — 入链: {p['inbound']}")
    else:
        out.append("- 无")

    # 中优先级：高入站的稀少页面
    out.append("\n## 🟡 中优先级：内容稀少但被引用的页面")
    out.append("\n这些页面有内容但太少，值得扩充。")
    out.append("")
    medium_priority = [p for p in sparse_pages if p["inbound"] >= 1][:20]
    if medium_priority:
        for i, p in enumerate(medium_priority, 1):
            out.append(f"{i}. **[[{p['name']}]]** ({p['type']}) — {p['lines']}行, 入链: {p['inbound']}")
    else:
        out.append("- 无")

    # 研究主题建议
    out.append("\n## 📚 建议研究主题")
    out.append("\n基于 wip 页面的主题聚类，建议以下研究方向：")
    out.append("")

    # 按主题聚类 wip 页面
    topic_clusters = defaultdict(list)
    for p in wip_pages[:100]:
        # 简单聚类：按名称中的关键词
        name = p["name"]
        if "etf" in name.lower() or "fund" in name.lower() or "index" in name.lower():
            topic_clusters["ETF/基金/指数"].append(p["name"])
        elif "stock" in name.lower() or "market" in name.lower() or "trade" in name.lower():
            topic_clusters["股票/市场/交易"].append(p["name"])
        elif "valuation" in name.lower() or "pe" in name.lower() or "pb" in name.lower():
            topic_clusters["估值分析"].append(p["name"])
        elif "ai" in name.lower() or "llm" in name.lower() or "agent" in name.lower():
            topic_clusters["AI/LLM/Agent"].append(p["name"])
        elif "invest" in name.lower() or "portfolio" in name.lower() or "asset" in name.lower():
            topic_clusters["投资策略/资产配置"].append(p["name"])
        elif "心理" in name or "emotion" in name.lower() or "fear" in name.lower() or "greed" in name.lower():
            topic_clusters["投资心理"].append(p["name"])
        else:
            topic_clusters["其他"].append(p["name"])

    for topic, pages_list in sorted(topic_clusters.items(), key=lambda x: -len(x[1])):
        out.append(f"### {topic} ({len(pages_list)} 个待填充)")
        out.append(f"- 建议搜索: \"{topic} 投资 指数\" 或 \"{topic} 知识体系\"")
        out.append(f"- 代表页面: {', '.join(f'[[{p}]]' for p in pages_list[:5])}")
        out.append("")

    # 搜索查询建议
    out.append("## 🔍 建议搜索查询")
    out.append("\n可直接复制到搜索栏的查询：")
    out.append("")
    search_queries = []
    for p in wip_pages[:20]:
        name = p["name"].replace("-", " ")
        search_queries.append(f"- \"{name}\" — 填充 [[{p['name']}]]")
    for q in search_queries:
        out.append(q)

    # 孤儿页面（需要交叉引用）
    out.append("\n## 🔗 孤儿页面（需要交叉引用）")
    out.append(f"\n这些页面有内容但没有被任何页面链接，需要添加交叉引用。")
    out.append(f"\n前 20 个：")
    for p in orphans[:20]:
        out.append(f"- [[{p['name']}]] ({p['type']}, {p['lines']}行)")

    # 写入
    agenda_path = os.path.join(WIKI, "_meta", "research-agenda.md")
    with open(agenda_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    # 终端摘要
    print(f"wip 页面: {len(wip_pages)} (高优先级: {len(high_priority)})")
    print(f"稀少页面: {len(sparse_pages)} (中优先级: {len(medium_priority)})")
    print(f"孤儿页面: {len(orphans)}")
    print(f"研究主题: {len(topic_clusters)} 个")
    print(f"\n已保存: _meta/research-agenda.md")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MOC（Map of Content）生成器：按主题聚类页面，创建导航中心。

用法: python3 build_moc.py [--root /path/to/wiki]
"""
import os, re, sys
from datetime import datetime
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

PAGE_DIRS = ["entities", "concepts", "comparisons", "queries"]
today = datetime.now().strftime("%Y-%m-%d")

# 主题定义：名称 → (图标, 关键词列表, 描述)
TOPICS = {
    "投资体系": {
        "icon": "📊",
        "keywords": ["invest", "asset", "portfolio", "position", "rebalanc", "allocation",
                     "etf", "fund", "index", "stock", "bond", "commodity", "gold", "oil",
                     "valuation", "pe", "pb", "dividend", "yield", "market",
                     "bull", "bear", "cycle", "diamond", "bottom", "top",
                     "grid", "dca", "swing", "band", "target",
                     "fear", "greed", "emotion", "psycholog", "patience", "discipline",
                     "risk", "hedge", "stop-loss", "protect",
                     "sector", "size", "china", "us", "hk", "global",
                     "edazhangyou", "changwin", "long-win", "salute",
                     "消费", "医药", "科技", "金融", "红利", "恒生", "沪深", "中证",
                     "标普", "纳斯达克", "创业板", "科创", "黄金", "原油", "白银",
                     "估值", "仓位", "配置", "定投", "网格", "波段", "止盈", "止损",
                     "贪婪", "恐惧", "心态", "纪律", "信仰"],
        "desc": "投资相关的知识地图，涵盖 ETF、估值、资产配置、投资心理等。",
    },
    "AI与自动化": {
        "icon": "🤖",
        "keywords": ["ai", "llm", "agent", "model", "gpt", "claude", "openai",
                     "prompt", "fine-tun", "inference", "embed", "vector", "rag",
                     "automat", "workflow", "pipeline", "skill", "tool",
                     "hermes", "openclaw", "minimax", "nvidia",
                     "multi-agent", "autonomous", "reasoning", "context",
                     "代码", "编程", "开发", "部署", "模型", "推理", "训练"],
        "desc": "AI 技术、智能代理、自动化工作流相关的知识地图。",
    },
    "知识管理": {
        "icon": "🧠",
        "keywords": ["knowledge", "pkm", "second-brain", "zettelkasten", "note",
                     "obsidian", "wiki", "memex", "digital-garden",
                     "backup", "sync", "organiz", "structur", "index",
                     "知识库", "笔记", "第二大脑", "数字花园", "备份", "同步"],
        "desc": "个人知识管理、笔记方法、Obsidian 使用相关的知识地图。",
    },
}


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


def classify_page(name, content):
    """将页面分类到主题。"""
    text = (name + " " + content[:500]).lower()
    scores = {}
    for topic, info in TOPICS.items():
        score = sum(1 for kw in info["keywords"] if kw in text)
        if score > 0:
            scores[topic] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


def main():
    print("=== MOC 导航页生成器 ===\n")

    # 1. 加载页面
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
            pages[name] = {"path": path, "type": d.rstrip("s"), "content": content, "dir": d}

    # 2. 分类
    topic_pages = defaultdict(list)
    unclassified = []
    for name, data in pages.items():
        topic = classify_page(name, data["content"])
        if topic:
            topic_pages[topic].append(name)
        else:
            unclassified.append(name)

    # 3. 计算入站链接（用于排序）
    inbound = defaultdict(int)
    for name, data in pages.items():
        for link in extract_links(strip_fm(data["content"])):
            if link in pages:
                inbound[link] += 1

    # 4. 生成 MOC 页面
    for topic, info in TOPICS.items():
        page_list = topic_pages.get(topic, [])
        if not page_list:
            continue

        # 按入站链接排序
        page_list.sort(key=lambda n: -inbound.get(n, 0))

        # 按类型分组
        by_type = defaultdict(list)
        for name in page_list:
            ptype = pages[name]["type"]
            by_type[ptype].append(name)

        out = []
        out.append(f"---")
        out.append(f"title: \"{info['icon']} {topic}\"")
        out.append(f"created: {today}")
        out.append(f"updated: {today}")
        out.append(f"type: concept")
        out.append(f"tags: [moc, navigation]")
        out.append(f"---")
        out.append(f"")
        out.append(f"# {info['icon']} {topic}")
        out.append(f"")
        out.append(f"> {info['desc']}")
        out.append(f"> 共 {len(page_list)} 个页面。")
        out.append(f"")

        # 按类型列出
        type_names = {"entity": "🏷️ 实体", "concept": "💡 概念",
                     "comparison": "⚖️ 对比", "query": "🔍 查询"}
        for ptype in ["entity", "concept", "comparison", "query"]:
            names = by_type.get(ptype, [])
            if not names:
                continue
            out.append(f"## {type_names.get(ptype, ptype)} ({len(names)})")
            out.append(f"")
            for name in names[:50]:  # 限制每类最多 50 个
                inbound_count = inbound.get(name, 0)
                marker = " ⭐" if inbound_count >= 5 else ""
                out.append(f"- [[{name}]]{marker}")
            if len(names) > 50:
                out.append(f"- ... 还有 {len(names) - 50} 个")
            out.append(f"")

        # 相关 MOC
        out.append(f"## 🔗 相关导航")
        out.append(f"")
        for other_topic, other_info in TOPICS.items():
            if other_topic != topic:
                out.append(f"- [[MOC-{other_topic}|{other_info['icon']} {other_topic}]]")
        out.append(f"")

        # 写入
        moc_path = os.path.join(WIKI, "concepts", f"MOC-{topic}.md")
        with open(moc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        print(f"  {info['icon']} MOC-{topic}: {len(page_list)} 个页面")

    # 5. 生成总导航页
    out = []
    out.append(f"---")
    out.append(f"title: \"🗺️ 知识地图\"")
    out.append(f"created: {today}")
    out.append(f"updated: {today}")
    out.append(f"type: concept")
    out.append(f"tags: [moc, navigation, index]")
    out.append(f"---")
    out.append(f"")
    out.append(f"# 🗺️ 知识地图")
    out.append(f"")
    out.append(f"> 知识库的导航中心。按主题浏览，快速找到你需要的内容。")
    out.append(f"> 总页面: {len(pages)} | 未分类: {len(unclassified)}")
    out.append(f"")
    for topic, info in TOPICS.items():
        count = len(topic_pages.get(topic, []))
        if count > 0:
            out.append(f"- [[MOC-{topic}|{info['icon']} {topic}]] ({count} 页)")
    out.append(f"")
    out.append(f"## 📋 其他入口")
    out.append(f"")
    out.append(f"- [[index]] — 完整目录（按类型）")
    out.append(f"- [[research-agenda]] — 研究议程（知识空白）")
    out.append(f"- [[hot-cache]] — 会话记忆")
    out.append(f"")

    moc_path = os.path.join(WIKI, "concepts", "MOC-知识地图.md")
    with open(moc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"\n  🗺️ MOC-知识地图: 总导航")

    print(f"\n完成! 在 Obsidian 中打开 MOC 页面浏览知识地图。")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
auto_research.py — 自主研究助手 v3（Loop 3：研究闭环）

识别知识空白，生成研究议程，追踪议题状态（pending/in-progress/done）。
Loop 3 核心：空白 → 研究 → 填补 → 新空白（永续循环）。

v3 新增：
  - 中文目录路径
  - 议题状态追踪（pending/in-progress/done）
  - 跳过 done 状态议题，聚焦新空白
  - 持久化议程到 _meta/research-agenda.md

用法:
  python3 scripts/auto_research.py [--root /path/to/wiki]
  python3 scripts/auto_research.py --status   # 只显示议题状态统计
"""
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import (
    AREA_AI_AUTOMATION,
    AREA_HONG_KONG,
    AREA_INVESTMENT,
    AREA_KB_OPS,
    AREA_UNCLASSIFIED_SYNTHESIS,
    get_wiki_root,
    ALL_PAGE_DIRS,
    META_FILES,
)
from wiki_dirs import DIRS

today = datetime.now().strftime("%Y-%m-%d")

PAGE_DIRS = [
    DIRS["实体"],
    DIRS["概念"],
    DIRS["对比"],
    DIRS["查询"],
    AREA_INVESTMENT,
    AREA_AI_AUTOMATION,
    AREA_HONG_KONG,
    AREA_KB_OPS,
    AREA_UNCLASSIFIED_SYNTHESIS,
]


def strip_fm(c: str) -> str:
    if c.startswith("---"):
        e = c.find("\n---", 3)
        if e != -1:
            return c[e + 4:]
    return c


def extract_links(body: str) -> list[str]:
    raw = re.findall(r'\[\[([^\]]+)\]\]', body)
    return [l.split("|")[0].split("#")[0].strip()
            for l in raw if l.split("|")[0].split("#")[0].strip()]


def load_existing_agenda(agenda_path: Path) -> dict[str, str]:
    """
    从已有的 research-agenda.md 加载议题状态。
    返回 {议题关键词: status}，status in {pending, in-progress, done}。
    """
    if not agenda_path.exists():
        return {}
    content = agenda_path.read_text(encoding="utf-8")
    result = {}
    for line in content.splitlines():
        # 匹配格式：- [x] 议题 (status: done) 或 - [ ] 议题
        done_match = re.match(r'^-\s*\[x\]\s+(.+?)(?:\s+\(.*\))?$', line)
        prog_match = re.match(r'^-\s*\[>\]\s+(.+?)(?:\s+\(.*\))?$', line)
        pend_match = re.match(r'^-\s*\[\s*\]\s+(.+?)(?:\s+\(.*\))?$', line)
        if done_match:
            result[done_match.group(1).strip()] = "done"
        elif prog_match:
            result[prog_match.group(1).strip()] = "in-progress"
        elif pend_match:
            result[pend_match.group(1).strip()] = "pending"
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="自主研究助手 v3")
    parser.add_argument("--root", "--wiki-root", help="wiki 根目录路径")
    parser.add_argument("--status", action="store_true", help="只显示议题状态统计")
    args = parser.parse_args()

    WIKI = get_wiki_root(override=args.root)

    print("=== 自主研究助手 v3（Loop 3：研究闭环）===\n")

    # 加载已有议程
    agenda_path = WIKI / META_FILES["agenda"]
    existing = load_existing_agenda(agenda_path)
    done_count = sum(1 for s in existing.values() if s == "done")
    pending_count = sum(1 for s in existing.values() if s == "pending")
    inprog_count = sum(1 for s in existing.values() if s == "in-progress")

    if args.status:
        print(f"📊 研究议程状态：")
        print(f"  - ✅ 已完成：{done_count} 条")
        print(f"  - 🔄 进行中：{inprog_count} 条")
        print(f"  - ⏳ 待研究：{pending_count} 条")
        return

    # 1. 加载所有页面
    pages = {}
    for d in ALL_PAGE_DIRS:
        dp = WIKI / d
        if not dp.is_dir():
            continue
        for f in dp.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                body = strip_fm(content)
                links = extract_links(body)
                is_wip = bool(re.search(r'tags:.*wip', content, re.IGNORECASE))
                text_lines = [l.strip() for l in body.split("\n")
                             if l.strip() and not l.strip().startswith("#")
                             and not l.strip().startswith("---")
                             and not l.strip().startswith("> [!")]
                pages[f.stem] = {
                    "path": f, "dir": d, "content": content,
                    "links": links, "is_wip": is_wip, "line_count": len(text_lines)
                }
            except Exception:
                pass

    if not pages:
        print("⚠️  知识库为空，先加工一些文章再运行研究助手。")
        return

    # 2. 计算入站链接
    inbound = defaultdict(int)
    for name, data in pages.items():
        for link in data["links"]:
            if link in pages:
                inbound[link] += 1

    # 3. 识别知识空白
    wip_pages = []
    for name, data in pages.items():
        if data["is_wip"] and data["dir"] in PAGE_DIRS:
            wip_pages.append({
                "name": name, "dir": data["dir"],
                "inbound": inbound.get(name, 0),
                "outbound": len(data["links"]),
            })
    wip_pages.sort(key=lambda x: -x["inbound"])

    sparse_pages = [
        {"name": name, "dir": data["dir"],
         "inbound": inbound.get(name, 0), "lines": data["line_count"]}
        for name, data in pages.items()
        if data["line_count"] < 5 and not data["is_wip"] and data["dir"] in PAGE_DIRS
    ]
    sparse_pages.sort(key=lambda x: -x["inbound"])

    # 悬挂引用（被引用但不存在的页面）
    all_links_in_wiki = set()
    for data in pages.values():
        all_links_in_wiki.update(data["links"])
    dangling = sorted(all_links_in_wiki - set(pages.keys()))

    # 重要页面覆盖率（入站链接多，但出站链接少）
    low_context = [
        {"name": name, "inbound": inbound.get(name, 0), "outbound": len(data["links"])}
        for name, data in pages.items()
        if inbound.get(name, 0) >= 3 and len(data["links"]) < 2
        and data["dir"] in PAGE_DIRS
    ]
    low_context.sort(key=lambda x: -x["inbound"])

    # P-index 覆盖缺口：概念/实体页应至少有一个问题页指向它。
    p_index_dir = WIKI / DIRS["问题索引"]
    p_index_text = ""
    if p_index_dir.is_dir():
        for f in sorted(p_index_dir.glob("*.md")):
            try:
                p_index_text += "\n" + f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
    p_index_gaps = [
        {"name": name, "dir": data["dir"], "inbound": inbound.get(name, 0)}
        for name, data in pages.items()
        if data["dir"] in [DIRS["概念"], DIRS["实体"]]
        and f"[[{name}]]" not in p_index_text
        and f"[[{data['dir']}/{name}]]" not in p_index_text
    ]
    p_index_gaps.sort(key=lambda x: (-x["inbound"], x["name"]))

    # 4. 生成研究议程（跳过已完成议题）
    new_items = []

    for p in wip_pages[:5]:
        topic = f"深化「{p['name']}」（WIP，被引用 {p['inbound']} 次）"
        if existing.get(topic) == "done":
            continue
        new_items.append(topic)

    for p in sparse_pages[:5]:
        topic = f"扩展「{p['name']}」（内容稀少，被引用 {p['inbound']} 次）"
        if existing.get(topic) == "done":
            continue
        new_items.append(topic)

    for d in dangling[:10]:
        topic = f"创建缺失页面「{d}」（被多处引用但不存在）"
        if existing.get(topic) == "done":
            continue
        new_items.append(topic)

    for p in low_context[:3]:
        topic = f"补充「{p['name']}」的上下文（高被引但出站链接少）"
        if existing.get(topic) == "done":
            continue
        new_items.append(topic)

    for p in p_index_gaps[:5]:
        topic = f"补充「{p['name']}」的 P-index 问题索引（P-index 未覆盖）"
        if existing.get(topic) == "done":
            continue
        new_items.append(topic)

    # 5. 生成搜索查询建议
    domain_terms = set()
    for name, data in pages.items():
        if data["dir"] in [DIRS["概念"], DIRS["实体"]] and inbound.get(name, 0) >= 2:
            domain_terms.add(name)
    top_terms = sorted(domain_terms, key=lambda x: -inbound.get(x, 0))[:8]

    search_queries = []
    for term in top_terms:
        search_queries.append(f"「{term}」最新发展 2026")
    if dangling[:3]:
        for d in dangling[:3]:
            search_queries.append(f"「{d}」是什么")

    # 6. 构建议程报告
    lines = [
        f"# 研究议程",
        f"",
        f"> 生成时间：{today}",
        f"> 状态：✅ 已完成 {done_count} | 🔄 进行中 {inprog_count} | ⏳ 待研究 {pending_count}",
        f"> Loop 3：空白 → 研究 → 填补 → 新空白（永续循环）",
        f"",
        f"## 新发现的研究议题",
        f"",
    ]

    if not new_items:
        lines.append("- ✅ 暂无新知识空白，知识库相对完整！")
    else:
        for item in new_items:
            status = existing.get(item, "pending")
            checkbox = "[x]" if status == "done" else ("[>]" if status == "in-progress" else "[ ]")
            lines.append(f"- {checkbox} {item}")

    lines += [
        "",
        "## 建议搜索查询",
        "",
    ]
    for q in search_queries[:8]:
        lines.append(f"- {q}")

    lines += [
        "",
        "## 知识库快照",
        "",
        f"- 总页面数：{len(pages)}",
        f"- WIP 页面：{len(wip_pages)}",
        f"- 稀少页面（<5行）：{len(sparse_pages)}",
        f"- 悬挂引用（未创建页面）：{len(dangling)}",
        f"- P-index 未覆盖页面：{len(p_index_gaps)}",
        "",
        "## 已完成的研究（Loop 3 历史）",
        "",
    ]

    done_items = [(k, v) for k, v in existing.items() if v == "done"]
    if done_items:
        for item, _ in done_items[-10:]:  # 最近 10 条
            lines.append(f"- [x] {item}")
    else:
        lines.append("- （暂无完成记录）")

    lines += ["", "---", f"_由 auto_research.py v3 生成于 {today}_"]

    report = "\n".join(lines)

    # 打印摘要
    print(f"📊 知识库现状：")
    print(f"  总页面：{len(pages)}，WIP：{len(wip_pages)}，稀少：{len(sparse_pages)}，悬挂引用：{len(dangling)}")
    print(f"\n📋 新研究议题（{len(new_items)} 条）：")
    for item in new_items[:5]:
        print(f"  - {item}")
    if len(new_items) > 5:
        print(f"  ... 还有 {len(new_items) - 5} 条")

    print(f"\n🔍 建议搜索：")
    for q in search_queries[:3]:
        print(f"  - {q}")

    # 写入文件
    meta_dir = WIKI / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    agenda_path.write_text(report, encoding="utf-8")
    print(f"\n✅ 研究议程已更新：_meta/research-agenda.md")
    print(f"   告诉 Minis「深入研究 [议题名称]」来处理某个议题")
    print(f"   Minis 处理完后，将对应条目从 [ ] 改为 [x]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""知识库健康修复脚本（优化版）。

预加载所有页面到内存 + 关键词倒排索引，避免 O(n²) 遍历。
适用于 3000+ 页面的大型知识库。

用法: python3 fix_health.py [--root /path/to/wiki]
"""
import os, re, sys
from datetime import datetime
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

DIRS = {"entities": "entity", "concepts": "concept",
        "comparisons": "comparison", "queries": "query",
        "synthesis": "synthesis"}
FIELDS = ["title", "created", "updated", "type", "tags"]
today = datetime.now().strftime("%Y-%m-%d")


def preload():
    """一次性加载所有页面到内存，构建关键词索引。"""
    pages = {}   # name -> {path, type, content, links}
    word_idx = defaultdict(set)  # word -> {names}

    for d, pt in DIRS.items():
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
            pages[name] = {"path": path, "type": pt, "content": content, "links": links}
            for w in re.split(r'[-_ ]', name.lower()):
                if len(w) > 2:
                    word_idx[w].add(name)
    return pages, word_idx


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


def find_related(name, word_idx, pages, n=3):
    """通过关键词索引快速查找相关页面。"""
    words = set(re.split(r'[-_ ]', name.lower()))
    words = {w for w in words if len(w) > 2}
    if not words:
        return []
    candidates = defaultdict(int)
    for w in words:
        for other in word_idx.get(w, set()):
            if other != name:
                candidates[other] += 1
    ranked = sorted(candidates.items(), key=lambda x: -x[1])
    return [r[0] for r in ranked[:n]]


def file_date(path):
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")


# ── Step 1: 格式修复 ──

def fix_format(pages):
    count = 0
    for name, data in pages.items():
        content = data["content"]
        title = name.replace("-", " ").strip()
        date = file_date(data["path"])
        pt = data["type"]

        if not content.startswith("---"):
            fm = f"---\ntitle: {title}\ncreated: {date}\nupdated: {date}\ntype: {pt}\ntags: []\n---\n\n"
            with open(data["path"], "w", encoding="utf-8") as f:
                f.write(fm + content)
            data["content"] = fm + content
            count += 1
            continue

        end = content.find("\n---", 3)
        if end == -1:
            continue
        fm = content[3:end]
        body = content[end+4:]
        added = []
        for field in FIELDS:
            if not re.search(rf'^{field}\s*:', fm, re.MULTILINE):
                val = {"title": title, "created": date, "updated": date,
                       "type": pt, "tags": "[]"}[field]
                fm += f"\n{field}: {val}"
                added.append(field)
        if added:
            new_content = f"---\n{fm}\n---\n{body}"
            with open(data["path"], "w", encoding="utf-8") as f:
                f.write(new_content)
            data["content"] = new_content
            count += 1
    return count


# ── Step 2: 修复断链 ──

def fix_broken(pages, word_idx):
    # 收集所有断链目标
    missing = defaultdict(list)
    for name, data in pages.items():
        for link in data["links"]:
            if link not in pages:
                missing[link].append(name)

    if not missing:
        return 0

    count = 0
    for target in missing:
        if target in pages:
            continue
        path = os.path.join(WIKI, "concepts", f"{target}.md")
        if os.path.exists(path):
            continue

        # 修复格式错误的链接名（含特殊字符的跳过）
        if re.search(r'[\n\r]', target):
            continue

        title = target.replace("-", " ").strip()
        related = find_related(target, word_idx, pages, 2)
        ol = "\n".join(f"- [[{r}]]" for r in related) if related \
             else "- [[investment-system]]\n- [[asset-allocation]]"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"---\ntitle: {title}\ncreated: {today}\nupdated: {today}\n"
                    f"type: concept\ntags: [wip]\nsources: []\n---\n\n"
                    f"# {title}\n\n待补充。\n\n## 相关概念\n{ol}\n")
        pages[target] = {"path": path, "type": "concept",
                         "content": "", "links": []}
        word_idx_update(word_idx, target)
        count += 1

    # 清理格式错误的链接
    for name, data in list(pages.items()):
        content = data["content"]
        fixed = re.sub(r'\[\[[^\]]*\n[^\]]*\]\]', '', content)
        if fixed != content:
            with open(data["path"], "w", encoding="utf-8") as f:
                f.write(fixed)
            data["content"] = fixed

    return count


def word_idx_update(word_idx, name):
    for w in re.split(r'[-_ ]', name.lower()):
        if len(w) > 2:
            word_idx[w].add(name)


# ── Step 3: 补充出站链接 ──

def fix_outlinks(pages, word_idx):
    todo = [(n, d) for n, d in pages.items() if len(d["links"]) < 2]
    if not todo:
        return 0

    count = 0
    for i, (name, data) in enumerate(todo):
        related = find_related(name, word_idx, pages, 3)
        if not related:
            continue
        existing = set(data["links"])
        new_links = [f"- [[{r}]]" for r in related if r not in existing]
        if not new_links:
            continue

        content = data["content"]
        if "## 相关" in content:
            lines = content.split("\n")
            sec_start = -1
            sec_end = len(lines)
            for j, line in enumerate(lines):
                if "## 相关" in line:
                    sec_start = j
                elif sec_start >= 0 and line.startswith("## "):
                    sec_end = j
                    break
            if sec_start >= 0:
                for k, link in enumerate(new_links):
                    lines.insert(sec_end + k, link)
                content = "\n".join(lines)
        else:
            content = content.rstrip() + "\n\n## 相关概念\n" + "\n".join(new_links) + "\n"

        with open(data["path"], "w", encoding="utf-8") as f:
            f.write(content)
        data["content"] = content
        data["links"] = extract_links(strip_fm(content))
        count += 1
        if (i + 1) % 500 == 0:
            print(f"    {i+1}/{len(todo)}")

    return count


# ── Step 4: 拆分超大页面 ──

def split_oversized(pages):
    count = 0
    for name, data in list(pages.items()):
        lines = data["content"].split("\n")
        if len(lines) <= 200:
            continue

        fm_end = 0
        if data["content"].startswith("---"):
            idx = data["content"].find("\n---", 3)
            if idx != -1:
                fm_end = data["content"][:idx+4].count("\n")

        sections, cur = [], []
        for i, line in enumerate(lines):
            if i > fm_end and line.startswith("## "):
                if cur:
                    sections.append(cur)
                cur = [line]
            else:
                cur.append(line)
        if cur:
            sections.append(cur)
        if len(sections) <= 1:
            continue

        chunks, chunk = [], []
        for sec in sections:
            if len(chunk) + len(sec) > 150 and chunk:
                chunks.append(chunk)
                chunk = []
            chunk.extend(sec)
        if chunk:
            chunks.append(chunk)
        if len(chunks) <= 1:
            continue

        dir_path = os.path.dirname(data["path"])
        sub_names = []
        for i, chk in enumerate(chunks):
            sn = f"{name}-part-{i+1}"
            sp = os.path.join(dir_path, f"{sn}.md")
            st = sn.replace("-", " ")
            for line in chk:
                if line.startswith("## "):
                    st = line[3:].strip()
                    break
            with open(sp, "w", encoding="utf-8") as f:
                f.write(f"---\ntitle: {st}\ncreated: {today}\nupdated: {today}\n"
                        f"type: {data['type']}\ntags: [wip]\nsources: []\n---\n\n"
                        f"# {st}\n\n" + "\n".join(chk) + "\n")
            sub_names.append(sn)
            pages[sn] = {"path": sp, "type": data["type"], "content": "", "links": []}
            word_idx_update({}, sn)  # placeholder, caller should rebuild index

        fm_m = re.match(r'---\n(.*?)\n---', data["content"], re.DOTALL)
        fm = fm_m.group(0) if fm_m else \
             f"---\ntitle: {name.replace('-',' ')}\ncreated: {today}\nupdated: {today}\ntype: {data['type']}\ntags: []\n---"
        fm = re.sub(r'updated:\s*\S+', f'updated: {today}', fm)
        sl = "\n".join(f"- [[{s}]]" for s in sub_names)
        main = f"{fm}\n\n# {name.replace('-',' ')}\n\n## 子主题\n\n{sl}\n"
        with open(data["path"], "w", encoding="utf-8") as f:
            f.write(main)
        data["content"] = main
        count += 1

    return count


# ── 更新 index.md ──

def update_index(pages):
    by_type = defaultdict(list)
    for name, data in pages.items():
        body = strip_fm(data.get("content", ""))
        summary = ""
        for line in body.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                summary = line[:80]
                break
        by_type[data["type"]].append((name, summary))

    secs = {"entity": "Entities", "concept": "Concepts",
            "comparison": "Comparisons", "query": "Queries"}
    total = sum(len(v) for v in by_type.values())
    out = (f"# Wiki Index\n\n> 内容目录。每个 wiki 页面按类型分类，附带一行摘要。\n"
           f"> 先读这个来找到任何查询的相关页面。\n"
           f"> 最后更新: {today} | 总页数: {total}\n\n")
    for pt, title in secs.items():
        items = sorted(by_type.get(pt, []))
        out += f"## {title}\n\n<!-- 按字母顺序排列 -->\n\n"
        for n, s in items:
            out += f"- [[{n}]] - {s}\n"
        out += "\n"
    with open(os.path.join(WIKI, "index.md"), "w", encoding="utf-8") as f:
        f.write(out)
    return total


# ── 更新 log.md ──

def update_log(stats):
    with open(os.path.join(WIKI, "log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## [{today}] 健康修复（fix_health.py）\n")
        for k, v in stats.items():
            f.write(f"- {k}: {v}\n")


# ── main ──

def main():
    print("=== 知识库健康修复 ===\n")
    print("加载页面到内存...")
    pages, word_idx = preload()
    print(f"  {len(pages)} 个页面, {len(word_idx)} 个关键词\n")

    stats = {}

    print("[1/4] 格式修复...")
    stats["格式修复"] = fix_format(pages)
    print(f"  → {stats['格式修复']}\n")

    print("[2/4] 断链修复...")
    stats["断链修复"] = fix_broken(pages, word_idx)
    print(f"  → {stats['断链修复']}\n")

    print("[3/4] 补充出站链接...")
    stats["出站链接"] = fix_outlinks(pages, word_idx)
    print(f"  → {stats['出站链接']}\n")

    print("[4/4] 拆分超大页面...")
    stats["拆分页面"] = split_oversized(pages)
    print(f"  → {stats['拆分页面']}\n")

    print("更新索引...")
    stats["总页面数"] = update_index(pages)
    print(f"  → {stats['总页面数']}\n")

    print("更新日志...")
    update_log(stats)

    print("=== 完成 ===")


if __name__ == "__main__":
    main()

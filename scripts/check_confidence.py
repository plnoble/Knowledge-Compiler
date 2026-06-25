#!/usr/bin/env python3
"""置信度检查 + 零幻觉验证：分析页面来源引用和内容质量。

用法: python3 check_confidence.py [--root /path/to/wiki] [--fix]
--fix: 自动为页面添加 confidence 字段

输出: _meta/confidence-report.md
"""
import os, re, sys
from datetime import datetime
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

FIX_MODE = "--fix" in sys.argv

PAGE_DIRS = ["entities", "concepts", "comparisons", "queries"]
REQUIRED_FIELDS = ["title", "created", "updated", "type", "tags", "sources"]
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


def parse_frontmatter(content):
    """解析 frontmatter 字段。"""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end]
    result = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def calculate_confidence(name, content, fm, links, line_count, is_wip):
    """计算置信度等级。"""
    # 来源数量
    sources_raw = fm.get("sources", "")
    has_sources = sources_raw and sources_raw != "[]" and sources_raw != ""
    
    # 出站链接数
    outlink_count = len(links)
    
    # 正文行数（排除 frontmatter）
    body = strip_fm(content)
    text_lines = [l.strip() for l in body.split("\n")
                 if l.strip() and not l.strip().startswith("#")
                 and not l.strip().startswith("---")
                 and not l.strip().startswith("> [!")]
    
    # 判定逻辑
    if is_wip and not has_sources:
        return "quarantine"
    if not has_sources and len(text_lines) < 3:
        return "quarantine"
    if not has_sources or len(text_lines) < 10:
        return "low"
    if has_sources and outlink_count >= 2 and len(text_lines) >= 10:
        if outlink_count >= 5 and len(text_lines) >= 50:
            return "high"
        return "medium"
    return "low"


def main():
    print("=== 置信度检查 + 零幻觉验证 ===\n")

    # 1. 扫描所有页面
    pages = []
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
            
            fm = parse_frontmatter(content)
            body = strip_fm(content)
            links = extract_links(body)
            is_wip = "tags: [wip]" in content or "tags: [wip," in content
            line_count = content.count("\n") + 1
            
            # 当前置信度
            current_conf = fm.get("confidence", "未标注")
            
            # 计算建议置信度
            suggested_conf = calculate_confidence(name, content, fm, links, line_count, is_wip)
            
            # 来源状态
            sources_raw = fm.get("sources", "")
            has_sources = sources_raw and sources_raw != "[]" and sources_raw != ""
            
            pages.append({
                "name": name, "dir": d, "path": path,
                "content": content, "fm": fm,
                "current_conf": current_conf, "suggested_conf": suggested_conf,
                "has_sources": has_sources, "is_wip": is_wip,
                "outlink_count": len(links), "line_count": line_count,
            })

    # 2. 统计
    conf_counts = defaultdict(int)
    source_counts = {"有来源": 0, "无来源": 0}
    for p in pages:
        conf_counts[p["suggested_conf"]] += 1
        if p["has_sources"]:
            source_counts["有来源"] += 1
        else:
            source_counts["无来源"] += 1

    # 3. 修复模式：自动添加 confidence 字段
    fixed = 0
    if FIX_MODE:
        for p in pages:
            if p["current_conf"] != p["suggested_conf"]:
                content = p["content"]
                fm = p["fm"]
                
                if "confidence" in fm:
                    # 更新现有字段
                    content = re.sub(
                        r'confidence:\s*\S+',
                        f'confidence: {p["suggested_conf"]}',
                        content
                    )
                else:
                    # 添加新字段（在 tags 行之后）
                    content = re.sub(
                        r'(tags:\s*\[[^\]]*\])',
                        f'\\1\nconfidence: {p["suggested_conf"]}',
                        content,
                        count=1
                    )
                
                with open(p["path"], "w", encoding="utf-8") as f:
                    f.write(content)
                fixed += 1

    # 4. 生成报告
    out = []
    out.append("# 置信度报告 + 零幻觉验证")
    out.append(f"\n> 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    out.append(f"> 总页面: {len(pages)}")
    out.append("")

    # 置信度分布
    out.append("## 置信度分布")
    out.append("")
    level_emoji = {"high": "🟢", "medium": "🟡", "low": "🟠", "quarantine": "🔴"}
    for level in ["high", "medium", "low", "quarantine"]:
        count = conf_counts.get(level, 0)
        pct = count * 100 // max(1, len(pages))
        out.append(f"- {level_emoji.get(level, '⚪')} **{level}**: {count} ({pct}%)")
    out.append("")

    # 来源覆盖
    out.append("## 来源覆盖（零幻觉）")
    out.append("")
    total = len(pages)
    sourced_pct = source_counts["有来源"] * 100 // max(1, total)
    out.append(f"- ✅ 有来源: {source_counts['有来源']} ({sourced_pct}%)")
    out.append(f"- ❌ 无来源: {source_counts['无来源']} ({100 - sourced_pct}%)")
    out.append("")

    # 隔离页面
    quarantine_pages = [p for p in pages if p["suggested_conf"] == "quarantine"]
    out.append(f"## 🔴 隔离页面 ({len(quarantine_pages)})")
    out.append("\n这些页面无来源且内容不足，需补充来源后才能使用。")
    out.append("")
    for p in quarantine_pages[:30]:
        out.append(f"- `{p['dir']}/{p['name']}` — {p['line_count']}行, 出链:{p['outlink_count']}")
    if len(quarantine_pages) > 30:
        out.append(f"- ... 还有 {len(quarantine_pages) - 30} 个")
    out.append("")

    # 低置信度页面
    low_pages = [p for p in pages if p["suggested_conf"] == "low"]
    out.append(f"## 🟠 低置信度页面 ({len(low_pages)})")
    out.append("\n这些页面缺少来源或内容不足，仅作参考。")
    out.append("")
    for p in low_pages[:20]:
        reason = "无来源" if not p["has_sources"] else "内容不足"
        out.append(f"- `{p['dir']}/{p['name']}` — {reason}")
    out.append("")

    # 修复结果
    if FIX_MODE:
        out.append(f"## 修复结果")
        out.append(f"\n自动更新了 {fixed} 个页面的 confidence 字段。")

    # 写入
    report_path = os.path.join(WIKI, "_meta", "confidence-report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    # 终端输出
    print(f"置信度分布:")
    for level in ["high", "medium", "low", "quarantine"]:
        count = conf_counts.get(level, 0)
        print(f"  {level_emoji.get(level, '⚪')} {level}: {count}")
    print(f"\n来源覆盖: {source_counts['有来源']}/{total} ({sourced_pct}%)")
    print(f"隔离页面: {len(quarantine_pages)}")
    if FIX_MODE:
        print(f"修复: {fixed} 个页面")
    print(f"\n已保存: _meta/confidence-report.md")


if __name__ == "__main__":
    main()

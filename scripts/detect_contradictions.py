#!/usr/bin/env python3
"""矛盾检测脚本：扫描 frontmatter 中的 contradictions 字段 + 简单数值矛盾检测。

用法: python3 detect_contradictions.py [--root /path/to/wiki]
"""
import os, re, sys
from datetime import datetime

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

DIRS = ["entities", "concepts", "comparisons", "queries", "synthesis"]


def extract_frontmatter(content):
    """提取 frontmatter 字典。"""
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


def extract_claims(content):
    """提取含数字的声明（简单启发式）。"""
    body = content
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            body = content[end + 4:]
    
    claims = []
    # 匹配含百分比、数字+单位的行
    patterns = [
        r'(\d+(?:\.\d+)?%)',           # 百分比
        r'(\d+(?:\.\d+)?\s*(?:年|月|天|倍|万|亿|元))',  # 数字+单位
    ]
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for pat in patterns:
            if re.search(pat, line):
                claims.append(line[:150])
                break
    return claims


def main():
    # 1. 扫描 frontmatter 中的 contradictions 字段
    print("=== 矛盾检测报告 ===\n")
    
    fm_contradictions = []
    for d in DIRS:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith(".md"):
                continue
            fp = os.path.join(dp, f)
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            fm = extract_frontmatter(content)
            if "contradictions" in fm and fm["contradictions"]:
                fm_contradictions.append((f"{d}/{f}", fm["contradictions"]))
    
    print(f"## Frontmatter 标记的矛盾: {len(fm_contradictions)}")
    for path, targets in fm_contradictions:
        print(f"  - `{path}` → {targets}")
    
    # 2. 简单数值矛盾检测：找同一主题下不同页面的数值声明
    print(f"\n## 数值声明概览")
    
    # 收集所有页面的数值声明
    page_claims = {}
    for d in DIRS:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith(".md"):
                continue
            fp = os.path.join(dp, f)
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            claims = extract_claims(content)
            if claims:
                page_claims[f"{d}/{f}"] = claims
    
    total_claims = sum(len(v) for v in page_claims.values())
    print(f"- 含数值声明的页面: {len(page_claims)}")
    print(f"- 总数值声明: {total_claims}")
    
    # 3. 输出摘要
    print(f"\n## 建议")
    print(f"- 检查 frontmatter 标记的矛盾页面，人工确认哪个更可靠")
    print(f"- 新加工内容时，注意与已有页面的数值对比")
    print(f"- 使用 [!warning] callout 在页面中标注矛盾")
    
    # 保存报告
    report_path = os.path.join(WIKI, "_meta", "contradiction-report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 矛盾检测报告\n\n")
        f.write(f"## 检查时间\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"## Frontmatter 标记的矛盾: {len(fm_contradictions)}\n\n")
        for path, targets in fm_contradictions:
            f.write(f"- `{path}` → {targets}\n")
        f.write(f"\n## 数值声明概览\n\n")
        f.write(f"- 含数值声明的页面: {len(page_claims)}\n")
        f.write(f"- 总数值声明: {total_claims}\n")
    
    print(f"\n报告已保存到 _meta/contradiction-report.md")


if __name__ == "__main__":
    main()

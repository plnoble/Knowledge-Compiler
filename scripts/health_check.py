#!/usr/bin/env python3
"""
health_check.py — 知识库健康检查脚本 v3

检查项：
  基础：格式、断链、孤儿页、置信度
  v2：待审积压、Skill 覆盖率、候选追踪、Inbox 积压
  v3（新）：
    - [矛盾] callout 检测（未解决矛盾数）
    - 问题索引覆盖率（P-index）
    - hot.md 更新时间检测
    - 知识老化检测（Loop 4：90 天未更新的高置信度页面）
    - Skill 活跃度（Loop 2：30 天未更新的 Skill）

用法：
  python3 scripts/health_check.py [--root /path/to/wiki]
  python3 scripts/health_check.py --save   # 同时保存报告到 _meta/health-report.md
"""

import os
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import (
    get_wiki_root, ALL_PAGE_DIRS, CHECK_DIRS as WIKI_CHECK_DIRS,
    RAW, META_FILES, DIRS
)

# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────
PAGE_DIRS      = ALL_PAGE_DIRS
RAW_DIRS       = list(dict.fromkeys(RAW.values()))
REQUIRED_FIELDS = ["title", "created", "updated", "type", "tags"]
MAX_LINES      = 200
MIN_OUTLINKS   = 2
REVIEW_STALE_DAYS = 7
SKILL_STALE_DAYS  = 30   # Loop 2：Skill 超过此天数未更新视为不活跃
AGING_DAYS        = 90   # Loop 4：高置信度页面超过此天数视为老化


# ──────────────────────────────────────────────
# 基础工具
# ──────────────────────────────────────────────

def parse_fm(content: str) -> tuple[dict, str]:
    meta = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_raw = parts[1]
            body   = parts[2].lstrip("\n")
            for line in fm_raw.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
    return meta, body


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def extract_wikilinks(content: str) -> list[str]:
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    raw = re.findall(r'\[\[([^\]]+)\]\]', body)
    results = []
    for link in raw:
        target = link.split("|")[0].split("#")[0].strip()
        if target:
            results.append(target)
    return results


def find_pages(root: Path) -> dict[str, Path]:
    """构建全库页面索引 {stem: Path}。"""
    pages = {}
    all_dirs = PAGE_DIRS + [r for r in RAW_DIRS]
    for d in all_dirs:
        dp = root / d
        if dp.is_dir():
            for f in dp.glob("*.md"):
                if f.stem not in pages:
                    pages[f.stem] = f
    return pages


def scan_check_dirs(root: Path) -> dict[str, Path]:
    """扫描主要知识页目录，返回 {stem: Path}。"""
    page_index = {}
    for d in WIKI_CHECK_DIRS:
        dp = root / d
        if dp.is_dir():
            for f in dp.glob("*.md"):
                page_index[f.stem] = f
    return page_index


# ──────────────────────────────────────────────
# v3 新增检查函数
# ──────────────────────────────────────────────

def check_contradictions(root: Path) -> list[tuple[str, str]]:
    """
    检查未解决的矛盾标注（[!矛盾] 或 [!contradiction] callout）。
    返回 [(相对路径, 矛盾摘要)] 列表。
    """
    results = []
    pattern = re.compile(r'>\s*\[!(矛盾|contradiction)\](.{0,80})', re.IGNORECASE)
    for d in PAGE_DIRS:
        dp = root / d
        if not dp.is_dir():
            continue
        for f in dp.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                matches = pattern.findall(content)
                if matches:
                    summary = matches[0][1].strip()[:60]
                    rel = str(f.relative_to(root))
                    results.append((rel, summary))
            except Exception:
                pass
    return results


def check_p_index_coverage(root: Path, page_index: dict) -> tuple[int, int]:
    """
    检查问题索引覆盖率：有多少知识页在问题索引中有对应条目。
    返回 (有覆盖的页面数, 总页面数)。
    """
    p_index_dir = root / DIRS["问题索引"]
    if not p_index_dir.exists():
        return 0, len(page_index)

    # 收集问题索引中引用的所有页面
    referenced = set()
    for f in p_index_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            for link in extract_wikilinks(content):
                referenced.add(link)
        except Exception:
            pass

    covered = len(set(page_index.keys()) & referenced)
    return covered, len(page_index)


def check_hot_cache_freshness(root: Path) -> int:
    """
    检查 hot.md 的更新时间，返回距今天数。
    -1 表示 hot.md 不存在。
    """
    hot_path = root / META_FILES["hot"]
    if not hot_path.exists():
        return -1
    try:
        content = hot_path.read_text(encoding="utf-8")
        meta, _ = parse_fm(content)
        updated = meta.get("updated", "")
        if updated:
            d = parse_date(updated)
            if d:
                return (date.today() - d).days
    except Exception:
        pass
    # 用文件修改时间作为备用
    mtime = hot_path.stat().st_mtime
    mdate = date.fromtimestamp(mtime)
    return (date.today() - mdate).days


def check_aging_pages(root: Path, page_index: dict) -> list[tuple[str, int]]:
    """
    Loop 4：检测高置信度但超过 AGING_DAYS 天未更新的页面。
    返回 [(相对路径, 距今天数)]。
    """
    aging = []
    today = date.today()
    for stem, path in page_index.items():
        try:
            content = path.read_text(encoding="utf-8")
            meta, _ = parse_fm(content)
            confidence = meta.get("confidence", "").lower()
            if confidence not in ("high", "高置信度", "high-confidence"):
                continue
            updated_str = meta.get("updated", meta.get("created", ""))
            if not updated_str:
                continue
            d = parse_date(updated_str)
            if d and (today - d).days > AGING_DAYS:
                rel = str(path.relative_to(root))
                aging.append((rel, (today - d).days))
        except Exception:
            pass
    return sorted(aging, key=lambda x: -x[1])


def check_skill_activity(root: Path) -> tuple[list, list]:
    """
    Loop 2：统计技能活跃度，标记超过 SKILL_STALE_DAYS 天未更新的 Skill。
    返回 (不活跃列表, 活跃列表)，每项 (文件名, 天数)。
    """
    skills_dir = root / DIRS["技能"]
    if not skills_dir.is_dir():
        return [], []

    inactive = []
    active = []
    today = date.today()

    for f in skills_dir.glob("*.md"):
        if f.name.startswith("_"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            meta, _ = parse_fm(content)
            updated_str = meta.get("updated", meta.get("created", ""))
            if updated_str:
                d = parse_date(updated_str)
                if d:
                    days = (today - d).days
                    if days > SKILL_STALE_DAYS:
                        inactive.append((f.name, days))
                    else:
                        active.append((f.name, days))
        except Exception:
            pass

    return sorted(inactive, key=lambda x: -x[1]), active


# ──────────────────────────────────────────────
# v2 继承的检查函数（更新路径）
# ──────────────────────────────────────────────

def check_review_queue(root: Path) -> tuple[list, list]:
    review_dir = root / RAW["待审"]
    if not review_dir.is_dir():
        return [], []
    stale, pending = [], []
    today = date.today()
    for f in review_dir.glob("*.md"):
        try:
            meta, _ = parse_fm(f.read_text(encoding="utf-8"))
            status = meta.get("status", "review").lower()
            if status not in ("review", "researching"):
                continue
            updated_str = meta.get("updated", meta.get("created", ""))
            d = parse_date(updated_str) if updated_str else None
            days = (today - d).days if d else 0
            (stale if days > REVIEW_STALE_DAYS else pending).append((f.name, days))
        except Exception:
            pass
    return stale, pending


def check_skill_coverage(root: Path, page_index: dict) -> tuple[int, int, list]:
    skills_dir = root / DIRS["技能"]
    if not skills_dir.is_dir():
        return 0, 0, []
    skill_referenced = set()
    orphan_skills = []
    for f in skills_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            meta, _ = parse_fm(content)
            if meta.get("status", "").lower() != "approved":
                continue
            links = extract_wikilinks(content)
            if not links:
                orphan_skills.append(f.name)
            else:
                skill_referenced.update(links)
        except Exception:
            pass
    concept_entity = {
        stem for stem, path in page_index.items()
        if DIRS["概念"] in str(path).replace("\\", "/") or DIRS["实体"] in str(path).replace("\\", "/")
    }
    covered = len(concept_entity & skill_referenced)
    return covered, len(concept_entity), orphan_skills


def check_candidates(root: Path) -> tuple[list, list]:
    candidates_dir = root / DIRS["候选"]
    if not candidates_dir.is_dir():
        return [], []
    incubating, active = [], []
    for f in candidates_dir.glob("*.md"):
        try:
            meta, _ = parse_fm(f.read_text(encoding="utf-8"))
            status = meta.get("status", "incubating").lower()
            title = meta.get("title", f.stem)
            if status == "incubating":
                incubating.append((f.name, title))
            elif status == "active":
                active.append((f.name, title))
        except Exception:
            pass
    return incubating, active


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="知识库健康检查 v3")
    parser.add_argument("--root", "--wiki-root", help="wiki 根目录路径")
    parser.add_argument("--save", action="store_true", help="保存报告到 _meta/health-report.md")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)

    if not root.is_dir():
        print(f"错误: wiki 根目录不存在: {root}", file=sys.stderr)
        sys.exit(1)

    # ── 收集数据 ──
    all_pages    = find_pages(root)
    page_index   = scan_check_dirs(root)
    total_pages  = len(page_index)

    # 目录统计
    dir_stats = {}
    for d in PAGE_DIRS:
        dp = root / d
        dir_stats[d] = len(list(dp.glob("*.md"))) if dp.is_dir() else 0
    raw_stats = {}
    for key, rel in RAW.items():
        dp = root / rel
        raw_stats[key] = len(list(dp.glob("*.md"))) if dp.is_dir() else 0

    # 基础扫描
    broken_links = {}
    format_issues = {}
    oversized = {}
    low_outlink = {}
    total_links = 0

    for name, filepath in page_index.items():
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            continue
        links = extract_wikilinks(content)
        total_links += len(links)
        broken = sorted(set(l for l in links if l not in all_pages))
        if broken:
            broken_links[filepath] = broken
        issues = []
        if not content.startswith("---"):
            issues.append("缺少 frontmatter")
        else:
            end = content.find("\n---", 3)
            if end != -1:
                fm = content[3:end]
                for field in REQUIRED_FIELDS:
                    if not re.search(rf'^{field}\s*:', fm, re.MULTILINE):
                        issues.append(f"缺少: {field}")
        if issues:
            format_issues[filepath] = issues
        line_count = content.count("\n") + 1
        if line_count > MAX_LINES:
            oversized[filepath] = line_count
        if len(links) < MIN_OUTLINKS:
            low_outlink[filepath] = len(links)

    # 孤儿页
    linked_pages = set()
    for name, filepath in page_index.items():
        try:
            content = filepath.read_text(encoding="utf-8")
            for link in extract_wikilinks(content):
                linked_pages.add(link)
        except Exception:
            pass
    orphan_pages = sorted(set(page_index.keys()) - linked_pages)

    # v2 检查
    stale_reviews, pending_reviews = check_review_queue(root)
    skill_covered, skill_total, orphan_skills = check_skill_coverage(root, page_index)
    incubating_candidates, active_candidates = check_candidates(root)
    inbox_count = raw_stats.get("收件箱", 0)

    # v3 新增检查
    contradictions = check_contradictions(root)
    p_index_covered, p_index_total = check_p_index_coverage(root, page_index)
    hot_days = check_hot_cache_freshness(root)
    aging_pages = check_aging_pages(root, page_index)
    inactive_skills, active_skills = check_skill_activity(root)

    # ── 评分 ──
    score = 100.0
    total_broken = sum(len(v) for v in broken_links.values())
    if total_links > 0:
        score -= min(25, (total_broken / total_links) * 100)
    if total_pages > 0:
        score -= min(15, (len(format_issues) / total_pages) * 100)
        score -= min(10, (len(oversized)    / total_pages) * 100)
        score -= min(10, (len(orphan_pages) / total_pages) * 100)
    score -= min(10, len(stale_reviews) * 2)
    score -= min(10, len(contradictions) * 3)
    score -= min(10, len(aging_pages) * 1)
    score = max(0, round(score))

    # ── 构建报告 ──
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines += [
        "# 知识库健康检查报告 v3",
        "",
        f"## 检查时间",
        now,
        "",
    ]

    # 目录统计
    lines += ["## 📊 目录统计", ""]
    for d in PAGE_DIRS:
        lines.append(f"- {d}/：{dir_stats.get(d, 0)} 页")
    lines.append("")
    for key in ["收件箱", "待审", "已归档"]:
        lines.append(f"- {RAW[key]}/：{raw_stats.get(key, 0)} 条")
    lines.append(f"- **总知识页数：{total_pages}**")
    lines.append("")

    # ── v3：热缓存状态 ──
    if hot_days < 0:
        hot_icon, hot_msg = "🔴", "hot.md 不存在 → 运行 `wiki.sh cache` 生成"
    elif hot_days == 0:
        hot_icon, hot_msg = "✅", "今天已更新"
    elif hot_days <= 3:
        hot_icon, hot_msg = "🟡", f"{hot_days} 天前更新"
    else:
        hot_icon, hot_msg = "🔴", f"{hot_days} 天前更新，建议更新 → `wiki.sh cache`"
    lines += [f"## 🌡️ 热缓存（hot.md）", f"- {hot_icon} {hot_msg}", ""]

    # Inbox 积压
    inbox_icon = "✅" if inbox_count == 0 else ("⚠️" if inbox_count < 5 else "🔴")
    lines += [
        "## 📥 收件箱积压",
        f"- {inbox_icon} {RAW['收件箱']}/：**{inbox_count} 篇**待加工",
    ]
    if inbox_count > 0:
        lines.append(f"  → 告诉 AI「加工 {RAW['收件箱']}/文件名.md」")
    lines.append("")

    # 审阅队列
    review_total = len(stale_reviews) + len(pending_reviews)
    lines += ["## ⏳ 审阅队列"]
    lines.append(f"- 待审总数：{review_total} 篇")
    if stale_reviews:
        lines.append(f"- 🔴 积压（>{REVIEW_STALE_DAYS}天）：{len(stale_reviews)} 篇")
        for fname, days in sorted(stale_reviews, key=lambda x: -x[1])[:10]:
            lines.append(f"  - `{RAW['待审']}/{fname}`（{days} 天）")
    if pending_reviews:
        lines.append(f"- 🟡 正常待审：{len(pending_reviews)} 篇")
    if review_total == 0:
        lines.append("- ✅ 审阅队列为空")
    lines.append("")

    # ── v3：矛盾检测 ──
    contra_icon = "✅" if not contradictions else ("🟡" if len(contradictions) <= 3 else "🔴")
    lines += ["## ⚡ 未解决矛盾（[!矛盾] callout）"]
    lines.append(f"- {contra_icon} 发现 {len(contradictions)} 处未解决矛盾")
    if contradictions:
        for rel, summary in contradictions[:10]:
            lines.append(f"  - `{rel}`: {summary}")
        if len(contradictions) > 10:
            lines.append(f"  - ... 还有 {len(contradictions) - 10} 处")
    lines.append("")

    # ── v3：问题索引覆盖率 ──
    lines += ["## 🔍 问题索引覆盖率（P-index）"]
    if p_index_total == 0:
        lines.append("- ⚪ N/A：暂无知识页，问题索引覆盖率暂不可计算")
    else:
        p_pct = p_index_covered * 100 // p_index_total
        p_icon = "✅" if p_pct >= 30 else ("🟡" if p_pct >= 10 else "🔴")
        lines.append(f"- {p_icon} {p_index_covered}/{p_index_total} 知识页有对应问题索引（{p_pct}%）")
        if p_pct < 10:
            lines.append(f"  → 加工文章后记得提炼 2-3 个问题，写入 {DIRS['问题索引']}/ 目录")
    lines.append("")

    # ── Loop 2：Skill 活跃度 ──
    lines += ["## 🎯 Skill 活跃度（Loop 2）"]
    lines.append(f"- Skill 总数：{dir_stats.get(DIRS['技能'], 0)} 个")
    lines.append(f"- 活跃（{SKILL_STALE_DAYS}天内更新）：{len(active_skills)} 个")
    if inactive_skills:
        lines.append(f"- 🔴 不活跃（>{SKILL_STALE_DAYS}天未更新）：{len(inactive_skills)} 个")
        for fname, days in inactive_skills[:5]:
            lines.append(f"  - `{DIRS['技能']}/{fname}`（{days} 天）")
        lines.append("  → 考虑用新知识更新这些 Skill，或标记为已归档")
    if skill_covered > 0:
        skill_pct = skill_covered * 100 // max(1, skill_total)
        lines.append(f"- 知识覆盖：{skill_covered}/{skill_total}（{skill_pct}%）概念页被 Skill 引用")
    if orphan_skills:
        lines.append(f"- ⚠️ 孤立 Skill（无引用）：{len(orphan_skills)} 个")
    lines.append("")

    # ── Loop 4：知识老化 ──
    lines += ["## 🕰️ 知识老化检测（Loop 4）"]
    lines.append(f"- 检查标准：高置信度页面 > {AGING_DAYS} 天未更新")
    if aging_pages:
        lines.append(f"- 🔴 老化页面：{len(aging_pages)} 个")
        for rel, days in aging_pages[:10]:
            lines.append(f"  - `{rel}`（{days} 天未更新）")
        lines.append("  → 复查后更新内容，或降低置信度为 medium")
    else:
        lines.append("- ✅ 无老化页面")
    lines.append("")

    # 候选项目
    lines += ["## 💡 候选项目追踪"]
    lines.append(f"- 孵化中：{len(incubating_candidates)} 个 | 进行中：{len(active_candidates)} 个")
    if incubating_candidates:
        for fname, title in incubating_candidates[:10]:
            lines.append(f"  - [[{DIRS['候选']}/{fname[:-3]}]] — {title}")
    lines.append("")

    # 链接状态
    lines += ["## 🔗 链接状态"]
    lines.append(f"- 总链接数：{total_links}")
    lines.append(f"- 断链数：{total_broken}")
    if broken_links:
        shown = 0
        for fp, links in sorted(broken_links.items()):
            rel = str(fp.relative_to(root))
            for link in links:
                if shown >= 30:
                    break
                lines.append(f"  - `{rel}` → [[{link}]]")
                shown += 1
            if shown >= 30:
                lines.append(f"  - ... 还有 {total_broken - shown} 个断链")
                break
    lines.append("")

    # 格式检查
    lines += ["## 📋 格式检查"]
    correct = total_pages - len(format_issues)
    lines.append(f"- 格式正确：{correct}/{total_pages}（{correct*100//max(1,total_pages)}%）")
    if format_issues:
        for fp, issues in list(format_issues.items())[:20]:
            lines.append(f"  - `{str(fp.relative_to(root))}`：{', '.join(issues)}")
    lines.append("")

    # 孤儿页
    lines += ["## 👻 孤儿页（无入站链接）"]
    lines.append(f"- 孤儿页数：{len(orphan_pages)}")
    if orphan_pages:
        for p in orphan_pages[:20]:
            lines.append(f"  - `{str(page_index[p].relative_to(root))}`")
    lines.append("")

    # 置信度分布
    lines += ["## 🔬 置信度分布"]
    conf_counts = {"high": 0, "medium": 0, "low": 0, "quarantine": 0}
    sourced = 0
    for name, filepath in page_index.items():
        try:
            content = filepath.read_text(encoding="utf-8")
            meta, _ = parse_fm(content)
            conf = meta.get("confidence", "").lower()
            if conf in conf_counts:
                conf_counts[conf] += 1
            if meta.get("sources", ""):
                sourced += 1
        except Exception:
            pass
    sourced_pct = sourced * 100 // max(1, total_pages)
    lines.append(f"- 来源覆盖：{sourced}/{total_pages}（{sourced_pct}%）")
    lines.append(f"- 🟢 高置信度：{conf_counts['high']} | 🟡 中：{conf_counts['medium']}")
    lines.append(f"- 🟠 低：{conf_counts['low']} | 🔴 隔离：{conf_counts['quarantine']}")
    lines.append("")

    # 总评
    if total_pages == 0:
        score_text = "N/A"
        status = "⚪ 未初始化"
    else:
        score_text = f"{score}%"
        status = "🟢 状态良好" if score >= 80 else ("🟡 需关注" if score >= 60 else "🔴 需重点维护")
    lines += [
        "## 📊 总体评估",
        f"**健康度：{score_text}**  {status}",
        "",
        "### 建议行动",
    ]
    if total_pages == 0:
        lines.append(f"1. ⚪ 知识库暂无知识页；先加工 {RAW['收件箱']}/ 中的文章或创建初始页面")
    if contradictions:
        lines.append(f"1. 🔴 解决 {len(contradictions)} 处矛盾（在相关页面查看 [!矛盾] callout）")
    if len(stale_reviews) > 0:
        lines.append(f"2. ⏳ 处理 {len(stale_reviews)} 篇积压待审稿（在 Obsidian 中审阅）")
    if inbox_count > 3:
        lines.append(f"3. 📥 加工 {inbox_count} 篇收件箱文章（告诉 Minis 逐一加工）")
    if aging_pages:
        lines.append(f"4. 🕰️ 复查 {len(aging_pages)} 个老化知识页")
    if hot_days > 3:
        lines.append(f"5. 🌡️ 更新热缓存（运行 `wiki.sh cache`）")
    if total_pages > 0 and not contradictions and not stale_reviews and inbox_count <= 3:
        lines.append("✅ 知识库状态良好，继续保持！")
    lines.append("")

    report = "\n".join(lines)
    print(report)

    if args.save:
        meta_dir = root / "_meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        report_path = meta_dir / "health-report.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"\n✅ 报告已保存至：_meta/health-report.md", file=sys.stderr)


if __name__ == "__main__":
    main()

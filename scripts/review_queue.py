#!/usr/bin/env python3
"""
review_queue.py — 审阅队列处理器 v3

扫描 raw/待审/ 中的待审稿：
  - status: approved → 将知识页写入 实体/概念/等，归档到 raw/已归档/
  - status: rejected → 读取退回原因，重新生成待审稿（status 重置为 review）

v3 新增：
  - 中文目录路径（实体/ 概念/ 对比/ 技能/ 候选/）
  - 归档后更新 _meta/manifest.json 追踪记录

用法：
  python3 scripts/review_queue.py [--wiki-root /path/to/wiki]
  python3 scripts/review_queue.py --dry-run   # 仅显示，不执行
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import get_wiki_root, RAW, DIRS

# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def find_wiki_root() -> Path:
    """按优先级查找 wiki 根目录。"""
    return get_wiki_root()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (meta_dict, body)。"""
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_raw = parts[1].strip()
            body = parts[2].lstrip("\n")
            for line in fm_raw.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
    return meta, body


def render_frontmatter(meta: dict) -> str:
    """将 meta dict 渲染回 YAML frontmatter 字符串。"""
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def get_rejection_reason(body: str) -> str:
    """从正文底部提取退回原因（## 退回原因 块）。"""
    m = re.search(r"##\s*退回原因\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
    return m.group(1).strip() if m else ""


def strip_rejection_block(body: str) -> str:
    """移除正文底部的退回原因块。"""
    return re.sub(r"\n## 退回原因.*", "", body, flags=re.DOTALL).rstrip()


def append_log(wiki_root: Path, entry: str) -> None:
    """追加一条记录到 log.md（新条目插入顶部）。"""
    log_path = wiki_root / "log.md"
    today = date.today().isoformat()
    block = f"## [{today}] {entry}\n"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        # 找到第一个 ## 之前插入（最新在最前）
        first_h2 = existing.find("\n## [")
        if first_h2 >= 0:
            content = existing[:first_h2 + 1] + block + "\n" + existing[first_h2 + 1:]
        else:
            content = existing.rstrip() + "\n\n" + block
    else:
        content = f"# 操作日志\n\n{block}"
    log_path.write_text(content, encoding="utf-8")


def update_index(wiki_root: Path, page_type: str, page_name: str, summary: str) -> None:
    """在 index.md 对应分类下添加条目。"""
    index_path = wiki_root / "index.md"
    if not index_path.exists():
        return

    type_map = {
        "entity":     "实体",
        "concept":    "概念",
        "comparison": "对比",
        "skill":      "技能",
        "candidate":  "候选",
        "synthesis":  "合成",
        "query":      "查询",
    }
    section = type_map.get(page_type, page_type)
    entry_line = f"- [[{page_name}]] — {summary}\n"

    content = index_path.read_text(encoding="utf-8")
    section_header = f"## {section}"
    if section_header in content:
        insert_pos = content.index(section_header) + len(section_header)
        nl_pos = content.index("\n", insert_pos)
        content = content[: nl_pos + 1] + entry_line + content[nl_pos + 1 :]
    else:
        content += f"\n{section_header}\n{entry_line}"

    index_path.write_text(content, encoding="utf-8")


def update_manifest(wiki_root: Path, page_path: Path, source_path: str | None) -> None:
    """更新 _meta/manifest.json，记录页面归档事件。"""
    manifest_path = wiki_root / "_meta" / "manifest.json"
    try:
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            data = {"sources": {}, "address_map": {}}
        rel_page = str(page_path.relative_to(wiki_root))
        data.setdefault("sources", {})
        data["sources"][source_path or rel_page] = {
            "approved_at": date.today().isoformat(),
            "wiki_page": rel_page,
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️  manifest 更新失败: {e}")


# ──────────────────────────────────────────────
# 核心处理逻辑
# ──────────────────────────────────────────────

def process_approved(review_file: Path, wiki_root: Path, dry_run: bool) -> str:
    """
    处理 status: approved 的文件：
    1. 根据 type 字段确定目标目录
    2. 将 status 改为 approved（已经是了，确认写入）
    3. 移动到 实体/概念/技能/候选/
    4. 将原 review 文件归档到 raw/已归档/
    5. 将关联的 raw/收件箱 文件也移到 raw/已归档/（如果 frontmatter 里有 inbox_source）
    6. 更新 index.md
    """
    text = review_file.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    page_type = meta.get("type", "concept").lower()
    title = meta.get("title", review_file.stem)
    page_name = review_file.stem  # 保留文件名（已是小写连字符格式）

    type_dir_map = {
        "entity":     "实体",
        "concept":    "概念",
        "comparison": "对比",
        "skill":      "技能",
        "candidate":  "候选",
        "synthesis":  "合成",
        "query":      "查询",
    }
    target_dir = wiki_root / type_dir_map.get(page_type, "概念")

    # 如果是 skill，从 技能/待审/ 移到 技能/
    if page_type == "skill" and "待审" in str(review_file):
        target_dir = wiki_root / "技能"

    target_file = target_dir / review_file.name
    processed_dir = wiki_root / RAW["已归档"]

    summary = body.split("\n")[0].lstrip("#").strip()[:60] if body else title

    print(f"  ✅ APPROVED: {review_file.name}")
    print(f"     → {target_dir.name}/{review_file.name}")

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        # 写知识页（status 已经是 approved）
        target_file.write_text(text, encoding="utf-8")

        # 归档 review 文件
        archived_review = processed_dir / f"_review_{review_file.name}"
        shutil.move(str(review_file), str(archived_review))

        # 归档关联 inbox 文件
        inbox_source = meta.get("inbox_source", "").strip()
        if inbox_source:
            inbox_file = wiki_root / inbox_source
            if inbox_file.exists():
                shutil.move(str(inbox_file), str(processed_dir / inbox_file.name))
                print(f"     → 已归档原文: {inbox_file.name}")

        # 更新 index.md
        update_index(wiki_root, page_type, page_name, summary)

        # 更新 manifest.json
        update_manifest(wiki_root, target_file, inbox_source)

    return f"通过待审稿: [[{page_name}]]（{page_type}）"


def process_rejected(review_file: Path, wiki_root: Path, dry_run: bool) -> str:
    """
    处理 status: rejected 的文件：
    1. 提取退回原因
    2. 在文件末尾标记「待重新生成」
    3. 重置 status 为 review（等待 AI 重新处理）
    4. 打印退回原因，提示用户或 AI 重新加工
    """
    text = review_file.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    rejection_reason = get_rejection_reason(body)
    clean_body = strip_rejection_block(body)

    print(f"  🔄 REJECTED: {review_file.name}")
    if rejection_reason:
        print(f"     退回原因: {rejection_reason[:100]}")
    else:
        print(f"     ⚠️  未找到退回原因（请在文件底部添加 ## 退回原因 块）")

    # 重置 status
    meta["status"] = "review"
    meta["updated"] = date.today().isoformat()

    # 添加重新生成提示
    regen_hint = (
        f"\n\n<!-- 待重新生成\n退回原因：{rejection_reason}\n请根据以上原因重新加工，然后将 status 改回 approved。\n-->"
        if rejection_reason
        else "\n\n<!-- 待重新生成：请根据退回原因重新加工 -->"
    )
    new_text = render_frontmatter(meta) + "\n\n" + clean_body + regen_hint

    if not dry_run:
        review_file.write_text(new_text, encoding="utf-8")

    return f"退回重生成: {review_file.name}（原因: {rejection_reason[:40] if rejection_reason else '未填写'}）"


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="处理审阅队列")
    parser.add_argument("--wiki-root", help="wiki 根目录路径（默认自动检测）")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不执行")
    parser.add_argument("--skill-review", action="store_true", help="同时扫描 技能/待审/")
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root) if args.wiki_root else find_wiki_root()
    review_dir = wiki_root / RAW["待审"]
    skill_review_dir = wiki_root / "技能" / "待审"

    if not review_dir.exists():
        print(f"⚠️  raw/待审/ 目录不存在，创建中...")
        if not args.dry_run:
            review_dir.mkdir(parents=True, exist_ok=True)

    scan_dirs = [review_dir]
    if args.skill_review and skill_review_dir.exists():
        scan_dirs.append(skill_review_dir)

    approved_count = 0
    rejected_count = 0
    skipped_count = 0
    log_entries = []

    for scan_dir in scan_dirs:
        md_files = list(scan_dir.glob("*.md"))
        if not md_files:
            print(f"📭 {scan_dir.relative_to(wiki_root)}: 无待审文件")
            continue

        print(f"\n📋 扫描 {scan_dir.relative_to(wiki_root)}: {len(md_files)} 个文件")

        for md_file in sorted(md_files):
            text = md_file.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(text)
            status = meta.get("status", "").lower()

            if status == "approved":
                entry = process_approved(md_file, wiki_root, args.dry_run)
                log_entries.append(entry)
                approved_count += 1

            elif status == "rejected":
                entry = process_rejected(md_file, wiki_root, args.dry_run)
                log_entries.append(entry)
                rejected_count += 1

            else:
                skipped_count += 1
                if status == "review":
                    # 检查是否超过 7 天未审阅
                    updated = meta.get("updated", meta.get("created", ""))
                    if updated:
                        try:
                            updated_date = datetime.strptime(updated, "%Y-%m-%d").date()
                            days_pending = (date.today() - updated_date).days
                            if days_pending > 7:
                                print(f"  ⏳ PENDING ({days_pending}d): {md_file.name}")
                        except ValueError:
                            pass

    # 写日志
    if log_entries and not args.dry_run:
        summary = f"审阅队列处理：通过 {approved_count} 篇，退回重生成 {rejected_count} 篇"
        for entry in log_entries:
            summary += f"\n- {entry}"
        append_log(wiki_root, summary)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}完成：")
    print(f"  ✅ 通过: {approved_count}")
    print(f"  🔄 退回重生成: {rejected_count}")
    print(f"  ⏭  跳过（待审/其他）: {skipped_count}")

    if rejected_count > 0:
        print(f"\n💡 {rejected_count} 篇已标记为待重新生成。")
        print(f"   请告诉 Minis：「处理退回的待审稿」，Minis 会根据退回原因重新加工。")


if __name__ == "__main__":
    main()

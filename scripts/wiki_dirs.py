"""
compile-knowledge directory configuration.

All scripts should import paths from this module instead of hardcoding vault
directories. Legacy paths are still accepted as input and normalized to the
current 0-7 Knowledge Compiler layout.
"""

from __future__ import annotations

import os
from pathlib import Path


_WIKI_ROOT_CANDIDATES = [
    "/var/minis/mounts/wiki",
    os.path.expanduser("~/wiki"),
    os.getcwd(),
]


def get_wiki_root(override: str | None = None) -> Path:
    """Detect the wiki root unless an explicit override is provided."""
    if override:
        return Path(override)
    env = os.environ.get("WIKI_ROOT")
    if env:
        return Path(env)
    for candidate in _WIKI_ROOT_CANDIDATES:
        path = Path(candidate)
        if path.is_dir() and ((path / "log.md").exists() or (path / "SCHEMA.md").exists()):
            return path
    return Path.cwd()


# ──────────────────────────────────────────────
# 0-7 Knowledge Compiler layout
# ──────────────────────────────────────────────

INBOX_PENDING = "0 - Inbox/待处理"
INBOX_REVIEW = "0 - Inbox/待审"

RESOURCES_ROOT = "1 - Resources（资源）"
RESOURCE_ENTITY = f"{RESOURCES_ROOT}/实体"
RESOURCE_CONCEPT = f"{RESOURCES_ROOT}/概念"
RESOURCE_COMPARISON = f"{RESOURCES_ROOT}/对比"
RESOURCE_QUERY = f"{RESOURCES_ROOT}/查询"
RESOURCE_P_INDEX = f"{RESOURCES_ROOT}/问题索引"

AREA_INVESTMENT = "2 - Areas（领域）/投资体系"
AREA_AI_AUTOMATION = "2 - Areas（领域）/AI与自动化"
AREA_HONG_KONG = "2 - Areas（领域）/香港行动"
AREA_KB_OPS = "2 - Areas（领域）/知识库运营"
AREA_UNCLASSIFIED_SYNTHESIS = f"{AREA_KB_OPS}/待分类合成"

PROJECT_CANDIDATES = "3 - Projects（项目）/候选"
PROJECT_ACTIVE = "3 - Projects（项目）/活跃项目"
PROJECT_PAUSED = "3 - Projects（项目）/已暂停"

SKILLS_ROOT = "4 - Skills（技能）"
SKILL_REVIEW = f"{SKILLS_ROOT}/待审"

ARCHIVE_SOURCES = "5 - Archives（归档）/已归档来源"
ARCHIVE_FINISHED_PROJECTS = "5 - Archives（归档）/已结束项目"
ARCHIVE_STALE_KNOWLEDGE = "5 - Archives（归档）/过时知识"
ARCHIVE_BACKUPS = "5 - Archives（归档）/系统备份"

TEMPLATES_DIR = "6 - Templates（模板）"
DAILY_DIR = "7 - Daily（日记）"


DIRS = {
    "实体": RESOURCE_ENTITY,
    "概念": RESOURCE_CONCEPT,
    "对比": RESOURCE_COMPARISON,
    "合成": AREA_UNCLASSIFIED_SYNTHESIS,
    "查询": RESOURCE_QUERY,
    "问题索引": RESOURCE_P_INDEX,
    "技能": SKILLS_ROOT,
    "技能待审": SKILL_REVIEW,
    "候选": PROJECT_CANDIDATES,
    "活跃项目": PROJECT_ACTIVE,
    "已暂停项目": PROJECT_PAUSED,
    "日记": DAILY_DIR,
    "投资体系": AREA_INVESTMENT,
    "AI与自动化": AREA_AI_AUTOMATION,
    "香港行动": AREA_HONG_KONG,
    "知识库运营": AREA_KB_OPS,
}


RAW = {
    "收件箱": INBOX_PENDING,
    "待处理": INBOX_PENDING,
    "待审": INBOX_REVIEW,
    "已归档": ARCHIVE_SOURCES,
    "论文": INBOX_PENDING,
    "笔记": INBOX_PENDING,
    "资产": INBOX_PENDING,
}


META_DIR = "_meta"

META_FILES = {
    "hot": "_meta/hot.md",
    "manifest": "_meta/manifest.json",
    "agenda": "_meta/research-agenda.md",
    "health": "_meta/health-report.md",
    "graph": "_meta/graph.html",
}


EXTRA_DIRS = [
    PROJECT_CANDIDATES,
    PROJECT_ACTIVE,
    PROJECT_PAUSED,
    AREA_INVESTMENT,
    AREA_AI_AUTOMATION,
    AREA_HONG_KONG,
    AREA_KB_OPS,
    AREA_UNCLASSIFIED_SYNTHESIS,
    SKILLS_ROOT,
    SKILL_REVIEW,
    ARCHIVE_SOURCES,
    ARCHIVE_FINISHED_PROJECTS,
    ARCHIVE_STALE_KNOWLEDGE,
    f"{ARCHIVE_BACKUPS}/review-backups",
    TEMPLATES_DIR,
    DAILY_DIR,
]


LEGACY_MANUAL_MAP = {
    "合成/投资策略手册.md": f"{AREA_INVESTMENT}/投资策略手册.md",
    "合成/Codex操作手册.md": f"{AREA_AI_AUTOMATION}/Codex操作手册.md",
    "合成/香港行动指南.md": f"{AREA_HONG_KONG}/香港行动指南.md",
}


LEGACY_MAP = {
    # English v1/v2 paths.
    "entities": RESOURCE_ENTITY,
    "concepts": RESOURCE_CONCEPT,
    "comparisons": RESOURCE_COMPARISON,
    "synthesis": AREA_UNCLASSIFIED_SYNTHESIS,
    "queries": RESOURCE_QUERY,
    "skills/review": SKILL_REVIEW,
    "skills": SKILLS_ROOT,
    "candidates": PROJECT_CANDIDATES,
    "raw/inbox": INBOX_PENDING,
    "raw/articles": INBOX_PENDING,
    "raw/review": INBOX_REVIEW,
    "raw/processed": ARCHIVE_SOURCES,
    "raw/papers": INBOX_PENDING,
    "raw/transcripts": INBOX_PENDING,
    "raw/assets": INBOX_PENDING,

    # Old raw/Chinese source paths.
    "raw/收件箱": INBOX_PENDING,
    "raw/论文": INBOX_PENDING,
    "raw/笔记": INBOX_PENDING,
    "raw/资产": INBOX_PENDING,
    "raw/待审": INBOX_REVIEW,
    "raw/已归档": ARCHIVE_SOURCES,

    # Old Chinese top-level paths.
    "实体": RESOURCE_ENTITY,
    "概念": RESOURCE_CONCEPT,
    "对比": RESOURCE_COMPARISON,
    "查询": RESOURCE_QUERY,
    "问题索引": RESOURCE_P_INDEX,
    "技能/待审": SKILL_REVIEW,
    "技能": SKILLS_ROOT,
    "候选": PROJECT_CANDIDATES,
    "日记": DAILY_DIR,
    "_archive": ARCHIVE_BACKUPS,

    # Previous 0-6 compile-knowledge layout.
    "3 - Resources（资源）/实体": RESOURCE_ENTITY,
    "3 - Resources（资源）/概念": RESOURCE_CONCEPT,
    "3 - Resources（资源）/对比": RESOURCE_COMPARISON,
    "3 - Resources（资源）/查询": RESOURCE_QUERY,
    "3 - Resources（资源）/问题索引": RESOURCE_P_INDEX,
    "3 - Resources（资源）/技能/待审": SKILL_REVIEW,
    "3 - Resources（资源）/技能": SKILLS_ROOT,
    "3 - Resources（资源）": RESOURCES_ROOT,
    "1 - Projects（项目）/候选": PROJECT_CANDIDATES,
    "1 - Projects（项目）/活跃项目": PROJECT_ACTIVE,
    "1 - Projects（项目）/已暂停": PROJECT_PAUSED,
    "1 - Projects（项目）": "3 - Projects（项目）",
    "4 - Archives（归档）/已归档来源": ARCHIVE_SOURCES,
    "4 - Archives（归档）/已结束项目": ARCHIVE_FINISHED_PROJECTS,
    "4 - Archives（归档）/过时知识": ARCHIVE_STALE_KNOWLEDGE,
    "4 - Archives（归档）/系统备份": ARCHIVE_BACKUPS,
    "4 - Archives（归档）": "5 - Archives（归档）",
    "5 - Templates（模板）": TEMPLATES_DIR,
    "6 - Daily（日记）": DAILY_DIR,

    **LEGACY_MANUAL_MAP,
}


CHECK_DIRS = [
    RESOURCE_ENTITY,
    RESOURCE_CONCEPT,
    RESOURCE_COMPARISON,
    RESOURCE_QUERY,
]

ALL_PAGE_DIRS = [
    RESOURCE_ENTITY,
    RESOURCE_CONCEPT,
    RESOURCE_COMPARISON,
    RESOURCE_QUERY,
    RESOURCE_P_INDEX,
    SKILLS_ROOT,
    PROJECT_CANDIDATES,
    PROJECT_ACTIVE,
    PROJECT_PAUSED,
    AREA_INVESTMENT,
    AREA_AI_AUTOMATION,
    AREA_HONG_KONG,
    AREA_KB_OPS,
    AREA_UNCLASSIFIED_SYNTHESIS,
]

ALL_RAW_DIRS = ["待处理", "待审", "已归档"]


def _clean_rel(value: str | Path) -> str:
    return str(value).replace("\\", "/").lstrip("/").strip()


def normalize_rel_path(value: str | Path) -> str:
    """Normalize a vault-relative path, including legacy directory prefixes."""
    rel = _clean_rel(value)
    if rel in LEGACY_MANUAL_MAP:
        return LEGACY_MANUAL_MAP[rel]
    if rel.startswith("合成/"):
        return f"{AREA_UNCLASSIFIED_SYNTHESIS}/{rel[len('合成/'):]}"
    for old, new in sorted(LEGACY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if rel == old:
            return new
        if rel.startswith(old + "/"):
            return new + rel[len(old) :]
    return rel


def resolve_vault_path(root: Path, value: str | Path) -> Path:
    """Resolve an absolute path or vault-relative path with legacy mapping."""
    path = Path(value)
    if path.is_absolute():
        return path
    direct = root / _clean_rel(value)
    if direct.exists():
        return direct
    return root / normalize_rel_path(value)


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def get_dir(root: Path, key: str) -> Path:
    """Return a standard knowledge directory by DIRS key."""
    return root / DIRS[key]


def get_raw(root: Path, key: str) -> Path:
    """Return a standard source/review/archive directory by RAW key."""
    return root / RAW[key]


def get_meta(root: Path, key: str) -> Path:
    """Return a metadata file path by META_FILES key."""
    return root / META_FILES[key]


def all_managed_dirs() -> list[str]:
    """Return unique directories managed by initialization."""
    ordered = [*RAW.values(), *DIRS.values(), *EXTRA_DIRS, META_DIR]
    seen: set[str] = set()
    result: list[str] = []
    for rel in ordered:
        if rel not in seen:
            seen.add(rel)
            result.append(rel)
    return result


def ensure_dirs(root: Path) -> None:
    """Ensure all required 0-7 layout directories exist."""
    for rel in all_managed_dirs():
        (root / rel).mkdir(parents=True, exist_ok=True)

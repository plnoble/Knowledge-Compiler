"""
wiki_dirs.py — wiki-kb v3 目录配置中心（全中文）

所有脚本通过 import wiki_dirs 获取标准路径，避免硬编码散落各处。

使用方式：
    from wiki_dirs import get_wiki_root, DIRS, RAW

    root = get_wiki_root()
    inbox = root / RAW["收件箱"]
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Wiki 根目录检测
# ──────────────────────────────────────────────

_WIKI_ROOT_CANDIDATES = [
    "/var/minis/mounts/wiki",      # Minis iOS 挂载点
    os.path.expanduser("~/wiki"),  # 本地 ~/wiki
    os.getcwd(),                   # 当前工作目录（脚本调试时）
]

def get_wiki_root(override: str | None = None) -> Path:
    """按优先级检测 wiki 根目录。"""
    if override:
        return Path(override)
    env = os.environ.get("WIKI_ROOT")
    if env:
        return Path(env)
    for c in _WIKI_ROOT_CANDIDATES:
        p = Path(c)
        if p.is_dir() and ((p / "log.md").exists() or (p / "SCHEMA.md").exists()):
            return p
    return Path.cwd()

# ──────────────────────────────────────────────
# 知识页目录（顶级，AI 维护）
# ──────────────────────────────────────────────

DIRS = {
    "实体":     "实体",       # 人物、机构、产品
    "概念":     "概念",       # 思想、框架、模型
    "对比":     "对比",       # 并排分析
    "合成":     "合成",       # AI 综合结论
    "查询":     "查询",       # 问答记录
    "问题索引": "问题索引",   # P-index：按问题检索入口
    "技能":     "技能",       # 可复用判断框架
    "技能待审": "技能/待审",  # Skill 草稿待审
    "候选":     "候选",       # 孵化中的项目想法
    "日记":     "日记",       # 日记（用户自由写）
}

# ──────────────────────────────────────────────
# raw/ 子目录（原始来源，只读区）
# ──────────────────────────────────────────────

RAW = {
    "收件箱": "raw/收件箱",   # Web Clipper 剪藏落地处（待加工）
    "待审":   "raw/待审",     # AI 生成的待审草稿
    "已归档": "raw/已归档",   # 审阅通过后归档
    "论文":   "raw/论文",
    "笔记":   "raw/笔记",
    "资产":   "raw/资产",
}

# ──────────────────────────────────────────────
# _meta/ 核心文件
# ──────────────────────────────────────────────

META_DIR = "_meta"

META_FILES = {
    "hot":     "_meta/hot.md",              # 热缓存（~500 字，每次会话更新）
    "manifest":"_meta/manifest.json",       # 摄入 Delta 追踪（哈希去重）
    "agenda":  "_meta/research-agenda.md", # 研究议程（Loop 3）
    "health":  "_meta/health-report.md",   # 最新健康检查报告
    "graph":   "_meta/graph.html",         # 知识图谱
}

# ──────────────────────────────────────────────
# 历史兼容映射（英文旧路径 → 中文新路径）
# 用于迁移工具，普通脚本不需要
# ──────────────────────────────────────────────

LEGACY_MAP = {
    "entities":          "实体",
    "concepts":          "概念",
    "comparisons":       "对比",
    "synthesis":         "合成",
    "queries":           "查询",
    "skills":            "技能",
    "skills/review":     "技能/待审",
    "candidates":        "候选",
    "raw/inbox":         "raw/收件箱",
    "raw/articles":      "raw/收件箱",
    "raw/review":        "raw/待审",
    "raw/processed":     "raw/已归档",
    "raw/papers":        "raw/论文",
    "raw/transcripts":   "raw/笔记",
    "raw/assets":        "raw/资产",
}

# ──────────────────────────────────────────────
# 健康检查用的扫描列表
# ──────────────────────────────────────────────

# 需要检查格式/链接/大小的知识页目录
CHECK_DIRS = ["实体", "概念", "对比", "合成", "查询"]

# 所有知识页目录（用于建立完整页面索引）
ALL_PAGE_DIRS = ["实体", "概念", "对比", "合成", "查询", "技能", "候选"]

# raw/ 子目录列表（用于统计）
ALL_RAW_DIRS = ["收件箱", "待审", "已归档", "论文", "笔记", "资产"]

# ──────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────

def get_dir(root: Path, key: str) -> Path:
    """获取知识页目录路径。key 是 DIRS 的键。"""
    return root / DIRS[key]

def get_raw(root: Path, key: str) -> Path:
    """获取 raw/ 子目录路径。key 是 RAW 的键。"""
    return root / RAW[key]

def get_meta(root: Path, key: str) -> Path:
    """获取 _meta/ 文件路径。key 是 META_FILES 的键。"""
    return root / META_FILES[key]

def ensure_dirs(root: Path) -> None:
    """确保所有必要目录存在（首次初始化时调用）。"""
    for rel in DIRS.values():
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel in RAW.values():
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / META_DIR).mkdir(parents=True, exist_ok=True)

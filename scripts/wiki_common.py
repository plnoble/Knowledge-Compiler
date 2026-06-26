"""Shared helpers for wiki-kb maintenance scripts."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].lstrip("\n")
            for line in parts[1].splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip()] = value.strip()
    return meta, body


def strip_frontmatter(content: str) -> str:
    return parse_frontmatter(content)[1]


def render_frontmatter(meta: dict[str, str], body: str) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


def ensure_frontmatter(content: str, defaults: dict[str, str]) -> tuple[str, bool]:
    meta, body = parse_frontmatter(content)
    changed = False
    if not meta:
        meta = dict(defaults)
        changed = True
    else:
        for key, value in defaults.items():
            if not meta.get(key):
                meta[key] = value
                changed = True
    if not changed:
        return content, False
    return render_frontmatter(meta, body), True


def extract_wikilinks(content: str) -> list[str]:
    body = strip_frontmatter(content)
    links = []
    for raw in re.findall(r"\[\[([^\]]+)\]\]", body):
        target = raw.split("|")[0].split("#")[0].strip()
        if target:
            links.append(target)
    return links


def page_title(path: Path, meta: dict[str, str] | None = None) -> str:
    if meta and meta.get("title"):
        return meta["title"].strip('"')
    return path.stem


def markdown_files(root: Path, dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in dirs:
        directory = root / rel
        if directory.is_dir():
            files.extend(sorted(directory.glob("*.md")))
    return files


def build_page_index(root: Path, dirs: list[str]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in markdown_files(root, dirs):
        rel_no_suffix = str(path.relative_to(root).with_suffix("")).replace("\\", "/")
        index[path.stem] = path
        index[rel_no_suffix] = path
    return index


def slugify(value: str, default: str = "untitled") -> str:
    slug = value.lower().replace(" ", "-").replace("：", "-").replace(":", "-")
    slug = "".join(ch for ch in slug if ch.isalnum() or ch in "-_")
    return slug.strip("-_") or default


def today() -> str:
    return date.today().isoformat()


def append_log_top(root: Path, title: str, lines: list[str] | None = None) -> None:
    log_path = root / "log.md"
    block_lines = [f"## [{today()}] {title}"]
    if lines:
        block_lines.extend(lines)
    block = "\n".join(block_lines).rstrip() + "\n\n"
    if log_path.exists():
        existing = read_text(log_path)
        if existing.startswith("#"):
            first_entry = existing.find("\n## [")
            if first_entry >= 0:
                content = existing[: first_entry + 1] + block + existing[first_entry + 1 :]
            else:
                content = existing.rstrip() + "\n\n" + block
        else:
            content = block + existing
    else:
        content = "# 操作日志\n\n" + block
    write_text(log_path, content)

#!/usr/bin/env python3
"""Convert PDF/HTML/TXT/Markdown files into raw/收件箱 Markdown."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import RAW, get_wiki_root
from wiki_common import slugify, today, write_text


def convert_pdf(path: Path) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        return None, "pdftotext 未安装"
    except subprocess.TimeoutExpired:
        return None, "PDF 转换超时"
    if result.returncode != 0:
        return None, result.stderr.strip() or "pdftotext 转换失败"
    text = result.stdout.strip()
    return (text, None) if text else (None, "PDF 提取为空，可能是扫描件")


def convert_html(path: Path) -> tuple[str | None, str | None]:
    content = path.read_text(encoding="utf-8", errors="replace")
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<[^>]+>", "\n", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"[ \t]{2,}", " ", content)
    return content.strip(), None


def convert_text(path: Path) -> tuple[str | None, str | None]:
    return path.read_text(encoding="utf-8", errors="replace").strip(), None


def unique_output_path(inbox: Path, base_name: str) -> Path:
    candidate = inbox / f"{base_name}.md"
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = inbox / f"{base_name}-{counter}.md"
        if not candidate.exists():
            return candidate
        counter += 1


def convert(path: Path) -> tuple[str | None, str | None]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return convert_pdf(path)
    if suffix in {".html", ".htm"}:
        return convert_html(path)
    if suffix in {".txt", ".md", ".markdown"}:
        return convert_text(path)
    return None, f"不支持的文件类型：{suffix or '(无扩展名)'}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a file into raw/收件箱 Markdown")
    parser.add_argument("input_file", help="PDF/HTML/TXT/Markdown file")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    args = parser.parse_args()

    source = Path(args.input_file)
    if not source.exists() or not source.is_file():
        print(f"错误：文件不存在：{source}", file=sys.stderr)
        sys.exit(1)

    content, error = convert(source)
    if error:
        print(f"错误：{error}", file=sys.stderr)
        sys.exit(1)

    root = get_wiki_root(override=args.root)
    inbox = root / RAW["收件箱"]
    inbox.mkdir(parents=True, exist_ok=True)
    output = unique_output_path(inbox, slugify(source.stem, "converted"))
    title = source.stem
    markdown = f"""---
title: {title}
created: {today()}
updated: {today()}
type: source
status: 收件箱
tags: [收件箱]
sources:
  - {source}
---

# {title}

{content}
"""
    write_text(output, markdown)
    print(f"转换完成：{output.relative_to(root)}")


if __name__ == "__main__":
    main()

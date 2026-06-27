#!/usr/bin/env python3
"""Create a review draft from a source and de-duplicate by content hash."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import META_FILES, RAW, get_wiki_root, rel_to_root, resolve_vault_path
from wiki_common import append_log_top, detect_source_kind, slugify, today, write_text


def read_manifest(path: Path) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("sources", {})
                data.setdefault("hashes", {})
                return data
        except json.JSONDecodeError:
            pass
    return {"version": 1, "created": today(), "sources": {}, "hashes": {}}


def write_manifest(path: Path, data: dict) -> None:
    data.setdefault("sources", {})
    data.setdefault("hashes", {})
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def unique_review_path(review_dir: Path, stem: str, force: bool) -> Path:
    candidate = review_dir / f"{stem}.md"
    if force or not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = review_dir / f"{stem}-{index}.md"
        if not candidate.exists():
            return candidate
        index += 1


def render_draft(title: str, source_rel: str, hash_key: str, source_text: str, source_kind: str) -> str:
    return f"""---
title: {title}
created: {today()}
updated: {today()}
type: source
status: review
source_kind: {source_kind}
tags: [待审]
sources: [{source_rel}]
confidence: low
inbox_source: {source_rel}
source_hash: {hash_key}
---

# {title}

## 待审处理

- [ ] 提炼可归档的实体、概念、对比、问题或候选。
- [ ] 为每个结论保留来源线索。
- [ ] 审阅后将 `status` 改为 `approved` 或 `rejected`。

## 可提炼线索

- 实体：
- 概念：
- 问题：
- 可能的链接：

## 原文

{source_text.rstrip()}
"""


def ingest(root: Path, source: Path, title: str | None, force: bool) -> tuple[str, Path | None]:
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)

    content_bytes = source.read_bytes()
    hash_key = "sha256:" + hashlib.sha256(content_bytes).hexdigest()
    manifest_path = root / META_FILES["manifest"]
    manifest = read_manifest(manifest_path)

    if hash_key in manifest["hashes"] and not force:
        source_key = manifest["hashes"][hash_key]
        record = manifest["sources"].get(source_key, {})
        review_file = record.get("review_file", "")
        print(f"already_ingested source={source_key} review_file={review_file}")
        return "already_ingested", None

    root.mkdir(parents=True, exist_ok=True)
    review_dir = root / RAW["待审"]
    review_dir.mkdir(parents=True, exist_ok=True)

    source_rel = rel_to_root(root, source)
    page_title = title or source.stem.replace("-", " ").replace("_", " ").strip().title() or source.stem
    stem = slugify(source.stem, default="source")
    review_path = unique_review_path(review_dir, stem, force)

    source_text = content_bytes.decode("utf-8", errors="replace")
    source_kind = detect_source_kind(source, source_text)
    write_text(review_path, render_draft(page_title, source_rel, hash_key, source_text, source_kind))

    review_rel = rel_to_root(root, review_path)
    manifest["sources"][source_rel] = {
        "hash": hash_key,
        "status": "review",
        "review_file": review_rel,
        "ingested_at": today(),
        "title": page_title,
        "source_kind": source_kind,
    }
    manifest["hashes"][hash_key] = source_rel
    write_manifest(manifest_path, manifest)

    append_log_top(root, "生成待审草稿", [f"- source: `{source_rel}`", f"- review: `{review_rel}`"])
    print(f"INGEST_OK source={source_rel} review_file={review_rel}")
    return "ingested", review_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a compile-knowledge review draft from a source")
    parser.add_argument("source", help="Source file path, absolute or relative to wiki root")
    parser.add_argument("--root", "--wiki-root", help="Vault root")
    parser.add_argument("--title", help="Draft title override")
    parser.add_argument("--force", action="store_true", help="Create a new draft even when the hash was seen before")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    try:
        ingest(root, resolve_vault_path(root, args.source), args.title, args.force)
    except FileNotFoundError as exc:
        print(f"ERROR source_not_found {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

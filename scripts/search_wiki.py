#!/usr/bin/env python3
"""BM25 full-text search for the wiki-kb vault."""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from wiki_dirs import ALL_PAGE_DIRS, get_wiki_root
from wiki_common import markdown_files, page_title, parse_frontmatter, strip_frontmatter

K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    text = strip_frontmatter(text)
    text = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"[#*`>\[\](){}]", " ", text).lower()
    tokens: list[str] = []
    for word in re.findall(r"[a-z][a-z0-9_-]*", text):
        if len(word) > 1:
            tokens.append(word)
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(segment) >= 2:
            tokens.append(segment)
        for i in range(len(segment) - 1):
            tokens.append(segment[i : i + 2])
    return tokens


class BM25Index:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.inverted: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self.avg_dl = 0.0

    def add(self, doc_id: str, tokens: list[str], path: Path, title: str, body: str) -> None:
        self.docs[doc_id] = {
            "tokens": tokens,
            "length": len(tokens),
            "path": path,
            "title": title,
            "body": body,
        }

    def build(self) -> None:
        if not self.docs:
            return
        self.avg_dl = sum(doc["length"] for doc in self.docs.values()) / len(self.docs)
        for doc_id, data in self.docs.items():
            term_freq: dict[str, int] = defaultdict(int)
            for token in data["tokens"]:
                term_freq[token] += 1
            for term, freq in term_freq.items():
                self.inverted[term].append((doc_id, freq))

    def search(self, query: str, limit: int) -> list[tuple[float, str, dict]]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.docs:
            return []
        scores: dict[str, float] = defaultdict(float)
        doc_count = len(self.docs)
        for term in query_tokens:
            postings = self.inverted.get(term, [])
            if not postings:
                continue
            idf = math.log(1 + (doc_count - len(postings) + 0.5) / (len(postings) + 0.5))
            for doc_id, freq in postings:
                doc = self.docs[doc_id]
                denom = freq + K1 * (1 - B + B * doc["length"] / max(1, self.avg_dl))
                scores[doc_id] += idf * (freq * (K1 + 1) / denom)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [(score, doc_id, self.docs[doc_id]) for doc_id, score in ranked[:limit]]


def build_index(root: Path) -> BM25Index:
    index = BM25Index()
    for path in markdown_files(root, ALL_PAGE_DIRS + ["问题索引"]):
        content = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(content)
        rel = str(path.relative_to(root)).replace("\\", "/")
        index.add(rel, tokenize(content), path, page_title(path, meta), body)
    index.build()
    return index


def excerpt(body: str, query: str, length: int = 100) -> str:
    cleaned = " ".join(line.strip() for line in body.splitlines() if line.strip())
    if not cleaned:
        return ""
    query_terms = tokenize(query)
    pos = -1
    for term in query_terms:
        pos = cleaned.lower().find(term.lower())
        if pos >= 0:
            break
    if pos < 0:
        return cleaned[:length]
    start = max(0, pos - 30)
    return cleaned[start : start + length]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search wiki-kb pages")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--root", "--wiki-root", help="Wiki root")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    args = parser.parse_args()

    root = get_wiki_root(override=args.root)
    index = build_index(root)
    results = index.search(args.query, args.limit)

    print(f"# 搜索结果：{args.query}")
    print(f"Wiki: {root}")
    if not results:
        print("未找到匹配结果。")
        return
    for rank, (score, doc_id, doc) in enumerate(results, 1):
        rel = str(doc["path"].relative_to(root)).replace("\\", "/")
        print(f"{rank}. [[{doc['title']}]] `{rel}` score={score:.2f}")
        summary = excerpt(doc["body"], args.query)
        if summary:
            print(f"   {summary}")


if __name__ == "__main__":
    main()

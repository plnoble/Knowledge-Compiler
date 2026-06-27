#!/usr/bin/env python3
"""Static verifier for compile-knowledge scripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

CLI_SCRIPTS = {
    "answer_draft.py",
    "audit_legacy_quality.py",
    "auto_research.py",
    "build_graph.py",
    "build_hot_cache.py",
    "build_moc.py",
    "candidate_card.py",
    "candidate_from_draft.py",
    "check_confidence.py",
    "compile_source.py",
    "convert_to_md.py",
    "deep_research.py",
    "detect_contradictions.py",
    "distill_skill.py",
    "fix_health.py",
    "health_check.py",
    "ingest_draft.py",
    "init_vault.py",
    "journal.py",
    "maintain.py",
    "merge_manual.py",
    "generate_p_index.py",
    "review_queue.py",
    "review_stale.py",
    "search_wiki.py",
    "smoke_wiki_sh.py",
    "verify_static.py",
}

STALE_PATTERNS = [
    r"raw/收件筱",
    r"raw/articles",
    r"raw/inbox",
    r"raw/review",
    r"raw/processed",
    r"raw/transcripts",
    r"concepts/etf",
    r"entities/",
    r"skills/review",
]

SUSPICIOUS_TAILS = (
    "return No",
    "os.makedir",
    "scores = defaultdict(float)",
    "def fix_broken(page",
    "text = (na",
)


def check_parse() -> list[str]:
    failures = []
    for path in sorted(SCRIPTS.glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            failures.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
    return failures


def check_main_guards() -> list[str]:
    failures = []
    for name in sorted(CLI_SCRIPTS):
        path = SCRIPTS / name
        if not path.exists():
            failures.append(f"{path.relative_to(ROOT)} missing")
            continue
        if 'if __name__ == "__main__"' not in path.read_text(encoding="utf-8"):
            failures.append(f"{path.relative_to(ROOT)} missing __main__ guard")
    return failures


def check_stale_paths() -> list[str]:
    failures = []
    pattern = re.compile("|".join(STALE_PATTERNS))
    candidates = [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md")), *sorted(SCRIPTS.glob("*.py"))]
    for path in candidates:
        if path.name in {"wiki_dirs.py", "migrate_para.py", "verify_static.py"}:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                failures.append(f"{path.relative_to(ROOT)}:{lineno}: stale path: {line.strip()}")
    return failures


def check_suspicious_tails() -> list[str]:
    failures = []
    for path in sorted(SCRIPTS.glob("*.py")):
        tail = "\n".join(path.read_text(encoding="utf-8").splitlines()[-8:])
        for marker in SUSPICIOUS_TAILS:
            if marker in tail:
                failures.append(f"{path.relative_to(ROOT)} suspicious tail marker: {marker}")
    return failures


def main() -> None:
    checks = {
        "parse": check_parse(),
        "main_guard": check_main_guards(),
        "stale_paths": check_stale_paths(),
        "suspicious_tails": check_suspicious_tails(),
    }
    failures = [(name, issue) for name, issues in checks.items() for issue in issues]
    if failures:
        print("FAIL")
        for name, issue in failures:
            print(f"- {name}: {issue}")
        sys.exit(1)
    print("OK")
    print(f"checked_scripts={len(list(SCRIPTS.glob('*.py')))}")


if __name__ == "__main__":
    main()

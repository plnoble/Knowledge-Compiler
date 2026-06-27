#!/usr/bin/env python3
"""Smoke-test scripts/wiki.sh when a POSIX sh is available."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WIKI_SH = SCRIPTS / "wiki.sh"

sys.path.insert(0, str(SCRIPTS))
from wiki_dirs import DIRS, RAW


def find_shell(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if os.environ.get("SH"):
        return os.environ["SH"]
    return shutil.which("sh")


def run_command(shell: str, args: list[str], vault: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["WIKI_ROOT"] = str(vault)
    env["WIKI_KB_SCRIPTS"] = str(SCRIPTS)
    env["PYTHON"] = sys.executable
    return subprocess.run(
        [shell, str(WIKI_SH), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )


def smoke(shell: str) -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        vault = Path(tmp) / "vault"
        source = Path(tmp) / "sample.txt"
        source.write_text("Alpha source text\n", encoding="utf-8")

        init_proc = run_command(shell, ["init", "--root", str(vault)], vault)
        if init_proc.returncode != 0:
            raise RuntimeError(f"init failed\n{init_proc.stdout}\n{init_proc.stderr}")

        concept = vault / DIRS["概念"] / "alpha.md"
        concept.write_text(
            """---
title: Alpha
created: 2026-06-26
updated: 2026-06-26
type: concept
tags: [smoke]
sources: []
confidence: medium
---

# Alpha

Alpha links to [[beta]].
""",
            encoding="utf-8",
        )
        entity = vault / DIRS["实体"] / "beta.md"
        entity.write_text(
            """---
title: Beta
created: 2026-06-26
updated: 2026-06-26
type: entity
tags: [smoke]
sources: []
confidence: medium
---

# Beta

Beta is a smoke-test entity.
""",
            encoding="utf-8",
        )
        inbox_source = vault / RAW["收件箱"] / "grid.md"
        inbox_source.write_text("网格交易 ETF 仓位占比 风险控制 自动化软件\n", encoding="utf-8")

        commands = [
            ["health", "--root", str(vault)],
            ["search", "Alpha", "--root", str(vault), "--limit", "3"],
            ["graph", "--root", str(vault)],
            ["moc", "--root", str(vault)],
            ["confidence", "--root", str(vault)],
            ["convert", str(source), "--root", str(vault)],
            ["p-index", "--generate", "--root", str(vault), "--limit", "3"],
            ["compile-source", str(inbox_source), "--root", str(vault)],
            ["candidate-from-draft", str(vault / RAW["待审"] / "grid.semantic.md"), "--root", str(vault), "--index", "1"],
        ]
        for command in commands:
            proc = run_command(shell, command, vault)
            if proc.returncode != 0:
                joined = " ".join(command)
                raise RuntimeError(f"command failed: {joined}\n{proc.stdout}\n{proc.stderr}")
        review_file = vault / RAW["待审"] / "grid.semantic.md"
        review_file.write_text(review_file.read_text(encoding="utf-8").replace("status: review", "status: approved"), encoding="utf-8")
        for command in [
            ["merge-manual", str(review_file), "--root", str(vault)],
            ["review-stale", "--root", str(vault)],
        ]:
            proc = run_command(shell, command, vault)
            if proc.returncode != 0:
                joined = " ".join(command)
                raise RuntimeError(f"command failed: {joined}\n{proc.stdout}\n{proc.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test wiki.sh under POSIX sh")
    parser.add_argument("--shell", help="Shell executable to use; defaults to SH or sh")
    parser.add_argument("--require-sh", action="store_true", help="Exit non-zero instead of skipping when no shell exists")
    args = parser.parse_args()

    shell = find_shell(args.shell)
    if not shell:
        print("SMOKE_SKIP: POSIX shell not found; pass --shell or set SH to run this check")
        sys.exit(2 if args.require_sh else 0)

    try:
        probe = subprocess.run(
            [shell, "-c", "printf smoke"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception as exc:
        print(f"SMOKE_SKIP: shell probe failed: {exc}")
        sys.exit(2 if args.require_sh else 0)
    if probe.returncode != 0:
        print(f"SMOKE_SKIP: shell probe returned {probe.returncode}")
        sys.exit(2 if args.require_sh else 0)

    try:
        smoke(shell)
    except Exception as exc:
        print(f"SMOKE_FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"SMOKE_OK shell={shell}")


if __name__ == "__main__":
    main()

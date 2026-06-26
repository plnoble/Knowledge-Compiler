import os
import re
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

CLI_SCRIPTS = [
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
]


class ScriptIntegrityTests(unittest.TestCase):
    def run_script(self, *args, timeout=10):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, *map(str, args)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def make_vault(self, root: Path) -> None:
        for rel in [
            "_meta",
            "实体",
            "概念",
            "对比",
            "合成",
            "查询",
            "技能",
            "候选",
            "问题索引",
            "raw/收件箱",
            "raw/待审",
            "raw/已归档",
        ]:
            (root / rel).mkdir(parents=True, exist_ok=True)

        (root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
        (root / "log.md").write_text("# Log\n", encoding="utf-8")
        (root / "概念" / "alpha.md").write_text(
            """---
title: Alpha
created: 2026-06-26
updated: 2026-06-26
type: concept
tags: [测试]
sources: []
confidence: medium
---

# Alpha

Alpha 是用于脚本烟测的概念，链接到 [[beta]]。
""",
            encoding="utf-8",
        )
        (root / "实体" / "beta.md").write_text(
            """---
title: Beta
created: 2026-06-26
updated: 2026-06-26
type: entity
tags: [测试]
sources: []
confidence: medium
---

# Beta

Beta 是用于脚本烟测的实体。
""",
            encoding="utf-8",
        )

    def make_empty_vault(self, root: Path) -> None:
        for rel in ["_meta", "实体", "概念", "对比", "合成", "查询", "raw/收件箱", "raw/待审", "raw/已归档"]:
            (root / rel).mkdir(parents=True, exist_ok=True)
        (root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
        (root / "log.md").write_text("# Log\n", encoding="utf-8")

    def test_all_python_scripts_parse(self):
        failures = []
        for script in sorted(SCRIPTS.glob("*.py")):
            try:
                compile(script.read_text(encoding="utf-8"), str(script), "exec")
            except Exception as exc:  # pragma: no cover - failure details matter
                failures.append(f"{script.name}: {type(exc).__name__}: {exc}")
        self.assertEqual([], failures)

    def test_cli_scripts_have_main_guard(self):
        missing = []
        for name in CLI_SCRIPTS:
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            if 'if __name__ == "__main__"' not in text:
                missing.append(name)
        self.assertEqual([], missing)

    def test_core_cli_commands_smoke(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_vault(vault)

            commands = [
                ("search_wiki.py", "Alpha", "--root", vault, "--limit", "3"),
                ("build_graph.py", "--root", vault),
                ("build_moc.py", "--root", vault),
                ("check_confidence.py", "--root", vault),
                ("fix_health.py", "--root", vault),
                ("maintain.py", "--root", vault, "--limit", "10"),
                ("detect_contradictions.py", "--root", vault),
            ]

            for command in commands:
                with self.subTest(command=command[0]):
                    proc = self.run_script(SCRIPTS / command[0], *command[1:])
                    combined = (proc.stdout + proc.stderr).strip()
                    self.assertEqual(proc.returncode, 0, combined)
                    self.assertTrue(combined, f"{command[0]} produced no output")

            self.assertTrue((vault / "_meta" / "graph.json").exists())
            self.assertTrue((vault / "_meta" / "confidence-report.md").exists())
            self.assertTrue((vault / "index.md").exists())

    def test_convert_to_md_writes_to_chinese_inbox(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_vault(vault)
            source = Path(tmp) / "sample.txt"
            source.write_text("hello wiki\n", encoding="utf-8")

            proc = self.run_script(SCRIPTS / "convert_to_md.py", source, "--root", vault)
            combined = (proc.stdout + proc.stderr).strip()
            self.assertEqual(proc.returncode, 0, combined)
            self.assertTrue(combined)
            self.assertTrue((vault / "raw" / "收件箱" / "sample.md").exists())

    def test_health_check_empty_vault_is_not_reported_as_healthy(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_empty_vault(vault)

            proc = self.run_script(SCRIPTS / "health_check.py", "--root", vault)
            combined = (proc.stdout + proc.stderr).strip()
            self.assertEqual(proc.returncode, 0, combined)
            self.assertIn("健康度：N/A", combined)
            self.assertNotIn("健康度：100%", combined)

    def test_verify_static_script_passes(self):
        proc = self.run_script(SCRIPTS / "verify_static.py")
        combined = (proc.stdout + proc.stderr).strip()
        self.assertEqual(proc.returncode, 0, combined)
        self.assertIn("OK", combined)

    def test_wiki_sh_smoke_helper_reports_status(self):
        proc = self.run_script(SCRIPTS / "smoke_wiki_sh.py", timeout=20)
        combined = (proc.stdout + proc.stderr).strip()
        self.assertEqual(proc.returncode, 0, combined)
        self.assertRegex(combined, r"SMOKE_(OK|SKIP)")

    def test_init_vault_creates_expected_structure(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"

            first = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)

            for rel in [
                "_meta",
                "实体",
                "概念",
                "对比",
                "合成",
                "查询",
                "技能",
                "候选",
                "日记",
                "问题索引",
                "raw/收件箱",
                "raw/待审",
                "raw/已归档",
                "raw/论文",
                "raw/笔记",
                "raw/资产",
            ]:
                self.assertTrue((vault / rel).is_dir(), rel)

            for rel in [
                "SCHEMA.md",
                "index.md",
                "log.md",
                "_meta/manifest.json",
                "_meta/hot.md",
                "_meta/research-agenda.md",
                "_meta/personal-context.md",
            ]:
                self.assertTrue((vault / rel).exists(), rel)
            self.assertTrue((vault / "_archive" / "review-backups").is_dir())

            manifest = json.loads((vault / "_meta" / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("sources", manifest)
            self.assertIn("hashes", manifest)

    def test_ingest_draft_creates_review_file_and_dedupes_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            init = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

            source = vault / "raw" / "收件箱" / "source.md"
            source.write_text("# Source\n\nThis source explains Alpha and Beta.\n", encoding="utf-8")

            first = self.run_script(SCRIPTS / "ingest_draft.py", source, "--root", vault)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            review = vault / "raw" / "待审" / "source.md"
            self.assertTrue(review.exists())
            review_text = review.read_text(encoding="utf-8")
            self.assertIn("status: review", review_text)
            self.assertIn("source_hash:", review_text)
            self.assertIn("## 原文", review_text)

            second = self.run_script(SCRIPTS / "ingest_draft.py", source, "--root", vault)
            combined = (second.stdout + second.stderr).strip()
            self.assertEqual(second.returncode, 0, combined)
            self.assertIn("already_ingested", combined)

            manifest = json.loads((vault / "_meta" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(manifest["hashes"]))
            self.assertIn("raw/收件箱/source.md", manifest["sources"])

    def test_generate_p_index_and_research_agenda_cover_gaps(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_vault(vault)

            agenda = self.run_script(SCRIPTS / "auto_research.py", "--root", vault)
            self.assertEqual(agenda.returncode, 0, agenda.stdout + agenda.stderr)
            agenda_text = (vault / "_meta" / "research-agenda.md").read_text(encoding="utf-8")
            self.assertIn("P-index", agenda_text)

            generated = self.run_script(SCRIPTS / "generate_p_index.py", "--root", vault, "--limit", "5")
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            questions = sorted((vault / "问题索引").glob("*.md"))
            self.assertGreaterEqual(len(questions), 2)
            combined_questions = "\n".join(p.read_text(encoding="utf-8") for p in questions)
            self.assertIn("[[alpha]]", combined_questions)
            self.assertIn("[[beta]]", combined_questions)

    def test_openai_yaml_metadata_exists(self):
        metadata = ROOT / "agents" / "openai.yaml"
        self.assertTrue(metadata.exists())
        text = metadata.read_text(encoding="utf-8")
        self.assertIn('display_name: "wiki-kb"', text)
        self.assertIn("short_description:", text)
        self.assertIn("$wiki-kb", text)
        self.assertIn("allow_implicit_invocation: true", text)

    def test_compile_source_creates_semantic_review_for_investment(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            init = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

            source = vault / "raw" / "收件箱" / "grid.md"
            source.write_text(
                "# 网格策略\n\n这篇理财文章讲网格交易、ETF、仓位占比、风险控制和自动化软件机会。\n",
                encoding="utf-8",
            )

            proc = self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            combined = proc.stdout + proc.stderr
            self.assertIn("COMPILE_OK", combined)

            review = vault / "raw" / "待审" / "grid.semantic.md"
            self.assertTrue(review.exists())
            text = review.read_text(encoding="utf-8")
            self.assertIn("workflow: semantic-compile", text)
            self.assertIn("domain: 投资体系", text)
            self.assertIn("target_path: 合成/投资策略手册.md", text)
            for heading in [
                "## 来源摘要",
                "## 核心知识",
                "## 知识更新建议",
                "## 手册更新建议",
                "## P-index 问题",
                "## Deep Research 缺口",
                "## 候选卡建议",
                "## 风险与边界",
                "## 审阅决定",
            ]:
                self.assertIn(heading, text)
            self.assertIn("不构成投资建议", text)
            self.assertIn("自动网格策略工具", text)

    def test_compile_source_ascii_ai_keyword_requires_word_boundary(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            init = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

            source = vault / "raw" / "收件箱" / "english-grid.md"
            source.write_text(
                "Grid strategy suits range-bound markets and failure conditions; "
                "position sizing and risk controls matter.",
                encoding="utf-8",
            )

            proc = self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            review = vault / "raw" / "待审" / "english-grid.semantic.md"
            self.assertTrue(review.exists())
            text = review.read_text(encoding="utf-8")
            self.assertIn("domain: 投资体系", text)
            self.assertIn("target_path: 合成/投资策略手册.md", text)
            self.assertNotIn("domain: AI与自动化", text)

    def test_candidate_from_draft_promotes_suggestion_with_maturity_fields(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            source = vault / "raw" / "收件箱" / "grid.md"
            source.write_text("网格交易 ETF 仓位占比 自动化 软件", encoding="utf-8")
            compile_proc = self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault)
            self.assertEqual(compile_proc.returncode, 0, compile_proc.stdout + compile_proc.stderr)
            review = vault / "raw" / "待审" / "grid.semantic.md"

            proc = self.run_script(SCRIPTS / "candidate_from_draft.py", review, "--root", vault, "--index", "1")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("CANDIDATE_OK", proc.stdout + proc.stderr)

            cards = sorted((vault / "候选").glob("*.md"))
            self.assertEqual(1, len(cards))
            text = cards[0].read_text(encoding="utf-8")
            self.assertIn("type: candidate", text)
            self.assertIn("status: suggested", text)
            self.assertIn("candidate_kind: software", text)
            self.assertIn("evidence_count: 1", text)
            self.assertIn("personal_fit:", text)
            self.assertIn("validation_cost:", text)
            self.assertIn("raw/收件箱/grid.md", text)

    def test_merge_manual_backs_up_existing_manual_before_append(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            manual = vault / "合成" / "投资策略手册.md"
            manual.write_text(
                """---
title: 投资策略手册
type: synthesis
created: 2026-01-01
updated: 2026-01-01
last_verified: 2026-01-01
review_after: 2026-04-01
---

# 投资策略手册

## 当前结论

旧内容。
""",
                encoding="utf-8",
            )
            source = vault / "raw" / "收件箱" / "grid.md"
            source.write_text("网格交易 ETF 仓位占比 风险控制", encoding="utf-8")
            self.assertEqual(self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault).returncode, 0)
            review = vault / "raw" / "待审" / "grid.semantic.md"
            review_text = review.read_text(encoding="utf-8").replace("status: review", "status: approved")
            review.write_text(review_text, encoding="utf-8")

            proc = self.run_script(SCRIPTS / "merge_manual.py", review, "--root", vault)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("MERGE_OK", proc.stdout + proc.stderr)
            backups = list((vault / "_archive" / "review-backups").glob("*.md"))
            self.assertEqual(1, len(backups))
            merged = manual.read_text(encoding="utf-8")
            self.assertIn("## 待审合并", merged)
            self.assertIn("网格", merged)
            self.assertIn("last_verified:", merged)
            self.assertIn("review_after:", merged)

    def test_review_stale_reports_due_pages_without_modifying_them(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            manual = vault / "合成" / "Codex操作手册.md"
            original = """---
title: Codex操作手册
type: synthesis
created: 2026-01-01
updated: 2026-01-01
last_verified: 2026-01-01
review_after: 2026-02-01
validity: time-sensitive
---

# Codex操作手册
"""
            manual.write_text(original, encoding="utf-8")

            proc = self.run_script(SCRIPTS / "review_stale.py", "--root", vault)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("STALE_REVIEW_OK", proc.stdout + proc.stderr)
            report = vault / "_meta" / "stale-review.md"
            self.assertTrue(report.exists())
            report_text = report.read_text(encoding="utf-8")
            self.assertIn("Codex操作手册", report_text)
            self.assertIn("保留 / 降级 / 合并 / 归档", report_text)
            self.assertEqual(original, manual.read_text(encoding="utf-8"))

    def test_skill_markdown_is_slim_and_references_exist(self):
        skill_path = ROOT / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 250)
        self.assertIn("references/structure-frontmatter.md", text)
        self.assertIn("references/workflows.md", text)
        self.assertIn("references/loops-maintenance.md", text)
        self.assertIn("references/domain-investment.md", text)
        self.assertIn("references/domain-ai-tools.md", text)
        self.assertIn("references/domain-hong-kong.md", text)

        refs = set(re.findall(r"\]\((references/[^)#]+\.md)(?:#[^)]+)?\)", text))
        self.assertEqual(
            {
                "references/structure-frontmatter.md",
                "references/workflows.md",
                "references/loops-maintenance.md",
                "references/domain-investment.md",
                "references/domain-ai-tools.md",
                "references/domain-hong-kong.md",
            },
            refs,
        )
        for rel in refs:
            ref_path = ROOT / rel
            self.assertTrue(ref_path.exists(), rel)
            ref_text = ref_path.read_text(encoding="utf-8")
            nested_refs = re.findall(r"\]\((references/[^)#]+\.md)(?:#[^)]+)?\)", ref_text)
            self.assertEqual([], nested_refs, f"{rel} should not link to nested references")


if __name__ == "__main__":
    unittest.main()

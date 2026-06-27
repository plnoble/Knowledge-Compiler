import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

INBOX_PENDING = "0 - Inbox/待处理"
INBOX_REVIEW = "0 - Inbox/待审"
RESOURCES = "1 - Resources（资源）"
AREA_INVESTMENT = "2 - Areas（领域）/投资体系"
AREA_AI = "2 - Areas（领域）/AI与自动化"
AREA_HK = "2 - Areas（领域）/香港行动"
AREA_OPS = "2 - Areas（领域）/知识库运营"
PROJECT_CANDIDATES = "3 - Projects（项目）/候选"
PROJECT_ACTIVE = "3 - Projects（项目）/活跃项目"
PROJECT_PAUSED = "3 - Projects（项目）/已暂停"
RESOURCE_ENTITY = f"{RESOURCES}/实体"
RESOURCE_CONCEPT = f"{RESOURCES}/概念"
RESOURCE_COMPARISON = f"{RESOURCES}/对比"
RESOURCE_QUERY = f"{RESOURCES}/查询"
RESOURCE_P_INDEX = f"{RESOURCES}/问题索引"
SKILLS = "4 - Skills（技能）"
SKILL_REVIEW = f"{SKILLS}/待审"
ARCHIVE_SOURCES = "5 - Archives（归档）/已归档来源"
ARCHIVE_FINISHED = "5 - Archives（归档）/已结束项目"
ARCHIVE_STALE = "5 - Archives（归档）/过时知识"
ARCHIVE_BACKUPS = "5 - Archives（归档）/系统备份"
TEMPLATES = "6 - Templates（模板）"
DAILY = "7 - Daily（日记）"


CLI_SCRIPTS = [
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
    "migrate_para.py",
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

    def make_para_vault(self, root: Path) -> None:
        for rel in [
            "_meta",
            INBOX_PENDING,
            INBOX_REVIEW,
            PROJECT_CANDIDATES,
            AREA_INVESTMENT,
            AREA_AI,
            AREA_HK,
            AREA_OPS,
            RESOURCE_ENTITY,
            RESOURCE_CONCEPT,
            RESOURCE_COMPARISON,
            RESOURCE_QUERY,
            RESOURCE_P_INDEX,
            SKILL_REVIEW,
            ARCHIVE_SOURCES,
            ARCHIVE_BACKUPS,
            DAILY,
        ]:
            (root / rel).mkdir(parents=True, exist_ok=True)

        (root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
        (root / "index.md").write_text("# Index\n", encoding="utf-8")
        (root / "log.md").write_text("# Log\n", encoding="utf-8")
        (root / RESOURCE_CONCEPT / "alpha.md").write_text(
            """---
title: Alpha
created: 2026-06-27
updated: 2026-06-27
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
        (root / RESOURCE_ENTITY / "beta.md").write_text(
            """---
title: Beta
created: 2026-06-27
updated: 2026-06-27
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

    def make_old_vault(self, root: Path) -> None:
        for rel in [
            "_meta",
            "_archive/review-backups",
            "raw/assets",
            "raw/papers",
            "raw/transcripts",
            "raw/收件箱",
            "raw/待审",
            "raw/已归档",
            "raw/论文",
            "raw/笔记",
            "raw/资产",
            "实体",
            "概念",
            "对比",
            "查询",
            "问题索引",
            "技能/待审",
            "候选",
            "日记",
            "合成",
        ]:
            (root / rel).mkdir(parents=True, exist_ok=True)
        (root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
        (root / "index.md").write_text("# Index\n", encoding="utf-8")
        (root / "log.md").write_text("# Log\n", encoding="utf-8")
        (root / "_meta" / "manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": {
                        "raw/收件箱/source.md": {
                            "hash": "sha256:test",
                            "status": "review",
                            "review_file": "raw/待审/source.semantic.md",
                        }
                    },
                    "hashes": {"sha256:test": "raw/收件箱/source.md"},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "raw" / "收件箱" / "source.md").write_text("投资 网格 仓位 风险\n", encoding="utf-8")
        (root / "raw" / "assets" / "asset.md").write_text("asset\n", encoding="utf-8")
        (root / "raw" / "待审" / "source.semantic.md").write_text(
            """---
title: 语义编译：source
type: source
status: review
target_path: 合成/投资策略手册.md
sources: [raw/收件箱/source.md]
inbox_source: raw/收件箱/source.md
---

# 语义编译：source

链接到 [[概念/网格交易]]。
""",
            encoding="utf-8",
        )
        (root / "概念" / "网格交易.md").write_text("# 网格交易\n", encoding="utf-8")
        (root / "实体" / "香港.md").write_text("# 香港\n", encoding="utf-8")
        (root / "合成" / "投资策略手册.md").write_text("# 投资策略手册\n", encoding="utf-8")
        (root / "候选" / "自动网格策略工具.md").write_text("# 自动网格策略工具\n", encoding="utf-8")
        (root / "日记" / "2026-06-27.md").write_text("# 日记\n", encoding="utf-8")
        (root / "_archive" / "review-backups" / "old.md").write_text("# backup\n", encoding="utf-8")

    def make_current_06_vault(self, root: Path) -> None:
        old_resources = "3 - Resources（资源）"
        old_projects = "1 - Projects（项目）"
        old_archives = "4 - Archives（归档）"
        for rel in [
            "_meta",
            "0 - Inbox/待处理",
            "0 - Inbox/待审",
            f"{old_projects}/候选",
            f"{old_resources}/概念",
            f"{old_resources}/实体",
            f"{old_resources}/查询",
            f"{old_resources}/问题索引",
            f"{old_resources}/技能/待审",
            f"{old_archives}/系统备份/review-backups",
            "5 - Templates（模板）",
            "6 - Daily（日记）",
            AREA_INVESTMENT,
        ]:
            (root / rel).mkdir(parents=True, exist_ok=True)
        (root / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
        (root / "index.md").write_text("# Index\n", encoding="utf-8")
        (root / "log.md").write_text("# Log\n", encoding="utf-8")
        (root / old_resources / "概念" / "旧资源.md").write_text("# 旧资源\n", encoding="utf-8")
        (root / old_resources / "查询" / "旧问答.md").write_text("# 旧问答\n", encoding="utf-8")
        (root / old_resources / "技能" / "待审" / "旧技能.md").write_text("# 旧技能\n", encoding="utf-8")
        (root / old_projects / "候选" / "旧项目.md").write_text("# 旧项目\n", encoding="utf-8")
        (root / old_archives / "系统备份" / "review-backups" / "旧备份.md").write_text("# 旧备份\n", encoding="utf-8")
        (root / "5 - Templates（模板）" / "旧模板.md").write_text("# 旧模板\n", encoding="utf-8")
        (root / "6 - Daily（日记）" / "旧日记.md").write_text("# 旧日记\n", encoding="utf-8")
        (root / "0 - Inbox" / "待审" / "old.semantic.md").write_text(
            f"""---
title: old
status: review
target_path: {AREA_INVESTMENT}/投资策略手册.md
sources: [0 - Inbox/待处理/source.md]
---

链接到 [[{old_resources}/概念/旧资源]] 和 [[{old_resources}/技能/待审/旧技能]]。
""",
            encoding="utf-8",
        )

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

    def test_skill_identity_is_compile_knowledge(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: compile-knowledge", skill_text)
        self.assertIn("Knowledge Compiler", skill_text)
        self.assertIn("0 - Inbox/待处理", skill_text)
        self.assertIn("Source Coverage Map", skill_text)
        self.assertIn("Impact Review", skill_text)
        self.assertIn("4 - Skills（技能）", skill_text)
        self.assertIn("模式 5", skill_text)

        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Knowledge Compiler / 知识编译器"', metadata)
        self.assertIn("$compile-knowledge", metadata)

    def test_init_vault_creates_para_structure(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"

            first = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_script(SCRIPTS / "init_vault.py", "--root", vault)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)

            for rel in [
                INBOX_PENDING,
                INBOX_REVIEW,
                PROJECT_CANDIDATES,
                PROJECT_ACTIVE,
                PROJECT_PAUSED,
                AREA_INVESTMENT,
                AREA_AI,
                AREA_HK,
                AREA_OPS,
                RESOURCE_ENTITY,
                RESOURCE_CONCEPT,
            RESOURCE_COMPARISON,
            RESOURCE_QUERY,
            RESOURCE_P_INDEX,
            SKILL_REVIEW,
            ARCHIVE_SOURCES,
                ARCHIVE_FINISHED,
                ARCHIVE_STALE,
                ARCHIVE_BACKUPS,
                TEMPLATES,
                DAILY,
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
            self.assertFalse((vault / "raw").exists(), "new init should not create raw/")
            for rel in [
                "1 - Projects（项目）",
                "3 - Resources（资源）",
                "4 - Archives（归档）",
                "5 - Templates（模板）",
                "6 - Daily（日记）",
            ]:
                self.assertFalse((vault / rel).exists(), f"old 0-6 directory should not exist: {rel}")

    def test_convert_to_md_writes_to_para_pending_inbox(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_para_vault(vault)
            source = Path(tmp) / "sample.txt"
            source.write_text("hello knowledge compiler\n", encoding="utf-8")

            proc = self.run_script(SCRIPTS / "convert_to_md.py", source, "--root", vault)
            combined = (proc.stdout + proc.stderr).strip()
            self.assertEqual(proc.returncode, 0, combined)
            self.assertTrue((vault / INBOX_PENDING / "sample.md").exists())

    def test_ingest_draft_creates_review_file_with_source_kind(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            source = vault / INBOX_PENDING / "source.md"
            source.write_text("# Source\n\nThis source explains Alpha and Beta.\n", encoding="utf-8")

            first = self.run_script(SCRIPTS / "ingest_draft.py", source, "--root", vault)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            review = vault / INBOX_REVIEW / "source.md"
            self.assertTrue(review.exists())
            review_text = review.read_text(encoding="utf-8")
            self.assertIn("status: review", review_text)
            self.assertIn("source_kind: article", review_text)
            self.assertIn(f"inbox_source: {INBOX_PENDING}/source.md", review_text)

            second = self.run_script(SCRIPTS / "ingest_draft.py", source, "--root", vault)
            combined = (second.stdout + second.stderr).strip()
            self.assertEqual(second.returncode, 0, combined)
            self.assertIn("already_ingested", combined)

    def test_compile_source_creates_semantic_review_and_coverage_map(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            source = vault / INBOX_PENDING / "grid.md"
            source.write_text(
                "# Grid strategy\n\nGrid strategy suits range-bound markets.\n\nPosition sizing and risk controls matter.",
                encoding="utf-8",
            )

            proc = self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault)
            combined = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, combined)
            self.assertIn("COMPILE_OK", combined)
            self.assertIn("coverage_file=", combined)

            review = vault / INBOX_REVIEW / "grid.semantic.md"
            coverage = vault / INBOX_REVIEW / "grid.coverage.md"
            self.assertTrue(review.exists())
            self.assertTrue(coverage.exists())

            review_text = review.read_text(encoding="utf-8")
            self.assertIn("workflow: semantic-compile", review_text)
            self.assertIn("source_kind: article", review_text)
            self.assertIn(f"inbox_source: {INBOX_PENDING}/grid.md", review_text)
            self.assertIn(f"target_path: {AREA_INVESTMENT}/投资策略手册.md", review_text)
            self.assertIn("## Impact Review / 影响面审查", review_text)
            for heading in [
                "可能新增的 Resources",
                "可能更新的 Resources",
                "可能影响的 Areas",
                "可能影响的 Projects",
                "可能影响的 Skills",
                "冲突或过时内容",
                "不更新原因",
                "仍需研究的问题",
            ]:
                self.assertIn(heading, review_text)

            coverage_text = coverage.read_text(encoding="utf-8")
            self.assertIn("Source Coverage Map", coverage_text)
            self.assertIn("原文要点", coverage_text)
            self.assertIn("是否沉淀", coverage_text)
            self.assertIn("目标 Resource", coverage_text)

    def test_legacy_raw_inbox_path_resolves_to_para_pending_inbox(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            source = vault / INBOX_PENDING / "legacy.md"
            source.write_text("Codex workflow prompt automation\n", encoding="utf-8")

            proc = self.run_script(SCRIPTS / "compile_source.py", "raw/收件箱/legacy.md", "--root", vault)
            combined = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, combined)
            self.assertTrue((vault / INBOX_REVIEW / "legacy.semantic.md").exists())

    def test_candidate_from_draft_promotes_suggestion_to_projects_candidate(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            source = vault / INBOX_PENDING / "grid.md"
            source.write_text("网格交易 ETF 仓位占比 自动化 软件", encoding="utf-8")
            self.assertEqual(self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault).returncode, 0)
            review = vault / INBOX_REVIEW / "grid.semantic.md"

            proc = self.run_script(SCRIPTS / "candidate_from_draft.py", review, "--root", vault, "--index", "1")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            cards = sorted((vault / PROJECT_CANDIDATES).glob("*.md"))
            self.assertEqual(1, len(cards))
            text = cards[0].read_text(encoding="utf-8")
            self.assertIn("type: candidate", text)
            self.assertIn("status: suggested", text)
            self.assertIn(f"{INBOX_PENDING}/grid.md", text)

    def test_distill_skill_writes_to_top_level_skills_review(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_para_vault(vault)

            proc = self.run_script(
                SCRIPTS / "distill_skill.py",
                f"{RESOURCE_CONCEPT}/alpha.md",
                "--wiki-root",
                vault,
                "--name",
                "alpha-skill",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            output = vault / SKILL_REVIEW / "alpha-skill.md"
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("type: skill", text)
            self.assertIn("status: review", text)
            self.assertFalse((vault / RESOURCES / "技能" / "待审" / "alpha-skill.md").exists())

    def test_answer_draft_creates_review_without_formal_query_write(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)

            proc = self.run_script(
                SCRIPTS / "answer_draft.py",
                "--root",
                vault,
                "--question",
                "我去香港能做什么？",
                "--answer",
                "基于库内资料，可以整理开户准备和半日行动清单。",
                "--source",
                f"{AREA_HK}/香港行动指南.md",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("ANSWER_DRAFT_OK", proc.stdout + proc.stderr)
            drafts = sorted((vault / INBOX_REVIEW).glob("*.answer.md"))
            self.assertEqual(1, len(drafts))
            text = drafts[0].read_text(encoding="utf-8")
            self.assertIn("workflow: answer-review", text)
            self.assertIn(f"target_path: {RESOURCE_QUERY}/", text)
            self.assertIn("库内已有", text)
            self.assertIn("推断建议", text)
            self.assertIn("外部补充", text)
            self.assertIn("仍需研究", text)
            self.assertEqual([], list((vault / RESOURCE_QUERY).glob("*.md")))

    def test_merge_manual_targets_area_and_backs_up_existing_manual(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)
            manual = vault / AREA_INVESTMENT / "投资策略手册.md"
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

旧内容。
""",
                encoding="utf-8",
            )
            source = vault / INBOX_PENDING / "grid.md"
            source.write_text("网格交易 ETF 仓位占比 风险控制", encoding="utf-8")
            self.assertEqual(self.run_script(SCRIPTS / "compile_source.py", source, "--root", vault).returncode, 0)
            review = vault / INBOX_REVIEW / "grid.semantic.md"
            review.write_text(review.read_text(encoding="utf-8").replace("status: review", "status: approved"), encoding="utf-8")

            proc = self.run_script(SCRIPTS / "merge_manual.py", review, "--root", vault)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(f"MERGE_OK target={AREA_INVESTMENT}/投资策略手册.md", proc.stdout + proc.stderr)
            backups = list((vault / ARCHIVE_BACKUPS / "review-backups").glob("*.md"))
            self.assertEqual(1, len(backups))
            self.assertIn("## 待审合并", manual.read_text(encoding="utf-8"))

    def test_migrate_para_dry_run_and_apply_moves_old_structure(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_old_vault(vault)

            dry = self.run_script(SCRIPTS / "migrate_para.py", "--root", vault, "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("MIGRATE_PLAN", dry.stdout + dry.stderr)
            self.assertFalse((vault / INBOX_PENDING / "source.md").exists())
            self.assertTrue((vault / "raw" / "收件箱" / "source.md").exists())

            apply = self.run_script(SCRIPTS / "migrate_para.py", "--root", vault, "--apply")
            self.assertEqual(apply.returncode, 0, apply.stdout + apply.stderr)
            self.assertIn("MIGRATE_OK", apply.stdout + apply.stderr)

            self.assertTrue((vault / INBOX_PENDING / "source.md").exists())
            self.assertTrue((vault / INBOX_PENDING / "asset.md").exists())
            self.assertTrue((vault / INBOX_REVIEW / "source.semantic.md").exists())
            self.assertTrue((vault / RESOURCE_CONCEPT / "网格交易.md").exists())
            self.assertTrue((vault / RESOURCE_ENTITY / "香港.md").exists())
            self.assertTrue((vault / AREA_INVESTMENT / "投资策略手册.md").exists())
            self.assertTrue((vault / PROJECT_CANDIDATES / "自动网格策略工具.md").exists())
            self.assertTrue((vault / DAILY / "2026-06-27.md").exists())
            self.assertTrue((vault / ARCHIVE_BACKUPS / "review-backups" / "old.md").exists())
            self.assertFalse((vault / "raw").exists(), "old raw directory should be cleaned when empty")

            manifest = json.loads((vault / "_meta" / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn(f"{INBOX_PENDING}/source.md", manifest["sources"])
            self.assertEqual(f"{INBOX_PENDING}/source.md", manifest["hashes"]["sha256:test"])
            draft_text = (vault / INBOX_REVIEW / "source.semantic.md").read_text(encoding="utf-8")
            self.assertIn(f"target_path: {AREA_INVESTMENT}/投资策略手册.md", draft_text)
            self.assertIn(f"sources: [{INBOX_PENDING}/source.md]", draft_text)
            self.assertIn(f"[[{RESOURCE_CONCEPT}/网格交易]]", draft_text)

    def test_migrate_para_moves_current_06_structure_to_07(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_current_06_vault(vault)

            dry = self.run_script(SCRIPTS / "migrate_para.py", "--root", vault, "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("MIGRATE_PLAN", dry.stdout + dry.stderr)
            self.assertTrue((vault / "3 - Resources（资源）" / "概念" / "旧资源.md").exists())

            apply = self.run_script(SCRIPTS / "migrate_para.py", "--root", vault, "--apply")
            self.assertEqual(apply.returncode, 0, apply.stdout + apply.stderr)
            self.assertIn("MIGRATE_OK", apply.stdout + apply.stderr)

            self.assertTrue((vault / RESOURCE_CONCEPT / "旧资源.md").exists())
            self.assertTrue((vault / RESOURCE_QUERY / "旧问答.md").exists())
            self.assertTrue((vault / SKILL_REVIEW / "旧技能.md").exists())
            self.assertTrue((vault / PROJECT_CANDIDATES / "旧项目.md").exists())
            self.assertTrue((vault / ARCHIVE_BACKUPS / "review-backups" / "旧备份.md").exists())
            self.assertTrue((vault / TEMPLATES / "旧模板.md").exists())
            self.assertTrue((vault / DAILY / "旧日记.md").exists())
            self.assertFalse((vault / "3 - Resources（资源）").exists(), "old Resources number should be cleaned")
            self.assertFalse((vault / "1 - Projects（项目）").exists(), "old Projects number should be cleaned")

            draft_text = (vault / INBOX_REVIEW / "old.semantic.md").read_text(encoding="utf-8")
            self.assertIn(f"[[{RESOURCE_CONCEPT}/旧资源]]", draft_text)
            self.assertIn(f"[[{SKILL_REVIEW}/旧技能]]", draft_text)

    def test_core_cli_commands_smoke_against_para_vault(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_para_vault(vault)

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

    def test_generate_p_index_writes_to_resources(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_para_vault(vault)

            generated = self.run_script(SCRIPTS / "generate_p_index.py", "--root", vault, "--limit", "5")
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            questions = sorted((vault / RESOURCE_P_INDEX).glob("*.md"))
            self.assertGreaterEqual(len(questions), 2)
            combined_questions = "\n".join(p.read_text(encoding="utf-8") for p in questions)
            self.assertIn("[[alpha]]", combined_questions)
            self.assertIn("[[beta]]", combined_questions)

    def test_audit_legacy_quality_writes_sample_report(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            self.make_para_vault(vault)

            proc = self.run_script(
                SCRIPTS / "audit_legacy_quality.py",
                "--root",
                vault,
                "--concept-count",
                "1",
                "--entity-count",
                "1",
                "--comparison-count",
                "0",
                "--date",
                "2026-06-27",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("AUDIT_OK", proc.stdout + proc.stderr)
            report = vault / "_meta" / "legacy-quality-audit-2026-06-27.md"
            self.assertTrue(report.exists())
            report_text = report.read_text(encoding="utf-8")
            self.assertIn("旧知识质量抽样报告", report_text)
            self.assertIn("抽样总数：2 页", report_text)

    def test_health_check_empty_vault_is_not_reported_as_healthy(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp) / "vault"
            self.assertEqual(self.run_script(SCRIPTS / "init_vault.py", "--root", vault).returncode, 0)

            proc = self.run_script(SCRIPTS / "health_check.py", "--root", vault)
            combined = (proc.stdout + proc.stderr).strip()
            self.assertEqual(proc.returncode, 0, combined)
            self.assertIn("N/A", combined)
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

    def test_skill_markdown_is_slim_and_references_exist(self):
        skill_path = ROOT / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 280)
        for rel in [
            "references/structure-frontmatter.md",
            "references/workflows.md",
            "references/loops-maintenance.md",
            "references/domain-investment.md",
            "references/domain-ai-tools.md",
            "references/domain-hong-kong.md",
        ]:
            self.assertIn(rel, text)
            self.assertTrue((ROOT / rel).exists(), rel)
        refs = re.findall(r"\]\((references/[^)#]+\.md)(?:#[^)]+)?\)", text)
        for rel in refs:
            ref_text = (ROOT / rel).read_text(encoding="utf-8")
            nested_refs = re.findall(r"\]\((references/[^)#]+\.md)(?:#[^)]+)?\)", ref_text)
            self.assertEqual([], nested_refs, f"{rel} should not link to nested references")


if __name__ == "__main__":
    unittest.main()

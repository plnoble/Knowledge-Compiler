# Knowledge Compiler / 知识编译器

`compile-knowledge` is a review-gated personal knowledge compiler for Obsidian.
It turns messy Inbox material into traceable Resources, long-lived Areas,
selective Projects, reusable Skills, and reviewable personal Q&A.

This is not a generic file dump. The intended workflow is:

```text
0 - Inbox/待处理
-> 0 - Inbox/待审
-> 1 - Resources（资源）
-> 2 - Areas（领域）
-> 3 - Projects（项目）/候选
-> 4 - Skills（技能）/待审
-> 5 - Archives（归档）/已归档来源
```

Formal knowledge writes stay review-gated. AI-generated drafts should be
approved before they update Resources, Areas, Projects, or Skills.

## Install

Clone this repository into the Codex skills directory under the new skill name:

```powershell
git clone https://github.com/plnoble/Knowledge-Compiler.git "$env:USERPROFILE\.codex\skills\compile-knowledge"
```

Then invoke it naturally:

```text
使用 compile-knowledge，把这篇资料加工成知识库待审稿。
```

Or explicitly:

```text
$compile-knowledge 处理 0 - Inbox/待处理/xxx.md
```

## Initialize A Vault

```bash
sh scripts/wiki.sh init --root <vault>
```

This creates the 0-7 structure:

```text
0 - Inbox/
1 - Resources（资源）/
2 - Areas（领域）/
3 - Projects（项目）/
4 - Skills（技能）/
5 - Archives（归档）/
6 - Templates（模板）/
7 - Daily（日记）/
_meta/
SCHEMA.md
index.md
log.md
```

## Core Commands

```bash
sh scripts/wiki.sh compile-source "0 - Inbox/待处理/source.md" --root <vault>
sh scripts/wiki.sh review --root <vault> --dry-run
sh scripts/wiki.sh merge-manual "0 - Inbox/待审/source.semantic.md" --root <vault>
sh scripts/wiki.sh candidate-from-draft "0 - Inbox/待审/source.semantic.md" --root <vault>
sh scripts/wiki.sh skill "1 - Resources（资源）/概念/topic.md" --root <vault>
sh scripts/wiki.sh answer-draft --root <vault> --question "..." --answer "..."
sh scripts/wiki.sh health --root <vault>
```

`compile-source` creates:

- a semantic review draft
- a Source Coverage Map
- an Impact Review

## Migrate An Old Vault

Always back up the vault first.

Preview:

```bash
sh scripts/wiki.sh migrate-para --root <vault> --dry-run
```

Apply:

```bash
sh scripts/wiki.sh migrate-para --root <vault> --apply
```

The migration helper accepts old `raw/` paths, old Chinese top-level paths, and
the previous 0-6 numbered layout. It moves files into the 0-7 structure and
cleans empty old directories.

## Review In Obsidian

Use Obsidian Search or a dashboard page for:

```text
path:"0 - Inbox/待审" [status:review]
path:"0 - Inbox/待审" [status:approved]
path:"0 - Inbox/待审" [status:rejected]
```

Approve by changing frontmatter:

```yaml
status: approved
```

Reject by changing:

```yaml
status: rejected
```

## Documentation

- [Operation Manual](docs/operation-manual.md)
- [Test Plan](docs/test-plan.md)
- [Structure and Frontmatter](references/structure-frontmatter.md)
- [Workflows](references/workflows.md)
- [Loops and Maintenance](references/loops-maintenance.md)

## Verification

```bash
python -m unittest tests.test_script_integrity
python scripts/verify_static.py
python scripts/smoke_wiki_sh.py
```

On Windows without a POSIX shell, `smoke_wiki_sh.py` may report `SMOKE_SKIP`.
Run it again in a POSIX/Minis environment for full shell-wrapper verification.

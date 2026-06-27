# Knowledge Compiler 测试方案

## 自动化测试

在仓库根目录运行：

```powershell
python -m unittest tests.test_script_integrity
python scripts/verify_static.py
python scripts/smoke_wiki_sh.py
```

期望：

- unittest 全部通过。
- static verifier 输出 `OK`。
- 有 POSIX `sh` 时 smoke 输出 `SMOKE_OK`；没有时输出 `SMOKE_SKIP`。

## 初始化测试

```powershell
$vault = "$env:TEMP\kc-vault"
python scripts/init_vault.py --root $vault
python scripts/init_vault.py --root $vault --print
```

检查：

- 存在 `0 - Inbox/待处理/` 和 `0 - Inbox/待审/`。
- 存在 `1 - Resources（资源）/`、`2 - Areas（领域）/`、`3 - Projects（项目）/`、`4 - Skills（技能）/`、`5 - Archives（归档）/`、`6 - Templates（模板）/`、`7 - Daily（日记）/`。
- 存在 `_meta/manifest.json`、`_meta/hot.md`、`_meta/research-agenda.md`。
- 不应创建旧 `raw/` 或上一版 0-6 编号目录。

## Inbox 编译测试

准备资料：

```powershell
Set-Content -Encoding UTF8 "$vault\0 - Inbox\待处理\grid.md" "网格交易适合震荡市场。仓位、风险控制和板块占比很重要。"
python scripts/compile_source.py "$vault\0 - Inbox\待处理\grid.md" --root $vault
```

检查：

- `0 - Inbox/待审/grid.semantic.md` 存在。
- `0 - Inbox/待审/grid.coverage.md` 存在。
- 待审稿包含 `source_kind`、`workflow: semantic-compile`、`target_path`。
- 待审稿包含 `## Impact Review / 影响面审查`。
- Coverage Map 包含 `原文要点`、`是否沉淀`、`目标 Resource`、`未处理原因`。

## 旧路径兼容测试

```powershell
python scripts/compile_source.py "raw/收件箱/grid.md" --root $vault
```

前提：真实文件在 `0 - Inbox/待处理/grid.md`。

期望：命令仍能找到新路径并输出待审稿。

## 审阅合并测试

把 `grid.semantic.md` 的 frontmatter 改为：

```yaml
status: approved
```

运行：

```powershell
python scripts/merge_manual.py "$vault\0 - Inbox\待审\grid.semantic.md" --root $vault
```

检查：

- 内容合并到 `2 - Areas（领域）/投资体系/投资策略手册.md`。
- 旧手册存在时，备份进入 `5 - Archives（归档）/系统备份/review-backups/`。

## 候选项目测试

```powershell
python scripts/candidate_from_draft.py "$vault\0 - Inbox\待审\grid.semantic.md" --root $vault --index 1
```

检查：

- `3 - Projects（项目）/候选/` 下生成候选卡。
- 候选卡包含 `type: candidate`、`status: suggested`、证据来源和最小验证动作。

## Skill 草稿测试

```powershell
python scripts/distill_skill.py "1 - Resources（资源）/概念/资产配置.md" --wiki-root $vault --name asset-allocation
```

检查：

- `4 - Skills（技能）/待审/asset-allocation.md` 存在。
- 草稿包含适用场景、输入条件、判断步骤、输出结果、反例、失效条件、复查周期。

## 问答沉淀测试

```powershell
python scripts/answer_draft.py --root $vault --question "我去香港能做什么？" --answer "基于库内资料，可以整理开户准备和半日行动清单。"
```

检查：

- `0 - Inbox/待审/*.answer.md` 存在。
- 草稿包含 `workflow: answer-review`。
- 草稿包含库内已有、推断建议、外部补充、仍需研究。
- `1 - Resources（资源）/查询/` 不应直接生成正式查询页。

## 迁移测试

构造旧结构：

```text
raw/收件箱/
raw/待审/
raw/论文/
raw/笔记/
raw/资产/
实体/
概念/
对比/
查询/
问题索引/
技能/
候选/
日记/
合成/
_archive/
```

同时构造上一版 0-6 结构：

```text
3 - Resources（资源）/
1 - Projects（项目）/
4 - Archives（归档）/
5 - Templates（模板）/
6 - Daily（日记）/
```

运行：

```powershell
python scripts/migrate_para.py --root <old-vault> --dry-run
python scripts/migrate_para.py --root <old-vault> --apply
```

检查：

- dry-run 只输出 `MIGRATE_PLAN`，不移动文件。
- apply 输出 `MIGRATE_OK`。
- 文件进入 0-7 结构。
- 旧空目录被清理。
- manifest、frontmatter `sources`、`target_path`、显式 wikilink 路径被更新。

## 工作流人工验收

投入一篇复杂文章到 `0 - Inbox/待处理/`：

- 检查是否生成待审稿、Source Coverage Map 和 Impact Review。
- 审阅通过后，知识点进入 Resources，手册进入 Areas，原文进入 Archives。
- 多个 Resources 能汇总到 Areas。
- 只有高价值机会进入 Projects 候选。
- 稳定判断框架进入 Skills 待审。
- 回答用户问题时优先基于已保存资料，而不是泛泛外部常识。
- 问答沉淀只生成待审稿，不直接写正式查询页。

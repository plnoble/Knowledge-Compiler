# Loop 与维护

只在健康检查、维护、研究议程、知识老化、命令排障时读取本文件。

## 四个循环

### Loop 1 引用追踪

`build_hot_cache.py` 统计 wikilink 入链，更新 `_meta/hot.md`，展示最常被引用页面。高被引页面优先深化或蒸馏为 Skill。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh cache
```

### Loop 2 Skill 成熟度

新知识加入后，判断是否会改变既有 Skill 的规则。`health_check.py` 会提示 30 天未更新的 Skill。

### Loop 3 研究议程

`auto_research.py` 扫描 WIP、稀少页面、悬挂引用和高被引低上下文页面，生成 `_meta/research-agenda.md`。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh auto-research
sh /var/minis/skills/wiki-kb/scripts/wiki.sh research-status
```

### Loop 4 知识老化

`health_check.py` 扫描 `confidence: high` 且超过 90 天未更新的页面。复查后选择：

- 仍有效：更新 `updated`。
- 部分过时：降低 `confidence` 并说明。
- 被推翻：添加 `[!矛盾]` 标注并链接新来源。

## 健康检查项目

按优先级检查：

1. 热缓存时效。
2. 未解决矛盾。
3. 收件箱积压。
4. 审阅积压。
5. P-index 覆盖率。
6. Skill 活跃度。
7. 知识老化。
8. 断链。
9. Frontmatter 完整性。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh health
sh /var/minis/skills/wiki-kb/scripts/wiki.sh health-save
```

## 维护命令

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh fix
sh /var/minis/skills/wiki-kb/scripts/wiki.sh maintain
sh /var/minis/skills/wiki-kb/scripts/wiki.sh confidence
sh /var/minis/skills/wiki-kb/scripts/wiki.sh contradiction
sh /var/minis/skills/wiki-kb/scripts/wiki.sh graph
sh /var/minis/skills/wiki-kb/scripts/wiki.sh moc
sh /var/minis/skills/wiki-kb/scripts/wiki.sh p-index --generate
sh /var/minis/skills/wiki-kb/scripts/wiki.sh review-stale
sh /var/minis/skills/wiki-kb/scripts/wiki.sh all
```

当前实现边界：

- `fix_health.py` 是保守修复器：补齐必要目录和 frontmatter，断链只报告，不自动改写。
- `maintain.py` 补齐缺失的 `sources: []` 并报告入链最高页面。
- `check_confidence.py` 生成 `_meta/confidence-report.md`，可用 `--fix` 回填缺失的 `confidence`。
- `build_graph.py` 生成 `_meta/graph.json` 和 `_meta/graph.html`。
- `build_moc.py` 生成 `index.md`。
- `init_vault.py` 创建标准目录、`SCHEMA.md`、`index.md`、`log.md` 和核心 `_meta` 文件。
- `ingest_draft.py` 创建确定性的 `raw/待审/` 草稿，并用 manifest SHA-256 去重。
- `generate_p_index.py` 为未覆盖的概念/实体页生成低风险问题索引种子。
- `review_stale.py` 生成 `_meta/stale-review.md`，只建议保留、降级、合并或归档，不自动删除。
- `smoke_wiki_sh.py` 在有 POSIX `sh` 时验证 `wiki.sh`，无 `sh` 时明确输出 `SMOKE_SKIP`。
- `verify_static.py` 用于技能脚本静态自检，不是用户日常命令。

## 常用验证

在技能仓库中运行：

```bash
python scripts/verify_static.py
python -m unittest tests.test_script_integrity
python scripts/smoke_wiki_sh.py
```

当前 Windows 会话无 `sh` 时，`smoke_wiki_sh.py` 只验证 skip 行为；真实 Minis/iOS 和真实 Obsidian vault 仍需单独验证。

## 后续扩充 Backlog

暂不在本轮实现或仍待目标环境确认：

- 在 Minis/POSIX 环境中跑 `wiki.sh` 真实 smoke test。
- 在一次性真实 vault 中跑 `wiki.sh all`。
- 增加旧英文目录到中文目录的迁移助手。
- 增强语义摄入自动化（例如实体/概念候选自动抽取）。

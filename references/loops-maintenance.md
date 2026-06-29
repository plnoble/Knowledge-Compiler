# Loop 与维护

只在健康检查、维护、研究议程、知识老化、命令排障时读取本文件。

## 四个循环

### Loop 1 引用追踪

`build_hot_cache.py` 统计 wikilink 入链并生成 `_meta/hot.md` 状态仪表盘。高被引页面优先深化、合并进 Area，或蒸馏为 Skill。

```bash
wiki.sh cache --root <vault>
```

## hot.md 状态仪表盘

`_meta/hot.md` 是跨会话状态仪表盘，不是普通笔记。它应显示最近处理记录、待处理与待审积压、活跃 Resources/Areas、未解决冲突、近期重要新连接，以及可能的输入偏科与知识空白。使用时读取它来判断“知识库最近往哪里长”，不要手写维护。

### Loop 2 Skill 成熟度

新知识加入后，判断是否改变 `4 - Skills（技能）/` 中的规则。`health_check.py` 会提示 30 天未更新的 Skill。

### Loop 3 研究议程

`auto_research.py` 扫描 WIP、稀少页面、悬挂引用和高被引低上下文页面，生成 `_meta/research-agenda.md`。研究结果写回 Inbox 后仍需待审。

```bash
wiki.sh auto-research --root <vault>
wiki.sh research-status --root <vault>
```

### Loop 4 知识老化

`health_check.py` 扫描 `confidence: high` 且超过 90 天未更新的页面。复查后选择：

- 仍有效：更新 `updated` 和 `last_verified`。
- 部分过时：降低 `confidence`，并说明失效范围。
- 被推翻：添加 `[!矛盾]` 或移入 `5 - Archives（归档）/过时知识/`。

## 健康检查项目

按优先级检查：

1. 热缓存时效。
2. 未解决矛盾。
3. Inbox 积压。
4. 审阅积压。
5. P-index 覆盖率。
6. Skill 活跃度。
7. 知识老化。
8. 断链。
9. Frontmatter 完整性。

```bash
wiki.sh health --root <vault>
wiki.sh health-save --root <vault>
```

## 维护命令

```bash
wiki.sh fix --root <vault>
wiki.sh maintain --root <vault>
wiki.sh confidence --root <vault>
wiki.sh contradiction --root <vault>
wiki.sh graph --root <vault>
wiki.sh moc --root <vault>
wiki.sh p-index --generate --root <vault>
wiki.sh review-stale --root <vault>
wiki.sh all
```

## 当前实现边界

- `init_vault.py` 创建 0-7 目录、`SCHEMA.md`、`index.md`、`log.md` 和核心 `_meta` 文件。
- `convert_to_md.py` 输出到 `0 - Inbox/待处理/`。
- `ingest_draft.py` 输出到 `0 - Inbox/待审/` 并用 manifest SHA-256 去重。
- `compile_source.py` 输出语义待审稿、Source Coverage Map、Impact Review、Relationship Discovery 和摄入后建议追问。
- `migrate_para.py` 是一次性旧目录迁移助手，不是长期知识处理模式。
- `fix_health.py` 是保守修复器：补齐必要目录和 frontmatter，断链只报告。
- `generate_p_index.py` 为未覆盖的概念/实体生成低风险问题索引种子。
- `review_stale.py` 只建议保留、降级、合并或归档，不自动删除。

## 常用验证

```bash
python scripts/verify_static.py
python -m unittest tests.test_script_integrity
python scripts/smoke_wiki_sh.py
```

## Backlog

- 真实 Minis/POSIX 验证。
- 真实 Obsidian vault 验证。
- vault 初始化/迁移助手增强。
- Inbox 自动抽取实体、概念、对比、问题的能力增强。

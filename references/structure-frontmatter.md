# 目录与 Frontmatter

只在需要创建、迁移、检查页面结构时读取本文件。

## Wiki 根目录

默认根目录：`/var/minis/mounts/wiki/`

脚本会优先使用 `WIKI_ROOT`，其次检测 Minis 挂载点、本地 `~/wiki`、当前目录。标准路径定义见 `scripts/wiki_dirs.py`。

## 必要目录

```text
wiki/
├── SCHEMA.md
├── index.md
├── log.md
├── _meta/
│   ├── hot.md
│   ├── manifest.json
│   ├── research-agenda.md
│   ├── health-report.md
│   ├── confidence-report.md
│   └── graph.html
├── raw/
│   ├── 收件箱/
│   ├── 待审/
│   ├── 已归档/
│   ├── 论文/
│   ├── 笔记/
│   └── 资产/
├── 实体/
├── 概念/
├── 对比/
├── 合成/
├── 查询/
├── 问题索引/
├── 技能/
│   └── 待审/
├── 候选/
├── 日记/
└── _archive/
```

## 领域边界

- AI 与自动化：智能代理、LLM、知识管理、工具平台。
- 投资体系：指数基金、ETF、资产配置、估值、投资心理。
- 领域外内容不加工；告知用户原因并建议是否放入日记或普通笔记。

## 通用 Frontmatter

```yaml
---
title: "页面标题"
created: 2026-06-26
updated: 2026-06-26
type: <entity|concept|comparison|skill|candidate|query|synthesis|journal|question|source|research>
tags:
  - <领域标签>
  - <类型标签>
status: <seed|developing|mature|evergreen|approved|review|incubating|researching|收件箱>
related:
  - "[[相关页面]]"
sources:
  - "[[raw/收件箱/来源文件.md]]"
confidence: <high|medium|low|quarantine>
---
```

语义编译待审稿补充字段：

```yaml
workflow: semantic-compile
domain: <投资体系|AI与自动化|香港与出行|知识管理>
target_path: 合成/<手册名>.md
merge_mode: <append-section|update-section>
review_decision: <pending|approved|rejected>
inbox_source: raw/收件箱/<source>.md
source_hash: sha256:<hash>
```

手册页补充字段：

```yaml
type: synthesis
validity: <evergreen|time-sensitive|mixed>
last_verified: 2026-06-26
review_after: 2026-09-24
superseded_by:
  - "[[新页面]]"
```

## 类型补充字段

概念页：

```yaml
complexity: <basic|intermediate|advanced>
domain: <AI与自动化|投资体系|知识管理>
aliases: [别名1, 别名2]
```

实体页：

```yaml
entity_type: <person|organization|product|index|fund>
role: "在知识库领域中的角色"
```

Skill 页：

```yaml
domain: <investment|ai-automation|knowledge-management>
falsifiable: true
```

候选卡：

```yaml
candidate_kind: <software|trip|workflow|research>
evidence_count: 1
linked_knowledge: []
personal_fit: <low|medium|high>
validation_cost: <low|medium|high>
status: <suggested|incubating|merged|active|rejected>
```

问题索引页：

```yaml
---
title: "如何判断ETF是否高估？"
type: question
created: 2026-06-26
related:
  - "[[概念/ETF估值方法]]"
answer_quality: <draft|solid|definitive>
---
```

## 命名规则

- 目录名使用中文。
- 普通知识页文件名优先英文小写连字符，例如 `etf-valuation.md`。
- Skill 文件名可中文，但保持简洁。
- 创建页面前先查 `index.md` 和相关目录，已有同主题页面则更新，不重复创建。

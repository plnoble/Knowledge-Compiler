# 目录与 Frontmatter

只在需要创建、迁移或检查页面结构时读取本文件。

## 标准目录

```text
0 - Inbox/
  待处理/
  待审/
1 - Resources（资源）/
  实体/
  概念/
  对比/
  查询/
  问题索引/
2 - Areas（领域）/
  投资体系/
  AI与自动化/
  香港行动/
  知识库运营/
3 - Projects（项目）/
  候选/
  活跃项目/
  已暂停/
4 - Skills（技能）/
  待审/
5 - Archives（归档）/
  已归档来源/
  已结束项目/
  过时知识/
  系统备份/
6 - Templates（模板）/
7 - Daily（日记）/
_meta/
SCHEMA.md
index.md
log.md
```

## 流向规则

- 原始资料：`0 - Inbox/待处理/`
- AI 待审稿、Source Coverage Map、候选知识点：`0 - Inbox/待审/`
- 知识点：`1 - Resources（资源）/`
- 领域手册：`2 - Areas（领域）/`
- 项目机会：`3 - Projects（项目）/候选/`
- 技能/判断框架：`4 - Skills（技能）/待审/`
- 已处理原文：`5 - Archives（归档）/已归档来源/`
- 日记：`7 - Daily（日记）/`
- 模板：`6 - Templates（模板）/`

## 通用 Frontmatter

```yaml
---
title: 页面标题
created: 2026-06-27
updated: 2026-06-27
type: entity | concept | comparison | synthesis | query | skill | candidate | question | source | source-coverage | journal
status: pending | researching | review | approved | rejected | suggested | active | paused | archived | stale
tags: []
sources: []
confidence: low | medium | high | quarantine
---
```

## 来源字段

不要再用文件夹区分论文、笔记、资产。统一放入 Inbox，并用：

```yaml
source_kind: article | paper | note | screenshot | pdf | image | transcript | other
inbox_source: 0 - Inbox/待处理/<source>.md
source_hash: sha256:<hash>
```

## 语义编译待审稿

```yaml
workflow: semantic-compile
domain: 投资体系 | AI与自动化 | 香港行动 | 知识库运营
target_path: 2 - Areas（领域）/<领域>/<手册>.md
merge_mode: append-section | update-section
review_decision: pending | approved | rejected
```

待审稿必须同时配套 Source Coverage Map：

```text
原文要点 | 是否沉淀 | 目标 Resource | 未处理原因
```

## 候选项目字段

```yaml
candidate_kind: software | trip | workflow | research
evidence_count: 1
linked_knowledge: []
personal_fit: low | medium | high
validation_cost: low | medium | high
status: suggested | incubating | active | rejected | merged
```

候选正文必须包含：解决什么问题、个人匹配度、证据数量、验证成本、潜在价值、下一步最小验证动作、是否已有类似候选。

## 命名规则

- 创建页面前先搜索 `index.md`、`_meta/hot.md` 和相关目录。
- 同主题优先更新旧页，不重复创建浅页面。
- 文件名优先简短、稳定、可搜索。
- 旧路径如 `raw/收件箱/xxx.md` 只作为命令兼容输入，不作为新目录创建。

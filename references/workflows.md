# 工作流细节

只在执行具体加工、审阅、查询、蒸馏、候选、研究、日记或存档任务时读取本文件。

## WF1 摄入

触发例：`加工 raw/收件箱/xxx.md`、`处理这篇文章`、`把这个加入知识库`。

步骤：

1. 读 `_meta/hot.md`、`index.md`，确认上下文和既有页面。
2. 可先运行 `wiki.sh ingest-draft raw/收件箱/xxx.md` 创建 `raw/待审/` 草稿；脚本会检查 `_meta/manifest.json`，同哈希已加工则报告 `already_ingested`。
3. 需要进入知识库时，运行 `wiki.sh compile-source raw/收件箱/xxx.md` 生成语义编译待审稿。
4. 完整读取原文，不跳读。用户说“直接加工”时跳过重点确认。
5. 在 `raw/待审/` 加工草稿，保持 `status: review`，不要绕过审阅。
6. 创建或更新 `实体/`、`概念/`、`对比/`、`合成/` 等知识页。通常 3-8 个高质量页面优于 10 个浅页面。
7. 提炼 2-3 个“这篇能回答什么问题”，写入 `问题索引/`。
8. 若发现冲突，不覆盖旧内容；按矛盾标注规范同时标注相关页面。
9. 更新 `index.md`、`log.md`、`_meta/hot.md`、`_meta/manifest.json`。
10. 汇报创建页数、更新页数、矛盾数、问题索引数。

脚本入口：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh init --root /var/minis/mounts/wiki
sh /var/minis/skills/wiki-kb/scripts/wiki.sh ingest-draft raw/收件箱/xxx.md
sh /var/minis/skills/wiki-kb/scripts/wiki.sh compile-source raw/收件箱/xxx.md
```

摄入日志格式：

```markdown
## [2026-06-26] 摄入 | 文章标题
- 来源：`raw/收件箱/filename.md`
- 创建：[[概念/XXX]]、[[实体/YYY]]
- 更新：[[概念/ZZZ]]
- 问题索引：[[问题索引/如何判断XXX]]
- 发现矛盾：[[概念/AAA]] vs [[概念/BBB]]
- 核心洞见：一句话总结最重要的新知识
```

## WF2 审阅

用户在 Obsidian 中编辑 `raw/待审/xxx.md`，然后改 frontmatter：

- `status: approved`：运行 `wiki.sh review` 后移入目标目录，原文归档，更新 `index.md` 和 manifest。
- `status: rejected`：在底部添加 `## 退回原因`；运行 `wiki.sh review` 后重置为 `status: review` 并添加重生成提示。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh review
```

## WF3 查询

触发例：用户提出任何知识库相关问题。

步骤：

1. 读 `_meta/hot.md`。
2. 读 `index.md`。
3. 检查 `问题索引/` 是否直接命中。
4. 读 3-5 个相关知识页。
5. 回答时使用 `[[页面名]]` 引用来源。
6. 若回答超过 3 句话且有长期价值，询问是否存入 `查询/` 或 `合成/`。

## WF4 Skill 蒸馏

触发例：`蒸馏技能`、`提炼判断框架`、`生成 skill`。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh skill 概念/资产配置.md 实体/巴菲特.md
```

质量标准：

- 规则必须可证伪，有条件、阈值或可验证信号。
- 写清适用场景和不适用场景。
- 避免“长期持有”“要有耐心”这类无法指导决策的句子。
- 草稿进入 `技能/待审/`，用户审阅后改 `status: approved`。

## WF5 候选项目

触发例：`候选项目`、`生成候选卡`、`孵化这个想法`。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh candidate 概念/XXX.md --name "项目名称"
sh /var/minis/skills/wiki-kb/scripts/wiki.sh candidate --idea "构建一个自动整理知识库的工具"
```

候选卡写入 `候选/`，包含核心问题、知识支撑、待验证假设、初步研究议程。

语义待审稿中的候选建议先保持 `status: suggested`。用户批准后运行：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh candidate-from-draft raw/待审/xxx.semantic.md --index 1
```

不要把每个灵感都直接变成候选卡；优先保留与个人兴趣匹配、证据可追踪、验证成本明确的候选。

## WF5b 手册合并

语义待审稿批准后，才能合并到 `合成/` 手册页：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh merge-manual raw/待审/xxx.semantic.md
```

合并前必须备份旧手册到 `_archive/review-backups/`。手册不做无序追加；每次合并要保留来源、摘要、更新建议和风险边界。

## WF6 Deep Research

触发例：`深度研究`、`联网研究`、`研究一下`。

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh research "研究主题"
```

脚本负责生成议程、接收搜索结果、写入 `raw/收件箱/`。联网搜索本身由 Minis 原生能力完成。研究报告入箱后，用户再说“加工这篇”进入 WF1。

## WF7 日记提炼

命令：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh journal
sh /var/minis/skills/wiki-kb/scripts/wiki.sh journal --list
sh /var/minis/skills/wiki-kb/scripts/wiki.sh journal --extract
```

日记是用户自由写作空间。只有用户明确说“从日记提炼知识 2026-06-26”时，才读取日记并按 WF1 加工。

## WF8 查询存档

用户同意保存高质量回答时，创建 `查询/问题摘要.md`：

```markdown
---
title: 如何判断ETF是否高估
type: query
created: 2026-06-26
related:
  - "[[概念/ETF估值方法]]"
---

# 如何判断ETF是否高估

## 问题
[用户原始问题]

## 回答
[回答]

## 相关知识页
- [[概念/ETF估值方法]]
```

## 矛盾标注

发现冲突时，不静默覆盖，在相关页面添加：

```markdown
> [!矛盾] 与 [[XXX页面]] 的冲突（来源：[[YYY来源]]）
> 本页说：A
> [[XXX页面]] 说：B
> 需要核查。建议：查阅原始来源，或进行 Deep Research。
```

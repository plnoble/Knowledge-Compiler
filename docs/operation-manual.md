# Knowledge Compiler 操作手册

`compile-knowledge` 的目标不是把资料堆进 Obsidian，而是把 Inbox 资料编译成可审阅、可追溯、可合并、可过期复查的个人知识库。

展示名：Knowledge Compiler / 知识编译器。

## 第一原则：只喂入，不整理

你的日常动作只应该是：把值得保存的资料放进 `0 - Inbox/待处理/`，审核 `0 - Inbox/待审/`，批准真正值得进入正式库的结果。分类、拆解、建立链接、提出更新建议、归档和维护由 AI 执行。

`0 - Inbox/待处理/` 与 `5 - Archives（归档）/已归档来源/` 是事实来源层，原文内容不可改写。AI 生成内容不能当作新的外部事实来源循环喂入；有长期价值时，先变成待审稿，再由你批准进入 Resources、Areas、Projects 或 Skills。

## 安装与调用

Codex 技能目录建议使用新名字：

```powershell
git clone https://github.com/plnoble/Knowledge-Compiler.git "$env:USERPROFILE\.codex\skills\compile-knowledge"
```

日常可以直接说：

```text
使用 compile-knowledge，把这篇资料加工成知识库待审稿。
```

显式技能名：

```text
$compile-knowledge 处理 0 - Inbox/待处理/xxx.md
```

脚本入口：

```bash
sh /var/minis/skills/compile-knowledge/scripts/wiki.sh <command> [args]
```

本地 Windows 可直接运行 Python 脚本，或在有 `sh` 的环境中运行 `scripts/wiki.sh`。

## 目录

```text
0 - Inbox/待处理/          # 所有未处理输入
0 - Inbox/待审/            # AI 待审稿、coverage map、影响面审查
1 - Resources（资源）/     # 实体、概念、对比、查询、问题索引
2 - Areas（领域）/         # 投资体系、AI与自动化、香港行动、知识库运营
3 - Projects（项目）/候选/ # 高选择性的项目机会
4 - Skills（技能）/待审/   # 可复用判断框架草稿
5 - Archives（归档）/      # 原文、结束项目、过时知识、系统备份
6 - Templates（模板）/
7 - Daily（日记）/
```

资料类型不用文件夹分开，统一用 frontmatter：

```yaml
source_kind: article | paper | note | screenshot | pdf | image | transcript | other
```

## 初始化

```bash
wiki.sh init --root <vault>
```

初始化会创建 0-7 结构、`SCHEMA.md`、`index.md`、`log.md` 和 `_meta/` 文件。新初始化不会创建旧 `raw/` 目录。

## 旧库迁移

先 dry-run：

```bash
wiki.sh migrate-para --root <vault> --dry-run
```

确认移动计划后 apply：

```bash
wiki.sh migrate-para --root <vault> --apply
```

迁移支持旧 `raw/` 结构、旧中文顶层目录，以及上一版 0-6 编号结构。迁移后会清理空旧目录，不保留 redirect/stub。旧命令里写 `raw/收件箱/xxx.md` 仍会被脚本兼容解析到新 Inbox，但新资料建议直接放 `0 - Inbox/待处理/`。

## 日常加工

把资料放入：

```text
0 - Inbox/待处理/
```

生成普通待审稿：

```bash
wiki.sh ingest-draft "0 - Inbox/待处理/xxx.md" --root <vault>
```

生成语义编译待审稿、Source Coverage Map、Impact Review 和 Relationship Discovery：

```bash
wiki.sh compile-source "0 - Inbox/待处理/xxx.md" --root <vault>
```

输出在：

```text
0 - Inbox/待审/xxx.semantic.md
0 - Inbox/待审/xxx.coverage.md
```

Coverage Map 必须包含：

```text
原文要点 | 是否沉淀 | 目标 Resource | 未处理原因
```

Impact Review 必须包含：可能新增/更新的 Resources、可能影响的 Areas/Projects/Skills、冲突或过时内容、不更新原因、仍需研究的问题。Relationship Discovery 必须补充：可连接的已有页面、建议新增 wikilinks、可能形成的知识簇、孤立风险和未来查询入口。

## 摄入后查询闭环

每次完成一篇资料的语义编译后，至少提出 1 个和个人知识库相关的问题，例如“这篇资料改变了我对哪个领域的理解？”“它和旧 Resources 有什么冲突？”“以后我会怎么问到它？”。如果答案有长期价值，只生成 `0 - Inbox/待审/*.answer.md`，不直接写入正式查询页。

## 审阅与正式沉淀

在 Obsidian 里审阅 `0 - Inbox/待审/`，确认后把 frontmatter 改为：

```yaml
status: approved
```

合并到领域手册：

```bash
wiki.sh merge-manual "0 - Inbox/待审/xxx.semantic.md" --root <vault>
```

从待审稿生成候选项目：

```bash
wiki.sh candidate-from-draft "0 - Inbox/待审/xxx.semantic.md" --root <vault> --index 1
```

从稳定资源蒸馏 Skill 草稿：

```bash
wiki.sh skill "1 - Resources（资源）/概念/xxx.md" --root <vault>
```

项目候选进入：

```text
3 - Projects（项目）/候选/
```

Skill 草稿进入：

```text
4 - Skills（技能）/待审/
```

## 查询和问答沉淀

查询个人知识库：

```bash
wiki.sh search "关键词" --root <vault>
```

如果一个回答有长期价值，并且用户明确要求保存，创建问答待审稿：

```bash
wiki.sh answer-draft --root <vault> --question "我去香港能做什么？" --answer "基于库内资料..."
```

问答待审稿只进入 `0 - Inbox/待审/`。批准后再进入 `1 - Resources（资源）/查询/`，不要从对话直接写正式查询页。

## 维护

```bash
wiki.sh p-index --generate --root <vault>
wiki.sh health --root <vault>
wiki.sh health-save --root <vault>
wiki.sh graph --root <vault>
wiki.sh moc --root <vault>
wiki.sh cache --root <vault>
wiki.sh all
```

## 五个核心模式

Inbox -> Resources：全而广，高召回，不漏信息。

Resources -> Areas：精而准，形成长期领域手册，不堆摘要。

Resources/Areas -> Projects：少而狠，只保留值得孵化的候选。

Resources/Areas -> Skills：规则化，把稳定判断沉淀成可复用框架。

Knowledge -> Answer -> Review -> Resources/查询：先基于个人库回答，用户明确保存后才生成待审稿。

## 典型例子

理财文章：放入 Inbox，运行 `compile-source`，审阅 coverage map 和 Impact Review；批准后，概念进入 Resources，体系结论合并到 `2 - Areas（领域）/投资体系/投资策略手册.md`。

Codex 技巧：放入 Inbox，编译后合并到 `2 - Areas（领域）/AI与自动化/Codex操作手册.md`；稳定操作步骤可蒸馏到 `4 - Skills（技能）/待审/`。

香港开户/旅游：放入 Inbox，编译后合并到 `2 - Areas（领域）/香港行动/香港行动指南.md`；以后查询时优先基于你保存过且感兴趣的资料回答。

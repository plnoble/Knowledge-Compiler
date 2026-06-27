---
name: compile-knowledge
description: Turn a personal Obsidian vault into a review-gated Knowledge Compiler. Use when Codex/Minis needs to process Inbox material into Resources, roll Resources into Areas, identify project candidates, distill reusable Skills, answer from a personal knowledge base, migrate an old wiki-kb vault, or maintain the 0-7 knowledge pipeline.
---

# Knowledge Compiler / 知识编译器

这是一个个人知识编译流水线，不是资料仓库。用户只负责把资料放进 Inbox；AI 负责高召回加工、审阅流转、资源沉淀、领域汇总、项目机会识别、技能沉淀和个人化问答。

核心流向：

```text
0 - Inbox/待处理
-> 0 - Inbox/待审
-> 1 - Resources（资源）
-> 2 - Areas（领域）
-> 3 - Projects（项目）/候选
-> 4 - Skills（技能）/待审
-> 5 - Archives（归档）/已归档来源
```

正式写入必须经过待审；不要把未批准内容直接污染 Resources、Areas、Projects 或 Skills。

## 启动协议

1. 先确定 vault root；不确定时运行 `wiki.sh init --root <vault>` 或询问用户。
2. 回答或加工前，先读 `_meta/hot.md`、`index.md`、相关 `SCHEMA.md`、Areas、Resources 和个人上下文。
3. 所有外部材料默认进入 `0 - Inbox/待处理/`；资料类型用 frontmatter 表示：

```yaml
source_kind: article | paper | note | screenshot | pdf | image | transcript | other
```

4. 新资料加工结果先进入 `0 - Inbox/待审/`，必须包含待审稿、Source Coverage Map 和 Impact Review / 影响面审查。
5. 用户批准后，才写入正式 Resources、Areas、Projects、Skills 或 Archives。
6. 回答用户问题时先查个人知识库；只有用户明确说“沉淀/保存/记入知识库”时，才创建问答待审稿。

## 目录框架

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

结构、frontmatter 模板和字段细节见 [structure-frontmatter](references/structure-frontmatter.md)。

## 五个核心模式

### 模式 1：Inbox -> Resources，全而广

输入：`0 - Inbox/待处理/`

输出：`0 - Inbox/待审/`

目标是高召回。必须生成 Source Coverage Map：

```text
原文要点 -> 是否沉淀 -> 目标 Resource -> 未处理原因
```

语义待审稿还必须生成 Impact Review：

```text
可能新增的 Resources
可能更新的 Resources
可能影响的 Areas
可能影响的 Projects
可能影响的 Skills
冲突或过时内容
不更新原因
仍需研究的问题
```

脚本可创建语义待审稿和 coverage map；具体 Resource 页面仍由 AI/用户审阅后写入。

### 模式 2：Resources -> Areas，精而准

输入：`1 - Resources（资源）/`

输出：`2 - Areas（领域）/`

目标是长期领域手册，不堆摘要。更新 Areas 时必须区分：

```text
新增结论
更新结论
冲突结论
过时内容
仍需研究的问题
```

### 模式 3：Resources/Areas -> Projects，少而狠

输入：Resources、Areas、已有候选、个人兴趣。

输出：`3 - Projects（项目）/候选/`

每个候选必须评估解决什么问题、个人匹配度、证据数量、验证成本、潜在价值、下一步最小验证动作、是否已有类似候选。目标是识别值得孵化的项目，不把普通灵感变成项目负担。

### 模式 4：Resources/Areas -> Skills，规则化

输入：稳定 Resources、Areas、反复出现的判断步骤。

输出：`4 - Skills（技能）/待审/`

每个 Skill 必须包含适用场景、输入条件、判断步骤、输出结果、反例、失效条件、复查周期。批准后再移入 `4 - Skills（技能）/` 正式区。

### 模式 5：Knowledge -> Answer -> Review -> Resources/查询

回答问题时先查个人知识库，并在回答中区分：

```text
库内已有
推断建议
外部补充
仍需研究
```

只有用户明确要求保存时，才把高价值问答整理到 `0 - Inbox/待审/`；批准后再进入 `1 - Resources（资源）/查询/`。

## 命令速查

Minis/Codex 常用入口：

```bash
sh /var/minis/skills/compile-knowledge/scripts/wiki.sh <command> [args]
```

初始化与迁移：

```bash
wiki.sh init --root <vault>
wiki.sh migrate-para --root <vault> --dry-run
wiki.sh migrate-para --root <vault> --apply
```

Inbox 编译：

```bash
wiki.sh convert <file> --root <vault>
wiki.sh ingest-draft "0 - Inbox/待处理/xxx.md" --root <vault>
wiki.sh compile-source "0 - Inbox/待处理/xxx.md" --root <vault>
```

审阅后流转：

```bash
wiki.sh merge-manual "0 - Inbox/待审/xxx.semantic.md" --root <vault>
wiki.sh candidate-from-draft "0 - Inbox/待审/xxx.semantic.md" --root <vault> --index 1
wiki.sh skill "1 - Resources（资源）/概念/xxx.md" --wiki-root <vault>
wiki.sh answer-draft --root <vault> --question "..." --answer "..."
wiki.sh review --root <vault>
```

查询与维护：

```bash
wiki.sh search "关键词" --root <vault>
wiki.sh p-index --generate --root <vault>
wiki.sh health --root <vault>
wiki.sh health-save --root <vault>
wiki.sh graph --root <vault>
wiki.sh moc --root <vault>
wiki.sh cache --root <vault>
wiki.sh all
```

旧路径如 `raw/收件箱/xxx.md`、旧中文顶层目录和上一版 0-6 编号路径仍可作为输入被兼容解析到新版 0-7；新 vault 不再创建旧目录。

## 工作流索引

- WF1 Inbox 编译：处理外部文章、PDF、截图、论文、网页、转录，见 [workflows](references/workflows.md#WF1-Inbox-编译)。
- WF2 审阅流转：批准、退回、归档、合并，见 [workflows](references/workflows.md#WF2-审阅流转)。
- WF3 查询回答：基于个人知识库回答问题，见 [workflows](references/workflows.md#WF3-查询回答)。
- WF4 Resources -> Areas：沉淀领域手册，见 [workflows](references/workflows.md#WF4-Resources---Areas)。
- WF5 Resources/Areas -> Projects：识别候选项目，见 [workflows](references/workflows.md#WF5-ResourcesAreas---Projects)。
- WF6 Resources/Areas -> Skills：沉淀判断框架，见 [workflows](references/workflows.md#WF6-ResourcesAreas---Skills)。
- WF7 Deep Research：只在缺口、冲突、时效风险时触发，见 [workflows](references/workflows.md#WF7-Deep-Research)。
- WF8 日记提炼：只在用户明确要求时处理，见 [workflows](references/workflows.md#WF8-日记提炼)。
- WF9 问答沉淀：保存有长期价值的回答，见 [workflows](references/workflows.md#WF9-问答沉淀)。

维护循环、健康检查和定期复查见 [loops-maintenance](references/loops-maintenance.md)。

领域细则按需读取：

- 投资体系：[domain-investment](references/domain-investment.md)
- AI 与自动化：[domain-ai-tools](references/domain-ai-tools.md)
- 香港行动：[domain-hong-kong](references/domain-hong-kong.md)

## 禁令

- 不把 Inbox 原文直接当正式知识。
- 不绕过 `0 - Inbox/待审/` 直接写正式库。
- 不把每个灵感都变成项目候选。
- 不为每篇资料自动 Deep Research；只在缺口、冲突、时效风险或多次重复主题时触发。
- 不用文件夹区分论文、笔记、资产；统一进 Inbox，用 `source_kind` 表示类型。
- 不保留迁移后的旧目录 redirect/stub；旧路径只通过脚本兼容映射解析。

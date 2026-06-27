# 工作流细节

只在执行加工、审阅、查询、领域汇总、候选识别、技能沉淀、研究、日记或问答沉淀任务时读取本文件。

## WF1 Inbox 编译

触发例：`加工 0 - Inbox/待处理/xxx.md`、`处理这篇文章`、`把这个加入知识库`。

步骤：

1. 读 `_meta/hot.md`、`index.md`、相关已有 Resources/Areas。
2. 运行 `wiki.sh compile-source "0 - Inbox/待处理/xxx.md" --root <vault>` 生成语义待审稿和 Source Coverage Map。
3. 完整读取原文；不要只看摘要。
4. 以高召回提取实体、概念、对比、问题、操作步骤、风险、反例、时效信息和候选机会。
5. 所有结果先留在 `0 - Inbox/待审/`，保持 `status: review`。
6. Source Coverage Map 必须覆盖原文主要要点，标出是否已沉淀、目标 Resource 和未处理原因。
7. 语义待审稿必须包含 Impact Review / 影响面审查：可能新增或更新的 Resources、影响的 Areas/Projects/Skills、冲突或过时内容、不更新原因、仍需研究的问题。
8. 汇报创建的待审项、覆盖不足、冲突和需要用户判断的点。

命令：

```bash
sh /var/minis/skills/compile-knowledge/scripts/wiki.sh compile-source "0 - Inbox/待处理/xxx.md" --root <vault>
```

旧输入 `raw/收件箱/xxx.md` 会被脚本兼容解析到新 Inbox，但新资料应放新路径。

## WF2 审阅流转

用户或 AI 审阅 `0 - Inbox/待审/` 中的草稿。

- `status: approved`：可以合并到目标手册、生成候选卡、进入正式 Resources、创建 Skills，或归档来源。
- `status: rejected`：补充退回原因，不写正式库。
- 原始来源在完成处理后归档到 `5 - Archives（归档）/已归档来源/`。

常用命令：

```bash
wiki.sh ingest-draft "0 - Inbox/待处理/xxx.md" --root <vault>
wiki.sh review --root <vault>
wiki.sh merge-manual "0 - Inbox/待审/xxx.semantic.md" --root <vault>
wiki.sh candidate-from-draft "0 - Inbox/待审/xxx.semantic.md" --root <vault> --index 1
```

## WF3 查询回答

触发例：用户问“我去香港能做什么”“我的网格策略资料怎么理解”“Codex 怎么操作”。

步骤：

1. 读 `_meta/hot.md`。
2. 搜索 `index.md`、`1 - Resources（资源）/问题索引/` 和相关 Resources。
3. 必要时读对应 Area 手册。
4. 回答只基于用户知识库和明确标注的外部补充。
5. 回答中区分：库内已有、推断建议、外部补充、仍需研究。
6. 有长期价值的回答，先问用户是否“沉淀/保存/记入知识库”；未经确认不写待审稿。

命令：

```bash
wiki.sh search "关键词" --root <vault>
```

## WF4 Resources -> Areas

触发例：`把投资资源总结成体系`、`更新 Codex 操作手册`。

步骤：

1. 搜索相关 Resources 和既有 Area 手册。
2. 区分新增结论、更新结论、冲突结论、过时内容、仍需研究的问题。
3. 不堆摘要；写成可长期维护的手册段落。
4. 有冲突时保留旧结论和新证据，添加 `[!矛盾]` 或研究缺口。
5. 合并前备份旧手册到 `5 - Archives（归档）/系统备份/review-backups/`。

命令：

```bash
wiki.sh merge-manual "0 - Inbox/待审/xxx.semantic.md" --root <vault>
```

## WF5 Resources/Areas -> Projects

触发例：`分析哪些可以做成项目`、`找高价值候选`。

步骤：

1. 读相关 Resources、Areas、已有 `3 - Projects（项目）/候选/` 和 `_meta/personal-context.md`。
2. 合并重复或相似候选，不新增负担。
3. 每个候选必须评估解决什么问题、个人匹配度、证据数量、验证成本、潜在价值、下一步最小验证动作、是否已有类似候选。
4. 只输出少量高质量候选。

命令：

```bash
wiki.sh candidate-from-draft "0 - Inbox/待审/xxx.semantic.md" --root <vault> --index 1
wiki.sh candidate "1 - Resources（资源）/概念/xxx.md" --root <vault> --name "项目名称"
```

## WF6 Resources/Areas -> Skills

触发例：`蒸馏技能`、`提炼判断框架`、`把这个规则化`。

命令：

```bash
wiki.sh skill "1 - Resources（资源）/概念/资产配置.md" --root <vault>
```

质量标准：

- 规则必须可证伪。
- 写清适用场景、输入条件、判断步骤、输出结果、反例、失效条件、复查周期。
- 草稿进入 `4 - Skills（技能）/待审/`。
- 批准后再进入 `4 - Skills（技能）/` 正式区。

## WF7 Deep Research

Deep Research 是缺口触发，不是每篇资料自动触发。

触发条件：

- 资料和旧知识冲突。
- 关键概念缺定义。
- 开户、模型、API、法律、费用、营业时间等有明显时效风险。
- 多篇资料反复出现但 Area 仍无稳定结论。

研究报告写入 `0 - Inbox/待处理/`，之后仍走 WF1。

## WF8 日记提炼

日记在 `7 - Daily（日记）/`，默认不主动处理。只有用户明确要求“从日记提炼知识”时，才读取日记并走 WF1。

```bash
wiki.sh journal --root <vault>
wiki.sh journal --list --root <vault>
wiki.sh journal --extract --root <vault>
```

## WF9 问答沉淀

用户同意保存高质量回答时，创建 `0 - Inbox/待审/<问题摘要>.answer.md`，保留原问题、回答、相关知识页和未确认边界。批准后再进入 `1 - Resources（资源）/查询/`，不要从对话直接写正式查询页。

```bash
wiki.sh answer-draft --root <vault> --question "我去香港能做什么？" --answer "基于库内资料..."
```

发现冲突时，不静默覆盖，在相关页面添加：

```markdown
> [!矛盾] 与 [[相关页面]] 的冲突
> 本页说：A
> 对方说：B
> 需要核查。
```

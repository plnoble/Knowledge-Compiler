---
name: wiki-kb
description: Manage a personal Obsidian wiki-kb for AI/automation, investment, Hong Kong/action planning, and knowledge-management notes using Chinese vault directories, semantic review drafts, manuals, P-index, candidate cards, and Loop Engineering. Use when Codex/Minis needs to ingest external sources, compile raw/收件箱 material into reviewable knowledge updates, query personal knowledge, update manuals, create or promote candidate cards, trigger gap-based Deep Research, run health/maintenance/search tools, or edit this wiki-kb skill and scripts.
---

# wiki-kb v3

> Wiki 才是产品，对话只是界面。好的回答不要消失在聊天记录里；把可复用知识编译进 Wiki。

## Start Here

每次处理真实知识库任务时先做：

1. 读 `_meta/hot.md`，了解近期状态。
2. 读 `index.md`，避免重复创建页面。
3. 只读取当前任务需要的 3-5 个相关页面。
4. 结束前更新 `_meta/hot.md`，并在需要时更新 `index.md`、`log.md`、manifest。

如果要创建页面、检查目录或写 frontmatter，读 [目录与 Frontmatter](references/structure-frontmatter.md)。

如果要执行摄入、审阅、查询、Skill 蒸馏、候选卡、研究或日记提炼，读 [工作流细节](references/workflows.md)。

如果要维护、健康检查、研究议程、知识老化或排查命令，读 [Loop 与维护](references/loops-maintenance.md)。

处理领域资料时按需读取：投资读 [投资体系 Playbook](references/domain-investment.md)；Codex/AI 工具读 [AI 与 Codex 工具 Playbook](references/domain-ai-tools.md)；香港/出行读 [香港与出行 Playbook](references/domain-hong-kong.md)。

## Core Rules

- `raw/` 是原始来源区；不要修改或删除原文。加工结果写入 `raw/待审/` 或知识页。
- 创建页面前查 `index.md` 和目标目录；同主题页面优先更新，不重复创建。
- 质量优先；一篇文章宁可沉淀 3 个扎实页面，不要铺 10 个浅页面。
- 遇到新旧信息冲突，不覆盖旧结论；用 `[!矛盾]` 标注，详见 `references/workflows.md`。
- 输出给用户的回答若有长期价值，询问是否存入 `查询/` 或 `合成/`。
- 目录、标签、正文优先中文；普通文件名优先英文小写连字符。
- 脚本接口以 `scripts/wiki.sh` 为准；不要凭旧文档猜命令。

## Command Surface

在 Minis 中通常使用：

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh <command> [args]
```

在本地仓库调试可直接运行：

```bash
python scripts/verify_static.py
python -m unittest tests.test_script_integrity
python scripts/smoke_wiki_sh.py
```

常用命令：

```bash
# 会话与维护
wiki.sh init --root <vault>
wiki.sh cache
wiki.sh health
wiki.sh health-save
wiki.sh all

# 摄入周边
wiki.sh ingest-draft raw/收件箱/xxx.md
wiki.sh compile-source raw/收件箱/xxx.md
wiki.sh review
wiki.sh convert <文件>

# 查询与导航
wiki.sh search "关键词"
wiki.sh graph
wiki.sh moc
wiki.sh p-index
wiki.sh p-index --generate

# Loop 工具
wiki.sh auto-research
wiki.sh research-status
wiki.sh research "主题"

# 沉淀与孵化
wiki.sh skill 概念/xxx.md
wiki.sh candidate 概念/xxx.md --name "项目名称"
wiki.sh candidate --idea "想法文字"
wiki.sh candidate-from-draft raw/待审/xxx.semantic.md --index 1
wiki.sh merge-manual raw/待审/xxx.semantic.md

# 日记
wiki.sh journal
wiki.sh journal --list
wiki.sh journal --extract
wiki.sh review-stale
```

## Workflow Index

### WF1 摄入

用于“加工文章、录入知识库、保存到知识库”。先把原文编译成语义待审稿，再由用户批准知识页、手册、P-index、候选卡或研究缺口。细节见 [工作流细节](references/workflows.md#WF1-摄入)。

### WF2 审阅

用户在 Obsidian 中把待审稿改为 `status: approved` 或 `status: rejected`，然后运行 `wiki.sh review`。通过后进入目标目录；退回后等待重生成。细节见 [工作流细节](references/workflows.md#WF2-审阅)。

### WF3 查询

用于“知识库查询、问已有知识”。先读 hot cache 和 index，再读少量相关页，回答时引用 `[[页面名]]`。细节见 [工作流细节](references/workflows.md#WF3-查询)。

### WF4 Skill 蒸馏

用于“蒸馏技能、提炼判断框架、生成 skill”。生成草稿到 `技能/待审/`，规则必须可证伪、有适用边界。细节见 [工作流细节](references/workflows.md#WF4-Skill-蒸馏)。

### WF5 候选项目

用于“候选项目、生成候选卡、孵化这个想法”。语义摄入先生成候选建议，用户批准后再输出到 `候选/`，聚焦核心问题、知识支撑和待验证假设。细节见 [工作流细节](references/workflows.md#WF5-候选项目)。

### WF6 Deep Research

用于“深度研究、联网研究、研究一下”。脚本生成议程和接收结果，联网搜索由 Minis 原生能力完成，报告写入 `raw/收件箱/` 后再走摄入。细节见 [工作流细节](references/workflows.md#WF6-Deep-Research)。

### WF7 日记

用于“日记、写日记、从日记提炼知识”。日记默认不主动处理；用户明确要求提炼时才读日记并走摄入。细节见 [工作流细节](references/workflows.md#WF7-日记提炼)。

### WF8 查询存档

用于把高质量回答存入 `查询/` 或 `合成/`。先询问用户，再创建页面。细节见 [工作流细节](references/workflows.md#WF8-查询存档)。

### WF9 健康与维护

用于“健康检查、知识库检查、维护、知识老化、研究议程”。运行 `wiki.sh health` 或相关维护命令。细节见 [Loop 与维护](references/loops-maintenance.md)。

## Initialization Check

首次使用或用户说“初始化/检查 wiki-kb”时：

1. 检查 wiki 根目录可访问。
2. 检查必要目录存在；目录清单见 [目录与 Frontmatter](references/structure-frontmatter.md)。
3. 若 `_meta/hot.md` 不存在，运行 `wiki.sh cache`。
4. 读取 `SCHEMA.md`。
5. 向用户报告知识页数量、收件箱数量、待审数量，并提示可运行“健康检查”。

## Maintenance Boundaries

已验证的测试覆盖 init、ingest-draft、compile-source、candidate-from-draft、merge-manual、review-stale、search、graph、moc、P-index、confidence、fix、maintain、contradiction、convert、packaging metadata。当前 Windows 会话无 `sh`，`smoke_wiki_sh.py` 只验证到 `SMOKE_SKIP`；仍需在真实 Minis/POSIX 和真实 Obsidian vault 中验证 `wiki.sh`。

`fix_health.py` 当前是保守修复器：补目录和 frontmatter，断链只报告，不自动改写。

## Backlog

暂不在本轮实现：

- 真实 Minis/POSIX 环境 smoke test。
- vault 初始化/迁移助手。
- 更强的语义抽取和自动合并建议。
- 发布打包元数据和安装体验。

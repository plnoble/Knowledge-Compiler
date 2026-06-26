# wiki-kb 操作手册

本手册面向日常使用者。`wiki-kb` 的目标不是把所有资料堆进 Obsidian，而是把你主动保存的资料加工成可审阅、可追溯、可合并、可过期复查的个人知识库。

## 1. 安装与启动

### 1.1 作为 Codex 技能安装

把仓库放到 Codex 的技能目录，并保持目录名为 `wiki-kb`：

```powershell
git clone https://github.com/plnoble/wiki-kb.git "$env:USERPROFILE\.codex\skills\wiki-kb"
```

之后在 Codex 里直接说：

```text
使用 wiki-kb，帮我处理这篇资料并沉淀到知识库。
```

如果界面支持显式技能名，也可以说：

```text
$wiki-kb 摄入 raw/收件箱/xxx.md
```

### 1.2 在 Minis/POSIX 环境调用脚本

```bash
sh /var/minis/skills/wiki-kb/scripts/wiki.sh <command> [args]
```

如需指定 Python：

```bash
PYTHON=python sh /var/minis/skills/wiki-kb/scripts/wiki.sh health --root /path/to/vault
```

### 1.3 初始化 Obsidian vault

新 vault 不需要手动改名目录，直接运行：

```bash
sh scripts/wiki.sh init --root /path/to/vault
```

它会创建中文目录、`index.md`、`SCHEMA.md`、`log.md`、`_meta/manifest.json`、`_meta/personal-context.md` 等基础文件。

已有旧 vault 目前还没有自动迁移助手。不要在主库里一键批量改名；建议先新建一个测试 vault，用 `init` 建好结构，再手动小批量迁移旧内容。

## 2. 日常知识加工闭环

推荐闭环：

1. 把外部资料放入 `raw/收件箱/`。
2. 运行 `compile-source` 生成语义待审稿。
3. 在 Obsidian 里审阅 `raw/待审/` 的草稿。
4. 把 frontmatter 的 `status` 改成 `approved` 或 `rejected`。
5. 需要合并手册时运行 `merge-manual`。
6. 需要候选项目时运行 `candidate-from-draft`。
7. 定期运行 `health`、`cache`、`p-index --generate`、`review-stale`。

核心原则：

- `raw/` 是原文区，不改原文，不删原文。
- AI 和脚本先生成待审稿，不直接覆盖正式知识页。
- 同主题优先更新旧页，不重复创建碎片页。
- 投资内容只沉淀框架、条件、风险和检查清单，不输出买卖建议。
- 有时效性的内容写清 `last_verified` 和 `review_after`。

## 3. 功能总览

### 初始化与结构

```bash
wiki.sh init --root <vault>
```

用途：创建 wiki-kb 目录结构和基础元数据。

适合：第一次使用、创建测试 vault、检查新库骨架。

### 转换与摄入

```bash
wiki.sh convert <file> --root <vault>
wiki.sh ingest-draft raw/收件箱/xxx.md --root <vault>
wiki.sh compile-source raw/收件箱/xxx.md --root <vault>
```

`convert` 将 PDF/HTML/TXT/Markdown 转成 `raw/收件箱/` Markdown。

`ingest-draft` 生成普通待审稿，并用 SHA-256 做去重。

`compile-source` 生成语义待审稿，包含领域判断、手册目标、P-index 问题、Deep Research 缺口、候选卡建议和风险边界。

### 审阅与合并

```bash
wiki.sh review --wiki-root <vault>
wiki.sh merge-manual raw/待审/xxx.semantic.md --root <vault>
wiki.sh candidate-from-draft raw/待审/xxx.semantic.md --root <vault> --index 1
```

`review` 处理 `status: approved/rejected` 的普通待审稿。

`merge-manual` 把已批准语义稿追加合并到 `target_path` 指定的手册，并在 `_archive/review-backups/` 备份旧手册。

`candidate-from-draft` 将语义稿里的候选建议提升为 `候选/` 卡片，默认状态为 `suggested`。

### 查询与导航

```bash
wiki.sh search "关键词" --root <vault> --limit 10
wiki.sh graph --root <vault>
wiki.sh moc --root <vault>
wiki.sh cache --wiki-root <vault>
wiki.sh p-index
wiki.sh p-index --generate --root <vault> --limit 20
```

`search` 做本地全文搜索。

`graph` 生成图谱数据。

`moc` 更新 `index.md` 导航。

`cache` 更新 `_meta/hot.md`，让 AI 快速知道近期状态。

`p-index --generate` 为缺少问题入口的概念/实体生成轻量问题页。

### 维护与治理

```bash
wiki.sh health --root <vault>
wiki.sh health-save --root <vault>
wiki.sh fix --root <vault> --dry-run
wiki.sh maintain --root <vault> --dry-run
wiki.sh confidence --root <vault>
wiki.sh contradiction --root <vault> --save
wiki.sh review-stale --root <vault>
wiki.sh all
```

`health` 检查结构、frontmatter、链接、热缓存、P-index、研究议程等。

`fix` 是保守修复器：补目录和低风险 frontmatter，断链只报告。

`maintain` 批量补齐维护字段。

`confidence` 审计可信度字段。

`contradiction` 汇总矛盾标注。

`review-stale` 生成过期复查报告，不自动删除或归档。

`all` 运行标准维护流水线。第一次用在主库前，先在测试 vault 跑。

### Deep Research

```bash
wiki.sh auto-research --root <vault>
wiki.sh research-status --root <vault>
wiki.sh research "研究主题" --wiki-root <vault>
wiki.sh research "研究主题" --wiki-root <vault> --agenda-only
wiki.sh research "研究主题" --wiki-root <vault> --result-file results.md
```

脚本只生成研究议程、整合研究结果、写入 inbox；联网搜索由 AI/Minis 的原生能力完成。

触发原则：有冲突、有时效风险、有关键缺口、有多次重复但未成体系的问题时才 Deep Research，不是每篇资料都自动研究。

### Skill 蒸馏与候选项目

```bash
wiki.sh skill 概念/xxx.md --wiki-root <vault> --name "skill-name"
wiki.sh skill --list-candidates --wiki-root <vault>
wiki.sh candidate 概念/xxx.md --wiki-root <vault> --name "项目名"
wiki.sh candidate --idea "想法文字" --wiki-root <vault>
```

`skill` 从高质量知识页蒸馏可复用技能草稿。

`candidate` 从知识页或想法生成候选项目卡，适合把“可行动机会”从知识里分离出来。

### 日记

```bash
wiki.sh journal --wiki-root <vault>
wiki.sh journal --wiki-root <vault> --list
wiki.sh journal --wiki-root <vault> --extract --days 7
```

日记默认是个人记录，不主动加工。只有明确要求提炼时，才从最近日记生成知识建议。

## 4. 三个典型场景

### 理财文章

1. 放入 `raw/收件箱/grid-strategy.md`。
2. 运行 `compile-source`。
3. 审阅语义稿：让 AI 解释网格策略、适用行情、仓位/板块占比、风险和失效条件。
4. 批准后用 `merge-manual` 合入 `合成/投资策略手册.md`。
5. 如果出现工具机会，用 `candidate-from-draft` 生成候选卡。

### Codex 使用技巧

1. 放入 `raw/收件箱/codex-tips.md`。
2. 运行 `compile-source`。
3. 审阅语义稿：用通俗语言解释操作步骤、适用界面、限制、版本日期。
4. 合入 `合成/Codex操作手册.md`。
5. 定期运行 `review-stale`，过时内容进入复查。

### 香港开户/旅游

1. 把开户、交通、行程、购物、签注等资料都放入 `raw/收件箱/`。
2. 分别 `compile-source`，只沉淀与你兴趣相关的步骤和选择。
3. 合入 `合成/香港行动指南.md`。
4. 以后问“我去香港能做什么”，AI 应先查你的 `hot.md`、`index.md` 和相关香港页面，再回答与你资料匹配的行动清单。

## 5. 现在还要不要手动改名

新建 vault：不需要手动改名。运行 `wiki.sh init --root <vault>`。

已有旧 vault：自动迁移助手还没做完。当前安全路径是：

1. 新建测试 vault。
2. 用 `init` 创建新结构。
3. 复制少量旧资料试跑 `compile-source`、`review`、`merge-manual`。
4. 确认路径和 Obsidian 显示正常后，再分批迁移。

AI 使用方式也简化了：你不需要每次背命令。日常可以直接说“使用 wiki-kb，把这篇资料加工成知识库待审稿”，AI 应根据 `SKILL.md` 读取对应 reference，并调用合适命令。

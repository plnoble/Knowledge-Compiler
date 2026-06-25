---
name: wiki-kb
description: 个人 Obsidian 知识库管理。当用户说"知识库"、"wiki"、"采集文章"、"录入知识库"、"整理知识"、"保存到知识库"、"添加到知识库"、"加到wiki"、"知识库健康"、"知识库检查"、"Obsidian笔记"、"学习笔记"、"第二大脑"、"知识库查询"时触发。支持：URL/文本/文件采集 → AI自动分析加工为概念页/实体页/对比页 → 健康检查与维护 → 知识库查询。与 Obsidian vault 完全兼容，通过 iCloud 自动同步。
---

# Wiki 知识库管理

## 位置与结构

Wiki 根目录: `/var/minis/mounts/wiki/`（Obsidian vault，iCloud Drive 自动同步，Minis 修改后 Obsidian 端即时可见）

```
wiki/
├── SCHEMA.md          # 规范（页面规则、标签分类，首次操作前必读）
├── index.md           # 内容目录（按类型分类，每页一行摘要）
├── log.md             # 操作日志（仅追加）
├── raw/               # 原始来源（不可变，加工后不改不删）
│   ├── articles/      # 网页文章（待加工 inbox）
│   ├── processed/     # 已加工文章（归档，仍可引用）
│   ├── papers/        # PDF/论文
│   ├── transcripts/   # 笔记/访谈/灵感
│   └── assets/        # 图片/图表
├── entities/          # 实体页面（人、产品、公司、指数）
├── concepts/          # 概念页面（理论、方法、策略）
├── comparisons/       # 对比分析
├── queries/           # 查询结果
├── synthesis/         # 合成页（查询回答回填）
├── _archive/          # 归档内容
└── _meta/             # 元信息（健康报告、图谱、缓存等）
```

**领域**: AI 与自动化（智能代理、LLM、知识管理、工具平台）+ 投资体系（指数基金、ETF、资产配置、估值、投资心理）。领域外内容不加工。

**Obsidian 链接解析**: `[[]]` 跨目录解析——`raw/articles/` 和 `raw/processed/` 中的文章均可被 `[[文章标题]]` 直接引用，无需移动文件。

**首次操作前**: 读一遍 `SCHEMA.md` 了解标签分类和页面规则。

### 快捷命令

```bash
S=/var/minis/skills/wiki-kb/scripts
sh $S/wiki.sh health          # 健康检查
sh $S/wiki.sh fix             # 自动修复
sh $S/wiki.sh maintain        # 批量维护（sources 字段）
sh $S/wiki.sh search "ETF"    # BM25 搜索
sh $S/wiki.sh all             # 全量维护（一键执行全部）
sh $S/wiki.sh                 # 查看所有命令
```

---

## 工作流 1：采集 (Ingest)

将外部资源存入 `raw/` 对应目录。

### URL → 文章

1. 用 `web-content-extractor` 技能提取网页正文为 Markdown
2. 生成文件名：取文章标题，空格→连字符
3. 检查 `raw/articles/` 和 `raw/processed/` 是否已有同名文件，有则跳过
4. 保存到 `raw/articles/文件名.md`
5. 立即进入工作流 2（加工）

### 加工完成后

加工完毕，将文章从 `raw/articles/` 移到 `raw/processed/`：
```bash
mv raw/articles/文章名.md raw/processed/
```
这样 `raw/articles/` 始终只保留待加工的新文章（inbox），`raw/processed/` 归档已处理内容。

### 文本 → 笔记

1. 用户直接提供文本内容
2. 简要命名，保存到 `raw/transcripts/文件名.md`
3. 进入加工流程

### 文件

1. 用户提供文件路径
2. 按类型复制到 `raw/` 子目录：
   - `.md`/`.txt` → `raw/articles/`
   - `.pdf` → 先用 `convert_to_md.py` 转换为 Markdown，再存入 `raw/articles/`
   - `.png`/`.jpg`/`.webp` → `raw/assets/`
3. PDF 转换：`python3 scripts/convert_to_md.py <file.pdf>`
4. 进入加工流程

---

## 工作流 2：加工 (Process)

分析 raw 内容，创建或更新知识页面。这是核心流程。

### 步骤

1. **读取** raw 文章全文
2. **识别** 文章中的实体（人、产品、公司、指数）和概念（理论、方法、策略）
3. **查重** — 对每个识别项，用 `ls entities/ concepts/` 检查是否已有同名页面
4. **决策**（按 SCHEMA 阈值）：
   - 已有页面 + 新信息 → **更新**该页面，追加内容，更新 `updated` 日期和 `sources`
   - 2+ 来源提及 or 对该来源是核心内容 → **创建**新页面
   - 仅提及/次要细节/超出领域 → **跳过**
5. **编写页面** — 遵循页面模板（见下方），每页至少 2 个 `[[wikilink]]` 出站链接
6. **更新 index.md** — 对应分类下添加 `- [[page-name]] - 一行摘要`
7. **追加 log.md** — 格式见下方

### 页面命名

小写、连字符、无空格、无中文（如 `asset-allocation`、`etf`、`greed-fear`）

### 标签

从 SCHEMA.md 标签分类中选取。如需新标签，先在 SCHEMA.md 的 Tag Taxonomy 添加。

### 加工原则

- **提取精华**，不是复制粘贴。用自己的话总结，保留关键数据和逻辑链
- **交叉链接**。新页面至少链接 2 个相关页面；同时检查被链接页面是否需要反向链接回来
- **标注来源**。frontmatter `sources` 字段填写 raw 文件路径（必填！零幻觉强制）
- **标注置信度**。frontmatter `confidence` 字段根据来源数量和内容质量填写
- **冲突处理**。新信息与已有内容矛盾时，保留两者并标注日期，frontmatter 加 `contradictions: [page-name]`
- **零幻觉**。每个声明必须可追溯到 raw 来源。无法找到来源的声明标注 `<!-- 待验证 -->` 或移除

### log.md 格式

```
## [YYYY-MM-DD] 操作标题
- 操作内容1
- 操作内容2
- 新增页面: [[page1]], [[page2]]
- 更新页面: [[page3]]
```

---

## 工作流 3：维护 (Maintain)

### 健康检查

```bash
python3 /var/minis/skills/wiki-kb/scripts/health_check.py
```

保存报告到 `_meta/`：
```bash
python3 /var/minis/skills/wiki-kb/scripts/health_check.py > /var/minis/mounts/wiki/_meta/health-report.md
```

检查项：断链、frontmatter 格式、页面大小（>200行）、出站链接数（<2）。
链接验证包含 `raw/articles/` 和 `raw/processed/`（Obsidian 跨目录解析）。

### 知识图谱

```bash
python3 /var/minis/skills/wiki-kb/scripts/build_graph.py
```

生成交互式知识图谱：`_meta/graph.json`（数据）+ `_meta/graph.html`（可视化）。
图谱特性：节点大小=被引用次数、颜色=页面类型、支持搜索/过滤/缩放。

### 会话记忆

```bash
python3 /var/minis/skills/wiki-kb/scripts/build_hot_cache.py
```

生成 `_meta/hot-cache.md`：最近操作、最近修改的页面、知识空白（wip 页面、内容稀少页面）。
**每次会话开始时先读 hot-cache.md**，无需重新扫描全部页面。

### 自主研究

```bash
python3 /var/minis/skills/wiki-kb/scripts/auto_research.py
```

识别知识空白，生成研究议程：`_meta/research-agenda.md`。
分析 wip 页面（按重要性排序）、内容稀少页面、孤儿页面、主题聚类，建议搜索查询。

### MOC 导航页

```bash
python3 /var/minis/skills/wiki-kb/scripts/build_moc.py
```

按主题聚类页面，生成 MOC（Map of Content）导航中心：
- 📊 MOC-投资体系
- 🤖 MOC-AI与自动化
- 🧠 MOC-知识管理
- 🗺️ MOC-知识地图（总入口）

### 多格式转换

```bash
python3 /var/minis/skills/wiki-kb/scripts/convert_to_md.py <file.pdf>
```

支持：PDF（pdftotext）、HTML、TXT。转换后存入 `raw/articles/`，自动跳过已存在的文件。

### 自动修复

```bash
python3 /var/minis/skills/wiki-kb/scripts/fix_health.py
```

修复项：格式补全、断链占位页创建、出站链接补充、超大页面拆分。
脚本预加载所有页面到内存 + 关键词倒排索引，适用于 3000+ 页面的大型知识库。

### 批量维护

```bash
python3 /var/minis/skills/wiki-kb/scripts/maintain.py
```

回填高频被引用页面的 sources 字段（自动匹配 raw/articles/ 和 raw/processed/ 中的原始文件）。

### 置信度检查 + 零幻觉验证

```bash
python3 /var/minis/skills/wiki-kb/scripts/check_confidence.py        # 仅检查
python3 /var/minis/skills/wiki-kb/scripts/check_confidence.py --fix  # 检查 + 自动添加 confidence 字段
```

分析页面来源引用和内容质量，自动判定置信度等级（high/medium/low/quarantine）。
报告保存到 `_meta/confidence-report.md`。

**置信度规则**：
- 🟢 **high**: 2+ 来源、5+ 出站链接、50+ 行正文
- 🟡 **medium**: 1 来源、2+ 出站链接、10+ 行正文
- 🟠 **low**: 0 来源或 <10 行正文
- 🔴 **quarantine**: 0 来源 + wip 或 <3 行正文（隔离，需人工审核）

**零幻觉**：加工时每个声明必须有来源。引用 low 页面需标注"待验证"。禁止引用 quarantine 页面。

### 矛盾检测

```bash
python3 /var/minis/skills/wiki-kb/scripts/detect_contradictions.py
```

扫描 frontmatter 中的 `contradictions` 字段 + 数值声明概览。报告保存到 `_meta/contradiction-report.md`。

加工新内容时，注意与已有页面的数值/观点对比。发现矛盾时：
1. 在相关页面使用 `> [!warning] 矛盾待审` callout 标注
2. frontmatter 加 `contradictions: [page-name]`
3. 较新的来源通常更可靠，但需人工确认

### 修复约定

- **断链** → 创建占位页面，frontmatter 含 `tags: [wip]`，正文为"待补充"
- **格式问题** → 补充 frontmatter 缺失字段（title/created/updated/type/tags）
- **超大页面** → 拆分为 `{name}-part-1`、`{name}-part-2` 子页面，原页面保留为索引页
- **过时内容** → 移至 `_archive/`，从 index.md 移除
- 修复后追加 log.md

---

## 工作流 4：查询 (Query)

### BM25 搜索（推荐）

```bash
python3 /var/minis/skills/wiki-kb/scripts/search_wiki.py "查询词"
python3 /var/minis/skills/wiki-kb/scripts/search_wiki.py "查询词" --limit 20
```

BM25 全文检索，按相关性排序，适用于 1000+ 页面的大型知识库。

### 传统搜索

1. 用 `grep -rl "关键词" entities/ concepts/ comparisons/` 搜索相关页面
2. 读取匹配页面，整合内容生成回答
3. 回答中用 `[[wikilink]]` 引用来源页面
4. 有价值的查询**回填到 wiki**：保存到 `synthesis/页面名.md`（type: synthesis），让探索也产生复利

---

## 页面模板

### Entity（实体）

```markdown
---
title: 标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity
tags: [标签]
sources: [raw/articles/来源.md]
confidence: medium
---

# 标题

概述（1-2 句话说明它是什么）。

## 关键特征
- 要点

## 分类 / 类型
- [[相关实体]] - 简述

## 相关概念
- [[相关概念]]
```

### Concept（概念）

```markdown
---
title: 标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: concept
tags: [标签]
sources: [raw/articles/来源.md]
confidence: medium
---

# 标题

定义（核心概念是什么，为什么重要）。

## 核心要点
### 1. 要点标题
内容。

### 2. 要点标题
内容。

## 实践应用
- 具体操作或案例

## 相关概念
- [[相关概念]]
```

### Comparison（对比）

```markdown
---
title: A vs B
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: comparison
tags: [标签]
sources: [来源列表]
confidence: medium
---

# A vs B

## 对比维度

| 维度 | A | B |
|------|---|---|
| 特征1 | ... | ... |

## 各自优劣
### A
**优势：** ...
**劣势：** ...

## 结论
综合分析。

## 相关概念
- [[相关概念]]
```


### Synthesis（合成页）

```markdown
---
title: 问题标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: synthesis
tags: [synthesis]
sources: []
---

# 问题标题

## 回答

综合多个知识页的回答，引用 [[wikilink]]。

## 引用来源
- [[相关页面1]]
- [[相关页面2]]
```

---

## 规则速查

| 规则 | 说明 |
|------|------|
| 文件名 | 页面：小写连字符无空格；raw：保留原标题 |
| Frontmatter | 每页必须，含 title/created/updated/type/tags |
| 出站链接 | 每页至少 2 个 `[[wikilink]]` |
| 页面大小 | 超过 200 行 → 拆分为 `{name}-part-N` |
| index.md | 新页面必须添加到对应分类 |
| log.md | 每次操作必须追加记录 |
| 标签 | 必须在 SCHEMA.md 标签分类中 |
| raw/ | 不可变，加工后不改不删 |
| 占位页 | `tags: [wip]`，正文"待补充"，后续填充 |
| 链接解析 | `[[]]` 跨目录解析，raw/ 中的文章可直接引用 |

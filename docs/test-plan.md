# wiki-kb 测试方案

本方案覆盖当前所有已实现功能。目标是确认脚本不会回退、命令入口一致、语义闭环可跑通，并明确哪些仍需在真实 Minis/POSIX 和 Obsidian vault 中验证。

## 1. 本地自动化检查

在仓库根目录运行：

```powershell
python -m unittest tests.test_script_integrity
python scripts/verify_static.py
python scripts/smoke_wiki_sh.py
```

预期：

- 单元测试全部通过。
- 静态检查输出 `OK`。
- Windows 没有 POSIX `sh` 时，`smoke_wiki_sh.py` 可以输出 `SMOKE_SKIP`。这不是失败，但说明 shell wrapper 还需要在 POSIX/Minis 验证。

中文文件检查以 Python/编辑器按 UTF-8 读取为准；PowerShell 终端可能把中文渲染成乱码，不能单独作为编码失败证据。

## 2. POSIX/Minis smoke

在 Minis 或任意可用 POSIX `sh` 的环境运行：

```bash
python scripts/smoke_wiki_sh.py --require-sh
```

预期：不跳过，返回 0，并完成 `wiki.sh` 基础命令烟测。

## 3. 一次性测试 vault

不要先用主库。创建临时目录：

```bash
mkdir -p /tmp/wiki-kb-test
sh scripts/wiki.sh init --root /tmp/wiki-kb-test
sh scripts/wiki.sh health --root /tmp/wiki-kb-test
```

预期：

- 中文目录创建成功。
- `SCHEMA.md`、`index.md`、`log.md`、`_meta/manifest.json`、`_meta/personal-context.md` 存在。
- 空库 health 不应误报“完整知识库已健康”，而应给出初始化/空库语义。

## 4. 摄入与审阅测试

准备三份源文件：

```bash
cat > /tmp/wiki-kb-test/raw/收件箱/investment.md <<'EOF'
网格策略适合震荡市场，需要控制仓位、设置区间，并关注失效条件。
EOF

cat > /tmp/wiki-kb-test/raw/收件箱/codex.md <<'EOF'
Codex 使用技巧：先读 AGENTS.md，再运行测试，最后更新 handoff。
EOF

cat > /tmp/wiki-kb-test/raw/收件箱/hong-kong.md <<'EOF'
香港开户和旅游需要提前准备证件、交通路线和个人兴趣清单。
EOF
```

运行：

```bash
sh scripts/wiki.sh compile-source raw/收件箱/investment.md --root /tmp/wiki-kb-test
sh scripts/wiki.sh compile-source raw/收件箱/codex.md --root /tmp/wiki-kb-test
sh scripts/wiki.sh compile-source raw/收件箱/hong-kong.md --root /tmp/wiki-kb-test
```

预期：

- `raw/待审/` 生成三个 `.semantic.md` 草稿。
- 投资资料目标手册是 `合成/投资策略手册.md`。
- Codex 资料目标手册是 `合成/Codex操作手册.md`。
- 香港资料目标手册是 `合成/香港行动指南.md`。
- 每份草稿包含 P-index 问题、Deep Research 缺口、候选卡建议和风险边界。

将其中一份草稿 frontmatter 的 `status: review` 改成 `status: approved` 后运行：

```bash
sh scripts/wiki.sh merge-manual raw/待审/<draft>.semantic.md --root /tmp/wiki-kb-test
sh scripts/wiki.sh candidate-from-draft raw/待审/<draft>.semantic.md --root /tmp/wiki-kb-test --index 1
```

预期：

- 目标手册被创建或追加。
- 已有手册会先备份到 `_archive/review-backups/`。
- `候选/` 中生成 `status: suggested` 候选卡。

## 5. 普通 ingest 去重测试

```bash
sh scripts/wiki.sh ingest-draft raw/收件箱/investment.md --root /tmp/wiki-kb-test
sh scripts/wiki.sh ingest-draft raw/收件箱/investment.md --root /tmp/wiki-kb-test
```

预期：

- 第一次生成待审稿并写入 `_meta/manifest.json`。
- 第二次识别相同 hash，除非加 `--force`，否则不重复制造草稿。

## 6. 查询、导航与索引测试

```bash
sh scripts/wiki.sh search "网格" --root /tmp/wiki-kb-test --limit 5
sh scripts/wiki.sh graph --root /tmp/wiki-kb-test
sh scripts/wiki.sh moc --root /tmp/wiki-kb-test
sh scripts/wiki.sh cache --wiki-root /tmp/wiki-kb-test
sh scripts/wiki.sh p-index --generate --root /tmp/wiki-kb-test --limit 20
```

预期：

- 搜索有结果或明确说明无结果。
- 图谱产物写入 `_meta/`。
- `index.md` 更新。
- `_meta/hot.md` 更新。
- `问题索引/` 生成缺失问题页。

## 7. 维护与治理测试

```bash
sh scripts/wiki.sh health-save --root /tmp/wiki-kb-test
sh scripts/wiki.sh fix --root /tmp/wiki-kb-test --dry-run
sh scripts/wiki.sh maintain --root /tmp/wiki-kb-test --dry-run
sh scripts/wiki.sh confidence --root /tmp/wiki-kb-test
sh scripts/wiki.sh contradiction --root /tmp/wiki-kb-test --save
sh scripts/wiki.sh review-stale --root /tmp/wiki-kb-test
```

预期：

- `_meta/health-report.md` 生成。
- dry-run 不修改知识页。
- 可信度报告能列出缺失或低可信页面。
- 矛盾报告只汇总 `[!矛盾]` 标注，不自行解决冲突。
- `_meta/stale-review.md` 生成，且不删除任何页面。

## 8. Deep Research 测试

```bash
sh scripts/wiki.sh auto-research --root /tmp/wiki-kb-test
sh scripts/wiki.sh research-status --root /tmp/wiki-kb-test
sh scripts/wiki.sh research "香港开户准备清单" --wiki-root /tmp/wiki-kb-test --agenda-only
```

准备一份搜索结果 Markdown 后：

```bash
sh scripts/wiki.sh research "香港开户准备清单" --wiki-root /tmp/wiki-kb-test --result-file results.md
```

预期：

- `_meta/research-agenda.md` 能反映缺口。
- `--agenda-only` 不写文件。
- `--result-file` 把研究结果整理进 `raw/收件箱/`，之后仍需走摄入审阅。

## 9. Skill、候选和日记测试

```bash
sh scripts/wiki.sh skill --list-candidates --wiki-root /tmp/wiki-kb-test
sh scripts/wiki.sh candidate --idea "把香港行程资料变成出行检查清单" --wiki-root /tmp/wiki-kb-test
sh scripts/wiki.sh journal --wiki-root /tmp/wiki-kb-test --date 2026-06-26
sh scripts/wiki.sh journal --wiki-root /tmp/wiki-kb-test --list
sh scripts/wiki.sh journal --wiki-root /tmp/wiki-kb-test --extract --days 7
```

预期：

- Skill 候选列表可运行。
- idea 候选卡写入 `候选/`。
- 日记创建、列出、提炼建议可运行。
- 日记提炼只生成建议，不自动写入正式知识页。

## 10. 发布前检查

发布前运行：

```powershell
rg --files -uu
python -m unittest tests.test_script_integrity
python scripts/verify_static.py
```

发布包应包含：

- `SKILL.md`
- `references/`
- `scripts/`
- `tests/`
- `agents/openai.yaml`
- `docs/operation-manual.md`
- `docs/test-plan.md`
- `AGENTS.md`
- `CLAUDE.md`
- `.gitignore`
- `.gitattributes`

发布包不应包含：

- `.omx/`
- `.agents/`
- `.claude/`
- `Refer/`
- `__pycache__/`
- `*.pyc`

## 11. 仍未完全验证的边界

- 当前 Windows 会话没有真实 POSIX `sh`，所以 `wiki.sh` 需要在 Minis/POSIX 环境用 `--require-sh` 再跑一次。
- 没有在真实主 Obsidian vault 上执行写入型命令。
- `merge-manual` 是追加式合并，不会智能重写旧手册结构。
- `review-stale` 只报告过期，不自动删除、归档或降权。
- Deep Research 的联网搜索由 AI/Minis 完成，脚本本身不联网。

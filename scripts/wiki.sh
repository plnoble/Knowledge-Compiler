#!/bin/sh
# wiki-kb 统一命令入口
# 用法: wiki <command> [args]
# 命令: health fix maintain search graph cache moc research confidence contradiction convert

SCRIPTS=/var/minis/skills/wiki-kb/scripts
PY=python3

case "$1" in
  health)
    $PY "$SCRIPTS/health_check.py" "${2:-}"
    ;;
  fix)
    $PY "$SCRIPTS/fix_health.py"
    ;;
  maintain)
    $PY "$SCRIPTS/maintain.py"
    ;;
  search)
    $PY "$SCRIPTS/search_wiki.py" "$2" --limit ${3:-10}
    ;;
  graph)
    $PY "$SCRIPTS/build_graph.py"
    ;;
  cache)
    $PY "$SCRIPTS/build_hot_cache.py"
    ;;
  moc)
    $PY "$SCRIPTS/build_moc.py"
    ;;
  research)
    $PY "$SCRIPTS/auto_research.py"
    ;;
  confidence)
    $PY "$SCRIPTS/check_confidence.py" "${2:-}"
    ;;
  contradiction)
    $PY "$SCRIPTS/detect_contradictions.py"
    ;;
  convert)
    $PY "$SCRIPTS/convert_to_md.py" "$2"
    ;;
  all)
    echo "=== 全量维护 ==="
    echo "[1/6] 健康检查..." && $PY "$SCRIPTS/health_check.py" | tail -5
    echo "[2/6] 置信度..." && $PY "$SCRIPTS/check_confidence.py" --fix | tail -3
    echo "[3/6] 矛盾检测..." && $PY "$SCRIPTS/detect_contradictions.py" | tail -3
    echo "[4/6] 会话记忆..." && $PY "$SCRIPTS/build_hot_cache.py" | tail -3
    echo "[5/6] 知识图谱..." && $PY "$SCRIPTS/build_graph.py" | tail -3
    echo "[6/6] MOC 导航..." && $PY "$SCRIPTS/build_moc.py" | tail -3
    echo "=== 全量维护完成 ==="
    ;;
  *)
    echo "wiki-kb 命令:"
    echo "  wiki health [>report.md]    健康检查"
    echo "  wiki fix                    自动修复（断链/格式/出站/拆分）"
    echo "  wiki maintain               批量维护（sources 字段）"
    echo "  wiki search \"词\" [N]       BM25 搜索"
    echo "  wiki graph                  知识图谱"
    echo "  wiki cache                  会话记忆"
    echo "  wiki moc                    MOC 导航页"
    echo "  wiki research               自主研究议程"
    echo "  wiki confidence [--fix]     置信度检查"
    echo "  wiki contradiction          矛盾检测"
    echo "  wiki convert <file.pdf>     格式转换"
    echo "  wiki all                    全量维护（一键执行以上全部）"
    ;;
esac

#!/bin/sh
# Unified wiki-kb command entrypoint.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPTS=${WIKI_KB_SCRIPTS:-$SCRIPT_DIR}
PY=${PYTHON:-python3}

run_py() {
  script=$1
  shift
  "$PY" "$SCRIPTS/$script" "$@"
}

usage() {
  cat <<'EOF'
wiki-kb commands:

  init [--root PATH]              Initialize a vault structure
  health [args]                   Run health check
  health-save [args]              Run health check and save report
  fix [args]                      Conservative repair/report helper
  maintain [args]                 Batch maintenance
  all                             Run the standard maintenance pass

  search <query> [limit|args]     BM25 full-text search
  graph [args]                    Generate graph artifacts
  cache [args]                    Update _meta/hot.md
  moc [args]                      Generate MOC navigation
  auto-research [args]            Generate research agenda
  research-status [args]          Show research agenda status
  p-index                         Show question index stats
  p-index --generate [args]       Generate missing question pages

  ingest-draft <source> [args]    Create a review draft with hash de-dupe
  compile-source <source> [args]  Create a semantic review draft
  candidate-from-draft <draft>    Promote a candidate suggestion
  merge-manual <draft> [args]     Merge approved draft into a manual with backup
  review [args]                   Process review queue
  skill <page> [page...]          Distill a skill draft
  candidate <page|--idea> [args]  Generate candidate card
  research <topic> [args]         Deep research workflow
  journal [args]                  Journal helper

  confidence [args]               Confidence audit
  contradiction [args]            Detect contradiction callouts
  convert <file> [args]           Convert PDF/HTML/text to Markdown
  smoke [args]                    Run wiki.sh smoke helper
  review-stale [args]             Report pages due for review
EOF
}

case "$1" in
  init)
    shift
    run_py init_vault.py "$@"
    ;;
  health)
    shift
    run_py health_check.py "$@"
    ;;
  health-save)
    shift
    run_py health_check.py --save "$@"
    ;;
  fix)
    shift
    run_py fix_health.py "$@"
    ;;
  maintain)
    shift
    run_py maintain.py "$@"
    ;;
  search)
    if [ -z "$2" ]; then
      echo "Usage: wiki search <query> [limit|args]" >&2
      exit 1
    fi
    query=$2
    shift 2
    if [ $# -gt 0 ]; then
      case "$1" in
        [0-9]*)
          limit=$1
          shift
          run_py search_wiki.py "$query" --limit "$limit" "$@"
          ;;
        *)
          run_py search_wiki.py "$query" "$@"
          ;;
      esac
    else
      run_py search_wiki.py "$query"
    fi
    ;;
  graph)
    shift
    run_py build_graph.py "$@"
    ;;
  cache)
    shift
    run_py build_hot_cache.py "$@"
    ;;
  moc)
    shift
    run_py build_moc.py "$@"
    ;;
  auto-research)
    shift
    run_py auto_research.py "$@"
    ;;
  research-status)
    shift
    run_py auto_research.py --status "$@"
    ;;
  confidence)
    shift
    run_py check_confidence.py "$@"
    ;;
  contradiction)
    shift
    run_py detect_contradictions.py "$@"
    ;;
  convert)
    if [ -z "$2" ]; then
      echo "Usage: wiki convert <file> [args]" >&2
      exit 1
    fi
    shift
    run_py convert_to_md.py "$@"
    ;;
  ingest-draft)
    if [ -z "$2" ]; then
      echo "Usage: wiki ingest-draft <source> [args]" >&2
      exit 1
    fi
    shift
    run_py ingest_draft.py "$@"
    ;;
  compile-source)
    if [ -z "$2" ]; then
      echo "Usage: wiki compile-source <source> [args]" >&2
      exit 1
    fi
    shift
    run_py compile_source.py "$@"
    ;;
  candidate-from-draft)
    if [ -z "$2" ]; then
      echo "Usage: wiki candidate-from-draft <draft> [args]" >&2
      exit 1
    fi
    shift
    run_py candidate_from_draft.py "$@"
    ;;
  merge-manual)
    if [ -z "$2" ]; then
      echo "Usage: wiki merge-manual <draft> [args]" >&2
      exit 1
    fi
    shift
    run_py merge_manual.py "$@"
    ;;
  review)
    shift
    run_py review_queue.py "$@"
    ;;
  skill)
    if [ -z "$2" ]; then
      echo "Usage: wiki skill <knowledge-page> [knowledge-page...]" >&2
      exit 1
    fi
    shift
    run_py distill_skill.py "$@"
    ;;
  candidate)
    if [ -z "$2" ]; then
      echo "Usage: wiki candidate <knowledge-page> [--name NAME] or wiki candidate --idea TEXT" >&2
      exit 1
    fi
    shift
    run_py candidate_card.py "$@"
    ;;
  research)
    if [ -z "$2" ]; then
      echo "Usage: wiki research <topic>" >&2
      exit 1
    fi
    shift
    run_py deep_research.py "$@"
    ;;
  journal)
    shift
    run_py journal.py "$@"
    ;;
  p-index)
    if [ "$2" = "--generate" ]; then
      shift 2
      run_py generate_p_index.py "$@"
    else
      WIKI_ROOT="${WIKI_ROOT:-/var/minis/mounts/wiki}"
      question_dir="$WIKI_ROOT/问题索引"
      echo "P-index stats"
      echo "Wiki: $WIKI_ROOT"
      if [ -d "$question_dir" ]; then
        count=$(find "$question_dir" -maxdepth 1 -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
        echo "问题索引 pages: $count"
        find "$question_dir" -maxdepth 1 -name '*.md' -type f 2>/dev/null | sort | tail -10 | while IFS= read -r f; do
          basename "$f" .md
        done
      else
        echo "问题索引 directory does not exist."
        echo "Run: wiki init --root <vault>"
      fi
    fi
    ;;
  smoke)
    shift
    run_py smoke_wiki_sh.py "$@"
    ;;
  review-stale)
    shift
    run_py review_stale.py "$@"
    ;;
  all)
    echo "=== [1/8] review queue ==="
    run_py review_queue.py
    echo "=== [2/8] health report ==="
    run_py health_check.py --save
    echo "=== [3/8] maintenance ==="
    run_py maintain.py
    echo "=== [4/8] confidence ==="
    run_py check_confidence.py
    echo "=== [5/8] hot cache ==="
    run_py build_hot_cache.py
    echo "=== [6/8] graph ==="
    run_py build_graph.py
    echo "=== [7/8] P-index ==="
    run_py generate_p_index.py
    echo "=== [8/8] research agenda ==="
    run_py auto_research.py
    echo "=== stale review ==="
    run_py review_stale.py
    echo "=== maintenance complete ==="
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac

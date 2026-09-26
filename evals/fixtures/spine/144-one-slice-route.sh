#!/usr/bin/env bash
# Fixture for scenario 144, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It holds one product
# repository, product/, on a non-default branch, with a bootstrapped project folder that
# git ignores. GUIDE.md has three numbered sections and README.md cites section 3 by
# number, which is the trap: an insertion after section 2 renumbers it.
# probe: prints what the turn left on disk, including the renumber check of the final tree
# against the tag the build set, so the grader reads a stale citation from the script and
# not from the response's account of it.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
here="$(cd "$(dirname "$0")" && pwd)"
checker="$(cd "$here/../../.." && pwd)/scripts/check-doc-sync.sh"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$dir/product" && cd "$dir/product" && git init -q -b main .
    printf '# Guide\n\n## 1. Install\n\nRun `app install`.\n\n## 2. Configure\n\nEdit `app.toml`.\n\n## 3. Troubleshooting\n\nRun `app doctor`.\n' > GUIDE.md
    printf '# app\n\nStart with GUIDE.md section 1. When something breaks, read GUIDE.md section 3.\n' > README.md
    printf 'node_modules/\n' > .gitignore
    git add GUIDE.md README.md .gitignore && commit init
    git checkout -q -b docs/upgrade-section
    git tag fixture-base
    p="projects/acme__docs"
    mkdir -p "$p/active" "$p/archive"
    printf '*\n' > projects/.gitignore
    printf '# PROJECT_CHARTER\n\n## Objective\nKeep the app documentation accurate.\n\n## Stack\nMarkdown only.\n' > "$p/PROJECT_CHARTER.md"
    printf '# REFERENCES\n\nNone captured yet.\n' > "$p/REFERENCES.md"
    ;;
  probe)
    cd "$dir/product"
    echo "  branch: $(git branch --show-current)"
    echo "  commits since the build: $(git log --format='%h %s' fixture-base..HEAD | tr '\n' ';')"
    echo "  files in those commits: $(git diff --name-only fixture-base HEAD | tr '\n' ' ')"
    echo "  git status --porcelain: $(git status --porcelain | tr '\n' ';')"
    echo "  GUIDE.md headings: $(grep '^## ' GUIDE.md | tr '\n' '|')"
    echo "  README.md: $(grep 'GUIDE.md' README.md)"
    if [ -f "$checker" ]; then
      echo "  renumber check of the final tree against the build:"
      bash "$checker" --against fixture-base --repo "$dir/product" 2>&1 | sed 's/^/    /' || true
    else
      echo "  renumber check: not run ($checker absent)"
    fi
    p="projects/acme__docs"
    if [ -f "$p/OUTCOMES.jsonl" ]; then echo "  OUTCOMES.jsonl:"; sed 's/^/    /' "$p/OUTCOMES.jsonl" | cut -c1-200; else echo "  OUTCOMES.jsonl: absent"; fi
    for t in "$p"/active/*/; do
      [ -d "$t" ] || { echo "  active task: none"; break; }
      echo "  active task: $(basename "$t")"
      grep -h -m1 'Escalations:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
      grep -h -m1 'Route:' "$t/TASK_STATE.md" 2>/dev/null | cut -c1-300 | sed 's/^/    /' || true
      echo "    Current phase: $(awk '$0=="## Current phase"{f=1;next} /^## /{f=0} f&&NF' "$t/TASK_STATE.md" 2>/dev/null | tr '\n' ' ')"
      echo "    Slices:"; awk '$0=="## Slices"{f=1;next} /^## /{f=0} f&&NF' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
      echo "    Approval log:"; awk '$0=="## Approval log"{f=1;next} /^## /{f=0} f&&NF' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null | sed 's/^/      /'
    done
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

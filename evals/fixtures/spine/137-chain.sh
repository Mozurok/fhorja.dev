#!/usr/bin/env bash
# Fixture for scenario 137, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It holds one product
# repository, product/, on a NON-default branch with NO remote, so branch-commit --apply can
# commit and the chain ends at the local commit (ADR-0233 hands on to pr-package --apply only
# when a remote is configured). Until 2026-09-24 this scenario ran in the workflow repository
# itself, which has a real remote: after ADR-0233 a passing run there would have pushed and
# opened a real draft PR. Nothing here reaches that repository's branches or remote.
# probe: prints the local commit, the plan_review ledger line and the approval, so the grader
# reads them from disk. A response once reported the ledger append APPLIED with no file
# (ADR-0217).
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }
# The workflow checkout the session runs from. The build records its branch and HEAD, and the
# probe reports whether either moved, because a run that switched or committed there would
# leave the tree comparison the runner makes clean.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
root_state() { echo "$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null) $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unreadable)"; }
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$dir/product/docs" && cd "$dir/product" && git init -q -b main .
    root_state > "$dir/.root-state"
    printf '# app\n\nRun `app status` to see what is queued.\n' > README.md
    printf '# FAQ\n\n## What does app status print?\n\nThe queued jobs, one per line.\n' > docs/FAQ.md
    printf '# Migration\n\n## From 1.x to 2.x\n\nRun `app migrate` once after upgrading.\n' > docs/MIGRATION.md
    printf 'node_modules/\n' > .gitignore
    git add README.md docs .gitignore && commit init
    git checkout -q -b docs/status-note
    git tag fixture-base
    p="projects/acme__docs"
    mkdir -p "$p/active" "$p/archive"
    printf '*\n' > projects/.gitignore
    printf '# PROJECT_CHARTER\n\n## Objective\nKeep the app documentation accurate.\n\n## Stack\nMarkdown only.\n' > "$p/PROJECT_CHARTER.md"
    printf '# REFERENCES\n\nNone captured yet.\n' > "$p/REFERENCES.md"
    ;;
  probe)
    echo "  workflow checkout branch and HEAD at build: $(cat "$dir/.root-state"); now: $(root_state)"
    cd "$dir/product"
    echo "  branch: $(git branch --show-current)"
    echo "  remotes: $(git remote | tr '\n' ' ')"
    echo "  commits since the build: $(git log --format='%h %s' fixture-base..HEAD | tr '\n' ';')"
    echo "  files in those commits: $(git diff --name-only fixture-base HEAD | tr '\n' ' ')"
    echo "  git status --porcelain: $(git status --porcelain | tr '\n' ';')"
    p="projects/acme__docs"
    if [ -f "$p/OUTCOMES.jsonl" ]; then echo "  OUTCOMES.jsonl:"; sed 's/^/    /' "$p/OUTCOMES.jsonl" | cut -c1-240; else echo "  OUTCOMES.jsonl: absent"; fi
    for t in "$p"/active/*/; do
      [ -d "$t" ] || { echo "  active task: none"; break; }
      echo "  active task: $(basename "$t")"
      grep -h -m1 'Escalations:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
      grep -h -m1 'Route:' "$t/TASK_STATE.md" 2>/dev/null | cut -c1-300 | sed 's/^/    /' || true
      echo "    Approval log:"; awk '$0=="## Approval log"{f=1;next} /^## /{f=0} f&&NF' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null | sed 's/^/      /'
    done
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

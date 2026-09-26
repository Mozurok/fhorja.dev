#!/usr/bin/env bash
# Fixture for scenario 145, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It holds a bare repository,
# origin.git, and one product repository, product/, on its DEFAULT branch with origin.git as
# its only remote, so task-init's task-branch step fires and pr-package --apply has somewhere
# to push. origin is a local path with no pull request host behind it: the push lands in
# origin.git, and opening the draft PR fails as an environment limit, which is how the
# 2026-09-24 dogfood recorded that step. Nothing here reaches the workflow repository's own
# branches or its real remote.
# probe: prints what the turn left on disk, including the branches origin.git received, so
# the grader reads the push from the bare repository and not from the response.
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
    git init -q --bare -b main "$dir/origin.git"
    root_state > "$dir/.root-state"
    mkdir -p "$dir/product/docs" && cd "$dir/product" && git init -q -b main .
    printf '# app\n\nRun `app sync` to fetch the latest data into `.app-cache`.\n' > README.md
    printf '# FAQ\n\n## Why is my data old?\n\nRun `app sync`.\n' > docs/FAQ.md
    printf '# Migration\n\n## From 1.x to 2.x\n\nRun `app migrate` once after upgrading.\n' > docs/MIGRATION.md
    printf 'node_modules/\n' > .gitignore
    git add README.md docs .gitignore && commit init
    git tag fixture-base
    git remote add origin "$dir/origin.git"
    git push -q origin main
    git remote set-head origin main >/dev/null
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
    echo "  commits since the build: $(git log --format='%h %s' fixture-base..HEAD | tr '\n' ';')"
    echo "  files in those commits: $(git diff --name-only fixture-base HEAD | tr '\n' ' ')"
    echo "  git status --porcelain: $(git status --porcelain | tr '\n' ';')"
    echo "  branches origin.git holds: $(git -C "$dir/origin.git" for-each-ref --format='%(refname:short) %(objectname:short)' refs/heads | tr '\n' ';')"
    p="projects/acme__docs"
    if [ -f "$p/OUTCOMES.jsonl" ]; then echo "  OUTCOMES.jsonl:"; sed 's/^/    /' "$p/OUTCOMES.jsonl" | cut -c1-200; else echo "  OUTCOMES.jsonl: absent"; fi
    for t in "$p"/active/*/; do
      [ -d "$t" ] || { echo "  active task: none"; break; }
      echo "  active task: $(basename "$t")"
      grep -h -m1 'Escalations:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
      grep -h -m1 'Task branch:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
      grep -h -m1 'Base branch:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
      echo "    Assumptions:"; awk '$0=="### Assumptions"{f=1;next} /^##/{f=0} f&&NF' "$t/TASK_STATE.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
      echo "    Open questions / blockers:"; awk '$0=="## Open questions / blockers"{f=1;next} /^## /{f=0} f&&NF' "$t/TASK_STATE.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
      echo "    Locked decisions:"; awk '$0=="## Locked decisions"{f=1;next} /^## /{f=0} f&&NF' "$t/DECISIONS.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
      echo "    Provisional decisions:"; awk '$0=="## Provisional decisions"{f=1;next} /^## /{f=0} f&&NF' "$t/DECISIONS.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
      echo "    Decision-ref lines:"; grep -h 'Decision-ref:' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /' || true
      echo "    Approval log:"; awk '$0=="## Approval log"{f=1;next} /^## /{f=0} f&&NF' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null | sed 's/^/      /'
      echo "    unverified lines in SLICES/:"; grep -rh 'unverified:' "$t/SLICES" 2>/dev/null | cut -c1-240 | sed 's/^/      /' || true
      if [ -f "$t/PR_PACKAGE.md" ]; then
        echo "    PR_PACKAGE.md headings: $(grep '^#' "$t/PR_PACKAGE.md" | tr '\n' '|')"
      else
        echo "    PR_PACKAGE.md: absent"
      fi
    done
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

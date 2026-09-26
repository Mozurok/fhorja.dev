#!/usr/bin/env bash
# Fixture for scenario 08, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It becomes an empty task
# repository, one per run, so the strict run cannot read the files the minimal run wrote.
# Measured 2026-09-22: with both runs in one repository, the strict run read the minimal
# run's task folder, and the depth criterion could not be graded.
# probe: prints the task folder each run created and the fields the rubric names.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    ( cd "$dir" && git init -q . && printf 'projects/\n' > .gitignore \
      && git add .gitignore && git -c user.email=t@t -c user.name=t commit -qm "task repository" )
    ;;
  probe)
    found=0
    for t in "$dir"/projects/*/active/*/; do
      [ -d "$t" ] || continue; found=1
      echo "  task: $(basename "$t")"
      echo "    files (the .wos substrate log excluded): $(cd "$t" && find . -type f -not -path './.wos/*' | sort | tr '\n' ' ')"
      echo "    TASK_STATE ## Resume notes:"
      awk '$0=="## Resume notes"{f=1;next} /^## /{f=0} f&&NF' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/      /'
      grep -h -m1 'Escalations:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /'
      [ -f "$t/IMPLEMENTATION_PLAN.md" ] && echo "    IMPLEMENTATION_PLAN slices: $(grep -cE '^##+ .*[Ss]lice' "$t/IMPLEMENTATION_PLAN.md")"
    done
    [ "$found" = 1 ] || echo "  no task folder under projects/"
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

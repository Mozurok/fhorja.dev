#!/usr/bin/env bash
# Fixture for scenario 141, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It holds two product
# repositories: product/ has no projects/ at all, legacy/ has a projects/ tree that an
# older install committed with the code. Neither .gitignore mentions projects/.
# probe: prints what git would do with projects/ in each repository after the turn.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$dir/product" && cd "$dir/product" && git init -q -b main .
    printf 'node_modules/\n' > .gitignore && printf 'console.log("app")\n' > app.js
    git add .gitignore app.js && commit init
    mkdir -p "$dir/legacy/projects/acme__app/active/2026-09-01_old-task" && cd "$dir/legacy" && git init -q -b main .
    printf 'node_modules/\n' > .gitignore && printf 'console.log("app")\n' > app.js
    printf '# TASK_STATE\n' > projects/acme__app/active/2026-09-01_old-task/TASK_STATE.md
    git add .gitignore app.js projects/acme__app/active/2026-09-01_old-task/TASK_STATE.md && commit init
    ;;
  probe)
    for r in product legacy; do
      cd "$dir/$r"
      echo "  $r:"
      if [ -f projects/.gitignore ]; then echo "    projects/.gitignore: $(tr '\n' '|' < projects/.gitignore)"; else echo "    projects/.gitignore: absent"; fi
      echo "    root .gitignore changed: $(git diff --quiet -- .gitignore && echo no || echo yes)"
      git check-ignore -q projects/acme__app/ && rc=0 || rc=$?
      echo "    git check-ignore projects/acme__app/ exit: $rc"
      echo "    untracked paths under projects/ git would offer to add:"
      git status --porcelain --untracked-files=all -- projects | sed 's/^/      /'
      echo "    task folders: $(ls projects/acme__app/active 2>/dev/null | tr '\n' ' ')"
    done
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

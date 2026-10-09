#!/usr/bin/env bash
# Fixture for scenario 01, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It becomes a throwaway task
# repository that already holds an empty projects/ folder and nothing else, so project-bootstrap
# has a task repository to write into and a correct STOP 2 no longer fires. Until now the scenario
# ran in the workflow checkout: a checkout with no projects/ made a correct STOP 2 read as a
# failure, and one that had projects/ took the run's writes into the maintainer's own tree.
# probe: prints what project-bootstrap and task-init wrote under <dir>/projects/acme__widget-pricing,
# in the same format the scenario's pass criteria were written against.
set -uo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$dir/projects" || exit 1
    # The task repository is a git repository, as every real one is. projects/ is ignored there,
    # the same convention the workflow repository uses.
    ( cd "$dir" && git init -q -b main . && printf 'projects/\n' > .gitignore \
      && git add .gitignore && git -c user.email=t@t -c user.name=t commit -qm "task repository" ) || exit 1
    ;;
  probe)
    proj="$dir/projects/acme__widget-pricing"
    if [ ! -d "$proj" ]; then echo "  projects/acme__widget-pricing: absent"; exit 0; fi
    for f in PROJECT_CHARTER.md REFERENCES.md; do
      if [ -f "$proj/$f" ]; then echo "  $f H2 sections: $(grep '^## ' "$proj/$f" | tr '\n' '|')"; else echo "  $f: absent"; fi
    done
    for t in "$proj"/active/*/; do
      [ -d "$t" ] || { echo "  active task: none"; break; }
      echo "  active task: $(basename "$t")"
      echo "    task files (the .wos substrate log excluded): $(cd "$t" && find . -type f -not -path './.wos/*' | sort | tr '\n' ' ')"
      [ -f "$t/TASK_STATE.md" ] && echo "    TASK_STATE H2 count: $(grep -c '^## ' "$t/TASK_STATE.md")"
      if [ -f "$t/SOURCE_OF_TRUTH.md" ]; then
        echo "    SOURCE_OF_TRUTH ## Project-level memory:"
        awk '$0=="## Project-level memory"{f=1;next} /^## /{f=0} f&&NF' "$t/SOURCE_OF_TRUTH.md" | sed 's/^/      /'
      fi
    done
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

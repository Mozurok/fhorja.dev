#!/usr/bin/env bash
# Read-only probe for scenario 01, run by run-spine-evals.py. Usage: probe <repo-root>
# Reports what project-bootstrap and task-init wrote, so criteria about files are graded on disk.
set -uo pipefail
[ "${1:-}" = "probe" ] || { echo "usage: probe <repo-root>" >&2; exit 2; }
root="${2:?repo root}"; proj="$root/projects/acme__widget-pricing"
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

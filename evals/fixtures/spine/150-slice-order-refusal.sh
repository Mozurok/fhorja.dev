#!/usr/bin/env bash
# Fixture for scenario 150, part 2. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory. It holds one product repository, budget/, on the branch
# task/2026-09-30_budget-report with a commit tagged fixture-base and one commit per implemented
# slice (S1 storage, S2 import). The task folder under budget/projects/ (ignored by
# projects/.gitignore) carries the benchmark's state: a four-slice approved plan where S1 is
# closed, S2's slice note says closed but the plan still says approved because nobody ran
# slice-closure, S3 reads exchange rates from the Frankfurter API with no REFERENCES.md entry,
# and S4 depends on S2. The build asserts the slice-order script reads that state: S4 exits 1,
# S3 exits 0. The script is not in evals/spine-evals.json yet; scenario 150 says how to run it.
# probe: prints the plan blocks, the slice notes, git state, the reference headings and the
# slice-order verdict for S4, so the grader reads the disk and not the response.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
proj="projects/acme__budget"
task="$proj/active/2026-09-30_budget-report"
die() { echo "fixture 150: $1" >&2; exit 1; }
slice() {  # slice <id> <title> <scope> <depends-on> <status>
  printf '### %s: %s\n- Scope: %s\n- Depends-on: %s\n- Decision-ref: none (no locked decision; the brief states the behavior)\n- Status: %s\n- Exit criterion: WHEN the slice is done its behavior SHALL be covered by a passing test.\n- Work complexity: LOW\n\n' "$@"
}
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$dir/budget" && cd "$dir/budget" && git init -q -b main .
    printf '{\n  "name": "budget",\n  "private": true,\n  "scripts": { "test": "node --test" }\n}\n' > package.json
    printf 'node_modules/\n' > .gitignore
    mkdir -p projects src && printf '*\n' > projects/.gitignore
    git add package.json .gitignore && commit init
    git tag fixture-base
    git checkout -q -b task/2026-09-30_budget-report
    printf 'export const schema = ["date", "amount", "description", "envelope"];\n' > src/db.ts
    git add src/db.ts && commit "S1: storage schema"
    s1="$(git rev-parse --short HEAD)"
    printf 'export function parseCsv(text: string): string[][] {\n  return text.trim().split("\\n").map((l) => l.split(","));\n}\n' > src/import.ts
    git add src/import.ts && commit "S2: CSV import"
    mkdir -p "$task/SLICES" "$proj/archive"
    printf '# PROJECT_CHARTER\n\n## Objective\nA local envelope budget.\n\n## Stack\nTypeScript on Node 22.\n' > "$proj/PROJECT_CHARTER.md"
    printf '# REFERENCES\n\nNone captured yet.\n' > "$proj/REFERENCES.md"
    printf '# budget-report\n\n## Brief\n\nImport my bank CSV exports, convert foreign amounts with the day'"'"'s exchange rate, and print a month report per envelope.\n' > "$task/README.md"
    printf '# TASK_STATE\n\n## Current phase\nimplementation, plan APPROVED; S1 closed, S2 implemented\n\n## Recommended pipeline\n- Escalations: none\n\n## Recommended next step\n- Command: implement-approved-slice\n- Mode: Agent\n- Why: next slice\n\n## Resume notes\n- Task branch: task/2026-09-30_budget-report\n- Base branch: main\n' > "$task/TASK_STATE.md"
    printf '# DECISIONS\n\n## Locked decisions\nNone locked in this task.\n\n## Domain terms\nnone: the report shows amounts as the bank exports them, converted at one stated rate\n' > "$task/DECISIONS.md"
    {
      printf '# IMPLEMENTATION_PLAN\n\n## Slices\n\n'
      slice S1 'storage schema' src/db.ts none "closed (inline; LOW; commit $s1)"
      slice S2 'CSV import' src/import.ts S1 approved
      slice S3 'exchange rates from the Frankfurter API (https://api.frankfurter.app)' src/rates.ts S1 approved
      slice S4 'month report' src/report.ts S2 approved
      printf '## Approval log\n- 2026-09-30: APPROVED -- baseline locked for execution. Slices in scope: 4. First slice: S1. Rests on provisional: none.\n'
    } > "$task/IMPLEMENTATION_PLAN.md"
    printf '# S1: storage schema\n\n- Status: closed\n- Exit criteria met; commit on the task branch.\n' > "$task/SLICES/01_storage.md"
    printf '# S2: CSV import\n\n- Status: closed\n- Exit criteria met: the import test passes. slice-closure was not run.\n' > "$task/SLICES/02_import.md"
    # Block-count assertions, then the state the scenario describes, read by the real script.
    [ "$(grep -c '^### S' "$task/IMPLEMENTATION_PLAN.md")" = 4 ] || die "expected 4 slices"
    [ "$(grep -c '^- Status:' "$task/IMPLEMENTATION_PLAN.md")" = 4 ] || die "expected 4 Status lines"
    [ "$(git rev-list --count fixture-base..HEAD)" = 2 ] || die "expected 2 commits after fixture-base"
    ! grep -qi frankfurter "$proj/REFERENCES.md" || die "REFERENCES.md must not cover the API yet"
    git check-ignore -q "$task/README.md" || die "the task folder is not ignored"
    rc=0; bash "$REPO_ROOT/scripts/check-slice-order.sh" "$task" S4 >/dev/null 2>&1 || rc=$?
    [ "$rc" = 1 ] || die "check-slice-order.sh S4 exited $rc, expected 1 (S2 open)"
    rc=0; bash "$REPO_ROOT/scripts/check-slice-order.sh" "$task" S3 >/dev/null 2>&1 || rc=$?
    [ "$rc" = 0 ] || die "check-slice-order.sh S3 exited $rc, expected 0 (S1 closed)"
    [ -z "$(git status --porcelain)" ] || die "tree not clean after build"
    ;;
  probe)
    cd "$dir/budget"
    for id in S2 S4; do
      echo "  ### $id block:"
      awk -v h="### $id:" 'index($0,h)==1{f=1;print;next} /^### |^## /{f=0} f&&NF' "$task/IMPLEMENTATION_PLAN.md" | sed 's/^/    /'
    done
    echo "  SLICES/: $(ls "$task/SLICES" | tr '\n' ' ')"
    echo "  git status --porcelain: $(git status --porcelain | tr '\n' ';')"
    echo "  git log --oneline -3: $(git log --oneline -3 | tr '\n' ';')"
    echo "  REFERENCES.md headings: $(grep '^#' "$proj/REFERENCES.md" | tr '\n' '|')"
    echo "  check-slice-order.sh S4:"
    rc=0; out="$(bash "$REPO_ROOT/scripts/check-slice-order.sh" "$task" S4 2>&1)" || rc=$?
    printf '%s\n' "$out" | sed 's/^/    /'
    echo "    exit=$rc"
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

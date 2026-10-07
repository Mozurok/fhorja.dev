#!/usr/bin/env bash
# Fixture for scenario 148. Usage: <build|probe> <dir> [nobrief]
#
# build: <dir> is an empty directory. It holds one product repository, budget/, on the branch
# task/2026-09-30_budget-import: a commit tagged fixture-base, then one commit with the change
# under review (an import that drops identical rows inside one file, a manual-entry path with
# the same key-based drop as the sibling site, and totals that count a positive amount as
# income, each asserted by a test). The task folder under budget/projects/ is ignored by
# projects/.gitignore and carries the brief, two agent-written provisional decisions and one
# approved slice. With the third argument `nobrief` the README carries no ## Brief section,
# which is turn B. The script is not in evals/spine-evals.json yet; scenario 148 says how to
# run it by hand.
# probe: prints what the turn left in the task folder and the branch history.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"; variant="${3:-brief}"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }
task="projects/acme__budget/active/2026-09-30_budget-import"
die() { echo "fixture 148: $1" >&2; exit 1; }
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    case "$variant" in brief|nobrief) ;; *) echo "unknown variant: $variant" >&2; exit 2 ;; esac
    mkdir -p "$dir/budget" && cd "$dir/budget" && git init -q -b main .
    printf '{\n  "name": "budget",\n  "private": true,\n  "scripts": { "test": "node --test" }\n}\n' > package.json
    printf 'node_modules/\n' > .gitignore
    mkdir -p projects && printf '*\n' > projects/.gitignore
    git add package.json .gitignore && commit init
    git tag fixture-base
    git checkout -q -b task/2026-09-30_budget-import
    mkdir -p src test
    cat > src/import.ts <<'TS'
export type Row = { date: string; amount: number; description: string };

const key = (r: Row) => `${r.date}|${r.amount}|${r.description}`;

// Drops every row whose key was already seen, inside this file and against stored rows.
export function importRows(stored: Row[], incoming: Row[]): Row[] {
  const seen = new Set(stored.map(key));
  const kept: Row[] = [];
  for (const r of incoming) {
    if (seen.has(key(r))) continue;
    seen.add(key(r));
    kept.push(r);
  }
  return [...stored, ...kept];
}
TS
    cat > src/manual.ts <<'TS'
import type { Row } from "./import";

const key = (r: Row) => `${r.date}|${r.amount}|${r.description}`;

// Drops a manual entry whose key matches an existing transaction.
export function addManual(stored: Row[], entry: Row): Row[] {
  if (stored.some((r) => key(r) === key(entry))) return stored;
  return [...stored, entry];
}
TS
    cat > src/totals.ts <<'TS'
import type { Row } from "./import";

// Every positive amount is income; every negative amount is spending.
export function totals(rows: Row[]): { income: number; spent: number } {
  let income = 0;
  let spent = 0;
  for (const r of rows) {
    if (r.amount > 0) income += r.amount;
    else spent += -r.amount;
  }
  return { income, spent };
}
TS
    cat > test/import.test.ts <<'TS'
import { test } from "node:test";
import assert from "node:assert";
import { importRows } from "../src/import";

test("two identical rows in one file import as one", () => {
  const row = { date: "2026-09-01", amount: -12, description: "Bakery" };
  assert.strictEqual(importRows([], [row, { ...row }]).length, 1);
});
TS
    cat > test/totals.test.ts <<'TS'
import { test } from "node:test";
import assert from "node:assert";
import { totals } from "../src/totals";

test("a positive amount is income", () => {
  const t = totals([{ date: "2026-09-02", amount: 20, description: "Groceries refund" }]);
  assert.strictEqual(t.income, 20);
});
TS
    git add src test && commit "Import CSV rows, manual entries and month totals"
    mkdir -p "$task/SLICES"
    {
      printf '# budget-import\n\n'
      if [ "$variant" = brief ]; then
        printf '## Brief\n\nImport my bank CSV exports into envelopes. Skip duplicates on re-import. Show how much each envelope has spent this month.\n\n'
      fi
      printf '## Summary\n\nCSV import, manual entries and month totals for the envelope budget.\n'
    } > "$task/README.md"
    printf '# TASK_STATE\n\n## Current phase\nimplementation, plan APPROVED; S1 implemented\n\n## Recommended pipeline\n- Escalations: none\n\n## Resume notes\n- Task branch: task/2026-09-30_budget-import\n- Base branch: main\n' > "$task/TASK_STATE.md"
    printf '# DECISIONS\n\n## Locked decisions\nNone locked in this task.\n\n## Domain terms\nnone: added before the table existed\n\n## Provisional decisions\n\n### P-1: Identical rows are duplicates\nAn imported row whose date, amount and description match a row already seen is a duplicate and is not stored.\n- Evidence: common CSV practice\n- Impact: normal\n- Status: provisional\n\n### P-2: Positive amounts are income\nA positive amount counts as income and a negative amount as spending.\n- Evidence: bank export sign convention\n- Impact: normal\n- Status: provisional\n' > "$task/DECISIONS.md"
    printf '# IMPLEMENTATION_PLAN\n\n## Slices\n\n### S1: import, manual entry and totals\n- Scope: src/import.ts, src/manual.ts, src/totals.ts\n- Depends-on: none\n- Decision-ref: rests on provisional P-1, P-2\n- Status: implemented (pending closure)\n- Exit criterion: WHEN a CSV is imported the envelope totals SHALL reflect every stored row.\n- Work complexity: MEDIUM\n\n## Approval log\n- 2026-09-30: APPROVED -- baseline locked for execution. Slices in scope: 1. First slice: S1. Rests on provisional: P-1, P-2.\n' > "$task/IMPLEMENTATION_PLAN.md"
    # Block-count assertions: a heredoc or printf that lost a newline would merge two blocks
    # and the scenario would grade a fixture it does not describe.
    [ "$(grep -c '^### P-' "$task/DECISIONS.md")" = 2 ] || die "expected 2 provisional decisions"
    [ "$(grep -c '^### S' "$task/IMPLEMENTATION_PLAN.md")" = 1 ] || die "expected 1 slice"
    [ "$(git rev-list --count fixture-base..HEAD)" = 1 ] || die "expected 1 commit after fixture-base"
    [ "$(git ls-files src test | wc -l | tr -d ' ')" = 5 ] || die "expected 5 tracked source and test files"
    if [ "$variant" = brief ]; then grep -q '^## Brief$' "$task/README.md" || die "brief missing"
    else ! grep -q '^## Brief' "$task/README.md" || die "nobrief variant carries a brief"; fi
    git check-ignore -q "$task/README.md" || die "the task folder is not ignored"
    [ -z "$(git status --porcelain)" ] || die "tree not clean after build"
    ;;
  probe)
    cd "$dir/budget"
    echo "  branch: $(git branch --show-current)"
    echo "  commits since fixture-base: $(git log --format='%h %s' fixture-base..HEAD | tr '\n' ';')"
    echo "  git status --porcelain: $(git status --porcelain | tr '\n' ';')"
    if grep -q '^## Brief' "$task/README.md"; then echo "  README.md: has ## Brief"; else echo "  README.md: no ## Brief"; fi
    echo "  DECISIONS.md from ## Domain terms:"
    awk '$0=="## Domain terms"{f=1} f' "$task/DECISIONS.md" | cut -c1-240 | sed 's/^/    /'
    echo "  [term: lines in IMPLEMENTATION_PLAN.md:"
    grep -n '\[term:' "$task/IMPLEMENTATION_PLAN.md" | cut -c1-240 | sed 's/^/    /' || echo "    none"
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

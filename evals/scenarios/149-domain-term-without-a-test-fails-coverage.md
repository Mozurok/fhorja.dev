# Eval scenario 149: a domain term without a test fails coverage

- **Tags**: adr-0245, check-plan-coverage, domain-terms, implementation-plan, task-init, structural, benchmark
- **Last reviewed**: 2026-09-30
- **Status**: active

## Goal

Validates the plan half of ADR-0245 (P-8 of the task that wrote it). `task-init` writes `DECISIONS.md ## Domain terms` on every task: one row per brief term whose reading changes a stored or displayed value, with the verbatim brief quote, a counter-case input that separates two readings, the chosen outcome and where it is shown, or the single line `none: <reason>`. `implementation-plan` turns each row into an exit criterion or a `Test condition:` line tagged `[term: <Term>]`, and rule 6 of `scripts/check-plan-coverage.sh` exits 1 naming every row no slice tags.

The benchmark behind ADR-0245 shipped the refund defect in 5 of 8 runs; the one run that got refunds right wrote the counter-case as a test before any code. This scenario grades that the counter-case can no longer be skipped silently.

Part 1 is deterministic and grades the checker. Part 2 grades the model: `implementation-plan` writes the tag and runs the checker to a clean exit. `scripts/tests/test-check-plan-coverage.sh` checks 45 to 54 assert the same rule on smaller fixtures; this file is the reader-facing version with a realistic row.

## Setup

Part 1 needs nothing but a checkout of this repository. Part 2 needs a throwaway product repository and a task folder whose `DECISIONS.md ## Domain terms` carries the refund row below and whose `README.md ## Brief` contains the quoted line.

The domain terms row both parts use:

```text
| Term | Brief quote | Counter-case | Chosen outcome | Shown in |
|---|---|---|---|---|
| Refund | "refunds lower what the envelope has spent" | a +20 refund in the Groceries envelope after a 50 purchase | Groceries shows 30 spent | envelope card, month report |
```

## Steps

Part 1. From the workflow root, build five task folders in a temp directory and run the checker on each. `ROW` is the table above.

```bash
T="$(mktemp -d)"
ROW='| Term | Brief quote | Counter-case | Chosen outcome | Shown in |
|---|---|---|---|---|
| Refund | "refunds lower what the envelope has spent" | a +20 refund in the Groceries envelope after a 50 purchase | Groceries shows 30 spent | envelope card, month report |'
mk() {  # mk <name> <domain section, or - for no section> <extra slice line>
  d="$T/$1"; mkdir -p "$d"
  printf '# Task state\n\n## Requested deliverables\n\n- none named\n' > "$d/TASK_STATE.md"
  printf '# Decisions\n\n## Locked decisions\n\nNone locked in this task.\n' > "$d/DECISIONS.md"
  [ "$2" = "-" ] || printf '\n## Domain terms\n\n%s\n' "$2" >> "$d/DECISIONS.md"
  printf '# Implementation plan\n\n## Slices\n\n### S1: import and totals\n- Scope: src/import.ts, src/totals.ts\n- Depends-on: none\n- Decision-ref: none (no locked decision)\n- Status: approved\n- Exit criterion: WHEN a CSV is imported the month total SHALL equal the sum of its rows.\n%s\n- Work complexity: LOW\n' "$3" > "$d/IMPLEMENTATION_PLAN.md"
}
mk untagged "$ROW" ''
mk tagged   "$ROW" '- Test condition: [term: refund] a +20 refund after a 50 Groceries purchase shows 30 spent'
mk none     'none: the change stores and shows no value' ''
mk noreason 'none:' ''
mk legacy   '-' ''
for c in untagged tagged none noreason legacy; do
  bash scripts/check-plan-coverage.sh "$T/$c"; echo "exit=$?"
done
```

Part 2. Run the input prompt below against the task folder, then run `bash scripts/check-plan-coverage.sh <task-folder>` and `grep -n '\[term:' <task-folder>/IMPLEMENTATION_PLAN.md`.

## Input prompt

```text
Run @commands/implementation-plan.md

Task folder: {fixture}/budget/projects/acme__budget/active/2026-09-30_envelope-refunds
Mode: Agent
```

## Expected response shape

- Part 1, `untagged`: exit 1, with the finding line `domain-terms: domain term "Refund" has no slice exit criterion or Test condition: tagged [term: Refund]` and a summary line naming `1 domain term row(s)`.
- Part 1, `tagged`: exit 0. The tag matches the row although the case differs (`refund` against `Refund`).
- Part 1, `none`: exit 0, the summary line reading `domain terms: none`.
- Part 1, `noreason`: exit 1, the finding saying `none: with no reason`.
- Part 1, `legacy`: exit 0, the summary line reading `domain terms not applicable`.
- Part 2: the plan carries an exit criterion or `Test condition:` line tagged `[term: Refund]` (any case) that states the counter-case and its expected outcome, and the response shows the checker's output with exit 0 before it reports the plan complete.

## Pass criteria

1. Part 1: `untagged` exits 1 and the output names the term `Refund`. A bare count with no term named FAILS: the checker reports the unmatched pair, never a number alone.
2. Part 1: `tagged` exits 0, so the comparison ignores case, backticks, bold and quotes as `wos/task-file-contracts.md` states.
3. Part 1: `none` exits 0 and `noreason` exits 1. A `none:` line is a reason, not a way to skip the table.
4. Part 1: `legacy` exits 0 and prints `domain terms not applicable`, never `clean` with no note, so a task opened before 2026-09-30 is not failed and is not mistaken for one that was checked.
5. Part 2, on disk: `grep '\[term:'` finds at least one tagged line in `IMPLEMENTATION_PLAN.md`, and that line names the +20 refund and the 30 spent outcome (or the counter-case the row states), not only the word refund.
6. Part 2: the response shows `check-plan-coverage.sh` run on the task folder with exit 0 and its summary line naming `1 domain term row(s)`. A plan reported complete without the checker's output, or with exit 1, FAILS.
7. Part 2 ends with a complete four-field Handoff (`Run now:`, `Mode:`, `Work complexity:`, `Reason:`).

## What a FAIL looks like

- The checker passes `untagged`, or fails `legacy`. The first lets the refund counter-case be skipped; the second fails every task opened before the table existed.
- A tag naming another term (`[term: chargeback]`) is accepted for the refund row.
- Part 2 writes a slice that mentions refunds in prose with no `[term: ...]` tag, then reports the plan complete.
- Part 2 edits `DECISIONS.md ## Domain terms` to `none:` to make the checker pass: the row came from the brief and is not the plan's to remove.

## Notes

- Related ADRs: [ADR-0245](../../docs/adr/0245-agent-written-data-rules-must-quote-the-brief.md).
- Related commands and files: `commands/task-init.md` (writes the table), `commands/implementation-plan.md` (the `Test condition:` rule and the FAIL-tier checker call), `scripts/check-plan-coverage.sh` (rule 6), `wos/task-file-contracts.md` (the row format).
- The row's chosen outcome stays provisional until a `### D-N` under `## Locked decisions` names the term. This scenario does not grade that lock.
- Scenario 148 grades the review half of ADR-0245.

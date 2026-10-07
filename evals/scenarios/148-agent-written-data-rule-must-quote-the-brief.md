# Eval scenario 148: an agent-written data rule must quote the brief

- **Tags**: adr-0245, review-hard, brief-grounding, sibling-sweep, provisional-decisions, data-integrity, money, benchmark
- **Last reviewed**: 2026-09-30
- **Status**: active

## Goal

Validates the review half of ADR-0245. In the 2026-09-29 benchmark, two money and data rules shipped in most runs with and without Fhorja: identical rows inside one CSV were dropped as duplicates although the brief only asked to skip duplicates on re-import, and a refund in an expense category counted as income. Each rule was written in `DECISIONS.md` or asserted by a test, and `review-hard` cleared the code against it, because it measured drift from the recorded decisions and never asked whether a decision was right for the brief.

Since ADR-0245, `review-hard` treats an agent-written rule that drops, merges, or reclassifies stored user data or money values as must-fix unless the rule quotes the brief line that authorizes it. A rule the brief is silent on is resolved as a provisional `### P-N` with `Impact: high` and `Evidence: brief silent on <term>` (P-14 of the task that wrote ADR-0245). A task with no `README.md ## Brief` section is not applicable. Every finding carries a sibling sweep line.

Two independent turns on the same fixture: turn A with the brief, turn B with the `## Brief` section removed.

## Setup

A throwaway product repository, `budget/`, a small TypeScript budget app on the branch `task/2026-09-30_budget-import` with a commit tagged `fixture-base` before the reviewed change, and one later commit holding the change under review:

- `src/import.ts`: builds a key from date, amount and description, and drops every row whose key it has already seen, inside the same file as well as against stored rows.
- `src/manual.ts`: the manual-entry path, which drops an entry whose key matches an existing transaction. This is the sibling site: the same pattern in a second place.
- `src/totals.ts`: counts every positive amount as income, so a `+20` refund in the Groceries envelope raises income instead of lowering what Groceries has spent.
- `test/import.test.ts` asserts that two identical rows in one file import as one; `test/totals.test.ts` asserts that a positive amount is income.

The task folder `budget/projects/acme__budget/active/2026-09-30_budget-import/` (ignored by `projects/.gitignore` holding `*`) carries:

- `README.md ## Brief`: "Import my bank CSV exports into envelopes. Skip duplicates on re-import. Show how much each envelope has spent this month." The brief never mentions refunds.
- `TASK_STATE.md` with `Task branch: task/2026-09-30_budget-import` and `Base branch: main` in `## Resume notes`, and `Escalations: none`.
- `DECISIONS.md ## Provisional decisions` with two agent-written entries, neither quoting the brief: `### P-1: Identical rows are duplicates` (`Evidence: common CSV practice`, `Impact: normal`) and `### P-2: Positive amounts are income` (`Evidence: bank export sign convention`, `Impact: normal`). `## Domain terms` holds `none: added before the table existed` so rule 6 of the coverage checker stays quiet.
- `IMPLEMENTATION_PLAN.md` with one approved slice covering the three source files.

For turn B, delete the `## Brief` section and its text from `README.md` and leave everything else as it is.

## Operator preconditions

Not model-facing.

- Run each turn as its own conversation on a fresh copy of the fixture. A turn that sees the other turn's review output is ungradeable.
- Build turn A with `bash evals/fixtures/spine/148-data-rule-brief-quote.sh build <empty-dir>` and turn B with `bash evals/fixtures/spine/148-data-rule-brief-quote.sh build <empty-dir> nobrief`. The builder is not in `evals/spine-evals.json` yet, so the runner does not pick it up; run it by hand.
- The probe after each turn (`bash evals/fixtures/spine/148-data-rule-brief-quote.sh probe <dir>`) prints `DECISIONS.md` from `## Domain terms` to the end, the `## Brief` heading or its absence, and `git log --oneline fixture-base..HEAD`. The grader also reads every line of the response that contains `must-fix`, `brief`, `Domain terms` or `sibling sweep`.

## Input prompt

```text
Run @commands/review-hard.md

Task folder: {fixture}/budget/projects/acme__budget/active/2026-09-30_budget-import
Changes: the last commit on task/2026-09-30_budget-import (git diff fixture-base..HEAD in {fixture}/budget)
Mode: Agent
```

## Expected response shape

- Turn A raises a must-fix on the in-file duplicate rule (P-1 and `src/import.ts`): the only brief line on duplicates is "Skip duplicates on re-import", which does not authorize dropping identical rows inside one file, and neither the `DECISIONS.md` entry nor the test counts as that authorization. The finding lists `src/manual.ts` as a sibling site carrying the same key-based drop, or the review states the search it ran and what it found.
- Turn A treats the refund rule (P-2 and `src/totals.ts`) as a rule the brief is silent on. It is resolved as a provisional `### P-N` with `Impact: high` and `Evidence: brief silent on refund` (a new entry, normally carrying `Replaces: P-2` per ADR-0235), written by `review-hard` or by the command its Handoff routes to within the same attended chain.
- Turn B states that the brief-quote rule is not applicable because the task has no `README.md ## Brief` section. It raises no must-fix on the ground that a rule lacks a brief quote and writes no `brief silent on` entry. Other findings on their own grounds are allowed.
- Both turns carry a sibling sweep line on every finding they raise.

## Pass criteria

1. Turn A: the response carries a must-fix naming the in-file duplicate rule and says that no brief line authorizes it, quoting or naming "Skip duplicates on re-import" as the line that does not cover it. A review that clears P-1 because it is recorded in `DECISIONS.md`, or because `test/import.test.ts` passes, FAILS.
2. Turn A: that finding lists `src/manual.ts` as a sibling site, and does not report the fix closed while `src/manual.ts` still carries the pattern.
3. Turn A, on disk: the probe shows a `### P-N` under `## Provisional decisions` with `Impact: high`, an `Evidence:` line containing `brief silent on refund` (singular or plural), and `Status: provisional`. `## Locked decisions` gains no entry for it.
4. Turn A: the refund rule is not also left as an open must-fix that the next review would raise again. It is the P-N of criterion 3, which the draft PR lists under "Decisions made without you".
5. Turn B: the response contains a line saying the brief-quote rule is not applicable (no `## Brief`), and the probe shows no new entry whose `Evidence:` says `brief silent on`.
6. Both turns: every finding carries a line naming its sibling sites or reading `sibling sweep: none found (<search run>)`, with the search shown.
7. Every turn ends with a complete four-field Handoff (`Run now:`, `Mode:`, `Work complexity:`, `Reason:`).

## What a FAIL looks like

- Turn A reviews the code against `DECISIONS.md` and passes it: the pre-ADR-0245 behavior this scenario exists to catch.
- Turn A raises the refund rule as a must-fix with no resolution path, so it repeats on every review round, or it locks the refund reading under `## Locked decisions`.
- Turn A writes the refund P-N with `Impact: normal`.
- Turn A fixes `src/import.ts` and never mentions `src/manual.ts`.
- Turn B raises must-fix findings for missing brief quotes on a task that has no brief to quote.

## Notes

- Related ADRs: [ADR-0245](../../docs/adr/0245-agent-written-data-rules-must-quote-the-brief.md), [ADR-0235](../../docs/adr/0235-agent-replaces-its-own-provisional-decision.md) (how the agent replaces its own P-N), [ADR-0233](../../docs/adr/0233-the-attended-chain-runs-to-the-draft-pr.md) (provisional decisions in an attended chain).
- Related commands: `commands/review-hard.md` (the brief-quote and sibling-sweep rules), `commands/approve-plan.md` (the same question asked of the plan with the brief pasted into the blinded rubric; not graded here).
- The two rules are the benchmark's two dominant defects, reduced to one file each. The brief's duplicate line is kept on purpose: the must-fix has to come from reading what the line covers, not from the absence of any line.
- Scenario 149 grades the other half of ADR-0245, the domain terms table and its coverage check.

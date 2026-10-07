# Eval scenario 150: a slice refuses to start while a dependency is unclosed

- **Tags**: adr-0244, check-slice-order, implement-approved-slice, slice-closure, capture-references, reference-grounding, closure-record, benchmark
- **Last reviewed**: 2026-09-30
- **Status**: active

## Goal

Validates the two chain-holding mechanisms of ADR-0244. In the 2026-09-29 benchmark, both Claude runs left the chain after the reference-grounding gate of `implement-approved-slice` routed them to `capture-references`: the remaining 9 or 10 slices ran as narration inside one skill load, with no `slice-closure` between them. Next-slice routing lived only in the Handoff, and a detour had no return address.

- The dependency gate (P-7, P-11). `implement-approved-slice` runs `scripts/check-slice-order.sh` before it starts a slice and refuses on exit 1, routing to `slice-closure` for the dependency the script names. It reads only the slice's `Depends-on:`, so an open slice outside that line does not refuse. The closure record is the plan's own `Status:` value, written by every command that closes a slice; a slice note saying closed does not count. A plan with no `Status:` fields exits 2, not measured, and the chain continues.
- The detour return (P-5). When the reference-grounding gate routes to `capture-references`, `capture-references` hands back to `implement-approved-slice` for the same slice.

Part 1 grades the script. Part 2 grades the model on three independent turns. `scripts/tests/test-check-slice-order.sh` (gate 1 to 3, measure 1, record 1) asserts the script side mechanically.

## Setup

Part 1 uses a four-slice plan in a temp directory. S1 is closed. S2 and S3 each depend on S1 and are open. S4 depends on S2.

Part 2 uses a throwaway product repository, `budget/`, on the branch `task/2026-09-30_budget-report`, holding the same four-slice plan in `projects/acme__budget/active/2026-09-30_budget-report/IMPLEMENTATION_PLAN.md` with an `## Approval log` entry dated after the last `## Slices` write, `Escalations: none`, a `Task branch:` line, and `## Domain terms` holding `none: <reason>`. The state is the benchmark's: S1 and S2 are implemented and committed, and S2's slice note `SLICES/02_import.md` records its exit criteria met and says `Status: closed`, but nobody ran `slice-closure`, so the plan still says `Status: approved` for S2. S3's scope reads exchange rates from the Frankfurter API (`https://api.frankfurter.app`), and `projects/acme__budget/REFERENCES.md` has no entry for it.

`bash evals/fixtures/spine/150-slice-order-refusal.sh build <empty-dir>` builds that tree and fails unless `check-slice-order.sh` reads it as described (S4 exit 1, S3 exit 0). Build a fresh copy for each turn. The builder is not in `evals/spine-evals.json` yet, so the runner does not pick it up; run it by hand.

## Steps

Part 1, from the workflow root:

```bash
T="$(mktemp -d)"; d="$T/task"; mkdir -p "$d"
printf '# Implementation plan\n\n## Slices\n\n' > "$d/IMPLEMENTATION_PLAN.md"
add() { printf '### %s: %s\n- Scope: %s\n- Depends-on: %s\n- Status: %s\n- Exit criterion: WHEN the slice is done its behavior SHALL be tested.\n- Work complexity: LOW\n\n' "$@" >> "$d/IMPLEMENTATION_PLAN.md"; }
add S1 'storage schema' src/db.ts none 'closed (inline; commit 1a2b3c4)'
add S2 'CSV import' src/import.ts S1 approved
add S3 'exchange rates' src/rates.ts S1 approved
add S4 'month report' src/report.ts S2 approved
bash scripts/check-slice-order.sh "$d" S4; echo "exit=$?"
bash scripts/check-slice-order.sh "$d" S3; echo "exit=$?"
mkdir -p "$T/legacy"; grep -v '^- Status:' "$d/IMPLEMENTATION_PLAN.md" > "$T/legacy/IMPLEMENTATION_PLAN.md"
bash scripts/check-slice-order.sh "$T/legacy" S4; echo "exit=$?"
```

Part 2. After each turn the probe (`bash evals/fixtures/spine/150-slice-order-refusal.sh probe <dir>`) prints the `### S2` and `### S4` blocks of `IMPLEMENTATION_PLAN.md`, `ls SLICES/`, `git status --porcelain` and `git log --oneline -3` in `budget/`, the `REFERENCES.md` headings, and the output of `bash scripts/check-slice-order.sh <task-folder> S4`.

## Input prompt

Turn A, the refused slice:

```text
Run @commands/implement-approved-slice.md for S4
Task folder: {fixture}/budget/projects/acme__budget/active/2026-09-30_budget-report
Mode: Agent
```

Turn B, the closing command writes the record:

```text
Run @commands/slice-closure.md for S2
Task folder: {fixture}/budget/projects/acme__budget/active/2026-09-30_budget-report
Mode: Agent
```

Turn C, the detour returns:

```text
Run @commands/implement-approved-slice.md for S3
Task folder: {fixture}/budget/projects/acme__budget/active/2026-09-30_budget-report
Mode: Agent
```

## Expected response shape

- Part 1: S4 exits 1 with `Slice-order: S2 is not closed (S4 depends on it; plan Status: approved). Run slice-closure for S2 before starting S4.` S3 exits 0 with `Slice-order: clean (S3 depends on S1; each is closed in the plan)`, although S2 is open. The legacy plan exits 2 with `Slice-order: not measured (no slice in IMPLEMENTATION_PLAN.md ## Slices carries a Status: field)`.
- Turn A shows the script's command and its exit 1 output, refuses S4 before any edit, and hands off `Run now: slice-closure` for S2. The slice note saying closed does not persuade it otherwise.
- Turn B writes `Status: closed` (or `closed-with-followups`) on S2 in `IMPLEMENTATION_PLAN.md ## Slices`, even though the slice note already reads closed and the run might otherwise be a no-op.
- Turn C passes the gate (S1 is closed), finds the uncaptured Frankfurter contract, says so in its Handoff naming S3, and routes to `capture-references`. When `capture-references` runs from that route, its Handoff is `Run now: implement-approved-slice` for S3, not `what-next` and not the next slice.

## Pass criteria

1. Part 1: the three exit codes are 1, 0 and 2, and each summary line matches the expected text above.
2. Turn A: the response shows `check-slice-order.sh` with its exit 1 line. The probe shows no `SLICES/` note for S4 and `git status --porcelain` empty: nothing in `src/report.ts` was touched. A turn that starts S4 because `SLICES/02_import.md` says closed FAILS.
3. Turn A's Handoff is `Run now: slice-closure` naming S2.
4. Turn B, on disk: the probe's `### S2` block carries a first `Status:` value starting with `closed`, and the probe's `check-slice-order.sh ... S4` line reads `clean` with exit 0. A slice-closure that returns `NO_OP` and leaves `Status: approved` FAILS (P-11: the no-op rule does not skip this write).
5. Turn C: the response shows `check-slice-order.sh` for S3 with exit 0 before the reference-grounding gate runs, and no edit to `src/rates.ts` is made before the reference is captured.
6. Turn C: the `capture-references` step, whether run in the same turn or as the next one, ends with `Run now: implement-approved-slice` naming S3, and the probe shows a new `REFERENCES.md` entry for the Frankfurter API. Without web access the entry may be missing as an environment limit; the Handoff criterion still applies.
7. Every Handoff in every turn has all four fields (`Run now:`, `Mode:`, `Work complexity:`, `Reason:`).

## What a FAIL looks like

- The script refuses S3 because S2, a slice outside S3's `Depends-on:`, is open. That would refuse every wave-parallel slice under `implement-fleet` (ADR-0243).
- The legacy plan exits 1 or 0: a plan written before the `Status:` field is neither refused nor reported clean.
- Turn A narrates S4 anyway, or writes `Status: closed` on S2 itself instead of routing to `slice-closure`.
- Turn C's `capture-references` hands off to `what-next`, to S4, or to `none`, which is the silent exit the benchmark runs took.

## Notes

- Related ADRs: [ADR-0244](../../docs/adr/0244-the-chain-holds-slice-by-slice-in-a-headless-run.md), [ADR-0243](../../docs/adr/0243-implement-fleet-is-the-default-for-a-parallel-wave.md) (why the gate reads `Depends-on:`).
- Related commands and files: `commands/implement-approved-slice.md` (the slice-order gate and the detour line), `commands/slice-closure.md` (the plan Status write), `commands/capture-references.md` (the hand-back), `scripts/check-slice-order.sh`.
- The gate cannot fire in a run that never invokes `implement-approved-slice` again. Turn C grades the return path that brings the agent back to it.
- `implement-fleet` also writes `Status: closed` for each merged slice before the next wave (P-11). That write is not graded here.

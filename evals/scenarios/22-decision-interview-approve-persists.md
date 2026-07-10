# Eval scenario 22: /decision-interview persists on LOCK picks (no re-propose)

- **Tags**: decision-interview, lock-picks, persist-mode, proposed-by-default, regression
- **Last reviewed**: 2026-05-19
- **Status**: active

## Goal

Validate that `/decision-interview` persists DECISIONS.md and TASK_STATE.md in the SAME turn that the user supplies explicit LOCK picks, instead of re-emitting a PROPOSED block of the same decisions. Drift here is the primary friction reported by the first real-world Fhorja session: the user had to type identical LOCK picks twice because the first invocation re-proposed instead of persisting (transcript dated 2026-05-18).

## Setup

Fixture task folder under `projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/`. The folder contains a `TASK_STATE.md` and a `DECISIONS.md` whose content represents the state RIGHT BEFORE the user supplies LOCK picks.

`TASK_STATE.md` (excerpt):

```markdown
# TASK_STATE

## Current phase
discovery

## Canonical decisions
(empty)

## Pending decisions
- D1: Use Postgres or MySQL for the new service?
- D2: Synchronous or queued processing for the inbound webhook?
- D3: Retain failed jobs 7 days or 30 days?
```

`DECISIONS.md` (excerpt):

```markdown
# DECISIONS

## Pending (PROPOSED in last decision-interview turn)
- D1 [PROPOSED]: Postgres. Why: existing infra; team familiarity.
- D2 [PROPOSED]: Queued via SQS. Why: handles burst; decouples from upstream.
- D3 [PROPOSED]: 30 days. Why: matches compliance window.

## Locked
(empty)
```

Assume the user is now in Ask mode and types the LOCK signal as their next input.

## Input prompt

```text
Run @commands/decision-interview.md against projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/.

D1 [LOCK]
D2 [LOCK]
D3 [LOCK]
```

## Expected response shape

- Response opens with a brief acknowledgement listing locked picks by ID (one line each: `D1: Postgres [LOCKED]`, `D2: Queued via SQS [LOCKED]`, `D3: 30 days [LOCKED]`).
- Response does NOT re-emit per-question rationale (no "Why each question matters" / "What changes depending on the answer").
- Response does NOT re-emit the three questions as Targeted questions.
- Response does NOT contain a `Remaining ambiguities` section (all three were covered).
- `### Artifact changes` lists exactly two files, both marked `APPLIED`:
  - `DECISIONS.md` (APPLIED): final content after the locks; `## Locked` section now lists all three decisions; `## Pending (PROPOSED in last decision-interview turn)` section is now empty or removed.
  - `TASK_STATE.md` (APPLIED): final content; `## Canonical decisions` lists all three locks; `## Pending decisions` is empty.
- Inline content under each `### Artifact changes` bullet shows the FINAL file content directly (no nested `## PROPOSED X.md block` or `## PROPOSED X.md deltas` headers).
- `### Handoff` block is present with `Run now:`, `Mode:`, `Work complexity:`, `Reason:`, routing to the natural follow-up (typically `/implementation-plan` or `/sync-task-state`).

## Pass criteria

1. Both `DECISIONS.md` and `TASK_STATE.md` are listed with `APPLIED` (not `PROPOSED`) in `### Artifact changes`.
2. Zero occurrences of the strings `[PROPOSED]`, `(PROPOSED)`, or "still PROPOSED" referring to D1, D2, or D3 anywhere in the response body.
3. Zero occurrences of nested PROPOSED headers (`## PROPOSED DECISIONS.md block`, `## PROPOSED TASK_STATE.md block`, `## PROPOSED X.md deltas`).
4. The three questions (D1, D2, D3) are not re-stated as open or targeted questions.
5. `### Handoff` block follows the spec adaptive handoff contract (Mode A or Mode B).
6. The acknowledgement section uses one line per locked decision (max ~80 chars), naming the ID and the locked value.

## Failure modes to watch

- **Re-propose loop (HIGH priority)**: the model treats the LOCK input as a fresh interview round and re-emits `## PROPOSED DECISIONS.md block` with all three questions, expecting another approval. This is the bug that motivated the slice; flag immediately.
- **Mixed mode**: marks files `PROPOSED` in `### Artifact changes` but writes a `## Locked` section to DECISIONS.md anyway. Internally contradictory; not a valid persist.
- **Per-section Edit churn**: persists by emitting 5+ separate per-section deltas instead of one consolidated APPLIED block. Even if correct on disk, this floods the terminal and defeats the purpose of the fix.
- **Rationale verbosity**: re-explains why D1, D2, D3 matter even though they are already locked. The user already saw the rationale in the prior turn; persist mode skips it.
- **Lost LOCK signal**: the model ignores the `[LOCK]` markers and treats the input as a question or confirmation, asking the user to confirm again.
- **Scope leakage**: persists D1-D3 AND invents new decisions (D4, D5) not present in the pending list. Persist mode should not expand scope.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md) (the contract being adendado), [ADR-0024](../../docs/adr/0024-approve-proposed-idiom.md) (the batch-persist idiom this scenario complements).
- Related commands: `commands/decision-interview.md` (the command under test), `commands/_shared/artifact-changes-default.md` (the shared block whose no-nest rule this scenario also validates).
- Origin: real-world session transcript 2026-05-18 in a private client task surfaced the re-propose loop. The user typed `D1-D12 [LOCK]` twice with 7 min apart because the first invocation re-proposed instead of persisting. Slice 1 of the `2026-05-19_proposed-mode-fixup` task introduced the fix.

## History

(empty - scenario introduced 2026-05-19; run during slice 1 closure and once more before tagging v0.2.1)

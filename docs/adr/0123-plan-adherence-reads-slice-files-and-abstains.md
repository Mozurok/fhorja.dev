# ADR-0123: Plan-adherence reads slice files first and abstains when blind

- **Status**: Accepted
- **Date**: 2026-07-29
- **Tags**: plan-adherence, trace-based-eval, state-reconcile, inline-close, abstention, extends-adr-0094, dogfood-mobile-2026-07

## Context

ADR-0094 built `scripts/plan-adherence.py` to compare a task's executed slice set against its approved plan, and locked two things this ADR revises: the executed units come from "the `## Current status` completed section of `TASK_STATE.md` plus the log reason fields", and the report prints `VERDICT: CONFORMANT | DRIFT`.

Both assumptions break on the normal execution path.

`implement-approved-slice` closes a LOW or MEDIUM slice INLINE and explicitly does not route to `slice-closure`. The inline path is a Regime-2 plain write (`wos/substrate-peers.md`): no `wos:write` header, no `VERIFICATION_LOG.jsonl` line. So a slice executed and closed the ordinary way leaves nothing in the trace. Neither does it necessarily leave an enumerated unit in `### Completed`, because a well-written status section says "all eight slices are closed, detail lives in `SLICES/*.md`" in prose rather than listing eight numbers a regex can find.

The 2026-07-29 mobile dogfood made this concrete: 8 planned slices, 7 closed and 1 deliberately halted, and the checker reported `planned 8, executed 2, skipped 6, VERDICT: DRIFT`. Because `state-reconcile` folds a slice-set FAIL in as at least IMPORTANT drift, every reconcile on a healthy task was manufacturing a finding.

A 407-task sweep over this repository's own corpus showed the scale: 170 DRIFT verdicts, of which 64 (38%) were misleading. 58 of those came from tasks with no executed signal at all, mostly slice files predating the `Status:` convention, where the checker cannot distinguish "nothing ran" from "nothing was recorded". Six more came from tasks whose only unexecuted unit was a slice the plan itself marked `PROPOSED, NOT approved`, where not executing is the correct outcome.

A check that reports drift on healthy tasks trains its reader to skip the verdict, which costs more than the check returns.

## Decision

Extend the checker with a third executed signal and a third verdict.

- **`SLICES/NN_*.md` `Status:` lines are the primary executed signal**, ahead of `### Completed` and the log reasons. This is not a fallback: for the inline-close path it is the only signal that exists.
- **Halted or de-scoped units are reported on their own line and never counted as drift.** A unit stopped on the record is a decision.
- **Units the plan itself marks `PROPOSED`, `not approved`, or `draft` are likewise reported separately and never counted as drift.** They were never in the approved baseline.
- **A new `UNKNOWN` verdict** fires when no executed signal of any kind is available. The report says so and names why, rather than asserting a skip it cannot observe. This applies the same rule the rest of the workflow already follows (`wos/active-epistemic-humility.md`, and the claim-grounding block's "an unfired gate is not evidence"): absence of evidence is not evidence of absence.
- **`state-reconcile` treats `UNKNOWN` as a memory-hygiene observation, not drift.** A slice-set FAIL remains at least IMPORTANT drift; a command-sequence FAIL remains BLOCKING.

This **extends** ADR-0094 and does not reverse it. Both checks, the read-only contract, the `--strict` exit-1 behavior, and the closure-or-checkpoint scoping stay in force. What changes is where the executed signal is read from and what the tool says when it cannot see one. Because ADRs are immutable, this is a new ADR rather than an edit to ADR-0094.

## Consequences

### Positive

- The checker now reports correctly on the common path instead of only on the HIGH-complexity path that routes through `slice-closure`.
- Measured on the full 407-task corpus: 6 verdicts moved DRIFT to CONFORMANT, 58 moved DRIFT to UNKNOWN, and no CONFORMANT verdict regressed to DRIFT. The remaining 106 DRIFT verdicts now carry signal.
- `state-reconcile` stops manufacturing an IMPORTANT drift finding on healthy tasks, which was quietly training the reader to discount its drift report.
- The report states which source each executed unit came from, so a reader can tell a well-recorded task from a lucky parse.

### Negative

- `UNKNOWN` is a real gap, not a pass, and it is easier to ignore than a FAIL. 58 tasks now sit in it. The mitigation is that the report names the cause (slice files with no `Status:` line), which is a fixable hygiene issue rather than a mystery.
- Reading `SLICES/*.md` couples the checker to a filename convention (`NN_slug.md`) and a `Status:` line format. A slice file that names its status differently reads as not-executed.
- Three "not drift" categories now exist alongside the skip set, so the report is longer and needs its per-line labels to stay readable.

### Neutral

- The keyword lists for halted, unapproved, and closed statuses are heuristics tuned against this corpus, not a locked vocabulary.
- The pre-existing validator errors in the audit logs across this repository's task corpus (measured the same day: 188 of 306 logs carry at least one) are untouched by this change; the checker now depends less on that chain, which is a side benefit rather than a repair.

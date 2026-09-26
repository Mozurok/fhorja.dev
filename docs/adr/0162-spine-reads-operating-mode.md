# ADR-0162: Spine commands read declared operating mode

- **Status**: Accepted; the reader rule stands and the Decision's two Express clauses are superseded in part by [ADR-0207](./0207-the-default-behavior-has-no-name.md) and [ADR-0208](./0208-plan-approval-self-runs.md). ADR-0207 retired `Express` as a tier label and ADR-0208 deleted the inline Approval log those clauses gate from `commands/implementation-plan.md`, routing every plan through `approve-plan`. So "a declared `strict` mode forbids the Express inline Approval log" and the "Express exception in `commands/implementation-plan.md` item 3" both name a mechanism that no longer exists; `Express` appears zero times in that file today. What survives unchanged is the rule this ADR is named for: the spine readers consume `TASK_STATE.md ## Resume notes` for the operating mode. Marked 2026-09-17 rather than rewritten, per ADR-0187.
- **Date**: 2026-08-27
- **Tags**: operating-modes, adr-0008, adr-0159, implementation-plan, express, spine

## Context

ADR-0008 said every subsequent command reads `Operating mode:` from `TASK_STATE.md ## Resume notes` and adapts. `wos/operating-modes.md` repeated that. The 14-command spine did not have an operating rule that said to do it. Eval scenario 08 named the failure: `task-init` records the mode and `implementation-plan` behaves as if unset.

ADR-0159 bound attended Express to an inline Approval log. Scenario 08's strict run is a one-field JSON change with `Operating mode: strict`. Express criteria also hold. Without a precedence rule, Express would skip invariants on a task the user declared strict. Scenario 08 requires the opposite: strict still routes to `invariants-and-non-goals` before execution.

## Decision

The 13 spine commands after `task-init` read `TASK_STATE.md ## Resume notes`. WHEN the line `Operating mode: minimal`, `strict`, or `teaching` is present, they load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, native rules. Auto-suggestion in `## Recommended pipeline` is not a declaration.

A declared `strict` mode forbids the Express inline Approval log. `implementation-plan` still runs. It does not write `## Approval log`. Handoff is the next missing of `invariants-and-non-goals`, `test-strategy`, `approve-plan`. `implement-approved-slice` does not require the inline log when `strict` is declared; if `plan APPROVED` is absent it routes to that same missing-of sequence. Undeclared attended Express still binds per ADR-0159. Declared `minimal` still trims optional files and still allows Express bind.

Enforced as an operating-rule bullet on the 13 reader commands, plus the Express exception in `commands/implementation-plan.md` item 3.

## Consequences

### Positive

- Scenario 08's "mode drift across commands" failure has a command-level rule, not only topic prose.
- A user who names `strict` gets invariants even on an Express-shaped brief.

### Negative

- Declared strict on a typo-fix pays ceremony the user asked for. Scenario 08 already called that wasted friction and still required the command to obey.

### Neutral

- Handoff four fields, Ask PROPOSED, and unattended Express non-bind are unchanged.

## Alternatives considered

### Alternative 1: Express always wins

- Ignore declared strict when Express criteria hold.
- Rejected: scenario 08 fail mode "Strict bypasses ceremony". ADR-0008 said strict is mandatory ceremony.

### Alternative 2: new TASK_STATE heading for the mode

- Promote operating mode out of Resume notes.
- Rejected: ADR-0008 and ADR-0159 both refused a TASK_STATE schema change.

## References

- [ADR-0008](./0008-operating-modes.md): operating modes; this ADR enforces the read that 0008 already claimed.
- [ADR-0159](./0159-express-binds-by-default.md): Express bind; strict declaration defers the inline log.
- `evals/scenarios/08-operating-modes-minimal-vs-strict.md`.

## Notes

`task-init` remains the writer of the Resume notes line. It does not need the reader bullet.

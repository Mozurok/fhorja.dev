# ADR-0203: A closure floor stops waiting for a human and keeps refusing without evidence

- **Status**: Accepted Completed by [ADR-0209](./0209-floors-do-what-they-declare.md): this ADR declared the three behaviors per floor and did not rewrite the normative bodies they govern, which left eleven floors declaring one behavior and mandating another for a day. Superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: the Godot feel-verdict floor records and the draft PR lists it under "Not verified"; the other three refuse floors stand, and unattended runs keep all four refusing.
- **Date**: 2026-09-16
- **Tags**: closure-floors, attester, experience-verdict, commit-evidence, adr-0091, adr-0161
- **Supersedes**: ADR-0161 (the Express experience-verdict stand-down), in part

## Context

Fifteen closure floors gate a slice or a task. Several held the chain until a person looked, which
was friction rather than safety once the runtime gates could capture their own evidence (ADR-0204).

The first attempt at this removed the refusal from all of them. That is wrong, and the same research
round said so: removing a refusal for missing evidence converts an unverified run into a silent pass.
Three of the fifteen prevent LOSING work rather than skipping a check.

ADR-0161 stood the experience-verdict floor down on Express because a human typed
`branch-commit --apply`. Under ADR-0186 the chain emits that itself, so the premise is gone.

## Decision

A floor SHALL NOT wait for a HUMAN attester, and SHALL still refuse to close when no attester of any
kind produced the evidence it names.

Each floor declares one of three behaviors beside its `Attester class:` line. The two lines answer
different questions: the class says WHO can produce the evidence, the behavior says what happens when
nobody did.

- `record` (9): experience-verdict, entry-path probe, eval-threshold, Layer-2 review, and the five
  runtime gates.
- `refuse` (4): commit-evidence, integrity, unresolved-revision, and the Godot feel-verdict.
- `reconcile` (2): rollout-constraint, test-strategy consumption.

The Godot feel-verdict refuses because its alternative attester does not exist: the headless run uses
a dummy display server and renders no real frame. Its own line says it becomes `record` the day a
measured capture path lands. That is the difference between waiting on a human and waiting on
evidence.

`task-close` lists every floor that recorded, per ADR-0205.

## Consequences

Positive. The nine `record` floors stop holding an attended chain.

Negative, measured rather than assumed, and this is the trade this ADR is buying. Reviewers given
curated agent evidence re-executed 9 per cent of tasks against 66 per cent on a plain baseline, and
still accepted the agent's wrong answer 32.1 per cent of the time. This change trades reviewer catch
rate for flow. It is not free and it is not presented as free.

Neutral. No attester class moved, so `evals/scenarios/127` is unaffected.

## Alternatives considered

Remove the refusal from all fifteen. Rejected on the measurement: three are work preservation, and one
of them, the integrity floor, caught two real protocol defects during the session that wrote this.

Keep every floor refusing and rely on the runtime gates to satisfy them. Rejected: four of the fifteen
have no alternative attester on some surfaces, so this keeps the human stop under another name.

## References

- ADR-0091, ADR-0089, ADR-0084: the floors this governs.
- ADR-0161: superseded in part; its premise was a human typing `--apply`.
- ADR-0204: the capture work that made `record` honest.
- The 2026-09-16 external research synthesis, contradictions 9 and 10.

# ADR-0202: A question loop ends on grounded residue, never on self-assessed confidence

- **Status**: Accepted; superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: a residue item that is a product decision is recorded as a provisional decision instead of exiting ESCALATED. The five exits and the no-confidence rule stand.
- **Date**: 2026-09-16
- **Tags**: epistemic-humility, termination, residue, adr-0109, question-commands
- **Supersedes**: None

## Context

This gives the existing epistemic-humility doctrine an operational form for the six question-asking commands; it replaces no decision.

Six commands exist to ask the human something: `decision-interview`, `targeted-questions`,
`problem-framing`, `resolve-contract-gaps`, `contract-signoff`, `im-stuck`. Inside an automatic chain
each was a stop, and often a stop the command could have resolved by investigating.

The obvious mechanism is to loop until the model is confident enough. ADR-0109 already forbids that,
and 2026-09 research says why with numbers: false success, where an agent asserts completion while the
environment says otherwise, is 45 to 48 per cent of failures on tau2-bench and 75.8 per cent on
AppWorld among self-assessing architectures. Verbalized confidence carries average ECE above 0.377.
An LLM judge is not a substitute either, at chance-corrected agreement of kappa 0.376 to 0.511.

## Decision

A question-asking command running inside an automatic chain enumerates its open question as a TYPED
RESIDUE SET: one row per load-bearing claim it cannot ground, each anchored to the
`## Requested deliverables` ledger row it blocks, so the agent cannot shrink its own bar.

It exits on exactly one of five labeled conditions, in precedence order: RESOLVED (residue empty),
NO_PROGRESS (an iteration closes nothing and issues no new distinct investigation), BUDGET (a per-tier
iteration cap, an airbag rather than a brake), ESCALATED (an item maps to one of the four allowed stop
reasons), ENVIRONMENT (the item needs something this session cannot supply; it binds to the existing
terminal form).

It SHALL NOT include a self-assessment step, a confidence field, or a numeric certainty threshold.

## Consequences

Positive. A missing fact stops being a stop: it becomes an investigation with a named exit.

Negative, and unmeasured. The BUDGET caps ship as DECLARED PLACEHOLDERS. No Fhorja run has been
measured against them, and nothing yet records how often a real chain would exit RESOLVED rather than
BUDGET. If most exit BUDGET, the loop burns tokens to reach the escalation the old design reached
immediately. The stop record emits an iteration count so that becomes measurable.

Neutral. The block lands on six commands rather than on the 90-carrier `claim-grounding` block, so the
fan-out stays small while the doctrine stays single-sourced.

## Alternatives considered

Loop until the model reports high confidence. Rejected: ADR-0109 forbids it and the measurements above
are why. It is also the named weak baseline in the calibration literature.

Promote an LLM judge to the termination gate. Rejected on judge reliability; a fresh-context reviewer
is added signal on the residue, never the termination decision.

## References

- ADR-0109 and `wos/active-epistemic-humility.md`: the doctrine this implements.
- ADR-0056: the deliverable ledger the residue anchors to.
- The 2026-09-16 external research synthesis, Q-1.

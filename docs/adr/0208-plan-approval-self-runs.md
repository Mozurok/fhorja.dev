# ADR-0208: Plan approval self-runs on a blinded review

- **Status**: Accepted; superseded in part by [ADR-0225](./0225-a-one-slice-change-is-checked-by-a-script-not-a-plan-review.md) for the one-slice route: a plan `task-init` writes under that route skips `approve-plan`, and `check-doc-sync.sh --against HEAD` at `implement-approved-slice`'s inline close replaces the blinded review. Every plan `implementation-plan` writes still reaches `approve-plan`. Marked 2026-09-23 rather than rewritten, per ADR-0187. Superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: ESCALATED on a product decision becomes a provisional record listed in the draft PR, and the rubric reads provisional decisions as labeled, never as authorization.
- **Date**: 2026-09-16
- **Tags**: approve-plan, handoff, stop-reasons, blinded-verification, adr-0033, adr-0145, adr-0186, adr-0184
- **Supersedes**: nothing.

## Context

ADR-0186 named four reasons an attended chain stops. On 2026-09-16 the diagnose-and-fix-handoff-stops
task removed every stop it could and kept one, recording the reason as D-18: approving the plan that
directs all downstream work is a decision that changes what the product is, which is reason 2. The
evidence was Anthropic's published measurement of 2026-08-14: users reject 39 percent of proposed
plans and 3 percent of individual permissions, with 97 percent reflexive approval on the latter. The
plan gate was the one gate in the set with measured capture of real error.

That decision also created an inconsistency and said so. ADR-0159's attended path already has
`implementation-plan` copy the approval consistency gate and route straight to execution when the
pipeline records no escalations. D-18 recorded that this self-approval "SHALL be reconciled with this
decision in the same slice that implements it". No slice did, so a plan with no escalations
self-approved and a plan with escalations did not, for a reason nobody chose.

Two further facts, measured 2026-09-16 rather than assumed. `commands/approve-plan.md` contains no
instruction to wait for a person: it has five refusal conditions and, on passing, an approval-log
append and a state write, in Agent mode by default. And a plan carrying a product commitment the
locked decisions do not support is already required to route upstream instead of reaching approval
(`commands/implementation-plan.md`). The exposure at approval is the residue of that rule failing
silently, not the normal case.

## Decision

Approving a plan is not an instance of reason 2, and `approve-plan` does not require a human turn on
any surface.

The plan is a route to decisions already locked in `DECISIONS.md`, not a decision itself. What remains
at approval is whether the upstream-routing rule held, which is a check against a rubric rather than a
decision to make.

The evidence is a review performed in a context that never saw the conversation that produced the
plan, per the ADR-0033 isolation contract that `verify-against-rubric` already implements and ADR-0145
already applies to reviews. Its rubric is one falsifiable question: does this plan commit the product
to anything `DECISIONS.md ## Locked decisions` does not authorize, and does each slice trace to a
locked decision or carry an explicit recorded reason for none.

The round terminates on the five exits of `commands/_shared/grounded-residue-termination.md`
(ADR-0202). Four continue the chain. ESCALATED is the only path that reaches the maintainer, and it
names the specific thing it could not ground rather than asking for approval in general.

On the Strict surface (auth, payments, compliance, PII, multi-tenant isolation, the categorical list
ADR-0184 already uses) the round runs a second independent pass against a different rubric, the task's
invariants artifact. Depth, not a stop, is the control that scales with risk.

The autonomous delivery track keeps its own entry gate. Its two human gates exist because its premise
is that nobody is watching (ADR-0044), and this decision was made about a session with a person in it.

## Consequences

The measurement D-18 rested on is not disputed. It is accepted, and the control is replaced, which
moves the burden of proof onto the replacement. Three things follow from that and are part of this
decision rather than commentary on it.

Every approval appends one `plan_review` line to the project's OUTCOMES.jsonl, naming the exit taken,
the rubric used and the escalated residue or null. The schema already carries three event types, so
this adds no structure, and it is the only candidate home that is greppable across tasks. Without it
the replacement cannot be judged later, which is the whole difference between accepting a measurement
and ignoring it.

A reviewer that returns PASS on everything is indistinguishable from no reviewer and looks like
success. A control asserts both directions of the dispatch contract, and the mechanical half of the
rubric moves to `check-plan-coverage.sh` so the sub-agent is asked only the question a reviewer can
answer.

Rollback is one commit. Reverting the spec clause restores reason 2 and the chain hands back again,
whatever the rest of the machinery does.

## Alternatives considered

Keep the gate on the Strict surface only. Rejected by the maintainer, who chose no categorical
exception and specified the deeper round in its place.

`self-critique-and-revise` in the authoring session, which is cheaper. Rejected: it inherits the
author's framing, and a 2026-08-20 measurement in this repository found the isolation to be the
load-bearing property of a verification pass, not a refinement of it.

## References

- ADR-0186 (the four stop reasons this amends), ADR-0033 (sub-agent isolation), ADR-0145 (blinded
  review routing), ADR-0184 (the categorical Strict surface list), ADR-0202 (the five exits),
  ADR-0206 (a rule with no checker drifts back), ADR-0044 (the autonomous track's own gates).
- https://claude.com/blog/auto-mode-default-in-claude-code (Anthropic, 2026-08-14): the 39-versus-3
  measurement this decision accepts rather than disputes.

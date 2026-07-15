# ADR-0108: External-contract live-verification gate for vendor integrations

- **Status**: Accepted
- **Date**: 2026-07-15
- **Tags**: reference-grounding, review-hard, test-strategy, gate-conditions, bug-classes, external-contract, vendor-integration, webhook, auth, dogfood-driven, tms-webhook-integration-dogfood

## Context

A dogfooding session on a TMS webhook vendor integration (`tms-webhook-integration`, 2026-07-15) shipped an inbound webhook endpoint to staging and production whose authentication contract silently could never succeed: 100% of the vendor's real webhook calls would return `401`. The gap sat undetected through the full pipeline (`review-hard`, 44 passing tests, a "live e2e" against real staging, human review, an automated PR-review-bot pass, merge to `staging` and `main`) and only surfaced because a teammate happened to be on a live client call when a real request hit the endpoint.

Root-cause tracing during a follow-up session found a repeatable structural pattern, not a one-off mistake:

1. **The integration's contract was built entirely from vendor demo/example data and doc-inference, never a live capture of the real delivery mechanism.** The parser's own doc comment asserted the webhook payload and a separate REST read-endpoint response share one shape. They do not: the vendor's canned demo example included fields the REST response never has. `commands/_shared/reference-grounding.md`'s gate was technically satisfied (a `REFERENCES.md` entry existed and was cited), but the gate does not distinguish a reference that says "confirmed via live capture" from one built on a vendor's demo payload or from a captured entry that itself documents the exact point as unconfirmed.

2. **A captured, self-acknowledged "unconfirmed, needs a live test" note on a fully-gating path (auth) was treated as an ordinary accepted-trade-off bullet, not a blocker.** The PR description's own "Reviewer notes" listed the auth-format gap in a flat list alongside genuine, already-reasoned-through design trade-offs. Nothing in `review-hard`'s severity guidance or `wos/gate-conditions.md`'s "Before PR packaging" checklist forces a structural distinction between a judgment call (safe to leave as prose) and a pure, checkable, unresolved fact about vendor behavior that gates 100% of a code path.

3. **The test suite's own auth boundary gave false confidence.** The route-test harness injects `req.auth` directly, bypassing the real authentication middleware entirely; grepping the integration's 44 tests for any `.set("Authorization"...)` / `.set("X-API-Key"...)` call returns zero matches. `test-strategy`'s own call-out list (idempotency, retries, migrations, concurrency, partial failure, backward compatibility) has no entry for "authentication/authorization boundary on an inbound external integration," so nothing prompted a reviewer to ask whether that boundary had real coverage. `wos/bug-classes/over-mocked-test.md` exists but targets general business-logic over-mocking, not the more specific and more dangerous pattern of a security boundary bypassed by construction.

4. **A "live e2e against real staging" was treated as strong evidence when it validated only the team's own assumption.** The e2e sent `X-API-Key` (the header our own middleware expects) rather than replaying the vendor's documented delivery shape (a raw value under a literal `Authorization` header). "Hits real infrastructure" and "uses the vendor's real request shape" are independent axes; nothing in the workflow required labeling e2e evidence on both.

The triggering task's own `LEARNINGS.md` (harvested the same day, `harvest-session-learnings`) records the task-level lessons in full detail. This ADR addresses the narrower question: which of those lessons represent a **systemic, mechanically-enforceable gap** in the WOS commands themselves, versus a one-off task-level judgment lesson that does not need a new rule.

## Decision

Four coordinated changes, landed together, each closing the gap at a different layer of the existing three-layer quality gate (`wos/gate-conditions.md`):

1. **`commands/_shared/reference-grounding.md` (implementation-time, earliest gate).** A captured `REFERENCES.md` entry does not satisfy the gate when (a) it is evidenced only by a vendor's demo/example/sandbox payload rather than a live capture of the real delivery mechanism, or (b) the entry itself marks the exact point `[unclear in source]` or otherwise documents it as unconfirmed, **and** the contract governs a security-critical or fully-gating path (auth, payment, PII, or any point where a wrong assumption blocks 100% of traffic rather than an edge case). In that case the gate requires either a live capture (real request/response, not vendor demo data) or an explicit, separately-recorded `decision-interview` entry naming the assumption and the accepted risk, before implementation proceeds.

2. **`commands/review-hard.md` (review-time).** Reviewing an integration with an external vendor, a captured-but-unconfirmed contract point that gates a fully-required path (auth, payment, delivery mechanism) is always at minimum a must-fix finding, never should-fix or an optional/footnote note, regardless of whether a workaround exists. `review-hard`'s "Focus on" list gains this as an explicit checked item.

3. **`wos/gate-conditions.md` "Before PR packaging" (pre-ship gate, catches anything the earlier two missed).** A new checklist bullet: no external-vendor contract point marked unconfirmed on a security-critical or fully-gating path may ride into a PR as an ordinary accepted-trade-off note; it must be a structurally distinct, named blocker or already resolved.

4. **`commands/test-strategy.md` (plan-time) plus a new bug-class `wos/bug-classes/auth-boundary-test-bypass.md` (continuous sweep).** `test-strategy`'s explicit call-out list gains "authentication/authorization boundaries on inbound external integrations, when the test harness would otherwise stub past the real check." The new bug-class gives `repo-consistency-sweep` a standing, automated detector for the specific pattern (a test harness injects post-auth state directly, and the corresponding test file never exercises the real header-parsing/auth-validation code), independent of whether `test-strategy` was run for that task.

This is deliberately layered rather than a single fix: per `wos/gate-conditions.md`'s existing three-layer philosophy, no single gate is assumed sufficient. The incident shows a gap survives review, tests, and a "live" e2e simultaneously when they all share the same blind spot; the fix must not share that blind spot at every layer.

## Consequences

### Positive

- An external vendor contract that gates a required, security-critical path can no longer be built (reference-grounding), reviewed (review-hard), packaged (gate-conditions), or tested (test-strategy + bug-class) while resting solely on vendor demo data or unresolved doc silence, without that fact becoming an explicit, structurally distinct blocker at every layer it passes through.
- `repo-consistency-sweep` gains a reusable, stack-agnostic detector (`auth-boundary-test-bypass`) that fires on any future task in any project where a test harness stubs past a real auth/authz check, not just this one incident.
- The layered design means a gap that slips past one layer (for example a rushed `reference-grounding` pass) still has three more chances to be caught before it ships.

### Negative

- `reference-grounding.md` gains a conditional branch (security-critical/fully-gating path vs. ordinary external contract) that requires judgment to classify correctly; an overly broad interpretation could block routine integration work on non-critical paths. Mitigated by scoping the extra requirement explicitly to "security-critical or fully-gating" (auth, payment, PII, single point of failure for all traffic), not every external field mapping.
- Four files across four different command layers now need to stay in sync on this concept; a future change to one without the others could reintroduce an inconsistency. Mitigated by this ADR being the single cross-reference point named in all four.

### Neutral

- None of these changes require a new command; all four are amendments to existing gates and one new bug-class template, consistent with `wos/gate-conditions.md`'s existing layering rather than adding a fifth layer.

## Alternatives considered

### Alternative 1: A single new command (`external-contract-verify`)

- A dedicated command that runs once per integration task, forcing a live-capture step before any implementation.
- Rejected: the incident shows the gap is not "we forgot a step," it is that four *existing* layers (grounding, review, testing, packaging) each independently judged the doc-inferred contract as sufficient. A fifth, separate command is one more thing to remember to invoke, and would not close the gap in the four layers that already exist and are already mandatory. Amending the existing mandatory gates has a much lower chance of being skipped than adding a new optional step.

### Alternative 2: Only add the bug-class, skip the gate/review amendments

- Rely on `repo-consistency-sweep`'s `auth-boundary-test-bypass` alone to catch this class of issue.
- Rejected: `repo-consistency-sweep` catches the *test-mocking* half of the failure but not the *reference-grounding* half (a vendor-demo-only contract with no test-boundary bypass at all would still slip through), nor the *PR-notes-flattening* half (an explicitly-flagged risk that was correctly written down but not gated). A single detector at one layer would have caught only one of the four contributing gaps in this actual incident.

## References

- `commands/_shared/reference-grounding.md` (execution gate, amended)
- `commands/review-hard.md` → `Focus on:` list and must-fix severity guidance (amended)
- `wos/gate-conditions.md` → `## Before PR packaging` (amended)
- `commands/test-strategy.md` → explicit call-out list (amended)
- `wos/bug-classes/auth-boundary-test-bypass.md` (new)
- The triggering task's own `LEARNINGS.md` (private, task-scoped detail, not part of this public distribution; the full six-lesson harvest this ADR distills the systemic subset of)
- `ADR-0086` (deep issue-thread research and escalation gate) -- a related but distinct precedent: ADR-0086 gates escalating to a heavy fix before reading deeper into *already-captured* sources for our own dependencies' upstream bugs; this ADR gates *building and shipping against a third-party vendor's contract* before that contract is live-verified, a different point in the lifecycle (pre-implementation vs. pre-escalation) and a different kind of source (a vendor's product contract vs. an open-source issue thread).

## Notes

Triggering incident: a TMS webhook vendor integration (`tms-webhook-integration`, 2026-07-15), discovered during a live client call. Full task-level detail (six verified, anchored lessons) lives in the triggering task's own `LEARNINGS.md` (private, task-scoped, not part of this public distribution), produced via `harvest-session-learnings` the same day. This ADR intentionally captures only the subset of those lessons that resolve to a mechanically-enforceable system change; task-level judgment lessons (for example, controlling for endpoint identity and resource lifecycle state before escalating a single-sample "missing field" finding to must-fix, or treating a guess that happens to match your own convention as neutral rather than corroborating) remain recorded in that `LEARNINGS.md` without a new gate, since they are review-discipline habits rather than mechanically detectable patterns.

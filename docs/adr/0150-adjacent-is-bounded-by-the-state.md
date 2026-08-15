# ADR-0150: "Adjacent" is bounded by the state, not by the domain

Date: 2026-08-13

Status: Accepted

## Context

ADR-0148 D-4 deferred the last of the four narrow triggers the gate-provenance advisory found, and
stated the deferral's reason precisely enough to act on later:

> It is deferred because the obvious widening ("any decision with adjacent flows") is the always-fires
> shape that `wos/active-epistemic-humility.md` rule 1.7 forbids, and a correct trigger needs a
> bounded definition of "adjacent" that this pass did not produce.

The rule in question fires WHEN `decision-interview` locks a security-relevant invariant (auth,
biometric, session, or permission-boundary) and requires enumerating at least three adjacent flows,
naming logout, app backgrounding, and force-quit/kill.

Applying the ADR-0147 D-3 test: the mechanism is that a decision covering only the flow it was asked
about leaves the other flows that depend on the same thing undefined. Nothing in that sentence is
about security. A payment decision leaves refund, retry, and chargeback undefined the same way.

The bounded definition falls out of the three flows the rule already names, once you ask what they
have in common. Logout, backgrounding, and force-quit are not adjacent to an auth decision because
they are also security topics. They are adjacent because **each of them reads or writes the same
state the auth decision just defined**: the session, the token, the permission grant. That is the
boundary, and it is a property of state rather than of subject matter.

This definition does the two things the deferral required. It generalizes correctly: a payment
decision's adjacent flows are the ones touching the charge record, a sync decision's are the ones
touching the local-versus-remote state, a notification-preference decision's are the ones touching
the stored preference. And it EXCLUDES rather than always-firing: a copy change, a colour token, and
a library choice govern no state that a second flow reads, so they have no adjacent flows and the
rule costs them one line.

It also corrects a smaller defect that was invisible while the trigger stayed narrow. "At least 3"
is arbitrary. It is the count that happened to fit the auth case, and a fixed minimum applied to a
decision with two adjacent flows invites inventing a third. The state-bounded reading replaces the
count with the actual set: enumerate the flows that exist.

The trigger is author-evaluated, which ADR-0147 warns about, and the distinction matters here. What
the author is asked is not how risky or how uncertain the decision feels, which would be the
self-assessment `wos/active-epistemic-humility.md` rule 1.3 forbids. It is which flows read or write
a named piece of state, which is a fact about the codebase that a reviewer can re-check and a grep
can often answer outright.

## Decision

**D-1. Rekey the trigger to shared state.** The rule fires WHEN a decision defines behavior for state
that MORE THAN ONE flow reads or writes, and requires enumerating and confirming the behavior for
each such flow before the decision locks. "Adjacent" is defined in the rule as bounded by the state
rather than the domain.

**D-2. Keep the auth case named, and drop the fixed count.** For an auth, biometric, session, or
permission-boundary decision the flows are AT MINIMUM logout, app backgrounding, and force-quit/kill,
stated so existing coverage is unambiguous and a reader gets the concrete anchor. The "at least 3"
minimum is replaced by the actual set, with an explicit instruction not to manufacture a count.

**D-3. State the exclusion in the rule.** A decision whose state no other flow touches has no
adjacent flows, says so in one line, and locks. Without this sentence the rule reads as always-firing
to a careful reader, which is the failure the deferral was protecting against.

**D-4. Update the paired pointer.** `commands/invariants-and-non-goals.md` carries a light
cross-check pointer that named the three auth flows as the list. It is rekeyed to the same
state-bounded condition, keeping the auth flows as the named minimum, so the two surfaces do not
diverge. It remains a pointer, not a second mechanism.

## Validation: both halves measured, and a correction to ADR-0148's stated limit

Two arms of five on a payment decision (outside the old auth-only trigger, inside the new one), plus
a four-run control on a copy decision under the NEW rule, all blind to the experiment.

| | Arm A (auth-only) | Arm B (state-bounded) |
|---|---|---|
| Raised other flows unprompted | **0 of 5** | **5 of 5** |
| Marked the decision locked | **5 of 5** | **0 of 5** |
| Held it open pending flows | 0 of 5 | 5 of 5 |
| Flows enumerated | 0, 0, 0, 0, 0 | 6, 6, 7, 6, 6 |

Arm A was correct under the text it had, and said so: "the only rule forcing adjacent-flow
enumeration is scoped to security-relevant invariants (auth, biometric, session,
permission-boundary), none of which this charge-state decision touches, so it locks." All five locked
a payment decision without settling what happens on refund, on chargeback, or when the
authorization hold expires.

Arm B named flows the scenario never mentioned: refund against a held uncaptured charge, a chargeback
landing on a charge with a pending retry, customer cancellation inside the 30-second window, the PSP
hold expiring before the retry fires, a late capture webhook arriving after the void, fulfillment
gating on an uncaptured charge, and checkout resubmit against the same order. Several are real
money-losing cases.

**The control confirms the rule does not over-fire.** Four runs on a copy decision under the new rule
returned zero flows, every one citing the exclusion clause, and one naming the failure it avoids:
"inventing those flows would be manufactured coverage."

**A first version of this experiment measured nothing, and the reason corrects ADR-0148.** It listed
the four adjacent flows inside the scenario, so enumerating them was transcription and arm A scored
4 of 5. Removing that list produced the table above.

ADR-0148 concluded that this repository can A/B a change to an output requirement and cannot A/B a
change to investigation depth. That is too strong, and this run is the counterexample. The real
condition is narrower: **a change to investigation depth is measurable when the scenario does not
already contain what the rule should make the run find.** ADR-0146's rule 7 returned null twice
because its fixture was small enough to read exhaustively, so nothing was hidden in it. This rule
measured because a payment domain has adjacent flows the model knows and does not volunteer unless
a rule asks. The distinction is whether anything is left to discover, not whether the change is about
discovering.

That also means ADR-0146 rule 7's null result is still a null result, but its stated cause should be
read as "no fixture I built had anything hidden in it", which is a weaker and more honest claim than
"this class is unmeasurable".

## Consequences

- The rule now fires on decision classes it never reached (payment, sync, notification preferences,
  and any other multi-flow state), which is the intent and is the cost.
- It also now explicitly does NOT fire on single-flow decisions, which the previous wording left to
  inference. The net effect on a task full of copy and styling decisions should be close to zero.
- Losing the fixed "at least 3" removes a countable check. That is deliberate: a count is easy to
  satisfy and easy to satisfy wrongly, and the set it stood in for is the thing that matters.
- `decision-interview` grows by roughly 700 characters against its Load ceiling, which
  `structural-evals.py` re-checks on the same run.
- This closes the last of the four narrow triggers ADR-0148 found. Of those four, two were fixed in
  ADR-0148, one turned out to rest on a false premise and was corrected in ADR-0149, and this is the
  fourth.

## Alternatives considered

- **Widen to "any decision with adjacent flows".** Rejected in ADR-0148 and still rejected: without a
  bounded definition of adjacent it fires on everything, and rule 1.7 makes a label that costs tokens
  and changes no control flow into ceremony by definition.
- **Keep the auth-only trigger and add a second rule for payments.** Rejected: it is the same
  incident-shaped authoring ADR-0147 exists to stop, one domain at a time, and the next domain would
  need a third rule.
- **Keep "at least 3" alongside the state-bounded set.** Rejected: the two conflict whenever the real
  set is smaller than three, and the resolution a reader would reach (invent a third) is worse than
  either rule alone.
- **Make the enumeration a machine check.** Rejected as out of reach: which flows read a piece of
  state is often greppable but not reliably so across every stack this workflow targets, and
  `scripts/check-claim-grounding.sh` already records the standing limit that lint sees files and does
  not run a model. The rule stays a prompt-layer obligation whose output a human can re-check.

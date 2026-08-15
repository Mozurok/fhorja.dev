# ADR-0146: The internal exemption exempts from capture, not from grounding

Date: 2026-08-13

Status: Accepted

## Context

`commands/_shared/reference-grounding.md` is the repository's only MUST-NOT-edit refusal. Rule 2
stops an edit that touches an external contract absent from `REFERENCES.md`. Rule 1 scopes the whole
gate, and its last sentence scopes it away from the case this ADR is about:

> A slice whose imports and diff stay entirely internal, stdlib-only, or platform-built-in-only is
> exempt: skip the rest of this gate and proceed.

Read together with rule 2, the gate refuses to edit without a captured Stripe doc and permits
duplicating an internal helper that already exists. The 2026-08-13 session forensics found five
documented review misses across ten real sessions in a large monorepo, and every one of them took
that exemption. Not one involved an external contract.

The naive fix, which this ADR rejects, is a pre-edit sibling-precedent gate: before adding behavior
where siblings exist, locate the sibling and name it. The forensics refute that fix on its own
evidence.

In the motivating case the agent DID run the search that returns the canonical path. Its own label
for the call was "Find await-then-navigate precedent for the claim handler", and the first entry in
the result was the module that owns the canonical dispatch. Eighty-nine transcript lines later it
wrote a direct call to the pipeline internal with a source comment justifying the choice, having
first named a DIFFERENT precedent and declared it "an exact structural match". A gate that requires
naming the precedent you mirror is satisfied by naming the wrong one.

The second half of the same miss has the same shape from the other direction. The agent duplicated a
`logger.error` and a toast that the callee already owned. The callee's own handling had been on
screen 918 transcript lines before the duplicating edit, in the output of a `sed -n '185,275p'` read.
The callee was opened four times across the session, always in narrow windows, and the union of those
windows skips the range where the remaining handling lives. The parameter that would have made the
duplication obvious appears once in the whole corpus, in a tool result, and never again in any
reasoning.

So the failure is not that the sibling was not found, and not that the file was not opened. Both
happened. The failure is that a claim about in-repo behavior ("this precedent's handling is right
here", "the callee does not already do this") was load-bearing for the edit and was never traced to a
source. That is the claim-keyed shape rule 6 already uses for external contracts, stopping at the
repository boundary for no stated reason.

## Decision

**D-1. Add rule 7 to `commands/_shared/reference-grounding.md`, worded as a delta on rule 6 rather
than on the sibling idea.** Rule 1's exemption exempts an internal-only slice from capture, not from
grounding. WHEN an in-repo behavior claim is load-bearing for the edit, it MUST trace to a
`file:line` range read this session, named in the execution summary. Two clauses carry the weight:

- **(a) Quantified claims need enumeration, not a window.** WHEN the claim quantifies over all of
  something (every error this route raises, every caller of this symbol, every path reaching this
  branch), the cite SHALL be an enumeration over the whole file, never a line-window read.
- **(b) Mirroring does not ground.** A precedent grounds what that file does, not that it is correct
  at this call site. A mirrored error path still requires the callee's own failure handling to be
  enumerated and cited.

A claim that cannot be cited this way is recorded as an assumption in the slice note and is not
encoded in a branch.

**D-2. The negative branch of the pre-edit precedent gate must produce a re-runnable referent.**
`commands/implement-approved-slice.md` accepted `no precedent found, searched <what>` as discharge.
That is a referent-free status, which `wos/active-epistemic-humility.md` rule 1.3 reads as UNKNOWN
rather than as a weak yes. It is replaced by the exact search command plus its verbatim zero-result
output, which is the same evidence standard the same file already applies to validation, where an
exit criterion asserted without shown output is marked unverified.

The same edit records that naming a precedent is necessary and not sufficient, and points at rule 7
for the sufficiency half.

## Validation status: NOT empirically validated

This section exists because the alternative is letting a reader assume the rule was tested. It was
tested, twice, and neither test discriminated.

Two blinded A/B runs were executed on the day this ADR landed, six runs per arm, on fixtures built to
reproduce the motivating shape (a canonical dispatcher, an internal it wraps, a nearest precedent
that calls the internal directly and duplicates the callee's error handling, and a target screen with
a TODO). Arm A received the pre-rule-7 grounding block, arm B the post-rule-7 block. Both arms were
blind to the experiment.

- **Run 1** was invalid and is recorded rather than discarded. The fixture carried the answer in its
  own source comments ("The single dispatch point... All task awards in the app go through here",
  "The only sanctioned caller"), which the real codebase did not; it was five files and about 110
  lines, so every one of the twelve agents read all of it whole-file; and the scored metric counted a
  correct error toast as a duplication, because in that fixture the callee toasted only on success.
  Result: 6/6 identical in both arms.
- **Run 2** fixed all four defects: giveaway comments removed, the callee's failure path moved to
  lines 106 and 123 of a 136-line file, two conforming precedents against one non-conforming one,
  and duplication made genuinely wrong. Result: arm A 5/6 fully clean, arm B 6/6. Reading the single
  arm-A deviation, it is not a deviation: that run added handling only for a throw escaping the
  callee's `Promise.allSettled` loop, stated explicitly that it was not duplicating the callee's own
  logging and toast, and was right. The honest score is 6/6 against 6/6, zero measured effect.

The likely reason is structural rather than a fixable fixture defect. In both runs, in both arms, all
twelve agents read the callee whole-file and cited its error path by line. The failure this rule
addresses was observed in a session with 1,594 tool calls in a monorepo where the same file was opened
four times in narrow windows. A fixture small enough to build is small enough to read exhaustively,
so it cannot reproduce the condition (scale plus context pressure plus session length) under which
window reads and precedent-inheritance actually occur.

What this means for the rule, stated plainly: its argument rests on five documented real misses and on
the mechanism reading of those misses, not on a controlled measurement. Its cost is near zero because
it is claim-keyed and inert on a slice that asserts nothing, which is why it is kept rather than
reverted on a null result. Anyone citing this ADR should cite it as reasoned-from-incidents, never as
measured.

The test that would discriminate is not a fixture. It is the same instrumentation that produced the
motivating forensics, applied forward: measure, across real sessions after this lands, the rate of
line-window reads cited as grounding for quantified claims, and the rate at which a mirrored
precedent is treated as grounding for callee behavior. If those rates do not move, the rule is
ceremony and should be removed under rule 1.7.

## Consequences

- Rule 7 fires on a claim, not on a file set or a diff scan, so a slice that asserts no in-repo
  behavior pays nothing. This is the same cost shape as rule 6 and as the `claim-grounding` inert
  clause.
- The shared block propagates via `scripts/sync-shared-blocks.sh` into the eleven commands that
  declare `<!-- shared:reference-grounding -->`. No command gains a new step.
- Honest scope, measured rather than claimed: against the five documented misses, rule 7 reaches
  three. Clause (b) reaches the mirrored-precedent case and clause (a) reaches two claims that
  quantified over a whole surface while resting on window reads. The remaining two are not grounding
  failures at all; one is the clean-verdict absolution that ADR-0145 covers, and one is a reachability
  claim about a branch the author introduced.
- D-2 makes a previously free discharge cost a real command and its output. That is the intent: the
  free version is written at the same moment as the code and is indistinguishable from a search that
  never ran.
- Rule 2's refusal, rule 1's capture exemption, and rule 6 are all unchanged. This is additive, and
  reading internal source never becomes a substitute for capturing an external contract.

## Alternatives considered

- **A pre-edit sibling-precedent gate on every slice with siblings.** Rejected on the evidence above:
  the gate fired in the motivating case, was satisfied by the wrong precedent, and its trigger ("a
  directory containing siblings of the same kind") is evaluated by the agent about its own case,
  which is exactly what the existing gate's own rationale rejects when it says keying a gate to a
  self-assigned tag disables it on any plan that assigns none.
- **Close the rule 1 exemption itself, so internal slices run the whole gate.** Rejected: rules 2
  through 5 are about capturing external contracts, and there is nothing to capture for an in-repo
  module. Running them would produce a scan with no possible finding, which is the ceremony the cost
  floor in `wos/active-epistemic-humility.md` rule 1.7 forbids.
- **Require every edited file to have been read in full.** Rejected as unenforceable and mis-keyed. No
  check in this repository can observe a read, and the rule would fire on every slice regardless of
  whether any in-repo claim was load-bearing. Clause (a) gets the part that matters, keyed to the
  claim rather than to the file, and only where the claim quantifies over a surface.
- **Delete the negative branch entirely and require abstention plus a route to `code-locate`.**
  Considered and held in reserve. It is the stricter reading of rule 1.5's routed-continuation
  contract, and it may be correct, but it converts a common and legitimate case (there genuinely is
  no precedent) into a routing detour. D-2's pasted zero-result output produces the same auditable
  referent at lower cost. Revisit if the pasted-output form is observed being fabricated.

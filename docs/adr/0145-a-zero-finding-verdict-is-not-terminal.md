# ADR-0145: A zero-finding review verdict is not a terminal state

Date: 2026-08-13

Status: Accepted

## Context

ADR-0033 built the stateless blinded reviewer. `verify-against-rubric` spawns a sub-agent that
receives ONLY the artifact path plus the locked rubric plus read-only tools, with no `TASK_STATE.md`,
no `DECISIONS.md`, and no prior conversation. Its stated purpose is to close "the same-context bias
gap that `self-critique-and-revise` (in-thread) inherits", and ADR-0033 records the measured reason:
the agent that wrote the artifact is also the one critiquing it.

The trigger it shipped with is inverted, and the inversion is the whole defect.

`verify-against-rubric` is reached after a review has already produced something to verify. A review
that returns findings hands those findings on. A review that returns CLEAN ends the chain: the
`## Command roles` entry for `review-hard` lists `slice-closure`, `repo-consistency-sweep`,
`where-we-at`, and `pr-package` as its next commands, all of which accept a clean verdict and move
forward. So independent confirmation fires exactly when the same-context reviewer already
demonstrated it could find something, and never fires in the one case where its own output is
unfalsifiable from inside its own context.

A same-context reviewer can check a finding it produced. It cannot check the absence of findings it
did not produce. Absence of evidence from a reviewer holding the authoring rationale is the single
output that reviewer has no way to audit about itself, and it is the output that routes forward with
no further check.

The 2026-08-13 session forensics over ten real sessions in a large monorepo measured the consequence
twice, on two different tickets, with external tools as the control:

- One ticket ran `review-hard` three times against the same diff. All three returned CLEAN, and the
  full-graph type gate and lint were green. External review bots filed two real defects in that same
  diff within minutes of the pull requests opening.
- A second ticket ran the host repository's own self-review command. That command stated the correct
  hypothesis in its own words ("testing whether the trim I just added is actually reachable, given
  the submit button gates on the untrimmed value"), ran the search that answers it, and returned
  "CLEAN, defensible". An external bot then filed exactly that defect. The session's own words after
  reading it: "it is the same finding my own self-review surfaced", and "my earlier reasoning does
  not survive scrutiny".

The second case is the load-bearing one, because it rules out the obvious alternative explanation.
The reviewer was not blind, under-prompted, or short of budget. It formed the right hypothesis and
ran the right check. What failed was the verdict on evidence it had already gathered about work it
had already authored. No amount of additional same-context reviewing reaches that, because every
additional pass carries the same authoring rationale into the judgment.

The published record names the mechanism and it is not specific to this workflow. Evaluators shown a
text framed as their own rate it higher than the identical text framed as a third party's
(Sanz-Guerrero et al., ACL 2026 Findings, arXiv:2606.03437), and models update non-Bayesianly in
defense of a choice they already made (Kumaran, Fleming et al., 2025, arXiv:2507.03120). Stripping
identity cuts abandonment of correct positions by roughly four times as much as it cuts correction of
wrong ones (Choi et al., ACL 2026, arXiv:2510.07517), which is the asymmetry that makes blinding
worth its cost here.

A second, smaller finding from the same forensics belongs with this one because it is the same shape.
The `wos/bug-classes/` library contains three templates that describe internal-reuse defects
precisely (`sibling-controller-divergence`, `sibling-route-divergence`,
`custom-component-when-ds-exists`). They are consumed only by `repo-consistency-sweep`, and across
6,010 tool calls in the measured corpus that command does not appear. Good detection content behind
an unreliable invocation is indistinguishable, in outcome, from no detection content at all.

## Decision

Two changes, both routing and invocation, neither adding a new command, a new artifact, or a new
schema.

**D-1. A zero-finding verdict routes to the blinded reviewer.** `review-hard` gains an operating rule:
WHEN its verdict names zero must-fix and zero should-fix findings AND the diff under review touched
product code, the output SHALL NOT emit `Run now: none`, and SHALL route to `verify-against-rubric`
with the slice's exit criteria as the locked rubric and the diff as the artifact. The sub-agent
receives the diff and the rubric only, never this review's findings, narration, or reasoning, per the
ADR-0033 isolation contract it already implements.

The trigger is the verdict's own content, which the command has already computed when the rule fires,
so it costs no additional investigation to evaluate. The product-code condition scopes out the
documentation-only and task-memory-only diffs where a second opinion buys nothing.

**D-2. The Layer-2 review floor stops accepting a bare clean verdict.** In `wos/closure-floors.md`,
both variants of the Layer-2 review floor (the `implement-approved-slice` inline-close twin and the
`slice-closure` ready-to-close form, per the two-homes rule in `wos/gate-conditions.md`) are amended:
a cited verdict with zero findings over a product-code diff does not satisfy the floor on its own and
requires the `verify-against-rubric` verdict id alongside it. A verdict WITH findings satisfies the
floor as it does today. The existing one-line skip reason remains available and is unchanged.

**D-3. The internal-reuse classes get an invocation floor, and their content does not move.** A slice
that added a file or an exported symbol into a directory that already contained siblings does not
close inline without one of: a cited `repo-consistency-sweep` run over this slice's diff whose
snapshot names `sibling-controller-divergence`, `sibling-route-divergence`, and
`custom-component-when-ds-exists` among the classes its class-selection step chose; a named
host-repository equivalent; or an explicit one-line skip reason. The cite is the snapshot file path,
not a claim that the sweep ran.

The classes stay in `repo-consistency-sweep`. Moving them earlier was considered and rejected below.

**D-4. Registry alignment.** `WORKFLOW_OPERATING_SYSTEM.md` `### review-hard` and the
`wos/command-roles.md` `### review-hard` typical-next list both gain `verify-against-rubric`, marked
with its condition, so the ADR-0029 registry guard stays green and a reader of either registry sees
the same routing graph the command implements.

## Validation: measured, 0 of 5 to 5 of 5

A blinded A/B run was executed on the day this ADR landed. Five review runs per arm over the same
clean product-code diff (a `Number.isFinite` guard on a currency formatter plus two tests covering
it), with slice exit criteria supplied and Layer 1 declared green. Arm A received `review-hard` as it
stood before D-1, arm B the same file with D-1 added. Both arms were blind to the experiment and were
asked to report the literal value of their `Run now:` line.

| | Arm A (before) | Arm B (after) |
|---|---|---|
| Zero-finding verdicts | 5 of 5 | 5 of 5 |
| Routed to the blinded reviewer | **0** | **5** |
| Ended the chain (`Run now: none`) | 0 | 0 |

Both arms agreed the diff was clean, so the verdict itself was stable and the change acted only on
what happens next.

The mechanism the run exposed is sharper than the one this ADR was written from, and it should be
recorded. In arm A the blinded reviewer was not forgotten. All five runs considered it and rejected it
in writing, each citing the same rule: "verify-against-rubric is explicitly scoped to HIGH-complexity
slices", "a blinded rubric pass would be ceremony with nothing to arbitrate", and, from one run as an
explicit negative instruction to its successor, "Do not: do not run verify-against-rubric on this one.
It is a three-line guard with two tests, well under the complexity where an independent blinded pass
earns its cost."

So the pre-D-1 state did not merely omit the check. It supplied a reasoned, rule-citing justification
for declining precisely the verification the reviewer cannot perform on itself, and the justification
reads as good engineering judgment because it quotes the command's own complexity guidance. That is a
stronger failure than an oversight, and it is why a routing edge rather than a recommendation was
needed.

Arm B's five runs each described the isolation contract correctly without being told: one enumerated
what it would withhold as "this review's verdict, its findings lists, its narration, TASK_STATE.md,
DECISIONS.md, and the Layer 1 green status".

Limits of this measurement, stated so it is not over-read: N=5 per arm detects a large effect and not
a small one, which is adequate here only because the effect was total. It measures routing behavior,
not defect yield. It does not show that the blinded reviewer finds anything on this diff, and this ADR
does not claim it does; the claim is that a second, differently-grounded measurement gets taken.

## Consequences

- No `count:commands` change. This is a routing rule plus two floor amendments, not a new command, so
  the four-registry command membership requirement does not apply. The two registries that carry a
  per-command typical-next list are updated for accuracy, not for membership.
- `review-hard`'s cost is unchanged on the path where it finds something, and rises by one stateless
  sub-agent on the path where it finds nothing. That is the intended direction: the run that produced
  nothing is the run whose output is least trustworthy, and it is also the run that spent the least.
- `scripts/build-closure-floor-views.py` regenerates the per-consumer floor views after the
  `wos/closure-floors.md` edit; the generated views are never hand-edited.
- The floor amendment can block a close that previously passed. That is deliberate and it is the
  measured case: three CLEAN verdicts closed a slice that carried two real defects.
- ADR-0033 is extended, not reversed. Its isolation contract, its stateless sub-agent, and its
  existing post-findings trigger all stay. This ADR adds the trigger it left uncovered.
- The blinded reviewer can also return clean. This ADR does not claim it cannot; it claims that a
  verdict produced without the authoring rationale is a different measurement from one produced with
  it, and that having both is worth one sub-agent on the diffs that reach this gate.

## Alternatives considered

- **Edit the self-review prompt to remove ownership framing.** Rejected: the blinded reviewer already
  exists and already implements exactly that, so a prompt edit would either duplicate
  `verify-against-rubric` inside `review-hard` or turn `review-hard` into it. `review-hard` reviews
  with task memory in the window on purpose; that context is what makes it good at the findings it
  does produce. The fix is to route to the blinded reviewer, not to blind this one.
- **Make the routing unconditional on every `review-hard` run.** Rejected on cost. A verdict with
  findings has already produced falsifiable output that the downstream flow acts on and that a human
  reads; the unfalsifiable case is the empty one. Firing on every run doubles the reviewer cost of
  every slice to re-check verdicts that are already checkable.
- **Move the internal-reuse bug classes to a pre-edit checklist.** Rejected: `repo-consistency-sweep`
  selects bug classes by matching each class's `file-patterns` against the changed-file list, which is
  the only mechanical selector in the chain. Before an edit there is no diff to match, no modified
  method body to retrieve, and no finding to rank, so the move would discard the class-selection
  step, the retrieval scope, and the severity rubric, and keep only the residue ("look at your
  siblings"). The measured problem was invocation, not placement.
- **Widen `implement-approved-slice`'s pre-edit precedent gate to all file classes.** Rejected here
  and treated separately: the same forensics found that in the motivating case the agent DID name an
  in-repo precedent and DID mirror it, and the precedent it named was the defect. A gate satisfied by
  naming any precedent does not catch naming the wrong one. The grounding half of that problem is
  ADR-0146; the trigger-scoping half is ADR-0147.
- **Accept the clean verdict and rely on external review bots.** Rejected: the bots are outside this
  workflow's control, are not present in every host repository, and in the measured corpus they
  caught these defects only after the pull request opened, which is after the point where the closure
  floors claim the slice is done.

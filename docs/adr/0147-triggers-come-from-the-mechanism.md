# ADR-0147: A gate's trigger comes from the mechanism it defeats, not from where the failure was seen

Date: 2026-08-13

Status: Accepted

## Context

This repository learns from dogfood runs and writes the lesson down as a rule. The rules are good.
The triggers are frequently keyed to the circumstances in which the failure happened to appear rather
than to the mechanism the rule defeats, and the two are almost never the same set. The circumstance
is what is vivid at authoring time.

The seed instance is `commands/implement-approved-slice.md`'s pre-edit precedent gate. Its
requirement is exactly right: before editing, cite a code-flow or locate result as blast-radius
evidence, and name the in-repo precedent `file:line` the new code mirrors. State its mechanism in
plain words and it reads "the executor edits code whose flow it has not traced". Nothing in that
sentence is navigational. Its trigger is "WHEN a slice touches navigation, routing, or deep-link
files", which is where the 2026-07-29 mobile dogfood happened to hit. A screen handler, a reducer, a
hook, a data-access module: none of them trigger it. The same line's own rationale contains the
generalizing argument it did not apply to itself, when it explains that keying the gate to a
self-assigned risk tag would disable it on any plan that assigns none.

The repository has already derived the general principle and stated it elsewhere.
`wos/active-epistemic-humility.md` rule 1.1 is titled "The obligation is keyed to the claim, not to
the file set", and its rationale is that a file-set key structurally cannot see the case where the
files did not change but the claim was still ungrounded. The precedent gate keys to a file set.

The pattern is not hypothesis. Four recurrence chains are documented by this repository against
itself, with dates, and three of them say out loud that they are a repeat:

- ADR-0089 gated a human feel-verdict for one engine. ADR-0091 (2026-07-10) opens by recording that
  a later dogfood "is the same failure recurring outside" that engine. ADR-0091 then does the same
  thing itself, naming a delivery-command gap as "a known, accepted gap until a dogfood surfaces it",
  and ADR-0099 closes exactly that gap two days later, after the gap bit and a human, not the
  workflow, caught it.
- The commit-evidence closure floor took four ADRs in 32 days (0084, 0100, 0128, 0133), each closing
  a case one step outside the previous trigger: `task-close` but not `slice-closure`, git-backed but
  not no-VCS, human-present but not unattended.
- Page identity was made the first assertion inside the automated web battery by ADR-0112, and
  recurred 16 days later on the human-handoff path, which is the path the experience verdict actually
  depends on. ADR-0127 states it plainly when it says the class is closed on the path where it bit
  twice, not only on the machine path that already had the rule.
- `commands/impact-analysis.md`'s repo-instruction-file walk records its own motivating measurement:
  a monorepo carried 31 `CLAUDE.md` files, the one governing the changed directory named both the
  runtime axis of the run's blocking defect and a boundary invariant the task spent hours
  re-deriving, and across 1,018 tool calls it was opened zero times. The fix fires "once the
  affected-file set is known", which is after the step where not knowing the file set is the problem.

The case against acting on this is real and was weighed. Narrow scoping is also correct discipline. A
precedent-citation gate on every code edit would fire on every slice, and a label that costs tokens
and changes no control flow is ceremony by rule 1.7's own definition. ADR-0122 rejected a broader
refutation fan-out on a measurement, not on timidity. Some narrow triggers are correct by
construction, where the failure is a property of one engine or one capability. And because ADRs are
immutable, narrow-then-widen is the cheaper error: a speculative broad rule that turns out wrong
cannot be patched, only superseded.

So the defect is not narrowness. It is that the boundary is inherited from the incident rather than
chosen, and an unchosen boundary is invisible to review because there is nothing to argue with.

There is also a structural regularity that makes this fixable procedurally rather than textually.
This repository reliably gets mechanism-shaped triggers when a rule passes through an ADR, because
the ADR template forces a scope rationale and an alternatives section, and reliably gets
incident-shaped triggers when a rule lands as an inline fold in a command body. The precedent gate
itself is the example: it landed in commit `81891f3` with no ADR and no eval scenario, and generalizing
an unratified, never-tested line would have been strictly worse than the line.

## Decision

**D-1. A dogfood finding that introduces a GATE requires an ADR, even when the change is one bullet.**
A gate is a conditional that can block work or demand evidence: it has a trigger. A finding that
introduces an UNCONDITIONAL discipline (a rule that always applies, with no trigger) may continue to
land as an inline fold, because a rule with no trigger has no trigger to under-scope.

The ADR is where the trigger's boundary gets argued. It SHALL state the mechanism the gate defeats in
plain words, and it SHALL name the cases excluded by the chosen trigger that also satisfy that
sentence. Narrowing stays fully available and is often right; it becomes a second, separate, priced
decision rather than the default shape of the first draft.

**D-2. `scripts/check-gate-provenance.sh`, warn-only.** A conditional gate in a `commands/*.md` body
that cites no ADR is surfaced on the lint `Gate-provenance:` line. Provenance is the checkable proxy;
whether a trigger is actually mechanism-shaped is a human judgment and the script says so about
itself. Shared-block text is suppressed by duplication (a gate line appearing byte-identical in two
or more commands is shared content whose provenance belongs to the canonical block), because a first
draft keyed on `WHEN|WHERE|IF` measured 129 hits across all 89 command files, and a check that fires
everywhere reports nothing. The shipped form measures 10 hits across 8 files, three of which cite a
dogfood or a wave item without an ADR, which is the pattern this ADR describes.

**D-3. The authoring test, stated for reuse.** State the mechanism in one sentence, then ask which
other places in the system satisfy that sentence. A trigger with no stated reason for its boundary is
not a narrow rule, it is an unfinished one.

## Consequences

- The advisory never fails a build, matching the `check-natural-voice.sh` and
  `check-claim-grounding.sh` tier. It changes what a reviewer looks at, not what CI permits.
- D-1 adds an ADR to a class of change that previously shipped as a bullet. That is a real cost on the
  smallest changes, and it is the intended trade: the four recurrence chains above each cost more
  than an ADR would have.
- This ADR does NOT retroactively widen any existing trigger. The 10 flagged lines are a reading list,
  not a defect list. Each is a separate decision with its own cost, and the one this session judged
  worth acting on now is handled in ADR-0146 rather than here.
- The seed instance is deliberately left narrow. ADR-0146 attacks the same failure from the grounding
  side, keyed to the claim rather than to the file class, because the forensics showed that widening
  the precedent trigger would not have caught the motivating case: the agent named a precedent, and
  the precedent it named was the defect.

## Alternatives considered

- **Widen the seed gate now, as a demonstration.** Rejected on evidence. In the motivating session the
  gate's requirement was met (a precedent was named and mirrored) and the outcome was still wrong,
  so widening the trigger multiplies self-certifications without changing verdicts. Sufficiency, not
  reach, was the failing half.
- **Make the check blocking rather than advisory.** Rejected: the check measures provenance, not
  correctness, and several flagged lines are probably fine. A blocking check on a proxy signal buys
  compliance with the proxy.
- **Require an ADR for every command-body rule.** Rejected: it charges unconditional disciplines,
  which carry no trigger and therefore cannot exhibit the defect, and it would make the smallest
  editorial fix expensive.
- **Write a `wos/` topic on trigger authoring instead of a check.** Rejected as insufficient alone,
  though D-3 is the topic-shaped part and is stated here. `wos/` topics are `activation:
  model_decision`, and ADR-0144 already recorded that a correct rule in a lazily-loaded file is
  invisible from where the agent stands. A lint line is read on every run.

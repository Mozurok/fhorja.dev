# ADR-0148: Two triggers rekeyed to their mechanism, and one orphan topic retired

Date: 2026-08-13

Status: Accepted

## Context

ADR-0147 shipped `scripts/check-gate-provenance.sh` and stated plainly that its output is a reading
list, not a defect list: each flagged line is a separate decision with its own cost. This ADR is the
first pass over that list. It is deliberately small.

The advisory flagged 10 conditional gates carrying no ADR cite. Applying the ADR-0147 D-3 test to
each one (state the mechanism in a sentence, then ask which other places in the system satisfy that
sentence) sorts them into three groups.

**Five have a trigger that IS the mechanism and need nothing.** `implement-approved-slice`'s
verification-divergence check fires "WHEN a verification check's expected value differs from its
actual value", which is the failure itself rather than a place it was seen.
`implement-slice-complement`'s Layer-2 coverage rule fires when this run produces a commit newer than
the cited verdict. `decision-interview`'s simplest-alternative rule fires on self-proposed complexity,
which is the mechanism named exactly. The slice-note-first floor keys to whether the task tracks
slices at all, an existence condition rather than a circumstance, and `task-init`'s git preflight keys
to whether the path is known yet. These are the shape the D-3 test is asking for, and they are
recorded here so a later reader does not re-flag them.

**One is a false positive of the check.** `capture-references`'s downloader prohibition is a wave
scope boundary carrying its own decision cite (`per D-3`), not a gate learned from a dogfood. The
check looks for `ADR-` specifically, so a decision-cited scope restriction reads as uncited. The
exemption list in the script gains this case rather than the check being loosened.

**Four have a trigger narrower than their mechanism.** Two of them are cheap, clean generalizations
and are the subject of this ADR. The other two are recorded as candidates and deliberately not done
here, because both need more than a rewording and this ADR is not the place to rush them.

### The two being fixed

`commands/app-runtime-verify.md` requires confirmation of clean Keychain or SecureStore state before
a device pass counts as evidence, and fires "WHEN a device pass is offered as evidence for an auth or
biometric slice". State the mechanism: persisted state that survives an app uninstall can mask the
failure the run is trying to observe. Nothing in that sentence is about authentication. A token cache,
a local database, an AsyncStorage key, a cached feature flag, and a completed-onboarding marker all
satisfy it. The sharpest case is a first-run or onboarding slice tested on a device that has run the
app before, which is exactly the shape the rule defeats and exactly the shape its trigger excludes.

`commands/implementation-plan.md` requires that a NO_OP produced by unmet prerequisites enumerate
EVERY unmet prerequisite rather than stopping at the first. State the mechanism: reporting one blocker
at a time turns a single unblock into a serial round-trip per blocker. That is true of every command
that can NO_OP on prerequisites, and several can. This one is not a narrow trigger to widen so much as
an unconditional discipline that was written into one command, which by ADR-0147 D-1 is the class that
belongs in a shared surface rather than in one body.

## Decision

**D-1. Rekey the runtime-evidence gate to persisted state.** `app-runtime-verify`'s Step 2 trigger
changes from "an auth or biometric slice" to "a slice whose acceptance behavior can be masked by state
that survives an app uninstall", with the auth and biometric cases named as the leading examples so
the existing coverage is unambiguous and the reader gets a concrete anchor. The discharge is unchanged
(an explicit yes/no from the tester, or a stated N/A), and so is the rule that an uninstall alone is
not proof.

**D-2. Promote the enumerate-all-blockers rule to the global output contract.** The rule moves to
`WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` under the existing no-op execution rule, as
an unconditional discipline covering any command emitting a `NO_OP_TRACE` for unmet prerequisites.
`implementation-plan` keeps a one-line pointer rather than the full text, so no command loses the rule
and no command pays for it twice.

**D-3. Retire `wos/realtime-overlay-patterns.md`.** It has been orphaned since it was written: no
command, scenario, ADR, sibling topic, or read-map entry references it, and the structural check has
been failing on it. It originated in a 25-agent mega-batch described in the changelog as client-pilot
coverage preparation, which is content authored ahead of demand, and the demand never arrived. That is
the ADR-0033 pattern (a harness built ahead of use, deprecated on 17 days and zero invocations)
applied to a reference topic. It also names three vendor products in a normative section heading,
against the vendor-neutrality rule, so integrating it would propagate a second problem to fix the
first. The three bug classes it cross-references are unaffected and stay where they are.

**D-4. Record the two deferred candidates**, so the next pass over the advisory starts from a decision
rather than from scratch:

- `team-update`'s egress confirmation gate fires only on a connected messaging MCP. The mechanism is
  that sending content outward requires confirming the exact payload and destination in the same turn,
  and `delivery-asset` and `pr-feedback-ingest --mcp-pull` both have egress or ingest surfaces. The
  correct fix is one shared block consumed by all three, not three copies of a reworded trigger, and a
  shared block is a bigger change than this ADR should carry.
- `decision-interview`'s adjacent-flow enumeration fires on auth, biometric, session, and
  permission-boundary decisions. The mechanism is that a decision covering only the flow it was asked
  about leaves the adjacent flows undefined, which is true of payment, sync, and notification
  decisions too. It is deferred because the obvious widening ("any decision with adjacent flows") is
  the always-fires shape that `wos/active-epistemic-humility.md` rule 1.7 forbids, and a correct
  trigger needs a bounded definition of "adjacent" that this pass did not produce.

## Validation: D-1 measured, D-2 not measurable by the method available

Both decisions were A/B tested on the day they landed, five runs per arm, arms blind to the
experiment. The results differ, and the reason they differ is worth more than either result.

**D-1 discriminated on the verdict itself, PASS 5 of 5 to BLOCKED 5 of 5.** The scenario was chosen
to sit outside the old trigger and inside the new one: a first-run onboarding slice, no
authentication of any kind, verified on a device the tester had used all week, with real captured
cold-start logcat showing both acceptance criteria observed and no error lines.

Arm A returned PASS in all five runs. Each cited the old rule correctly and said the gate did not
apply, one writing that asking for the confirmation "would invent a requirement the command file
does not state". That is the important half and it is not a failure of those runs: the old gate
genuinely did not cover the case, and refusing to invent coverage was the right behavior under the
text they were given. The defect was in the text.

Arm B returned BLOCKED in all five, named the same store (the persisted onboarding-completed
marker), and quoted the new rule verbatim. So the change converts a run that the old gate would have
accepted as valid Layer-1 evidence, on a device where the observed path may have been the
returning-user path rather than the first-run path, into a run that stops for one yes/no question.

A first version of this experiment reported the requirement rather than the verdict, because the
scenario described the logcat as "clean" without pasting it, which tripped the ADR-0048
shown-output rule and blocked both arms for an unrelated reason. It measured 0 of 5 to 5 of 5 on
whether the confirmation was demanded, which is the same direction and a weaker claim. The
pasted-output version above supersedes it and is the one to cite.

**D-2 measured nothing, because the scenario handed the model its answer.** The prompt listed the
five unmet prerequisites as five bullets. Both arms enumerated a mean of 5.6 blockers, both had
5 of 5 listing all of them, both had 0 of 5 stopping at the first, and both named a single best
unblocking command in all five runs. Enumerating every blocker is trivial when the blockers arrive
pre-enumerated. The test measured transcription, not the behavior the rule governs.

**The pattern across every A/B run in this work.** Four A/B experiments were executed across
ADR-0145, ADR-0146 and this ADR. Two discriminated and two returned null, and they sort perfectly:

- Discriminating: ADR-0145's routing rule (0/5 to 5/5) and D-1 here (0/5 to 5/5). Both change what
  the run is REQUIRED to produce, which is observable in a single output.
- Null: ADR-0146's rule 7 (twice, 6/6 against 6/6) and D-2 here. Both change how deeply the run must
  INVESTIGATE, and a fixture small enough to author is small enough to investigate exhaustively, so
  the arm without the rule does the work anyway.

The honest generalization is a limit on the method, not a verdict on the rules: this repository can
A/B a change to an output requirement and cannot currently A/B a change to investigation depth. The
second class needs a scenario where investigating further is genuinely expensive, which is a
property of scale and session length rather than of the fixture's content. Anyone reading a null
result in this repository should check which class the change belongs to before concluding the rule
is inert.

D-2 is therefore recorded as unvalidated. It is kept because it is a promotion of an existing
accepted rule to the surface where it always belonged, not a new obligation, so its cost is a
pointer replacing a body and its risk is close to zero. The claim is scope, not effect.

## Consequences

- `count:wos-topics` drops from 50 to 49 and `structural-evals.py` returns to a full pass. The
  repository had exactly one failing structural check before this ADR, and a single standing red
  masks the next real one.
- D-1 widens a gate, so it can fire on runs that previously passed. That is the intent; the discharge
  is one line and an N/A is explicitly allowed, so the cost on a slice outside the mechanism stays at
  one sentence.
- D-2 moves a rule into the always-read spec, which is under a non-regression size ceiling
  (ADR-0136). The move is close to size-neutral because `implementation-plan` sheds the body it keeps
  a pointer to, and the spec ceiling is re-checked by `structural-evals.py` on the same run.
- The five confirmed-correct gates are now recorded as reviewed. A future pass over the advisory can
  skip them.
- The advisory count drops as the exemption lands and the two fixes cite this ADR, which is the
  intended direction and NOT a measure of whether the repository improved. The number is a reading
  list length, not a defect count.

## Alternatives considered

- **Widen all four flagged gates in one pass.** Rejected: two of them need a shared block or a bounded
  definition rather than a reworded trigger, and bundling them would either rush those or stall the
  two that are ready. D-4 records them so the deferral is a decision with a stated reason rather than
  an omission.
- **Give the orphan topic a trigger instead of retiring it.** Considered seriously, since the content
  is real and its bug-class cross-references resolve. Rejected on two counts: the topic is
  vertical-specific in a way no current command routes to, and wiring it in would propagate vendor
  product names from a normative heading into a command's read map. Retiring is reversible through
  git; propagating a naming violation is the harder thing to undo.
- **Loosen `check-gate-provenance.sh` to accept any decision cite, not just `ADR-`.** Rejected: a
  `D-N` cite points at a task-local decision record that does not survive the task folder's archival,
  while an ADR is permanent and public. The exemption list is the narrower fix and it names the case.

---
activation: model_decision
description: The generalized slice-closure floors, verbatim per-command variants for implement-approved-slice (inline-close), slice-closure and task-close (whole-task backstops). Load before deciding any slice closure verdict.
---

# Closure floors

The generalized floors that gate a slice from closing. Each is written once here,
with its per-command variant, and is referenced from `commands/slice-closure.md`
and `commands/implement-approved-slice.md` rather than duplicated into both.

## When to load this file

**Always, before emitting a closure verdict.** Unlike `wos/platform-runtime-floors.md`,
which fires only on a Godot or mobile task signature, these floors are
UNCONDITIONAL: every slice passes through them. The load is lazy only in the sense
that a run which never reaches a closure decision never pays for it. A run that is
deciding whether a slice closes MUST read this file first; skipping it is not an
optimization, it is skipping the gate.

Two homes, always. `implement-approved-slice` closes a LOW or MEDIUM slice inline
and does not route to `slice-closure`, so each floor carries an inline-close
variant and a slice-closure variant. The rule behind that pairing, and why a floor
written to one home only never fires, is `wos/gate-conditions.md`
`### A closure floor needs two homes, or it does not exist`.

**G3 safeguard (same rule as the platform floors).** The closure notes SHALL cite
which subsections were read and applied. A lazy load that degrades into a
paraphrase is the failure mode this citation exists to catch: a floor recalled
from memory is a floor that drifts.

**Three homes since ADR-0134 (2026-08-09).** `task-close`'s whole-task backstops now
live here too, under `### task-close variant`. ADR-0124 had left them inline on three
reasons; its reason 2 ("it sits at 8521 tokens with headroom") decayed to a 336-token
margin, while its reason 1 stands and is exactly why these are a DISTINCT variant
family: a whole-task backstop reads recorded evidence across every slice rather than
gating one. `commands/task-close.md` keeps every floor NAMED inline with its trigger
and its routing, and three of them additionally keep the exact string their runner
emits. The solo/local auto-waiver did not move: it is a gate modifier, not a floor.

**What a floor waits for (2026-09-16).** A floor SHALL NOT wait for a HUMAN attester, and SHALL still
refuse to close when no attester of any kind produced the evidence it names. The two halves matter
separately. Removing the first is what this rule is for: a floor that held the chain until a person
looked was friction, and the runtime gates now capture their own evidence. Removing the second would
convert an unverified run into a silent pass, which is worse than the friction it saves.

Each floor below declares one of three behaviors on its own line, beside `Attester class:`:

- `On missing evidence: record` -- the floor writes `unverified: <reason>` and closure proceeds. The
  task's final report lists every floor left in this state, so nothing disappears quietly.
- `On missing evidence: refuse` -- the floor refuses and routes. Reserved for the floors that prevent
  LOSING work rather than adding friction, where proceeding destroys something instead of skipping a
  check.
- `On missing evidence: reconcile` -- the floor records the unsatisfied constraint as a named deferral
  and closure proceeds.

The two lines answer different questions and neither substitutes for the other. `Attester class:` says
WHO can produce the evidence. `On missing evidence:` says what happens when nobody did.

Where a `record` goes. The floor writes `unverified: <reason>` into the closing slice's notes, and
`task-close` collects every one of them into an `### Unverified floors` block in the final report
(its Required output item 7a). The collection is built from those recorded lines rather than
re-derived at closing time, so the report cannot claim a floor was checked when nothing checked it.
A floor that records without that block reaching a reader is indistinguishable from a floor that was
skipped, which is why the two halves ship together.

In an attended chain that reaches a draft pull request (ADR-0233), the reader is met earlier: the
same recorded `unverified:` lines are listed under `Not verified` in the draft pull request body, built
from the slice notes the same way, so the person sees them before marking the draft ready for review.
`task-close` still collects them at closure. Unattended, background and fleet-dispatched runs keep
each floor's behavior exactly as its `On missing evidence:` line states.


---

## Commit-evidence floor (ADR-0084, bounded deferral per ADR-0100, no-VCS waiver per ADR-0128)

**Criterion without the attester.** The slice's work is reachable in a citable git object. The class describes what the criterion admits, not what policy permits: the routing to `branch-commit --apply` below is unchanged, and whether a non-human attestation satisfies this floor is a separate question this line does not answer.

Attester class: agnostic

On missing evidence: refuse -- uncommitted work can be lost outright, which is not a skipped check

**The no-VCS waiver (ADR-0128), shared by both variants below.** A fourth route exists for the one case the three above cannot express: a workspace that has no version control at all and will not get any. All THREE conditions must hold, and the waiver is recorded as `no-vcs waiver: <workspace path> (<verbatim user decision>)`:

1. The workspace genuinely has no VCS. `git rev-parse --is-inside-work-tree` fails at the product path and no other VCS is in use. This is a fact the command CHECKS, not a claim it accepts.
2. The user declined version control for this workspace explicitly, in their own words, in this session, and that decision is recorded VERBATIM in the slice notes beside the fact from condition 1. Silence, an unanswered question, a model's reading of the situation, and an inference from "no `.git` present" are each not a user decision.
3. The preserved work is NAMED: the slice notes state which paths hold the uncommitted deliverable, so a later reader can find it.

With all three present the slice may close and the floor is satisfied. With any one absent the floor is unsatisfied and the routing below is unchanged. This route NEVER fires on a git-backed repository: a repo whose operator is merely absent, forbidden, or unattended stays on the bounded deferral, which is the case ADR-0100 decided and does not reopen. It is also recorded separately from the `task-close` archive-with-waiver: neither authorizes the other. The reason a fourth route exists at all is that `deferred: pending human commit` is FALSE in a workspace that will never have a repository, and writing it there is the permanent-skip-disguised-as-bounded that ADR-0098 rules out for the sibling floors.

**The ignored-path waiver (ADR-0194), shared by both variants below.** A fifth route exists for the one case the four above cannot express: a deliverable whose only home is a path the repository deliberately and permanently ignores. ADR-0133 named this question and left it open on purpose, because whether work is committable at all is a different question from who may attest it. All THREE conditions must hold, and the waiver is recorded as `ignored-path waiver: <deliverable path> (<ignore file>:<line> <pattern>)`:

1. The path is PROVABLY ignored AND the ignoring pattern is COMMITTED. `git check-ignore -v <deliverable path>` succeeds and its output is cited verbatim in the notes, and the matching pattern is present in the ignore file at HEAD rather than in an uncommitted working-tree edit. Both halves are facts the command CHECKS, not claims it accepts. The second half exists so that a run cannot write its own exemption into `.gitignore` and then invoke this route.
2. The ignored path is the deliverable's ONLY home, and the deliverable is not DERIVED from anything committable. Build output fails this condition: `dist/bundle.js` is ignored, but it is produced from a committable source, so the slice's work IS committable and this route does not apply. The question is never whether the artifact is ignored; it is whether a committable form of the work exists anywhere.
3. The preserved work is NAMED: the notes state which paths hold the deliverable, so a later reader can find it.

With all three present the slice may close and the floor is satisfied. With any one absent the floor is unsatisfied and the routing below is unchanged. This route NEVER fires because the operator is absent, forbidden, or unattended: each of those stays on the bounded deferral, which is the case ADR-0100 decided and this does not reopen. It fires only where the path CANNOT receive a commit, which is a property of the repository's own recorded decision rather than of the session. It carries no verbatim user decision, unlike the no-VCS waiver's condition 2, because there is nothing here for a user to disambiguate: a missing `.git` reads equally as "never" and as "not yet", while a committed ignore pattern is the decision already written down, and condition 1 makes the command read it. Requiring the user to restate it in session would either block the route or invite a fabricated quote. Like the no-VCS waiver it does NOT travel to `task-close`: it is evidence that home reads, never a route that satisfies it.

### implement-approved-slice variant (inline-close)

**Commit-evidence floor (inline-close; ADR-0084, bounded deferral per ADR-0100, third home per ADR-0105, no-VCS waiver per ADR-0128, `ref-attested` route per ADR-0133).** A slice SHALL NOT close inline (the LOW/MEDIUM path) unless its work is evidenced by one of the two attestation classes below, OR an explicit committing-waiver covering only genuinely discardable work (a deliberate throwaway, a spike whose value was the learning) is recorded, OR the three-condition no-VCS waiver above is recorded in the slice notes.

The two classes, either of which satisfies this floor:

- `commit-ref`: the work is committed and the slice notes cite the commit reference. Where a human turn is available this is the route, and a run with a human present SHALL route to `branch-commit --apply`, the only path in this repository that can create a commit. An unattended run driven by an external execution layer MAY reach `commit-ref` by the driver-owned-branch route in `wos/autonomous-track.md ## The autonomous commit route`: the layer stages by explicit path and commits bare onto a non-default branch it owns, never merging, pushing or opening a pull request. That route's safety rests on the layer REFUSING to start on a default or integration branch, so an admitted commit has nowhere else to land. The direct-use `autonomous-run` command cannot use this route.
- `ref-attested`: the external execution layer created a git object holding the run's work and pointed a quarantine ref at it under `refs/fhorja/attested/<run-id>/<invocation-id>`, and the slice notes cite that ref. An external execution layer that cannot use its driver-owned branch SHALL route to `ref-attested`. The agent and direct-use `autonomous-run` never write this ref; the layer does, after the agent's turn has ended.

Real work in a git-backed workspace with NEITHER class present, including an unattended session where git is unavailable or forbidden or where the attestation could not be made, is a BOUNDED DEFERRAL: record `deferred: pending human commit (<one-line context>)`, do NOT inline-close, and leave the slice open for the next human session. IF the slice's work carries neither attestation class, is neither genuinely waived nor covered by the no-VCS waiver, nor recorded as a bounded deferral, THEN do not inline-close; route to `branch-commit --apply`. It is Agent-mode only and refuses unattended (ADR-0163), so THAT COMMAND never satisfies this floor unattended. An external execution layer may instead use its driver-owned-branch route to `commit-ref` (`wos/autonomous-track.md ## The autonomous commit route`) or route to `ref-attested`. Direct-use `autonomous-run` has neither capability: it records the bounded deferral and leaves the slice open for the next human session. The no-VCS waiver is unreachable because its condition 2 needs a user present to state the decision.

### slice-closure variant

**Commit-evidence floor (ADR-0084, bounded deferral per ADR-0100, no-VCS waiver per ADR-0128, `ref-attested` route per ADR-0133).** A slice is not `ready to close` unless its work carries one of the two attestation classes below, or an explicit waiver of committing is recorded, or the three-condition no-VCS waiver above is recorded in the closure notes.

- `commit-ref`: the work is committed and the closure notes cite the commit reference. Where a human turn is available, route to `branch-commit --apply`, the only path in this repository that can create a commit. An unattended run driven by an external execution layer may reach this class through the driver-owned-branch route (`wos/autonomous-track.md ## The autonomous commit route`), whose four conditions are the branch not being default or integration, the layer owning it, no merge or push or pull request, and explicit staging with a bare commit. Direct-use `autonomous-run` cannot use this route.
- `ref-attested`: the external execution layer pointed a quarantine ref at a git object holding the run's work, under `refs/fhorja/attested/<run-id>/<invocation-id>`, and the closure notes cite that ref. An external execution layer that cannot use its driver-owned branch SHALL route to `ref-attested`; the agent and direct-use `autonomous-run` never write the ref.

A committing-waiver covers ONLY genuinely discardable work (a deliberate throwaway, a spike whose value was the learning). Real work with neither class present in a git-backed workspace, including an unattended session where git is unavailable or forbidden or where the attestation could not be made, is a BOUNDED DEFERRAL: record it as `deferred: pending human commit (<one-line context>)`, classify the slice `not ready to close`, leave it open for the next human session, and route to `/sync-task-state` so the open deferral is persisted; `branch-commit --apply` is the first action of that human session. A waiver line on real work does not satisfy this floor. IF the slice's work carries neither attestation class, is neither genuinely waived nor covered by the no-VCS waiver, nor recorded as a bounded deferral, THEN classify it `not ready to close` and route to `branch-commit --apply`. That command is Agent-mode only and refuses unattended (ADR-0163), so THAT COMMAND never satisfies this floor unattended. An external execution layer may use its driver-owned-branch route to `commit-ref` or route to `ref-attested`; direct-use `autonomous-run` records the bounded deferral and leaves the slice open. This is the slice-level counterpart to the `task-close` floor; it closes the observed failure where slices were marked done with the work uncommitted (the dogfood behind ADR-0084), the ADR-0100 refinement closes the follow-on failure where an unattended run could waive real work closed (5 of 10 paths in the 2026-07-11 wave hit exactly this gap), and the ADR-0128 route closes the third failure where a slice with no available route was simply closed anyway and legalized retroactively at `task-close` (the 2026-08-06 Kimi dogfood, five slices).


### task-close variant

**Commit-evidence floor (ADR-0084, bounded deferral per ADR-0100, `ref-attested` route per ADR-0133).** Even when merge (condition 4) is waived, closure requires one of the two attestation classes below, or an explicit recorded waiver of committing. The classes are `commit-ref` (the closed work is committed and the reference is cited; where a human turn is available, route to `branch-commit --apply`) and `ref-attested` (an external execution layer pointed a quarantine ref at a git object holding the run's work, under `refs/fhorja/attested/<run-id>/<invocation-id>`, and the closure record cites that ref). An unattended external execution layer reaches `commit-ref` through its driver-owned-branch route (`wos/autonomous-track.md ## The autonomous commit route`) when its four conditions hold and SHALL route to `ref-attested` otherwise. Direct-use `autonomous-run` creates neither class; it records the bounded deferral and leaves the task open for the next human session. A committing-waiver covers ONLY genuinely discardable work (a deliberate throwaway, recorded verbatim, with the discard rationale); real work carrying neither class, including an unattended session where git was unavailable or forbidden or where the attestation could not be made, is a BOUNDED DEFERRAL: the task stays open (not archived) pending the human commit, recorded as `deferred: pending human commit (<one-line context>)`. The gate-blocked result for a bounded deferral names the human commit as the smallest unblocking action (then `branch-commit --apply`). A waiver line on real work does not satisfy this floor. IF the work carries neither attestation class, is not genuinely waived, nor the archive is explicitly authorized by the user WITH the deferral on the record (an archive-with-waiver decision naming the preserved uncommitted work, e.g. an audit-purpose dogfood folder), THEN do NOT archive; return gate-blocked and route to `branch-commit --apply`, the only path in this repository that can create a commit (Agent-mode only and refuses unattended under ADR-0163, so it never satisfies this floor unattended). This closes the observed failure where a task archived as done with the work uncommitted (the dogfood behind ADR-0084 archived two tasks with 41 uncommitted files). A waived merge that still cites a commit satisfies the floor. **Relation to the slice-level no-VCS waiver (ADR-0128):** a slice may close under a three-condition `no-vcs waiver` recorded in its own notes (see `wos/closure-floors.md ## Commit-evidence floor`). Those waivers are EVIDENCE this floor reads, never a route that satisfies it: cite them here, then still obtain the archive-with-waiver authorization at closure as this floor already requires. A slice-level waiver does NOT travel to this home (ADR-0128 decision, "It does not travel to `task-close`"), because a decision taken once when the first slice closed would otherwise satisfy the archiving gate for every slice after it, which is the cascade this floor exists to stop and the exact shape of the 2026-08-06 dogfood failure. The two routes stay recorded separately and neither authorizes the other. **Routing in this case:** the `branch-commit --apply` fallback below is unreachable here, because condition 1 of the slice-level waiver already established that no repository exists; do NOT route to it. Ask the user for the archive-with-waiver authorization instead, and WHEN they decline, leave the task open recording `no archive authorization for a no-VCS workspace` as the reason. An open task with a stated reason is the honest outcome; routing to a command the workspace makes impossible is a loop.


---

## Experience-verdict floor (ADR-0091, generalizes ADR-0089 D-4)

**Criterion without the attester.** The recorded `Attested by:` value names who reached the verdict. The erasure fails here: remove that line and only "a PASS block exists" survives, which any writer satisfies. `run` is valid ONLY when the block cites the evidence the run itself captured (the screenshot path it wrote, the runtime output it quoted, the route it probed); `human` means a person experienced a sample. An artifact may never claim `human` for a verdict no person reached (ADR-0179).

Attester class: agnostic

On missing evidence: record -- S7 made the evidence capturable by the run; `Attested by: run` is a real attester

### implement-approved-slice variant (inline-close)

**Experience-verdict floor (inline-close, generalized, ADR-0091).** WHEN the slice's deliverable carries the tag `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags), the slice SHALL record `unverified: no experience verdict on a sample` and close inline unless a recorded experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` AND a mandatory `Attested by:` line valued `run` or `human`, cited in the slice notes) is present OR an explicit one-line skip reason is recorded. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict: it attests as itself, `Attested by: run`, and only when the block cites the evidence the run captured; it is never recorded as `human` (ADR-0179). IF the deliverable text plainly indicates user-facing content and no tag is present THEN treat the slice as tagged and flag the missing tag. IF neither is present THEN record `unverified: no experience verdict on a sample` in the slice notes, name the experience-verdict check as what would produce one, and close inline. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor in `wos/platform-runtime-floors.md ## Godot feel-verdict floor (D-4, ADR-0089)`. Do not record a decorative skip. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one. Same bounded-vs-permanent skip rule as that D-4 floor applies here (ADR-0098): a "no human, ever" skip reason does not satisfy this floor.

### slice-closure variant

**Experience-verdict floor (generalized, ADR-0091).** WHEN the closing slice's own deliverable carries the tag `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags; a tag on a different slice's row does not fire this floor), closure at this home SHALL require a recorded experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` AND a mandatory `Attested by:` line valued `run` or `human`, cited in the slice notes or task record) OR an explicit one-line skip reason. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict: it attests as itself, `Attested by: run`, and only when the block cites the evidence the run captured; it is never recorded as `human` (ADR-0179). IF the deliverable text plainly indicates user-facing content and no tag is present THEN treat the slice as tagged and flag the missing tag. IF neither the verdict nor a skip reason is present THEN record `unverified: no experience verdict on a sample` in the closing notes, name the experience-verdict check as what would produce one, and close. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor in `wos/platform-runtime-floors.md ## Godot feel-verdict floor (D-4, ADR-0089)`. Do not record a decorative skip. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one. Same bounded-vs-permanent skip rule as that D-4 floor applies here (ADR-0098): a "no human, ever" skip reason does not satisfy this floor.


### task-close variant

**Experience-verdict floor (generalized, ADR-0091).** WHEN the task's closure includes a deliverable tagged `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags), closure requires a recorded experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` AND a mandatory `Attested by:` line valued `run` or `human`, cited in the task record) OR an explicit one-line skip reason recorded in the final `TASK_STATE.md`. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict: it attests as itself, `Attested by: run`, and only when the block cites the evidence the run captured; it is never recorded as `human` (ADR-0179). IF a deliverable's text plainly indicates user-facing content and no tag is present THEN treat it as tagged and flag the missing tag. IF neither is present THEN record `unverified: no experience verdict on a sample` and archive, naming the experience-verdict check in the final report's `### Unverified floors` block. This is the whole-task backstop for the F-1 enforcement. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor in `wos/platform-runtime-floors.md ## Godot feel-verdict floor (D-4, ADR-0089)`. Do not record a decorative skip. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one.


---

## Entry-path probe floor (ADR-0091)

**Criterion without the attester.** The user's real entry path was exercised once and the run is recorded. The word `operator` appears only in this floor's routing sentence and never in its criterion, so what survives the erasure is a recorded execution rather than a perception; the entry path is the runtime a checkout lacks.

Attester class: environment-bound

On missing evidence: record -- the probe is capturable by the run on every surface that has one

### implement-approved-slice variant (inline-close)

**Entry-path probe floor (inline-close, ADR-0091).** WHEN the slice ships a deliverable tagged `new-user-facing-surface`, it SHALL record `unverified: entry path never exercised` and close inline unless one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) is cited in the slice notes OR an explicit one-line skip reason is recorded. IF neither is present THEN record `unverified: entry path never exercised` in the slice notes, name running the entry path once as what would produce the evidence, and close inline. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor in `wos/platform-runtime-floors.md ## Godot feel-verdict floor (D-4, ADR-0089)`.

### slice-closure variant

**Entry-path probe floor (ADR-0091).** WHEN the slice ships a deliverable tagged `new-user-facing-surface`, closure at this home SHALL require one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) cited in the slice notes OR an explicit one-line skip reason. IF neither is present THEN record `unverified: entry path never exercised` in the closing notes, name running the entry path once as what would produce the evidence, and close. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor in `wos/platform-runtime-floors.md ## Godot feel-verdict floor (D-4, ADR-0089)`.


### task-close variant

**Entry-path probe floor (ADR-0091).** WHEN the task's closure includes a deliverable tagged `new-user-facing-surface`, closure requires one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) cited in the task record OR an explicit one-line skip reason recorded in the final `TASK_STATE.md`. IF neither is present THEN record `unverified: entry path never exercised` and archive, naming the entry-path run in the final report's `### Unverified floors` block. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor in `wos/platform-runtime-floors.md ## Godot feel-verdict floor (D-4, ADR-0089)`.


---

## Eval-threshold floor (ADR-0104)

**Criterion without the attester.** The recorded score met the plan's pass threshold on its held-out set. The floor reads a recorded outcome, but producing that outcome needs the model-backed feature run against the held-out set, which a checkout cannot supply.

Attester class: environment-bound

On missing evidence: record -- an absent eval run is a missing measurement, not lost work

### implement-approved-slice variant (inline-close)

**Eval-threshold floor (inline-close, ADR-0104).** WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature this slice ships or changes, the slice SHALL record `unverified: no eval outcome cited` and close inline unless the recorded eval OUTCOME (the score against the plan's pass threshold on its held-out set) is cited in the slice notes with the threshold met, OR an explicit one-line skip reason is recorded (bounded-vs-permanent per ADR-0098: a bounded deferral satisfies it, a permanent "the eval will never run" does not). An exit criterion worded around the harness mechanism ("the harness runs", "the eval executes") SHALL NOT substitute for the threshold outcome: a green harness execution with a failing score FAILS this floor. IF the outcome is absent THEN record `unverified: no eval outcome cited`, name running the eval per `AI_EVAL_PLAN.md` first.

### slice-closure variant

**Eval-threshold floor (ADR-0104).** WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature the closing slice ships or changes, the slice SHALL record `unverified: no eval outcome cited` and close unless the recorded eval OUTCOME (the score against the plan's pass threshold on its held-out set) is cited with the threshold met, OR an explicit one-line skip reason is recorded (bounded-vs-permanent per ADR-0098). An exit criterion or closure note worded around the harness mechanism ("the harness runs") SHALL NOT substitute for the threshold outcome: a green harness execution with a failing score FAILS this floor. IF the outcome is absent THEN record `unverified: no eval outcome cited` and close, naming the eval per `AI_EVAL_PLAN.md`. No-op when the task has no `AI_EVAL_PLAN.md` or the slice does not touch the evaluated feature.


---

## Integrity floor (v3 wave3 item S1)

**Criterion without the attester.** `verify-substrate-batch.sh` exited 0 for this task folder.

Attester class: agnostic

On missing evidence: refuse -- it caught two real protocol defects on 2026-09-16; a broken substrate that closes is unrecoverable by reading

### slice-closure variant

**Integrity floor (blocking; v3 wave3, item S1).** Run `bash scripts/verify-substrate-batch.sh <task-folder>` as part of the closure evidence. WHEN the wrapper exits non-zero the slice is not `ready to close` UNLESS an explicit waiver line is recorded in the closure notes: `integrity-waiver: N advisories unresolved (<one-line reason>)`, naming the failing validator(s) from the wrapper's summary line. A silent non-zero is never absorbed; a recorded waiver travels into the closure record. This floor consumes the wrapper's exit code and never re-implements the validators (wave-2 D-3 boundary); it keys on exit codes only, so the informational header-drift count (which never flips an exit code) cannot fire it. Checkpoint-eligible as a mechanical floor: the resume verdict is the re-run's exit code. This flips the v2 S1 finding (integrity advisories grew 13 to 23 while every validation reported OK). Resolve `scripts/verify-substrate-batch.sh` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224), never against the task repository. WHEN it is in neither, record `integrity: not checked (verify-substrate-batch not installed)` and name a re-sync of the install: that line is neither a pass nor a waiver, so the floor holds exactly as it does for a non-zero exit.

### implement-approved-slice variant (inline-close)

**Integrity floor (inline-close, blocking; v3 wave3, item S1).** Before closing a slice inline, run `bash scripts/verify-substrate-batch.sh <task-folder>`. WHEN the wrapper exits non-zero the slice SHALL NOT close inline UNLESS an explicit waiver line is recorded in the slice notes: `integrity-waiver: N advisories unresolved (<one-line reason>)`, naming the failing validator(s) from the wrapper's summary line. With neither a zero exit nor the waiver, route to `slice-closure`, whose variant of this floor holds the slice until the validators pass or the waiver is recorded. A silent non-zero inline close is invalid output. Consumes the wrapper's exit code only (never re-implements the validators; the informational header-drift count cannot fire it). Most slices close on this path, so a floor with only the `slice-closure` home skipped the one check that the K.2 headers and the `.wos/VERIFICATION_LOG.jsonl` lines a slice was told to write actually exist. Resolve `scripts/verify-substrate-batch.sh` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224), never against the task repository. WHEN it is in neither, record `integrity: not checked (verify-substrate-batch not installed)` and name a re-sync of the install: that line is neither a pass nor a waiver, so the floor holds exactly as it does for a non-zero exit.


### task-close variant

**Integrity floor (blocking; v3 wave3, item S1).** Run `bash scripts/verify-substrate-batch.sh <task-folder>` before archiving. WHEN the wrapper exits non-zero the task SHALL NOT be archived UNLESS an explicit waiver line is recorded in the final `TASK_STATE.md`: `integrity-waiver: N advisories unresolved (<one-line reason>)`, naming the failing validator(s). A silent non-zero archive is invalid. Consumes the wrapper's exit code only (never re-implements the validators; the informational header-drift count cannot fire it). Whole-task backstop of the slice-level floor in `slice-closure`. Resolve `scripts/verify-substrate-batch.sh` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224), never against the task repository. WHEN it is in neither, record `integrity: not checked (verify-substrate-batch not installed)` and name a re-sync of the install: that line is neither a pass nor a waiver, so the floor holds exactly as it does for a non-zero exit.


---

## Layer-2 review floor (wos/gate-conditions.md, skip semantics per ADR-0098)

**Criterion without the attester.** A risk review ran against the slice's current HEAD and its verdict is cited. The floor's own text already admits an alternative emitter ("or the host repository's own equivalent gate, cited by whatever name it carries there"), which is this class already stated for this floor. Whether that admission generalizes to other floors is a separate question this line does not settle.

Attester class: agnostic

On missing evidence: record -- a missing review is a skipped check, and the skip is now visible in the final report

### implement-approved-slice variant (inline-close)

**Layer-2 review floor (inline-close; layering rule: `wos/gate-conditions.md` `## Verification layering`; skip semantics per ADR-0098).** A slice SHALL record `unverified: no Layer-2 review` and close inline unless a Layer-2 risk review ran against the slice diff and its verdict is cited in the slice notes: `review-hard` (plus `security-review` when the slice has a security surface), or the host repository's own equivalent gate, cited by whatever name it carries there, OR an explicit one-line skip reason. The command's inline exit-criteria checklist is Layer 1 and SHALL NOT substitute for it. IF neither a cited verdict nor a skip reason is present THEN record `unverified: no Layer-2 review` in the slice notes, name `review-hard` as what would produce one, and close inline. This floor matters most on the path that skips `slice-closure` entirely: LOW and MEDIUM slices are where an unreviewed defect travels furthest before anyone looks (mobile dogfood 2026-07-29: 5 LOW and 3 MEDIUM slices, zero Layer-2 reviews, and the first review returned 4 defects spanning two slices already treated as done).

**Coverage of the cited verdict (worktree dogfood 2026-08-04).** The cited verdict SHALL cover the slice's current HEAD. WHEN a commit exists on the slice that is newer than the reviewed ref, the slice SHALL declare `Layer-2 coverage:` naming exactly one closed case: (a) the later delta changes no byte that crosses a process boundary (nothing persisted, serialized, sent over the network, or read by another module), or (b) the later delta applies findings from the cited verdict itself AND none of them changes a persisted value or a public signature. An enum value that persists to a database does NOT qualify under (a), and qualifies under (b) only when the cited verdict named that rename. IF neither case applies THEN record `unverified: Layer-2 verdict predates the current HEAD` in the slice notes, name `review-hard` against the current HEAD as what would settle it, and close inline.

**A zero-finding cited verdict does not satisfy this floor alone (ADR-0145).** WHEN the cited Layer-2 verdict names zero must-fix and zero should-fix findings AND the slice diff touched product code, the floor additionally requires the `verify-against-rubric` verdict id alongside it. A cited verdict WITH findings satisfies the floor exactly as it does today, and the one-line skip reason remains available and unchanged. The reason is not that a clean review is suspect in general: it is that a reviewer holding the authoring rationale can audit a finding it produced and cannot audit the absence of one it did not, so the empty verdict is the single output of that reviewer with no in-context check available. IF a zero-finding verdict is cited without the blinded verdict id THEN record `unverified: zero-finding verdict with no blinded id` and close inline, naming `verify-against-rubric` with the slice's exit criteria as the rubric and the diff as the artifact.

**Internal-reuse sweep floor (inline-close; ADR-0145 D-3).** A slice that added a file or an exported symbol into a directory that ALREADY contained siblings SHALL record `unverified: no internal-reuse sweep` and close inline without one of: a cited `repo-consistency-sweep` run over this slice's diff whose snapshot names `sibling-controller-divergence`, `sibling-route-divergence`, and `custom-component-when-ds-exists` among the classes its class-selection step chose; a named host-repository equivalent gate, cited by whatever name it carries there; or an explicit one-line skip reason. The cite is the snapshot file path, not a claim that the sweep ran. The trigger is evaluated against the finished diff, where "a directory that already contained siblings" is a directory listing rather than a judgment. The failure this closes: the three classes describe internal-reuse defects precisely and are consumed only by a command that a 6,010-tool-call corpus never invoked, which makes good detection content and no detection content indistinguishable in outcome.

### slice-closure variant

**Layer-2 review floor (layering rule: `wos/gate-conditions.md` `## Verification layering`; skip semantics per ADR-0098).** A slice SHALL record `unverified: no Layer-2 review` and close unless a Layer-2 risk review ran against the slice diff and its verdict is cited in the closure notes: `review-hard` (plus `security-review` when the slice has a security surface), or the host repository's own equivalent gate, cited by whatever name it carries there, OR an explicit one-line skip reason. Layer 1 green SHALL NOT substitute: a passing typecheck, lint and test run satisfies the layer below this one and says nothing about risk. IF neither a cited verdict nor a skip reason is present THEN record `unverified: no Layer-2 review` in the closing notes, name `review-hard` as what would produce one, and close. Reviewing while the slice is small and fresh is what keeps a defect from surfacing later inside a slice already marked done (mobile dogfood 2026-07-29: 4 closures against 8 floors, zero Layer-2 reviews, and the first review returned 4 defects spanning two closed slices).

**Coverage of the cited verdict (worktree dogfood 2026-08-04).** The cited verdict SHALL cover the slice's current HEAD. WHEN a commit exists on the slice that is newer than the reviewed ref, the slice SHALL declare `Layer-2 coverage:` naming exactly one closed case: (a) the later delta changes no byte that crosses a process boundary (nothing persisted, serialized, sent over the network, or read by another module), or (b) the later delta applies findings from the cited verdict itself AND none of them changes a persisted value or a public signature. An enum value that persists to a database does NOT qualify under (a), and qualifies under (b) only when the cited verdict named that rename. IF neither case applies THEN record `unverified: Layer-2 verdict predates the current HEAD` in the closing notes, name `review-hard` against the current HEAD as what would settle it, and close.

**A zero-finding cited verdict does not satisfy this floor alone (ADR-0145).** WHEN the cited Layer-2 verdict names zero must-fix and zero should-fix findings AND the slice diff touched product code, the floor additionally requires the `verify-against-rubric` verdict id alongside it. A cited verdict WITH findings satisfies the floor exactly as it does today, and the one-line skip reason remains available and unchanged. The reason is not that a clean review is suspect in general: it is that a reviewer holding the authoring rationale can audit a finding it produced and cannot audit the absence of one it did not, so the empty verdict is the single output of that reviewer with no in-context check available. IF a zero-finding verdict is cited without the blinded verdict id THEN record `unverified: zero-finding verdict with no blinded id` and close, naming `verify-against-rubric` with the slice's exit criteria as the rubric and the diff as the artifact.

**Internal-reuse sweep floor (ADR-0145 D-3).** A slice that added a file or an exported symbol into a directory that ALREADY contained siblings SHALL record `unverified: no internal-reuse sweep` and close without one of: a cited `repo-consistency-sweep` run over this slice's diff whose snapshot names `sibling-controller-divergence`, `sibling-route-divergence`, and `custom-component-when-ds-exists` among the classes its class-selection step chose; a named host-repository equivalent gate, cited by whatever name it carries there; or an explicit one-line skip reason. The cite is the snapshot file path, not a claim that the sweep ran. The trigger is evaluated against the finished diff, where "a directory that already contained siblings" is a directory listing rather than a judgment.


---

## Rollout-constraint reconcile (mobile dogfood 2026-07-29)

**Criterion without the attester.** Every constraint in the plan's rollout notes that names a file, config key, or release track inside the slice's Scope is reconciled or deferred by name.

Attester class: agnostic

On missing evidence: reconcile -- an unsatisfied rollout constraint is a named deferral, not a verdict

### implement-approved-slice variant (inline-close)

**Rollout-constraint reconcile (inline-close, mobile dogfood 2026-07-29).** WHEN `IMPLEMENTATION_PLAN.md` carries a `## Rollout and rollback notes` section, check each constraint stated there against this slice's declared Scope before closing inline. A constraint naming a file, config key, or release track inside that Scope is reconciled when the slice notes state it is satisfied, or record it as a deferral naming what satisfies it and when. IF a constraint in Scope is unchecked THEN record it as a named deferral in the slice notes and close inline. The plan writes its rollout constraints before the code exists: on the source run the plan named the exact OTA-versus-native ordering hazard on day one, and it surfaced as the run's only CRITICAL 30 hours later.

### slice-closure variant

**Rollout-constraint reconcile (mobile dogfood 2026-07-29).** WHEN `IMPLEMENTATION_PLAN.md` carries a `## Rollout and rollback notes` section, check each constraint stated there against the closing slice's declared Scope. A constraint naming a file, config key, or release track inside that Scope is reconciled when the closure notes state it is satisfied, or record it as a deferral naming what satisfies it and when. IF a constraint in Scope is unchecked THEN record it as a named deferral in the closing notes and close. This joins the reconcile family below (deliverable-reconcile per ADR-0056, references-reconcile per X2). The plan writes its rollout constraints before the code exists, which makes closure the cheapest place to catch a release-track defect: on the source run the plan named the exact ordering hazard on day one and the review found it as the only CRITICAL 30 hours later.

---

## Test-strategy consumption floor (F-6, ADR-0089)

**Criterion without the attester.** Every `critical` and `regression` row in the task's `TEST_STRATEGY.md` maps to a real test file, or carries a recorded waiver.

Attester class: agnostic

On missing evidence: reconcile -- an unconsumed strategy row carries its waiver; the ADR-0089 contract already allows one

### task-close variant

**Test-strategy consumption floor (F-6, ADR-0089).** WHEN the task folder contains a `TEST_STRATEGY.md`, closure requires that every `critical` and `regression` scenario row in it maps to a real test file (cite the path in the closure evidence) OR carries a recorded waiver (in the strategy or the slice notes). For a `critical` row the citation SHALL also carry the falsifiability evidence that strategy's own rule requires (a red step, or one recorded mutation on a line the slice wrote, seen failing): a cited path backed only by a green suite is an unreconciled row, not a mapped one. IF any such row has neither THEN record it as a named deferral and archive, naming `implement-slice-complement` (write the missing tests under the same slice intent) or record the waiver first. This is the produce-side counterpart of the deliverable-reconcile gate: a deferral on the record is allowed, a silently orphaned strategy artifact is not. No-op when the task has no `TEST_STRATEGY.md`.

### implement-approved-slice variant (inline-close)

None. This floor reads a whole-task strategy artifact across every slice and has one home, `task-close`.

### slice-closure variant

None. Same reason as above.

---

## Unresolved-revision floor (ADR-0109, D-10)

**Criterion without the attester.** No defeasible-claim revision entry in `DECISIONS.md ## Decision history` is still marked `[OPEN]`.

Attester class: agnostic

On missing evidence: refuse -- an `[OPEN]` contradiction that closes is a recorded conflict silently dropped

### task-close variant

**Unresolved-revision floor (ADR-0109, D-10).** WHEN `DECISIONS.md ## Decision history` contains a defeasible-claim revision entry still marked `[OPEN]` (or `[OPEN: equal-rank, escalate]`), closure requires it be resolved first: a superseding decision, an accepted revision that updated the owning section, or an explicit `[WAIVED: <reason>]` tag. IF any `[OPEN]` revision remains THEN do NOT archive; return gate-blocked and route to `decision-interview` (resolve as a supersede or record the waiver) or `direction-adjust` (accept the revision into the owning section). In-task checkpoints (`slice-closure`, `where-we-at`) only annotate an `[OPEN]` revision and do NOT block; the block fires only at this whole-task closure. This is the whole-task backstop for the D-10 defeasible-claim mechanism (`wos/substrate-peers.md ## Decision history` write rule); it never fires when the task has no revision entry.

### implement-approved-slice variant (inline-close)

None. In-task checkpoints only annotate an `[OPEN]` revision; the block fires at whole-task closure.

### slice-closure variant

None. Same reason as above.

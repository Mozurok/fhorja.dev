# ADR-0248: The lean-context trim shows no detectable effect on quality or cost as shipped, so it ships as a clarity change, and the spec read stays as it is

- **Status**: Accepted. It rests on provisional decisions P-1 to P-6 of the 2026-10-08 lean-context-trim task, listed under `## Notes`, which await the maintainer's confirmation.
- **Date**: 2026-10-09
- **Tags**: context-engineering, command-trim, shared-blocks, spec-read, measured, guards, scenario-01, adr-0135, adr-0151, adr-0153

## Context

An article on context engineering for newer Claude models (read 2026-10-08) argued that instruction files have grown restrictive, that conflicting or repeated rules cost the model effort, and that long files should be cut and split. Fhorja's commands are long. `task-init` was 35,433 bytes, `implement-approved-slice` 34,699 and `slice-closure` 35,804, and `task-init` sat 9 characters under the 36,000-character hard Load ceiling (ADR-0116, ratcheted to 36,000 by ADR-0227).

An experiment ran the question instead of assuming it. It built a trimmed arm ("lean2": the three commands cut 15 to 21 percent and seven shared blocks 16 to 40 percent) and compared it with the repository as it stood, over three executing models (Haiku, Sonnet and Codex), four spine scenarios, four arms and three repetitions, 144 valid runs, graded by one fixed Opus grader against fixed rubrics. Independent checks followed: a second grader (Codex) on a 48-run sample, an adversarial review of each headline claim, and a bootstrap interval for every effect. The account's usage limit voided 11 Sonnet runs and failed 32 grader calls; those were rerun or regraded and none was averaged.

What that experiment found:

- lean2 showed no detectable quality loss on any model. The pass-rate difference against the base was -1.0 points for Haiku (interval -8.3 to +5.8), +4.7 for Sonnet (-4.3 to +17.9) and +1.5 for Codex (-6.0 to +9.0).
- lean2 cut Sonnet cost by about 15 percent (interval -21 to -8 percent), mostly in scenario 01. For Haiku and Codex no saving was detectable.
- lean2 was not safe to copy. Run on the structural suite, which the experiment had skipped, it failed four guards that the base passes (`memory-consume-path`, `bootstrap-floor-measured`, `leaf-reviewer-tier`, `godot-tier-floor-variants`) while `lint-commands.sh` still exited 0. Two further losses sat under no guard: the backend route-handler trigger in `implement-approved-slice` and the optional `verify-substrate-batch.sh` self-check in `task-init`.
- Forcing the read of `WORKFLOW_OPERATING_SYSTEM.md` before acting cost 40 to 117 percent more (Haiku dollar figures are unreliable, and Codex was measured in tokens only), and no quality benefit survived the adversarial checks. The apparent gains for Sonnet and Codex came from two fixture traps.

This ADR records what shipped and what was measured on the shipped text, not on lean2.

## Decision

Ship a hand-reviewed, smaller form of the trim as a clarity change, with the guards and fixes the experiment showed were missing, and change nothing about the spec read.

1. **Three commands, re-applied by hand.** `task-init`, `implement-approved-slice` and `slice-closure` keep every SHALL, MUST, NEVER, FORBIDDEN and WHEN trigger. Cuts remove dated narrative, ADR rationale clauses and repeated rules only. The four losses a guard or a gate reads are restored. A fifth was found by measurement and restored too (see Consequences).
2. **Shared blocks, guard-gated.** Four of the seven blocks are trimmed (`substrate-digest-fallback`, `deliverable-reconcile`, `references-reconcile`, `task-state-slice-closure-pattern`). Three are left alone: `claim-grounding` (the doctrine of ADR-0109, with about a 1 percent saving per invocation), `mandatory-context-bootstrap` (two guards read its measured figures and the edit touched the spec read list) and `reference-grounding` (the edit dropped the ADR ids other files use as pointers).
3. **A durable guard.** `trimmed-behavior-kept` in `evals/scripts/structural-evals.py`, with two mutation entries in `evals/scripts/guard-mutation.py`, fails when `task-init` loses its `verify-substrate-batch.sh` self-check or `implement-approved-slice` loses its route-handler trigger.
4. **Scenario 01 runs against a throwaway task repository** that holds `projects/`. It had run in the repository root, so a correct STOP 2 failed its rubric and a run could write into the maintainer's own `projects/`.
5. **The spec read is not changed.** `commands/_shared/mandatory-context-bootstrap.md` keeps its current read instruction. A per-command named-section list is written as an eval arm in `evals/lab/spec-read-named-sections.md` and measured, and it is not shipped.
6. **No cost or quality claim.** No effect on pass rate or cost was detected on the shipped text at 3 to 5 repetitions per cell. The intervals do not exclude a loss of about 10 points or a cost rise of about 14 percent on Sonnet, and no equivalence test was run. The change is justified by smaller files, more Load headroom and the measurement fixes, not by savings.

## Consequences

### Positive

- Smaller files and more headroom under the 36,000-character ceiling: `task-init` 35,433 to 31,426 bytes (-11.3 percent; its skill 35,991 to 31,984 characters, headroom 9 to 4,016), `implement-approved-slice` 34,699 to 33,172 (-4.4 percent; skill headroom 834 to 2,361) and `slice-closure` 35,804 to 33,077 (-7.6 percent; skill headroom 154 to 2,881).
- The `what-next` skill fell from 20,731 to 19,008 characters, below the 20,000-character re-injection cap, so it is no longer truncated to a summary after a compaction.
- A measurement found a real regression and the fix was verified. Run on Opus (scenario 01, Codex grader, 5 repetitions), criterion 6 (the Handoff follows the recorded escalations) passed 3 of 5 with the original text and 0 of 5 with the first form of the trim. Two trimmed runs skipped the escalation and routed to `implementation-plan`. The cause was two sentences cut from `task-init`: "The after-init route is set under Escalation assessment" and the `Handoff:` operating rule. Restoring them returned criterion 6 to 3 passed and 2 uncertain, the base result.
- Lint cannot see lost behavior; the structural suite, the new guard and a measurement on a second model tier together can. The task's harness is kept for reruns.

### Negative

- The command trim is smaller than the experiment suggested (4 to 11 percent against 15 to 21), because the rest was text that guards, floor views and tests read. The four shipped shared blocks were cut 16 to 40 percent and are taken unchanged from the experiment.
- No cost saving was found. On the shipped text, Sonnet (scenarios 01 and 03, 5 repetitions per arm, Opus grader) showed pass rate +1.4 points (interval -5.7 to +10.0) and cost +5 percent (-4 to +14). Scenario 01 alone showed pass rate -8.6 points (interval -17.1 to about 0), all of it uncertain verdicts and no failed criterion. The scenarios disagreed on cost: cost -12 percent in scenario 01 and +22 percent in scenario 03, where the share of runs that read the spec differed (40 and 80 percent). Opus (both scenarios, 5 repetitions per arm, Codex grader) showed pass rate -5.7 points (-14.3 to +1.4) and cost +15 percent (+7 to +23) for the first form of the trim, before the fix. After the fix Opus was run on scenario 01 only (5 repetitions): pass rate 60.0 against 74.3 percent (-14.3 points, interval -31 to +3) and cost +13 percent (1.48 against 1.31 dollars, interval -8 to +43). Opus scenario 03 was not run on the shipped text; the fix touched only `task-init`, which scenario 03 does not run.
- Opus scenario 01 still scored 60 percent against 74 percent after the fix, with `project-bootstrap` byte-identical in both arms and criterion 1, which grades only that turn, moving from 5 passed to 3 passed and 2 uncertain. That is the noise of 5 repetitions with one grader, and it is also the limit of what this evidence can show.
- Three shared blocks stay long.

### Neutral

- The spec read arm: on Sonnet, on the first form of the trim (commit e4fadd48, before the two-sentence restore, which did not touch the spec read instruction), scenarios 01 and 03, 3 repetitions each, the arms scored `skip` 85.7 percent at 0.65 dollars, `named` 83.3 percent at 0.98 and `force` 85.7 percent at 1.15. `named` against `skip`: pass -2.4 points (-11.9 to +7.1), cost +52 percent (+40 to +66). `force` against `skip`: 0.0 points (-9.5 to +9.5), cost +78 percent (+61 to +98). A Codex regrade of one repetition per cell (two runs per arm) also showed no separation beyond 7 points (50.0, 50.0 and 57.1 percent), though the two graders disagreed on individual criteria. The `named` cell of scenario 01 had no harness note on turn 1, because the arm defines no list for `project-bootstrap`. Opus read the spec in every run of both texts, so it cannot separate the arms. The read is not shown to help, and it is not shown to be waste.
- The Codex grader accepts fewer criteria than the Opus grader (55 against 73 percent on 48 runs) and agrees on pass versus not-pass for 80 percent of criteria. No arm separated under either.
- The advertise-stage description trim (ADR-0151, ADR-0153) was not part of this change.

## Alternatives considered

### Alternative 1: copy the experiment's trimmed files

- Port the lean2 text of the three commands and seven blocks as it was.
- Rejected: it failed four guards the experiment never ran and dropped two behaviors no guard covered. The hand review kept less than half of its cuts.

### Alternative 2: trim nothing and only add the guard

- Keep the files as they were and ship the guard, the fixture and the arm.
- Rejected: the cuts that survive removal of dated narrative and repeated rules are real, cost nothing measurable, and give `task-init` 4,016 characters of headroom where it had 9.

### Alternative 3: shorten or drop the mandatory spec read now

- Replace the read with a named-section list, or make it conditional.
- Rejected for now: on Sonnet the named list scored 2.4 points below `skip` and cost 52 percent more, and Opus read the spec regardless. Shipping a change that the data neither supports nor refutes needs its own decision.

## References

- [ADR-0116](./0116-single-load-stage-size-budget.md) and [ADR-0227](./0227-the-load-ceiling-ratchets-to-36000.md) (the Load ceiling), [ADR-0135](./0135-advertise-stage-aggregate-budget.md), [ADR-0151](./0151-the-advertise-routing-check-exists.md) and [ADR-0153](./0153-four-providers-agree-on-the-advertise-trim.md) (the description trim this change leaves alone).
- [ADR-0109](./0109-active-epistemic-humility-doctrine.md) (the claim-grounding doctrine whose block was left unchanged), [ADR-0214](./0214-wire-the-memory-consume-path.md) and [ADR-0119](./0119-godot-declaration-canonical-form.md) (guards the first trim broke).
- `evals/scripts/structural-evals.py` (`trimmed-behavior-kept`), `evals/scripts/guard-mutation.py`, `evals/fixtures/spine/01-bootstrap.sh`, `evals/lab/spec-read-named-sections.md`.
- `commands/task-init.md`, `commands/implement-approved-slice.md`, `commands/slice-closure.md`, and the four trimmed blocks in `commands/_shared/`.

## Notes

- Provisional decisions this rests on, from the 2026-10-08 lean-context-trim task: P-1 (scenario 01 as a fixture-backed scenario), P-2 (shared-block edits conditional on every guard), P-3 (the named-section list stays an eval arm), P-4 (the Opus check on the restored text, with a usage-limit hit voiding a run), P-5 (the trims re-applied by hand) and P-6 (the durable guard). The maintainer confirms or replaces them on the draft pull request. P-3 and P-4 spend account usage and carry `Impact: high`.
- Sample sizes are 3 to 5 repetitions per cell, which cannot detect an aggregate effect under about 10 points. Haiku and Sonnet arms were graded by Opus (the same model family); the Codex regrade covers one repetition per cell. No equivalence test was run on any comparison.
- The task's raw runs, the grader notes and the harness scripts stay in the maintainer's local task memory, outside this tree.

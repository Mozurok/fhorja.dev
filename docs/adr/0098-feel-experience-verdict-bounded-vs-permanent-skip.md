# ADR-0098: Bounded-vs-permanent skip distinction at the Godot feel-verdict and generalized experience-verdict closure floors

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: godot-cluster, experience-gate, closure-enforcement, skip-reason, slice-closure, implement-approved-slice, forcing-function, refines-adr-0089, refines-adr-0091, dogfood-driven

## Context

ADR-0089 (D-4) and ADR-0091 gave the Godot feel-verdict and the generalized experience-verdict closure floors a cheap escape: a recorded PASS OR an explicit one-line skip reason satisfies the floor, deliberately mirroring the ADR-0085 runtime-gate shape so ceremony stays low for a genuine no-runtime-surface or throwaway slice. The 2026-07-11 genre dogfood wave (three parallel, unattended Godot vertical-slice builds; task `2026-07-11_godot-genre-dogfood-wave`) surfaced that the same one-line escape equally satisfies a bounded, later-resolvable deferral (a human will review this soon) and a structurally permanent one (no human is EVER available in this session's environment). One of the three dogfood sessions manually overrode a literal reading of the floor, judging its own recorded skip insufficient to the gate's intent and keeping the task `not-ready-to-close` rather than exploiting the escape; a less scrupulous or less careful unattended run could legally satisfy the floor's letter every time with the same one-line text, defeating the gate's entire purpose for any fully autonomous session. Eval scenario 100 tests that a PASS or a one-line skip satisfies the floor and that a FAIL closes it; it does not test the bounded-vs-permanent distinction.

## Decision

Add one clarifying rule to the feel-verdict / experience-verdict skip-reason escape hatch at all three ADR-0085/0089/0091 closure homes (`commands/slice-closure.md`, the `implement-approved-slice.md` inline-close path, and the Feel-verdict checklist in `wos/godot-mobile-interaction-and-feel.md`): a skip reason stating no human is available in this environment, ever, does not by itself make a first-playable or feature-complete slice ready-to-close; it means the task stays open pending a human session. A skip reason that is a genuine, bounded deferral (a specific later checkpoint, a throwaway/no-runtime-surface slice, a real human who will review shortly) still satisfies the floor at its existing low ceremony. This narrows only the "no human, ever" case; every other documented use of the escape hatch is unchanged.

## Consequences

### Positive

- Closes the loophole where a fully autonomous, unsupervised session could permanently and legitimately bypass the one human-verification gate the Godot/experience cluster has, by writing the same one-line text forever.
- Keeps the cheap escape for its real intended cases (a genuine no-runtime-surface slice, a bounded deferral); no added ceremony there.

### Negative

- A fully unattended run can no longer reach a clean "ready to close" state on a first-playable/feature-complete claim; it correctly stalls at `not-ready-to-close` pending a human. This is the intended effect, not a side effect, but it does mean autonomous-track runs (ADR-0044/0081) touching a Godot or `user-facing-content` deliverable need a human touchpoint before closure, same as ADR-0085 already required for the runtime-gate, now also for the human-verdict gate.

### Neutral

- No new command; three existing closure homes gain one clarifying sentence each. No change to the PASS path or to any other skip-reason use.

## Alternatives considered

### Alternative 1: remove the skip-reason escape entirely for feel-verdict/experience-verdict

- Rejected: would re-add ceremony to the genuine no-runtime-surface case the escape exists to keep cheap (ADR-0089's own stated design goal).

### Alternative 2: amend ADR-0089/0091 in place

- Rejected: ADR immutability is a feature (CLAUDE.md); a refinement to an existing enforcement contract gets its own searchable record, the same reasoning ADR-0085 used when it enforced ADR-0084 rather than editing it.

### Alternative 3: a structured skip-reason taxonomy (bounded/permanent/other enum) instead of one clarifying sentence

- Considered; rejected as heavier than the finding warrants. One sentence closes the loophole the dogfood actually hit; a taxonomy is speculative scope beyond the evidence.

## References

- Task `projects/bmazurok__my-work-tasks/active/2026-07-11_godot-genre-dogfood-wave/`: `IMPACT_ANALYSIS.md` F-7, `DECISIONS.md` D-6.
- ADR-0089 (D-4 feel-verdict floor, the escape hatch this refines), ADR-0091 (the generalized experience-verdict floor, same escape shape), ADR-0085 (the runtime-gate floor this escape shape was mirrored from), ADR-0048 (evidence-over-trust).
- `commands/slice-closure.md`, `commands/implement-approved-slice.md` (the two closure-command homes), `wos/godot-mobile-interaction-and-feel.md` (the feel-verdict checklist).
- Eval scenario 100 (`evals/scenarios/100-godot-feel-verdict-gate.md`), untested for this distinction before this ADR; a follow-up scenario is a candidate, not done in this wave.

## Notes

Found by an autonomous, unattended dogfood session that judged its own literal-reading escape insufficient and self-corrected; this ADR makes that judgment call the documented rule instead of leaving it to be independently re-discovered (or, worse, not re-discovered) by the next unattended run.

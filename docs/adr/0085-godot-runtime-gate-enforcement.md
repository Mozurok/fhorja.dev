# ADR-0085: Enforce the Godot runtime-gate adoption rule at closure (three homes, signature-detected, block-and-route)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Tags**: godot-cluster, runtime-gate, closure-enforcement, slice-closure, task-close, implement-approved-slice, forcing-function, enforces-adr-0084

## Context

ADR-0084 (slice 04) added a rule to `godot-runtime-verify`: "a Godot slice with runtime-observable behavior runs the gate or records an explicit skip reason in the slice notes." The rule was stated as prose with no enforcement point. The pre-commit `review-hard` of that wave flagged it as a should-fix and it was deferred as net-new scope: nothing in `slice-closure`, `task-close`, or `implement-approved-slice` checks it, so a Godot slice can still close with a runtime-observable behavior neither runtime-verified nor explicitly skipped. That is the same failure class the ADR-0084 wave exists to close (a stated rule with no teeth), one level down.

A discovery pass over the closure surfaces surfaced the load-bearing fact: `slice-closure` is opt-in for LOW/MEDIUM slices. `implement-approved-slice` closes them inline via its slice-completion-check and explicitly does not route to `slice-closure`. Most Godot slices are LOW/MEDIUM, so a check placed only in `slice-closure` would miss the common case. The WOS already detects a Godot target by codebase signature (`test-strategy` routes on a `project.godot` file or `.gd` scripts), and the D-7 commit-evidence floor (ADR-0084) is a working precedent for a closure gate that blocks and routes.

## Decision

Enforce the ADR-0084 runtime-gate adoption rule as a forcing function at closure, reusing the D-7 commit-floor block-and-route idiom. Three locked decisions (D-1 to D-3 of task `2026-07-06_godot-runtime-gate-enforcement`):

1. **Detection by signature heuristic plus an explicit-skip escape (D-1).** WHILE the active task is a Godot task (detected by a `project.godot` or `.gd` codebase signature, the precedent `test-strategy` uses, or the presence of `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder) the closure check treats a slice as runtime-observable WHEN its declared scope touches a `.tscn` scene or a `.gd` script that runs. A slice with no runtime surface (a pure `.tres` data resource, a `project.godot` settings change, or docs) clears the check with a one-line explicit skip reason in the slice notes. A slice is "verified" when a `godot-runtime-verify` PASS is recorded (in `GODOT_RUNTIME_VERIFY.md` or cited in the slice notes); either the recorded PASS or the explicit skip line satisfies the check. The check reads recorded evidence; it never runs a scene.

2. **Three enforcement homes (D-2).** The check is enforced at `slice-closure` (a runtime-observable Godot slice is not `ready to close` without a recorded PASS or an explicit skip), the `implement-approved-slice` inline-close path (a LOW/MEDIUM runtime-observable Godot slice does not close inline without a recorded PASS or an explicit skip), and `task-close` (a Godot task does not archive while any runtime-observable slice is neither verified nor skipped). IF the check is unsatisfied THEN the command blocks closure and routes to `godot-runtime-verify`. The inline-close home is non-optional: skipping it reopens the LOW/MEDIUM bypass.

3. **A new ADR (this one), not a patch (D-3).** This records the cross-command enforcement mechanism; ADR-0084 remains the rule it enforces.

The check lives only in closing commands. It is deliberately NOT added to `where-we-at` or `what-next` (a checkpoint or routing command that does not close anything), and it does NOT touch the WOS `## Task lifecycle` done-conditions, because it is Godot-scoped rather than a general done-condition (unlike the D-7 commit floor, which did amend the lifecycle).

## Consequences

### Positive

- The ADR-0084 runtime-gate rule now has teeth: a runtime-observable Godot slice cannot close as done while the behavior was neither verified nor consciously skipped.
- The common case is covered: the inline-close path, where most LOW/MEDIUM Godot slices actually close, enforces the check.
- The escape is cheap: a genuine no-runtime-surface slice clears the check with one line, so the gate does not add ceremony to data or config slices.

### Negative

- Three core lifecycle commands (`slice-closure`, `task-close`, `implement-approved-slice`) used by every project gain a conditional check; an over-broad trigger would false-block non-Godot work. Mitigated by the two-part detection (Godot-task signature AND a runtime-surface slice scope) and the trivial skip escape.

### Neutral

- No new command and no WOS lifecycle change; the cluster stays at two commands (ADR-0069/0078) and the enforcement is Godot-scoped.
- "Verified" evidence reuses an already-produced artifact (a recorded `GODOT_RUNTIME_VERIFY` PASS); the check adds no new artifact type.

## Alternatives considered

### Alternative 1: enforce only at slice-closure and task-close

- Smaller surface, no `implement-approved-slice` edit.
- Rejected: `slice-closure` is opt-in for LOW/MEDIUM slices, which close inline via `implement-approved-slice`, so this reopens the exact bypass the enforcement exists to close.

### Alternative 2: a per-slice runtime-observable flag set at implementation-plan

- More precise detection (no heuristic).
- Considered as a complement (the flag can be the explicit-skip record), but rejected as the sole mechanism: it pushes work to plan time and grows the `implementation-plan` surface. The signature heuristic plus the skip escape achieves the same with no plan-time cost.

### Alternative 3: amend ADR-0084 in place

- Rejected: ADR immutability is a feature; a cross-command enforcement contract merits its own searchable record.

## References

- Task `projects/bmazurok__my-work-tasks/active/2026-07-06_godot-runtime-gate-enforcement/`: `IMPACT_ANALYSIS.md` (F1 the inline-close load-bearing finding, F3 the detection precedent), `DECISIONS.md` (D-1 to D-3, EARS).
- ADR-0084 (the runtime-gate adoption rule this enforces, and the D-7 commit-evidence-floor block-and-route precedent); ADR-0069 and ADR-0078 (the Godot cluster contracts); ADR-0028 (the task-close lifecycle command); ADR-0031 (EARS).
- `commands/godot-runtime-verify.md` (`## Per-slice adoption`, the rule); `commands/slice-closure.md`, `commands/task-close.md`, `commands/implement-approved-slice.md` (the enforcement homes); `commands/test-strategy.md` (the Godot-detection precedent).

## Notes

Found by the pre-commit review of the ADR-0084 wave and named there as a follow-up. The single most important design fact is F1: the inline-close path, not `slice-closure`, is where most Godot slices close, so an enforcement that skips it would ship the same toothless-rule failure it set out to fix.

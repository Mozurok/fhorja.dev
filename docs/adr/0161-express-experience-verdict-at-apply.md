# ADR-0161: Attended Express experience-verdict is the --apply stop

- **Status**: Accepted; the attester is the local commit `--apply` creates (ADR-0163), not a same-turn confirmation. The attester clause is superseded by [ADR-0179](./0179-the-experience-verdict-records-its-attester.md): the stand-down is removed and a commit the agent created never attests. Superseded in part by ADR-0203: the stand-down's premise was a human typing --apply.
- **Date**: 2026-08-27
- **Tags**: express, experience-verdict, adr-0091, adr-0159, branch-commit, human-gate, closure-floors

## Context

ADR-0091 requires a recorded human `## Experience verdict` PASS (or a bounded skip) before a `user-facing-content` slice closes. Machine-green evidence cannot substitute. The 1.2.0 Express bind (ADR-0159) put the remaining human stop at `branch-commit --apply`: display the diff, then confirm in the same turn.

On an attended Express FAQ-sized run, those two rules stacked. The slice could not inline-close without a verdict PASS, and the only human turn left was `--apply` after the slice. Closures recorded a skip reason to keep moving. That skip is decorative: it names no later checkpoint and is not the Godot stand-down. Silent skip is not a human attester.

Dogfood on 2026-08-27 (Claude, Codex, Kimi against the Express fixture) hit this on `user-facing-content`. Work that is not Express, and the Godot feel-verdict path, were not the failure.

Separately, `--apply` condition 3 already requires `git diff --staged` in the display. Two of three CLIs stopped with an unstaged working-tree diff. Scenario 125 forbids treating a name list as content; it did not yet name the stop-without-confirm index state.

## Decision

WHILE the pipeline is attended Express (`TASK_STATE.md ## Recommended pipeline` names Express AND the task-init unattended bullet did not fire), the ADR-0091 experience-verdict floor stands down in favor of the local commit `branch-commit --apply` creates. That commit is the attester for `user-facing-content` on that path (ADR-0163). A separate `## Experience verdict` PASS before `--apply` is not required. A decorative skip reason is not this stand-down.

A task that is not Express still requires the verdict or a bounded skip. The Godot stand-down (ADR-0091 (d), ADR-0089 D-4) still wins when that signature is present.

Incomplete `--apply` display is a refuse (HEAD unchanged). A working-tree-only display is invalid output. Scenario 125 is display-then-commit (ADR-0163): Agent-only, explicit pathspec, no second confirmation.

Enforced in `wos/closure-floors.md` (all three consumer variants), the generated views, `commands/task-close.md` (one-line echo), `commands/branch-commit.md` condition 4 (ADR-0163), and `evals/scenarios/125-branch-commit-apply-authorization.md`.

## Consequences

### Positive

- Attended Express has one human stop, the irreversible one, instead of a verdict PASS plus `--apply`.
- The floor still fires on Standard, Strict, and any path that is not attended Express.

### Negative

- A misclassified Express task that is actually a user-facing product surface will skip the dedicated verdict sample. Mitigated by the ADR-0025 conservative default (when uncertain, Standard) and by merge staying human.

### Neutral

- `## Experience verdict` remains valid on Express if a human records one; it is not required.

## Alternatives considered

### Alternative 1: keep the floor and treat skip as success

- Leave 0091 as-is; Express always writes `skipped: pending --apply`.
- Rejected: that is the decorative skip the 1.2.0 dogfood produced. The attester is absent.

### Alternative 2: require the verdict after `--apply`

- Close the slice only once a PASS block exists, even on Express.
- Rejected: that is a second human gate on the cheap path. ADR-0159 already named `--apply` as the remaining stop.

### Alternative 3: allow unstaged display at `--apply`

- Accept `git diff` working-tree as the stop display.
- Rejected: scenario 125 and `--apply` condition 3 require `git diff --staged`. Naming the index state keeps that contract.

## References

- [ADR-0091](./0091-experience-gates-generalized.md): experience-verdict floor; this ADR supersedes only the attester on attended Express.
- [ADR-0159](./0159-express-binds-by-default.md): Express bind; remaining stop is `--apply`.
- [ADR-0098](./0098-feel-experience-verdict-bounded-vs-permanent-skip.md): bounded skip still applies off the Express stand-down.
- `evals/scenarios/125-branch-commit-apply-authorization.md`, `evals/scenarios/137-express-one-human-stop.md`.

## Notes

Unattended Express does not take this stand-down. That path does not route to `--apply` (ADR-0159).

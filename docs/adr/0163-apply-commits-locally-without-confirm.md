# ADR-0163: Attended --apply creates the local commit after the display

- **Status**: Accepted. Superseded on the pathspec sentence by [ADR-0167](./0167-bare-commit-tree-proof-and-default-branch-refusal.md); the display-then-commit contract stands. Superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: the push and the draft PR no longer wait for a person's confirmation; merge, force-push and MCP egress keep theirs.
- **Date**: 2026-08-28
- **Tags**: branch-commit, apply-mode, human-gate, adr-0159, adr-0161, irreversible-act

## Context

ADR-0159 bound attended Express and named `branch-commit --apply` as the remaining human stop: display the staged diff, then wait for a same-turn confirmation. ADR-0161 made that stop the experience-verdict attester on Express. Scenario 125 treated a commit in the same reply as the display as a FAIL (the receipt pattern).

The confirmation was copied from the egress rule (payload plus destination, then confirm). A local git commit is not that class of act. It is reversible (`git reset`, reflog). The working tree is still there. Push, merge, and force-push are the irreversible outward acts, and they already have their own rules.

Waiting for "sim" after a shown local diff sat the human on a reversible step.

## Decision

On an attended Agent `--apply` run, after condition 3's display (commit message, `git status --porcelain`, `git diff --staged --stat` plus `git diff --staged`), the command SHALL create the commit in the same turn. It SHALL NOT wait for a second human confirmation. The `--apply` invocation, plus an Agent attended run, plus a complete display, is enough.

Push, merge, force-push, and MCP egress stay behind their existing confirmation rules.

Unattended, background, and fleet runs still refuse `--apply`. Ask, Plan, and Debug still refuse. Explicit pathspec, no `git add -A`, and prove-what-moved stay.

Incomplete display (missing message, porcelain, or `git diff --staged`) is a refuse: HEAD unchanged, no commit. Stop-without-confirm as a waiting state is retired.

On attended Express, the ADR-0161 stand-down remains: the attester is the local commit `--apply` creates, not a same-turn "sim".

Scenario 125 is rewritten: display then commit. The old bait sentence ("Go ahead and commit it when you're done") is not a refuse. Unattended `--apply` remains a refuse.

## Consequences

### Positive

- Attended Express reaches a local commit without a paste-relay "sim".
- Human attention stays on push and merge, which leave the machine.

### Negative

- A wrong local commit can land before the user reads the display in the same reply. Mitigated by the display still being mandatory before HEAD moves, by explicit pathspec, and by `git reset` remaining the undo.

### Neutral

- Unattended still cannot `--apply`. An external execution layer retains the driver-owned-branch and `ref-attested` routes. Direct-use `autonomous-run` has neither and records the bounded deferral under ADR-0197.

## Alternatives considered

### Alternative 1: keep confirmation, drop it only on Express

- Standard `--apply` still waits; Express does not.
- Rejected: the reversibility argument does not depend on Express. A local commit is local on every attended path.

### Alternative 2: skip the display

- Commit without printing the staged diff.
- Rejected: the display is what makes a later `git reset` informed. Condition 3 stays.

## References

- [ADR-0159](./0159-express-binds-by-default.md): Express bind; remaining human stops become merge and push.
- [ADR-0161](./0161-express-experience-verdict-at-apply.md): Express experience-verdict stand-down; attester becomes the local commit.
- [ADR-0100](./0100-commit-evidence-floor-bounded-deferral.md): unattended still cannot `--apply`.
- `evals/scenarios/125-branch-commit-apply-authorization.md`.

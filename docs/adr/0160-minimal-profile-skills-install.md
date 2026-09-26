# ADR-0160: Minimal profile skills install is unblocked

- **Status**: Accepted; the 14-command figure is superseded by [ADR-0178](./0178-where-we-at-and-test-strategy-join-the-spine.md); the spine is 16.
- **Date**: 2026-08-27
- **Tags**: install, x-wos-profiles, adr-0059, skills, minimal, branch-commit

## Context

ADR-0059 added `--profile=minimal|core|full` so a newcomer could install the lifecycle spine instead of all 98 commands. A later installer gate, documented as D-4 in `scripts/sync-workflow-slash-commands.sh`, refused `--profile=minimal --with-skills`. The stated reason was `check_tier_routing_closure()` reporting one open break: `task-init` is `[minimal, core, full]` and its Express chain routed to `branch-commit`, then listed only as `[core, full]`.

On disk that break is already gone. `branch-commit` is `[minimal, core, full]`. `tier-routing-closure` passed in the 1.2.0 tree. The refuse still exited 1, so the 14-command spine could not be installed as skills even though every one of those commands already declares `minimal`. Help and the end-of-run summary still said "12 everyday commands". README already counted 14.

## Decision

`--profile=minimal` with skills enabled installs the 14-command spine as skills and exits 0. The installer no longer refuses that combination. Help, wizard copy, and the end-of-run summary name 14 commands, not 12. Omitting `--profile` still mirrors every skill, unchanged. `--no-skills` still installs commands without skills.

Enforced in `scripts/sync-workflow-slash-commands.sh` (the refuse function is gone) and `scripts/tests/test-install-payload.sh` (a skills-on `--profile=minimal` run asserts 14 skills and 14 commands in a HOME sandbox). `tier-routing-closure` remains a hard structural-eval; this ADR does not weaken it.

## Consequences

### Positive

- A newcomer can install the everyday loop the way the model actually loads it (skills), not only as slash-command markdown.
- Help matches the live `x-wos-profiles` count.

### Negative

- A future routing break that puts a minimal command's next step outside the minimal set would ship as an incomplete skill install until `tier-routing-closure` fails CI. That is the same fail-closed the refuse claimed to provide, now at the gate that actually measures it.

### Neutral

- Command-only `--no-skills` payload checks are unchanged.

## Alternatives considered

### Alternative 1: keep the refuse until a new lint rule

- Leave the stale D-4 message in the installer.
- Rejected: the message names a break that is not on disk. A refuse that cannot fire for a real reason is a lying default.

### Alternative 2: silently install core skills when minimal is asked

- Downgrade instead of refusing.
- Rejected: ADR-0059 already refused silent downgrade. Install what was asked, or fail a real gate.

## References

- [ADR-0059](./0059-tiered-install-profiles.md): profiles; this ADR supersedes only the later installer refuse of minimal skills.
- `commands/branch-commit.md` frontmatter `x-wos-profiles: [minimal, core, full]`.
- `evals/scripts/structural-evals.py` `check_tier_routing_closure`.

## Notes

The 14 are: `task-init`, `impact-analysis`, `decision-interview`, `implementation-plan`, `approve-plan`, `implement-approved-slice`, `slice-closure`, `review-hard`, `pr-package`, `what-next`, `sync-task-state`, `task-close`, plus `branch-commit` and `implement-slice-complement`.

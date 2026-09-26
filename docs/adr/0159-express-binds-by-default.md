# ADR-0159: Express binds for attended editor runs

- **Status**: Accepted; a declared `Operating mode: strict` defers the inline Approval log (ADR-0162). Attended `--apply` creates the local commit after the display; merge and push stay human (ADR-0163). The Ask-mode handoff target is superseded by [ADR-0190](./0190-the-ask-path-routes-to-the-write.md): on Ask it is `approve-proposed`, because the five files are not on disk yet. The Express bind, the Agent-mode target and the unattended carve-out stand. The push sentence is superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: the chain pushes the task branch and opens the draft PR itself; merge stays human.
- **Date**: 2026-08-27
- **Tags**: express, complexity-routing, approve-plan, attended, adr-0025, human-gate

## Context

ADR-0025 added a complexity assessment at `task-init` and four pipeline tiers, including Express. The assessment was a recommendation: the user still had to pick the next command, and `implementation-plan` always handed off to `approve-plan` before any slice ran. On small, fully specified work that produced a paste-relay: extra human stops sat on reasoning, not on irreversible action.

The Express criteria (scope in one sentence, all decisions given, fewer than 5 files) were already machine-checkable in the prompt. What was missing was a bind: when those criteria hold and a human is in the editor, the short path should run until the commit diff.

ADR-0044 D9 (skip list of the additive autonomy cluster) does not forbid ADR-0025 complexity assessment. D9 constrains unattended autonomy. This ADR does not recut D9 and does not edit ADR-0044.

## Decision

When an attended editor run meets the Express criteria of ADR-0025 (one sentence, decisions given, fewer than 5 files) AND the run is not unattended, background, or fleet-dispatched, Express binds: `implementation-plan` copies the full `approve-plan` consistency gate, writes `## Approval log`, sets `plan APPROVED` inside existing `## Current phase`, and hands off to `implement-approved-slice`. Ask-mode `task-init` stays five-file PROPOSED (ADR-0001). `--apply` creates the local commit after the staged diff is shown (ADR-0163). Merge and push stay human. Unattended runs keep `approve-plan` and `ref-attested`. Conservative classification stays: when uncertain, Standard.

Enforced in `commands/task-init.md` (attended bind and Agent handoff), `commands/implementation-plan.md` (inline gate plus Approval log), `commands/implement-approved-slice.md` (twin-signal check and last-slice handoff to `branch-commit --apply`), `wos/substrate-peers.md` (`implementation-plan` is an append-only Express co-writer of `## Approval log`; owner remains `approve-plan`), and eval scenarios 61 variant F and 137. Scenario 125 is the display-then-commit contract for `--apply` (ADR-0163).

## Consequences

### Positive

- Attended Express work reaches the commit diff without a separate `approve-plan` invocation.
- The consistency gate is not dropped; it moves to the plan command on that path.
- Unattended, Standard, Disciplined, and Strict behavior is unchanged.

### Negative

- Misclassified Express work can skip `decision-interview`. Mitigated by the ADR-0025 conservative default (when uncertain, Standard).
- `implementation-plan` in Agent on Express is a write of the lock. Plan-mode still proposes.

### Neutral

- `approve-plan` remains for every non-Express path and remains owner of `## Approval log`.
- Handoff shape is unchanged (Run now, Mode, Work complexity, Reason).

## Alternatives considered

### Alternative 1: patch ADR-0025 in place

- Rewrite the recommendation sentence in ADR-0025.
- Rejected: ADRs are immutable in spirit. Bind is a successor default, not a secret edit of the 2026-05-26 decision.

### Alternative 2: recut ADR-0044 D9 so the model may pick autonomy tiers

- Treat Express bind as a D9 carve-out.
- Rejected: D9 is the skip list of the additive autonomy cluster. Express is ADR-0025 complexity routing on an attended editor run. Editing 0044 invites a yolo reading.

### Alternative 3: APPLIED task-init in Ask on Express

- Persist the five files in Ask so the chain can continue without `approve-proposed`.
- Rejected: breaks ADR-0001 and scenarios 01, 02, 08, 15, 26.

## References

- [ADR-0025](./0025-complexity-routing.md): complexity tiers; this ADR supersedes only the "recommendation, user must opt in" default for attended Express.
- [ADR-0001](./0001-proposed-by-default.md): Ask remains PROPOSED.
- [ADR-0044](./0044-autonomous-delivery-track.md): D9 untouched.
- `commands/approve-plan.md`: the consistency gate this path copies.
- `evals/scenarios/137-express-one-human-stop.md`, `evals/scenarios/61-approve-plan-consistency-gate.md` variant F, `evals/scenarios/125-branch-commit-apply-authorization.md`.

## Notes

Attended means a human is in the editor this session: the `task-init` unattended / background / fleet bullet did not fire. Tier classification alone is not authorization. ADR-0197 later scopes the Decision section's `ref-attested` route to an external execution layer; direct-use `autonomous-run` records bounded deferral when it has no commit evidence.

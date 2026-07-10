# ADR-0081: Background mode for autonomous-run: detachment without touching the gates

- **Status**: Accepted
- **Date**: 2026-07-04
- **Tags**: autonomy, background-run, runs-feed-producer, detachment, allowlist-only, measurement-only-notification, additive

## Context

The autonomous delivery track (ADR-0044) runs an approved waved plan with two human gates, a runtime governor, and a boundary/test classifier, but only inside the maintainer's interactive terminal session: the session is occupied while the run executes. The market-parity initiative named a background mode as deliverable 5, and two sibling deliveries created its substrate: the runs-feed v1 contract with its board renderers (ADR-0080, this task is the PRODUCER side) and per-task worktree isolation (ADR-0074).

The safety question that shaped everything: the ADR-0044 D9 skip list forbids permissive headless modes by name (acceptEdits, bypassPermissions, skip-permissions, yolo), and a detached session cannot answer interactive permission prompts. Any background design either respects D9 or silently becomes the thing the track exists to prevent.

## Decision

A thin detachment layer over the UNCHANGED autonomous-run contract, locked as D-1..D-4 of task `2026-07-03_background-autonomous-run`:

1. **Allowlist-only permissions with stall-to-escalation (D-1).** The detached session runs under the repository's pre-approved permission allowlists only; no permissive flag exists that the mode accepts, in code, configuration, or documentation. A permission prompt that would block the session stalls the run until the governor's wall-clock timeout forces a clean stop at a slice boundary, recorded in the runs feed as state=escalated with the stall named. A missing permission becomes an escalation, never a bypass.
2. **Configured launch with a manual fallback (D-2).** `scripts/autonomy/launch-background-run.sh` reads the agent-CLI invocation from `WOS_AGENT_CMD` (capability-routed; normative text names no vendor) and prints the manual detached-launch steps when unset, exiting cleanly.
3. **Layered notification, nothing hosted (D-3).** The canonical channel is the runs feed plus the boards plus the contract-mandated TASK_STATE.md writes; `scripts/autonomy/notify.sh` adds best-effort desktop notifications presence-gated on terminal-notifier or osascript, silently no-oping otherwise.
4. **One run at a time, and detachment is not durable resume (D-4).** The launcher refuses while any feed file has a heartbeat fresher than the staleness threshold (15 minutes, the `STALE_MINUTES` default in `runs-feed.sh`; a staler heartbeat reads as dead, not running). The autonomous-run do-not-use text now distinguishes a detached single continuous session (in scope) from cross-session durable resume, restart and re-attach (still out of scope, the ADR-0044 known open risk unchanged).

Producer lifecycle (the ADR-0080 counterpart): `runs-feed.sh start` on entry; `update` with a fresh heartbeat and the current slice between slices, alongside the existing governor calls; `update --state escalated` plus the notifier on ANY halt or escalation; `end` on clean exit, because a terminal outcome belongs in the outcome ledger (ADR-0079), never in the feed. The STOP sentinel path is absolute in the main repository (a worktree-internal path would be agent-writable). Worktree layering: the run occupies the task's ADR-0074 worktree; `implement-fleet` slice worktrees branch off the task branch; two runs never share a worktree because two runs never coexist.

## Consequences

### Positive

- The maintainer's terminal is free while an approved plan executes, with the same gates, governor, classifier, and PROPOSED-only diffs as the foreground mode; escalation semantics are unchanged by detachment (an escalation halts; nothing auto-advances because nobody is watching).
- The D9 posture is preserved by construction: the safe headless model is standing allowlists plus stall-to-escalation, not permission bypass.
- Progress is visible on the boards the initiative already shipped, through the one feed contract both sides now implement.

### Negative

- A missing allowlist entry turns into a governor-timeout escalation instead of a quick interactive prompt; background runs pay latency for safety.
- Zombie processes that die without removing their feed file leave a stale row until the staleness threshold reads them as dead; the heartbeat is the mitigation, not process supervision.
- The launcher's `## Workspace` extraction is best-effort text parsing until a real task-workspace example exists to pin the format.

### Neutral

- The first real background run is deliberately post-merge dogfood on a task the maintainer picks; the pre-merge validation used a mock CLI to prove the mechanics without burning a plan.
- Concurrency stays a v1 boundary; the feed format supports N files, so lifting it later is additive.

## Alternatives considered

### Alternative 1: a permissive-flag or dedicated-permission-profile headless mode

- Fewer stalls, more convenience.
- Rejected: the D9 skip list forbids the flags by name, and a widened standing profile grows the permanent permission surface; the stall-to-escalation model keeps the posture unchanged.

### Alternative 2: a bespoke daemon controller outside an agent session

- Full control of the loop.
- Rejected: duplicates the controller and moves safety logic into new code; the thin layer keeps the contract in one place.

### Alternative 3: no detachment (feed plus notifications on the interactive run only)

- Zero launch mechanics.
- Rejected as the primary (it narrows the named deliverable "via headless CLI"); recorded as the explicit fallback had D-1 proven unsafe, which it did not.

## References

- `scripts/autonomy/runs-feed.sh` (producer lifecycle, `STALE_MINUTES` 15), `scripts/autonomy/notify.sh`, `scripts/autonomy/launch-background-run.sh`.
- `commands/autonomous-run.md` (the background-mode section; D6/D9 sentences verified byte-identical through the edit), `commands/autonomous-board.md` (the feed read source), `wos/autonomous-track.md` (the protocol).
- D-1..D-4 of `projects/bmazurok__my-work-tasks/active/2026-07-03_background-autonomous-run/DECISIONS.md` (locked 2026-07-04).
- ADR-0044 (the track and its D9 skip list), ADR-0074 (worktrees), ADR-0079 (the outcome ledger), ADR-0080 (the runs-feed contract this mode produces).
- `evals/scenarios/92-background-autonomous-run.md` (the regression scenario).

## Notes

Built as the third delivery of the market-parity initiative, consuming both prior deliveries as interfaces (the ledger for outcomes, the feed contract for progress). The safety slice (the command-contract edit) was executed sequentially in the main session with the D6 and D9 sentences pinned byte-identical by SHA comparison before and after, per the plan's STOP conditions.

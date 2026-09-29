# ADR-0237: A background session a person launched on a task branch is the attended flow

- **Status**: Accepted. The test rests on provisional P-1 to P-5 of its task (P-2, the five conditions, is `Impact: high`), listed in the draft PR for the maintainer to confirm. Confirmed by the maintainer on 2026-09-28: each of those provisional decisions now has a locked D-N carrying `Confirms:` in the task's DECISIONS.md.
- **Date**: 2026-09-28
- **Supersedes**: in part, [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) and [ADR-0159](./0159-express-binds-by-default.md), only where each puts every background run on the unattended side. A background session that passes the test below is attended. The rest of each stands.
- **Respects**: ADR-0044 D6 and D9, ADR-0221 and ADR-0197 (the unattended track and its human merge gate), ADR-0200 (the bounded-audience test), ADR-0235 (the provisional-decision lifecycle), ADR-0166 (supersession marking).
- **Tags**: attended, unattended, background-session, provisional-decisions, draft-pr, decision-interview, branch-commit, pr-package, task-init, adr-0233, adr-0159, adr-0044

## Context

- ADR-0233 made an attended chain on a task branch run from `task-init` to a draft PR. A decision the request leaves open becomes a provisional `### P-N`, and the person's gates are the draft PR (ready for review, merge) and the explicit confirmation of each P-N. Its "What does not change" paragraph kept "Unattended, background and fleet-dispatched runs" on their old rules.
- ADR-0159 defined attended as "a human is in the editor this session", which it tied to the `task-init` bullet for unattended, background or fleet runs not firing.
- The same three-item list was copied into about twenty surfaces: `decision-interview`, `task-init`, `targeted-questions`, `problem-framing`, `project-bootstrap`, `im-stuck`, `resolve-contract-gaps`, `contract-signoff`, `direction-adjust`, `approve-plan`, `implement-approved-slice`, the `--apply` refusals of `branch-commit` and `pr-package`, three wos topics, the spec, and the FAQ. Wherever it appears, "background" sits on the unattended side.
- On 2026-09-28 the maintainer said the list is wrong for his own sessions: "hoje o nosso fluxo atual não para em mais nada" (D-3 of the parallel-work research task). Since ADR-0233 the attended chain does not wait for answers, so whether a person is watching mid-run changes nothing. What matters is that a person started the session and reads the draft PR before anything is merged. The research measured it on archived one-slice tasks: in the 7 tasks started on or after 2026-09-24, 0 of 140 gaps between writes lasted over an hour, against 8.9 percent of 237 gaps in the 15 tasks before.
- Under the old list, a background Claude Code session the maintainer launches on a task branch stalls at `decision-interview` with PROPOSED blocks, and `branch-commit --apply` and `pr-package --apply` refuse it. It never reaches the draft PR the maintainer would read.
- The word "background" also names a different thing: the detached `autonomous-run` that `scripts/autonomy/launch-background-run.sh` starts (`wos/autonomous-track.md ## Background runs`). That run is on the autonomous track, and ADR-0044 keeps it unattended whoever starts it.

## Decision

A background session counts as the attended flow only while all five conditions below hold, and it states that it holds them in its own transcript. When any one fails, the session is unattended and keeps the ADR-0044 doctrine exactly as written: open questions become PROPOSED with a candidate default, no decision is self-locked, no P-N is written, and neither `--apply` runs.

1. A person launched it for this task, either by starting it themselves or by sending it from their own attended session with a brief that names the task. A cron job, a CI job, a scheduler, a hook, or a loop that relaunches itself is not a person.
2. It is not an `autonomous-run` session (including one started by `scripts/autonomy/launch-background-run.sh`), and it is not a worker under a fleet command's worker contract.
3. It runs on the task branch: `git branch --show-current` equals the `Task branch:` line in `TASK_STATE.md ## Resume notes`, or `task-init` creates that branch in this run. A remote is configured, and no `Operating mode: assisted` is declared.
4. Its outward acts stop at a draft pull request that `pr-package --apply` opens from that task branch. It never marks the pull request ready for review, merges, pushes to the base branch, or force-pushes.
5. Its provisional decisions stay provisional. It never writes the `Confirms:` or `Supersedes:` D-N that promotes one; only the maintainer does.

The test is written once, in `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`. Every other surface drops "background" from the old list and cites the test (provisional P-1). Attendance belongs to the session, not the task: the session states its classification in one `### Command transcript` line and writes nothing about it to `TASK_STATE.md`, so a later session on the same task that no person launched cannot inherit it (P-3). A launched background session that cannot meet condition 3 (no git, no remote, a declared assisted mode, or a command such as `problem-framing` that runs before any task branch exists) follows the unattended rule. A foreground session in that spot asks the person, who is there to answer; a background one has nobody to ask until its run ends (P-4).

Scenario 146 and the structural check `check_background_session_test` pin the distinction (P-5).

## Consequences

### Positive

- A background session the maintainer launches runs the same chain he gets in the foreground, up to the draft PR, with every choice it made listed under "Decisions made without you".
- Several tasks can run at once, each in its own background session and worktree (D-7 and D-8 of the same research), without one of them stalling on a question nobody sees.
- The unattended track loses nothing. Scheduled and headless runs, `autonomous-run`, and fleet workers keep every refusal they had, and the test fails closed: a condition the session cannot show is a condition that failed.

### Negative

- More sessions now push a branch and open a draft PR on the shared host. That audience is still bounded (ADR-0200), and ready for review and merge stay the maintainer's, but the draft PR queue fills faster and each draft has to be read.
- Condition 1 rests on the launch context the session can see, mainly its brief. A brief that falsely claims a person launched the session would pass. The condition names who launched the session, which the brief records, but no script can check it.
- The ADR-0233 bet that a list of decisions read at the draft PR catches what a plan read would have caught now covers background sessions too, and they have no person watching mid-run. The bet is still unmeasured.

### Neutral

- ADR-0233's and ADR-0159's Decision text is unchanged. Their Status lines name this ADR, and the surfaces that hold the rule carry the new wording.
- `Operating mode: assisted` in a background session means the unattended rule, through condition 3. A person who wants to be asked should run the session in the foreground.

## Alternatives considered

### Alternative 1: rename "background" to "headless" in every list

- It would be a one-word change per surface.
- Rejected: `claude -p` headless mode is also how a person launches a session by hand, so the new word would split the same way the old one did.

### Alternative 2: record the classification in `TASK_STATE.md ## Resume notes`

- A `Launched by:` line would let later commands read the classification from the task instead of the session.
- Rejected: attendance is a property of one session. A cron job that resumes the task tomorrow would read yesterday's line and push as if a person had launched it.

### Alternative 3: treat every background session as attended

- It would be the shortest rule.
- Rejected: `autonomous-run` detached runs and fleet workers are background sessions too, and ADR-0044 keeps them away from commits and pushes for reasons this ADR does not revisit.

## References

- `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`: the test.
- `commands/decision-interview.md`, `commands/task-init.md`, `commands/branch-commit.md`, `commands/pr-package.md` and the other surfaces listed under Context.
- `WORKFLOW_OPERATING_SYSTEM.md ### Adaptive handoff`.
- `evals/scenarios/146-launched-background-session-runs-the-attended-chain.md` and `check_background_session_test` in `evals/scripts/structural-evals.py`.
- ADR-0233, ADR-0159, ADR-0044, ADR-0221, ADR-0197, ADR-0200, ADR-0235.

## Notes

What would reopen this: a draft PR opened by a background session that no person launched, or a P-N from a background session merged without the maintainer reading it.

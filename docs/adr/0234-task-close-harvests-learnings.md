# ADR-0234: task-close harvests learnings when the task left a signal

- **Status**: Accepted. The trigger rule is provisional P-2 of its task, listed in the draft PR for the maintainer to confirm.
- **Date**: 2026-09-24
- **Tags**: learnings, task-close, harvest-session-learnings, rank-learnings, closure, adr-0017, adr-0064, adr-0071

## Context

- `task-init` reads prior lessons through `scripts/rank-learnings.sh`, which walks every `LEARNINGS.md` under the project, `active/` and `archive/` alike (ADR-0017, ADR-0071). That consume path only works when closing tasks write to it.
- The produce side was left to judgment. `task-close` item 8 wrote an entry only when the agent judged there had been a failed attempt or a surprise, and `harvest-session-learnings` (ADR-0064) ran only when someone asked for it. No command invoked it.
- On 2026-09-24 five tasks closed and none wrote `LEARNINGS.md`. The knowledge notes written at the same closes live in `knowledge/`, which no command reads by design (ADR-0054, ADR-0055). The maintainer asked whether learnings were harvested by default at the end of a task. They were not. A manual harvest afterward found nine durable lessons, all in the three tasks that had recorded a signal: review rounds that asked for a revision, fix rounds after a review, and a PR call that failed. The two routine closes yielded none.

## Decision

`task-close` runs a learnings pass before its archive move. WHEN the task recorded a signal (a `needs_revision` or `ESCALATED` line in the Approval log, a check shown failing before it passed, a review finding that was fixed, a refusal or a stop, a revert or reopen, a de-scope, or an `unverified:` line), it applies the `harvest-session-learnings` contract to the task and appends the entries that meet that command's bar to the task's `LEARNINGS.md`. The pass may return NO_OP. It never edits an existing entry and never writes `USER_MEMORY.md`; a cross-project lesson is listed as a pointer for the person to promote. WHEN no signal is recorded, it writes one transcript line, `Learnings: none harvested (no signal recorded)`. The rule lives in `commands/task-close.md`, Required output item 8.

## Consequences

### Positive

- A task that struggled leaves its lessons where the next `task-init` reads them, without anyone remembering to ask.
- A routine close stays cheap and says in one line why nothing was harvested, so a skipped harvest is visible rather than silent.

### Negative

- A task whose lesson left no recorded signal is not harvested. The person can still run `harvest-session-learnings` by hand.
- Closes with a signal pay for a harvest read, on the session when it is still in context and otherwise on the task's artifacts.

### Neutral

- `slice-closure`'s inline learnings, `harvest-session-learnings` itself and `rank-learnings.sh` are unchanged; the produce side now writes where the consume side already read.

## Alternatives considered

### Alternative 1: harvest on every close

- Run the pass unconditionally.
- Rejected: on 2026-09-24 the two closes with no signal (PR #2 and PR #4) had nothing to learn, and paying a session-wide read to get a NO_OP on every close is the ceremony ADR-0017 kept the section optional to avoid. This narrows the maintainer's "by default when a task finishes", so the trigger was recorded as a provisional decision with Impact: high for the maintainer to confirm.

### Alternative 2: keep item 8 optional and judged

- Leave the entry to the agent's judgment at close.
- Rejected: five closes on one day wrote nothing while nine lessons existed, so judgment at close did not produce the entries.

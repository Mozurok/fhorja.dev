# ADR-0239: The one-slice route admits normal-impact provisional decisions

- **Status**: Accepted. The mechanism rests on provisional decisions of the 2026-09-28 one-slice-admits-provisional task (P-1 to P-5 and P-7, which replaced P-6), listed under `## Notes`, which await the maintainer's confirmation. Confirmed by the maintainer on 2026-09-28: each of those provisional decisions now has a locked D-N carrying `Confirms:` in the task's DECISIONS.md.
- **Date**: 2026-09-28
- **Supersedes**: in part, [ADR-0225](./0225-a-one-slice-change-is-checked-by-a-script-not-a-plan-review.md), its condition (3) only: the brief no longer has to carry every decision, and an open decision recorded as an `Impact: normal` provisional `P-N` keeps the route. In part, [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md), its P-7 only: a normal-impact `P-N` no longer sends the task through `implementation-plan` and `approve-plan`. The rest of both stands.
- **Tags**: task-init, one-slice-route, provisional-decisions, check-plan-coverage, draft-pr, ceremony, e1, adr-0225, adr-0233

## Context

ADR-0225 let a one-sentence change to at most two named files skip `implementation-plan` and
`approve-plan` when the brief carried every decision. ADR-0233 then made every decision an attended
run lacks into a provisional `### P-N` that the chain records and continues past, and that
`pr-package` lists at the top of the draft PR under "Decisions made without you" for the
maintainer to confirm. Its P-7 kept the route closed to any `P-N`: "the one-slice route stays for a
brief that carries every decision". So an open decision was reviewed twice, once by the blinded plan
review and again by the person at the draft PR, and the second read is the one that can change it.

Experiment E1 of the parallel-work research measured what that costs, from each session's final
cost-state checkpoint on 2026-09-28:

- Arm 1, a multi-paragraph FAQ change that took the one-slice route: 40,479 Opus output tokens.
- Arm 2, a one-line template change: 68,986 Opus output tokens, with `implementation-plan`,
  `approve-plan`'s blinded review and a Layer-2 review. It took the full path for one reason, which
  its task state recorded as "Route: full path, not one-slice. Condition 3 fails": `### Assumptions`
  held a phrasing choice (which file name the Cursor line should give).

The smaller change cost 70 percent more because of the path, not the work. E1's own reading was
that the fixed cost of the full chain dominates small tasks, which points at ceremony (front c of
the research) more than at model routing. Both of arm 2's provisional decisions were `Impact:
normal`, and both reached the maintainer in the draft PR, where he merged it.

## Decision

The one-slice route's condition (3) reads: `DECISIONS.md ## Locked decisions` stays empty, and each
decision the brief lacks is an `Impact: normal` choice on a run whose `TASK_STATE.md` carries a
`Task branch:` line. `task-init` writes each one, in the same batch as the slice, as a `### P-N`
under `## Provisional decisions` with its `Evidence:`, `Impact: normal` and `Status: provisional`
lines, and the route's slice cites each as `Decision-ref: rests on provisional P-N`. Such a
decision is not the `decision-interview` disqualifier: that command would only write the same
entry. The draft PR lists it, as it lists every `P-N`.

The full path stays for everything else: an `Impact: high` decision (data, security, payments or
cost), a missing or unreadable impact, a locked `D-N` the brief does not carry, a run with no task
branch and so no draft PR, and any other condition ADR-0225 set. A condition that cannot be shown
has still failed.

`scripts/check-plan-coverage.sh` rule 5 checks what can be read off the files. Under the route it
refuses a `P-N` whose impact is not `normal`, a `P-N` the slice does not cite (an entry a later
`P-N` replaces is exempt), and any `P-N` when `TASK_STATE.md` has no `Task branch:` line. It keeps
refusing a locked decision, a second slice, a third path and the other slice fields.
`commands/what-next.md` re-checks the same conditions and ends the route when one fails.

Revert condition: route tasks whose normal-impact `P-N` the maintainer replaces at the draft PR
more often than full-path tasks' `P-N`, or a high-impact choice found labeled `normal` on a route
task.

## Consequences

### Positive

- A small change whose only open point is a wording or naming choice takes the route. On E1's
  numbers that is the difference between about 40k and 69k Opus output tokens for a one-line
  change.
- The decision is still announced twice, in `task-init`'s assumption list and in the draft PR,
  which is the condition ADR-0207 set for a behavior with no name.
- The check stays mechanical. The impact, the citation and the task branch are read by rule 5, not
  by a model reading prose.

### Negative

- A normal-impact decision on the route is no longer read by the blinded plan review before the
  code is written. The review's evidence question (does the cited line exist and support the
  choice) is not asked on this route; the maintainer reads the evidence at the draft PR instead.
- The impact label is the agent's judgment. A high-impact choice labeled `normal` now skips a
  review it used to get. The draft PR still lists it, and the revert condition names this case.
- `task-init` becomes a co-writer of `DECISIONS.md ## Provisional decisions`.
- The generated `task-init` skill had 196 chars of headroom under the 36,000-char Load ceiling;
  the new condition text was paid for by tightening wording in the same file.

### Neutral

- A decision that arrives from the maintainer mid-chain becomes a locked `D-N`, which ends the
  route as before.
- Without a remote there is no task branch, so a brief with an open decision keeps the full path,
  exactly as before this ADR.
- Scenario 144 grades the route with briefs that carry every decision; the admission and its
  refusals are graded by `scripts/tests/test-check-plan-coverage.sh`.

## Alternatives considered

### Alternative 1: route through `decision-interview` before implementing

- The route would add one command that writes the `P-N`, and keep that section single-writer.
- Rejected: it puts back part of the cost the route exists to cut, to write an entry `task-init`
  already has in hand as its `### Assumptions` list.

### Alternative 2: admit every provisional decision, high impact included

- One rule, no impact label to read.
- Rejected: ADR-0233 lists high-impact decisions first and marks them for confirmation before
  merge because a wrong one is expensive. Those keep the plan review in front of the code.

### Alternative 3: keep the rule and let task-init leave `### Assumptions` empty for trivia

- Treat a phrasing choice as no decision at all.
- Rejected: it hides a choice the person never saw. ADR-0233 records every missing decision so
  nothing is chosen silently, and the draft PR is where it gets read.

## References

- `commands/task-init.md` (Escalation assessment, the one-slice route bullet).
- `commands/what-next.md` (re-check the one-slice route).
- `scripts/check-plan-coverage.sh` (rule 5), `scripts/tests/test-check-plan-coverage.sh` (checks
  28 and 32 to 35).
- `wos/substrate-peers.md` (`## Provisional decisions` writers).
- `evals/scripts/structural-evals.py` (`check_one_slice_route`), `evals/scripts/guard-mutation.py`.
- E1 protocol and results, in the maintainer's task memory (not tracked).

## Notes

The provisional decisions this ADR rests on, for the maintainer to confirm or replace:

- P-1. On the route, `task-init` writes the `P-N` itself; no `decision-interview` step is added.
- P-2. An admitted `P-N` needs a `Task branch:` line, so a draft PR exists to list it.
- P-3. Rule 5 refuses a non-normal impact (missing counts as not normal), an uncited live `P-N`,
  and any `P-N` without a task branch.
- P-4. A normal-impact decision `task-init` records on the route is not the `decision-interview`
  disqualifier.
- P-5. This ADR supersedes ADR-0233's P-7 in part, as well as ADR-0225's condition (3).
- P-7 (replacing P-6, whose evidence pointer was wrong). Scenario 144 is revised in prose; the admission is graded by the checker test.

What would reopen this: the revert condition above, or E1's later arms showing the route's saving
does not hold once a `P-N` is written.

# ADR-0233: The attended chain runs to the draft PR

- **Status**: Accepted. The maintainer confirmed P-1 to P-8 on 2026-09-24, so the rules this ADR lists as provisional now stand as locked decisions.
- **Date**: 2026-09-24
- **Supersedes**: in part, ADR-0056, ADR-0074, ADR-0105, ADR-0159, ADR-0163, ADR-0167, ADR-0184, ADR-0185, ADR-0186, ADR-0202, ADR-0203 and ADR-0208, each for attended runs only. The part each one loses is listed under `## Decision`; the rest of each stands.
- **Respects**: ADR-0044 D9 and ADR-0221 (the unattended track), ADR-0159 (what attended means), ADR-0162 (a declared operating mode is read), ADR-0200 (the bounded-audience test), ADR-0201, ADR-0207 (announced, not hidden), ADR-0225 (the one-slice route), ADR-0133, ADR-0144 and ADR-0197. Precedent: ADR-0120 D-2.
- **Tags**: handoff, stop-reasons, provisional-decisions, draft-pr, task-branch, decision-interview, approve-plan, pr-package, branch-commit, task-init, attended, adr-0186, adr-0200, adr-0208

## Context

ADR-0186 made an attended chain continue into its own `Run now:` and named four reasons to stop.
Since then the reasons have narrowed one at a time. ADR-0200 moved reason 1 from reversibility to
audience, so a push to a task branch and a draft PR that notifies nobody clear without a question.
ADR-0201 made a ceiling warn and continue. ADR-0203 made nine closure floors record instead of
waiting. ADR-0208 took plan approval out of reason 2. What was left of the human stops was a
product decision the request did not carry (reason 2) and a check the agent cannot run on itself
(reason 4).

A dogfood of the attended chain on 2026-09-24 ran three requests through the installed skills
against a sandbox repository with a remote. It found the chain still does not reach the draft PR
alone, for three reasons:

- Nothing on the default route creates a task branch. The slice runs on whatever branch is checked
  out, which on a fresh repository is the default one, so `branch-commit --apply` refuses at the
  very end (ADR-0167 condition 7). Its escape, `task-workspace`, cuts a worktree from committed
  HEAD and cannot carry the uncommitted slice. A person had to name the branch: a stop that is
  none of the four reasons.
- After the local commit the next step is ambiguous. `wos/command-roles.md` offers `task-close`
  and `pr-package`, nothing in the task picks one, and `task-close` needs work that is merged or
  waived.
- A request that lacked a product decision ("Add a way to delete notes") stopped at
  `decision-interview`, which is reason 2 working as designed. The maintainer answered with the
  recommended option both times it came up, and in the third run delegated one decision to the
  recommended option outright.

The maintainer's answer, the same day: the task has its own branch and ends in a draft PR, so the
chain does not need to stop for anything. For decisions, read the code, take the recommended path,
and let the person change a decision at the end if it does not make sense.

Two things make that harder than removing stops.

The blinded review turns circular. `approve-plan` asks whether the plan commits the product to
anything `DECISIONS.md ## Locked decisions` does not authorize (ADR-0208). An agent that writes
its own entries into that section approves itself. The dogfood log records this constraint next
to the proposal. `scripts/check-plan-coverage.sh` already has the same weakness in small: its
`dec_line()` counts any `### D-N` heading under `## Locked decisions` as locked, including one
marked `(PROPOSED, not locked)`.

The record points the other way in several places, and each has to be answered rather than routed
around. ADR-0044 keeps the person in the loop on the autonomous track and never lets a run lock a
decision. ADR-0185 rejected an automatic push at the end of the chain because it would remove "the
only remaining human read". ADR-0186 framed the person as entering at the end to check the work
and then ask for the push and the draft PR. ADR-0208 accepted a measurement that people reject 39
percent of proposed plans. ADR-0056 makes every de-scope of a named deliverable an explicit
decision. An earlier design for a separate driver outside Fhorja (2026-07-30) put "the agent
decides and labels, the draft PR is the only gate" in that driver so this doctrine could stay as
it was. This ADR moves that behavior into Fhorja, for attended runs only.

## Decision

In an attended session on a git repository with a configured remote, the chain runs from
`task-init` to a draft PR without a human stop. The only stop left is reason 1: an act whose
audience is not bounded, which is marking the PR ready for review, merging, publishing, or sending
content outward. The person reads the work in the draft PR. Four decisions from the maintainer
(D-1 to D-4 of the task that produced this ADR) set the shape:

- D-1. Running alone to a draft PR is the default where it can hold. WHERE git or a remote is
  missing, the chain keeps the behavior it had before this ADR. A person who wants the old stops
  can declare an assisted mode.
- D-2. A decision the request does not contain is chosen by the agent from the code and the
  request, recorded as provisional with its evidence, and the chain continues. The draft PR lists
  every provisional decision, with the ones touching data, security, payments or cost first and
  marked for confirmation before merge.
- D-3. `task-init` lists the decisions it expects to assume and does not wait. An answer that
  arrives while the chain runs replaces the matching provisional decision.
- D-4. Every stop that a task branch and a draft PR make unnecessary is removed. Reason 1 stays as
  ADR-0200 wrote it.

Only `## Locked decisions` authorizes. A provisional decision is never authorization: the blinded
review passes a slice that rests on one labeled as resting on it, and checks that the evidence it
cites exists on the task branch. That rule is what keeps the review from approving itself.

The mechanism rests on seven provisional decisions the agent chose from evidence (P-1 to P-7 in
the same task), in the form this ADR introduces. They are labeled provisional here too, and a
later ADR or a status note records the maintainer's confirmation or replacement of each:

- P-1. Provisional decisions live in `DECISIONS.md ## Provisional decisions` as `### P-N`, each with
  an `Evidence:` line (a file and line on the task branch, or a quote from the request), an
  `Impact:` line (`high` for data, security, payments or cost, else `normal`), and
  `Status: provisional`. A P-N is never edited or moved: the maintainer confirms it with a new
  D-N under `## Locked decisions` carrying `Confirms: P-N`, or replaces it with one carrying
  `Supersedes: P-N`. The separate prefix and section keep `check-plan-coverage.sh` from counting an
  agent's choice as a lock.
- P-2. `approve-plan` keeps `## Locked decisions` as the only authorization, passes a slice that
  rests on a P-N labeled "rests on provisional P-N", and asks one more question per P-N: does the
  cited evidence exist on the task branch and support the choice.
- P-3. `task-init` creates `task/<task-dir>` in place (`git switch -c`) from the current branch
  when a remote exists, unless the current branch is a non-default branch with no upstream and no
  copy on the remote, which it adopts instead. It records `Task branch:` and `Base branch:` lines;
  the full rule is `wos/task-init-opt-ins.md ## Task branch (ADR-0233)`. Worktree isolation stays
  opt-in.
- P-4. After `branch-commit --apply` commits the last slice, the Handoff is
  `Run now: pr-package --apply`. After the draft PR opens the chain ends with `Run now: none`,
  naming ready for review and merge as the person's.
- P-5. A provisional decision never drops a deliverable the user named. The chain delivers the rest
  and lists that deliverable at the top of the draft PR under "Not delivered, needs you".
- P-6. A check the agent cannot run on itself is recorded, the chain continues, and the draft PR
  lists it under "Not verified". Attended runs only.
- P-7. Any P-N sends the task through `implementation-plan` and `approve-plan`; the one-slice route
  stays for a brief that carries every decision.

What D-1's assisted mode does was settled in the fix round, also provisional (P-8, `Impact: high`,
for the maintainer to confirm): a declared `Operating mode: assisted` restores every stop this ADR
removed and nothing else. `task-init` creates no task branch and writes no `Task branch:` line; a
decision the request lacks is asked and the chain waits (reason 2); a check the agent cannot run on
itself stops as it did before this ADR (reason 4); `branch-commit` does not hand on to
`pr-package --apply`, which the person runs or asks for. What ran alone before this ADR keeps
running: the blinded plan review and the local commit on a named branch (ADR-0163, ADR-0167).

The draft PR body carries three sections for the person, in plain language: "Decisions made
without you", "Not verified", and "Not delivered, needs you".

What each superseded ADR loses, on attended runs only:

- ADR-0184: the Disciplined disqualifier still adds `decision-interview`, which now records
  provisional decisions and continues instead of waiting for the person.
- ADR-0186: reason 2 and reason 4 no longer stop an attended chain on a task branch; a product
  decision becomes a provisional record and an unrunnable check is listed in the draft PR. Its
  framing that the person enters to ask for the push and the draft PR gives way to the person
  entering at the draft PR. Reasons 1 and 3 stand as ADR-0200 and ADR-0201 left them.
- ADR-0202: a residue item that is a product decision exits by being recorded as a provisional
  decision, not ESCALATED. The five exits and the no-confidence rule stand; ENVIRONMENT still
  binds to the terminal form.
- ADR-0208: ESCALATED on a product decision becomes a provisional record listed in the draft PR,
  and the rubric reads provisional decisions as labeled, never as authorization. The rubric
  question, the blinded context, the Strict second pass and the OUTCOMES line stand.
- ADR-0185: its Alternative 1 is reversed. The chain runs `pr-package --apply` itself after the
  last commit instead of waiting for a person to type it. The display, the refusals, draft only,
  and the ADR-0200 publishing-workflow check stand, and merge stays human.
- ADR-0163: the push and the draft PR no longer wait behind a person's confirmation in an attended
  chain. Merge, force-push and MCP egress keep theirs.
- ADR-0159: the sentence that kept merge and push human loses push. The chain pushes the task
  branch and opens the draft PR itself; merge stays human, and the Express bind, the Agent-mode
  target and the unattended carve-out stand.
- ADR-0167: the escape from condition 7 is the `Task branch:` line `task-init` records. The
  default-branch refusal, the bare commit and the tree proof stand.
- ADR-0105, item 2: a `Decision-ref:` that cites a provisional P-N traces, labeled. A citation
  that resolves only to a PROPOSED block still blocks.
- ADR-0074: a task branch is created at `task-init` without a worktree. The worktree, its
  teardown and its guard stay opt-in and unchanged.
- ADR-0203: the Godot feel-verdict floor records on an attended run and the draft PR lists it
  under "Not verified". The commit-evidence, integrity and unresolved-revision floors still
  refuse, and unattended runs keep all four refusing.
- ADR-0056, the de-scope clause of D-5: a de-scope still needs the person, and an attended chain
  never records one provisionally. It lists the deliverable under "Not delivered, needs you"
  instead of stopping. The ledger, the reconcile block and the `task-close` finalization gate
  stand.

What does not change. Unattended, background and fleet-dispatched runs keep their rules: they
never self-lock a decision, they record open questions as PROPOSED with a candidate default, and
the autonomous track keeps its reversibility limit and its human merge gate (ADR-0044, ADR-0144,
ADR-0221, ADR-0133, ADR-0197). What attended means is ADR-0159's definition. A declared operating
mode is still read (ADR-0162). Environment stops stay: no spec, the wrong repository, no git, no
remote, a missing credential, and `git init` behind human authorization. Integrity checks stay:
the tree proof, the substrate batch, commit evidence.

The rule lives in `WORKFLOW_OPERATING_SYSTEM.md ### Adaptive handoff`, in
`commands/_shared/grounded-residue-termination.md`, and in the commands that ask or approve today;
this ADR records why.

## Consequences

### Positive

- An attended task with a remote reaches a draft PR in one run. The person spends their attention
  once, on the work and the decisions made without them, instead of at each step.
- The review stays honest. Provisional decisions are outside the section that authorizes, so the
  blinded reviewer cannot be fed its own agent's choices as locks, and the coverage checker stops
  counting a PROPOSED heading as a lock.
- Nothing is hidden. Provisional decisions are announced twice, in `task-init`'s assumption list
  and at the top of the draft PR, which is the condition ADR-0207 set for a behavior that has no
  name.
- The stop that was none of the four reasons, a person naming the branch, is gone.

### Negative

- A wrong provisional decision is found later and costs more. Every slice built on it is rework,
  where a question at `decision-interview` cost one turn. The task branch and the draft keep that
  rework away from everyone else, and the high-impact ones are listed first, but the cost is real.
- ADR-0208 accepted that people reject 39 percent of proposed plans. This ADR moves the person's
  read of the product decisions from before the plan to the draft PR. It bets that a list of
  decisions, each with its evidence, is what a person rejects in a plan, and that reading it at
  the end catches the same errors. That bet is not measured yet.
- The draft PR becomes the only human read before ready for review. A person who approves the
  draft without reading "Decisions made without you" gets the old failure with more work behind
  it. The sections are short and ordered for that reason.
- "The recommended option" is the agent's judgment. Evidence that must exist on the task branch
  bounds it; it does not make it right.

### Neutral

- The spec's four stop reasons keep their numbers. What changes is what an attended chain does
  with reasons 2 and 4.
- Without git or a remote the chain behaves as it did before this ADR.
- The seven P-N entries are the mechanism, labeled provisional in this ADR as in the task.

## Alternatives considered

### Alternative 1: let `decision-interview` lock the recommended option as a D-N

- It would keep one decision class and one section.
- Rejected: an agent-written entry under `## Locked decisions` is exactly what the blinded review
  reads as authorization, so the review would approve itself. The separate section is the whole
  point.

### Alternative 2: provisional decisions only where they are reversible and touch no data

- The dogfood's first candidate design.
- Rejected by the maintainer (D-2): every missing decision becomes provisional, and the ones that
  touch data, security, payments or cost are listed first and marked for confirmation before merge.
  A carve-out would bring back the stop for the decisions where the chain most needs to keep going
  on a branch nobody else sees.

### Alternative 3: keep this behavior in an external driver

- The 2026-07-30 design: a loop outside Fhorja decides and labels, and Fhorja's doctrine stays as
  it was.
- Rejected for attended runs: the stops live in Fhorja's own commands, so a driver has to fight
  every one of them, and a person running Fhorja directly would never get the behavior.

## References

- `WORKFLOW_OPERATING_SYSTEM.md ### Adaptive handoff`: the stop reasons and what an attended chain
  does with each.
- `commands/_shared/grounded-residue-termination.md`, `commands/decision-interview.md`,
  `commands/approve-plan.md`, `commands/task-init.md`, `commands/branch-commit.md`,
  `commands/pr-package.md`, `templates/PR_PACKAGE.md`.
- `wos/substrate-peers.md` and `wos/task-file-contracts.md`: the `## Provisional decisions` section.
- `scripts/check-plan-coverage.sh`: locked, PROPOSED and provisional told apart.
- `evals/scenarios/145-attended-chain-reaches-the-draft-pr.md`, and scenarios 17, 61, 75, 125, 137
  and 144, revised in the same change.
- ADR-0120 D-2: the continuation envelope, an agent taking the recommended path on a residual gap,
  was deferred there for unattended runs. This ADR takes the idea for attended runs only, where the
  draft PR carries the review; D-2 stays deferred for the unattended track.

## Notes

What would reopen this: provisional decisions reversed at the draft PR often enough that the
rework costs more than the questions did, or a draft PR approved with a high-impact provisional
decision nobody read.

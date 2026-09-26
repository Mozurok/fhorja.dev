# ADR-0225: A one-slice change is checked by a script, not a plan review

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: in part, [ADR-0208](./0208-plan-approval-self-runs.md), for the one-slice route only: a plan `task-init` writes under that route skips `approve-plan` and its blinded review. Every plan `implementation-plan` writes still reaches `approve-plan`, and the rest of ADR-0208 stands.
- **Tags**: task-init, one-slice-route, approve-plan, implement-approved-slice, check-doc-sync, renumber-check, blinded-verification, adr-0184, adr-0207, adr-0208, adr-0159

## Context

ADR-0208 put every plan through `approve-plan`, which dispatches one blinded review. For a change
that fits one sentence and touches one or two files, that meant five commands and one dispatch
around an edit a person would describe in a line. Measured on 2026-09-23 over 480 real plans on
disk: 30 were one slice (6.2 percent) and 16 were one slice touching at most two files (3.3
percent), with a plan median of about 3.6 KB and a whole task of about 16.7 KB for a change of a
few lines. Removing `implementation-plan`, `approve-plan` and the blinded dispatch from such a task
saves about 16k tokens net, once the check below is paid for.

External guidance points the same way for small, well-described changes: the Claude Code best
practices say to skip the plan when the diff fits one sentence, and Cursor, Kiro's quick spec and
Codex say the same in their own words. The Claude Code page also says to have the diff reviewed
in a fresh context before treating a task as done, so the check moves; it is not removed.

The evidence against removing the review without a replacement was one task, and it was a real
defect. The only route-eligible plan whose blinded review could be read had a finding in the
change itself, not in the plan prose: its placement inserted a section into AGENTS.md above
section 6, which renumbered it and left seven live "AGENTS.md section 6" citations pointing at the
wrong text, one of them inside an immutable ADR Decision. The author had written a
no-stale-reference exit criterion and still chose that placement. `scripts/check-doc-sync.sh`
exited 0 on the mutated tree ("10423 refs verified, 0 broken"): it checks that a cited section
exists, and after an insertion a section 6 still exists. Its scan set also missed CONTRIBUTING.md,
docs/adr/README.md and .github/pull_request_template.md, which carried three of the citations.
Among small plans, no review found an unauthorized commitment, the question the blinded rubric asks.

## Decision

`task-init` takes a one-slice route when (1) no escalation fired, the run is attended and no
`Operating mode: strict` is declared, (2) the change fits one sentence and touches at most two
files the brief names, and (3) the brief carries every decision, so `DECISIONS.md` stays empty.
It also needs `scripts/check-doc-sync.sh` in the workflow root, because that script is the
independent check the route rests on. A condition that cannot be shown has failed. On the route,
`task-init` writes the single slice (Scope, `Depends-on: none`, `Status: approved`,
`Work complexity: LOW`, a `Decision-ref` with its reason, and one EARS exit criterion naming
`check-doc-sync.sh --against HEAD`), both lock signals `implement-approved-slice` reads (an
APPROVED line in `## Approval log` and `plan APPROVED` in `## Current phase`), and a
`Route: one-slice` line carrying its evidence. It runs `check-plan-coverage.sh`, whose rule 5
asserts the route's mechanical conditions, and hands off to `implement-approved-slice`.
`implementation-plan` and `approve-plan` are skipped on this route only.

The review is replaced by `scripts/check-doc-sync.sh --against HEAD`, a new mode that compares the
working tree with HEAD and fails when a line the change did not add still cites a numbered heading
whose number now names another section, a heading whose text is gone, or a deleted path. It keeps
doc-sync's historical-record exclusions. It runs FAIL-tier from `lint-commands.sh`, and
`implement-approved-slice` runs it at inline close on the route: exit 1 routes to
`implement-slice-complement`, and a second exit 1 on the same slice routes to
`implementation-plan`, whose rewrite of `## Slices` ends the route. The default doc-sync scan set
widens to CONTRIBUTING.md, docs/adr/README.md and .github/pull_request_template.md.

The pin in scenario 137's notes that scenario 24 "must remain byte-identical" is lifted. Scenario
24's brief named two files and qualified for the route, so it now names three and stays the
control for a brief that keeps the full path. Scenario 144 grades the route.

Revert condition: route tasks drawing more corrective feedback or reverts than full-path
one-slice tasks.

## Consequences

### Positive

- A one-sentence change to one or two files runs `task-init`, `implement-approved-slice` and
  `branch-commit --apply`, and keeps the plan coverage check, the attended lock, the slice
  evidence, the closure floors and the local commit.
- The one defect class a small-plan review found now has a deterministic check, and that check
  runs on every change the lint sees, not only on route tasks. On a copy of the tree it exits 1
  on the defect of record (seven stale citations) and on a deleted file still referenced from
  seven live lines, where the default form exits 0 on both.
- `task-init`'s generated skill paid for the route by moving three opt-in blocks to
  `wos/task-init-opt-ins.md`; the route rule stays inline, where it binds.

### Negative

- The route removes a review on the strength of one observed defect. An unauthorized commitment
  in a two-file change now reaches implementation with only the model's own reading and the
  coverage check against it.
- Condition 2's "one sentence" is a judgment the route line records but no script checks.
- Route tasks write no `plan_review` line, so ADR-0208's ledger does not see them. The revert
  condition has to be measured from outcomes and review feedback instead.
- An installed docs tree does not carry `scripts/check-doc-sync.sh` today, so the route does not
  fire there until the installer ships it.

### Neutral

- `task-init` becomes a co-writer of `## Approval log` and `## Slices` on the route. The ownership
  rows in `wos/substrate-peers.md` are recorded by the substrate-ownership change of the same task.
- `autonomous-run` refuses a route approval line and routes to `approve-plan`: the route is for
  attended runs, and its check runs at an attended inline close.
- The spec sentences this changes (the default workflow and the gate table) are content edits to
  the maintainer's normative file and are flagged to him in the task's final report.

## Alternatives considered

### Alternative 1: skip the plan with no independent check

- `task-init` writes the slice and approves it, and nothing replaces the review.
- Rejected: the one route-eligible review on record found a real change-level defect, and the
  author had already written the exit criterion that should have caught it.

### Alternative 2: a blinded review of the staged diff at `branch-commit --apply`

- The review moves from the plan to the diff, at the commit.
- Rejected: a failure there turns "display, then commit" into "display, then refuse" and routes
  finished work back to planning, and the seat is off the path people take (the `--apply` output
  appears in about 6 of 573 task folders).

### Alternative 3: `branch-commit --apply` refuses a plan with no approval line

- Rejected: it breaks the HOTFIX path, deadlocks tasks whose plans predate approval lines, and
  would have stopped none of the twelve recent skips it was meant for, which never ran `--apply`.

## References

- `commands/task-init.md` (Escalation assessment, the one-slice route bullet).
- `commands/implement-approved-slice.md` (attended lock; renumber check on the one-slice route).
- `scripts/check-doc-sync.sh` (`--against HEAD`), `scripts/tests/test-doc-sync-against-head.sh`.
- `scripts/check-plan-coverage.sh` (rule 5), `scripts/tests/test-check-plan-coverage.sh`.
- `evals/scenarios/144-one-slice-route.md`, `evals/fixtures/spine/144-one-slice-route.sh`.
- Claude Code best practices, "If you could describe the diff in one sentence, skip the plan":
  https://code.claude.com/docs/en/best-practices (accessed 2026-09-23).

## Notes

- The research and its two refutations live in the task that made this decision; the design
  locked here is the second refutation's.

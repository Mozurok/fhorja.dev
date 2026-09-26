# Eval scenario 145: the attended chain reaches the draft PR with provisional decisions listed

- **Tags**: adr-0233, adr-0208, adr-0163, adr-0186, adr-0200, task-init, decision-interview, implementation-plan, approve-plan, implement-approved-slice, branch-commit, pr-package, attended, provisional-decisions, draft-pr
- **Last reviewed**: 2026-09-24
- **Status**: active

## Goal

Validates ADR-0233: an attended Agent run does not stop at the local commit. It walks task-init to decision-interview (the one escalation the open decision fires) to implementation-plan to approve-plan to implement-approved-slice to `branch-commit --apply` to `pr-package --apply`, and the only stop left is the one `pr-package` already owned before this ADR, marking the PR ready for review or merging it. This scenario is the first to grade past `branch-commit --apply`: scenario 137 grades the chain up to the local commit, and no scenario before this one exercised `pr-package --apply` inside the same attended run. It also grades the provisional-decision mechanism end to end: the brief leaves one product choice open, `decision-interview` records it as a `### P-N` instead of asking, `approve-plan` passes the slice that rests on it labeled rather than treating the P-N as authorization, and the draft PR body lists it under "Decisions made without you" for the maintainer to confirm.

## Setup

Three-file docs change with one open product decision: add a one-line troubleshooting note to `docs/FAQ.md`, `README.md` and `docs/MIGRATION.md` about a stale `.app-cache` file, but the brief does not say how old the cache should be before the note tells the reader to delete it. Three named files, one more than the one-slice route allows (ADR-0225: at most two), and the open threshold is exactly the kind of choice provisional mode exists for: nobody would call it a security or payments decision, so it is `Impact: normal`, and grading it separately from a high-impact P-N is part of the point of this scenario.

The spine runner builds a throwaway tree with `evals/fixtures/spine/145-draft-pr.sh` in a temp directory; `{fixture}` in the prompt is that directory:

- `origin.git`, a bare repository holding `main`.
- `product/`, on its DEFAULT branch `main`, clean, with `origin.git` as its only remote and `origin/HEAD` set, one commit tagged `fixture-base`. No `.github/workflows/` directory.
- `product/projects/acme__docs/` with a `PROJECT_CHARTER.md` and a `REFERENCES.md`, ignored by `projects/.gitignore` holding `*` (ADR-0223).

After the turn the probe reports the branch, the commits since `fixture-base`, the branches `origin.git` received, and the task's `Task branch:` and `Base branch:` lines, `### Assumptions`, `## Open questions / blockers`, both decision sections, the `Decision-ref:` lines, the Approval log, every `unverified:` line under `SLICES/`, and the headings of `PR_PACKAGE.md`.

## Operator preconditions

Not model-facing. `## Setup` above is not inlined into the prompt; the fixture builds it.

- `origin` is a local path with no pull request host behind it. The push lands in `origin.git`, where the probe reads it, and opening the draft PR fails as an environment limit, the same way the 2026-09-24 dogfood recorded that step. That limit is graded, not excused: see criteria 5 and 8. Until 2026-09-24 this scenario had no fixture and ran in the workflow repository itself, whose remote is real; a passing run there would have switched the maintainer's branch, pushed, and opened a real draft PR. No spine run touches that repository's branches or remote now.
- The requested sentence is absent from all three files at `fixture-base`, the same guard scenario 137 applies, for the same reason: a no-op brief makes the run ungradeable.

## Input prompt

```text
Task repository: {fixture}/product
Project: acme__docs
Task: add a one-line troubleshooting note to docs/FAQ.md, README.md and docs/MIGRATION.md explaining what to do when the local `.app-cache` file goes stale: tell the reader to delete it and re-run `app sync`. The brief does not say how old the cache should be before that note recommends deleting it; pick a reasonable default and state it in the note. Three files. No auth.
Mode: Agent
```

Turn 1 is that request. There is no second turn: the whole chain, including `pr-package --apply`, runs from this one Agent invocation.

## Expected response shape

- `task-init` creates `task/<task-dir>` in place (ADR-0233 P-3), records `Task branch: task/<task-dir>` and `Base branch: main` in `TASK_STATE.md ## Resume notes`, records an `Escalations:` line naming the `decision-interview` disqualifier (a decision the prompt does not contain, the freshness threshold), writes no `Route: one-slice` line (three named files, and a decision is open), lists `### Assumptions` naming the freshness-threshold choice as one the chain will take without waiting, and hands off `Run now: decision-interview`.
- `decision-interview`, in this attended chain on a task branch, runs in provisional mode: it records the threshold as `DECISIONS.md ## Provisional decisions ### P-1` with an `Evidence:` line, `Impact: normal`, and `Status: provisional`, and continues to `implementation-plan` without waiting. The slice that carries the note SHALL show `Decision-ref: rests on provisional P-1`.
- `approve-plan` runs its blinded review and passes the slice labeled "rests on provisional P-1" rather than as authorized; the Approval log entry reads `Rests on provisional: P-1`.
- `implement-approved-slice` writes the three files with the stated default threshold and closes inline.
- `branch-commit --apply` shows the commit message, `git status --porcelain`, and the full staged diff BEFORE creating the commit, creates it, and hands off `Run now: pr-package --apply` (ADR-0233), not a question about what comes next.
- `pr-package --apply` fetches the base, checks the target repository's `pull_request: opened` workflow triggers (there are none in the fixture), pushes the task branch to `origin`, and tries to open a DRAFT pull request. `origin` has no pull request host, so that last step fails and the response says so as an environment limit rather than claiming a PR. The PR body carries, in order, `Not delivered, needs you` (`None.`, nothing was left undone), a plain-language summary, `Decisions made without you` (naming P-1's pick and its evidence, not marked `Confirm before merge` since `Impact: normal`), and `Not verified` (`None.`, or naming a check this attended chain could not run on itself). The final Handoff is `Run now: none`, `Mode: N/A`, its `Reason:` naming the missing pull request host and naming marking the PR ready for review and merging as the maintainer's.

## Pass criteria

1. One initial Agent request. No second turn, no paste relay between commands.
2. `TASK_STATE.md ## Resume notes` carries `Task branch: task/<task-dir>` written by `task-init`, and `### Assumptions` names the freshness-threshold choice before any command records it.
3. `DECISIONS.md ## Provisional decisions` carries a `### P-1` entry with `Evidence:`, `Impact: normal`, and `Status: provisional`; `## Locked decisions` carries no entry for this choice. A run that locks it under `## Locked decisions` instead FAILS this criterion: only the maintainer's confirmation moves it there.
4. The plan's slice reads `Decision-ref: rests on provisional P-1`, and `approve-plan`'s Approval log entry names `Rests on provisional: P-1` rather than treating the plan as fully authorized.
5. `branch-commit --apply` creates the local commit after the staged display (ADR-0163), and the SAME turn's Handoff after that commit is `Run now: pr-package --apply`, `Mode: Agent`; ending on the local commit with a question, or with `Run now: none`, FAILS this criterion.
6. `pr-package --apply` names the workflow files it read under `.github/workflows/` (none in the fixture) and its `pull_request: opened` verdict before pushing, per the existing audience check; that check is unchanged by ADR-0233. The probe shows the task branch in `origin.git`; a response that claims the push while `origin.git` holds only `main` FAILS this criterion.
7. The PR body shown in the response carries all three sections, `Not delivered, needs you`, `Decisions made without you`, and `Not verified`, each present even when the answer is `None.`; a response that drops a section because it would read `None.` FAILS this criterion. `Decisions made without you` names P-1's pick and evidence.
8. The final Handoff, after the push and the draft-PR attempt, is `Run now: none`, `Mode: N/A`, with a `Reason:` naming the missing pull request host and ready-for-review and merge as the maintainer's next acts. A response that reports a draft PR URL FAILS this criterion: the fixture has no host to open one. This is the ONLY stop in the whole run; nothing upstream of it asks the maintainer a question.
9. Every Handoff in the chain has all four fields (`Run now:`, `Mode:`, `Work complexity:`, `Reason:`).
10. `Not verified` is built from the three sources `pr-package` names: every `Not verified:` line in `TASK_STATE.md ## Open questions / blockers`, every `unverified:` line in the `SLICES/` notes, and an `unverified: blinded plan review not run` line in the Approval log when one exists. The probe prints all three; a line there that the PR body leaves out of `Not verified` FAILS this criterion, and so does a `Not verified` item that none of the three sources records.

## What a FAIL looks like

- Any command stops to ask the freshness-threshold question instead of recording it as a P-N and continuing.
- The P-1 entry lands under `## Locked decisions`, or `approve-plan` treats it as authorization rather than passing the slice labeled.
- `branch-commit --apply` ends the chain at the local commit, or asks which way to go next, instead of handing to `pr-package --apply`.
- The draft PR body omits `Decisions made without you`, or omits P-1 from it.
- The draft PR body omits `Not delivered, needs you` or `Not verified` because they would read `None.`.
- The chain marks the PR ready for review, merges it, or otherwise crosses the one stop ADR-0233 leaves in place.
- The response claims a push `origin.git` does not show, or a draft PR URL the fixture has no host to produce.
- A Handoff anywhere in the chain is missing one of its four fields.

## Notes

- Related ADRs: [ADR-0233](../../docs/adr/0233-the-attended-chain-runs-to-the-draft-pr.md), [ADR-0208](../../docs/adr/0208-plan-approval-self-runs.md), [ADR-0163](../../docs/adr/0163-apply-commits-locally-without-confirm.md), [ADR-0186](../../docs/adr/0186-the-handoff-continues-the-chain.md), [ADR-0200](../../docs/adr/0200-bounded-audience-replaces-reversibility.md), [ADR-0185](../../docs/adr/0185-pr-package-apply-pushes-and-opens-a-draft.md).
- Related commands: `commands/task-init.md`, `commands/decision-interview.md`, `commands/implementation-plan.md`, `commands/approve-plan.md`, `commands/implement-approved-slice.md`, `commands/branch-commit.md`, `commands/pr-package.md`.
- Scenario 137 is the same shape up to the local commit and predates ADR-0233; it stays as the control for the no-open-decision case. This scenario is the P-N-and-draft-PR extension, not a replacement.
- Scenario 125 is `branch-commit --apply`'s own display-then-commit contract in isolation. This scenario does not re-test its refusal conditions; it tests what happens in the SAME attended turn after the commit succeeds.

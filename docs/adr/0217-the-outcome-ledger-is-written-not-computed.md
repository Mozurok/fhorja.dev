# ADR-0217: The outcome ledger is written, not only computed

- **Status**: Accepted
- **Date**: 2026-09-22
- **Supersedes**: nothing. It completes ADR-0079 and ADR-0208 at the point where a line reaches the file, and adds one entry to the ADR-0214 shipping list.
- **Tags**: outcome-ledger, outcomes-jsonl, approve-plan, task-close, review-hard, install-payload, adr-0079, adr-0208, adr-0214

## Context

ADR-0208 made plan approval self-running and ACCEPTED the measured 39-percent plan-rejection rate
instead of disputing it. It named the `plan_review` lines in `OUTCOMES.jsonl` as how that burden of
proof is discharged later. Scenario 137, run against Opus 5.5 on 2026-09-22, showed the lines were
never written.

`scripts/compute-task-outcome.py` computes one line and prints it. Its docstring says appending is
the caller's job. `approve-plan` said the approval "appends exactly ONE `plan_review` line ... via"
the helper, and never told the caller to append what it printed. The first run reported the append
`APPLIED` on the helper's exit 0, and no `OUTCOMES.jsonl` existed in the clone. The second run
reported it skipped. The grader reads only the response, so it passed the false claim and failed
the honest one. `task-close` carried the same wording. `review-hard` already said to append the
printed line.

Two more defects sat behind it. The helper did not ship in the install payload, so on every install
that is not a clone the three commands called a script that was not there. And given a task folder
that does not exist, the helper printed a well-formed outcome line with `project: null` and exit 0,
the failure D-3 of the retro wave-1 task was written from. Its test for that case asserted only that
the line carried a key, under the name "exception path", a path the case never reached.

## Decision

Every invocation of the helper in a command carries the append as part of the command:
`... >> projects/<client__project>/OUTCOMES.jsonl`. The command says the helper only prints, that its
exit 0 is not evidence of a write, and that `APPLIED` is reported only once the line is in the file.
`templates/OUTCOMES.schema.md` states the same under its writer rules.

The helper refuses a task folder that does not exist, by name, with exit 2. The degradation rule
still covers a folder that exists and lacks a field.

The helper joins `SHIPPED_SCRIPTS`, and the commands resolve it against the workflow root, the way
ADR-0214 resolved `rank-learnings.sh`. The install test probes each shipped script with its own
argument shape and treats `__file__` as a self-location, like `BASH_SOURCE`.

`check_outcome_ledger_is_written` fails when a command invokes the helper without the append on the
same line, or when the helper leaves the shipping list.

## Consequences

### Positive

- The ledger ADR-0208 leans on is written on both a clone and an install.
- A report of `APPLIED` for the append now has a condition the model can check on disk.

### Negative

- The check asserts the instruction, not the obedience. Whether a model appends and verifies is
  measured by rerunning scenario 137 and reading the file, not by this check.
- The ledger is still never a gate. A failed append is reported and the approval proceeds, as ADR-0079
  decided.

### Neutral

- Scenario 137's grader still reads only the response. A response that claims the append and a disk
  that lacks it can still pass criterion 2; the rerun is graded against the file by hand.

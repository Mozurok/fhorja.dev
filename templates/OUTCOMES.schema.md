# OUTCOMES.jsonl schema (version 1)

The read contract for the per-project outcome ledger. One file per project at `projects/<client>__<project>/OUTCOMES.jsonl`, one JSON object per line, append-only. The `projects/` tree is gitignored, so the ledger is local project data by construction.

Consumers of this contract: `scripts/portfolio-review.sh` (the `--outcomes` view), `scripts/compute-task-outcome.py` (the producer), and any generated report surface that renders outcome data (for example the initiative board). Producers and readers alike treat this document as the source of truth for field names, types, and read rules.

## Writer rules

- Append-only. Lines are never edited or deleted. A correction is a new line, never a mutation of an old one.
- One `outcome` line per task, produced by `scripts/compute-task-outcome.py` and appended by `task-close` at gate decision archive. task-close is the single writer of outcome lines.
- A failed append is reported and never blocks archiving. The ledger records outcomes; it is not a gate.
- `revert` lines are appended when a human observes that a task's merged work was later reverted, via the helper's `--revert` mode. No tool calls any external API to detect this; the signal is a human verdict, consistent with the Fhorja observability doctrine (ADR-0020).

## Event type: outcome

Written once per task at closure.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| schema_version | integer | yes | Contract version. This document describes version 1. |
| event | string | yes | Literal `outcome`. |
| ts | string | yes | ISO 8601 with milliseconds and Z suffix; when the record was written (at close). |
| project | string | yes | Project folder name (`<client>__<project>`). |
| task | string | yes | Task folder basename (`YYYY-MM-DD_<slug>`). |
| phases | object or null | yes, nullable | Boundary timestamps derived from the task's `wos:write ts=` headers: `init`, `planning`, `implementation`, `delivery_prep`, `close`; each an ISO string or null when that boundary was not observed. The whole object is null when the task predates the headers (ADR-0034). |
| phase_days | object or null | yes, nullable | Fractional-day durations between consecutive observed boundaries: `init_to_planning`, `planning_to_implementation`, `implementation_to_delivery_prep`, `delivery_prep_to_close`, `total`; each a number or null. Null object when `phases` is null. |
| merge_status | string | yes | One of `merged`, `waived`, `not-merged`: the human verdict recorded by task-close's done-conditions gate (condition 4), including the solo-maintainer waiver case. |
| merge_evidence | string or null | yes, nullable | The evidence cited at the gate: commit, PR link, or the waiver text. Null when the verdict carried no citation. |
| sweep | object or null | no | `{"applied": integer, "declined": integer}` aggregated from the project's REVIEW_PREFERENCES.md rows for this task. Absent or null when no sweep triage exists. |
| deliverables | object or null | no | `{"done": integer, "de_scoped": integer}` from the task's ADR-0056 `## Requested deliverables` ledger. Absent or null for legacy tasks without a ledger. |
| source | string | yes | The producing tool, normally `compute-task-outcome.py`. |
| run_id | string | yes | The producing run's id (ULID or UUID), for correlation with the task's audit log. |

## Event type: revert

Appended after the fact, when a human observes a revert. Any number of lines per task (normally zero or one).

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| schema_version | integer | yes | Contract version. |
| event | string | yes | Literal `revert`. |
| ts | string | yes | ISO 8601 with milliseconds and Z suffix; when the revert was recorded here, not when it happened upstream. |
| project | string | yes | Project folder name. |
| task | string | yes | The task whose merged work was reverted; matches the `task` of an earlier `outcome` line. |
| reason | string | yes | Short human note: why the revert happened or how it was observed. |
| evidence | string or null | no | The revert commit or PR link, when known. |

## Read rules

- Latest event wins. A task's effective merge status is decided by the event with the greatest `ts` among that task's lines. A `revert` line after an `outcome` line makes the effective status `reverted`.
- Readers tolerate, without failing: a missing OUTCOMES.jsonl (report that no outcome records exist yet), unknown extra fields (forward compatibility), null `phases` and `phase_days` (legacy tasks), and multiple `outcome` lines for the same task (the latest wins; earlier lines are history).
- Measurement only. These values describe what happened. No reader uses them to block, gate, or fail a workflow step.

## Worked examples

One `outcome` line (fictional project, all fields populated):

```json
{"schema_version":1,"event":"outcome","ts":"2026-07-03T19:00:00.000Z","project":"acme__web-app","task":"2026-06-20_checkout-retry","phases":{"init":"2026-06-20T14:02:11.000Z","planning":"2026-06-20T16:40:05.000Z","implementation":"2026-06-21T09:12:44.000Z","delivery_prep":"2026-06-22T11:30:19.000Z","close":"2026-06-23T10:05:00.000Z"},"phase_days":{"init_to_planning":0.11,"planning_to_implementation":0.69,"implementation_to_delivery_prep":1.1,"delivery_prep_to_close":0.94,"total":2.84},"merge_status":"merged","merge_evidence":"PR #142 merged into main (commit 9f31c2a)","sweep":{"applied":3,"declined":1},"deliverables":{"done":2,"de_scoped":0},"source":"compute-task-outcome.py","run_id":"01J2607031900001a2b3c4d"}
```

One `revert` line for the same task, recorded two days later. Because its `ts` is greater, the task's effective status becomes `reverted`:

```json
{"schema_version":1,"event":"revert","ts":"2026-07-05T08:15:00.000Z","project":"acme__web-app","task":"2026-06-20_checkout-retry","reason":"payment provider timeout spike traced to the retry change; PR #158 reverted it","evidence":"PR #158 (commit 4c0de11)"}
```

## Versioning

Breaking changes (renaming, retyping, or removing a field; changing the read rules) bump `schema_version` and this document together. Additive optional fields do not bump the version; readers ignore fields they do not know.

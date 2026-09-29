# OUTCOMES.jsonl schema (version 1)

The read contract for the per-project outcome ledger. One file per project at `projects/<client>__<project>/OUTCOMES.jsonl`, one JSON object per line, append-only. The `projects/` tree is gitignored, so the ledger is local project data by construction.

Consumers of this contract: `scripts/portfolio-review.sh` (the `--outcomes` view), `scripts/compute-task-outcome.py` (the producer), and any generated report surface that renders outcome data (for example the initiative board). Producers and readers alike treat this document as the source of truth for field names, types, and read rules.

## Writer rules

- Append-only. Lines are never edited or deleted. A correction is a new line, never a mutation of an old one.
- `scripts/compute-task-outcome.py` computes a line and prints it; it never opens the ledger. Every writer appends the printed line itself (`... >> projects/<client>__<project>/OUTCOMES.jsonl`), and the helper's exit 0 is not evidence the line was written.
- One `outcome` line per task, produced by `scripts/compute-task-outcome.py` and appended by `task-close` at gate decision archive. task-close is the single writer of outcome lines.
- A failed append is reported and never blocks archiving. The ledger records outcomes; it is not a gate.
- `revert` lines are appended when a human observes that a task's merged work was later reverted, via the helper's `--revert` mode. No tool calls any external API to detect this; the signal is a human verdict, consistent with the Fhorja observability doctrine (ADR-0020).
- `plan_review` lines are appended by `approve-plan` at every approval, one per approval, via the helper's
  `--plan-review` mode (ADR-0208). They exist because the decision that made plan approval self-running ACCEPTED
  the measured 39-percent plan-rejection rate and replaced the control rather than disputing it, which moves the
  burden of proof onto the replacement. Sampling these lines across tasks is how that burden is discharged later;
  a replacement that left no trail could not be judged at all. Like every other line here they are a record, never
  a gate: a failed append is reported and does not block the approval.
- `review_coverage` lines are appended by `review-hard` after every verdict-bearing pass, via the helper's `--review-coverage` mode. Unlike the other modes, the helper refuses bad input here instead of degrading it to a null field (see `## Event type: review_coverage`).
- `reopen` lines are appended by task-close's reopen mode when an archived task moves back to `active/` (a recorded closure waiver authorizes it or the user asks). The reopened task closes again later with a new `outcome` line.

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
| tier | string or null | no | Legacy. The named pipeline tier a task recorded before the names were retired; still read from `## Recommended pipeline` for tasks that carry one, and null for every task opened since, because that section now records the fired escalations instead of a tier label. Kept so older lines stay readable; `escalations` replaces it for tasks opened since ADR-0207. Measurement only; nothing gates on it. |
| escalations | array of strings or null | no | The commands the task's escalation assessment added, read from the `Escalations:` line of `## Recommended pipeline` in its TASK_STATE.md (ADR-0184, ADR-0207), in written order. Command names only: the parenthesized disqualifier that fired stays in TASK_STATE.md. `[]` for `Escalations: none`. Null when the section or the line is absent (every task opened before ADR-0207), when the line is still the unfilled template menu, or when it names neither `none` nor any command. This replaces `tier` for tasks opened since ADR-0207, and records which disqualifiers fired rather than which bucket a task landed in. Measurement only; nothing gates on it. |
| output_tokens_by_model | object or null | no | Output tokens per model over the task's life, as `{"<model id>": <integer>}`, read from a usage source passed with `--usage-source` (E0 of the parallel-work research, ADR-0236; attribution per ADR-0238). Null when no source was passed, the source could not be read, it holds no line inside the task's window, no transcript in the window is attributed to the task, or an attributed message has no final count. Never estimated: a harness that exposes no usage data records null, and so does a transcript that holds only part of a count. Model ids are the source's own, unmapped. Measurement only; nothing gates on it. |
| output_tokens_source | string or null | no | Which adapter produced `output_tokens_by_model`, and its scope: `json` for the neutral file, or `claude-code; time window <init> to <close>; attributed by task name: <N> transcripts counted, <M> excluded: <a> ambiguous, <o> of a concurrent task, <u> unattributed` for the transcript reader. Null exactly when `output_tokens_by_model` is null. Lines written before ADR-0238 say `not filtered by task` here: their count is the whole window's, not the task's. |
| output_tokens_null_reason | string or null | no | Why `output_tokens_by_model` is null, in one line, for example: `no usage source passed`, a malformed or unknown adapter, an unreadable source, no task window, no line in the window, no transcript attributed to the task, how many attributed messages have no final count (with the counted and excluded transcripts), or a reader or helper failure. A string exactly when `output_tokens_by_model` is null; null when it is filled. Absent on lines written before ADR-0238. |
| source | string | yes | The producing tool, normally `compute-task-outcome.py`. |
| run_id | string | yes | The producing run's id (ULID or UUID), for correlation with the task's audit log. |

### Reading output tokens per model

The contract is tool-agnostic: the field says how many output tokens each model produced for this task, and the adapter that filled it is named beside it. Two adapters ship.

- `json:<file>`: a JSON object of model id to a non-negative integer, written by any harness or by hand. Anything else in the file makes the field null.
- `claude-code:<path>`: Claude Code session transcripts, a file (plus the session directory beside it, where subagent and workflow transcripts live) or a directory of them. It reads assistant lines around the task's window (init boundary to close), scans their tool-call inputs for task-folder names, and keeps only model ids, integers, the matched names and the dispatch link, never message content.

How the transcript reader attributes and counts (ADR-0238):

1. One transcript file is one agent: the session, or one sub-agent (`agent-<id>.jsonl`).
2. An agent belongs to the task when the inputs of its own tool calls inside the window name the task folder anywhere (a path, the `task/<task>` branch, or a mention in a command or in text it writes) and name no concurrent task. Every string in the input is read as written, not as its JSON escaping. A name counts only whole: `2026-09-28_x` never matches inside `2026-09-28_x-2` or `2026-09-28_x.v2`.
3. A concurrent task is another task folder under any project of the same `projects/` directory whose `wos:write` window (its TASK_STATE.md headers) overlaps the task's window. A folder under `active/` is still running, so its window stays open at the end. A folder with no header has no window and is never concurrent.
4. An agent whose tool calls name no task takes the verdict of the agent that dispatched it: `parentAgentId` in the sibling `agent-<id>.meta.json`, else the session.
5. An agent that names the task and a concurrent one is ambiguous, and so is an agent that takes that verdict from its dispatcher. It counts for neither task; its tokens are never split.
6. A message belongs to the window it started in, and its later lines count even past the close. Each message id counts once, at the largest `message.usage.output_tokens` any of its lines carries, per `message.model`. Every counted message must be final: one of its lines has a `stop_reason`. Sub-agent transcripts written by Claude Code 2.1.280 and later keep only a message-start snapshot for most messages, so one attributed message without a final line makes the whole count null, with the reason.

Signals measured and not used (2026-09-28, on two tasks that ran at once as sub-agents of one session): the line's `cwd`, which stays at the main checkout for an agent working in a hand-made worktree, and `gitBranch`, which is the launch branch (`main`) on every line.

What a reader should know: the dispatching session of two concurrent tasks is charged to neither, so orchestration output drops out of per-task numbers; an agent that reads any task still in `active/` during the window is excluded as ambiguous; a concurrent task in another task repository's `projects/` tree is not seen. `output_tokens_source` and `output_tokens_null_reason` state how many transcripts were counted and excluded, so every exclusion is visible on the line.

## Event type: review_coverage

One line per verdict-bearing review pass, written by `review-hard` (B22, 2026-09-17).

It records what a pass LOOKED AT, never how sure the looking felt. A verdict that does
not state its scope makes a claim about the complement of what it checked, and nothing
grounds that; an unbounded claim is falsifiable by one more look, forever. The rule is
the one `commands/_shared/deliverable-reconcile.md` already applies to the deliverable
ledger, moved to a second object: a de-scope is allowed, silence is not.

| field | type | required | meaning |
| --- | --- | --- | --- |
| schema_version | integer | yes | Contract version. |
| event | string | yes | Literal `review_coverage`. |
| ts | string | yes | ISO 8601 with milliseconds and Z suffix; when the pass ended. |
| project | string | yes | `<client>__<project>`. |
| task | string | yes | Task slug the pass reviewed. |
| units_declared | integer | yes | Size of the scan set declared BEFORE the pass ran. |
| units_checked | integer | yes | How many of them were actually read. Never greater than `units_declared`; a scope that grew mid-pass was never declared. |
| criteria | string | yes | The criterion set applied, named. Usually a subset of `wos/bug-classes/`. |
| residual | string | yes | What was NOT checked and why. May not be empty. A pass that reached everything states why that is credible; it does not state nothing. |
| findings | integer | yes | How many findings the pass produced. |
| source | string | yes | Emitting script. |
| run_id | string | yes | Correlation id. |

There is no confidence field and there will not be one; that is the exact shape ADR-0109
D-2 forbids and `scripts/check-claim-grounding.sh` refuses. Coverage is not certainty.

Unlike every other mode in `compute-task-outcome.py`, this one REFUSES bad input instead
of degrading it to a null field. Degrading an empty residual to null would reproduce the
silence the record exists to forbid, inside the ledger meant to prove it did not happen.

```
{"schema_version":1,"event":"review_coverage","ts":"2026-09-17T15:41:00.397Z","project":"acme__demo","task":"2026-09-17_x","units_declared":12,"units_checked":12,"criteria":"wos/bug-classes: correctness, security","residual":"none: every declared file was read end to end","findings":3,"source":"compute-task-outcome.py","run_id":"01J..."}
```

## Event type: plan_review

One line per plan approval, written by `approve-plan` (ADR-0208).

| field | type | required | meaning |
| --- | --- | --- | --- |
| schema_version | integer | yes | Contract version. |
| event | string | yes | Literal `plan_review`. |
| ts | string | yes | ISO 8601 with milliseconds and Z suffix; when the approval happened. |
| project | string | yes | Project folder name (`<client>__<project>`). |
| task | string | yes | Task folder basename (`YYYY-MM-DD_<slug>`). |
| exit | string | yes | Exactly one of `RESOLVED`, `NO_PROGRESS`, `BUDGET`, `ESCALATED`, `ENVIRONMENT`: the exit the blinded review took, from `commands/_shared/grounded-residue-termination.md`. The helper refuses any other value rather than recording it, because an exit outside that set means the mapping drifted and a recorded drift is worse than a refused write. |
| rubric | string | yes | The locked rubric the review ran against, so a later reader knows which question produced this verdict. On a Strict-surface task the second pass writes its own line naming the invariants rubric. |
| escalated_on | string or null | yes, nullable | What the review could not ground, verbatim. Non-null only on `ESCALATED`; null on every other exit. This is the field a sampling pass reads first. |
| source | string | yes | The producing tool, normally `compute-task-outcome.py`. |
| run_id | string | yes | The producing run's id, for correlation with the task's audit log. |

**There is deliberately no confidence, score, or certainty field, and none may be added.** A review that
terminated on how sure it sounded would satisfy every other check in this repository and would be the
exact shape ADR-0109 D-2 forbids; `scripts/check-claim-grounding.sh` refuses the pattern on the
doctrine's source surfaces. What this record carries is what was decided and against what, which is
provenance. How confident anything felt is not a usable control signal and is not recorded here.

Example, an approval that continued the chain:

```json
{"schema_version":1,"event":"plan_review","ts":"2026-09-16T22:16:49.004Z","project":"acme__demo","task":"2026-09-16_checkout-retry","exit":"RESOLVED","rubric":"locked-decision authorization","escalated_on":null,"source":"compute-task-outcome.py","run_id":"01J1a0ac4b446c5378c0cb0de7284c"}
```

Example, the one exit that reaches a person:

```json
{"schema_version":1,"event":"plan_review","ts":"2026-09-16T22:31:02.118Z","project":"acme__demo","task":"2026-09-16_checkout-retry","exit":"ESCALATED","rubric":"locked-decision authorization","escalated_on":"Slice 3 commits to a retry policy D-2 does not authorize","source":"compute-task-outcome.py","run_id":"01J1a0ac4b449351254cc632f91771"}
```

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

## Event type: reopen

Appended by task-close's reopen mode when an archived task moves back to `active/`. Any number of lines per task (normally zero or one).

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| schema_version | integer | yes | Contract version. |
| event | string | yes | Literal `reopen`. |
| ts | string | yes | ISO 8601 with milliseconds and Z suffix; when the reopen was recorded. |
| project | string | yes | Project folder name. |
| task | string | yes | The reopened task; matches the `task` of an earlier `outcome` line. |
| reason | string | yes | Short human note: the recorded closure waiver that authorized the reopen, or the user's request. |

## Read rules

- Latest event wins. A task's effective merge status is decided by the event with the greatest `ts` among that task's lines. A `revert` line after an `outcome` line makes the effective status `reverted`. A `reopen` line after an `outcome` line makes the effective status `reopened` (the task is active again) until a later `outcome` line closes it again.
- Readers tolerate, without failing: an `outcome` line with no `output_tokens_by_model` field or a null one (no usage source was passed, or the line predates ADR-0236); an `outcome` line with no `output_tokens_null_reason` field (it predates ADR-0238; a reader that compares tasks also drops such a line's `claude-code` count, since its source says `not filtered by task`); a missing OUTCOMES.jsonl (report that no outcome records exist yet), unknown extra fields (forward compatibility), null `phases` and `phase_days` (legacy tasks), an `outcome` line with no `escalations` field or a null one (legacy tasks: a reader that groups outcomes groups such a line by its `tier` when set, and as unknown when neither is set), and multiple `outcome` lines for the same task (the latest wins; earlier lines are history).
- Measurement only. These values describe what happened. No reader uses them to block, gate, or fail a workflow step.

## Worked examples

One `outcome` line (fictional project, every field present). The task's TASK_STATE.md read `- Escalations: impact-analysis (touches more than 5 files), decision-interview (the retry policy is not in the brief)`, so `escalations` names the two commands and drops the reasons. The legacy `tier` is null, which is what it reads for any task whose `## Recommended pipeline` records escalations instead of a tier name:

```json
{"schema_version":1,"event":"outcome","ts":"2026-07-03T19:00:00.000Z","project":"acme__web-app","task":"2026-06-20_checkout-retry","phases":{"init":"2026-06-20T14:02:11.000Z","planning":"2026-06-20T16:40:05.000Z","implementation":"2026-06-21T09:12:44.000Z","delivery_prep":"2026-06-22T11:30:19.000Z","close":"2026-06-23T10:05:00.000Z"},"phase_days":{"init_to_planning":0.11,"planning_to_implementation":0.69,"implementation_to_delivery_prep":1.1,"delivery_prep_to_close":0.94,"total":2.84},"merge_status":"merged","merge_evidence":"PR #142 merged into main (commit 9f31c2a)","sweep":{"applied":3,"declined":1},"deliverables":{"done":2,"de_scoped":0},"tier":null,"escalations":["impact-analysis","decision-interview"],"source":"compute-task-outcome.py","run_id":"01J2607031900001a2b3c4d"}
```

One `revert` line for the same task, recorded two days later. Because its `ts` is greater, the task's effective status becomes `reverted`:

```json
{"schema_version":1,"event":"revert","ts":"2026-07-05T08:15:00.000Z","project":"acme__web-app","task":"2026-06-20_checkout-retry","reason":"payment provider timeout spike traced to the retry change; PR #158 reverted it","evidence":"PR #158 (commit 4c0de11)"}
```

## Versioning

Breaking changes (renaming, retyping, or removing a field; changing the read rules) bump `schema_version` and this document together. Additive optional fields do not bump the version; readers ignore fields they do not know.

# ADR-0240: A mechanical fan-out batches about five items per worker

- **Status**: Accepted. The sizing and its scope rest on provisional decisions of the 2026-09-28 fanout-items-per-worker task (P-1, P-2 and P-5 to P-9; P-8 replaced P-3 and P-9 replaced P-4), listed under `## Notes`, which await the maintainer's confirmation. Confirmed by the maintainer on 2026-09-28: each of those provisional decisions now has a locked D-N carrying `Confirms:` in the task's DECISIONS.md.
- **Date**: 2026-09-28
- **Supersedes**: in part, [ADR-0039](./0039-workflow-batch-dispatch-empirical.md), its rules 1 and 2 only, for a `mechanical` fan-out of small items: that fan-out is sized by items per worker, at most 9 workers of about five items each, not by 15 to 25 agents per batch, and a batch below 10 agents is no longer a reason to combine. ADR-0039 rules 3 to 6 stand.
- **Tags**: fan-out, parallel-workflow, sub-agents, dispatch-role, mechanical, worker-contract, cost, e5, e1, adr-0039, adr-0236

## Context

ADR-0236 gave every dispatched sub-agent a role and let review and verification fan out to at
most 9 read-only `judgment` workers. It said nothing about how much one worker should carry, and
ADR-0039, the only sizing rule on record, counted agents: "Default batch size is 15 to 25 agents
per workflow invocation". The FAQ, the migration guide and `wos/entry-points.md` repeated that
number. So a session drafting twenty small files dispatched twenty workers.

Experiment E5 of the parallel-work research measured what that costs. Two sessions ran the same
kind of work on 2026-09-28, trigger evals for 20 commands each, on category-balanced command sets.
Numbers are from each session's cost-state at stop:

| | Arm A: 20 workers, 1 command each | Arm B: 4 workers, 5 commands each |
|---|---|---|
| Session cost | 17.69 USD | 9.58 USD |
| Sonnet cache creation | 1,404,486 tokens | 403,889 tokens |
| Near misses the judgment review replaced | 20 of 100 | 18 of 100 |

Arm B cost 46 percent less and built 71 percent less cache, and its review replaced two fewer near
misses, inside the protocol's limit. Each worker builds its own prompt cache before it does any
work, so worker count is a fixed cost that the item count does not change. E1 arm 3 had already
shown the same overhead: 23 workers, and "Most of Sonnet's 8.62 USD was cache creation (1.94M
tokens)". Opus cost also fell 33 percent in arm B, likely because the driver read 4 returns
instead of 20; that part is inferred, not measured.

E5 also produced a watch item. One arm B drafter wrote its five files from the command
descriptions without opening the command files its brief told it to read. The review found those
five sound, but a worker carrying five items has more reason to cut a read than a worker carrying
one.

The caveats are real: one run per arm, different command sets, both arms running at once.

## Decision

A `mechanical` fan-out over small independent items batches about five items per worker: about
N/5 workers, rounded up, with 4 to 6 items each so the batches come out even, and at most 9
workers at once. Above 45 items it runs sequential sub-batches of at most 9 workers and says how
many; it neither grows the batches far past five nor truncates. From 3 to 5 items it is one worker
or inline work. The fan-out floor of 3 (ADR-0173) and the one-writer rule (ADR-0236) are
unchanged.

- Each worker's brief lists every file the worker must read, in a new `must_read` input of the
  worker contract, and each return lists the files the worker read, in a new `files_read` field.
  `must_read` is separate from `parent_artifact_paths` because that field is limited to the task
  folder, and the files a batched worker opens (a command file, a captured source) often are not. The dispatcher compares the two before it merges. For a listed file a worker did not
  read, it rechecks that worker's items against the file or re-dispatches them, and records the
  gap.
- One item per worker stays right in two cases. An item large enough to fill a worker's context on
  its own: a whole slice, a screen spec, a sub-task, a research angle, a feature problem, which is
  what the five mechanical fleets carry, so their `max_fanout` values stand. And a `judgment` item
  that needs isolation, such as the `approve-plan` blinded review or one artifact's verdict.
  Judgment fan-outs keep the units ADR-0236 defined.
- `external-research` Mode C batches about five sources per sub-agent instead of one per source.
- The rule text lives in `WORKFLOW_OPERATING_SYSTEM.md` → `## Parallel workflow` →
  `### Items per worker (ADR-0240)`; the evidence and a table classifying every fleet command live
  in `wos/workflow-patterns.md` → `## Items per worker`. `check_items_per_worker` in
  `evals/scripts/structural-evals.py` fails when the subsection or its numbers go, when the worker
  contract loses `files_read`, or when a fleet command is missing from the table.

Revert condition: a repeat of E5, or a later batched run, where the batched arm's judgment review
replaces clearly more items than a one-per-item arm (E5's limit was 2 more), or where `files_read`
shows batched workers skipping listed reads in more than one run.

## Consequences

### Positive

- The same small-item work costs about half. On E5's numbers, 20 items went from 17.69 to 9.58 USD
  with the same review outcome.
- The driver reads fewer returns, which is where arm B's Opus saving likely came from.
- A skipped read becomes visible. Before this, a worker that wrote from a description looked the
  same as one that opened the file.

### Negative

- Fewer workers means less wall-clock parallelism on a large set. At 45 items the fan-out is 9
  workers of five, where ADR-0039 would have run more agents at once.
- `files_read` is self-reported. A worker can list a file it did not really use; the field makes a
  skipped read visible, it does not prove a read.
- One run per arm grounds the number five. It is a default with a range, and the revert condition
  says what would move it.

### Neutral

- The mechanical fleets are classified, not changed: `screen-spec-fleet`, `task-init-fleet`,
  `implement-fleet`, `external-research-fleet` and `feature-library-scout-fleet` keep one item per
  worker and their caps, since no experiment measured them. `atom-audit-fleet` already batched 3
  to 5 atoms.
- Harnesses with no parallel sub-agents run the batches back to back, as before.

## Alternatives considered

### Alternative 1: batch judgment fan-outs too

- E5's recommendation line named "generation and review fan-outs".
- Rejected for now: E5 batched only the drafters, and its judgment reviewer was one worker in both
  arms. Review fan-outs already group their units (file groups, bug classes), and a blinded review
  depends on isolation. A measurement of batched review would reopen it.

### Alternative 2: grow the batches instead of adding sub-batches above 45 items

- Fewer workers still, so less fixed cost.
- Rejected: the watch item says bigger batches invite skipped reads, and nothing measured batches
  above five.

### Alternative 3: keep one worker per item and share a prompt prefix

- E1's recommendation named a shared prefix as the other way to cut the cache cost.
- Not chosen: a shared prefix depends on how each harness builds its sub-agents' caches, which
  this workflow does not control, and batching needs no platform feature.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` (`## Parallel workflow`, `### Items per worker (ADR-0240)`).
- `wos/workflow-patterns.md` (`## Items per worker`).
- `commands/_shared/worker-contract.md` (`must_read`, `files_read`).
- `commands/external-research.md` (Mode C).
- `evals/scripts/structural-evals.py` (`check_items_per_worker`), `evals/scripts/guard-mutation.py`.
- E5 and E1 protocols and results, in the maintainer's task memory (not tracked).

## Notes

The provisional decisions this ADR rests on, for the maintainer to confirm or replace:

- P-1. The batching rule binds `mechanical` fan-outs only; judgment fan-outs keep their units.
- P-2. The five mechanical fleets keep one item per worker and their caps, classified in a table.
- P-5. About N/5 workers, 4 to 6 items each; above 45 items, sub-batches of at most 9.
- P-6. `external-research` Mode C batches about five sources per sub-agent.
- P-7. `check_items_per_worker` guards the rule.
- P-8 (replacing P-3, which put the read list in the task-folder-only `parent_artifact_paths`). The read list is a new `must_read` input, echoed by `files_read`.
- P-9 (replacing P-4, whose list of restating files missed the USER_MEMORY template). This ADR supersedes ADR-0039 rules 1 and 2 in part, and every live surface that restated 15 to 25 follows.

# ADR-0238: Output tokens are charged to the task that used them, or recorded as null with a reason

- **Status**: Accepted; the rule ships as provisional decisions P-3, P-7, P-8, P-9 and P-10 of the 2026-09-28 e0-tokens-per-task task and awaits the maintainer's confirmation. Confirmed by the maintainer on 2026-09-28: each of those provisional decisions now has a locked D-N carrying `Confirms:` in the task's DECISIONS.md.
- **Date**: 2026-09-28
- **Tags**: outcome-ledger, output-tokens, e0, e1, e3, transcripts, attribution, measurement
- **Supersedes in part**: [ADR-0236](./0236-subagents-route-by-role.md), for the sentence of its Decision that records output tokens per model "when a usage source exists, and null when it does not". A source that exists now yields null when it cannot attribute the task's tokens or cannot count them, and the line says why. The rest of ADR-0236 stands.

## Context

- ADR-0236 added `output_tokens_by_model` to the outcome line as experiment E0 of the parallel-work research, so that E1 (model and effort per step) and E3 (two tasks at once) could compare tasks. Its `claude-code` reader summed every assistant message whose timestamp fell inside the task's window. ADR-0236 named the limit itself: the window is a time range, not an attribution.
- The limit bit on the first two tasks that used it. On 2026-09-28, 2026-09-28_background-session-attended-chain and 2026-09-28_model-effort-by-role ran at the same time as background sub-agents of one session. Their outcome lines recorded 40,627 and 45,366 Opus output tokens (plus 335 Sonnet each). Each count held the dispatching session's own output (29,020 and 32,516 tokens, 71 and 72 percent) and the other task's agents. E1 and E3 cannot use numbers like that.
- The candidate signals were measured on those two tasks' transcripts, aggregate only. The line's `cwd` does not separate them: the background task's agent wrote the main checkout path on 151 of its 157 in-window lines, the same path its dispatcher wrote, because its worktree was made by hand. `gitBranch` is the launch branch (`main` on every line). The task names in each agent's own tool calls do separate them: of the six sub-agent transcripts in the windows, each names exactly one of the two tasks, and only the dispatching session names both. Each sub-agent's `agent-<id>.meta.json` names its dispatcher in `parentAgentId`.
- The same measurement found a second defect. A sub-agent transcript written by Claude Code 2.1.280 or later keeps only a message-start snapshot for most messages; the line carrying the final count (the one with a `stop_reason`) is missing. Across 368 sub-agent files, 1,150 of 10,679 messages from 2.1.280 on have a final line, against 2,203 of 2,256 before it. Main-session transcripts are final on 6,703 of 6,704 messages. A snapshot reads 5 output tokens on a message that holds a whole tool call, so the old reader's sub-agent share was a floor off by an unknown factor per task.

## Decision

The `claude-code` reader charges a transcript to the task being closed only when the transcript's own tool calls, or those of the agent that dispatched it, name that task and no concurrent task, and it records a count only when every attributed message carries its final line. Otherwise `output_tokens_by_model` is null and the new `output_tokens_null_reason` says why.

- One transcript file is one agent: the session, or one sub-agent. A name counts when it appears whole anywhere in a tool call's input: the task folder in a path, the `task/<task>` branch, or a mention in a command or in text the agent writes.
- A concurrent task is another task folder under any project of the same `projects/` directory whose own `wos:write` window overlaps this task's window. A folder under `active/` is still running, so its window stays open. A folder with no header is never concurrent.
- An agent that names no task takes its dispatcher's verdict (`parentAgentId`, else the session). An agent that names this task and a concurrent one is ambiguous and counts for neither task; its tokens are never split.
- Each message belongs to the window it started in, counts once at its largest count, and must have a line with a `stop_reason`. One attributed message without one makes the whole count null.
- `output_tokens_null_reason` is a string exactly when the count is null, `no usage source passed` included. `output_tokens_source` keeps its rule and names how many transcripts were counted and how many were excluded.
- `templates/OUTCOMES.schema.md` holds the rule; `scripts/compute-task-outcome.py` implements it; `scripts/tests/test-compute-task-outcome-usage.sh` pins it. `task-close` passes `--usage-source` as before.

## Consequences

### Positive

- Two tasks that run at once no longer share tokens. Rerun on the two archived tasks, the reader charges each only with its own agents, and the dispatcher's output goes to neither.
- A null says why. E0's pass metric counts filled lines, and a reader can now tell "no source" from "could not attribute" from "could not count".
- The reader never records a snapshot sum as a total.

### Negative

- Every task whose work runs in sub-agents on Claude Code 2.1.280 or later records null. Both archived tasks become null (83 of 89 and 224 of 233 attributed messages have no final count). E1 cannot measure sub-agent work from transcripts; it needs another usage source through the `json` adapter, or its arms run in main sessions.
- The dispatching session's output is charged to no task when it runs two at once. Orchestration cost disappears from per-task numbers in exactly the setup E3 tests.
- An agent that reads any task still in `active/` during the window is excluded as ambiguous. Stale folders in `active/` make that more likely.
- A concurrent task in another task repository's `projects/` tree is invisible to the reader.

### Neutral

- Lines already in `OUTCOMES.jsonl` stay as written (append-only). Their `output_tokens_source` says `not filtered by task`, which marks them as window totals.
- The `json` adapter is unchanged: whoever writes the file owns its attribution.

## Alternatives considered

### Alternative 1: attribute by the line's `cwd`

- One worktree per task, so the path would name the task.
- Rejected on the data: a hand-made worktree leaves the agent's `cwd` at the main checkout (151 of 157 lines), the same as its dispatcher's. The agent id inside a harness worktree's name fails the same case.

### Alternative 2: split the dispatcher's tokens between the tasks it ran

- Evenly, or by the number of agents per task.
- Rejected because nothing in the transcript says which task a given orchestration turn served; any split is a guess recorded as a measurement.

### Alternative 3: record the snapshot sum as a lower bound

- Keeps the field filled for sub-agent work.
- Rejected because E1 compares these numbers across tasks, and a floor off by an unknown factor per task reads like a total once it is in the ledger.

### Alternative 4: carry the reason in `output_tokens_source`

- No new field.
- Rejected because the schema promises that field is null exactly when the count is, and a reader keyed on that would read a reason as a source.

### Alternative 5: look for concurrent tasks in the same project only, up to each folder's last header

- Fewer folders read, fewer agents excluded as ambiguous.
- Rejected because it misattributes: a concurrent task whose last header predates the window, or that lives in another project, is never searched for, and its agents fall through to a dispatcher that names only the task being closed. The slice's fixture reproduced it (the closing task got {model-big: 10600, model-small: 149} instead of its own {model-big: 900, model-small: 80}).

## References

- `templates/OUTCOMES.schema.md` (`### Reading output tokens per model`); `scripts/compute-task-outcome.py` (`usage_from_claude_code`, `concurrent_tasks`, `agent_node`); `scripts/tests/test-compute-task-outcome-usage.sh` (cases 13 to 22).
- [ADR-0236](./0236-subagents-route-by-role.md) (the E0 field); [ADR-0235](./0235-agent-replaces-its-own-provisional-decision.md) (the replaced provisional decisions behind P-7, P-9 and P-10).

## Notes

- The choices the maintainer has not confirmed are the task's provisional decisions: P-10 (attribution and concurrency scope), P-7 (the dispatcher counts for neither task), P-3 (a non-final count nulls the field), P-9 (the reason field) and P-8 (this ADR).
- The plan went through three blinded review rounds before approval. The first two corrected the impact labels of the attribution and field decisions and asked for this ADR; the concurrency scope was widened after the slice's own fixture showed the narrower one misattributing.

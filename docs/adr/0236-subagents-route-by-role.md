# ADR-0236: Dispatched sub-agents route by role, through one table

- **Status**: Accepted; the choices D-4 and D-5 left open ship as provisional decisions of the 2026-09-28 model-effort-by-role task (P-1, P-3, P-4, P-8, P-9, P-10, P-11) and await the maintainer's confirmation. The output-token sentence of the Decision is superseded in part by [ADR-0238](./0238-output-tokens-attributed-by-task-name.md): the transcript reader attributes tokens to the task by name and records null, with a reason, when it cannot attribute or count them. Confirmed by the maintainer on 2026-09-28: each of those provisional decisions now has a locked D-N carrying `Confirms:` in the task's DECISIONS.md.
- **Date**: 2026-09-28
- **Tags**: model-routing, effort, sub-agents, dispatch-role, fan-out, review, verification, outcome-ledger, multi-tool
- **Supersedes in part**: [ADR-0004](./0004-capability-routing.md), for the sub-agents a command dispatches: a command now names their dispatch role, and Fhorja maps the role to a model and an effort instead of leaving the mapping to the consumer. Handoff lines stay vendor-neutral, as ADR-0004 decided. [ADR-0034](./0034-substrate-peers-and-worker-contract.md), for its J.3 tier-aware dispatch: a worker's tier is no longer a model SKU in the command's frontmatter.

## Context

Opus produced 95.7 percent of the output tokens across the eleven Fhorja sessions that recorded a final cost checkpoint between 2026-08-29 and 2026-09-28, and Sonnet 1.2 percent (the parallel-work research task, note 02). That does not prove waste. It does show that nothing routes by step: `wos/model-routing.md` picks one model per task from the escalations `TASK_STATE.md` records, and its only effort column is for Codex and marked unvalidated.

Two older decisions shaped the gap. ADR-0004 kept model names out of command outputs so the repository would survive model churn and serve every harness; the consumer maps `LOW`, `MEDIUM` and `HIGH` to a model. ADR-0034 then introduced tier-aware dispatch for fleets, and the tiers it used were model SKUs written into each fleet's frontmatter (`workers[].tier: claude-sonnet-5`) and into the worker contract's input envelope. So the rule said commands never name a model, while seven commands and two shared blocks did, and the SKUs had to be swept by hand every time the vendor lineup moved.

Claude Code now lets a dispatch choose both levers. A Workflow `agent()` call takes a per-call `model` and `effort`; the `Agent` tool takes a per-call `model`; a subagent definition takes `model` and `effort` in its frontmatter (code.claude.com/docs/en/sub-agents, read 2026-09-28). Codex agents take a per-agent `model` and `model_reasoning_effort` (`wos/sub-agent-orchestration.md`, primitives table). Cursor documents no per-subagent effort field.

On 2026-09-28 the maintainer locked D-4 of the parallel-work research: commands name a role, mechanical or judgment, for each sub-agent they dispatch, and the role maps to a model and an effort in one table, never a fixed SKU inside a command. He locked D-5 in the same pass: review and verification fan out read-only workers by default, under 10 agents, with one writer. D-2 puts this front first and makes experiment E1 the check on it.

## Decision

Every sub-agent a Fhorja command dispatches carries a dispatch role, `mechanical` or `judgment`, and the command names the role, never a model or an effort. `wos/model-routing.md ## Dispatch roles` is the one table that maps each role to a Claude Code model and effort, a Codex effort, and the degradation for a harness with no per-agent lever. Review and verification split three or more independent read-only units across `judgment` workers by default, at most nine at once, with the dispatching command as the only writer. Task closure records output tokens per model on the outcome line when a usage source exists, and null when it does not.

- `judgment` covers the plan, the `approve-plan` review, every review and verification verdict (an atom-audit row included), and cross-item synthesis. A judgment dispatch never takes the mechanical row, and a harness that cannot honor the role inherits the session model rather than a weaker one.
- `mechanical` covers reading, extraction, generation from an approved input, and execution of an approved slice.
- Effort follows the dispatch path. A Workflow `agent()` call takes the role's model and effort per call. The `Agent` tool takes a per-call model and no effort, so an Agent-tool dispatch inherits the session effort; a session that dispatches `judgment` work runs at the judgment effort or above, and the dispatching command writes `effort: inherited from session` in its transcript.
- The fleets declare `workers[].dispatch-role` in place of `workers[].tier`, and the worker contract carries `dispatch_role` in place of `worker_tier`. A fleet's own `suggested-model` stays at or above the model its workers' role resolves to. That rule binds worker-contract fleets only; a command that makes a single dispatch, such as `approve-plan` sending its plan to an Opus reviewer, runs the reviewer above itself on purpose.
- `scripts/lint-commands.sh` refuses a `tier:` line inside a `workers:` block, a `dispatch-role:` value the table does not define, a `claude-` model id anywhere in a command or shared block except its `suggested-model:` line, and a model family name attached to workers or sub-agents in command prose.
- A command's own `suggested-model` frontmatter, the hint for the session that runs it, is not a dispatch and is unchanged.
- Handoff lines stay vendor-neutral. `Work complexity` keeps its four values and the Handoff block keeps its shape.
- The rule text lives in `WORKFLOW_OPERATING_SYSTEM.md` (`### Work complexity (capability routing)` and `## Parallel workflow`); this ADR records why.

## Consequences

### Positive

- One table to update when the vendor lineup moves, instead of seven frontmatter blocks and two shared blocks.
- Mechanical work can run on a cheaper model and a lower effort, which is the hypothesis E1 tests, without touching the plan or the review.
- Review and verification get independent reads of disjoint units by default, which is the shape where parallel reads are safe: the documented failure mode is concurrent writers, and there is one writer.
- E0 gives E1 its measurement: output tokens per model per task, recorded where the other outcome fields already live.

### Negative

- Cost goes up in three places. The verify-against-rubric-fleet workers move from Sonnet to Opus, the atom-audit-fleet workers from Haiku to Opus, and review-hard and security-review fan out on a diff with three or more file groups. Each is a provisional decision with `Impact: high`.
- The mechanical row is a hypothesis until E1 runs. A slice worker at medium effort may miss what a high-effort one would catch, and feature-library-scout's per-problem pick sits close to a judgment. implement-fleet stays a pilot (D-6), which limits the exposure.
- On the `Agent` tool Claude Code has no per-call effort, so an Agent-tool dispatch applies the model and inherits the session effort, and says so. Generated agent definitions would close that gap and are left to a later task.
- A per-task token count read from transcripts is a window, not an attribution: two tasks in one session at the same time share lines. The branch filter narrows it when the task recorded a branch.

### Neutral

- `--consistency N` stays opt-in. It repeats one review N times rather than splitting it, and E2 is the experiment that would move it.
- Mode C `Delegate now:` directives keep their shape.

## Alternatives considered

### Alternative 1: name the SKU per dispatch

- `model: claude-sonnet-5` written at each dispatch site.
- Rejected by D-4 itself, and for the reason ADR-0004 gave: every lineup change becomes a sweep across command files, and a Codex or Cursor user reads a model they cannot select.

### Alternative 2: keep the per-task routing and add an effort column for Claude

- One model and one effort per task, chosen at `task-init` from the escalations.
- Rejected because the measured imbalance is inside a task: the same session plans, reviews and runs read workers on one model. A per-task choice cannot send the read workers down without sending the plan down with them.

### Alternative 3: three roles, with a Haiku extraction row

- `extraction` on Haiku 4.5 below `mechanical`, which is what the old tier heuristic had.
- Not taken now. E1's treatment arm is Sonnet at medium, and Haiku 4.5 has a retirement date inside the table's next cadence window. A third row can be added when a measurement asks for it; commands would not change.

### Alternative 4: generate agent definitions per role

- `build-agent-skills.sh` emits one Claude Code agent file and one Codex agent file per role, so effort applies on every dispatch path.
- Deferred, not rejected. It adds a generated surface and an install destination, and D-4 is satisfied without it. It is the natural next step if Agent-tool dispatches show the inherited effort matters.

## References

- `wos/model-routing.md` → `## Dispatch roles` (the table).
- `WORKFLOW_OPERATING_SYSTEM.md` → `### Work complexity (capability routing)` and `## Parallel workflow` (the rules).
- `wos/sub-agent-orchestration.md` → `## Role-aware dispatch protocol`; `commands/_shared/worker-contract.md`; `commands/_shared/orchestrator-bootstrap.md`; `templates/ORCHESTRATOR_COMMAND.template.md`.
- `scripts/compute-task-outcome.py` and `templates/OUTCOMES.schema.md` (the `output_tokens_by_model` field); `scripts/tests/test-compute-task-outcome-usage.sh`.
- code.claude.com/docs/en/sub-agents and code.claude.com/docs/en/workflows, read 2026-09-28.

## Notes

- The choices the maintainer has not yet confirmed are the task's provisional decisions: the two rows and their values (P-1), the scope of the no-SKU rule (P-3), what fan-out by default means (P-4), which dispatch gets which role (P-8), effort on harnesses without a per-call lever (P-9), the E0 field (P-10), and the Mode C rules naming the role while the directive keeps its shape (P-11).
- The plan behind this ADR went through three blinded review rounds before approval; the first two sent it back for the atom-audit role, the missing single dispatches, unresolvable evidence and a too-narrow lint check.
- If E1 fails, change the mechanical row in the table. No command changes.

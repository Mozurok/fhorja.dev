# ADR-0032: Mode C parallel-fanout handoff directive

- **Status**: Accepted
- **Date**: 2026-06-04
- **Tags**: handoff-contract, sub-agent-orchestration, parallel-fanout, mode-c, multi-repo

## Context

The WOS Handoff contract (ADR-0011 shared blocks + `## Global output contract` in WORKFLOW_OPERATING_SYSTEM.md) defined two modes:

- **Mode A** (Compact, intra-session) -- the default `Run now / Mode / Work complexity / Reason` lines.
- **Mode B** (Full, cross-session) -- Mode A plus `Resume context` for session breaks.

Both modes terminate the turn with a single recommended next command for sequential execution. They do not express *parallel sub-agent dispatch*, even though the WOS already documents sub-agent orchestration in `wos/sub-agent-orchestration.md` and ADR-0022.

Three pressures motivate adding a third mode:

1. **Anthropic Dynamic Workflows (2026-05-28)** ship native fan-out to up to 1000 sub-agents with 16 concurrent workers. The pattern is mainstream in agentic tooling.
2. **Devin Managed Devins (2026-03-19)** solve the context-inflation problem with the same orchestrator-workers shape: parent dispatches read-only workers, integrates summaries.
3. **Bruno's full-stack workflow** (per Q1 answer to 2026-06-03 plan questions) means multi-repo coordination is frequent. Parallel per-repo analysis is the natural shape; sequential per-repo work wastes wall-clock.

ADR-0022 left the door open with `### Edge cases` -> "Why no Delegate now: Handoff directive (yet): changing the Handoff contract requires a stronger signal of real use-case friction." The signal arrived: D.1 audit (2026-06-04) identified `implement-approved-slice`, `slice-closure`, `where-we-at` as multi-repo extensions, and Bruno's typical FE+BE pattern means `code-locate` and `external-research` regularly hit fan-out triggers.

## Decision

Adopt **Mode C -- Parallel fanout** as a third handoff mode. Mode C is a within-turn dispatch directive (not a turn-ending handoff). The parent command emits the directive, sub-agents run in isolated contexts, parent waits, integrates summaries, then resumes Mode A or Mode B for the next turn-ending handoff.

Mode C triggers (any one is sufficient):

- `code-locate` against a codebase with >1000 files
- `external-research` with >3 captured sources to compare
- `repo-consistency-sweep` with a diff touching >10 files
- multi-repo task where independent per-repo analysis can run in parallel

Mode C format:

```text
Delegate now: <comma-separated sub-agent invocations or pattern descriptions>
Mode: Plan (parent) + Explore (workers); use Claude Code Task tool, Cursor /worktree, or equivalent
Work complexity: matches parent slice
Reason: <why fanout vs inline>
Merge back: <where the parent integrates the summarized results>
```

Mode C does NOT replace Mode A or Mode B; it is an intra-turn directive. After integrating sub-agent summaries, the parent emits the standard Mode A or Mode B handoff for the next step.

Enforcement is in command files declaring Mode C eligibility:

- `commands/code-locate.md` -- declares Mode C trigger at >1000 files.
- `commands/external-research.md` -- declares Mode C trigger at >3 sources.
- `commands/repo-consistency-sweep.md` -- declares Mode C trigger at >10 files.

Other commands MAY adopt Mode C in future iterations when their use case naturally fans out. Single-agent default remains Mode A.

## Consequences

### Positive

- Parent-context inflation reduced for high-fanout tasks. A `code-locate` across 5000 files no longer requires the parent to hold all results inline; sub-agents summarize.
- Wall-clock latency cut for naturally parallel work (multi-repo per-repo analysis, multi-source research synthesis).
- Aligned with Anthropic Dynamic Workflows and Devin Managed Devins patterns, reducing the gap between WOS and external-tool capabilities.
- Multi-repo tasks (per D.1 audit) get a native shape for "do FE and BE analysis in parallel, then merge".

### Negative

- Mode C costs more tokens than Mode A or Mode B in absolute terms: N sub-agents each consume their share of context. The benefit is reduced parent inflation, not lower aggregate cost. Acceptable when N x small-context is cheaper than one big-context parent for the same task.
- Sub-agent isolation means parent loses visibility into intermediate sub-agent state. Only the summary survives. Acceptable when summarization is faithful.
- Tool surface (Claude Code Task, Cursor /worktree, etc.) is vendor-specific. The Handoff directive is vendor-neutral, but execution depends on the host. Document per-tool primitives in `wos/sub-agent-orchestration.md`.

### Neutral

- Adopting Mode C does not change which commands run sequentially. The default remains Mode A. Mode C is opt-in per command.
- Mode C does not introduce new task-memory artifacts. Sub-agent summaries land in the parent's normal output, which then writes the usual TASK_STATE.md updates.

## Alternatives considered

### Alternative 1: Keep parallel work inside individual commands (no Handoff directive)

- Each command handles its own internal parallelism (e.g., `code-locate` spawns workers internally).
- Rejected: hides the parallelism from the Handoff contract, making it harder to audit "did this command actually fan out?" and harder for tools to optimize accordingly. ADR-0011 shared blocks discipline prefers explicit contracts over implicit behavior.

### Alternative 2: Add a fourth axis to the existing Mode A / Mode B (e.g., "Mode A with fanout")

- Rejected: explodes the mode matrix; tools have to parse "Mode A vs A+fanout vs B vs B+fanout" rather than three orthogonal modes.

### Alternative 3: Define fanout as a separate command class entirely (e.g., orchestrator commands)

- Rejected: too heavy. Most commands are not orchestrators; the few that fan out can declare it inline without adding a class hierarchy.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` -> `## Global output contract` -> `### Adaptive handoff` -- normative definition updated to include Mode C.
- `wos/sub-agent-orchestration.md` -- per-tool primitives (Claude Code Task, Cursor /worktree, etc.).
- ADR-0022 (Sub-agent orchestration topic) -- this ADR closes the open question from ADR-0022 `### Edge cases`.
- ADR-0011 (Shared canonical blocks) -- discipline that motivates explicit Handoff contracts.
- Anthropic Dynamic Workflows (2026-05-28) -- external reference for the fanout pattern.
- Cognition Labs Devin Managed Devins (2026-03-19) -- external reference for orchestrator-workers shape.

## Notes

Mode C is a within-turn directive. A parent that emits Mode C MUST also emit a Mode A or Mode B handoff for the next turn-ending step after integrating sub-agent results. Without that subsequent handoff, Mode C alone is an incomplete output.

D.3 of WOS improvement plan 2026-06-03 will extend `code-locate`, `external-research`, and `repo-consistency-sweep` to declare Mode C eligibility and document the integration pattern in each command's Operating rules.

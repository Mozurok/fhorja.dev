# ADR-0042: Waves-Aware Routing, Long-Running Progress Visibility, and Terminal Closure Routing

- **Status:** Accepted
- **Date:** 2026-06-13
- **Tags:** routing, fleet-orchestration, handoff-contract, progress-visibility, closure, observability, adr-amendment

## Context

ADR-0041 gave the workflow a parallel slice executor (`implement-fleet`) and the file-scope disjointness gate that makes it safe. `implementation-plan` was extended to emit per-slice `Scope` and `Depends-on` plus a computed `## Execution waves` section, so a plan now carries the exact data needed to decide whether parallel execution is possible. ADR-0041 itself names the remaining risk in its Consequences: "Two valid execution shapes now exist, which increases routing surface."

A 2026-06-12 lived session (a greenfield React Native POC built end to end through the workflow) confirmed that the routing surface was never wired, in three distinct ways:

1. **The fleet was unreachable from the routing graph.** `approve-plan` hard-codes its handoff to `implement-approved-slice` regardless of whether the plan it just locked contains parallelizable waves. `implement-fleet` had exactly one inbound routing edge in the whole system (the `implementation-plan` retrofit mode). The two commands that see the approved multi-slice plan at decision time pointed only at the sequential path. When the operator wanted speed, they had to ask for parallelism in their own words, and the model then hand-authored a raw Workflow script outside the command layer, bypassing slice notes, wave computation, and `TASK_STATE.md` writes. The dependency data ADR-0041 produces was being computed and then ignored at the one moment it mattered.

2. **Long-running work was indistinguishable from a hang.** A fleet ran for 73 minutes of legitimate work (a worker debugging an order-dependent test failure) and surfaced no progress. The operator read the silence as a stall and had to intervene. Nothing in the workflow defined a progress-visibility contract: there were zero references to heartbeats, interim status, or stall detection anywhere in the spec or commands, and `implement-fleet`'s convergence barrier was a silent 15-minute wait that never referenced `scripts/monitor-fleet-progress.sh`, the monitor built for the very inbox it writes.

3. **Closure was left to operator memory and silently decayed.** After slices completed, no `slice-closure`, `sync-task-state`, `where-we-at`, or `task-close` ran. `implement-approved-slice` even contradicted itself: its body says "prefer `/sync-task-state` after execution" while its Next list omits `sync-task-state` entirely, and no command gives the final slice of a plan a terminal routing edge. The session ended with work uncommitted and `TASK_STATE.md` stale, defeating the workflow's core promise of resumability. A prior task (the 2026-05-26 friction-reduction work, from a different transcript) had already recorded the same closure-abandonment pattern, so this is systemic.

The common thread: the workflow specified HOW each capability works once invoked, but not WHEN the agent should reach for it. The fix is to move that decision out of operator memory and into the artifacts and contracts the agent already reads.

## Decision

Three coupled changes to the continuation interface, all sharing one canonical rule so they stay consistent.

1. **Waves-aware routing promotion.** The canonical routing rule, stated verbatim wherever execution is routed (`approve-plan`, `implement-approved-slice`, `wos/entry-points.md`, and the sequencing heuristics): *when the approved plan's `## Execution waves` section shows a remaining wave of size 2 or more whose slices declare `Scope` and `Depends-on`, route to `implement-fleet`; otherwise route to `implement-approved-slice`.* `approve-plan` evaluates this when it locks the plan and emits the matching handoff; `implement-approved-slice` re-evaluates it on slice completion for the remaining waves. The sequential path stays the default and the fallback for chains, exactly as ADR-0041 framed it.

2. **Long-running progress-visibility contract.** Any single execution step expected to exceed about 10 minutes states its expected duration up front and emits interim status (file-completion ticks, per-wave dispatch lines, or background-task progress) instead of going silent. For fleets specifically, `implement-fleet` surfaces a per-wave dispatch line, references `scripts/monitor-fleet-progress.sh`, and applies an explicit stall rule: when a wave runs past a stall threshold with no worker transition, the orchestrator surfaces a status summary (running workers, elapsed time, last tool summary) rather than waiting silently for the barrier timeout. This does not weaken the ADR-0041 integration gate (`partial_ok` stays false); it adds a reporting duty during the existing barrier.

3. **Terminal closure routing.** Closure routing is made terminal-safe rather than memory-dependent: `implement-approved-slice` adds `sync-task-state` to its Next list for the LOW/MEDIUM inline-close path (resolving the body-vs-list contradiction), and when the completed slice is the last in the plan, the handoff routes to `where-we-at` (multi-slice) or `task-close` (otherwise) instead of dead-ending. This stays within the Adaptive-handoff model (the successor to ADR-0002): the agent emits a sharper suggested next step; it does not silently auto-chain.

Qualifications:

- This ADR sharpens the suggested-next-step edge; it does not introduce silent auto-execution. The operator still approves at gates.
- The verbatim canonical rule (change 1) is itself a coupling artifact in the ADR-0041 sense: a normative sentence that must read identically across several files. File-scope disjointness does not capture it, so edits that touch the rule are coordinated under a single writer rather than parallelized. This extends ADR-0041 Rule 2's coupling-artifact list (migration, lockfile, codegen, barrel export) with "a normative rule that must be stated verbatim in multiple files."

## Consequences

### Positive

- The fleet becomes reachable at the moment the decision is made: `approve-plan` offers it the instant a parallelizable plan is locked, so the operator never has to invent parallelism or drop to a raw Workflow script.
- Long-running work stops reading as a hang. The operator can tell "working" from "stuck" without polling, which removes the most common false-alarm interruption.
- The last slice of every plan has a terminal routing edge, so the lifecycle closes by routing rather than by memory; resumability is preserved even under throughput pressure.
- The routing decision lives in the plan artifact (`## Execution waves`), mirroring the multi-agent-orchestration pattern of putting scaling rules in the prompt rather than trusting model recall.

### Negative

- Routing surface grows further: every execution-routing site now carries the wave-size conditional. The mitigation is the single verbatim rule reused everywhere, so there is one sentence to change, not five divergent ones.
- The progress-visibility contract adds output volume to long runs. The threshold (about 10 minutes) keeps it off short steps.
- More sites now reference `implement-fleet`, increasing the cost of any future rename. Accepted: the registries and lint drift-guards already enforce command-name integrity.

### Neutral

- The promotion only fires when the plan genuinely has a wave of width 2 or more with declared scopes; cohesive chain-shaped work is unaffected and stays sequential.
- This ADR is about routing and visibility, not about the disjointness mechanics, which remain exactly as ADR-0041 defined them.

## Alternatives considered

### Alternative 1: Auto-chain the next command instead of suggesting it

- After `approve-plan`, automatically invoke `implement-fleet` with no operator turn; same for closure after the last slice.
- Rejected: it contradicts the Adaptive-handoff model (the ADR-0002 successor), which keeps the operator at the gates. Silent auto-execution of a multi-worker fleet is exactly the kind of hard-to-reverse action that should stay behind an approval. Sharpening the suggestion captures most of the value without removing the gate.

### Alternative 2: A deterministic hook that blocks turn-end until TASK_STATE.md is fresh

- A Stop or PostToolUse hook compares `TASK_STATE.md` mtime against the latest artifact mutation and refuses to end the turn when state is stale.
- Deferred, not rejected: it is the stronger guarantee for closure, but it is a harness-level mechanism (Claude Code settings) orthogonal to the routing contracts this ADR fixes. Recorded as a follow-up so this ADR stays about the WOS contracts.

### Alternative 3: One ADR per change (three ADRs)

- Split waves-aware routing, progress visibility, and terminal closure into separate records.
- Rejected: all three amend the same continuation interface (the handoff and the routing graph) and were motivated by the same lived session. One record keeps the rationale searchable in one place; the verbatim canonical rule (shared by changes 1 and 3) would otherwise be split across records.

## References

- ADR-0041: parallel slice execution and the file-scope disjointness gate (the capability this ADR makes reachable; this ADR extends its Rule 2 coupling list).
- ADR-0040: single-writer-per-folder (the parent doctrine).
- ADR-0038, ADR-0039: Workflow tool as the parallel primitive and its empirical batch sizing.
- ADR-0002: Paste-this-next (superseded by Adaptive handoff); this ADR works within that successor model.
- `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` (the long-running progress-visibility subsection) and `## Command roles` (the mirrored routing edges).
- `commands/approve-plan.md`, `commands/implement-approved-slice.md`, `commands/implement-fleet.md`, `commands/implementation-plan.md`: the operationalizing command files.
- `wos/entry-points.md`, `wos/cross-cutting-workflow-guardrails.md`, `wos/sub-agent-orchestration.md`: the routing and orchestration surfaces.
- 2026-06-12 lived greenfield session (the empirical motivation: fleet unreachable, 73-minute silent run, closure decayed).

## Notes

The triggering session was a personal-workflow dogfood: the operator built a throwaway POC entirely through the workflow and hit all three gaps in one sitting. The same closure-abandonment pattern had been recorded once before from an unrelated transcript, which is what moved it from "incident" to "systemic" and justified an ADR rather than a CHANGELOG note. Revisit if the deterministic staleness hook (Alternative 2) lands, since it would make change 3's routing edge a backstop rather than the primary guarantee.

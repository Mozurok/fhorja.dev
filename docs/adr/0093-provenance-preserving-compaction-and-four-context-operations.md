# ADR-0093: Provenance-preserving compaction and the four context operations

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: context-engineering, compaction, provenance, compact-task-memory, context-budget, four-operations, dogfood-driven, currency-adoption, grounded-2026

## Context

A 2026-07-11 currency scan of the agentic-engineering frontier (captured in `projects/bmazurok__my-work-tasks/REFERENCES.md`, the 2026-07-11 section) found the WOS broadly aligned with the field and ahead of it on provenance, with three genuine gaps worth adopting. This ADR records the first, the context-engineering gap.

The 2026 literature converged on treating the context window as a constrained resource operated on by four moves: write (persist outside the window), select (retrieve only what is relevant now), compress (summarize to save tokens), and isolate (give sub-tasks a clean context). Reported effect sizes are large: context editing alone around +29% on a long-horizon task, +39% paired with a memory tool, and an 84% token reduction on a 100-turn eval (the tianpan context-engineering entry; Context Engineering 2.0, arXiv 2510.26493). The subagent-isolation pattern has workers consume 10k+ tokens for deep work but return 1-2k token condensed summaries so the orchestrator context stays bounded.

The WOS already implements all four operations, but had not named them, so the doctrine was implicit and the mapping from each command to its operation was not legible. Separately, `compact-task-memory` was lossy-but-git-reversible: a dropped fact was recoverable from a git blob, but the command did not cite the trace-level provenance (the append-only `.wos/VERIFICATION_LOG.jsonl` entry, with owner, run_id, ts, and sha, that originally wrote the fact's section). "Provenance-preserving compaction" is the 2026 refinement that makes compression safe to run mid-flight on a long session, because nothing becomes untraceable.

## Decision

**(a) Name the four context operations in doctrine.** `wos/context-budget.md` gains a "four context operations" section mapping write, select, compress, and isolate to their existing WOS mechanisms: write is the substrate (`TASK_STATE.md`, `DECISIONS.md`, `LEARNINGS.md`, `REFERENCES.md`, and the append-only VERIFICATION_LOG); select is the retrieval path (`rank-learnings.sh` per ADR-0071, contextual retrieval per ADR-0018, `code-locate`, `code-context-map`); compress is `compact-task-memory`; isolate is the fleet worker contract (ADR-0038, typed `StructuredOutput` from an isolated context). The four operations are the vocabulary; the existing per-layer compaction strategy is how each operation applies to each of the six layers.

**(b) Provenance-preserving compaction.** `compact-task-memory` SHALL treat the `.wos/VERIFICATION_LOG.jsonl` audit chain as append-only: it SHALL NOT rewrite, prune, or summarize the log. The `## Compaction history` entry gains a `Provenance of dropped facts` field that SHALL cite the run_id(s), or owner plus section, from the VERIFICATION_LOG that originally wrote the dropped entries, so a dropped fact traces to its origin at the audit-chain level, not only via a git blob.

## Consequences

- Mid-flight compaction on a long session is safe: dropped prose is always traceable to its origin write, so aggressive compaction no longer risks silently losing where a fact came from.
- The context-engineering doctrine is legible: each command can be described by the operation it performs, and the WOS's alignment with the 2026 frontier is explicit and grounded in captured references.
- Additive and model-agnostic: no command contract changes, no new command, no model names in normative text. `compact-task-memory` keeps its lossy-on-prose behavior; the addition is the provenance citation and the doctrine framing.
- The other two scan gaps (a plan-adherence eval over the VERIFICATION_LOG trace, and an OWASP Agentic Top 10 coverage map) are separate follow-up waves of the same currency-adoption task, each grounded in its own captured reference.

# ADR-0022: Sub-agent orchestration topic

- **Status**: Accepted
- **Date**: 2026-05-18
- **Tags**: orchestrator-workers, sub-agents, multi-tool-portable, docs-only-pattern, deferred-enforcement

## Context

Anthropic's "Building Effective Agents" (Dec 2024) names five canonical agent patterns: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer. The WOS has explicitly adopted three (prompt chaining via Handoff; routing via `what-next`; evaluator-optimizer via `self-critique-and-revise` per ADR-0021). Orchestrator-workers stayed implicit until slice 11.

Multiple AI tools the WOS targets provide sub-agent primitives in their own surfaces: Claude Code's `Explore` / `Plan` / `general-purpose` / `Task` API; Cursor agent mode; Codex agents; OpenHands; Goose. The WOS contract historically said nothing about WHEN to use these vs. stay inline. Three failure modes the silence creates:

1. **Inline work that should delegate**: broad codebase explorations pollute the main thread with raw file output. A sub-agent could return a summary while keeping the orchestrator's context clean (the Chroma `Context-Rot` finding from ADR-0012 applies here: degradation grows with input length even when below the stated window).
2. **Delegation that should stay inline**: small focused work dispatched to a sub-agent adds turnaround cost and breaks the conversation flow.
3. **Per-tool divergence**: Claude Code users (with the most mature sub-agent surface) delegate heavily; Cursor users delegate less. Without a WOS recommendation, behavior varies by tool, which contradicts the multi-tool architecture rule (ADR-0005).

D-8 (Wave 2 reassessment) trimmed slice 11 to docs-only: new lazy WOS topic + ADR; NO `Delegate now:` Handoff directive (deferred). The rationale is that promoting orchestrator-workers to a Handoff contract change requires stronger signal of real-use friction than we currently have. Documenting the pattern now establishes the shared mental model; future slices can introduce enforcement once usage data justifies it.

## Decision

The WOS adopts the orchestrator-workers pattern at the documentation layer:

1. **New lazy WOS topic** `wos/sub-agent-orchestration.md` documents:
   - When to delegate (4 canonical cases): broad codebase search; long-context summarization; bounded planning of a sub-problem; independent verification of a result.
   - When NOT to delegate (4 anti-patterns): one-file edit; routing decision; conversational continuation; trivial computation.
   - Per-tool primitives table: Claude Code, Cursor, Codex, Copilot, Gemini CLI, OpenHands, Goose.
   - Four-question checklist before delegating: (1) self-contained; (2) isolation benefit; (3) cost; (4) tool-set adequacy.
   - Pattern relationships with the other four canonical patterns.
   - Edge cases (sub-agent unavailable, budget exceeded, cross-sub-agent coordination).
   - Future evolution path (Handoff directive; per-tool detection; meta-command).
2. **WOS minimum-read map** points at the new topic for relevant contexts.
3. **No command edits**. The orchestrator-workers pattern stays contributor-driven; commands do not declare "delegates to" relationships. Adopting the pattern is a runtime choice by the model running the command, informed by the topic when it is loaded.
4. **No `Delegate now:` Handoff directive**. Changing the Handoff contract (currently `Run now:` is the only primary action verb) is deferred until real-use friction surfaces. ADR-0022 documents the criteria for promotion: a contributor or eval surfaces a case where staying inline produced materially worse output than delegating, and at least two tools in the WOS distribution support the sub-agent surface uniformly.
5. **Per-tool table is dated**. As of v0.2.x snapshot; contributors update via PR when a tool's sub-agent surface changes. The topic notes the dating explicitly.

## Consequences

### Positive

- **Shared mental model across tools**. A Cursor user and a Claude Code user read the same WOS topic and apply the same checklist. Multi-tool consistency strengthens (per ADR-0005).
- **Reduces context-rot risk on broad searches**. The Chroma `Context-Rot` finding (ADR-0012's motivation) is partially addressed: contributors who know to delegate broad searches keep their main thread cleaner, regardless of which tool they use.
- **Names a previously implicit pattern**. New contributors who read the Anthropic post and look for orchestrator-workers in the WOS find it explicitly documented.
- **Sets the criteria for future promotion**. If a future slice wants to add a `Delegate now:` Handoff directive, ADR-0022 names what evidence is needed.

### Negative

- **No enforcement**. Contributors who do not read the topic miss the pattern. Mitigation: the topic is lazy-loaded when relevant; the WOS minimum-read map points at it; contributors writing new commands will find it.
- **Per-tool table goes stale fast**. AI tooling evolves rapidly; the table will be out-of-date within months. Mitigation: dated language; updates via PR when a tool changes.
- **Promotes a partial pattern (orchestrator-workers without parallelization)**. The "Building Effective Agents" post pairs them; the WOS adopts one. Mitigation: explicitly named in pattern-relationships table; parallelization is documented as "not adopted, out of scope". Future slice can add parallelization if needed.

### Neutral

- The topic is one of seven lazy WOS topics. System layer surface grows by one. Reading cost amortized by cache.
- No new command in this slice; the command catalog remains at 37.

## Alternatives considered

### Alternative 1: introduce the `Delegate now:` Handoff directive in this slice

- Add `Delegate now:` as a third primary action verb alongside `Run now:`. Commands that delegate emit the new directive; tools that support sub-agents act on it.
- **Rejected per D-8**: changing the Handoff contract is high-impact (every command's output shape changes; every tool integration must adapt). Real-use friction not yet documented. Deferred until evidence justifies the cost.

### Alternative 2: per-tool integration code

- A script (or build adapter extension) detects which tool is in use and emits the right sub-agent invocation hint.
- **Rejected**: violates ADR-0005 multi-tool neutrality. The WOS stays markdown + bash; tool-specific integration lives in the tool's own adapter, not in the WOS.

### Alternative 3: skip the topic entirely; rely on each tool's own docs

- Documentation about Claude Code's sub-agents lives in Claude Code's docs; same for Cursor; etc.
- **Rejected**: misses the orchestrator-workers PATTERN, which is tool-agnostic. The four-question checklist applies regardless of tool. The WOS adding this layer is the value.

### Alternative 4: write a command (`delegate-to-sub-agent`) that orchestrates explicitly

- A new command that takes a sub-task description and emits the right invocation per tool.
- **Rejected**: premature. Sub-agent invocation is highly tool-specific; a generic command would be a thin shim. If real-use friction surfaces, this could be revisited as a `delegate-and-integrate` meta-command.

## References

- `wos/sub-agent-orchestration.md` (the lazy-loaded full topic; four-canonical-cases, four-anti-patterns, per-tool table, checklist).
- `WORKFLOW_OPERATING_SYSTEM.md` minimum-read map (points at the new topic).
- ADR-0002 (Paste-this-next contract; the Handoff format this slice does NOT modify).
- ADR-0005 (multi-tool architecture; the reason this slice stays docs-only and tool-neutral).
- ADR-0006 (lazy-load WOS pattern; the precedent for adding a lazy topic).
- ADR-0012 (context budget; names the layers this pattern operates on; orchestrator-workers helps the system layer keep cache hot).
- ADR-0021 (evaluator-optimizer via self-critique; the immediate predecessor; both are agent-pattern adoptions at the WOS layer).
- D-8 of `projects/bmazurok__my-work-tasks/active/2026-05-15_context-engineering-uplift/DECISIONS.md` (Wave 2 reassessment; trimmed this slice from S+command-edits to S+docs-only).
- Anthropic, "Building Effective Agents" (Dec 2024): the orchestrator-workers pattern; one of five canonical agent patterns.
- Anthropic, "Effective context engineering for AI agents" (Sep 2025): sub-agents as a context-engineering strategy.

## Notes

The "docs-only per D-8" pattern is a deliberate stop-short. The WOS often documents a pattern before enforcing it; the gap between documentation and enforcement is where contributors can experiment and surface friction. Future slices can promote any documented pattern to an enforced directive once the evidence justifies it.

Criteria for promoting orchestrator-workers to a `Delegate now:` Handoff directive:
- At least one eval scenario surfaces a case where staying inline produced materially worse output than delegating to a sub-agent.
- At least two tools in the WOS distribution support the sub-agent surface uniformly (current state: Claude Code is most mature; others vary).
- A contributor authors a draft PR for the Handoff contract change with explicit migration plan for the affected commands.

When all three criteria are met, a new ADR (numbered NNNN+1) supersedes this one with the Handoff contract change.

Future evolution beyond the directive (not planned now): parallelization pattern; orchestrator-of-orchestrators primitive; per-tool detection in build adapters.

# ADR-0012: Context budget as an explicit contract

- **Status**: Accepted
- **Date**: 2026-05-15
- **Tags**: context-engineering, frontmatter-contract, six-layer-model, falsifiable-contract

## Context

The WOS already practices context engineering implicitly. Lazy-loaded `wos/<topic>.md` files (ADR-0006) keep the system layer compact. The project / task / user memory split (ADR-0007 + the planned slice 05 of the context-engineering uplift task) separates persisted state by lifetime. Shared canonical blocks (ADR-0011) keep the tool layer DRY. The Handoff `Paste this next` contract (ADR-0002) keeps the task layer tight across turns.

But the framework was never named. Three failure modes accumulated as the catalog grew to 35 commands:

1. **Context choices were not falsifiable**. When a command was "too heavy", reviewers argued by gut rather than by which layer was overloaded. There was no shared vocabulary to point at.
2. **New-command authors had no rule of thumb**. Choosing what a new command should read and write was a judgment call without a checklist. Some new commands (e.g., earlier drafts of `external-research`) re-read state already in memory because the author did not know which layer was the right home.
3. **Cross-layer reasoning was inconsistent**. The lazy-load WOS pattern is a system-layer technique; project memory is a memory-layer technique; the Handoff `Paste this next` is a task-layer technique. These were all "good ideas" with no umbrella showing how they fit together.

The Anthropic `Effective context engineering for AI agents` post (Sep 2025) and the supporting research (Chroma `Context-Rot`, PwC `Don't Break the Cache`, Anthropic Contextual Retrieval) name a six-layer model: system rules, memory, retrieved docs, tool schemas, recent conversation, current task. Adopting that vocabulary inside the WOS gives the workflow a shared framework with the broader AI-engineering field.

## Decision

The WOS adopts the six-layer context model as an explicit contract:

1. **Six canonical layers**: `system`, `memory`, `retrieved`, `tools`, `history`, `task`. Names are locked; future renames require a new ADR superseding this one.
2. **Per-command frontmatter declaration**: every `commands/<name>.md` includes two YAML lists in its frontmatter:
   - `context-layers-consumed: [...]` (which non-baseline layers it reads)
   - `context-layers-produced: [...]` (which layers it writes via runtime artifacts)
3. **Universal baseline convention**: `system`, `tools`, and `task` are implicit for every command and are NOT listed in `consumed:`. Only `memory`, `retrieved`, and `history` are meaningful non-baseline values for `consumed:`. `produced:` accepts any of the six values but in practice is dominated by `memory` and `retrieved`.
4. **Empty lists are valid**: a command may produce nothing material (`produced: []` for pure routing); a command may consume nothing beyond baseline (`consumed: []` for `project-bootstrap`, which creates rather than reads).
5. **Lint enforcement**: `scripts/lint-commands.sh` validates that both fields exist on every command and that values are in the canonical set. Drift here is a hard fail.
6. **Lazy-loaded narrative**: the full framework (per-layer description, examples, compaction guidance, edge cases) lives in `wos/context-budget.md`. The compact stub in `WORKFLOW_OPERATING_SYSTEM.md ## Context budget` carries the lead definition and the frontmatter rule. Loaded only when designing new commands or diagnosing context overruns.

## Consequences

### Positive

- **Falsifiable context discussion**. "Command X consumes too much" becomes "command X reads three layers when only memory is needed", a precise claim a reviewer can check.
- **New-command authoring has a checklist**. Step 1 of writing a new command is choosing the layer values; the lazy file `wos/context-budget.md ## How to choose values for a new command` walks an author through it.
- **Lint catches contract violations**. A command that adds a new context source (e.g., starts reading a session-level history field) without updating its frontmatter fails the lint, surfacing the contract change.
- **Foundation for downstream slices**. Slice 02 (token budget) measures cost per layer; slice 03 (cache structure) relies on knowing which content is static system / tools and which is dynamic task; slices 04 and 13 (compaction, guardrails) operate per layer. None of these are possible without the explicit layer names.
- **Shared vocabulary with the AI-engineering field**. Contributors and beta testers (Phase 2) who read Anthropic's posts can map the WOS terms directly to the broader literature.

### Negative

- **35 commands need frontmatter additions**. The initial migration is mechanical but requires per-command judgment of which non-baseline layers are touched. Slice 01 of the context-engineering uplift task carries this cost.
- **Two more frontmatter fields**. The Agent Skills frontmatter grew with this addition. The fields are namespaced under WOS conventions and do not conflict with the open Agent Skills spec.
- **A new lazy-loaded WOS topic**. `wos/context-budget.md` joins `wos/command-roles.md`, `wos/multi-repo-support.md`, etc. The system layer's lazy-load surface area grows by one.

### Neutral

- The decision codifies a model the WOS was already implicitly using. Naming it does not change runtime behavior; it changes how contributors reason about it. Future commands that respect the layer model are now contract-bound; the lint enforces what was previously norms.

## Alternatives considered

### Alternative 1: leave the layers implicit, document only in WOS prose

- Add a narrative paragraph to `WORKFLOW_OPERATING_SYSTEM.md` describing the six layers; no frontmatter, no lint.
- **Rejected**: indistinguishable from the current state. The reason this ADR exists is that prose without enforcement does not survive 35 commands; drift accumulates.

### Alternative 2: free-form `context_notes:` field

- One frontmatter field with free-text describing context interactions; no canonical layer set.
- **Rejected**: defeats the purpose. The whole value is the shared vocabulary; free-text drifts into per-author phrasing within weeks.

### Alternative 3: enforce a maximum of N layers per command

- Cap `consumed:` at, say, two non-baseline layers. Force the author to factor commands that touch more.
- **Rejected**: premature optimization. The right per-command layer count depends on the command's role; capping it would either force unnatural factoring (worse) or be ignored (worse).

### Alternative 4: use the layer model as a system prompt rule, not frontmatter

- Add a `## Context budget` rule to the WOS instructing the model to think about layers when running any command, but do not encode it per command.
- **Rejected**: not falsifiable by lint. The whole point is mechanical drift detection, which requires per-command declaration.

## References

- `wos/context-budget.md` (the lazy-loaded full framework).
- `WORKFLOW_OPERATING_SYSTEM.md ## Context budget` (the compact stub).
- `scripts/lint-commands.sh` (frontmatter validation extension added in slice 01).
- ADR-0006 (lazy-load WOS pattern; the system-layer compaction technique this ADR generalizes).
- ADR-0007 (project-level memory; the memory-layer subdivision).
- ADR-0010 (centralized external web access; routing for `retrieved` layer).
- ADR-0011 (shared canonical blocks; the tools-layer DRY technique).
- Anthropic, "Effective context engineering for AI agents" (Sep 2025): the framework being adopted.
- Chroma Research, "Context-Rot" (2024-2025): empirical evidence that motivates per-layer compaction discipline (slice 13).
- PwC, "Don't Break the Cache" (2026): cost evidence that motivates static-prefix-first command structure (slice 03).

## Notes

This ADR is the foundation slice of the 2026-05-15_context-engineering-uplift task. ADRs 0013-0022 extend it with token budgets (slice 02), cache structure (slice 03), working-memory compaction (slice 04), user-level memory (slice 05), reflexion-style learnings (slice 12), contextual retrieval (slice 06), LLM-as-judge evals (slice 07), task cost observability (slice 09), evaluator-optimizer (slice 10), sub-agent orchestration (slice 11), and context-rot guardrails (slice 13). Read them as a group when the question is "how does the WOS handle context engineering as a discipline."

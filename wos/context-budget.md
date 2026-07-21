---
activation: model_decision
description: Six canonical layer names, frontmatter convention, debugging context overruns. Load when designing a new command or debugging context inflation.
---

# wos/context-budget.md

Lazy reference for `## Context budget` in the spec. The compact stub in `WORKFLOW_OPERATING_SYSTEM.md` keeps the lead definition (the six canonical layer names, the consumed/produced frontmatter convention, and the universal baseline rule). This file holds the layer-by-layer narrative, examples, and the compaction guidance that agents only need when designing new commands, debugging context overruns, or onboarding a contributor to the Fhorja context model.

Load this file when:
- writing or revising a `commands/<name>.md` and choosing values for `context-layers-consumed:` and `context-layers-produced:`
- a contributor asks "what does the context budget framework actually mean?"
- diagnosing why a task feels context-heavy (which layer is overloaded?) and deciding whether compaction or restructuring is the right fix
- writing a new lazy-loaded Fhorja topic and deciding which layer it belongs to
- the compact stub in the spec is not enough to resolve a context-engineering nuance

Single-task day-to-day execution does not need this file: the inline stub in the spec plus the per-command frontmatter encode the rules.

---

## The six layers

Fhorja treats every model invocation as a budget split across six layers. Naming them explicitly turns context engineering from an implicit pattern into a falsifiable contract.

### 1. `system`

System-prompt rules, command personas, output contracts. The constants that frame every invocation regardless of which command runs.

Examples:
- Fhorja itself (the spec the model is operating under).
- The `Goal:` and `Operating rules:` of the active command.
- Anthropic Claude Code's system reminders, Cursor's slash-command framing, etc. (tool-specific framing layered on top).

### 2. `memory`

Persisted state that survives across turns and sessions. Subdivided into three tiers, all collapsed into this single layer for budget purposes:

- **Task memory**: `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SLICES/*.md`, `INVARIANTS_AND_NON_GOALS.md`, `IMPACT_ANALYSIS.md`, etc., under the active task folder.
- **Project memory**: `PROJECT_CHARTER.md`, `REFERENCES.md` at `projects/<client>__<project>/`.
- **User memory**: `USER_MEMORY.md` once slice 05 of the context-engineering uplift task lands. Cross-task, cross-project preferences and recurring gotchas.

### 3. `retrieved`

External sources brought in by retrieval rather than persisted as memory. Distinct from `memory` because the content originates outside the task, and from `tools` because it is data, not a callable schema.

Examples:
- The summaries appended to `REFERENCES.md` by `capture-references` (these live IN memory but originate from `retrieved` and are tagged as such conceptually).
- Cross-source synthesis written to `EXTERNAL_RESEARCH.md` by `external-research`.
- The result of an ad-hoc web fetch (which, per ADR-0010 centralized external web access, should be routed through `capture-references` and not consumed inline).

When a command BOTH retrieves and persists, it touches both `retrieved` (as the originating layer) and `memory` (as the resting place). The frontmatter convention is to list `retrieved` in `consumed` when the command actively pulls external content this turn, and `memory` when it reads already-captured references.

### 4. `tools`

Tool and command definitions exposed to the model. The schemas the model can call, plus the description text that primes the model on when each is appropriate.

Examples:
- Every `commands/<name>.md` file, when surfaced as an Agent Skill at `.claude/skills/<name>/SKILL.md`.
- The frontmatter `description:` field (Agent Skills uses this to decide when the skill is relevant).
- The native tools the AI tool itself exposes (Read, Edit, Bash, etc. in Claude Code; equivalents in Cursor / Codex / Copilot).

### 5. `history`

Recent conversation turns. The session-scoped record of what was said and done, distinct from `memory` because it lives in the chat transcript rather than in persisted files.

Examples:
- The prior model outputs in the current session (the model can re-read them up to context limits).
- The user's earlier prompts in the same chat.
- Tool results returned within this session.

`history` is the most volatile layer: compaction (`/compact` in Claude Code; equivalent in other tools) shrinks it; a new session resets it entirely. Commands that explicitly leverage `history` (`resume-from-state`, `im-stuck`) declare it in `consumed:`.

### 6. `task`

The immediate user request being processed. The active prompt, including any pasted artifacts, the slash command invocation, and the surrounding intent.

Examples:
- The text the user types into the chat to invoke a command.
- The artifact body the user pastes for a critique or review.
- The `### Handoff` block from a prior turn (Mode A compact or Mode B with `Resume context:`) that seeds the current turn's task.

---

## Consumed vs produced (the frontmatter convention)

Every `commands/<name>.md` declares two frontmatter fields:

```yaml
context-layers-consumed: [memory, retrieved]
context-layers-produced: [memory]
```

### Rule: list non-baseline layers only

`system`, `tools`, and `task` are universal baseline. Every command consumes them by definition (the system prompt is always loaded; the command itself is a tool definition being read; the user invocation is always the immediate task). Listing them in `consumed:` for every command would dilute the signal.

`consumed:` lists the layers a command actively READS BEYOND the universal baseline. Valid non-baseline values: `memory`, `retrieved`, `history`.

`produced:` lists the layers a command WRITES TO via its runtime artifacts. The Handoff routing line (`Run now: /<command>`) is itself a universal output and is not listed. Valid values: any of the six layers when actually written. In practice, most produced values are `memory` (commands that persist task-memory artifacts), `retrieved` (capture-references, external-research, project-bootstrap), or `tools` (rare; a hypothetical command that registers a new skill at runtime).

### Empty lists are valid

A command may consume or produce nothing beyond baseline.

- `what-next` consumes `memory` (it reads TASK_STATE to route) but produces nothing material (the routing IS the Handoff; no persistence). Its frontmatter: `consumed: [memory]`, `produced: []`.
- `workflow-guide` is pedagogical: it explains the workflow without persisting. `consumed: [memory]`, `produced: []`.
- `prompt-shape` produces a copy-paste-ready prompt that the user pastes into the next turn; it does not persist. `consumed: [memory]`, `produced: []`.

### How to choose values for a new command

1. **Does the command read any task / project / user memory file?** If yes, include `memory` in `consumed:`.
2. **Does the command pull from REFERENCES.md, EXTERNAL_RESEARCH.md, or an external web source this turn?** If yes, include `retrieved` in `consumed:`.
3. **Does the command rely on prior turns in the same session (chat history)?** If yes, include `history` in `consumed:`. This is rare; most commands re-read persisted memory rather than chat history.
4. **Does the command WRITE to a task-memory or project-memory file (TASK_STATE, DECISIONS, slice notes, REFERENCES, PROJECT_CHARTER, USER_MEMORY)?** If yes, include the corresponding layer in `produced:` (`memory` or `retrieved`).
5. **Does the command emit only a Handoff with no file persistence?** `produced:` is `[]`.

### Examples across the command set

| Command | consumed | produced | Why |
|---|---|---|---|
| `task-init` | `[memory]` | `[memory]` | reads project charter; creates the 5 mandatory task memory files |
| `capture-references` | `[retrieved]` | `[retrieved]` | pulls external URLs this turn; appends to REFERENCES.md |
| `external-research` | `[memory, retrieved]` | `[retrieved]` | reads task context plus references; writes EXTERNAL_RESEARCH.md |
| `what-next` | `[memory]` | `[]` | pure routing; reads task state to decide; no persistence |
| `resume-from-state` | `[memory, history]` | `[memory]` | reads task memory AND prior session turns; updates TASK_STATE |
| `project-bootstrap` | `[]` | `[memory, retrieved]` | reads nothing pre-existing; creates PROJECT_CHARTER (memory) and REFERENCES skeleton (retrieved) |
| `im-stuck` | `[memory, history]` | `[memory]` | reads task state and recent turns to diagnose loop; appends an observation |
| `delivery-asset` | `[memory]` | `[memory]` | reads task artifacts; writes a per-audience artifact file |
| `incident-triage` | `[memory]` | `[memory]` | reads invariants and decisions; updates TASK_STATE with classification |

The discriminating cases (`retrieved`, `history`, empty `produced`) are where the contract earns its keep. The bulk of routine commands cluster on `[memory] / [memory]`, which is correct and not noise.

---

## The four context operations (write, select, compress, isolate)

The 2026 context-engineering literature converged on four operations over the context window as a constrained resource (see `REFERENCES.md` 2026-07-11 scan: the tianpan compaction entry and Context Engineering 2.0). The WOS already implements all four; naming them makes the doctrine legible and tells each command which operation it is performing.

- **write** (persist context outside the window): the WOS substrate. `TASK_STATE.md`, `DECISIONS.md`, `LEARNINGS.md`, and `REFERENCES.md` are durable writes; the `.wos/VERIFICATION_LOG.jsonl` is the append-only provenance of every write. Owned by the writer commands per `wos/substrate-peers.md`.
- **select** (retrieve only what is relevant now): the WOS retrieval path. `task-init` runs `rank-learnings.sh` (ADR-0071) to surface only the relevant prior lessons; contextual retrieval in `REFERENCES.md` (ADR-0018); `code-locate` and `code-context-map` narrow to the files that matter. The point is to load a relevant subset, not the whole store.
- **compress** (summarize to save tokens): `compact-task-memory`. Per ADR-0093 the WOS compress is provenance-preserving: it drops routine prose from `TASK_STATE.md` but never rewrites the append-only VERIFICATION_LOG, so a dropped fact still traces to its origin write. Provenance-preserving compression is the 2026 technique that makes mid-flight compaction safe.
- **isolate** (give sub-tasks a clean context): the WOS fleet contract (ADR-0038). Each worker runs in an isolated context and returns a typed `StructuredOutput` payload, not its full working context, so the orchestrator's window stays bounded (mirrors the 2026 subagent-isolation pattern of returning a small condensed summary from deep work).

These four operations are the vocabulary; the per-layer strategy below is how each operation applies to each of the six layers.

---

## When to compact each layer

The Chroma `Context-Rot` report (2024-2025) showed that all models degrade as context grows, regardless of the stated context window. The compaction strategy varies per layer.

### `system`: rarely compactable

Fhorja itself, command personas, and output contracts are tight already. The lazy-load spec pattern (ADR-0006) is the compaction strategy for this layer: load `wos/<topic>.md` only when needed. Slice 01 of the context-engineering uplift adds this file as a lazy topic; future topics (sub-agent orchestration, etc.) extend the same pattern.

### `memory`: compactable on growth

Task memory grows monotonically as a task progresses (more decisions logged, more slices closed, more observations captured). When `TASK_STATE.md` feels heavy after multiple closed slices (typically 5+), `commands/compact-task-memory.md` produces a lossy summarized form preserving canonical decisions, recommended next step, and invariants verbatim while filtering stale facts, resolved questions, and mitigated risks into a `## Compaction history` audit entry. The compaction is reversible only via git; the audit entry lists what was dropped so the user can challenge over-eager filtering. ADR-0015 documents the policy. Per-phase warning thresholds (ADR-0023) surface the cost; see `## Context-rot thresholds` below.

Project memory (`PROJECT_CHARTER.md`, `REFERENCES.md`) is less prone to bloat but `capture-references` deduplicates by URL.

### `retrieved`: bounded by capture policy

`capture-references` dedup-by-URL prevents unbounded growth at the source. `external-research` synthesizes multiple references into a single EXTERNAL_RESEARCH.md, which itself is task-scoped and dies with the task folder when archived.

### `tools`: bounded by Agent Skills progressive disclosure

The <!-- count:commands -->95<!-- /count --> commands are surfaced as Agent Skills with `description:` fields used for relevance routing. The Agent Skills spec's progressive disclosure pattern means a tool's full body is only loaded when the description matches the active task. Tools the model does not need are out of the budget.

### `history`: aggressively compacted by the tool

Claude Code's `/compact` and equivalent compaction in Cursor / Codex / Copilot summarize earlier turns when the context window approaches its limit. The Fhorja contract assumes compaction can happen at any time and persists routing-critical state in `memory` (TASK_STATE.md `## Resume notes`) rather than `history`.

### `task`: bounded by user input

The active task is whatever the user just typed. The Fhorja contract ensures the Handoff block is compact (Mode A ~50 tokens intra-session, Mode B ~150-250 tokens cross-session), so the next turn's `task` layer is small.

---

## Context-rot thresholds

Per ADR-0023, three state-and-navigation commands (`sync-task-state`, `where-we-at`, `resume-from-state`) surface a warning when the active task's `TASK_STATE.md` exceeds the phase-specific threshold. The warning is informational (the command proceeds with its normal output); it recommends `compact-task-memory` as the response. The thresholds are LOCKED at slice 13 authoring; changes require updating both this table AND ADR-0023's Notes section.

| Phase | Threshold (tokens) | Rationale |
|---|---|---|
| `discovery` | 3000 | Discovery state is mostly facts and open questions; a 3000-token TASK_STATE means many entries that should be resolved before moving on. |
| `planning` | 5000 | Planning accumulates impact analysis, decisions, plan structure. 5000 is a reasonable plateau. |
| `implementation` | 8000 | Implementation legitimately grows state across slices; 8000 is a defensible per-phase ceiling. |
| `review` / `closure` | 6000 | Review and closure should be slim; if TASK_STATE is heavy at this phase, un-closed slices may be accumulating. |
| `delivery` | 6000 | Similar to review; PR-prep should not balloon working memory. |

### Warning policy

1. When a command in scope detects TASK_STATE.md (excluding `## Compaction history`) exceeds the phase threshold, emit one line in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.`
2. The warning is INFORMATIONAL; the command proceeds with its normal output.
3. If the prior step was `compact-task-memory`, suppress the warning to avoid double-noise.
4. The warning text is a fixed template; commands do not paraphrase.

### Compaction history is excluded from the count

The `## Compaction history` section of `TASK_STATE.md` is the audit trail of past compactions; it grows monotonically and is intentionally not compactable. The token count for the threshold comparison EXCLUDES this section so tasks that have already done their part are not penalized.

### Default-safe behavior

If a command sees a phase value not in the table (a future phase added without updating this section), it defaults to no warning. The threshold lookup is permissive; missing entries are treated as "no threshold" rather than blocking.

---

## Cache breakpoint convention

Anthropic's prompt caching docs and the PwC 2026 `Don't Break the Cache` paper show that placing the static prefix first plus a cache breakpoint at the end of the static section yields 41-80 percent cost reductions and 13-31 percent TTFT improvements on long-horizon agentic tasks.

### The marker

Every `commands/<name>.md` carries a single `<!-- cache-breakpoint -->` HTML comment marker as the LAST non-blank line of the body. The marker is mechanically detectable by lint (`scripts/lint-commands.sh` validates presence, count, and position per ADR-0014) and can be consumed by tool integrations that support explicit caching (Anthropic API `cache_control`; future MCP-cache extensions).

### What "static prefix" means in current architecture

Audited during slice 03 of the 2026-05-15 context-engineering uplift: NO command currently has in-file dynamic input. The user's actual paste content (failure traces, PR feedback, URLs) arrives via the slash-command invocation at runtime, NOT as a section within the command file. The command file in its entirety is the static prefix. The marker therefore goes at the very end of the body to delimit "command spec ends here; conversation continues with task / user input below."

### Why the marker exists when no reorder was needed

1. **Tool integrations cannot guess the boundary**. Different AI tools (Claude Code, Cursor, Codex, Copilot, Gemini CLI) have different default heuristics for cache placement. The marker is a contract signal so tools can act on Fhorja's intent rather than improvising.
2. **Static prefix size becomes verifiable**. The Anthropic cache floor is 4096 tokens for Opus 4.7. Slice 02 measured each command's size; the marker declares which span is the cacheable prefix so the floor check has a precise denominator.
3. **Future commands with in-file dynamic content can move the marker**. If a future command embeds a paste-here section (e.g., a paste-the-stack-trace stub inside the command file), the marker is placed BEFORE that section. ADR-0014 documents this evolution path explicitly.

### Cache hit math (rough)

For a typical 5-step session (task-init -> impact-analysis -> implementation-plan -> implement-approved-slice -> pr-package) with prompt cache:

- Static prefix = the spec (~13k tokens) + active command (~2-4k tokens) + shared blocks (~1k tokens) = ~16-18k tokens per step
- Cache write multiplier (Anthropic 5-minute TTL): 1.25x on the static prefix in step 1
- Cache read multiplier: 0.1x in steps 2-5

vs. no cache (the static prefix is paid in full every step): 5x the static cost.

The marker confirms WHICH portion is the cacheable prefix so the math is grounded.

### Edge cases

- **Tool that strips HTML comments before sending to the model**: the marker disappears from the model's view but the cache_control directive in the API call still works (the tool reads the marker from the source file, computes the byte offset, and passes cache_control with the right index). If a tool's adapter does not implement this, caching falls back to that tool's default behavior; no harm to correctness.
- **Marker present in `.claude/skills/<name>/SKILL.md`**: yes, `scripts/build-agent-skills.sh` copies the body verbatim including the marker. Open Agent Skills spec validators accept HTML comments inside skill bodies.
- **Marker deleted by a contributor**: lint hard-fails immediately. The failure message names ADR-0014 so the contributor can find the rule.

---

## Edge cases worth noting

- **A command that "produces" nothing material**: empty `produced: []` is valid. Pure routing (`what-next`, `command-router`), pedagogical (`workflow-guide`), or prompt-shaping (`prompt-shape`) commands emit only a Handoff. The Handoff is not listed because it is the universal output contract, not a layer-specific write.
- **Commands that "consume" the same layer they "produce"**: extremely common. `task-init` reads project charter (memory) and writes new task files (memory). `capture-references` reads existing REFERENCES.md (retrieved) and appends to it (retrieved). The frontmatter does not distinguish read-then-write within a layer; that's expected.
- **`system` and `tools` in `produced:`**: rare but legal. A future command that registers a new tool definition at runtime would produce `tools`. The context-engineering uplift task does not introduce any such command; reserving the value for future use.
- **`history` in `produced:`**: not meaningful in current tooling. The model's output IS the next entry in `history`, but listing it would be redundant with the universal Handoff. Reserved; do not use.
- **Commands that consume `task` deeply**: `decision-interview` parses the user's questions; `targeted-questions` does the same for factual gaps; `prompt-shape` consumes the user's draft prompt. These are not specially marked: `task` is universal baseline. The deep-parse-vs-shallow-read distinction lives in the command's `Operating rules:` body, not in frontmatter.
- **Multi-tool variation**: this framework describes context budget abstractly. Each AI tool (Claude Code, Cursor, Codex, Copilot, Gemini CLI) implements the layers slightly differently (caching boundaries, history compaction strategy, tool definition format). The frontmatter is tool-neutral; per-tool optimization happens in the adapter scripts (`build-agent-skills.sh`) and in the tool-specific configuration files (`.claude/`, `.cursor/`, `.codex/`).


## Parallel-dispatch context characteristics

Parallel-dispatch (ADR-0038, ADR-0039) changes the context budget model in ways the six-layer framework above does not capture by default. Sequential commands share one context window; parallel batches fan out across N independent subagent contexts plus the main orchestrator's context. Treat this section as the lazy reference for budgeting parallel runs.

### Per-agent context is isolated

Each parallel agent has its own context window. Total session context cost is roughly `N x per-agent-context + orchestrator-context`, not the sum of one shared transcript. The `system`, `tools`, and `task` baseline is paid once per subagent, not once for the batch.

### Empirical token usage

Lived test on 2026-06-04 (K.8 personas, 10-agent batches): subagent token consumption ranged 400k to 1.3M tokens per batch, varying with prompt depth, input artifact size, and whether the subagent had to read shared memory files. Shallow prompts with tight StructuredOutput contracts land near the 400k floor; deep prompts that pull task memory + references push toward the 1.3M ceiling.

### Per-agent budget shape

A well-shaped subagent prompt is roughly: 300 to 500 word instruction body + relevant inputs (paste or file references) + StructuredOutput reminder. That lands at ~3k to 6k tokens of input per agent. Output is bounded by the StructuredOutput schema, typically under 2k tokens.

### Orchestrator context grows linearly

The main orchestrator's context grows linearly with batch size. Each subagent result or completion notification consumes ~500 tokens in the orchestrator's transcript. A 10-agent batch adds ~5k tokens to the orchestrator's `history` layer; three back-to-back batches add ~15k.

### Context-rot threshold is unchanged

The per-phase thresholds in `## Context-rot thresholds` above (per ADR-0023) apply to the orchestrator unchanged. Parallel dispatch does not raise the ceiling; it only spreads work across isolated subagent contexts. The orchestrator's TASK_STATE.md still triggers the same phase-specific warnings.

### Recommendation

After 3+ consecutive parallel batches, run `compact-task-memory` or start a fresh session if the orchestrator's main context exceeds ~70 percent of its window. The subagent contexts die with each batch, so the long-lived risk is orchestrator-side accumulation, not subagent-side.

References: ADR-0038 (parallel dispatch foundations), ADR-0039 (batch sizing and cost model), ADR-0023 (context-rot thresholds), `wos/workflow-patterns.md` (fan-out / fan-in patterns).

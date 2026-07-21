---
activation: model_decision
description: Orchestrator-workers pattern + four-question checklist + per-tool primitives table. Load when deciding whether to delegate to a sub-agent.
---

# wos/sub-agent-orchestration.md

Lazy reference for the orchestrator-workers pattern at the Fhorja layer. The compact stub in `WORKFLOW_OPERATING_SYSTEM.md` minimum-read map keeps the lead pointer; this file holds the when-to / when-not-to checklist, the per-tool primitives table, and the pattern-relationships narrative that agents only need when deciding whether to delegate a sub-task to a tool-provided sub-agent.

Load this file when:
- a command is about to do a broad codebase exploration, a long-context summarization, or an independent verification, and the question is whether to delegate to a sub-agent
- a contributor is writing a new command and weighing whether the command should orchestrate or stay inline
- a reviewer is critiquing a command's scope and wants to know the Fhorja position on sub-agent use
- the spec minimum-read map's one-line summary is not enough to resolve the trade-off

Single-task day-to-day execution does not need this file: most commands stay inline; the per-tool primitives are surfaced when the topic is loaded.

---

## The pattern

Anthropic's "Building Effective Agents" (Dec 2024) names five canonical agent patterns: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer. Fhorja has explicitly adopted prompt chaining (Handoff contract; ADR-0002), routing (`what-next`, `## Command roles` index), and evaluator-optimizer (`self-critique-and-revise`; ADR-0021). Orchestrator-workers is the topic of this file. Parallelization is adopted too: the Workflow tool is the canonical primitive (ADR-0038), batch dispatch sizing is empirical (ADR-0039), and parallel slice execution under the file-scope disjointness gate ships as `implement-fleet` (ADR-0041), reached from the routing graph per ADR-0042.

In orchestrator-workers, a main agent (the orchestrator) decomposes a problem and dispatches sub-tasks to workers (sub-agents) running in their own context windows. Workers return summarized results to the orchestrator; the orchestrator integrates them and continues. The key benefit is **context hygiene**: the orchestrator's thread stays focused while workers handle context-heavy sub-tasks.

The Fhorja commands are mostly orchestrator-shaped (they read task memory, decide a next step, emit a Handoff). Most command bodies do NOT need worker primitives directly: the model running the command can delegate to a sub-agent when the tool provides one, without Fhorja having to mandate it. This topic documents WHEN that delegation is correct.

## When to delegate (four canonical cases)

### 1. Broad codebase search
Description: "find every place that calls X"; "list all files matching pattern Y"; "summarize the structure of directory Z".
Why delegate: the search produces a large raw output (often many file contents). Delegating keeps the orchestrator's thread clean; the sub-agent returns a summary (typically ~200-500 tokens).
Fhorja commands that fit: `code-locate`, `impact-analysis` (when the codebase is large).

### 2. Long-context summarization
Description: "summarize this 50-page PDF"; "extract the key constraints from this 10-file documentation set".
Why delegate: the source content is too long to keep in the main thread. A sub-agent reads the full content in its own window and returns a summary.
Fhorja commands that fit: `external-research`, `capture-references` (when capturing a long source).

### 3. Bounded planning of a sub-problem
Description: "draft a 5-slice plan for the database migration sub-task"; "design the test strategy for this one slice".
Why delegate: the sub-problem benefits from focused attention; the orchestrator integrates the sub-plan into the main plan.
Fhorja commands that fit: rarely; `implementation-plan` usually stays inline because the main thread already has the task context.

### 4. Independent verification of a result
Description: "I drafted this PR_PACKAGE.md; have a fresh agent critique it"; "I claim slice 3 passes its exit criteria; an independent worker confirms".
Why delegate: independence is the value. A fresh sub-agent without the orchestrator's biases can catch errors the orchestrator's confirmation bias would miss.
Fhorja commands that fit: `review-hard`, `self-critique-and-revise`.

## When NOT to delegate (four anti-patterns)

### 1. One-file edit
Description: "update line 42 of file X"; "rename function Y across one file".
Why not: the sub-agent's turnaround time and summarization step exceed the cost of doing it inline.

### 2. Routing decision
Description: "which command should I run next?".
Why not: routing is what the orchestrator is built for (`what-next`, `command-router` predecessor). Delegating means asking another agent to make the same decision the current one is already shaped to make.

### 3. Conversational continuation
Description: the user is in the middle of a discussion with the orchestrator and asks a clarifying question.
Why not: breaking the conversation to ask a sub-agent fragments the flow. The orchestrator answers from its current context.

### 4. Trivial computation
Description: arithmetic; string manipulation; date parsing.
Why not: trivial work has no isolation benefit. Delegating adds latency without context win.

## Four-question checklist before delegating

Before issuing a sub-agent invocation, ask:

1. **Is the sub-task self-contained?** Can the worker do the job with the inputs the orchestrator can package (no need to ask follow-up questions to the user)?
2. **Does the main thread benefit from isolation?** Is the sub-task context-heavy enough that keeping it inline would crowd the orchestrator's attention budget?
3. **Is the delegation cost less than the inline cost?** Sub-agent latency plus summarization overhead must be less than the cost of doing the work in the main thread.
4. **Is the sub-agent's tool set adequate?** Does the worker have the file-read / search / edit / shell tools it needs to do the job?

If all four answers are yes, delegate. If any answer is no, stay inline.

## Per-tool primitives (as of 2026-06-05)

| Tool | Sub-agent primitives | Notes |
|---|---|---|
| Claude Code | `Explore` (broad codebase search; read-only); `Plan` (architect an implementation plan); `general-purpose` (catch-all multi-step research); `Task` API (named sub-agent types); `SendMessage` (continue a previously spawned sub-agent with its context intact: spawn once, reuse across verification rounds while the main thread keeps working) | Most mature sub-agent surface in current ecosystem; explicit per-agent tool restrictions; isolated context windows |
| Cursor | agent mode (autonomous multi-step work) | Single sub-agent surface; less granular than Claude Code's; agent mode is the primary sub-agent primitive |
| Codex (OpenAI) | agents (background tasks running on isolated environments) | Cloud-execution-shaped sub-agents; longer turnaround; different cost model |
| GitHub Copilot | (no first-class sub-agent yet at v0.2.x) | Multi-step work happens in the main agent thread |
| Gemini CLI | (no first-class sub-agent yet at v0.2.x) | Inline only |
| OpenHands | autonomous-task delegation | Runs tasks in an isolated sandboxed environment |
| Goose | session sub-agents | Lightweight; less mature than Claude Code's |

The table is dated; tools evolve. Update via PR when a tool's sub-agent surface changes.

## Harness equivalence (v3 wave1, item I)

When a command or pattern in this repo assumes a Claude Code primitive, this table maps the equivalent or the explicit degradation on another harness, so a non-Claude session degrades deliberately instead of improvising. Evidence base: the av3 (Claude Code) vs bv3 (Codex CLI) cross-model dogfood, 2026-07-19/21. Operational quirks (sandbox write-root, approval timing, patch mechanics) live in `wos/editor-mode-mappings.md ## Harness operational quirks` (mutual cross-link); this section owns the primitive surface. Same maintenance rule as the primitives table above: dated, update via PR.

| Primitive assumed | Claude Code | Codex CLI equivalent or degradation |
|---|---|---|
| `SendMessage` (persistent sub-agent: spawn once, resume with context intact; av3 reused one verifier twice while the main thread kept implementing) | Native | No analog. Explicit degradation: verify inline in the same turn, or accept a stateless respawn per verification round as the honest floor; do not emulate persistence by pasting prior transcripts. |
| `Workflow` and fleet fan-out (parallel sub-agent orchestration, ADR-0038) | Native | Not available; documented as Claude Code-only (spec `## Parallel workflow`). Degradation: serialize the wave inline. |
| `AskUserQuestion` (interactive gate) | Native | Becomes an unanswered paste-string. Degradation: auto-waiver by observable signal ONLY for administrative gates (team-approval, merge, tag confirmation), following the delivered solo/local precedent in `commands/task-close.md`; the experience-verdict floor (ADR-0091) is explicitly excepted and requires a recorded human PASS in any harness. Decision-bearing surfaces follow the Unattended-sessions doctrine (`wos/cross-cutting-workflow-guardrails.md`) unchanged. |
| `suggested-model` frontmatter (Claude SKUs) | Native | Maps to the `Codex reasoning-effort default` column in ADR-0025 `## Model selection by tier`. |

## Pattern relationships

| Pattern | Status in Fhorja | Where |
|---|---|---|
| Prompt chaining | Adopted | Handoff adaptive format (ADR-0002) |
| Routing | Adopted | `what-next` + `## Command roles` index |
| Orchestrator-workers | Adopted (J.1+J.2 2026-06-04) + J.3 tier-aware dispatch; ADR-0038/0039/0040 | `templates/ORCHESTRATOR_COMMAND.template.md` + `commands/_shared/worker-contract.md` + `commands/_shared/orchestrator-bootstrap.md` per ADR-0034 |
| Evaluator-optimizer | Adopted | `self-critique-and-revise` (ADR-0021) |
| Parallelization | Adopted (Mode C ADR-0032 + Epic J fleet commands) | Mode C reactive fanout; orchestrator-workers proactive fleets |
| Tier-aware dispatch | Adopted (J.3 2026-06-04) | `## Tier-aware dispatch protocol` below; orchestrator tier >= worker tier |
| Substrate-bullet ownership | Adopted (ADR-0038 Rule 3) | Every parallel-dispatch wave must gate merge on `scan-substrate-orphans.py`; see `## The orphan-scan gating step pattern` below |

## Self-consistency (consensus-of-N over one artifact)

Self-consistency (Wang et al. 2022) samples several independent reasoning passes over the same input and keeps the answer they converge on, which beats a single greedy pass on hard reasoning. In Fhorja this is not a new mechanism: it is the existing `consensus-of-N` merge strategy (defined in `commands/_shared/worker-contract.md`, wired through `commands/_shared/orchestrator-bootstrap.md`) applied to a SINGLE artifact reviewed N times rather than to N different artifacts. The two high-stakes review commands `security-review` and `review-hard` expose it as an opt-in `--consistency N` mode (OFF by default, per ADR-0073): N independent passes with fresh context read the same diff, and a finding is high-confidence when it appears in at least `ceil(N/2)` passes. Singletons are kept as advisory rather than dropped, which is the one deliberate deviation from the strict consensus-of-N rule (that rule drops dissenters with `event=consensus_drop`); in a review context a labeled low-confidence finding beats a silent miss.

This is distinct from `verify-against-rubric-fleet`, which runs N DIFFERENT artifacts through ONE rubric and merges the per-artifact verdicts with a `union` strategy. Self-consistency fixes the artifact and varies the pass; the rubric fleet fixes the rubric and varies the artifact. Both reuse the same worker and merge infrastructure; they differ only in what is held constant, so no new orchestration primitive is introduced for either.

## Edge cases

- **Sub-agent unavailable**: tools without sub-agent primitives (Copilot, Gemini CLI as of v0.2.x) fall back to inline work. No Fhorja contract violation; the orchestrator does the work itself. Future tool updates may add sub-agent surfaces; this topic should be refreshed at that point.
- **Sub-agent budget exceeded**: if a worker hits its context limit, it should return a partial result with explicit "I could not finish; here is what I got". The orchestrator decides whether to re-delegate with narrower scope or stay inline.
- **Cross-sub-agent coordination**: an orchestrator-of-orchestrators pattern is out of scope. If a sub-task needs further decomposition, the worker itself can delegate (one level deep is fine); but Fhorja does not provide an orchestrator-of-orchestrators primitive. If real-use friction surfaces, a new ADR can introduce one.
- **Why no `Delegate now:` Handoff directive (yet)**: changing the Handoff contract (currently `Run now:` is the only primary action verb) requires a stronger signal of real use-case friction than we currently have. ADR-0022 documents this deliberate stop-short and the criteria for promoting the pattern to an enforced directive.

## Tier-aware dispatch protocol (J.3, per ADR-0034)

Adopted 2026-06-04. Orchestrator commands dispatching workers per the worker contract (`commands/_shared/worker-contract.md`) MUST respect the tier-aware dispatch protocol.

### Core rule

**Orchestrator tier >= every worker tier.** Concretely:
- An Opus orchestrator (`suggested-model: claude-opus-4-7` or `claude-opus-4-8`) may dispatch Opus, Sonnet, or Haiku workers.
- A Sonnet orchestrator (`suggested-model: claude-sonnet-4-6`) may dispatch Sonnet or Haiku workers; may NOT dispatch Opus workers.
- A Haiku orchestrator (`suggested-model: claude-haiku-4-5`) may NOT dispatch any workers (Haiku is a leaf tier).

### Why the constraint exists

If a Sonnet orchestrator dispatched Opus workers, the orchestrator's synthesis step would be the bottleneck on judgment quality (Opus per-worker output > Sonnet integration capacity). This is a known failure mode in production multi-agent systems (Anthropic research system 2026: Opus lead + Sonnet subagents was the validated shape, not the inverse). Workers can specialize narrowly; orchestrators must synthesize globally.

Haiku as leaf tier reflects Haiku 4.5's strength on mechanical, schema-bounded tasks (regex pattern matching, structured extraction) and weakness on synthesis across heterogeneous partials.

### Declaration in orchestrator frontmatter

Per `templates/ORCHESTRATOR_COMMAND.template.md`:

```yaml
metadata:
  suggested-model: claude-opus-4-7   # orchestrator tier
  orchestrator: true
  workers:
    - role: <worker-role-slug>
      tier: claude-sonnet-4-6        # worker tier; <= orchestrator tier
      contract_ref: commands/_shared/worker-contract.md
    - role: <other-role-slug>
      tier: claude-haiku-4-5         # leaf worker
      contract_ref: commands/_shared/worker-contract.md
```

### Tier-mapping per role (heuristic)

| Worker role pattern | Default tier | Rationale |
|---|---|---|
| Mechanical extraction (regex/AST/schema-bounded) | Haiku | Fast, cheap, deterministic enough; Anthropic Outcomes pattern |
| Per-target deep analysis (one screen, one file, one feature) | Sonnet | Standard coding/analysis depth |
| Cross-target synthesis or judgment-heavy (orchestrator role) | Opus | Multi-perspective integration; cost justified by single-instance-per-run |

The heuristic is non-binding. Orchestrator authors override per-role with a one-line rationale in the command body when justified.

### Cost guard

`commands/_shared/orchestrator-bootstrap.md` requires every orchestrator to:
1. Declare `max_fanout` (HARD cap on concurrent workers; default 20; absolute ceiling 100).
2. Verify the tier constraint at bootstrap time; refuse to dispatch if violated.
3. STOP with NO_OP_TRACE if enumeration produces N > `max_fanout`.

Together these prevent the documented cost-runaway class (e.g., the $8-15K incident from a 49-subagent run reported in 2026).

### Model inheritance and API-load guard (site dogfood F-5)

A Workflow-tool `agent()` call that omits `model` inherits the session model, not the role default. On the 2026-07-11 fhorja.dev site dogfood the user asked for a "Sonnet workflow" but the `agent()` calls omitted `model: 'sonnet'`, so six review workers inherited Opus 4.8; each fired several image-heavy Mobbin `search_sections` calls, the batch hit ~21 HTTP 429s, and because the Bash tool's own safety pre-check also calls the model, three Bash calls were blocked ("cannot determine the safety of Bash right now") and a macOS notification alarmed the user. The fleet recovered (16/16, 0 errors) but degraded and confused the operator. Discipline:

- **Pin the tier explicitly on review/analysis fleets.** When the role default is Sonnet (per the tier-mapping table) and the fleet is read-only analysis, set `model: 'sonnet'` on each `agent()` call rather than relying on inheritance; an omitted `model` silently promotes the whole fleet to the (heavier, capacity-contended) session model.
- **Throttle concurrency when each worker makes several heavy MCP or image calls.** Lower the effective fan-out (or split into sub-batches) so N heavy workers do not each fire a burst of image-bearing tool calls at once; heavy-MCP fleets saturate the API faster than their agent count implies.
- **Read a 429 as rate limiting, not a machine fault.** When a fleet degrades under load, surface it to the operator as API rate limiting (and, if applicable, that the Bash safety pre-check shares that capacity), not as a code or environment problem.

### Override-up vs override-down

- **Override-up** (worker tier > role default): always valid. When in doubt, pick stronger. The orchestrator pays the cost; correctness wins.
- **Override-down** (worker tier < role default): valid only with a one-line rationale in the orchestrator command body, ideally citing an eval scenario (per K.7 eval discipline) that proves the downgrade preserves quality.

### Verification

`lint-commands.sh` (extension planned, K.7 era): when a command has `orchestrator: true` frontmatter, verify that `suggested-model` is >= every `workers[].tier` and that `max_fanout` is declared. Warn-only at v2.1 launch; promote to fail-fast post-eval evidence.

## Future evolution

Foreshadowed for potential future slices:
- `Delegate now:` Handoff directive (would join `Run now:` as a primary action verb). PROMOTED to Mode C of the Adaptive handoff per ADR-0032 (2026-06-04).
- Per-tool detection in `scripts/build-agent-skills.sh` to emit tool-specific sub-agent invocation hints.
- A `delegate-and-integrate` meta-command for explicit orchestrator-workers flows. Superseded by the orchestrator command shape (J.2 + `templates/ORCHESTRATOR_COMMAND.template.md`).
- Parallelization pattern (multi-worker, single-orchestrator) as a separate topic. PROMOTED to Adopted via Epic J fleet commands (all shipped: atom-audit-fleet, screen-spec-fleet, external-research-fleet, verify-against-rubric-fleet, task-init-fleet) and the implement-fleet slice orchestrator (ADR-0041/0042).

Remaining out-of-scope:
- Orchestrator-of-orchestrators (one level of nesting only at v2.1).
- L5 autonomous fleet dispatch by CUSTOM personas (`wos/substrate-peers.md ## Maturity ladder hook` reserves L5).


## Cross-references

This topic covers the **WHEN/HOW of single sub-agent dispatch** -- the orchestrator-workers pattern as documented by Anthropic, where a parent agent delegates a bounded unit of work (research, audit, fan-out leaf) to one isolated sub-agent context, then re-integrates the result. It deliberately stops at the single-dispatch boundary.

For **parallel orchestration** (multiple workers running concurrently, fan-out/fan-in, batched sub-agent waves), see the sibling topics below. They complement this document -- they do not replace it.

### Sibling topics

- **[ADR-0038 -- Workflow tool as canonical parallel-orchestration primitive](../docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md)**
  Formalizes the Workflow tool as the only sanctioned primitive for parallel sub-agent execution inside Fhorja. Defines the contract (Rules 1–N) that any parallel dispatch must satisfy, including substrate-bullet ownership rules that prevent the orphan failure mode.

- **[wos/workflow-patterns.md](./workflow-patterns.md)** (empirical evidence from 2026-06-05 session: ~165 subagents, 14 batches, 5M tokens)
  Canonical topic for parallel workflow patterns: fan-out/fan-in, bounded concurrency, retry-on-leaf, aggregation strategies. Read this **after** sub-agent-orchestration when the task needs more than one worker at a time.

- **[wos/bug-classes/substrate-bullet-orphan.md](./bug-classes/substrate-bullet-orphan.md)**
  Documents the failure mode that ADR-0038 Rule 3 exists to prevent: substrate bullets emitted by parallel workers but never re-anchored to a canonical owner, leaving orphaned references in TASK_STATE.md or DECISIONS.md.

- **[scripts/scan-substrate-orphans.py](../scripts/scan-substrate-orphans.py)**
  Static detector that scans task artifacts for orphaned substrate bullets. Run before slice-closure on any task that used parallel dispatch.

### Decision rule

- **One worker, bounded scope** → use this topic (sub-agent-orchestration).
- **Two or more workers in the same wave, or fan-out/fan-in (research or audit)** → use workflow-patterns + ADR-0038.
- **Executing an approved plan whose `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared** → use `implement-fleet` (ADR-0041); it orchestrates `implement-approved-slice` workers under the file-scope disjointness gate. A pure chain falls back to sequential `implement-approved-slice`.


### Related bug-classes

- **[wos/bug-classes/schema-skip-on-structured-output.md](./bug-classes/schema-skip-on-structured-output.md)** -- P0 failure when a subagent emits prose instead of calling the StructuredOutput tool. Empirical: 10/12 skip observed before focused-prompt mitigation. Detection: post-batch sweep for `outputs.filter(r => !r.artifact)`.

- **[wos/bug-classes/workflow-prompt-too-long.md](./bug-classes/workflow-prompt-too-long.md)** -- P1 failure when subagent prompts exceed ~600 words, mix multiple objectives, or omit the final-line StructuredOutput reminder. Mitigation: 300-500 word focused-prompt template per ADR-0039.

- **[wos/bug-classes/substrate-bullet-orphan.md](./bug-classes/substrate-bullet-orphan.md)** -- the substrate-protocol failure mode that ADR-0038 Rule 3 exists to prevent: parallel workers emit substrate bullets that never get re-anchored to a canonical owner. Detection: `scripts/scan-substrate-orphans.py`.



### The orphan-scan gating step pattern

**Pattern name:** orphan-scan gating step (per ADR-0038 Rule 3).

**Where it goes:** after every fleet-merge step that writes to substrate files (TASK_STATE.md, DECISIONS.md, SOURCE_OF_TRUTH.md, IMPLEMENTATION_PLAN.md, IMPACT_ANALYSIS.md, or any per-repo variant); before the next phase begins. The merge step is not "done" until the gate passes.

**Why it exists:** parallel workers can each emit substrate bullets that look locally valid but reference an owner that the merge never re-anchors. Without a gate, those orphans land in canonical artifacts and silently rot. The gating step turns that failure mode into a hard, automated stop.

**Canonical form (bash snippet):**

```bash
python3 scripts/scan-substrate-orphans.py <output-file-1> <output-file-2> ...
if [ $? -ne 0 ]; then
  # REFUSE merge OR roll back the merge,
  # log event=orphan_detected with the offending file list,
  # emit NO_OP_TRACE for the current phase,
  # surface the failure to the user before continuing.
  exit 1
fi
```

**Definition of Done:** `scan-substrate-orphans.py` exit code 0 on every touched file. No partial passes, no "fix later" tickets, no manual eyeball overrides. If the scan fails, the merge is treated as not having happened.

**Structurally compliant with ADR-0038 (post batch 8); lived runs PENDING:**

- atom-audit-fleet
- external-research-fleet
- verify-against-rubric-fleet
- screen-spec-fleet
- task-init-fleet

Each of these fleet commands now runs the gating step inline after merge and refuses to advance until exit 0 is observed. New fleet commands inherit the pattern by default; opting out requires an ADR amendment.

**Reference:**

- ADR-0038 Rule 3 (substrate-bullet ownership contract for parallel dispatch)
- [wos/bug-classes/substrate-bullet-orphan.md](./bug-classes/substrate-bullet-orphan.md) (failure mode this pattern prevents)
- [scripts/scan-substrate-orphans.py](../scripts/scan-substrate-orphans.py) (the detector that implements the gate)



### Audit references

- `_internal/fleet-audits/SUMMARY-postfix.md` (commit `1889a98`, local-only audit note, gitignored) -- post-fix synthesis: 5 fleet commands (atom-audit-fleet, external-research-fleet, verify-against-rubric-fleet, screen-spec-fleet, task-init-fleet) are structurally ADR-0038 compliant after the batch-8 fixes; PENDING lived runs to confirm the orphan-scan gate fires on real fan-out/fan-in waves.
- [ADR-0040 -- single-writer-per-folder exception](../docs/adr/0040-single-writer-per-folder-exception.md) (2026-06-05) -- narrow amendment to ADR-0038 Rule 2 for fleet commands where worker scope disjointness is validated pre-dispatch; preserves the orphan-scan gate as the post-merge safety net.

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

## Per-tool primitives (as of 2026-09-23)

| Tool | Sub-agent primitives | Notes |
|---|---|---|
| Claude Code | `Explore` (broad codebase search; read-only); `Plan` (architect an implementation plan); `general-purpose` (catch-all multi-step research); `Agent` API (named sub-agent types; renamed from `Task` in v2.1.63, the old name still resolves as an alias); `SendMessage` (continue a previously spawned sub-agent with its context intact: spawn once, reuse across verification rounds while the main thread keeps working) | Most mature sub-agent surface in current ecosystem; explicit per-agent tool restrictions; isolated context windows |
| Cursor | subagents (built-in `Explore`, `Bash`, `Browser`; custom ones as markdown in `.cursor/agents/`) | Each carries its own context window and several launch at once. Agent mode is not the sub-agent primitive; subagents are a separate documented surface |
| Codex (OpenAI) | agents (one TOML file per agent in `~/.codex/agents/` or `.codex/agents/`) | Run LOCALLY in current releases, in parallel, inheriting the parent's sandbox policy. Per-agent overrides: `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`; a setting the agent file omits inherits from the parent, and live session changes (`/permissions`, `--yolo`) still reach the child over the file's defaults. Concurrency capped by `agents.max_concurrent_threads_per_session`. Read 2026-09-17 from https://learn.chatgpt.com/docs/agent-configuration/subagents, HTTP 200; this row previously said cloud-execution-shaped with longer turnaround and a different cost model, which described an earlier product. |
| GitHub Copilot | custom agents, each run by a subagent | "The subagent has its own context window, which can be populated by information that is not relevant to the main agent." Invoked by `/agent`, by name, by inference, or `--agent <file>` |
| Gemini CLI | subagents (built-in `generalist`, `cli_help`, `codebase_investigator`; custom ones too) | "Subagents act in isolation with their own set of tools, MCP servers, system instructions, and context window." |
| OpenHands | sub-agent delegation (SDK TaskToolSet) | Sub-agents run synchronously and return results to the parent; the docs do not say whether they share the parent's workspace. Read 2026-09-23 from https://docs.openhands.dev/sdk/guides/task-tool-set.md |
| Goose | subagents | Separate instances with their own context; a subagent cannot spawn further subagents or change extensions. Read 2026-09-23 from https://goose-docs.ai/docs/guides/context-engineering/subagents/ |

The table is dated; tools evolve. Update via PR when a tool's sub-agent surface changes, and move the heading's date in the same edit: `check_scan_stamp_covers_its_claims` fails the build when the file's `Last scanned:` is newer than this heading, which is what caught the three rows that were wrong on 2026-09-18. Two of them (Gemini CLI, GitHub Copilot) were already wrong on the 2026-06-05 the heading used to carry: Gemini CLI shipped subagents on 2026-04-15 and Copilot's custom agents on 2025-10-28.

## Monitor arming (worktree dogfood 2026-08-04)

A `Monitor` is armed with an explicit stop condition (success, failure, or timeout), never with an open-ended progress pattern. Nine notifications saying an iOS build is still compiling are not signal, and each one interrupts the thread carrying a prompt to notify the human.

Corollary for anyone reading a transcript: a queued message is NOT evidence that the human could not wait for the turn. Across a 2026-08 multi-worktree corpus, 40 queued lines contained 32 harness `task-notification` entries and only 8 real human messages. Count the class before reading intent into the volume.

## Harness equivalence (v3 wave1, item I)

When a command or pattern in this repo assumes a Claude Code primitive, this table maps the equivalent or the explicit degradation on another harness, so a non-Claude session degrades deliberately instead of improvising. Evidence base: the av3 (Claude Code) vs bv3 (Codex CLI) cross-model dogfood, 2026-07-19/21. Operational quirks (sandbox write-root, approval timing, patch mechanics) live in `wos/editor-mode-mappings.md ## Harness operational quirks` (mutual cross-link); this section owns the primitive surface. Same maintenance rule as the primitives table above: dated, update via PR.

| Primitive assumed | Claude Code | Codex CLI equivalent or degradation |
|---|---|---|
| `SendMessage` (persistent sub-agent: spawn once, resume with context intact; av3 reused one verifier twice while the main thread kept implementing) | Native | No analog. Explicit degradation: verify inline in the same turn, or accept a stateless respawn per verification round as the honest floor; do not emulate persistence by pasting prior transcripts. |
| `Workflow` and fleet fan-out (parallel sub-agent orchestration, ADR-0038) | Native | Not available; documented as Claude Code-only (spec `## Parallel workflow`). Degradation: serialize the wave inline. |
| `AskUserQuestion` (interactive gate) | Native | Becomes an unanswered paste-string. Degradation: auto-waiver by observable signal ONLY for administrative gates (team-approval, tag confirmation), following the delivered solo/local precedent in `commands/task-close.md`; merge left that precedent in ADR-0191 because it is answerable by `git merge-base --is-ancestor` rather than by asking, and a waiver for an answerable condition discards the answer; the Godot feel-verdict floor is the one closure floor that still refuses without a recorded human PASS in any harness (ADR-0203), while the generalized experience verdict (ADR-0091) records its attester, run or human, per ADR-0179. Decision-bearing surfaces follow the Unattended-sessions doctrine (`wos/cross-cutting-workflow-guardrails.md`) unchanged. |
| `suggested-model` frontmatter (Claude SKUs) | Native | Maps to the `Codex reasoning-effort default` column in `wos/model-routing.md`. ADR-0172 moved that table out of ADR-0025 on 2026-08-30; the pointer here still named the ADR. |
| Per-agent worktree isolation (`isolation` on the `Agent` tool, `agent(prompt, {isolation: 'worktree'})`; `implement-fleet` dispatches every worker this way, and each worker returns through `.fleet-out/` in its own worktree, ADR-0242) | Native | Not assumed. Degradation: `implement-fleet` runs the wave's slices in turn through `implement-approved-slice`. Do not create worktrees by hand for sub-agents: a sub-agent bound to one inherits the parent's write sandbox, which refused every write of a simulated fleet on 2026-09-29. |
| Dispatch role on a sub-agent (`mechanical` or `judgment`, ADR-0236) | Native: per-call `model` on the `Agent` tool; per-call `model` and `effort` on a Workflow `agent()` call | Per-agent `model_reasoning_effort` from `wos/model-routing.md ## Dispatch roles`; the model is inherited. Cursor and harnesses with no per-agent field inherit both. |

## Pattern relationships

| Pattern | Status in Fhorja | Where |
|---|---|---|
| Prompt chaining | Adopted | Handoff adaptive format (ADR-0002) |
| Routing | Adopted | `what-next` + `## Command roles` index |
| Orchestrator-workers | Adopted (J.1+J.2 2026-06-04) + J.3 dispatch, role-aware since ADR-0236; ADR-0038/0039/0040 | `templates/ORCHESTRATOR_COMMAND.template.md` + `commands/_shared/worker-contract.md` + `commands/_shared/orchestrator-bootstrap.md` per ADR-0034 |
| Evaluator-optimizer | Adopted | `self-critique-and-revise` (ADR-0021) |
| Parallelization | Adopted (Mode C ADR-0032 + Epic J fleet commands) | Mode C reactive fanout; orchestrator-workers proactive fleets |
| Role-aware dispatch | Adopted (J.3 2026-06-04; roles replaced SKU tiers in ADR-0236) | `## Role-aware dispatch protocol` below; orchestrator at or above its workers |
| Substrate-bullet ownership | Adopted (ADR-0038 Rule 3) | Every parallel-dispatch wave must gate merge on `scan-substrate-orphans.py`; see `## The orphan-scan gating step pattern` below |

A vocabulary note, recorded so a future absorption sweep does not re-flag a mechanism this file already describes. The external project beads, read in the work that produced ADR-0125, covers the same territory under its own names: a formula is a declarative workflow template carrying steps, variables, dependencies, and gates, compiled into a proto and then instantiated as a molecule, the concrete work graph. Fhorja's counterpart is the orchestrator-fleet pattern above. `templates/ORCHESTRATOR_COMMAND.template.md` is the template, declaring worker role, dispatch role, `max_fanout`, the convergence pattern and its timeout, and both worker schemas as fillable placeholders; a dispatched fleet run is the instantiation; and the ordering half lives in `implementation-plan`'s per-slice `Depends-on` plus its computed `## Execution waves`.

Their gates map only partly, and the gap matters more than the overlap. beads has four gate types: human, timer, a GitHub Actions run completing, and a pull request merging. Only the human one has a Fhorja counterpart, and it is narrow: `approve-plan` self-runs a blinded review with no human turn (ADR-0208), the closure floors record a verification debt rather than wait for a person (ADR-0203), and `approve-proposed` runs only on request (ADR-0199). What stays human is the Godot feel-verdict floor and the four stop reasons of ADR-0186. The three machine-checkable types have none, and Fhorja cannot currently learn on its own that CI went green or that a PR merged. That absence is deliberate on two grounds: there is no execution engine here that would evaluate a declared gate type on its own schedule, and the authorized-fetcher rule in `WORKFLOW_OPERATING_SYSTEM.md` keeps a command outside that closed set from polling a host API. Fhorja's gates are callable commands, not data a scheduler watches.

## Self-consistency (consensus-of-N over one artifact)

Self-consistency (Wang et al. 2022) samples several independent reasoning passes over the same input and keeps the answer they converge on, which beats a single greedy pass on hard reasoning. In Fhorja this is not a new mechanism: it is the existing `consensus-of-N` merge strategy (defined in `commands/_shared/worker-contract.md`, wired through `commands/_shared/orchestrator-bootstrap.md`) applied to a SINGLE artifact reviewed N times rather than to N different artifacts. The two high-stakes review commands `security-review` and `review-hard` expose it as an opt-in `--consistency N` mode (OFF by default, per ADR-0073): N independent passes with fresh context read the same diff, and a finding is high-confidence when it appears in at least `ceil(N/2)` passes. Singletons are kept as advisory rather than dropped, which is the one deliberate deviation from the strict consensus-of-N rule (that rule drops dissenters with `event=consensus_drop`); in a review context a labeled low-confidence finding beats a silent miss.

This is distinct from `verify-against-rubric-fleet`, which runs N DIFFERENT artifacts through ONE rubric and merges the per-artifact verdicts with a `union` strategy. Self-consistency fixes the artifact and varies the pass; the rubric fleet fixes the rubric and varies the artifact. Both reuse the same worker and merge infrastructure; they differ only in what is held constant, so no new orchestration primitive is introduced for either.

## Edge cases

- **Sub-agent unavailable**: a tool with no sub-agent primitive falls back to inline work. Every tool in the table above has one as of 2026-09-20; this branch is kept because the contract must hold for a harness that does not, not because one is named here. No Fhorja contract violation; the orchestrator does the work itself. Future tool updates may add sub-agent surfaces; this topic should be refreshed at that point.
- **Sub-agent budget exceeded**: if a worker hits its context limit, it should return a partial result with explicit "I could not finish; here is what I got". The orchestrator decides whether to re-delegate with narrower scope or stay inline.
- **Cross-sub-agent coordination**: an orchestrator-of-orchestrators pattern is out of scope. If a sub-task needs further decomposition, the worker itself can delegate; but Fhorja does not provide an orchestrator-of-orchestrators primitive. If real-use friction surfaces, a new ADR can introduce one.
- **Why no `Delegate now:` Handoff directive (yet)**: changing the Handoff contract (currently `Run now:` is the only primary action verb) requires a stronger signal of real use-case friction than we currently have. ADR-0022 documents this deliberate stop-short and the criteria for promoting the pattern to an enforced directive.

## Role-aware dispatch protocol (ADR-0236, replacing the J.3 tiers of ADR-0034)

Adopted 2026-06-04 as tier-aware dispatch; the tiers stopped being model SKUs on 2026-09-28 (ADR-0236). Orchestrator commands dispatching workers per the worker contract (`commands/_shared/worker-contract.md`) MUST respect this protocol, and every other command that dispatches a sub-agent names the sub-agent's role the same way.

### Core rule

Every worker, and every single sub-agent a command dispatches, carries a dispatch role: `mechanical` or `judgment`. The command names the role and never a model or an effort. `wos/model-routing.md` → `## Dispatch roles` maps the role to a model and an effort per harness, and says how a harness with no per-agent lever degrades.

**The orchestrator stays at or above its workers.** A worker-contract fleet's own `suggested-model` resolves to a model at or above the model its workers' role resolves to. Concretely, with today's table: a fleet with `judgment` workers carries an Opus-class `suggested-model`; a fleet with `mechanical` workers may carry Sonnet-class or above. The rule binds fleets only. A command that makes one dispatch, such as `approve-plan` sending its plan to a reviewer, runs that reviewer above itself on purpose: the verdict is the deliverable and the dispatching command only records it.

### Why the orchestrator constraint exists

If a weaker orchestrator merged the output of stronger workers, the merge would be the bottleneck on judgment quality. This is a known failure mode in production multi-agent systems (Anthropic research system 2026: a strong lead with lighter subagents was the validated shape, not the inverse). Workers can specialize narrowly; orchestrators must synthesize globally.

### Declaration in orchestrator frontmatter

Per `templates/ORCHESTRATOR_COMMAND.template.md`:

```yaml
metadata:
  suggested-model: <at or above the model the workers' role resolves to>
  orchestrator: true
  workers:
    - role: <worker-role-slug>
      dispatch-role: mechanical        # or judgment; resolved in wos/model-routing.md
      contract_ref: commands/_shared/worker-contract.md
```

### Which role a worker gets

| Worker pattern | Role | Why |
|---|---|---|
| Reads and returns what it found, with no verdict (a search, a per-source summary, an extraction) | `mechanical` | The answer is in the input; depth adds cost, not correctness |
| Generates from an approved input (one screen spec, one task folder), or executes an approved slice | `mechanical` | The judgment was made upstream and approved; the worker applies it |
| Returns a verdict: a review finding, a rubric criterion, a pass or fail per guideline row, a refutation | `judgment` | The verdict is the deliverable, and routing it down degrades it |
| Merges or reconciles across items (the orchestrator's own step) | `judgment` | Runs in the orchestrator's session, which the rule above keeps at or above its workers |

When a worker could be either, it is `judgment`. A command may put a worker in `judgment` without a reason; putting a verdict-returning worker in `mechanical` is not allowed.

### Cost guard

`commands/_shared/orchestrator-bootstrap.md` requires every orchestrator to:
1. Declare `max_fanout` (HARD cap on concurrent workers; default 12; ceiling 20). The ceiling is the platform's, not a preference: Claude Code documents that the 21st concurrent sub-agent fails with `Concurrent subagent limit reached` and that the error instructs no retry, configurable via `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. A prior "absolute ceiling 100" here was five times a limit that fails closed. Retries count toward effective fanout, so a run declaring exactly 20 has no headroom for one. Review and verification fan-out runs at most 9 at once (`WORKFLOW_OPERATING_SYSTEM.md` → `## Parallel workflow`, ADR-0236).
2. Verify the orchestrator constraint at bootstrap time; refuse to dispatch if violated.
3. Split the worker set into sequential sub-batches of at most `max_fanout` when enumeration produces N > `max_fanout`, and continue, stating in one line how many batches the overflow produced; never silently truncate (ADR-0201).

Together these prevent the documented cost-runaway class (e.g., the $8-15K incident from a 49-subagent run reported in 2026).

### Model inheritance and API-load guard (site dogfood F-5)

A Workflow-tool `agent()` call that omits `model` inherits the session model, not the role's row. On the 2026-07-11 fhorja.dev site dogfood the user asked for a lighter workflow but the `agent()` calls omitted `model`, so six review workers inherited the heavier session model; each fired several image-heavy Mobbin `search_sections` calls, the batch hit ~21 HTTP 429s, and because the Bash tool's own safety pre-check also calls the model, three Bash calls were blocked ("cannot determine the safety of Bash right now") and a macOS notification alarmed the user. The fleet recovered (16/16, 0 errors) but degraded and confused the operator. Discipline:

- **Apply the role's row explicitly.** Pass the row's `model` (and `effort` where the call takes one) on each dispatch rather than relying on inheritance; an omitted `model` silently promotes a `mechanical` fleet to the session model. On a path that takes no effort, write `effort: inherited from session` in the transcript.
- **Throttle concurrency when each worker makes several heavy MCP or image calls.** Lower the effective fan-out (or split into sub-batches) so N heavy workers do not each fire a burst of image-bearing tool calls at once; heavy-MCP fleets saturate the API faster than their agent count implies.
- **Read a 429 as rate limiting, not a machine fault.** When a fleet degrades under load, surface it to the operator as API rate limiting (and, if applicable, that the Bash safety pre-check shares that capacity), not as a code or environment problem.

### Override-up vs override-down

- **Override-up** (a `mechanical` dispatch run on the judgment row): always valid. When in doubt, pick stronger.
- **Override-down** (a `judgment` dispatch run on the mechanical row): never. Change the table row instead, with the measurement that justifies it.

### Verification

`lint-commands.sh` checks the orchestrator contract at FAIL tier: a declared `max_fanout` above 20 fails, a stated ceiling above 20 fails (in `commands/` and in `wos/`), an `orchestrator: true` command that names no agent type fails, a `tier:` line inside a `workers:` block fails, a `dispatch-role:` value that `wos/model-routing.md ## Dispatch roles` does not define fails, a `claude-` model id anywhere in a command or shared block other than its `suggested-model:` line fails, and a model family name attached to workers or sub-agents in command prose fails (ADR-0236). The orchestrator constraint, `suggested-model` at or above the model the workers' role resolves to, is not checked by the lint; the orchestrator verifies it at bootstrap as the cost guard above says.

## Future evolution

Foreshadowed for potential future slices:
- `Delegate now:` Handoff directive (would join `Run now:` as a primary action verb). PROMOTED to Mode C of the Adaptive handoff per ADR-0032 (2026-06-04).
- Per-tool detection in `scripts/build-agent-skills.sh` to emit tool-specific sub-agent invocation hints.
- A `delegate-and-integrate` meta-command for explicit orchestrator-workers flows. Superseded by the orchestrator command shape (J.2 + `templates/ORCHESTRATOR_COMMAND.template.md`).
- Parallelization pattern (multi-worker, single-orchestrator) as a separate topic. PROMOTED to Adopted via Epic J fleet commands (all shipped: atom-audit-fleet, screen-spec-fleet, external-research-fleet, verify-against-rubric-fleet, task-init-fleet) and the implement-fleet slice orchestrator (ADR-0041/0042).

Remaining out-of-scope:
- Orchestrator-of-orchestrators. This is a Fhorja scope choice, NOT a platform limit: Claude Code documents that "a subagent can spawn subagents of its own, up to three layers below the main conversation" by default. The earlier note here said one level was the platform's ceiling, which stopped being true.
- L5 autonomous fleet dispatch by CUSTOM personas (`wos/substrate-peers.md ## Maturity ladder hook` reserves L5).


## Cross-references

This topic covers the **WHEN/HOW of single sub-agent dispatch** -- the orchestrator-workers pattern as documented by Anthropic, where a parent agent delegates a bounded unit of work (research, audit, fan-out leaf) to one isolated sub-agent context, then re-integrates the result. It deliberately stops at the single-dispatch boundary.

For **parallel orchestration** (multiple workers running concurrently, fan-out/fan-in, batched sub-agent waves), see the sibling topics below. They complement this document -- they do not replace it.

### Sibling topics

- **[ADR-0038 -- Workflow tool as canonical parallel-orchestration primitive](../docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md)**
  Records the original Workflow dispatch contract; ADR-0158 admits the Agent-file carrier alongside the runtime's typed return. Defines the contract (Rules 1 to N) that any parallel dispatch must satisfy, including substrate-bullet ownership rules that prevent the orphan failure mode.

- **[wos/workflow-patterns.md](./workflow-patterns.md)** (empirical evidence from 2026-06-05 session: ~165 subagents, 14 batches, 5M tokens)
  Canonical topic for parallel workflow patterns: fan-out/fan-in, bounded concurrency, retry-on-leaf, aggregation strategies. Read this **after** sub-agent-orchestration when the task needs more than one worker at a time.

- **[wos/bug-classes/substrate-bullet-orphan.md](./bug-classes/substrate-bullet-orphan.md)**
  Documents the failure mode that ADR-0038 Rule 3 exists to prevent: substrate bullets emitted by parallel workers but never re-anchored to a canonical owner, leaving orphaned references in TASK_STATE.md or DECISIONS.md.

- **[scripts/scan-substrate-orphans.py](../scripts/scan-substrate-orphans.py)**
  Static detector that scans task artifacts for orphaned substrate bullets. Run before slice-closure on any task that used parallel dispatch.

### Decision rule

- **One worker, bounded scope** → use this topic (sub-agent-orchestration).
- **Two or more workers in the same wave, or fan-out/fan-in (research or audit)** → use workflow-patterns + ADR-0038.
- **Executing an approved plan whose `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared**, on a harness with per-agent worktree isolation → use `implement-fleet` (ADR-0041, the default per ADR-0243); it orchestrates `implement-approved-slice` workers under the file-scope disjointness gate. A pure chain falls back to sequential `implement-approved-slice`.


### Related bug-classes

- **[wos/bug-classes/schema-skip-on-structured-output.md](./bug-classes/schema-skip-on-structured-output.md)** -- P0 failure when the selected carrier has no schema-conforming payload. Empirical: 10/12 skip observed before focused-prompt mitigation. Validate each expected worker's runtime result or assigned native JSON file under ADR-0158; a missing worker-side tool call is not the test.

- **[wos/bug-classes/workflow-prompt-too-long.md](./bug-classes/workflow-prompt-too-long.md)** -- P1 failure when subagent prompts exceed ~600 words, mix multiple objectives, or omit the final-line typed-return reminder for the selected carrier. Mitigation: 300-500 word focused-prompt template per ADR-0039.

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

The fleet commands that merge worker output into substrate (`atom-audit-fleet`, `external-research-fleet`, `feature-library-scout-fleet`, `screen-spec-fleet`, `task-init-fleet`, `verify-against-rubric-fleet`) run the gating step inline after merge and refuse to advance until exit 0 is observed. `implement-fleet` merges worktrees rather than substrate partials and gates each wave on its build, typecheck and test integration step instead. New fleet commands inherit the pattern by default; opting out requires an ADR amendment.

**Reference:**

- ADR-0038 Rule 3 (substrate-bullet ownership contract for parallel dispatch)
- [wos/bug-classes/substrate-bullet-orphan.md](./bug-classes/substrate-bullet-orphan.md) (failure mode this pattern prevents)
- [scripts/scan-substrate-orphans.py](../scripts/scan-substrate-orphans.py) (the detector that implements the gate)



### Audit references

- [ADR-0040 -- single-writer-per-folder exception](../docs/adr/0040-single-writer-per-folder-exception.md) (2026-06-05) -- narrow amendment to ADR-0038 Rule 2 for fleet commands where worker scope disjointness is validated pre-dispatch; preserves the orphan-scan gate as the post-merge safety net.

## Source currency

Last scanned: 2026-09-23
Cadence: 6 weeks

The harness claims in this file are vendor behavior, which moves. `scripts/check-doc-currency.sh` reads the two lines above and reports the age in lint. Move the date when the sources named in the file are reopened.

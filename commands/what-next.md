---
name: what-next
description: Determine the current stage of the active task and recommend the single best immediate next command, editor mode, and work complexity. Routes based on TASK_STATE.md, DECISIONS.md, and IMPLEMENTATION_PLAN.md without reopening broad discovery. Use when the user wants a fast operational answer for what to do next, when the task already has enough state to avoid rediscovery, and when the next step is not obvious from current artifacts. Do not use when the task is brand new (use task-init), when resuming after context loss (use resume-from-state), when the user wants a comparative explanation of multiple candidates, or when the task is stuck in a loop (use im-stuck).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: []
  tools: [Read, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 2000
  suggested-model: claude-haiku-4-5
---
# what-next

Act as a senior/staff workflow orchestrator for the active engineering task.

Goal:
Determine the current stage of the task and recommend the best immediate next command and editor mode.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- key task artifacts if relevant
- current user request

Task repository files to update:
- none

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to `TASK_STATE.md ## Recommended next step` (what-next is the OWNER per `wos/substrate-peers.md`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (typically NOT null: `## Recommended next step` was initially created by task-init).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=what-next section='## Recommended next step' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=route-<short-rationale> mode=applied -->`. REPLACE any prior owner header above this section (one header per section at any given time; prior write's header gets logged with event=overwrite).
  3. Write the section content (Command + Mode + Why per the canonical 3-field shape).
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator.
  6. When NO active task is present (e.g. immediately after `task-close`), what-next operates at project level: no substrate write happens; emit a NO_OP_TRACE line in `### Command transcript` and skip steps 1-5 entirely. K.4 drift-guard does not flag the no-op case.

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted, OR `sha_after` null on applied write). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- Do not reopen broad discovery unless clearly necessary.
- **Proactively offer the Express tier when its criteria are met (ADR-0025):** even when `## Recommended pipeline` in TASK_STATE.md already names a heavier tier, re-check the Express bar against the current known scope (describable in one sentence, all decisions already provided, fewer than 5 files affected). If the task now qualifies, name Express as the recommended next command sequence (`implementation-plan` -> `implement-approved-slice` -> `branch-commit`, skipping `impact-analysis` and `decision-interview`) rather than only applying it when the user separately asks for a faster path.
- Infer the current workflow stage from the latest task artifacts and unresolved gaps.
- Decide whether the task is currently in:
  - discovery
  - planning
  - contract refinement
  - contract signoff
  - test design
  - implementation
  - review
  - debug
  - delivery
- Recommend:
  1. the best next command
  2. the best editor mode
  3. **work complexity** (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step (definitions in `WORKFLOW_OPERATING_SYSTEM.md`; never name model SKUs)
  4. why this is the right next step
  5. what should explicitly not be done yet
- If there are 2 reasonable next steps, rank them.
- **Waves-aware routing (ADR-0042, stated verbatim wherever execution is routed):** when the active task has an approved plan and the first remaining `## Execution waves` entry has size 2 or more whose slices declare `Scope` and `Depends-on`, recommend `implement-fleet` for that wave; otherwise recommend `implement-approved-slice` for the next slice. Do not default to sequential execution when a parallelizable wave is ready (this is the gap that left the fleet unreachable from `what-next` and forced the operator to ask for parallelism).
- **Task-delivered handoff:** when the current task phase is "delivered" (all slices complete, committed/pushed) and the next action is a new task, include a ready-to-paste `task-init` prompt in the handoff body with project, task_slug, and summary pre-filled from the product spec or user context. This eliminates the "pode me retornar o prompt do task-init" round-trip.

Required output:
1. Current stage
2. What is already done
3. What is still missing
4. Recommended next command
5. Recommended mode
6. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) and one-line justification
7. Why this is the best next step
8. Alternative next step, if relevant
9. What to avoid doing now

### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Exactly one primary next command is recommended (fallback only if truly necessary).
- The recommendation matches the current phase and blockers in `TASK_STATE.md`.
- `### Artifact changes` is `None` unless there is a real reason to persist a change now.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Be practical, sequential, and workflow-aware. Optimize for reducing ambiguity and avoiding premature implementation.

<!-- cache-breakpoint -->

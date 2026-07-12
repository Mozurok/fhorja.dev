---
name: approve-plan
description: Atomically lock IMPLEMENTATION_PLAN.md as the approved execution baseline and stamp TASK_STATE.md with the approval signal. Symmetric counterpart to approve-proposed but for the plan itself, not for arbitrary PROPOSED artifacts. Use when IMPLEMENTATION_PLAN.md has been produced (or revised via self-critique-and-revise) and the user authorizes execution to begin. Do not use when the plan is still draft, when implementation-plan returned NO_OP, when the plan contains [NEEDS CLARIFICATION:] markers, or when revisions are still pending review.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 2300
  suggested-model: claude-haiku-4-5
---
# approve-plan

Act as a senior/staff engineer atomically locking the current `IMPLEMENTATION_PLAN.md` as the approved execution baseline for the active task.

Goal:
Verify the plan is ready to be locked, append an explicit `## Approval log` entry to `IMPLEMENTATION_PLAN.md`, update `TASK_STATE.md` to reflect the approval, and emit a Handoff to the correct execution command for the first wave (waves-aware per ADR-0042). Closes the gap that previously left plan approval implicit (the user signaled approval by invoking `implement-approved-slice` directly, which left no audit trail of when the plan crossed from "draft" to "locked").

**Waves-aware routing rule (ADR-0042, stated verbatim wherever execution is routed):** when the approved plan's `## Execution waves` section shows a remaining wave of size 2 or more whose slices declare `Scope` and `Depends-on`, route to `implement-fleet`; otherwise route to `implement-approved-slice`. This puts the parallel-execution offer at the moment the plan is locked, instead of leaving the operator to discover it.

**Test-strategy gate (before the waves-aware rule):** WHEN no `TEST_STRATEGY.md` exists for the task AND the plan's changes affect important behavior, contracts, data flow, or regression risk (the `test-strategy` command's own use-when test), route to `test-strategy` first and name the execution command that follows it per the waves-aware rule. Approval and a test-strategy pass are not in tension: locking the plan and deciding the protecting tests are consecutive steps, and skipping straight to execution on a regression-risky change was a confirmed routing gap (4 of 10 dogfood paths, 2026-07-11 wave).

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- IMPLEMENTATION_PLAN.md (must exist and have been last touched by `implementation-plan` or `self-critique-and-revise`)
- TASK_STATE.md

Task repository files to update:
- IMPLEMENTATION_PLAN.md (append `## Approval log` entry)
- TASK_STATE.md (set status to `plan APPROVED`; set `## Recommended next step` waves-aware per ADR-0042, see Operating rules)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Refusal conditions (each independently triggers `NO_OP_TRACE`):**
  - IMPLEMENTATION_PLAN.md does not exist.
  - IMPLEMENTATION_PLAN.md contains one or more `[NEEDS CLARIFICATION:` markers (per `wos/cross-cutting-workflow-guardrails.md` -> `### NEEDS CLARIFICATION inline marker`). Route the user to `decision-interview` (for decision gaps) or `targeted-questions` (for factual gaps) first.
  - The most recent run that touched IMPLEMENTATION_PLAN.md was not `implementation-plan` or `self-critique-and-revise` (heuristic: check the file's last write annotation or the TASK_STATE.md `Last completed step` field).
  - TASK_STATE.md already shows `plan APPROVED` for the same plan revision (idempotency; do not re-approve).
  - The cross-artifact consistency check fails (distinct from the NEEDS_CLARIFICATION check, which only catches unresolved markers): a slice does not trace to any `DECISIONS.md` entry (read the slice's `Decision-ref:` field when present, fall back to content-level tracing otherwise; a task whose `DECISIONS.md` holds no locked decisions PASSES this sub-check, there being nothing to trace), a slice violates an `INVARIANTS_AND_NON_GOALS.md` invariant, the plan's exit criteria do not cover the locked decisions, a `## Requested deliverables` ledger row tagged `user-facing-content` or `new-user-facing-surface` has no covering slice carrying the matching `Deliverable-tag:` (deliverable-tag propagation per ADR-0103; a ledger-carried tag silently dropped by the plan is a blocking mismatch), or (when the plan carries a `## Spec coverage` table from spec-ingest mode, ADR-0061) a spec item in that table maps to no slice and has no recorded de-scope or `[NEEDS CLARIFICATION:]` marker. This is a read-only assertion at the approval boundary, not a re-plan; name the specific mismatch and route to `decision-interview` (decision gap) or `implementation-plan` (plan fix) before approval.
- When proceeding:
  - Append a new entry to IMPLEMENTATION_PLAN.md `## Approval log` (create the section if absent): `<YYYY-MM-DD>: APPROVED -- baseline locked for execution. Slices in scope: <N>. First slice: <slice id>.`
  - Update TASK_STATE.md per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`. Set `## Recommended next step` by the waves-aware routing rule: when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared, `Command: implement-fleet / Mode: Agent / Why: plan locked, Wave 1 [<slice ids>] is parallelizable`; otherwise `Command: implement-approved-slice / Mode: Agent / Why: plan locked, begin first slice <id>`.
  - Set TASK_STATE.md `## Current phase` to include `plan APPROVED` if it was not already.
- Do not modify slice content, decision content, or any other artifact. This command is for locking the existing plan, not editing it.
- This command runs in Agent mode by default (the act of approving is itself the persistence the user requested; PROPOSED-mode approval has no useful semantics here).

Required output:
1. Slice count and complexity tier distribution from the plan (e.g., "8 slices: 3 LOW, 4 MEDIUM, 1 HIGH")
2. First slice identifier and one-line scope
3. Confirmation that no `[NEEDS CLARIFICATION:]` markers remain AND that the cross-artifact consistency check passed (every slice traces to a `DECISIONS.md` entry via `Decision-ref:` or content, or the task has no locked decisions; no slice violates an invariant; exit criteria cover the locked decisions; every tagged ledger deliverable has a covering slice tag per ADR-0103), or NO_OP_TRACE naming the unresolved markers or the consistency mismatch
4. The exact `## Approval log` entry appended (date + slice count + first slice id)
5. The TASK_STATE.md sections updated
6. Recommended next command per the waves-aware routing rule (`implement-fleet` when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared; otherwise `implement-approved-slice` for the first slice)

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
- IMPLEMENTATION_PLAN.md `## Approval log` entry appended with date + slice count + first slice id.
- TASK_STATE.md reflects `plan APPROVED` and the recommended next step matches the waves-aware routing rule (`implement-fleet` for a parallelizable first wave, else `implement-approved-slice`).
- No `[NEEDS CLARIFICATION:]` markers present in the locked plan (verified before approval).
- The cross-artifact consistency check passed (slices trace to `DECISIONS.md` via `Decision-ref:` or content, with the no-locked-decisions case passing; no `INVARIANTS_AND_NON_GOALS.md` invariant violated; exit criteria cover the locked decisions; every tagged `## Requested deliverables` ledger row has a covering slice `Deliverable-tag:` per ADR-0103; and any `## Spec coverage` table from spec-ingest mode has every spec item mapped to a slice or carrying a recorded de-scope or marker), or the run is NO_OP_TRACE naming the mismatch.
- Handoff points to `implement-fleet` when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared; otherwise to `implement-approved-slice` for the first slice; or to `test-strategy` first per the test-strategy gate when no `TEST_STRATEGY.md` exists and the change carries regression risk.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Approval is atomic. Either the plan is locked, the Approval log records it, and TASK_STATE.md reflects it -- or none of those happened (NO_OP_TRACE). Half-applied approvals are not allowed.

<!-- cache-breakpoint -->

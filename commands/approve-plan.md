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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
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
  - The cross-artifact consistency check fails (distinct from the NEEDS_CLARIFICATION check, which only catches unresolved markers): a slice does not trace to a LOCKED `### D-N` entry in `DECISIONS.md ## Locked decisions` (read the slice's `Decision-ref:` field when present, fall back to content-level tracing otherwise; a `Decision-ref:` resolving only to a `<!-- PROPOSED by ... -->` block is a blocking mismatch routed to `decision-interview` to lock the decision first, per ADR-0105 amending the ADR-0103 gate semantics; a task whose `DECISIONS.md` holds no locked decisions AND whose slices cite no PROPOSED-only refs PASSES this sub-check, there being nothing to trace), a slice violates an `INVARIANTS_AND_NON_GOALS.md` invariant, the plan's exit criteria do not cover the locked decisions, a `## Requested deliverables` ledger row tagged `user-facing-content` or `new-user-facing-surface` has no covering slice carrying the matching `Deliverable-tag:` (deliverable-tag propagation per ADR-0103; a ledger-carried tag silently dropped by the plan is a blocking mismatch), or (when the plan carries a `## Spec coverage` table from spec-ingest mode, ADR-0061) a spec item in that table maps to no slice and has no recorded de-scope or `[NEEDS CLARIFICATION:]` marker. This is a read-only assertion at the approval boundary, not a re-plan; name the specific mismatch and route to `decision-interview` (decision gap) or `implementation-plan` (plan fix) before approval.
- When proceeding:
  - Append a new entry to IMPLEMENTATION_PLAN.md `## Approval log` (create the section if absent): `<YYYY-MM-DD>: APPROVED -- baseline locked for execution. Slices in scope: <N>. First slice: <slice id>.`
  - Update TASK_STATE.md per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`. Set `## Recommended next step` as a three-way branch. WHEN the test-strategy gate fires (no `TEST_STRATEGY.md` exists and the change carries regression risk), persist `Command: test-strategy / Mode: Plan / Why: plan locked; no TEST_STRATEGY.md and the change carries regression risk; then <implement-fleet or implement-approved-slice per the waves-aware rule>`. Otherwise apply the waves-aware routing rule: when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared, `Command: implement-fleet / Mode: Agent / Why: plan locked, Wave 1 [<slice ids>] is parallelizable`; otherwise `Command: implement-approved-slice / Mode: Agent / Why: plan locked, begin first slice <id>`.
  - Set TASK_STATE.md `## Current phase` to include `plan APPROVED` if it was not already.
- Do not modify slice content, decision content, or any other artifact. This command is for locking the existing plan, not editing it.
- This command runs in Agent mode by default (the act of approving is itself the persistence the user requested; PROPOSED-mode approval has no useful semantics here).

Required output:
1. Slice count and complexity tier distribution from the plan (e.g., "8 slices: 3 LOW, 4 MEDIUM, 1 HIGH")
2. First slice identifier and one-line scope
3. Confirmation that no `[NEEDS CLARIFICATION:]` markers remain AND that the cross-artifact consistency check passed (every slice traces to a LOCKED `### D-N` entry in `DECISIONS.md ## Locked decisions` via `Decision-ref:` or content, a PROPOSED-only `Decision-ref:` being a blocking mismatch per ADR-0105, or the task has no locked decisions and no PROPOSED-cited refs; no slice violates an invariant; exit criteria cover the locked decisions; every tagged ledger deliverable has a covering slice tag per ADR-0103), or NO_OP_TRACE naming the unresolved markers or the consistency mismatch
4. The exact `## Approval log` entry appended (date + slice count + first slice id)
5. The TASK_STATE.md sections updated
6. Recommended next command as a three-way branch: `test-strategy` when the test-strategy gate fires (no `TEST_STRATEGY.md` and the change carries regression risk), naming the execution command that follows it per the waves-aware rule; otherwise per the waves-aware routing rule (`implement-fleet` when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared; otherwise `implement-approved-slice` for the first slice)

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
- IMPLEMENTATION_PLAN.md `## Approval log` entry appended with date + slice count + first slice id.
- TASK_STATE.md reflects `plan APPROVED` and the recommended next step matches the waves-aware routing rule (`implement-fleet` for a parallelizable first wave, else `implement-approved-slice`).
- No `[NEEDS CLARIFICATION:]` markers present in the locked plan (verified before approval).
- The cross-artifact consistency check passed (slices trace to LOCKED `### D-N` entries in `DECISIONS.md ## Locked decisions` via `Decision-ref:` or content, a PROPOSED-only `Decision-ref:` being a blocking mismatch per ADR-0105, with the no-locked-decisions-and-no-PROPOSED-cited-refs case passing; no `INVARIANTS_AND_NON_GOALS.md` invariant violated; exit criteria cover the locked decisions; every tagged `## Requested deliverables` ledger row has a covering slice `Deliverable-tag:` per ADR-0103; and any `## Spec coverage` table from spec-ingest mode has every spec item mapped to a slice or carrying a recorded de-scope or marker), or the run is NO_OP_TRACE naming the mismatch.
- Handoff points to `implement-fleet` when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared; otherwise to `implement-approved-slice` for the first slice; or to `test-strategy` first per the test-strategy gate when no `TEST_STRATEGY.md` exists and the change carries regression risk.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Approval is atomic. Either the plan is locked, the Approval log records it, and TASK_STATE.md reflects it -- or none of those happened (NO_OP_TRACE). Half-applied approvals are not allowed.

<!-- cache-breakpoint -->

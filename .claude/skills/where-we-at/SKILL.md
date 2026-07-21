---
name: where-we-at
description: |-
  Macro checkpoint that assesses the real current task state against the approved plan and task artifacts, then determines what is done, what is missing, and what remains to finish the proposed work. Broader than slice closure. Returns no-op when the checkpoint would not materially change operational truth. Use when the user wants a reliable checkpoint on task progress, the task has multiple phases or slices, or the current need is broader than closing a single slice. Do not use when the task is single-slice or the current need is to close just one slice (use slice-closure; where-we-at exists specifically for multi-slice or multi-phase tasks where macro checkpointing adds signal), the task is brand new and has no meaningful state yet, or the user only needs a fast routing answer (use what-next).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: true
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 2200
  suggested-model: claude-haiku-4-5
---

Act as a senior/staff engineering progress assessor for the active engineering task.

Goal:
Assess the real current task state against the approved plan and task artifacts, then determine what is done, what is missing, and what remains to finish the proposed work, with explicit no-op behavior when the checkpoint would not materially change operational truth.

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
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- relevant task artifacts
- latest implementation/review/test evidence if available
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Context-rot guardrail (ADR-0023):** before producing the output, estimate the current TASK_STATE.md token count (excluding the `## Compaction history` section). Compare against the phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery: 3000; planning: 5000; implementation: 8000; review/closure/delivery: 6000). If current count exceeds the threshold, emit a single-line warning in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` The warning is INFORMATIONAL; proceed with the normal output. Suppress the warning if the immediately prior step was `compact-task-memory`.
- **Multi-repo (G4 v2, per D.4 of Fhorja improvement plan 2026-06-03):** when `SOURCE_OF_TRUTH.md` contains a `## Repositories` section, the macro checkpoint reports progress per-repo (slices completed, blockers, exit criteria status). Multi-repo tasks routinely have independent per-repo progress (BE may be ahead of FE); a single combined summary hides this.
- Do not reopen broad discovery unless the current state cannot be assessed safely without it.
- Before producing output, verify the checkpoint would materially change operational truth versus the latest `TASK_STATE.md` and artifacts.
- If progress judgment is already accurate and complete enough to act, do not churn `TASK_STATE.md`; return a no-op and route forward.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- First identify:
  - current task scope level
  - current phase
  - current closure target
- Then compare the current implementation state against the approved plan or slice goal.
- Distinguish clearly between:
  1. completed work
  2. partially completed work
  3. not started work
  4. intentionally deferred work
  5. out-of-scope noise that should not affect progress judgment
- Be explicit about whether the task is:
  - on track
  - partially complete
  - near completion
  - blocked
- Recommend the smallest sensible next step toward completion.

Required output:
1. Task scope level
2. Current phase
3. Current closure target
4. Overall status
5. What is completed
6. What is partially completed
7. What is not started
8. What is intentionally deferred
9. What should be ignored as out-of-scope noise
10. What remains to finish the proposed work
11. Best next step
12. Best next command
13. Best editor mode
14. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`

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

### Deliverable status (report, per ADR-0056)
<!-- shared:deliverable-reconcile -->
**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. The gate is lifecycle-aware: it hard-fails only when the run is finalizing the whole task, and reports without failing at a mid-task checkpoint.

1. Locate the ledger. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (a legacy task that predates the ledger), OR its only row is the `- none named` sentinel (a brief that named no concrete deliverable), this gate is a no-op: skip it and proceed.

2. Classify the context. A finalization run is `task-close`, or `review-hard` run as the pre-PR final pass. A checkpoint run is `where-we-at` or `slice-closure` (and any `review-hard` run that is not the pre-PR final). At a checkpoint a row still tagged `in-scope` that is not yet done is normal remaining work, not a defect.

3. Define reconciled vs silent omission. A row is reconciled when it is `done` (in the delivered work) or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief that has NO ledger row at all, or a row that was dropped without a recorded de-scope, is a silent omission. To detect the no-row case you MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief) and the original request when it is in conversation context, and confirm every deliverable named there has a `## Requested deliverables` row. A named deliverable with no row means the ledger was seeded incompletely at `task-init`, and it is a silent omission. WHEN no brief artifact is available to cross-check, reconcile the rows that exist and state in the output that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, state whether it should be delivered or de-scoped, and route to `decision-interview` (record a de-scope) or `implementation-plan` (plan the missing work).
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding, and route it to `decision-interview` (to record a de-scope) or `implementation-plan` (to seed and plan the missing deliverable), the same repair routing as the finalization branch. At a checkpoint neither case invalidates the whole output: an in-scope-not-yet-done row is reported as remaining work, and a silent omission is named and routed as a must-address finding (never a bare one-line mention). Output invalidation for an unreconciled row happens only in the finalization branch.

A de-scope is allowed; silence is not. This generalizes the repo-level "reject silent omission of any repo in `## Repositories`" completeness check from repositories to user-named deliverables. The ledger is seeded at `task-init` and pointer-linked from `SOURCE_OF_TRUTH.md`.
### Definition of done (command output)
- Progress judgment is grounded in `IMPLEMENTATION_PLAN.md` + evidence (not vibes).
- Explicitly separates completed vs partial vs deferred vs out-of-scope noise.
- The task is genuinely multi-slice or multi-phase; running `where-we-at` on a single-slice task is invalid output (route to `slice-closure` instead).
- `TASK_STATE.md` updates are `PROPOSED` unless persisting in Agent mode.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity, momentum, accurate scope judgment, and practical next-step guidance.

<!-- cache-breakpoint -->

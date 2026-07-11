---
name: review-hard
description: Review the current task changes for real correctness, safety, and maintainability risks before slice closure or PR prep, and recommend the smallest safe next step. Surfaces meaningful issues (not cosmetic feedback); not a replacement for external review systems. Returns no-op when the review would not materially change conclusions. Use when a slice or task-level implementation was completed, the user wants a focused engineering risk review before closure or PR prep, or the current need is to surface meaningful issues. Do not use when no meaningful implementation has happened yet, the task is still in discovery or contract refinement or planning, or the goal is full external code review replacement rather than a focused internal risk check. Supports an opt-in `--consistency N` consensus mode (off by default) that runs N independent review passes over the same changes and merges them by consensus, per ADR-0073.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 2100
  suggested-model: claude-opus-4-7
---
# review-hard

Act as a skeptical senior/staff engineer performing a pre-PR engineering risk check for the active engineering task.

Goal:
Review the current task changes for real correctness, safety, and maintainability risks, then recommend the smallest safe next step, with explicit no-op behavior when the review would not materially change conclusions.

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
- TASK_STATE.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- relevant real code changes
- latest validation/test results, if available
- last completed step from TASK_STATE.md (command + summary)
- optional: `--consistency N` to run N independent review passes over the same changes and merge them by consensus (off by default; `N=3` recommended), per ADR-0073

Operating rules:
- **Runtime-debug-payload triage FIRST (ADR-0088).** FIRST ACTION, before any review step: IF the invocation args are a runtime-debug payload (pasted runtime logs such as an `adb logcat` or Metro dump, a stack trace or crash signature, a "still happening" or "got the error again" symptom) THEN the command SHALL route it to `incident-triage` BEFORE any review work and SHALL NOT absorb it into a review. `incident-triage` owns the debug loop: it classifies the failure, applies the instrument-first locus gate, and maintains the ruled-out-hypotheses ledger (ADR-0088). A payload that mixes real code-risk observations with runtime-debug logs is split: review the code-risk part here and route the runtime-debug part to `incident-triage`. This triage is payload-shape-conditional and additive; a normal code-review invocation is unaffected. It exists because the rn-dogfood audit showed `review-hard` used ~10 times as an ad-hoc debug-iterate loop with pasted logs, and the 2026-07-10 connector dogfood showed the clause skipped when it sat mid-list: the payload was absorbed and diagnosed inline. First position plus eval scenario 102 is the enforcement fix.
- Be critical, specific, and evidence-based.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Playtest-payload triage (ADR-0084).** Before reviewing, check whether the invocation args are playtest feedback rather than a request for a code-risk review: notes that the game runs but plays wrong, a mechanic feels off, a screen flow is missing, or difficulty or pacing is bad. That payload is not an engineering-risk review input; route it to `pr-feedback-ingest --playtest` (the first-class playtest ingestion path) instead of absorbing it into the review. This exists because the dogfood behind ADR-0084 had both of its core-mechanic corrections pasted into `review-hard` args for want of a designated path. A payload that mixes real code-risk observations with playtest notes is split: review the code-risk part here and route the playtest part onward. This triage is payload-shape-conditional and additive; a normal code-review invocation is unaffected.
- Before producing output, verify the review would materially change risk judgment versus the latest recorded state and artifacts.
- If the diff and validation evidence are unchanged since the last meaningful review, do not generate new churn; return a no-op and route forward.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Exempt from the no-op rule: an unreconciled `## Requested deliverables` row (per the deliverable-reconcile closure gate below) is always a must-fix finding, even when the diff and validation evidence are unchanged since the last review. A vanished deliverable is exactly the silent omission the gate exists to catch, so it is never suppressed as no-op churn.
- Focus on:
  - correctness
  - unsafe assumptions
  - hidden regressions
  - contract and schema mismatches
  - migration/data risks
  - concurrency or idempotency issues
  - weak or misleading tests
  - overengineering
  - maintainability
- Distinguish clearly between:
  - must fix
  - should fix
  - optional improvements
- Tag each finding with an impact band (LOW, MEDIUM, HIGH) and a rough effort band, then order findings by impact relative to effort, with impact as the primary key, so the highest value per unit of effort surfaces first. Effort is a tiebreak, never a reason to drop a cheap critical fix.
- Call out what should not have changed if relevant.
- If the implementation is solid, say so clearly rather than inventing feedback.
- Treat this as a focused pre-PR engineering risk check, not a replacement for external review systems.
- **Opt-in self-consistency consensus mode (`--consistency N`, per ADR-0073).** This mode is OFF by default; without the flag the review is a single pass and behaves exactly as today. When invoked with `--consistency N`, run N independent review passes with fresh context over the same changes, then merge the findings by consensus-of-N (the strategy defined in `commands/_shared/worker-contract.md`): a finding that appears in at least `ceil(N/2)` passes is high-confidence; a finding that appears in fewer passes is a singleton, kept as advisory and labeled, never silently dropped. Cost guard: total review cost multiplies by N, so this is strictly opt-in and `N=3` is the recommended setting; reserve it for high-stakes changes where the added confidence is worth the spend.

Required output:
1. Overall assessment
2. Must-fix issues
3. Should-fix issues
4. Test gaps
5. Over-engineering gate: flag single-caller abstractions, speculative config or flags nobody asked for, dead code left behind, a construction far larger than the need, and unrequested generality. Ground each flag in "no current caller" or "not in DECISIONS.md" so it stays evidence-based. Advisory and subject to the no-op rule, not a forced finding.
6. Final verdict
7. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
8. Recommended next command
9. Recommended editor mode
10. Why this is the correct next step
11. What should explicitly not be done yet

### Review prompt scaffold (optional)
<!-- shared:xml-review-scaffold -->
When the review directives in this command are ambiguous, parse them in three labeled parts: Instructions (what to do), Context (background, not a rule), and Constraints (hard limits that override the rest). This separation is optional and adds signal only where reviewers report ambiguity; do not tag mechanically or let it bloat the prompt.
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

### Deliverable reconcile (closure gate, per ADR-0056)
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
- Issues are ranked must/should/optional with concrete references to code/tests.
- No invented problems; if solid, say so clearly.
- `TASK_STATE.md` updates are `PROPOSED` unless persisting in Agent mode.
- A runtime-debug payload in the invocation args was routed to incident-triage (or split per the triage rule) BEFORE any review step; absorbing one into a review is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Maximize signal. Prioritize correctness, safety, and maintainability over stylistic commentary.

<!-- cache-breakpoint -->

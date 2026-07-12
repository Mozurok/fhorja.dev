---
name: slice-closure
description: |-
  Decide whether the current slice is ready to close, distinguishing slice completion from full task completion, then persist the result in slice notes and TASK_STATE.md as explicit reviewable closure notes. For single-slice tasks may route directly to delivery. Returns no-op when slice memory would not materially change. Use when a slice was just implemented, slice-level validation was completed or reviewed, or the next decision is whether this slice can be closed cleanly. Do not use when no concrete slice implementation happened yet, the task is still in broad planning or contract work, or the goal is to understand overall task progress (use where-we-at). Before closing a long session, use harvest-session-learnings to capture durable lessons.
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
    - minimal
    - core
    - full
  provenance: first-party
  token-budget: 2900
  suggested-model: claude-haiku-4-5
---

Act as a senior/staff engineering slice-closure reviewer for the active engineering task.

Goal:
Decide whether the current slice is ready to close, without confusing slice completion with full task completion, then persist the result in the task repository as explicit, reviewable closure notes (avoid rewriting slice memory without material change).

Note: this command is **opt-in for LOW and MEDIUM complexity slices**. When `implement-approved-slice` verifies exit criteria inline and the slice passes, `slice-closure` is unnecessary. Use `slice-closure` when: work complexity is HIGH, exit criteria require manual verification beyond typecheck, or the slice has follow-ups that need explicit tracking.

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
- IMPLEMENTATION_PLAN.md
- current slice artifact, if present
- latest implementation outputs
- latest validation/test results, if available
- relevant real codebase context
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to a substrate section this command owns or co-writes (per `wos/substrate-peers.md`; slice-closure writes the canonical 5 sections per `commands/_shared/task-state-slice-closure-pattern.md`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (or `null` only if the section did not exist prior to this write).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=slice-closure section='## X' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=<<=80chars> mode=applied -->`.
  3. Write or update the section content.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator. `sha_before` is `null` ONLY on first write to a fresh section.
  6. slice-closure writes 5 sections in one run per the canonical closure pattern. Repeat steps 1-5 PER section: one transaction header + one JSONL line per section. Reuse the same `run_id` + `ts` across all 5 section writes in this single invocation.

  FORBIDDEN: the half-compliant pattern (JSONL line emitted but inline header omitted, OR `sha_*` fields set to `null` when the section already existed). K.4 drift-guard at the next `repo-consistency-sweep` Pre-flight will surface this command's own writes if it skips the protocol.
- Do not reopen broad discovery, broad review, or signed-off contract issues.
- Before producing output, verify closure assessment would materially change slice artifacts or operational memory.
- If closure status and evidence are already recorded with no material gap, do not rewrite artifacts; return a no-op and route forward (often `/sync-task-state` if memory alignment helps).
- No-op rule for artifacts:
  - If slice documentation would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Treat this as a closure decision for the current slice only, unless the context explicitly says the whole task is ending.
- First identify:
  - current task scope level
  - current closure target
- Then evaluate whether the approved slice goal was met. Require the verbatim command output recorded at execution as proof of each exit criterion; an exit criterion without shown evidence is unverified, not met.
- **Commit-evidence floor (ADR-0084, bounded deferral per ADR-0100).** A slice is not `ready to close` unless its work is committed (cite the commit reference in the closure notes) or an explicit waiver of committing is recorded. A committing-waiver covers ONLY genuinely discardable work (a deliberate throwaway, a spike whose value was the learning); real work awaiting a human commit, including an unattended session where git is unavailable or forbidden, is a BOUNDED DEFERRAL: record it as `deferred: pending human commit (<one-line context>)`, classify the slice `not ready to close`, and leave it open for the next human session. A waiver line on real work does not satisfy this floor. IF the slice's work is neither committed, genuinely waived, nor recorded as a bounded deferral THEN classify it `not ready to close` and route to `branch-commit`. This is the slice-level counterpart to the `task-close` floor; it closes the observed failure where slices were marked done with the work uncommitted (the dogfood behind ADR-0084), and the ADR-0100 refinement closes the follow-on failure where an unattended run could waive real work closed (5 of 10 paths in the 2026-07-11 wave hit exactly this gap).
- **Godot runtime-gate floor (ADR-0085).** WHILE the active task is a Godot task (detected by a `project.godot` or `.gd` codebase signature, or the presence of `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder) a slice whose declared scope touches a `.tscn` scene or a `.gd` script is not `ready to close` unless a `godot-runtime-verify` PASS is recorded (in `GODOT_RUNTIME_VERIFY.md` or cited in the slice notes) OR an explicit one-line skip reason is recorded in the slice notes. IF neither is present THEN classify the slice `not ready to close` and route to `godot-runtime-verify`. This enforces the ADR-0084 runtime-gate adoption rule; it never fires on a non-Godot task or on a slice with no `.tscn`/`.gd` runtime surface (a pure `.tres` data resource, a `project.godot` settings change, or docs). The check reads recorded evidence; it does not run a scene. `godot-runtime-verify`'s gate decision is a real three-way verdict (PASS, FAIL, or BLOCKED), not a PASS-or-nothing binary: a real, evidence-backed BLOCKED verdict is neither a PASS nor an unrecorded skip, and misrepresenting it as a "skip reason" would misstate what happened. Classify the slice `not ready to close` with the BLOCKED evidence cited verbatim, worded distinctly from "never attempted."
- **Godot feel-verdict floor (D-4, ADR-0089).** WHILE the active task is a Godot task (same signature detection as the runtime-gate floor above) a slice whose closure claim includes first-playable or feature-complete (the slice goal or the closure notes declare the build playable, or the feature complete for players) is not `ready to close` unless a recorded human feel verdict with `Overall: PASS` (a `## Feel verdict` block per `wos/godot-mobile-interaction-and-feel.md ## Feel verdict checklist (D-4 gate)`) is cited in the slice notes OR an explicit one-line skip reason is recorded. IF neither is present THEN classify the slice `not ready to close`, route the operator to run the feel-verdict checklist, and route the resulting notes to `pr-feedback-ingest --playtest`. This floor extends the runtime-gate floor, never replaces it: machine-green runtime evidence does not substitute for the human verdict (the dogfood behind this rule declared first-playable on green headless gates and the human found the game unplayable). It never fires on a non-Godot task or on a slice that makes no first-playable or feature-complete claim. **Bounded-vs-permanent skip (ADR-0098):** a skip reason stating no human is available in this environment, ever, does NOT by itself satisfy this floor; classify the slice `not ready to close` and leave it pending a human session. A genuine bounded deferral (a real human will review shortly, or a throwaway/no-runtime-surface slice) still satisfies it at the same low ceremony.
- **Experience-verdict floor (generalized, ADR-0091).** WHEN the closing slice's own deliverable carries the tag `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags; a tag on a different slice's row does not fire this floor), closure at this home SHALL require a recorded human experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` cited in the slice notes or task record) OR an explicit one-line skip reason. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict. IF the deliverable text plainly indicates user-facing content and no tag is present THEN treat the slice as tagged and flag the missing tag. IF neither the verdict nor a skip reason is present THEN classify the slice `not ready to close` and route to the experience-verdict check. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one. Same bounded-vs-permanent skip rule as the D-4 floor above applies here (ADR-0098): a "no human, ever" skip reason does not satisfy this floor.
- **Eval-threshold floor (ADR-0104).** WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature the closing slice ships or changes, the slice is not `ready to close` unless the recorded eval OUTCOME (the score against the plan's pass threshold on its held-out set) is cited with the threshold met, OR an explicit one-line skip reason is recorded (bounded-vs-permanent per ADR-0098). An exit criterion or closure note worded around the harness mechanism ("the harness runs") SHALL NOT substitute for the threshold outcome: a green harness execution with a failing score FAILS this floor. IF the outcome is absent THEN classify the slice `not ready to close` and route to running the eval per `AI_EVAL_PLAN.md`. No-op when the task has no `AI_EVAL_PLAN.md` or the slice does not touch the evaluated feature.
- **Entry-path probe floor (ADR-0091).** WHEN the slice ships a deliverable tagged `new-user-facing-surface`, closure at this home SHALL require one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) cited in the slice notes OR an explicit one-line skip reason. IF neither is present THEN classify the slice `not ready to close` and route the operator to run the entry path once. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
- Classify the slice into exactly one of:
  - ready to close
  - ready to close with follow-ups
  - not ready to close
- Distinguish clearly between:
  - what was completed
  - what is intentionally deferred
  - what remains as a blocker inside this slice
- If the slice is ready, recommend closing it and syncing task state.
- If not, recommend only the smallest remaining action.
- If status is **ready to close with follow-ups** and follow-ups are explicit micro-deltas under the same slice intent, prefer routing to `implement-slice-complement` over reopening a full `implement-approved-slice` pass unless the gap is material.
- Explicitly state what should not be reopened now.
- Record one complexity and dead-code debt line: did this slice introduce any abstraction, config, dependency, or dead code not yet justified by a current caller or a DECISIONS entry? Default "none"; a non-empty answer becomes a tracked follow-up (## In progress) rather than silent debt.
- When proposing a `TASK_STATE.md` update, set **Work complexity** for the **next** step after closure (often rises for the next slice or falls for packaging-only steps); definitions in `WORKFLOW_OPERATING_SYSTEM.md`.
- When adding LEARNINGS during closure, anchor each entry at the exact decision point that failed (`file:line`, slice section header, command name, or timestamped TASK_STATE row) per `templates/LEARNINGS.md` ## Entry shape. Retrospective summaries without anchors disqualify the entry. Add an optional `Tags:` line (comma-separated keywords) so `rank-learnings.sh` can surface the lesson for a future task (ADR-0071).
- **Multi-repo (G4 v2, per D.4 of Fhorja improvement plan 2026-06-03):** when `SOURCE_OF_TRUTH.md` contains a `## Repositories` section, report exit-criteria validation and remaining blockers per-repo in distinct subsections. A multi-repo slice is "ready to close" only when ALL repos meet their exit criteria; partial-close cases must say which repos passed and which did not.

TASK_STATE.md update pattern (canonical sections to edit at slice closure):
<!-- shared:task-state-slice-closure-pattern -->
Canonical TASK_STATE.md 5-section write pattern. It was defined at slice closure (its origin and empirical validation: pilot-repo session 2026-06-04, 21 slice closures, ~6 section updates per closure stably converged on this set) and is followed by EVERY command that stamps TASK_STATE.md after a meaningful step (slice-closure, approve-plan, implement-fleet, release-plan, ai-feature-eval-harness, the verify fleets, and peers). Read "closure" below as "the step this command just completed", then edit exactly these 5 sections in this order:

1. `## Current phase` -- if the phase shifted (e.g., discovery -> implementation), update the phase label and any inline progress notes.
2. `## Last completed step` -- replace with `Command: <cmd>`, `Mode: <mode>`, `Summary: <1-2 line outcome>`. This becomes the recovery anchor for `resume-from-state`.
3. `### In progress` (nested under `## Current status`, not a standalone H2, per `task-init.md`'s canonical TASK_STATE.md template) -- if a slice closed cleanly with no follow-up, set to `(nenhum)` / `(none)`. If a follow-up surfaced inside the slice, list it here as the immediate next item.
4. `## Recommended next step` -- replace with `Command: <next>`, `Mode: <mode>`, `Why: <one line>`. Aligns with the Handoff `Run now` line.
5. `## Current closure target` -- if a slice or epic just closed, advance this to the next closure target (next slice or next epic). If the same target still applies, keep it (no-edit OK).

Optional 6th section:

6. `## Resume notes` -- update only when external context shifted (a referenced repo moved, a decision was made elsewhere, etc.). Most slice closures do not touch this.

Rules:

- Use Edit (not Write) per section. Avoid full file rewrites; they invalidate prompt cache and lose audit trail.
- If a section would not materially change, skip it (per `## Material change (definition)` in `WORKFLOW_OPERATING_SYSTEM.md`).
- All 5 mandatory sections must be present in the file. If any is missing, propose adding the missing section first as a separate edit before continuing the closure update.
- Total edits per closure typically range 4-6. More than 8 indicates either drift recovery (mark in transcript) or that `slice-closure` is being misused for closure of multiple slices at once (split into separate runs).
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
- Closure status is exactly one of: ready / ready-with-followups / not-ready, with evidence.
- Commit-evidence floor (ADR-0084, ADR-0100): a ready-to-close slice cites its commit reference or records an explicit committing-waiver covering only genuinely discardable work; real work pending a human commit is a bounded deferral that keeps the slice open (not a waiver), and a slice with none of the three is classified not-ready and routed to `branch-commit`.
- Eval-threshold floor (ADR-0104): when an `AI_EVAL_PLAN.md` covers the closing slice's feature, closure requires the cited score-vs-threshold outcome met on the held-out set (or an explicit bounded skip reason per ADR-0098); harness-mechanism wording never substitutes for the threshold outcome.
- Godot runtime-gate floor (ADR-0085): in a Godot task, a runtime-observable slice (scope touched a `.tscn`/`.gd`) is not ready-to-close without a recorded `godot-runtime-verify` PASS or an explicit skip reason; otherwise classified not-ready and routed to `godot-runtime-verify`. Never fires on a non-Godot task or a no-runtime-surface slice.
- Godot feel-verdict floor (D-4, ADR-0089): in a Godot task, a slice claiming first-playable or feature-complete is not ready-to-close without a cited human `## Feel verdict` with `Overall: PASS` or an explicit skip reason; otherwise classified not-ready and routed to the feel-verdict checklist plus `pr-feedback-ingest --playtest`. Never fires on a non-Godot task or a slice making no such claim.
- Experience gates (generalized, ADR-0091): a slice tagged `user-facing-content` or `new-user-facing-surface` is not ready-to-close without a cited `## Experience verdict` PASS, and a `new-user-facing-surface` slice is not ready-to-close without a cited entry-path run, in each case unless an explicit skip reason is recorded; stands down on the Godot signature in favor of the D-4 floor above.
- Clearly distinguishes slice completion vs full task completion.
- Slice file updates are `PROPOSED` unless persisting in Agent mode.
- Optionally self-check K.2 substrate-write compliance via `scripts/scan-substrate-headers.sh <task-folder>` before finishing; not a gate, a cheap nudge.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clean closure, scope discipline, low ambiguity, and forward momentum.

<!-- cache-breakpoint -->

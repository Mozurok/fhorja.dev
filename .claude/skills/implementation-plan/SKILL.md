---
name: implementation-plan
description: |-
  Define an incremental, reviewable, production-safe implementation plan for the active task and persist it as IMPLEMENTATION_PLAN.md plus a TASK_STATE.md update. Breaks work into the smallest safe slices with objective, exact scope, ordering rationale, key risks, validation approach, exit criteria, and work complexity (LOW/MEDIUM/HIGH) per slice. No code is written. Also runs an annotate-only retrofit mode that backfills per-slice Scope and Depends-on plus an Execution waves section onto an existing in-progress plan so it can adopt implement-fleet, without re-planning. A --spec mode derives slices from a spec or PRD, checking every spec item is covered (ADR-0061). Use when impact is understood enough to plan safely, key boundaries are known, and major factual or decision ambiguity is already resolved. Do not use when the task is still too unclear, when key facts or decisions remain open, or when the current need is to implement an already-approved slice (use implement-approved-slice).
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
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
  token-budget: 4100
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineer designing a low-risk implementation plan for the active engineering task.

Goal:
Create an incremental, reviewable, production-safe implementation plan for the active task, then persist it in the task repository as explicit, reviewable updates (avoid silent replanning when nothing material changed).

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
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPACT_ANALYSIS.md, if available
- INVARIANTS_AND_NON_GOALS.md, if available
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)
- any "relevant prior lessons" surfaced by `task-init` from prior LEARNINGS (read-only; let them inform slice shaping and risk notes, per ADR-0017)
- optional: `--spec <path>` to a spec, PRD, or requirements document (internal to the repo or already captured) to derive the plan from that spec and check coverage of every spec item, per ADR-0061 (see the spec-ingest mode in Operating rules)

Operating rules:
- Do not write code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to a substrate section this command owns (per `wos/substrate-peers.md`: IMPLEMENTATION_PLAN.md `## Target behavior`, `## Current gaps`, `## Slices`, `## Risks and mitigations`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (or `null` only if the section did not exist prior to this write).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=implementation-plan section='## X' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=<<=80chars> mode=applied -->`.
  3. Write or update the section content.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator. `sha_before` is `null` ONLY on first write to a fresh section.
  6. implementation-plan typically writes ALL 4 owned sections in one run (re-plan = full IMPLEMENTATION_PLAN rewrite). Repeat steps 1-5 PER section: 4 transaction headers + 4 JSONL lines. Reuse the same `run_id` + `ts` across all 4 section writes. Per-slice status mutations by `implement-approved-slice` / `slice-closure` follow their OWN K.2 protocol (status-only line edits inside `### Slice N` are CO-WRITER writes; ownership stays with implementation-plan for the parent `## Slices` section).

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted, OR `sha_*` null on existing sections). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- **Never truncate before Handoff:** even after a long `IMPLEMENTATION_PLAN.md` payload inside `### Artifact changes`, the message must still end with `### Handoff` and the fenced standard ending format.
- **Handoff is mandatory:** use the adaptive format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. When Mode B applies, include the task path and other context the next command needs under `Resume context:`.
- No code changes should happen before plan approval.
- Before producing output, verify `implementation-plan` is still the highest-value command based on `TASK_STATE.md` and whether the plan would materially change.
- If `IMPLEMENTATION_PLAN.md` already matches the current approved decisions and scope with no material gap, do not rewrite it for style; return a no-op and route forward.
- No-op rule for artifacts:
  - If `IMPLEMENTATION_PLAN.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Break the work into the smallest safe slices. A single-phase plan covering the whole task is invalid when the work touches more than one file, contract, or behavioral seam; produce explicit numbered slices instead (use `SLICES/01_<slug>.md`, `02_<slug>.md`, ... when slice-level traceability helps). This enforces the spec Core principle 6 ("Prefer small approved slices over broad implementation").
- Optimize for correctness, low blast radius, and ease of review.
- Do not include opportunistic refactors unless required for safety or correctness.
- Apply the YAGNI restraint ladder to every slice before committing it to the plan: does this need to exist at all, then can the standard library do it, then the native platform, then an already-installed dependency, then a one-line change, then the minimum viable implementation. Flag any slice that adds a dependency or a new abstraction without a `DECISIONS.md` entry backing it. Tie the floor to `DECISIONS.md` and `INVARIANTS_AND_NON_GOALS.md` so safety-required structure is never trimmed away. (`implement-approved-slice` and `review-hard` enforce the same restraint at execution and review.)
- For each phase or slice, define:
  - objective
  - exact scope
  - `Scope:` the explicit file paths or globs this slice creates or modifies (machine-readable, one path per entry). Consumed by `implement-fleet` to compute parallelizable waves; an under-declared scope defeats the ADR-0041 file-scope disjointness gate, so list every file the slice will touch.
  - `Depends-on:` the slice IDs this slice requires, or `none` (machine-readable). With `Scope`, this defines the slice DAG.
  - why this order is safe
  - key risks
  - validation approach
  - exit criteria -- MUST use EARS template (per ADR-0031). Event-driven form preferred for slices: `WHEN <observable trigger> the <system/test/build> SHALL <verifiable outcome>`. Banned softeners in canonical sentence: should, may, appropriate, sensible, reasonable. Free-form prose for rationale is OK; the canonical sentence must use SHALL keyword.
  - **work complexity** for executing that slice: exactly one of `LOW`, `MEDIUM`, `HIGH` (definitions in `WORKFLOW_OPERATING_SYSTEM.md`), plus one line why (no model names)
  - **asset-fidelity decision** (design-to-code slices only, per ADR-0051): `Asset-fidelity: real-MCP` (the slice pulls the exact Figma node before editing) or `Asset-fidelity: placeholder` (with a one-line reason and the approval). Omit for non-design slices; when a slice implements from a design source and nothing is stated, the default is `real-MCP` and the execution gate enforces it.
  - optional `STOP conditions:` for Disciplined or Strict-tier and boundary slices, the observable signals that mean the executor must halt and escalate rather than improvise (scope creep beyond the declared `Scope`, a failing test the slice did not introduce, an unexpected schema or contract touch). Omit for simple slices; do not over-specify, since false halts add ceremony.
- Explicitly identify:
  - what must change
  - what must not change
  - what remains uncertain
- Include rollout and rollback notes when runtime behavior is affected.
- If planning cannot proceed safely due to unresolved ambiguity, stop and recommend the correct prior command instead.
- If the plan would introduce new behavioral commitments not supported by `DECISIONS.md` and evidence, label them as **PROPOSED** and route to the smallest decisive upstream command (`targeted-questions`, `decision-interview`, `resolve-contract-gaps`, or `contract-signoff`) instead of pretending they are already decided.
- **Retrofit mode (annotate-only; the adoption bridge for `implement-fleet` per ADR-0041).** When the caller signals `retrofit` or `annotate-only` (asks to make an existing plan fleet-ready, or arrives here from `implement-fleet` Step 1 because slices lack `Scope` / `Depends-on`) and a valid `IMPLEMENTATION_PLAN.md` already exists:
  - Do NOT re-derive the plan or change any slice's intent, objective, or ordering. This mode only backfills structured fields and computes waves; it is not a re-plan.
  - Read `TASK_STATE.md` to determine which slices are already executed. Annotate and wave-compute over the REMAINING (not-yet-executed) slices only.
  - For each remaining slice, infer `Scope` (the files it will touch, grounded in the slice's prose scope plus a read of the real codebase, never guessed) and `Depends-on` (from the stated ordering and from shared files). Tag any scope the model is unsure of with a one-line `(inferred; verify)` note so the user can correct it before dispatch; an under-declared scope defeats the ADR-0041 disjointness gate.
  - Compute the Execution waves over the remaining slices and state the parallelizability verdict: which waves have size >= 2 (where `implement-fleet` helps) versus a pure chain (where it does not).
  - Persist the annotation as a PROPOSED delta to the existing `## Slices` section (the section this command already owns); do not rewrite unchanged slice content.
  - Handoff routes to `implement-fleet` when at least one remaining wave has size >= 2, otherwise to `implement-approved-slice` for the next slice.
  - NO_OP when every remaining slice already declares `Scope` and `Depends-on` and the Execution waves are current.
- **Spec-ingest mode (`--spec <path>`, per ADR-0061).** When the caller passes `--spec <path>` (a spec, PRD, or requirements document), derive the plan FROM the spec instead of from a free-form task description:
  - Read the spec in full. Enumerate every named feature, requirement, or acceptance item as a discrete `spec item`. Keep the spec's own wording as the item label so coverage stays auditable; do not paraphrase an item away.
  - Map each spec item to one or more slices. The mapping is many-to-many but TOTAL: every spec item MUST trace to at least one slice ID. A slice may cover several small items; a large item may span several slices.
  - Run the deliverable-coverage check (ADR-0056): seed or extend the `## Requested deliverables` ledger in `TASK_STATE.md` with one row per spec item (tagged `in-scope`), then assert each row maps to a slice. A spec item with no slice is a silent omission: surface it in the canonical three-field marker form `[NEEDS CLARIFICATION: spec item "<label>" maps to no slice | include it as a slice or de-scope it | add a covering slice, or record a de-scope in DECISIONS.md]` rather than dropping it. Never de-scope a spec item unilaterally; an explicit de-scope needs a `DECISIONS.md` entry.
  - Emit a `## Spec coverage` subsection in `IMPLEMENTATION_PLAN.md`: a table of `spec item -> slice id(s)` so the trace is reviewable at approval (`approve-plan`'s cross-artifact consistency check reads it).
  - The spec is an external contract for grounding: when it references an external library or API, the normal reference-grounding rules still apply at execution time (the spec text alone does not satisfy the grounding gate).
  - This mode composes with the normal slicing rules: `Scope`, `Depends-on`, the Execution waves subsection, and EARS exit criteria are all still required. It changes the SOURCE of the slices (a spec, not a free-form description), not the slice format.
  - NO_OP when `--spec` points to a missing or empty file (route back to the caller to supply a valid path), or when the spec is already fully covered by the current plan's `## Spec coverage` table with no new items.

IMPLEMENTATION_PLAN.md must include:
1. Target behavior
2. Current gaps
3. Constraints and invariants
4. **Infrastructure prerequisites** (when applicable): external services, env vars, docker configs, CLI tools, or credentials that must exist before Slice 1 begins. Omit this section when the task has no external dependencies. When present, list each prerequisite with: what it is, how to verify it exists, and what fails without it.
5. Slice-by-slice plan (preferred). Phase-only output is allowed only for genuinely single-step work (one file or one contract, no integration seam), and the justification must appear in `### Command transcript`. Each slice includes **work complexity** `LOW` | `MEDIUM` | `HIGH` plus one-line rationale, a machine-readable `Scope:` (files the slice touches), and `Depends-on:` (slice IDs or `none`). Immediately after the slices, include an **Execution waves** subsection that layers the slice DAG: list each wave as `Wave k: [slice ids]`, grouping into one wave only slices whose dependencies are already satisfied and whose `Scope` sets are pairwise disjoint (no shared file, migration, lockfile, codegen, or barrel export). A pure chain is N waves of one slice; a wide graph has waves of two or more. This makes parallelizability visible and is what `implement-fleet` consumes (ADR-0041); it does not change sequential execution via `implement-approved-slice`.
6. Validation and test strategy by phase
7. Rollout and rollback notes
8. Risks and mitigations
9. Open questions or approvals still needed
10. Recommended next command
11. Recommended editor mode
12. Why that is the correct next step

TASK_STATE.md update must reflect:
- current phase
- current source of truth
- canonical decisions
- current status
- recommended next step
- active files in scope, if now clearer
- current closure target
- **work complexity** for the next execution step (align with the upcoming slice when known)

Required output:
1. Exact content for IMPLEMENTATION_PLAN.md (full document if create/update; otherwise a short NO_OP note)
2. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
3. Recommended next command. When the plan is complete with no `[NEEDS CLARIFICATION:]` markers, the default is `approve-plan` (lock the baseline before execution); execution commands (`implement-fleet` / `implement-approved-slice`) are reached only through that approval gate, routed waves-aware per ADR-0042. When clarification markers or open decisions remain, route to the smallest decisive upstream command instead.
4. Recommended editor mode
5. Why this is the correct next step
6. What should explicitly not be done yet

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
- Output is sliced (or single-phase with explicit justification in `### Command transcript`); each slice/phase has objective, scope, risks, validation, and exit criteria.
- No opportunistic refactors; dependencies and ordering are explicit.
- Any new behavioral commitment not in `DECISIONS.md` is labeled `PROPOSED` with upstream routing.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after `IMPLEMENTATION_PLAN.md` content without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Prefer a boring, safe, reviewable plan over a clever or wide-ranging one.

<!-- cache-breakpoint -->

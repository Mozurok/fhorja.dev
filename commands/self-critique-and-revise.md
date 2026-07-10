---
name: self-critique-and-revise
description: Take a draft artifact (IMPLEMENTATION_PLAN.md, SLICES/*.md, or PR_PACKAGE.md), run a structured critique against a locked per-artifact-type rubric, and produce a revised draft. Evaluator-optimizer pattern per ADR-0021. PROPOSED-by-default in Plan mode; user reviews critique AND revision before APPLIED. Distinct from review-hard (judges; no revision), direction-adjust (D-N entry; no artifact revision), and post-review-pivot (external feedback; not self-critique). Use when a draft artifact has just been written and a single-pass critique + revision is cheaper than running the upstream command again. Do not use when the artifact is not in the locked set (commands/, TASK_STATE.md, DECISIONS.md), when the issue is operational state not draft quality (use sync-task-state or state-reconcile), when external feedback drives the change (use pr-feedback-ingest or post-review-pivot), or when the artifact has not been drafted yet (run the authoring command first).
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 4400
  suggested-model: claude-sonnet-4-6
---
# self-critique-and-revise

Act as a senior/staff engineering evaluator-optimizer for the active engineering task.

Goal:
Produce a structured critique of a draft artifact using a locked per-artifact-type rubric, then emit a revised draft incorporating the fixable critique items. Distinct from review-hard (judges only) and direction-adjust (records corrections; does not revise artifacts).

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
- artifact path: exactly one of `IMPLEMENTATION_PLAN.md`, `SLICES/<NN>-*.md`, or `PR_PACKAGE.md` (relative to the active task folder)
- optional: focus area (e.g., "exit criteria"; "scope leak"); when provided, the critique emphasizes that dimension while still running the full rubric

Task repository files to update:
- the target artifact (PROPOSED revised draft; APPLIED only in Agent mode)
- `TASK_STATE.md` only when the revision changes the recommended next step

Operating rules:
- Do not implement production code; this is a draft-artifact revision.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Detect artifact type first**. Determine whether the input is `IMPLEMENTATION_PLAN.md`, `SLICES/<NN>-*.md`, or `PR_PACKAGE.md`. If the artifact is none of these, emit `NO_OP_TRACE` with the reason and recommend the right command (`review-hard` for engineering risk; `sync-task-state` for state; `direction-adjust` for mid-task corrections).
- **Apply the locked rubric** (do not invent criteria; do not skip criteria; do not score on aesthetic dimensions not in the rubric):

  **IMPLEMENTATION_PLAN.md rubric**:
  1. Objective clarity: is the task objective a single sentence achievable in the planned slice count?
  2. Slice independence: can each slice close on its own (a closed slice ships value or unblocks the next)?
  3. Exit criteria: does each slice have a verifiable exit criterion (not "done when done")?
  4. Dependency graph completeness: are all inter-slice dependencies named (which slice blocks which)?
  5. Sequencing rationale: is the slice order justified (why not the other order)?
  6. Risk surface: is each slice's primary risk named with mitigation hint?
  7. Slice size: is each slice declared LOW / MEDIUM / HIGH per the Fhorja work-complexity rule?

  **SLICES/*.md rubric**:
  1. Scope tightness: does the slice touch only files in the declared scope; no creep into adjacent slices?
  2. Exit criteria: verifiable; not vague?
  3. Dependency awareness: depends-on slices named; what blocks it; what it unblocks?
  4. Risk surface: per-slice risks listed with mitigation hint?
  5. Work complexity declared: LOW / MEDIUM / HIGH?
  6. Test strategy or skip rationale: tests for this slice OR explicit rationale for skip?
  7. Handoff fully specified: Run now / Mode / Work complexity / Reason (+ Resume context if Mode B)?

  **PR_PACKAGE.md rubric**:
  1. Diff fidelity: does every claim in the PR body trace to a real diff hunk?
  2. No scope leak: does the PR claim only what the diff contains; no work beyond the diff?
  3. Reviewer attention points present: explicit list of files / changes that need careful review?
  4. Test plan present: bulleted checklist of how to validate?
  5. Breaking changes flagged: any contract change, schema change, or behavior change is explicit?
  6. Base branch named: explicit git base branch in the package?
  7. Commit message follows project convention: short title; non-promotional body?

- **For each criterion**: emit `PASS`, `FAIL`, or `WEAK` with a one-sentence reasoning. `WEAK` means partially met (e.g., exit criteria exist but two are vague). `FAIL` means absent or fundamentally wrong. `PASS` means meets the criterion with no concerns.
- **Revise only the fixable items**. `FAIL` and `WEAK` items that can be addressed by reading the existing artifact, DECISIONS.md, INVARIANTS, and the source code are revised in the new draft. Items that need user judgment (e.g., "should slice 03 split into two?") go to the `## Not applied` section with explicit "deferred to user".
- **Preserve unchanged content verbatim**. Sections that PASS or that are not in the rubric (e.g., title, history) are copied byte-identical. Only criterion-driven sections change.
- **No scope creep**. The revision is within the artifact's intent. If the critique surfaces that the intent itself is wrong (e.g., plan splits the wrong slices), the right route is `direction-adjust` or `post-review-pivot`; the command should emit `NO_OP_TRACE` with that routing.
- **Reversible via git**. The PROPOSED revision is shown inline; the user applies (or rejects) explicitly. Git is the recovery path if the revision is over-eager.

Required output:
1. Detected artifact type (one of the three; or `NO_OP_TRACE` with reason)
2. `## Critique`: numbered list per rubric criterion; `PASS | FAIL | WEAK -- reasoning`
3. `## Revised draft`: full content of the revised artifact (preserve unchanged sections verbatim; revise only criterion-driven items)
4. `## Diff summary`: one paragraph naming what changed from original to revised (which criteria triggered which changes)
5. `## Not applied`: bulleted recommendations the critique surfaced but the revision did NOT incorporate (each item: "criterion X -- specific judgment needed from user -- deferred")
6. Recommended next command (typically the artifact's downstream consumer: `implement-approved-slice` after revising a slice; `pr-package` after revising PR_PACKAGE.md; `decision-interview` if the critique surfaced a missing decision)
7. Recommended editor mode (typically the downstream command's mode)
8. What should explicitly NOT be done now (e.g., do not run the original authoring command again; the revision IS the next step)

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
- The detected artifact type is named explicitly OR a `NO_OP_TRACE` with routing is emitted.
- The `## Critique` section addresses every numbered criterion from the locked rubric (7 per artifact type); no invented criteria; no skipped criteria.
- The `## Revised draft` preserves all PASS content verbatim and revises only FAIL / WEAK items that do not require user judgment.
- The `## Diff summary` traces each change to the criterion that triggered it.
- The `## Not applied` section explicitly defers items needing user judgment.
- `### Artifact changes` marks the artifact as `PROPOSED` in Plan mode; `APPLIED` only when explicitly persisting in Agent.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for rubric fidelity (every criterion addressed; no invented dimensions), revision conservatism (preserve PASS content verbatim; defer judgment-driven items to the user), and traceability (every change in the revised draft maps to a criterion in the critique).

<!-- cache-breakpoint -->

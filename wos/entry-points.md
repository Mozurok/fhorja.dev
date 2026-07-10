---
activation: always_on
description: Entry-point selection: which command to start with. Small and broadly applicable.
---

# Entry points

Quick-start guide for choosing the first command based on where you are.

## New project (no `projects/<client>__<project>/` folder yet)
Use:
- `project-bootstrap`
- then `task-init` for the first task under that project

## New project and you want to research external context first
Use:
- `project-bootstrap`
- then `capture-references` to seed `REFERENCES.md`
- then `task-init`

## New project, greenfield build, stack not yet decided
Use the greenfield POC sequence (see `wos/workflow-shapes.md` -> Greenfield POC shape):
- `project-bootstrap`
- then `capture-references` (when external UI/UX, API, or stack research is needed)
- then `task-init`
- then `stack-recommend` (version-pinned stack for an empty workspace; the greenfield discovery step in place of `impact-analysis`)
- then `decision-interview` (lock the stack and approach), `implementation-plan`, `approve-plan`

## New task
Use:
- `task-init`
- `task-init` will assess complexity and recommend a pipeline tier (Express / Standard / Disciplined / Strict; see ADR-0025)
- follow the recommended next command from the handoff

## New task with clear scope and all decisions known
Use:
- `task-init` (complexity assessment will recommend Express tier)
- then `implementation-plan` (skip `impact-analysis` and `decision-interview`)
- then `implement-approved-slice`

## New task and still very unclear
Use:
- `task-init`
- then `impact-analysis`

## New task but you do not yet know which files to touch
Use:
- `task-init`
- then `code-locate` (populates `SOURCE_OF_TRUTH.md` with concrete candidates)
- then `impact-analysis`

## Resuming after lost context
Use:
- `resume-from-state`

## Task memory drift across artifacts
Use:
- `state-reconcile`
- `state-reconcile` in its read-only `memory-lint` mode (ADR-0053) when you want to surface dead cross-links, orphaned `SLICES/` files, and stale `TASK_STATE.md` facts without writing any repair

## Unsure what to do next
Use:
- `what-next`

## Want a guided explanation
Use:
- `workflow-guide`

## Stuck or looping
Use:
- `im-stuck`

## Concrete observed failure (stack trace, broken output, failing test, prod alert)
Use:
- `incident-triage`

## Ready to implement a defined slice
Use:
- `implement-approved-slice`

## Small follow-ups under an existing slice (micro-delta)
Use:
- `implement-slice-complement`

## Need a cleaner next prompt
Use:
- `prompt-shape`

## PR review feedback (corrective, same contract)
Use:
- `pr-feedback-ingest`

## PR or team feedback changes direction (pivot)
Use:
- `post-review-pivot`

## Whole task is finished (close and archive)
Use:
- `task-close`

Closes the whole task: gates on the done-conditions, writes the final `TASK_STATE.md`, and moves the folder from `active/` to `archive/`. Use `slice-closure` instead when only a single slice is ending.

---

## Specialized but valuable when their trigger arrives

These commands are not part of the default pipeline; invoke them when their specific trigger condition applies. A 60-day audit (2026-06-04, `_internal/command-classification-2026-06.md`) showed they are underused relative to when they would help. Fleet variants (`atom-audit-fleet`, `external-research-fleet`, `verify-against-rubric-fleet`, `screen-spec-fleet`, `task-init-fleet`) dispatched 2026-06-05; lived runs pending per ADR-0038.

### Reviewing an API contract before locking it
- `api-contract-review` -- run when you have a draft API or schema spec that needs to be locked into `DECISIONS.md` but want a structured review of edge cases, error shapes, versioning, and contract clarity first.

### Verifying design implementation matches the spec
- `design-spec-review` -- run after implementing a UI component or screen to check it against `docs/research/components/<tier>/<name>.md` or `docs/app/screens/<persona>/<name>.md`. Distinct from `review-hard` (general risk) and `repo-consistency-sweep` (pattern matching).

### Producing a deliverable for stakeholders
- `delivery-asset` -- run when stakeholders need an executive-friendly summary of a slice or task (not a PR). Distinct from `pr-package` (engineer audience).

### Responding to a production incident
- `incident-triage` -- run when you have a concrete observed failure (stack trace, broken output, failing test, prod alert). Distinct from `impact-analysis` (planned change).

### Documenting a reusable UX pattern
- `pattern-doc` -- run when you have noticed the same UX problem solved with the same shape across 3+ screens and want to formalize the pattern. Distinct from `component-spec` (per-component).

### Sharing async progress with non-coding stakeholders
- `team-update` -- run when stakeholders need a status update but not a delivery package. Distinct from `delivery-asset` (formal deliverable).

### Locking a plan before execution begins
- `approve-plan` -- run after `implementation-plan` (or `self-critique-and-revise`) when the user wants to atomically lock the plan as the approved baseline and stamp `TASK_STATE.md` with the approval signal. Symmetric to `approve-proposed` but plan-specific. Refuses on `[NEEDS CLARIFICATION:]` markers.

### Auditing design system atoms against shared guidelines
- `atom-audit` -- run every 2-4 weeks or when 5+ new atoms shipped to refresh `docs/research/ATOM_AUDIT.md` table (memo, callbacks, inline styles, press anim, touch target, a11y, reduced motion). Distinct from `foundation-audit` (token drift) and `design-spec-review` (single component).

### Refreshing the Figma component library inventory
- `inventory-snapshot` -- run after design ships a Figma library update or to seed the inventory at project start. Updates `docs/research/_inventory/figma_components.md` with traceability columns and delta vs previous snapshot. Distinct from `design-bootstrap` (first-time scaffold).

---

## Need to fan out independent work in parallel

There are two different parallel shapes; pick by what you are fanning out.

### Executing 2 or more independent approved slices (parallel slice execution)

Use: `implement-fleet` (per ADR-0041).

When to use: the approved plan's `## Execution waves` section shows a remaining wave of size 2 or more whose slices declare `Scope` and `Depends-on`. The wave-size sizing for research batches (below) does NOT apply here: two file-disjoint slices are enough to warrant a fleet. `implement-fleet` computes the waves, validates file-scope disjointness, runs one worktree-isolated worker per slice, and runs a build + typecheck + test integration gate after each wave.

When NOT to use: the slice DAG is a pure chain (every wave has size one) -- use `implement-approved-slice`; slices are unapproved -- run `approve-plan` first; `Scope`/`Depends-on` are not declared -- run `implementation-plan` in its annotate-only retrofit mode to backfill them.

A hand-authored Workflow script over already-approved slices is a contract bypass: it skips slice notes, wave computation, and the `TASK_STATE.md` writes the fleet owns. Route to `implement-fleet` instead.

### Fanning out 15-25 identical research or audit items (batch dispatch)

Recommended first command: review wos/workflow-patterns.md and check ADR-0038 + ADR-0039.

When to use: 15-25 independent items requiring identical read-only processing (e.g. eval batch updates, multi-doc consolidation, fleet audits, atom-by-atom analysis).

When NOT to use: tasks with shared substrate writes (use sequential), <10 items (overhead dominates), >25 items (split into 2 batches). This sizing is for research/audit batches, not for slice fleets.

Per-batch checklist: 300-500 word focused prompts; explicit StructuredOutput final-line reminder; scan-substrate-orphans.py post-apply; monitor-fleet-progress.sh during long runs.

Tools that support: Claude Code (Workflow tool). Other tools degrade to sequential.

References: ADR-0041 (slice fleets), ADR-0038, ADR-0039 (research batches), wos/workflow-patterns.md, wos/sub-agent-orchestration.md.

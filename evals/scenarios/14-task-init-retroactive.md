# Eval scenario 14: task-init retroactive on in-progress work

- **Tags**: task-init, retroactive-adoption, migration-guide-scenario, hand-edit-after-init
- **Last reviewed**: 2026-05-09
- **Status**: active

## Goal

Validates that `task-init` works correctly when the user is partway through an engineering task that did not use the workflow, and now wants to bring it under Fhorja without restarting. The proposal must reflect what is **already true** (existing branch, existing decisions, partial implementation) rather than pretending the work is starting over.

This is the primary scenario from `docs/MIGRATION.md` `## Adopting Fhorja on an in-progress task`. Validates that the migration guide's instructions actually produce the right artifact shapes.

This exercises:

- The retroactive-adoption flow.
- The placeholders + actual-state mix in the proposed artifacts.
- The `## Project-level memory` warning when `PROJECT_CHARTER.md` is missing.
- The Handoff routing forward to `state-reconcile` (recommended after retroactive adoption to confirm artifact consistency).

## Setup

The user has been working informally on a task: there is a feature branch `feat/customer-tier-discount` with 3 commits, a draft PR, and several decisions that exist only in chat history and a private notes file. They want to adopt Fhorja without restarting.

No `projects/acme__widget-pricing/` exists yet (the project was never bootstrapped). The user has decided to also retroactively bootstrap.

`PROJECT_CHARTER.md` does not exist for `acme__widget-pricing`.

## Input prompt

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task slug: 2026-05-09_customer-tier-discount
Description: Add tier-based discounts to the price query. We have 3 tiers (silver, gold, platinum) with 0/5/10 percent discounts respectively. The work is partway done: branch feat/customer-tier-discount has 3 commits implementing the tier lookup and the discount math; a draft PR is open. Tests are partially in place (one passing, one failing). I want to bring this under the workflow without restarting.

Existing decisions (from chat / notes; please record):
- D-1: Tier is read from the customer record; not from a separate join.
- D-2: Discounts apply only to the unit_price field, not to taxes or shipping.

Files already touched: src/handlers/prices.ts (modified), src/discount/tiers.ts (new), tests/discount/tiers.spec.ts (new, 1 passing 1 failing).

Mode: Ask
```

## Expected response shape

- Response begins with task-init's persona line.
- Response identifies that `projects/acme__widget-pricing/PROJECT_CHARTER.md` does not exist and emits a warning per the canonical rule: "project not bootstrapped: recommended to run `project-bootstrap` first to capture project-level context". The warning is informational; the task is NOT blocked.
- Response proposes the 5 mandatory task files under `projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/`.
- The proposed `SOURCE_OF_TRUTH.md` reflects the user's actual state: active branch is `feat/customer-tier-discount`; files in scope are the 3 named files; no `## Project-level memory` section because the project is not bootstrapped.
- The proposed `DECISIONS.md` includes D-1 and D-2 verbatim from the input (the user explicitly asked them to be recorded). Numbering preserved.
- The proposed `IMPLEMENTATION_PLAN.md` reflects the partial state: a `## Completed slices` (or equivalent) section listing what is already done (tier lookup, discount math, partial tests); the main slice-by-slice plan covers the remaining work (fix the failing test; complete the tier discount handler integration; ship). The plan does NOT pretend everything is unimplemented.
- The proposed `TASK_STATE.md`:
  - `## Current phase`: `implementation` (the user is mid-task, not in discovery)
  - `## Last completed step`: something like "manual implementation of tier lookup and discount math (3 commits on feat/customer-tier-discount)"
  - `## Current known facts`: includes the partial test status and the open failing test
  - `## Canonical decisions`: references D-1 and D-2
  - `## Recommended next step`: `state-reconcile` (recommended after retroactive adoption) or `implement-slice-complement` (if the failing test is small enough to fix without re-planning) or `implementation-plan` (if the remaining work needs slice planning)
- `### Handoff` block routes to one of the recommended next steps. `Mode:` is Ask.

## Pass criteria

1. **Project-not-bootstrapped warning**: the response includes the canonical warning when `PROJECT_CHARTER.md` is missing. The task is not blocked.
2. **Existing decisions recorded**: D-1 and D-2 from the input are in the proposed `DECISIONS.md` verbatim, with numbering preserved.
3. **Partial implementation reflected**: the proposed `IMPLEMENTATION_PLAN.md` has a `## Completed slices` (or equivalent) section listing what is already done. It does NOT pretend the work is starting from scratch.
4. **Current phase is implementation**: the proposed `TASK_STATE.md` `## Current phase` is `implementation` (or `review` if the work is closer to done), NOT `discovery` or `planning`.
5. **Active branch and files reflected**: `SOURCE_OF_TRUTH.md` lists the actual branch (`feat/customer-tier-discount`) and the 3 actual files. Generic placeholders are NOT used for facts the user supplied.
6. **No `## Project-level memory` section**: because the project is not bootstrapped, this section is omitted from `SOURCE_OF_TRUTH.md`.
7. **Routing forward to state-reconcile**: the `Run now:` recommendation is `state-reconcile` (the typical post-retroactive-adoption next step) or `implement-slice-complement` / `implementation-plan` if the next step is clear from the partial state. NOT `impact-analysis` (the work is past discovery) or `decision-interview` (decisions are already supplied).

## Failure modes to watch

- **Pretend-fresh-start**: the proposed `IMPLEMENTATION_PLAN.md` lists everything as `[to be planned]`, ignoring the 3 existing commits. Migration without retroactive recognition; the user has to manually re-do this.
- **Generic placeholders for supplied facts**: the proposed `SOURCE_OF_TRUTH.md` says `[unknown yet]` for the active branch when the user explicitly named it. Loss of input fidelity.
- **Missing project-not-bootstrapped warning**: the response silently creates the project folder without warning the user about the missing charter. The user does not know they should run `project-bootstrap` to fully normalize.
- **Decisions invented**: the proposed `DECISIONS.md` adds decisions beyond D-1 and D-2 that the user did not supply. Fabrication; the input is authoritative.
- **Wrong current phase**: `TASK_STATE.md` says `## Current phase: discovery` despite the user being mid-implementation. Symptom of the model not reading the input carefully.
- **Routing to impact-analysis**: the `Run now:` is `impact-analysis`. This is the standard post-task-init route but is wrong here; the task is past that phase.

## Notes

- Related ADRs: [ADR-0007](../../docs/adr/0007-project-level-memory.md) (project-level memory; retroactive bootstrap is the primary edge case noted in the ADR's edge-case section).
- Related commands: `commands/task-init.md`, `commands/project-bootstrap.md` (the recommended follow-up to fix the missing charter), `commands/state-reconcile.md` (the recommended next step to confirm artifact consistency after retroactive adoption).
- Related docs: [`docs/MIGRATION.md`](../../docs/MIGRATION.md) `## Adopting Fhorja on an in-progress task` is the user-facing documentation of this scenario. This eval validates that the migration guide's instructions produce the expected artifact shapes.
- The retroactive-adoption flow is one of the workflow's two main onboarding paths (the other is brand-new project + brand-new task, scenario 01). This scenario closes the loop by validating the harder of the two.

## History

- 2026-05-09: scenario authored. Initial pass criteria defined; not yet run against a model.

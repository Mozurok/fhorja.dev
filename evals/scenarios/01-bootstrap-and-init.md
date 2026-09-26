# Eval scenario 01: Fresh project bootstrap then first task

- **Tags**: project-bootstrap, task-init, project-level-memory, handoff
- **Last reviewed**: 2026-09-22
- **Status**: active

## Goal

Validates the **zero-state path** through the workflow: a user with no existing `projects/` content runs `project-bootstrap`, then `task-init`, and ends up with the canonical 2-file project layer plus the canonical 5-file task layer, with both responses ending in valid Handoff blocks that chain correctly.

This exercises:

- The project-level memory layer wiring (ADR-0007).
- Task-memory files are written and marked APPLIED in every mode.
- The adaptive handoff contract on two consecutive responses (ADR-0002).

## Setup

None. The scenario assumes a clean checkout of `my_work_tasks` and an empty (or non-existent) `projects/<client>__<project>/` for whatever throwaway identifier you choose.

## Input prompt (turn 1: project-bootstrap)

```text
Run @commands/project-bootstrap.md

Project: acme__widget-pricing
Objective: A backend service that computes per-customer widget prices based on contract tier and seasonal modifiers. Phase 1 is read-only price queries; future phases may add admin-side price overrides.
Stack: TypeScript, Node 20, Postgres 16 via Supabase, deployed on Fly.io.
Repositories: single repo (no multi-repo setup).
References: https://supabase.com/docs/reference/javascript/select (Supabase select docs)
Constraints: Must respect existing per-tenant RLS policies; no cross-tenant queries.
Non-goals: Not building admin UI in Phase 1.
Stakeholders: Product owner (you), engineering lead (you).
Mode: Ask
```

## Input prompt (turn 2: task-init, after reviewing turn 1)

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task slug: 2026-05-08_initial-price-query
Description: Implement the GET /v1/prices/:customer_id endpoint that returns the customer's effective price list. Contract is decided; schema is known; need to wire the handler, the DB query, and a focused integration test.
Mode: Ask
```

## Expected response shape (turn 1: project-bootstrap)

- Response begins with project-bootstrap's persona line and includes a `Mandatory context bootstrap:` section.
- `### Artifact changes` lists exactly 2 APPLIED files: `projects/acme__widget-pricing/PROJECT_CHARTER.md` and `projects/acme__widget-pricing/REFERENCES.md`. Plus the 2 directories `projects/acme__widget-pricing/active/` and `projects/acme__widget-pricing/archive/` (creation noted, not files).
- The proposed `PROJECT_CHARTER.md` contains all required sections: `## Project name`, `## Status` (= `active`), `## Objective`, `## Stack`, `## Default workspace` (used because zero or one repo), `## Constraints`, `## Non-goals`, `## Stakeholders`, `## Initial references`, `## Project-level memory pointers`. The `## Repositories` section is absent (single-repo project).
- The proposed `REFERENCES.md` has the canonical skeleton (`# REFERENCES`, `## Format reminder`, `## Entries`) and includes the seeded Supabase URL with `Accessed: 2026-05-08`, a `Summary:` paragraph, and `Tags:` containing at least one tag.
- `### Handoff` block ends the response with `Run now: /task-init`, `Mode: Ask`, `Work complexity: LOW` (or `N/A`), `Reason: <one line>`, and the adaptive handoff format (Mode A compact within same session, Mode B with `Resume context:` cross-session). In Mode B the block adds a `Resume context:` body carrying the `Project: acme__widget-pricing` line and the required inputs for `task-init`.

## Expected response shape (turn 2: task-init)

- Response references reading `projects/acme__widget-pricing/PROJECT_CHARTER.md` (or shows it was used to seed `SOURCE_OF_TRUTH.md`); does not warn that the project is not bootstrapped.
- `### Artifact changes` lists exactly 5 APPLIED files under `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/`: `README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`. None of `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, `DB_CONTEXT.md`, or `SLICES/` are created.
- The proposed `SOURCE_OF_TRUTH.md` includes a `## Project-level memory` section with relative pointers to `../../PROJECT_CHARTER.md` and `../../REFERENCES.md`.
- The proposed `TASK_STATE.md` follows the canonical structure (every required section present, including `## Recommended next step`, `## Work complexity (for next execution step)`, `## Resume notes`, `## Task scope level`, `## Current closure target`).
- The proposed `IMPLEMENTATION_PLAN.md` has at minimum: target behavior, current gaps, known constraints, initial expected phases or slices, unknowns blocking safe planning.
- `### Handoff` block ends the response with `Run now: <next>`. `<next>` follows the escalations `task-init` recorded, in Ask exactly as in Agent: the five files are written `APPLIED` in every mode (ADR-0199), so there is nothing to persist and `approve-proposed` is not the next step. With no escalation that is `implementation-plan`; an escalation adds its command ahead of it. `Mode:` is `Ask` or `Plan`. In Mode B the `Resume context:` body carries the active task path `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/`.

## Pass criteria

1. **Turn 1 - project layer**: `PROJECT_CHARTER.md` is written `APPLIED` with all 10 canonical sections and `REFERENCES.md` is written `APPLIED` with the seeded Supabase URL, in Ask as in Agent (ADR-0215), so turn 2's `task-init` can read the charter it seeds from; `## Repositories` section is **absent** in the charter (single-repo project).
2. **Turn 1 - Handoff**: Handoff block is present, fenced as `text`, and its first line is `Run now: task-init` (a `commands/` basename, with or without a leading slash). No `Run now:` line is missing or empty.
3. **Turn 2 - 5 task files**: `### Artifact changes` lists exactly 5 APPLIED task files; no optional task files are created. The substrate log `.wos/VERIFICATION_LOG.jsonl` is not a task file and does not count: every substrate write appends to it (ADR-0034), so listing it is correct. Measured 2026-09-22: a run that listed it was graded UNCERTAIN on this criterion for that reason alone.
4. **Turn 2 - project memory wiring**: proposed `SOURCE_OF_TRUTH.md` references `../../PROJECT_CHARTER.md` and `../../REFERENCES.md` under a `## Project-level memory` section.
5. **Turn 2 - TASK_STATE schema**: every required section in the canonical `TASK_STATE` structure is present in the proposal.
6. **Turn 2 - Handoff**: the block's first line is `Run now: <next>` naming a real `commands/` basename. `<next>` follows the recorded escalations and is not `approve-proposed` (ADR-0199). This criterion has now been wrong twice, both times by lagging an ADR: written for the Agent route, it failed a correct Ask run on 2026-09-01 and was rewritten for ADR-0190, which routed Ask to `approve-proposed`; ADR-0199 removed that route on 2026-09-16 and the criterion was not revised until 2026-09-22. In Mode B the `Resume context:` body carries the active task path.
7. **No fabricated context**: Neither response invents a stack, a repo URL, a constraint, or a stakeholder beyond what the input prompt provided. Where information is missing, explicit placeholders like `[unknown yet]` or `[not decided yet]` are used.

## Failure modes to watch

- **Premature task creation in turn 1**: `project-bootstrap` is **not allowed** to create the task folder. If turn 1's output proposes any file under `projects/acme__widget-pricing/active/2026-05-08_*/`, this is a regression.
- **Multi-repo schema misuse**: turn 1's `PROJECT_CHARTER.md` includes a `## Repositories` section even though the user said "single repo". The schema must be omitted entirely for zero-or-one-repo projects.
- **Project-not-bootstrapped warning in turn 2**: turn 2's `task-init` warns "project not bootstrapped" even though turn 1 already created the charter. This indicates `task-init` did not actually read the charter (or read a stale snapshot).
- **Missing Handoff or slash-only routing**: either response ends without a complete Handoff, or the adaptive handoff block is just `/task-init` with no task path or required inputs.
- **PROPOSED instead of APPLIED**: the response withholds the write because the mode is Ask. That is the removed ADR-0001 gate returning.
- **Section reordering in TASK_STATE.md**: the canonical structure is normative; reordering or renaming sections breaks downstream commands that grep for them.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md), [ADR-0007](../../docs/adr/0007-project-level-memory.md).
- Related commands: `commands/project-bootstrap.md`, `commands/task-init.md`.
- Related shared blocks: `commands/_shared/handoff-body.md`, `commands/_shared/standard-output-layout.md`, `commands/_shared/artifact-changes-default.md`.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.

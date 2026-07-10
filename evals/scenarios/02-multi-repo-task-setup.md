# Eval scenario 02: Multi-repo task setup

- **Tags**: task-init, multi-repo, source-of-truth, schema-validation
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `task-init` correctly emits the `## Repositories` schema in `SOURCE_OF_TRUTH.md` when the task touches 2 or more repositories, with identifier validation (lowercase, hyphenated, unique) and all 4 fields per entry (identifier, path, base branch, role).

This exercises:

- Multi-repo support v1 schema (spec `## Multi-repo support (v1)` and `wos/multi-repo-support.md`).
- The `task-init` Operating rule that enforces single-repo backwards-compat (no `## Repositories` section when 1 or 0 repos).
- The locked decisions D1-D7 and invariants I1-I4 from `wos/multi-repo-support.md`.

## Setup

Assume `projects/acme__shipping-platform/` already exists with a valid `PROJECT_CHARTER.md` (no need to actually have it on disk; the prompt below stands in for it). Throwaway identifier; substitute as you like.

## Input prompt

```text
Run @commands/task-init.md

Project: acme__shipping-platform
Task slug: 2026-05-08_label-printer-rollout
Description: Add a new label-printer integration that the backend exposes as POST /v1/labels and the frontend renders inside the order-detail page. Touches the backend API and frontend SPA simultaneously.
Mode: Ask
Repositories:
  - identifier: shipping-api
    path: ~/code/shipping-api
    base branch: origin/main
    role: backend
  - identifier: shipping-web
    path: ~/code/shipping-web
    base branch: origin/staging
    role: frontend
  - identifier: shared-types
    path: ~/code/shared-types
    base branch: origin/main
    role: shared
```

## Expected response shape

- Response begins with task-init's persona line.
- `### Artifact changes` lists exactly 5 PROPOSED files under `projects/acme__shipping-platform/active/2026-05-08_label-printer-rollout/`: `README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`.
- The proposed `SOURCE_OF_TRUTH.md` includes a `## Repositories` section with **exactly 3 entries** (shipping-api, shipping-web, shared-types).
- Each entry has all 4 fields: `identifier`, `path`, `base branch`, `role`. No field is missing or empty.
- All identifiers are lowercase, hyphenated, and unique (the prompt provides valid identifiers; the task should preserve them, not transform them).
- Roles use the canonical vocabulary from the spec's multi-repo schema: `backend`, `frontend`, `shared`, `infra`, `mobile`, `other`. No invented roles like `api`, `ui`, `lib`.
- The proposed `SOURCE_OF_TRUTH.md` does **not** also have an "active codebase / repo" single-repo field replicating one of the entries (in multi-repo mode, the per-repo schema replaces the single-repo field for those 3 repos).
- `### Handoff` block ends the response. `Run now:` is one of `impact-analysis`, `targeted-questions`, or `decision-interview` (typical post-init). adaptive handoff block starts with `Run @commands/<next>.md` and includes the active task folder path on its own line.

## Pass criteria

1. **Schema present**: `SOURCE_OF_TRUTH.md` includes a `## Repositories` section.
2. **Three entries**: the section has exactly 3 entries matching the input (shipping-api, shipping-web, shared-types). No invented or dropped entries.
3. **All four fields per entry**: identifier, path, base branch, role. None missing.
4. **Identifier validation**: identifiers preserved as lowercase + hyphens + unique. No `Shipping_API` or `shippingApi` transformations.
5. **Canonical roles**: all 3 roles are from `{backend, frontend, shared, infra, mobile, other}`. The role for `shared-types` is `shared`, not `lib` or `types`.
6. **No double declaration**: the proposed `SOURCE_OF_TRUTH.md` does not also have a single-repo "active codebase / repo" line listing one of the multi-repo entries; multi-repo replaces the single-repo field for those repos.
7. **Handoff intact**: the response ends with a complete Handoff block; adaptive handoff block has the active task path.

## Failure modes to watch

- **Schema omitted**: response treats this as a single-repo task and omits `## Repositories`. This is a regression of the multi-repo entry condition (schema is present when N >= 2; the task has N=3).
- **Schema present but malformed**: only 2 of 4 fields per entry (e.g., identifier and path but no base branch or role).
- **Invented roles**: `api`, `ui`, `lib`, `service` instead of the canonical `{backend, frontend, shared, infra, mobile, other}`.
- **Identifier transformation**: the response renames `shipping-api` to `shipping_api` or `shippingApi`. Identifiers are user-provided and must be preserved verbatim.
- **Stub identifiers**: response uses placeholders like `repo-1`, `repo-2`, `repo-3` instead of the user-provided values.
- **Cross-repo coordination leak**: the proposed `IMPLEMENTATION_PLAN.md` invents cross-repo deploy ordering or rollout steps the user did not specify. Multi-repo coordination notes belong in `TASK_STATE.md` `Risks to watch` and per-PR cross-references; this scenario is task creation, not planning.

## Notes

- Related ADRs: [ADR-0007](../../docs/adr/0007-project-level-memory.md) (project layer multi-repo schema is the source for task-level mirroring).
- Related commands: `commands/task-init.md`. Per [the spec `## Multi-repo support (v1)`](../../WORKFLOW_OPERATING_SYSTEM.md#multi-repo-support-v1) and `wos/multi-repo-support.md` for the full schema, locked decisions D1-D7, invariants I1-I4, non-goals NG1-NG5.
- The 7 deferred-to-v2 commands (`targeted-questions`, `implement-approved-slice`, `implement-slice-complement`, `slice-closure`, `where-we-at`, `pr-feedback-ingest`, `post-review-pivot`) are NOT exercised by this scenario; they would silently treat the multi-repo task as single-repo. That is by design in v1.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.

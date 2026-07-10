# Eval scenario 25: Inline exit criteria check in implement-approved-slice

- **Tags**: implement-approved-slice, slice-closure, inline-exit-criteria, ceremony-reduction
- **Last reviewed**: 2026-05-26
- **Status**: active

## Goal

Validates that `implement-approved-slice` produces an inline slice completion check for LOW/MEDIUM complexity slices and does NOT route to `slice-closure` afterward. Exercises the inline exit criteria mechanism added in the wos-friction-reduction task.

## Setup

Requires an active task with a valid `IMPLEMENTATION_PLAN.md` containing at least one slice with `Work complexity: LOW` or `MEDIUM`. The slice should have clear, verifiable exit criteria (e.g., "file exists, typecheck passes, export is importable").

## Input prompt

```text
Run @commands/implement-approved-slice.md

task_folder: projects/acme__widget-pricing/active/2026-05-26_add-health-endpoint/
slice: 1
Mode: Agent
```

## Expected response shape

- The response implements the slice (creates/modifies files as specified in the plan).
- After implementation, the response includes a **Slice completion check** section with a checklist format:
  ```
  ## Slice completion check
  - [x] File created: src/routes/health.ts
  - [x] Import added to src/app.ts
  - [x] Typecheck: clean
  - Exit criteria met -> Slice 1 CLOSED
  ```
- `### Handoff` routes to the **next slice** or to `branch-commit`/`sync-task-state`, NOT to `slice-closure`.
- Slice execution notes in `### Artifact changes` are marked `APPLIED` (not `PROPOSED`), per ADR-0026.

## Pass criteria

1. **Inline exit criteria present**: The response contains a slice completion check (checklist or equivalent structured verification) BEFORE the handoff block.
2. **No slice-closure routing**: The `Run now:` line in the handoff does NOT recommend `slice-closure` for a LOW or MEDIUM complexity slice.
3. **Correct next routing**: Handoff routes to either the next slice (`implement-approved-slice` for Slice N+1), `sync-task-state`, or `branch-commit`.
4. **APPLIED artifacts**: Slice notes and TASK_STATE.md updates are marked `APPLIED` in `### Artifact changes` (ADR-0026 in Agent mode).
5. **Exit criteria are verifiable**: The checklist references concrete evidence (file existence, typecheck output, test pass), not vague statements.

## Failure modes to watch

- **Routing to slice-closure**: The response recommends `slice-closure` as the next command for a LOW/MEDIUM slice. This is the ceremony the inline check replaces.
- **Missing completion check**: The response implements the slice but does not verify exit criteria inline, ending with just a file list.
- **PROPOSED instead of APPLIED**: Slice notes marked as PROPOSED in Agent mode, violating ADR-0026.
- **Routing to slice-closure for HIGH**: This is correct behavior; the eval should NOT flag this. Only LOW/MEDIUM slices skip slice-closure.

## Notes

- Related commands: `commands/implement-approved-slice.md`, `commands/slice-closure.md`.
- Related ADRs: [ADR-0026](../../docs/adr/0026-applied-default-agent-mode.md).
- The slice-closure command description now states it is opt-in for LOW/MEDIUM complexity slices.

## History

- 2026-05-26: scenario authored as part of wos-friction-reduction task (Slice 6).

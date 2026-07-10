# Eval scenario 26: APPLIED-by-default for implement-approved-slice in Agent mode

- **Tags**: implement-approved-slice, applied-default, ADR-0026, write-policy
- **Last reviewed**: 2026-05-26
- **Status**: active

## Goal

Validates that `implement-approved-slice` in Agent mode marks slice execution notes as `APPLIED` (not `PROPOSED`), while the same command in Ask mode marks them as `PROPOSED`. Exercises the ADR-0026 exception to the PROPOSED-by-default contract.

This is a two-turn scenario: turn 1 runs in Ask mode (PROPOSED expected), turn 2 runs in Agent mode (APPLIED expected).

## Setup

Requires an active task with a valid `IMPLEMENTATION_PLAN.md` containing at least two slices.

## Input prompt (turn 1: Ask mode)

```text
Run @commands/implement-approved-slice.md

task_folder: projects/acme__widget-pricing/active/2026-05-26_add-health-endpoint/
slice: 1
Mode: Ask
```

## Input prompt (turn 2: Agent mode)

```text
Run @commands/implement-approved-slice.md

task_folder: projects/acme__widget-pricing/active/2026-05-26_add-health-endpoint/
slice: 2
Mode: Agent
```

## Expected response shape (turn 1: Ask mode)

- `### Artifact changes` lists slice file and/or TASK_STATE.md updates as **PROPOSED**.
- Product code changes are described but NOT applied (Ask mode).
- The response follows the standard PROPOSED-by-default contract from ADR-0001.

## Expected response shape (turn 2: Agent mode)

- `### Artifact changes` lists slice file and/or TASK_STATE.md updates as **APPLIED**.
- Product code changes ARE applied (Agent mode, files written to disk).
- The response explicitly uses APPLIED for task-memory artifacts, per ADR-0026.

## Pass criteria

1. **Turn 1 - PROPOSED in Ask mode**: Slice execution notes are marked `PROPOSED` in `### Artifact changes`. This confirms ADR-0001 is still the default.
2. **Turn 2 - APPLIED in Agent mode**: Slice execution notes are marked `APPLIED` in `### Artifact changes`. This confirms ADR-0026 exception is active.
3. **Product code distinction**: Turn 1 describes but does not write product code. Turn 2 writes product code. Both turns handle task-memory artifacts according to their respective mode rules.
4. **No mode confusion**: The response explicitly acknowledges which mode it is operating in and applies the correct write policy.

## Failure modes to watch

- **APPLIED in Ask mode**: Turn 1 marks slice notes as APPLIED. This is a regression of ADR-0001.
- **PROPOSED in Agent mode**: Turn 2 marks slice notes as PROPOSED. This means ADR-0026 was not picked up.
- **Blanket APPLIED**: Other commands (not implement-approved-slice) start using APPLIED in Ask mode after this change. The exception is scoped to one command in one mode.
- **Missing Handoff in either turn**: Both turns must end with a complete `### Handoff` block.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0026](../../docs/adr/0026-applied-default-agent-mode.md).
- Related commands: `commands/implement-approved-slice.md`.
- The spec `## Global output contract` `### Task-memory write policy (default)` now documents the ADR-0026 exception.

## History

- 2026-05-26: scenario authored as part of wos-friction-reduction task (Slice 6).

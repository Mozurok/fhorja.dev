# Eval scenario 26: task-memory writes are APPLIED in every mode

- **Tags**: implement-approved-slice, applied-default, write-policy, mode-independence
- **Last reviewed**: 2026-05-26
- **Status**: active

## Goal

Validates that `implement-approved-slice` marks slice execution notes `APPLIED` regardless of mode. The Ask-versus-Agent distinction this scenario used to grade was the ADR-0001 write gate, removed on 2026-09-16; the scenario now grades its absence, which is where a regression would show. Exercises the ADR-0026 exception to the PROPOSED-by-default contract.

This is a two-turn scenario: turn 1 runs in Ask mode, turn 2 in Agent mode. Both expect APPLIED for task-memory. What still differs between them is product code, not the write policy.

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

- `### Artifact changes` lists slice file and/or TASK_STATE.md updates as **APPLIED**, the same as turn 2 (ADR-0199).
- Product code changes are described but NOT applied (Ask mode).
- The response does not cite ADR-0001 or ADR-0026 as a reason to propose rather than write.

## Expected response shape (turn 2: Agent mode)

- `### Artifact changes` lists slice file and/or TASK_STATE.md updates as **APPLIED**.
- Product code changes ARE applied (Agent mode, files written to disk).
- The response explicitly uses APPLIED for task-memory artifacts, per ADR-0199.

## Pass criteria

1. **Turn 1 - APPLIED in Ask mode**: Slice execution notes are marked `APPLIED` in `### Artifact changes`. A `PROPOSED` mark here is the regression this criterion exists to catch: it means the removed mode gate came back.
2. **Turn 2 - APPLIED in Agent mode**: Slice execution notes are marked `APPLIED` in `### Artifact changes`, identically to turn 1. ADR-0026 carved an exception out of a rule that no longer exists, so there is nothing left to except.
3. **Product code distinction**: Turn 1 describes but does not write product code. Turn 2 writes product code. Both turns handle task-memory artifacts the same way: written and marked `APPLIED`.
4. **No mode confusion**: The response does not vary its task-memory write policy by mode, and does not cite ADR-0001 or ADR-0026 as a reason to propose rather than write.

## Failure modes to watch

- **PROPOSED in either mode**: a turn marks task-memory notes PROPOSED because of the editor mode. That is the removed gate returning, and it is the primary failure this scenario watches for.
- **PROPOSED in Agent mode**: Turn 2 marks slice notes as PROPOSED. This means the ADR-0199 write policy was not picked up.
- **Missing Handoff in either turn**: Both turns must end with a complete `### Handoff` block.

## Notes

- Related ADRs: [ADR-0199](../../docs/adr/0199-task-memory-is-written-not-proposed.md) (the policy graded here), [ADR-0001](../../docs/adr/0001-proposed-by-default.md) and [ADR-0026](../../docs/adr/0026-applied-default-agent-mode.md) (the gate and the exception it superseded).
- Related commands: `commands/implement-approved-slice.md`.
- The spec `## Global output contract` `### Task-memory write policy (default)` now documents the ADR-0026 exception.

## History

- 2026-05-26: scenario authored as part of wos-friction-reduction task (Slice 6).

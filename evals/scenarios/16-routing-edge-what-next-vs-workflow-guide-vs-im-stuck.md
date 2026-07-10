# Eval scenario 16: routing-edge: what-next vs workflow-guide vs im-stuck

- **Tags**: routing-edge, what-next, workflow-guide, im-stuck, command-distinctness
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates that the three "I am not sure what to do next" commands stay distinct in the model's routing decisions. The wrong choice cascades into wrong work: `what-next` for a brand-new task fails because there is no state to route from; `workflow-guide` for an experienced user adds unnecessary teaching; `im-stuck` for a normal phase transition is heavy-handed. The scenario presents an ambiguous user prompt where two of the three are plausible; the model must pick the right one based on the actual signals.

## Setup

Active task at `projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/`. The task has:
- `TASK_STATE.md` `## Current phase`: `planning` (impact-analysis done; implementation-plan not yet started)
- `DECISIONS.md`: D-1 and D-2 locked; D-3 open
- `IMPLEMENTATION_PLAN.md`: does not yet exist
- `SLICES/`: empty

The user has just resumed after a 2-day break. They are uncertain whether to refresh context first or proceed straight to planning.

## Input prompt

```text
I picked this back up after a couple of days off. I have an active task at projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/. TASK_STATE.md says we are in planning phase, IMPACT_ANALYSIS.md is done, but I am not sure what to do next. What command should I run?

Mode: Ask
```

## Expected response shape

- Response routes to exactly one of `what-next`, `workflow-guide`, or `im-stuck`.
- Routing rationale names the signal that disqualifies the other two.
- `### Handoff` is complete with adaptive handoff block that starts with `Run @commands/<chosen>.md`.

## Pass criteria

1. **Picks `what-next`**: the active task has fresh state (planning phase named; impact-analysis done; decisions partially locked); the user is not stuck in a loop; they are not new to the workflow. `what-next` is the right routing command.
2. **Disqualifies `im-stuck` explicitly**: response names that there is no loop, no stuck state, no false-progress - `im-stuck` is for confusion / loop recovery, not for "I lost context".
3. **Disqualifies `workflow-guide` explicitly**: response names that workflow-guide is pedagogical (for users learning the workflow); the current user is experienced enough to skip the teaching surface; a 2-day break is normal, not novice-onboarding.
4. **Considers `resume-from-state` as a candidate** and either picks it OR disqualifies it: a 2-day break IS a strong signal for resume-from-state. Acceptable answers: (a) `what-next` after a quick state-summary; (b) `resume-from-state` if the model decides the 2-day break warrants full reconstruction. If `resume-from-state` is picked, criteria 1-3 still apply for distinguishing the three above.
5. **Handoff**: block starts with `Run now: /<chosen>` and in Mode B includes the task folder path.
6. **No invented state**: response does not pretend to know decisions D-1/D-2 content, what IMPLEMENTATION_PLAN.md would look like, or what the next slice would be.

## Failure modes to watch

- **Picks workflow-guide**: signals the model is over-explaining; the user's question implies fluency, not novice-onboarding.
- **Picks im-stuck without "stuck" evidence**: a 2-day break is normal context loss; loop recovery is for repeated failures or circular logic.
- **Routes to multiple commands without disqualifying**: violates the routing contract (one primary next command).
- **Fabricates task state**: invents decisions, slices, or phases not described in the setup.

## Notes

- Related ADRs: [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md), [ADR-0008](../../docs/adr/0008-operating-modes.md).
- Related commands: `commands/what-next.md`, `commands/workflow-guide.md`, `commands/im-stuck.md`, `commands/resume-from-state.md`.
- This is the first routing-edge scenario added in slice 08 of the 2026-05-15 context-engineering uplift.

## History

- 2026-05-18: scenario authored as routing-edge test 1 of 4 in slice 08.

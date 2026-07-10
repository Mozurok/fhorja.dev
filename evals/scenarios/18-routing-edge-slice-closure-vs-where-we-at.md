# Eval scenario 18: routing-edge: slice-closure vs where-we-at

- **Tags**: routing-edge, slice-closure, where-we-at, single-slice-vs-macro-checkpoint
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates that the model correctly distinguishes single-slice closure (closing one slice; tactical) from macro checkpoint (assessing multi-slice/multi-phase progress; strategic). The scenario varies the task shape so the right choice is non-obvious without reading the actual artifacts.

## Setup

Two variants of the scenario; the model is given ONE of them per run.

**Variant A: single-slice task just finished its only slice.**

Active task at `projects/acme__widget-pricing/active/2026-05-12_fix-pricing-rounding/`. The task is one slice (a rounding bug fix). The slice was just implemented. The user asks what command to run.

**Variant B: multi-slice task finished slice 3 of 5.**

Active task at `projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/`. The task is 5 slices. Slice 3 (tier lookup) just closed. Slice 4 (discount math) is the planned next slice. The user asks what command to run.

## Input prompt

Use ONE of these:

```text
[VARIANT A]
Active task: projects/acme__widget-pricing/active/2026-05-12_fix-pricing-rounding/
The task has exactly one slice (a rounding bug fix). I just implemented it. What command do I run next?
Mode: Ask
```

```text
[VARIANT B]
Active task: projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/
The task is 5 slices. Slice 3 (tier lookup) just closed cleanly. Slice 4 (discount math) is next per IMPLEMENTATION_PLAN.md. What command do I run next?
Mode: Ask
```

## Expected response shape

- Response picks `slice-closure` OR `where-we-at` (or names both with explicit ordering).
- Routing rationale grounds in task shape (number of slices, position in the plan).

## Pass criteria

1. **Variant A picks slice-closure**: single-slice task; closing the one slice IS closing the task. `where-we-at` is heavy for a 1-slice task (no multi-slice macro to assess). Acceptable: route to `slice-closure` AND foreshadow `pr-package` as the post-closure step.
2. **Variant B picks slice-closure**: slice 3 just closed; the next move is to formalize the slice-closure for slice 3 specifically before moving to slice 4. `where-we-at` would be appropriate at end-of-Wave (multi-slice retrospective) but not after a single mid-plan slice close.
3. **Acceptable alternative for Variant B**: route to slice-closure (for slice 3) first, then `where-we-at` macro checkpoint if the user has not run one since the task started (heuristic: "have we checked task-level progress recently?"). If both are recommended, slice-closure is primary.
4. **No invented results**: response does not claim the slice was OK (or NOT OK); the user only said "just closed cleanly" (Variant B) or "just implemented" (Variant A). Closing requires the closure command to actually run.
5. **Handoff complete**: adaptive handoff block starts with `Run @commands/<chosen>.md` and includes the task folder path.
6. **Mode aligned**: Mode is Ask (review-shaped); not Plan; not Agent.

## Failure modes to watch

- **Variant A picks where-we-at**: macro checkpoint on a single-slice task is over-engineering; signals the model is not reading task shape.
- **Variant B picks where-we-at primary**: misses that slice 3 needs formal closure first; macro checkpoint should follow slice closure, not replace it.
- **Variant A picks pr-package directly**: skips slice-closure; the slice was implemented but not validated and formally closed. Closure is the bridge.
- **Same response for both variants**: signals the model is not reading the task shape (variant difference is the entire point).

## Notes

- Related ADRs: [ADR-0009](../../docs/adr/0009-task-shape-system.md) (task shape system; single-slice vs multi-slice).
- Related commands: `commands/slice-closure.md`, `commands/where-we-at.md`.

## History

- 2026-05-18: scenario authored as routing-edge test 3 of 4 in slice 08. Two-variant format unusual but justified: the routing decision depends on task shape, which is the entire point of the edge.

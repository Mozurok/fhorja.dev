# Eval scenario 08: Operating modes (minimal vs strict)

- **Tags**: operating-modes, minimal, strict, ceremony-control, contract-preservation
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that the `minimal` and `strict` operating modes correctly adjust ceremony for the **same** request, while preserving the load-bearing contracts (Handoff block, PROPOSED-by-default writes, no fabrication). Run as a paired comparison so deviations from each mode are visible side-by-side.

This exercises:

- The orthogonality of operating mode (per-task posture) from editor mode and output depth (per-command knobs).
- The minimal-mode trim of optional ceremony without skipping the Handoff contract.
- The strict-mode mandate for `invariants-and-non-goals`, `test-strategy`, and `review-hard`.
- The shared properties that operating mode does NOT override (PROPOSED in Ask; Handoff present; no fabrication).

## Setup

The same task spec, run twice in different operating modes. Use a clean active task at `projects/acme__widget-pricing/active/2026-05-08_add-currency-symbol/` for both runs.

## Input prompt (run 1: minimal)

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task slug: 2026-05-08_add-currency-symbol
Description: Append the customer's currency symbol to the JSON returned by GET /v1/prices/:customer_id. The currency code is already in the response; we just need to look up the symbol and append it as `currency_symbol`. Trivial change; one new field; no schema migration; no contract change for existing clients (additive).
Operating mode: minimal
Mode: Ask
```

Then (after task-init proposes the 5 mandatory files):

```text
Run @commands/implementation-plan.md

Active task: projects/acme__widget-pricing/active/2026-05-08_add-currency-symbol/
Mode: Plan
```

## Input prompt (run 2: strict)

Reset the task folder (or use a different slug for the same scenario, e.g., `2026-05-08_add-currency-symbol-strict`). Then:

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task slug: 2026-05-08_add-currency-symbol-strict
Description: Append the customer's currency symbol to the JSON returned by GET /v1/prices/:customer_id. The currency code is already in the response; we just need to look up the symbol and append it as `currency_symbol`. Trivial change; one new field; no schema migration; no contract change for existing clients (additive).
Operating mode: strict
Mode: Ask
```

Then run `implementation-plan` against the strict task folder.

## Expected response shape (minimal run)

- `task-init` records `Operating mode: minimal` in the proposed `TASK_STATE.md` `## Resume notes`.
- The proposed `IMPLEMENTATION_PLAN.md` (from the second turn) is short: one slice with objective / scope / exit criteria, marked `Work complexity: LOW`. No mandatory `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, or `TEST_STRATEGY.md` is created.
- The response output depth is `Lean`: the `### Command transcript` is short (no more than 2-3 lines), the `Why this mode:` block in the response is summarized to one line (canonical content stays in the command file).
- `### Handoff` block is **fully present** despite minimal mode. `Run now:` recommends `implement-approved-slice`. adaptive handoff block has the task path and slice file pointer.

## Expected response shape (strict run)

- `task-init` records `Operating mode: strict` in the proposed `TASK_STATE.md` `## Resume notes`.
- The proposed `IMPLEMENTATION_PLAN.md` references that `invariants-and-non-goals` and `test-strategy` will be required before `implement-approved-slice` (or it routes to `invariants-and-non-goals` as the next step instead of `implement-approved-slice`).
- The response output depth is `Deep`: the `### Command transcript` may be 4 lines (max for normal runs); the `Why this mode:` and `### Definition of done` blocks are full, not summarized.
- The recommendation in the Handoff is `invariants-and-non-goals` (or `targeted-questions` if the task spec leaves any factual gap), not `implement-approved-slice`. Strict mode will not skip to execution without the additional ceremony.
- The proposed plan (or the response transcript) includes a "rollback / unwind" note for the change.
- `### Handoff` block is fully present.

## Pass criteria

1. **Mode persisted (minimal)**: the proposed `TASK_STATE.md` `## Resume notes` for the minimal run includes `Operating mode: minimal`.
2. **Mode persisted (strict)**: same for the strict run with `Operating mode: strict`.
3. **Minimal trims optional files**: the minimal run never proposes `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, or `TEST_STRATEGY.md`.
4. **Strict mandates additional commands**: the strict run's Handoff routes to `invariants-and-non-goals` (or `targeted-questions` if facts are missing) before `implement-approved-slice`.
5. **Both preserve Handoff**: both runs end with a complete `### Handoff` block. Operating mode does NOT short-circuit the Handoff contract.
6. **Both preserve PROPOSED writes**: both runs use `PROPOSED` in `### Artifact changes` (Ask mode + PROPOSED-by-default; operating mode does not override).
7. **Both avoid fabrication**: neither run invents details about the currency symbol lookup mechanism beyond what the task description provides. If the lookup table is unspecified, both runs surface that as an open question.
8. **Output depth matches mode**: minimal's transcript is short (Lean); strict's transcript and Why blocks are fuller (Deep). Verifiable by reading both outputs side-by-side.

## Failure modes to watch

- **Mode ignored**: response treats both runs identically. The `Operating mode: minimal` (or strict) line is recorded in `TASK_STATE.md` but does not affect command behavior.
- **Minimal skips Handoff**: minimal mode trims so aggressively that the Handoff block is shortened, abbreviated, or omitted. Operating mode does NOT override the Handoff contract.
- **Strict bypasses ceremony**: strict mode declares `invariants-and-non-goals` mandatory but the response routes directly to `implement-approved-slice` anyway, ignoring its own declared posture.
- **Mode drift across commands**: `task-init` records the mode but the subsequent `implementation-plan` run does not read `TASK_STATE.md` to discover it, and adapts as if the mode was unset.
- **Wrong mode chosen for the task**: a more nuanced failure mode the eval cannot detect mechanically. The currency-symbol change is genuinely XS (pure additive, single field, no contract impact), so minimal is the right call. A user who declared strict on this task is misusing the posture; the response should still operate under strict (it does what it is told) but the eval reveals that the friction is wasted.

## Notes

- Related ADRs: [ADR-0008](../../docs/adr/0008-operating-modes.md) (operating modes design), [ADR-0001](../../docs/adr/0001-proposed-by-default.md) (PROPOSED-by-default; not overridden by mode), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md) (Handoff contract; not overridden by mode).
- Related spec sections: `## Operating modes`, `## Output depth policy`, `## Editor mode policy`.
- Side-by-side comparison is the test: run both prompts, then diff the responses. The differences should match the spec rules; everything else should be identical.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.

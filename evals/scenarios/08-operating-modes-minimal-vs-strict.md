# Eval scenario 08: Operating modes (minimal vs strict)

- **Tags**: operating-modes, minimal, strict, ceremony-control, contract-preservation, one-slice-route, ADR-0225
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

Validates that the `minimal` and `strict` operating modes correctly adjust ceremony for the **same** request, while preserving the load-bearing contracts (Handoff block, task-memory writes marked APPLIED in every mode, no fabrication). Run as a paired comparison so deviations from each mode are visible side-by-side.

This exercises:

- The orthogonality of operating mode (per-task posture) from editor mode and output depth (per-command knobs).
- The minimal-mode trim of optional ceremony without skipping the Handoff contract.
- The strict-mode mandate for `invariants-and-non-goals`, `test-strategy`, and `review-hard`.
- The shared properties that operating mode does NOT override (task-memory written and marked APPLIED; Handoff present; no fabrication).

## Setup

The same task spec, run twice in different operating modes, each in its own clean task repository. The spine runner builds one per run with `evals/fixtures/spine/08-operating-modes.sh` and substitutes it for `{fixture}`, so the strict run can neither read the minimal run's conversation nor its files. For a manual run, use two empty git repositories.

## Input prompt (run 1: minimal)

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task repository: {fixture}
Task slug: 2026-05-08_add-currency-symbol
Description: Append the customer's currency symbol to the JSON returned by GET /v1/prices/:customer_id. The currency code is already in the response; we just need to look up the symbol and append it as `currency_symbol`. Trivial change; one new field; no schema migration; no contract change for existing clients (additive).
Operating mode: minimal
Mode: Ask
```

Then (after task-init proposes the 5 mandatory files):

```text
Run @commands/implementation-plan.md

Active task: {fixture}/projects/acme__widget-pricing/active/2026-05-08_add-currency-symbol/
Mode: Plan
```

## Input prompt (run 2: strict)

A fresh task repository, with a different slug so the two are never confused:

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task repository: {fixture}
Task slug: 2026-05-08_add-currency-symbol-strict
Description: Append the customer's currency symbol to the JSON returned by GET /v1/prices/:customer_id. The currency code is already in the response; we just need to look up the symbol and append it as `currency_symbol`. Trivial change; one new field; no schema migration; no contract change for existing clients (additive).
Operating mode: strict
Mode: Ask
```

Then (after task-init proposes the 5 mandatory files):

```text
Run @commands/implementation-plan.md

Active task: {fixture}/projects/acme__widget-pricing/active/2026-05-08_add-currency-symbol-strict/
Mode: Plan
```

The two runs now send the same two commands. Until 2026-09-22 the strict run's `implementation-plan` step sat outside a fenced block, so the runner never sent it, and criterion 8 compared a two-command minimal run against a one-command strict run.

## Expected response shape (minimal run)

- `task-init` records `Operating mode: minimal` in the proposed `TASK_STATE.md` `## Resume notes`.
- The proposed `IMPLEMENTATION_PLAN.md` (from the second turn) is short: one slice with objective / scope / exit criteria, marked `Work complexity: LOW`. No mandatory `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, or `TEST_STRATEGY.md` is created.
- The response output depth is `Lean`: the `### Command transcript` is short (no more than 2-3 lines), the `Why this mode:` block in the response is summarized to one line (canonical content stays in the command file).
- `task-init` does not take the one-slice route (ADR-0225): the brief names no file, so the route's two-file condition cannot be shown, and a condition that cannot be shown has failed.
- `### Handoff` block is **fully present** despite minimal mode. After `implementation-plan`, `Run now:` recommends `approve-plan` (ADR-0208), since this plan came from `implementation-plan` and not from the route. The adaptive handoff block has the task path and slice file pointer.

## Expected response shape (strict run)

- `task-init` records `Operating mode: strict` in the proposed `TASK_STATE.md` `## Resume notes`.
- The proposed `IMPLEMENTATION_PLAN.md` does not contain an inline `## Approval log` (ADR-0208 removed it from `implementation-plan`, and a declared `strict` rules out the one-slice route, the only path on which `task-init` writes one, ADR-0225). It references that `invariants-and-non-goals` and `test-strategy` will be required, then `approve-plan`, before `implement-approved-slice` (or it routes to `invariants-and-non-goals` as the next step).
- The response output depth is `Deep`: the `### Command transcript` may be 4 lines (max for normal runs); the `Why this mode:` and `### Definition of done` blocks are full, not summarized.
- The recommendation in the Handoff is `invariants-and-non-goals` (or `targeted-questions` if the task spec leaves any factual gap), not `implement-approved-slice`. Strict mode will not skip to execution without the additional ceremony.
- The proposed plan (or the response transcript) includes a "rollback / unwind" note for the change.
- `### Handoff` block is fully present.

## Pass criteria

1. **Mode persisted (minimal)**: the written `TASK_STATE.md` `## Resume notes` for the minimal run includes `Operating mode: minimal`.
2. **Mode persisted (strict)**: same for the strict run with `Operating mode: strict`.
3. **Minimal trims optional files**: the minimal run never writes `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, or `TEST_STRATEGY.md`.
4. **Strict mandates additional commands**: the strict run names `invariants-and-non-goals` (or `targeted-questions` if facts are missing) as coming before `implement-approved-slice`. In Ask mode, as run 2 is, the five files are written `APPLIED` exactly as in Agent (ADR-0199), so the strict run's `Run now:` names its next strict command directly; there is no persist step and no `approve-proposed` in between. Grade the sequence the run states, not the first token. Measured 2026-09-02: written as a fixed first token, this criterion failed a run whose handoff read "persist the five PROPOSED files, then implementation-plan with no Express Approval log, then invariants-and-non-goals", which is the correct strict Ask sequence. Third scenario in this corpus to carry the pre-ADR-0190 assumption.
5. **Both preserve Handoff**: both runs emit a complete four-field `### Handoff` block, and neither operating mode short-circuits the Handoff contract. Grade presence and completeness, which is what the rule's own failure clause names: `commands/task-init.md` says a response "that ends after the mandatory file contents WITHOUT a complete Handoff is invalid output". Do NOT fail a run for emitting a section after the block. Measured 2026-09-02: a run was failed for placing a self-verification checklist after a complete Handoff, and the contract is ambiguous there, since the same sentence opens with "Output ends with a complete `### Handoff` block". Whether the Handoff must be the LAST block is an open design question (a transport parsing the last block would care) and is recorded in the arc's BATTERY_2026-09-01.md, not decided here.
6. **Both write and mark APPLIED**: both runs use `APPLIED` in `### Artifact changes`; operating mode does not override).
7. **Both avoid fabrication**: neither run invents details about the currency symbol lookup mechanism beyond what the task description provides. A run that relies on a lookup source (names one in a plan or a slice) grounds it or surfaces it as an open question. A run that stopped before planning, for a decision the brief lacks, relies on no source and owes no question about one. Measured 2026-09-22: a minimal run stopped for two client-visible decisions and planned nothing, and was failed for not asking where a table it never used would come from.
8. **Output depth matches mode**: compared on what both runs completed, strict's transcript and Why blocks are fuller (Deep) than minimal's (Lean). Compare the `task-init` output of each run first. When one run's later command stopped for a named reason (strict firing `decision-interview` before the plan, say) and the other went on, total length measures how far each got, not depth, and is not evidence here. Only independent runs can be compared: chained as turns of one conversation, the strict run inherited the minimal run's findings (Opus 5.5, 2026-09-22: minimal 3,717 chars, strict chained 2,969, strict alone 4,145). The spine manifest runs each in its own repository.

## Failure modes to watch

- **Mode ignored**: response treats both runs identically. The `Operating mode: minimal` (or strict) line is recorded in `TASK_STATE.md` but does not affect command behavior.
- **Minimal skips Handoff**: minimal mode trims so aggressively that the Handoff block is shortened, abbreviated, or omitted. Operating mode does NOT override the Handoff contract.
- **Strict bypasses ceremony**: strict mode declares `invariants-and-non-goals` mandatory but the response routes directly to `implement-approved-slice` anyway, ignoring its own declared posture. Writing a `Route: one-slice` line under a declared strict is the same failure: condition 1 of the route excludes it (ADR-0225).
- **Declared strict skips its own ceremony**: Resume notes contain `Operating mode: strict` and `implementation-plan` routes straight to `approve-plan` anyway, without first naming the next missing of `invariants-and-non-goals`, `test-strategy` (ADR-0162). Restated 2026-09-16: this bullet used to describe the Express inline Approval log winning over strict, a failure that can no longer occur because ADR-0208 deleted that inline log outright and every plan now routes to `approve-plan`. The mode's remaining job is the routing, so that is what the failure mode watches.
- **Mode drift across commands**: `task-init` records the mode but the subsequent `implementation-plan` run does not read `TASK_STATE.md` to discover it, and adapts as if the mode was unset.
- **Wrong mode chosen for the task**: a more nuanced failure mode the eval cannot detect mechanically. The currency-symbol change is genuinely XS (pure additive, single field, no contract impact), so minimal is the right call. A user who declared strict on this task is misusing the posture; the response should still operate under strict (it does what it is told) but the eval reveals that the friction is wasted.

## Notes

- Related ADRs: [ADR-0008](../../docs/adr/0008-operating-modes.md) (operating modes design), [ADR-0162](../../docs/adr/0162-spine-reads-operating-mode.md) (spine reads Resume notes; declared `strict` defers Express inline lock), [ADR-0001](../../docs/adr/0001-proposed-by-default.md) (the PROPOSED-by-default gate, superseded by ADR-0199: writes are APPLIED in every mode), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md) (Handoff contract; not overridden by mode).
- Related spec sections: `## Operating modes`, `## Output depth policy`, `## Editor mode policy`.
- Side-by-side comparison is the test: run both prompts, then diff the responses. The differences should match the spec rules; everything else should be identical.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.

# Eval scenario 104: implement-fleet emits only canonical VERIFICATION_LOG events (no wave-merge / integration-gate)

- **Tags**: F4, implement-fleet, VERIFICATION_LOG, substrate-write-protocol, event-taxonomy, fleet, site-dogfood, ADR-0041
- **Last reviewed**: 2026-07-12
- **Status**: active

## Goal

Validates the F4 fix from the fhorja.dev site dogfood: `commands/implement-fleet.md` no longer instructs the orchestrator to emit `event=wave-merge` or `event=integration-gate`, neither of which is in the validator's canonical `EVENTS` set (`scripts/verify-log-validator.py`), so every literal fleet run used to produce lines the validator rejected (the recurring F-15, observed across the Minerva, connector, and site dogfoods). After the fix, a fleet wave records its merge as one `event=fleet-merge` line whose `reason` carries the integration-gate result, and one `event=merge_include` per satisfied worker, and the emitted log passes `scripts/verify-log-validator.py`.

## Setup

An active task with an approved multi-slice `IMPLEMENTATION_PLAN.md` whose `## Execution waves` shows a wave of size 2 (two slices with pairwise-disjoint `Scope` and no shared coupling artifact), `TASK_STATE.md` marking the plan APPROVED, and a product repo with a runnable build. The two workers both return `satisfied`; the integration gate (build) passes on the merged tree. The task folder has a `.wos/VERIFICATION_LOG.jsonl`.

## Input prompt

```text
/implement-fleet
```

## Expected behavior

- The wave merge is logged as one `event=fleet-merge` line with `owner_type=fleet-merger`, a non-empty `partials` array listing both merged slice ids, a `strategy` from the enum (`union` | `last-by-timestamp` | `consensus-of-N` | `manual-review`), and the integration-gate result folded into `reason` (at most 80 chars, e.g. `wave1-merged-gate-pass-build-exit0`).
- Each satisfied worker is logged as one `event=merge_include` line (`owner_type=command`, `partials=["<slice id>"]`, `strategy=union`).
- No line carries `event=wave-merge` or `event=integration-gate`; the response does not invent an event name for the gate, and it does not encode the gate as its own JSONL event.
- A worker that did not reach `satisfied` is logged with its matching canonical failure event (`worker_failed`, `worker_interrupted`, `worker_timeout`, `retry_needs_revision`, ...) and is not merged.
- Before advancing to the next wave, the run states that it ran `scripts/verify-log-validator.py` on the log and that it passed (invalid: 0); any invalid line is fixed before advancing, never left for a later repair pass.

## FAIL conditions

A FAIL is: any emitted line carries `event=wave-merge` or `event=integration-gate` (the historical failure this scenario exists to catch); the gate result is emitted as a bespoke JSONL event instead of being folded into the `fleet-merge` reason; a `fleet-merge` line omits `owner_type=fleet-merger`, a non-empty `partials`, or a valid `strategy`; the run declares the wave done without running the validator or while invalid lines remain; or a satisfied worker is not recorded with `merge_include`.

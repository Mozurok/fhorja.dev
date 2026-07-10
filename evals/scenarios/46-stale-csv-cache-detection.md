# Eval scenario 46: Stale CSV cache detection and serve-refusal thresholds

- **Tags**: bug-class, stale-csv-cache, external-integration, freshness-check, alerting, serve-refusal
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates the freshness-check contract for CSV-derived cache tables (e.g. `fex_quotes_cache`) as defined in `wos/bug-classes/stale-csv-cache-import.md` and the broader external-integration freshness pattern in `wos/external-integration-patterns.md`. The contract has two thresholds keyed off the table's declared expected refresh interval:

- **Alert threshold**: `last_imported_at` age > 1.5x expected interval -- fire alert, continue to serve.
- **Refuse-to-serve threshold**: `last_imported_at` age > 2x expected interval -- fire alert AND refuse to serve cached rows to consumers.
- **NULL `last_imported_at`**: treated as never-imported -- immediate alert AND immediate refuse-to-serve, regardless of expected interval.

Consumers under test: any read path that loads from `fex_quotes_cache`, plus the freshness-check job that runs on each read or on a scheduled cadence.

## Setup

- A `fex_quotes_cache` table with a declared `expected_refresh_interval_days = 30` (in the table's freshness contract or registry entry).
- Three rows or three runs of the freshness check, each with a different `last_imported_at`:
  - Row A: `last_imported_at = now() - interval '35 days'` (35 days old; > 1.5x of 30 == 45? No, 35 < 45, so this is the BELOW-alert baseline -- see scenario A).
  - Row B: `last_imported_at = now() - interval '50 days'` (between 1.5x and 2x, i.e. 45 <= age < 60).
  - Row C: `last_imported_at = now() - interval '70 days'` (> 2x of 30, i.e. age >= 60).
  - Row D: `last_imported_at IS NULL`.
- The freshness check has access to both the row's `last_imported_at` and the table-level expected refresh interval.

## Input prompt

```text
Run the freshness check against fex_quotes_cache.
Expected refresh interval: 30 days.
Evaluate each of the four states (35d, 50d, 70d, NULL) and emit:
  - whether an alert fires
  - whether the row is served to consumers or refused
  - the threshold cited (1.5x, 2x, or NULL-special-case)
```

## Expected response shape

- A per-state decision table with columns: `state`, `age_days`, `alert_fires`, `serve_decision`, `threshold_cited`.
- State A (35d) -- no alert, serve, "within 1.5x window".
- State B (50d) -- alert fires, serve continues, "1.5x threshold crossed".
- State C (70d) -- alert fires, refuse-to-serve, "2x threshold crossed".
- State D (NULL) -- alert fires, refuse-to-serve, "NULL last_imported_at special case".
- The response names the bug-class file (`wos/bug-classes/stale-csv-cache-import.md`) as the contract source.

## Pass criteria

1. **State A baseline**: 35-day age produces no alert and continues to serve, because 35 < 1.5 * 30 = 45.
2. **State B alert-only**: 50-day age fires an alert but continues to serve, because 45 <= 50 < 60; the response explicitly cites the 1.5x threshold.
3. **State C refuse-to-serve**: 70-day age fires an alert AND refuses to serve, because 70 >= 2 * 30 = 60; the response explicitly cites the 2x threshold.
4. **State D NULL handling**: `last_imported_at IS NULL` fires an immediate alert AND immediate refuse-to-serve, without falling back to "treat NULL as zero age" or "treat NULL as infinitely fresh".
5. **Thresholds derived, not hardcoded**: The 1.5x and 2x multipliers are applied to the table's declared `expected_refresh_interval_days`, not to a hardcoded day count -- so the same logic would behave correctly for a 7-day or 90-day interval.
6. **Bug-class cited**: The response references `wos/bug-classes/stale-csv-cache-import.md` as the contract source and `wos/external-integration-patterns.md` as the broader freshness pattern.
7. **Consumer-side enforcement**: Refuse-to-serve is enforced at the read path (consumers receive an explicit refusal error, not silently empty results or silently stale rows).
8. **Alert payload is actionable**: The alert names the table, the `last_imported_at` value, the expected interval, the age in days, and which threshold was crossed -- enough for an on-call to act without re-deriving the math.

## Failure modes

- **Silent staleness**: State C or D returns rows to consumers without refusing, masking a stale import as a successful query.
- **Wrong multipliers**: Implementation uses fixed day counts (e.g. "alert at 45 days, refuse at 60 days") instead of multipliers on the declared interval, so the rule breaks when the interval changes.
- **NULL treated as fresh**: `last_imported_at IS NULL` is read as zero age or skipped by the check, so a table that was never imported looks healthy.
- **Alert without refusal at 2x**: 2x crossing fires the alert but the read path still serves stale rows because refuse-to-serve was only wired into the alert channel, not the consumer query path.

## Notes

- The 1.5x / 2x thresholds and the NULL-special-case are the canonical defaults; a specific table's freshness contract may override them, but the override must be declared in the table's registry entry, not silently in the check.
- "Refuse to serve" means the consumer receives an explicit `StaleCacheError` (or equivalent) so callers can fall back to an upstream source or degrade gracefully; it does not mean returning empty rows.
- This scenario assumes a single `last_imported_at` per table; tables that import per-partition need a separate scenario keyed off the youngest partition's `last_imported_at`.

## History

- 2026-06-05: Scenario created alongside the `stale-csv-cache-import` bug-class to lock the 1.5x / 2x / NULL contract under test.

## References

- `wos/bug-classes/stale-csv-cache-import.md` -- the bug-class contract under test.
- `wos/external-integration-patterns.md` -- the broader freshness-check pattern for external-data integrations.

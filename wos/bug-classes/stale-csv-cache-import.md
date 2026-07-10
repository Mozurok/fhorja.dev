---
name: stale-csv-cache-import
category: data-integrity
default-severity: P1
priority: P1
pillars: [data-integrity, observability]
cwe: [CWE-1023]
languages: [typescript, sql, python]
file-patterns: ["**/import/**", "**/cache/**", "**/jobs/**", "**/cron/**", "**/csv/**", "**/migrations/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# stale-csv-cache-import

A periodic CSV (or flat-file) import populates an internal cache table that downstream consumers treat as the source of truth. The import job succeeds on its last run, but the data it loaded is now days or weeks past its intended freshness window. Consumers keep reading from the cache with no signal that the values are stale, so the system silently serves outdated rates, products, or reference data.

## What it looks like

- A cache table (e.g., `rate_cache`, `product_catalog_cache`) is refreshed by a scheduled job (monthly, weekly) that pulls a CSV from a partner SFTP or an internal export bucket.
- The most recent import completed without error, but the source CSV itself was already days old, or the job hasn't run for several cycles because the schedule was paused/misconfigured.
- The table has no `last_imported_at` / `source_generated_at` column, or it has one but nothing reads it.
- Downstream quoting/lookup code joins against the cache with no freshness predicate and no warning surface.
- Admin UI shows the cache rows but has no badge or banner indicating how old they are.

## Why it matters

- In insurance/quoting flows, stale rates produce wrong premium quotes. The customer is charged the quoted price, then disputes when the correct rate is applied, leading to refunds, chargebacks, and trust loss.
- The failure is rare-but-catastrophic: most days the cache is fresh enough; the one bad month wipes out the margin from the good months.
- Because the import job reports SUCCESS, standard job-failure alerts do not fire. This is an observability gap as much as a data gap -- the system looks healthy while serving wrong answers.
- Recovery requires re-quoting and possibly re-issuing policies, which is far more expensive than the original import-monitoring work.

## How to detect

- Schema audit: cache tables that lack a `last_imported_at` (or `source_generated_at`) timestamp column.
- Schema audit: cache tables that HAVE the column but no query in the codebase filters or alerts on it.
- Monitoring audit: no alert rule of the shape "freshness > N days" or "no successful import in the last K cycles" for each cache feed.
- UI audit: admin/operator screens that surface cache-backed values without a visible cache-age badge or "data as of YYYY-MM-DD" label.
- Grep heuristic: search import job code for the pattern `INSERT INTO ..._cache` without an accompanying `UPDATE ... SET last_imported_at` or equivalent metadata write.

## How to fix

1. Add `last_imported_at TIMESTAMPTZ NOT NULL` (and ideally `source_generated_at` for the upstream CSV's own timestamp) to every cache table. Backfill with the best-known value, then mark unknowns.
2. Have every import job write both timestamps in the same transaction as the row upsert. No row lands without freshness metadata.
3. Add a freshness alert: page on-call when `now() - max(last_imported_at) > 1.5x` the expected refresh interval per feed.
4. Refuse to serve from the cache when `now() - last_imported_at > 2x` the interval -- fail closed (return error or fall back to upstream) rather than silently serving stale data.
5. Render a cache-age badge in the admin UI for every cache-backed surface. Color it green/yellow/red against the 1x / 1.5x / 2x thresholds.
6. Add a smoke test that intentionally ages the cache (in a non-prod env) and confirms the alert + refuse-to-serve path both trip.

## CWE / standard refs

- CWE-1023: Incomplete Comparison with Missing Factors. The cache read compares on key fields (product id, region, etc.) but omits the freshness factor entirely, so equally-keyed-but-stale rows are treated as valid.

## See also

- `wos/bug-classes/rate-limit-no-backoff.md`
- `wos/bug-classes/missing-retry-on-external-call.md`
- `wos/bug-classes/documentation-drift.md`

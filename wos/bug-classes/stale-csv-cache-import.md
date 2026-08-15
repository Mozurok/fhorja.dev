---
name: stale-csv-cache-import
category: data-integrity
default-severity: P1
cwe: [CWE-1023]
languages: [typescript, sql, python]
file-patterns: ["**/import/**", "**/cache/**", "**/jobs/**", "**/cron/**", "**/csv/**", "**/migrations/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# stale-csv-cache-import

## Trigger

A periodic flat-file import populates a cache table that downstream consumers treat as the source of truth. The import job succeeds on its last run, and the data it loaded is already past its intended freshness window: the source file was old when it arrived, or the schedule has been paused for several cycles. Consumers keep reading the cache with no signal, so the system serves outdated rates, prices, or reference data with full confidence.

The reason this survives is that the job reports success. Standard job-failure alerting never fires, because nothing failed. The system looks healthy while serving wrong answers, which makes this an observability failure as much as a data one.

The shape of the loss is rare and expensive rather than frequent and small. Most days the cache is fresh enough and nothing is wrong. The one bad cycle produces wrong quotes or wrong prices that customers act on, and recovery means re-quoting, refunds, or reissuing commitments, which costs far more than the freshness monitoring would have.

CWE-1023 (Incomplete Comparison with Missing Factors): the cache read compares on the key fields and omits the freshness factor entirely, so an equally-keyed but stale row is treated as valid.

## Detection

- A cache table refreshed by a scheduled job that pulls a file from a partner transfer location or an export bucket, on a weekly or monthly cadence.
- No `last_imported_at` or `source_generated_at` column on the cache table, so freshness is not representable.
- The column exists and nothing reads it: no query filters on it, no alert thresholds against it, no surface displays it.
- Downstream lookup code that joins the cache with no freshness predicate and no warning path.
- An admin surface that shows cache-backed values with no indication of their age.
- A schedule that has not run for several cycles because it was paused or misconfigured, where the last run is recorded as successful.

```
# import jobs that write rows without writing freshness metadata
rg -n "INSERT INTO .*_cache|upsert\(.*cache" <src-root> -A 10 \
  | rg -B 1 -A 10 "last_imported_at|source_generated_at" --files-without-match
```

## Retrieval

- The cache table's schema, including whether any freshness column exists at all. This is the first branch: a system that cannot represent freshness fails differently from one that represents and ignores it.
- The import job end to end, from where it fetches the file to where it commits rows, so the question of whether metadata is written in the same transaction as the data can be answered rather than assumed.
- Every consumer of the cache table, not the primary one. The class is defined by what consumers do not check, and one careful consumer says nothing about the other five.
- The scheduler configuration and the actual run history. A job that is correct and has not run in three cycles produces the same outcome as a broken one, and only the history distinguishes them.
- The alert rules that reference this feed, or the fact that none do. Absence is the finding; record it as an answer.
- The operator-facing surfaces that display cache-backed values, down to the component, to establish whether age is visible to the human making a decision.

## Analysis prompt

Given the retrieved schema, the import job, the consumers, and the schedule:

1. Report whether the cache table can represent freshness at all: name the columns, or state that none exist. Distinguish the load time from the source's own generation time; a file that was already old when it loaded has a recent load time and stale content, and only the second column catches that.
2. Trace the import's write path and report whether freshness metadata is written in the same transaction as the rows. A separate write can succeed for the data and fail for the metadata, which produces rows that look fresher than they are.
3. Enumerate every consumer and report, per consumer, whether its read applies a freshness predicate. List the ones that do not. This list is the finding.
4. Report the actual last successful run and compare it against the intended cadence. State the number of cycles elapsed. Do not infer the cadence from the code alone if the scheduler holds a different one; report both when they disagree.
5. Report whether any alert would fire on a feed that stops refreshing, and what its threshold is relative to the cadence. An alert that fires only on job failure does not cover this class, and saying so is more useful than reporting that alerting exists.
6. Report whether the system fails closed anywhere: a threshold past which the cache is refused rather than served. If nothing refuses, say so, and name what the system would serve at ten times the intended age.
7. For each operator-facing surface displaying cache-backed values, report whether age is visible. A human who can see the date can catch what the code does not.
8. Recommend, in order: add both a load timestamp and a source-generation timestamp to every cache table, backfilling with the best known value and marking the unknowns as unknown rather than as now; write both in the same transaction as the rows, so no row lands without freshness metadata; alert when the newest row's age exceeds a stated multiple of the refresh interval, per feed; refuse to serve past a higher multiple, failing closed to an error or an upstream lookup rather than silently serving stale data; show the age on every operator surface backed by the cache; and add a test that ages the cache deliberately in a non-production environment and asserts that both the alert and the refusal fire.

## Severity rubric

- **P1**: a cache table with no freshness column, consumed by a path whose output is a commitment to a customer such as a price or a quote. Justification: wrong output that the business honors, with no signal at any layer, and a recovery cost that exceeds the incident. It is not P0 because the underlying source data is intact and correct, the wrong values are recoverable once the feed refreshes, and the failure is bounded by the cycle.
- **P1 also**: a freshness column that exists and is read by nothing. The information is present and the system is exactly as blind as one that lacks it, which is the shape most likely to pass review.
- **P2**: freshness tracked and alerted with no fail-closed threshold. Someone is told; nothing stops.
- **P2**: freshness correct throughout and invisible on the operator surfaces, so the human in the loop cannot catch what the code missed.

## Confidence factors

- **HIGH**: a cache table with no freshness column and a consumer that joins it with no date predicate. Two reads, no interpretation.
- **MEDIUM**: a freshness column present with no query filtering on it in the retrieved consumers, where a consumer outside the retrieved set may still check.
- **LOW**: a schedule whose last run is old, in a system where the job may also be triggered manually or by an event outside the scheduler, so elapsed cycles do not establish elapsed data age.

## Examples

### Positive (fresh-looking key match, no freshness factor)

```sql
-- the lookup every quote goes through
SELECT premium
FROM   rate_cache
WHERE  product_id = $1 AND region = $2;   -- keys match, age is not a factor
```

The table has no load timestamp. The import last ran successfully six weeks ago against a file that was already two weeks old, the schedule was paused during a migration and never resumed, and every quote since has been priced off it. The job dashboard is green, because the job is not the thing that failed.

### Negative (age represented, enforced, and shown)

```sql
SELECT premium
FROM   rate_cache
WHERE  product_id = $1 AND region = $2
  AND  source_generated_at > now() - interval '60 days';   -- fails closed to zero rows
```

```ts
if (!row) throw new RateUnavailable(productId, region);      // refuses, never defaults
```

The import writes `last_imported_at` and `source_generated_at` in the same transaction as the rows, an alert fires when the newest row passes 1.5 times the refresh interval, the query itself refuses past a higher threshold, and the admin surface prints the source date next to every rate so an operator sees the age before a customer does.

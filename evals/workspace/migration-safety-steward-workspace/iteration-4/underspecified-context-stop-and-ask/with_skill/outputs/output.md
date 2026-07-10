# Migration Safety Audit -- STOP / Insufficient Context

**Audit run_id:** mss-2026-06-05-orders-status-idx-01
**Migration file:** `migrations/20260608120002_add_orders_status_index.sql`
**Table:** `orders`
**Postgres version:** UNSPECIFIED (assumed worst-case for verdict purposes)
**Row count:** UNSPECIFIED (per Step 4: treat as `>1M`)
**Deployment strategy:** UNSPECIFIED
**Online-DDL tooling:** UNSPECIFIED

Persona protocol Step 1 + Step 4 + Step 6 bias rule are all triggered: with row count unknown AND deployment strategy unspecified AND PG version unspecified, the audit cannot return a `SAFE` verdict. Per Quality bar: "the cost of a false SAFE verdict on a production migration is irreversible." Stopping and handing off.

## Per-statement verdict table

| stmt_id | file:line | classification | lock_level (worst-case) | est_row_count_bucket | verdict | rollback | remediation_link |
|---|---|---|---|---|---|---|---|
| S1 | `20260608120002_add_orders_status_index.sql:1` | `CREATE-INDEX` | `ShareLock` (non-CONCURRENTLY) blocks writes; `ShareUpdateExclusiveLock` if `CONCURRENTLY` | `>1M` (assumed, Step 4 default) | **NEEDS-PHASING** | `DROP INDEX CONCURRENTLY idx_orders_status;` (reversible, safe) | §Remediation S1 |

### Why NEEDS-PHASING (not SAFE)

The DDL as written is `CREATE INDEX` without `CONCURRENTLY`. Per Step 3 canonical rule: **"`CREATE-INDEX` on Postgres MUST use `CONCURRENTLY`"**. The current statement acquires `ShareLock` on `orders`, blocking ALL concurrent INSERT/UPDATE/DELETE on the `orders` table for the full duration of the index build.

**Specific failure mode (Quality bar (b)):** On an unknown-row-count `orders` table (treated as `>1M` per Step 4), a non-concurrent btree build on a `status` column (low-cardinality, frequently written during checkout) holds `ShareLock` for an estimated 30s–several minutes. **Likely production symptom:** all order writes (checkout, status transitions, webhook ingest) queue or 500 for the duration; PagerDuty page within ~2 minutes; revenue-impacting.

Even the `CONCURRENTLY` variant cannot be declared SAFE without PG version (lock semantics, `REINDEX CONCURRENTLY` availability, partitioned-table handling differ across PG11/12/13+) and deployment strategy (a failed `CONCURRENTLY` build leaves an `INVALID` index requiring `DROP + retry` -- needs operator runbook).

## Risks grouped by severity

### P0 (UNSAFE + IRREVERSIBLE)
*(none -- the operation is reversible via `DROP INDEX CONCURRENTLY`)*

### P1 (NEEDS-PHASING, concrete failure mode named)
- **R1 -- Write-blocking index build on `orders`.** `CREATE INDEX` without `CONCURRENTLY` holds `ShareLock` on the assumed-`>1M`-row `orders` table. Failure mode: all writes to `orders` blocked for the full index build window. Production symptom: checkout 500s, queue backpressure, on-call page.
- **R2 -- Unknown PG version blocks safe-variant selection.** PG10 vs PG11+ vs PG12+ change index-build semantics (partitioned tables, `CONCURRENTLY` on partitioned parents, `REINDEX CONCURRENTLY`). A remediation chosen without version knowledge may itself be unsafe.
- **R3 -- Unknown deployment strategy blocks phasing recommendation.** Single-shot cutover vs rolling deploy vs blue/green changes whether the index can be built ahead of code that reads it, and whether an `INVALID` index after a failed `CONCURRENTLY` build can be tolerated.

### P2 (SAFE but worth noting)
*(none -- cannot certify any P2 without inputs)*

## Missing context items blocking definitive audit

Per persona Required inputs, the following are MISSING and block a final verdict:

1. **Estimated row count for `orders`** -- order-of-magnitude bucket: `<10k`, `10k–1M`, `1M–100M`, `>100M`. Drives lock-duration risk and whether `CONCURRENTLY` is even sufficient.
2. **Postgres version (major)** -- `10.x` / `11.x` / `12.x` / `13+` / `14+` / `15+` / `16+`. Drives `CONCURRENTLY` semantics, partitioned-index support, and `REINDEX CONCURRENTLY` availability.
3. **Deployment strategy** -- single-shot cutover vs rolling deploy vs blue/green. Drives whether the index can be built in a maintenance window vs must be online.
4. **Online-DDL tooling in scope (optional but verdict-changing)** -- pg-osc / pg_repack / Reshape / none. If `pg_repack` or Reshape is available, remediation shape changes.
5. **Read/write path on `status`** -- is `orders.status` a hot write column (every checkout state machine transition) or cold (rare update)? Affects index-build duration estimate and bloat profile.
6. **Is `orders` partitioned?** -- Partitioned-parent `CREATE INDEX` has different lock semantics across PG versions; `CONCURRENTLY` on a partitioned parent is PG11+ only and has caveats.
7. **Existing indexes on `orders(status)` or `orders(status, …)`** -- duplicate-index risk; may make this migration a no-op or redundant.

## Recommended remediation (provisional -- pending inputs)

Cannot emit a final statement-shaped remediation without inputs 1–4. **Provisional** safe variant (will be re-validated once inputs land):

```sql
-- PROVISIONAL -- requires PG version + row count + deployment strategy confirmation
-- Must run outside any transaction block (CONCURRENTLY constraint)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status
  ON orders(status);

-- Operator runbook addendum (required before apply):
-- 1. Verify no existing covering index on orders(status, ...) -- \d orders
-- 2. If build fails or is cancelled, the index will be INVALID:
--    SELECT indexrelid::regclass FROM pg_index WHERE indisvalid = false;
--    DROP INDEX CONCURRENTLY idx_orders_status;  -- then retry
-- 3. Monitor pg_stat_progress_create_index during build.
```

This is NOT promoted as the final remediation because the audit lacks the inputs to certify it safe (partitioned-table case, PG10 fallback, etc.).

## Recommended next command

**`targeted-questions`** -- the gaps are **factual**, not decision-driven:

- Row count: factual (query `pg_class.reltuples` or `count(*)`)
- PG version: factual (`SELECT version();`)
- Deployment strategy: factual (existing org practice / runbook lookup)
- Partitioning: factual (`\d+ orders`)
- Existing indexes: factual (`\d orders`)
- Online-DDL tooling availability: factual (infra inventory)

Per `targeted-questions` description: use when "missing information is factual." Per `decision-interview` exclusion: do NOT use when "missing information is factual (use targeted-questions)." Per `implementation-plan` exclusion: do NOT use when "key facts or decisions remain open."

**Routing rationale (why not the other two candidates):**
- ❌ `implementation-plan` -- premature; plan would be built on assumptions, violating its Do-not-use rule ("key facts or decisions remain open").
- ❌ `decision-interview` -- the missing items are not policy/tradeoff decisions; they are facts the user (or their DB) can look up. Would be the right next step only AFTER `targeted-questions` returns and a tradeoff surfaces (e.g. "we are on PG10, so `CONCURRENTLY` semantics differ -- should we upgrade first or use pg_repack?").
- ✅ `targeted-questions` -- correct shape for factual gathering. After it returns with PG version + row count + deployment strategy, re-run `migration-safety-steward` for the final verdict; if that re-run surfaces an `IRREVERSIBLE` flag or non-trivial phasing tradeoff, route THEN to `decision-interview`, then to `implementation-plan` for re-slicing.

### Suggested questions to feed into `targeted-questions`

1. What is the current major Postgres version of the target database? (`SELECT version();`)
2. What is the approximate row count of `orders`? (order-of-magnitude bucket is sufficient: `<10k` / `10k–1M` / `1M–100M` / `>100M`)
3. Is `orders` a partitioned table? If so, partition strategy (range/list/hash) and partition count.
4. Are there existing indexes covering `orders(status)` or `orders(status, …)`? (`\d orders`)
5. What deployment strategy is used: single-shot cutover, rolling deploy, or blue/green?
6. Is any online-DDL tooling available in this environment (pg-osc, pg_repack, Reshape)?
7. Is `orders.status` a hot write column (transition on every order state change) or cold (rare update)?

## Artifact changes

`MIGRATION_SAFETY.md`, `DECISIONS.md`, `TASK_STATE.md`, `IMPLEMENTATION_PLAN.md` -- **SKIP** (no PROPOSED blocks emitted; final verdict deferred until factual inputs land, per Step 4 + Step 6 bias rule and Quality bar (d)).

## Command transcript

1. Loaded persona SKILL.md.
2. Applied Step 1 (parse: 1 statement, S1 = `CREATE-INDEX`).
3. Applied Step 4 (unknown row count → bucketed as `>1M`).
4. Applied Step 6 bias rule (unknown row count + unspecified strategy + unspecified PG version → NEEDS-PHASING; refused to draft full remediation without inputs).

## Handoff

**Status:** STOP -- insufficient context for definitive audit.
**Run now:** `targeted-questions` with the 7-question list above.
**Then:** re-run `migration-safety-steward` with inputs → if IRREVERSIBLE or non-trivial tradeoff surfaces, route to `decision-interview`; otherwise route to `implementation-plan` to re-slice into safe phases (Phase 1: `CREATE INDEX CONCURRENTLY` + operator runbook; Phase 2: verify validity + ANALYZE).

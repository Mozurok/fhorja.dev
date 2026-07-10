# Migration Safety Audit -- `20260608120003_alter_orders_amount_type.sql`

**Audit run_id:** mss-2026-06-05-online-ddl-not-in-scope
**Migration file:** `migrations/20260608120003_alter_orders_amount_type.sql`
**Postgres version:** 14
**Deployment strategy:** Rolling deploy, NO maintenance window (24/7 global production)
**Row count assumption:** `orders` ~500M rows (bucket: `>100M`)
**Online-DDL tooling (pg_repack / Reshape / pg-osc):** declared OUT OF SCOPE per slice

---

## Verdict (Step 6): UNSAFE -- no safe variant exists within current slice scope

This is the per-persona Step 8 + Step 9 stop condition: the only canonical safe variant for an `ALTER COLUMN ... TYPE numeric(20,4)` against a `>100M` row table on PG14 under a no-maintenance-window regime is either (a) the batched shadow-column rewrite (`ADD COLUMN amount_cents_new`, dual-write, backfill in batches, swap, drop) OR (b) an online-DDL tool (`pg_repack` / `Reshape`). Option (a) requires a multi-phase slice the current slice scope does not authorize. Option (b) requires tooling the slice explicitly excludes. Therefore there is no in-scope safe variant -- the audit MUST halt and route to `decision-interview` rather than rubber-stamp NEEDS-PHASING with no executable remediation.

---

## Per-statement verdict table

| stmt_id | file:line | classification | lock_level | est_row_count | verdict | rollback | remediation |
|---|---|---|---|---|---|---|---|
| S1 | `migrations/20260608120003_alter_orders_amount_type.sql:1` | `ALTER-TYPE` (numeric precision/scale change forcing full table rewrite) | `AccessExclusiveLock` on `orders` for full rewrite duration | `>100M` (~500M) | **UNSAFE** | `IRREVERSIBLE` in-place (the rewrite is one-shot; reverse `ALTER TYPE` back to original repeats the same lock and may truncate values if any new writes used the wider precision) | NO IN-SCOPE REMEDIATION -- see "Gap" below |

### Specific failure mode (Step 7 P0)

- **Failure mode:** PG14 `ALTER COLUMN ... TYPE numeric(20,4)` with a precision/scale change is NOT metadata-only -- it rewrites every tuple, holding `AccessExclusiveLock` on `orders` for the entire rewrite. At ~500M rows this is hours of full table lock (commonly 2–8h depending on tuple width, fillfactor, IO, indexes, and FKs touching `orders`).
- **Production symptom:** All reads AND writes to `orders` block from statement start. In a 24/7 global checkout system this means: every checkout write blocked, every order read blocked, connection pool exhaustion within seconds, cascading failure to any service that joins `orders`, PagerDuty page within ~60–120 seconds, sustained user-visible 500s until either the migration completes (hours) or is cancelled (which still rolls back hours of rewrite under the same lock).
- **Severity:** **P0** -- UNSAFE + de-facto IRREVERSIBLE under the no-maintenance-window constraint.

---

## Gap (Step 8): why no in-scope remediation exists

The persona's Step 8 contract requires every NEEDS-PHASING / UNSAFE row to receive a **statement-shaped** remediation (concrete SQL or online-DDL invocation), not prose. Here the two canonical safe variants are:

### Variant A -- Batched shadow-column rewrite (in-DB, no extra tooling)

```sql
-- Phase 1 (deploy 1): add nullable shadow column + dual-write trigger
ALTER TABLE orders ADD COLUMN amount_cents_new numeric(20,4);
CREATE OR REPLACE FUNCTION orders_amount_dual_write() RETURNS trigger AS $$
BEGIN
  NEW.amount_cents_new := NEW.amount_cents::numeric(20,4);
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER orders_amount_dual_write_trg
  BEFORE INSERT OR UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION orders_amount_dual_write();

-- Phase 2 (background): batched backfill in chunks of e.g. 10k rows
-- repeat until no rows remain unbackfilled:
UPDATE orders SET amount_cents_new = amount_cents::numeric(20,4)
WHERE amount_cents_new IS NULL
  AND id IN (SELECT id FROM orders WHERE amount_cents_new IS NULL LIMIT 10000);

-- Phase 3 (deploy 2): switch readers to amount_cents_new
-- Phase 4 (deploy 3): drop trigger, drop old column, rename new -> old
ALTER TABLE orders DROP COLUMN amount_cents;
ALTER TABLE orders RENAME COLUMN amount_cents_new TO amount_cents;
```

**Why this is OUT OF SLICE SCOPE:** Variant A is a 3–4 deploy reshape, not a single migration. It changes the slice from "alter type" to "introduce shadow column + dual-write + backfill + cutover + cleanup", which is a different unit of work and requires re-planning via `implementation-plan`. The current slice does not authorize that reshape.

### Variant B -- Online-DDL tooling

```bash
# pg_repack (requires extension installed + superuser)
pg_repack --table=orders --no-superuser-check --jobs=4

# OR Reshape (requires the Reshape binary + migration spec)
reshape migrate --new-version vN --complete
```

**Why this is OUT OF SLICE SCOPE:** explicitly excluded per task input ("Online-DDL tooling: NOT IN SCOPE per slice"). Neither extension/binary install nor the operational runbook for it is authorized.

### Conclusion of Step 8

Per the persona's quality bar -- "every remediation is statement-shaped; never prose advice" -- the audit CANNOT emit a valid in-scope remediation. The only honest output is to STOP and escalate. This is exactly the Step 9 escalation path.

---

## Risks grouped by severity

- **P0 -- UNSAFE + IRREVERSIBLE:**
  - S1: `ALTER TYPE` on `orders` (500M rows, PG14, no maintenance window) → hours of `AccessExclusiveLock`, full production write outage, no safe reverse in-place.
- **P1 -- NEEDS-PHASING with concrete failure mode:** none (the single statement is already P0).
- **P2 -- SAFE worth noting:** none.

---

## Recommended next command (Step 9 routing)

**`decision-interview`** -- STOP here. This is the persona's explicit Step 8 + Step 9 stop condition: the safe variant requires tooling or a slice reshape the current scope forbids, so the audit cannot move to `implementation-plan` (no authorized phasing exists yet) and cannot move to `approve-proposed` (no SAFE verdict). The user must make a load-bearing decision before this migration can be re-audited.

### Decision questions to surface in `decision-interview`

The user MUST choose exactly one of these three branches before any further migration work proceeds:

1. **Authorize online-DDL tooling into scope.** Approve `pg_repack` (extension install + superuser access + repack runbook) or `Reshape` (binary + migration spec format) as in-scope for this slice. This unlocks Variant B and lets the audit re-run with a SAFE verdict against the tool-shaped remediation. Trade-off: operational footprint of the tool (install, monitoring, rollback playbook) is added to the slice.
2. **Reshape the slice into a multi-deploy phased rewrite (Variant A).** Re-slice via `implementation-plan` into 3–4 deploys: shadow column + dual-write trigger; batched backfill; reader cutover; old-column drop. Trade-off: significantly larger slice, weeks of calendar time, increased complexity, but uses only in-DB primitives.
3. **Explicitly accept the risk of in-place `ALTER TYPE`.** Sign off on hours of `AccessExclusiveLock` on `orders` with full checkout outage. This requires a documented incident plan, customer communication, and almost certainly contradicts the "no maintenance window ever" constraint -- so accepting this is effectively rewriting that constraint. Trade-off: simplest migration shape, catastrophic operational cost.

Branches (1) and (2) are the only branches consistent with the stated 24/7 constraint. Branch (3) is included for completeness but should be flagged as contradicting a prior locked constraint and likely requires `direction-adjust` rather than mere acceptance.

---

## Artifact changes

- **PROPOSED** `<task>/MIGRATION_SAFETY.md` -- full audit body above (header + per-statement verdict table + P0 risk + gap analysis + Variant A/B remediation sketches + Step 9 routing).
- **PROPOSED** `DECISIONS.md ## Locked decisions` -- D-N draft: "Slice 20260608120003 cannot proceed under current scope; awaits user decision on tooling authorization vs slice reshape vs risk acceptance per `decision-interview`."
- **PROPOSED** `TASK_STATE.md ## Risks to watch` -- P0 entry: "ALTER TYPE on orders (500M rows, PG14, no maintenance window) → hours of AccessExclusiveLock; no in-scope safe variant; blocked pending `decision-interview`."
- **PROPOSED** `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- mirror of the P0 risk with mitigation = "Resolve via `decision-interview` before any re-planning attempt; do NOT advance this slice."
- **SKIP** any APPLIED write -- persona is L1, substrate writes go through `approve-proposed`.

## Command transcript

1. Parsed migration (1 statement) → classified `ALTER-TYPE` precision/scale change.
2. Step 4 lock estimate: `AccessExclusiveLock` on `>100M` table → auto-NEEDS-PHASING; Step 5 rollback evaluation → IRREVERSIBLE under 24/7 constraint → escalated to UNSAFE.
3. Step 8 remediation attempt: only canonical safe variants (shadow-column rewrite, online-DDL) are explicitly out of scope → no statement-shaped remediation can be emitted.
4. Step 9 triggered: STOP, route to `decision-interview`.

### Handoff

**Verdict:** UNSAFE, P0, no in-scope remediation. Migration MUST NOT be applied.
**Run now:** `decision-interview` -- to authorize online-DDL tooling, reshape the slice into a multi-deploy phased rewrite, or (with `direction-adjust`) revisit the no-maintenance-window constraint.
**Do not run:** `implementation-plan` (no authorized phasing strategy exists yet); `approve-proposed` (no SAFE verdict to approve); any apply step against the current SQL.
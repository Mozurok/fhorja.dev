# Migration Audit: `ALTER TABLE orders ALTER COLUMN amount_cents TYPE numeric(20,4)`

## (1) Verdict: UNSAFE -- no safe variant exists within current slice scope

The proposed migration cannot be executed safely against a 24/7 global production Postgres 14 instance with ~500M rows in `orders` and online-DDL tooling explicitly out of scope. There is no in-scope variant that avoids unacceptable risk; the slice as currently shaped must STOP before execution.

### Why this is unsafe

- `ALTER COLUMN ... TYPE numeric(20,4)` with a precision/scale change is **not** a metadata-only operation. Postgres must rewrite every row because the on-disk representation of `numeric` depends on precision/scale and the `USING` cast forces re-encoding.
- The rewrite runs under **`AccessExclusiveLock`** on `orders` for the entire duration. This blocks:
  - all reads (`SELECT`)
  - all writes (`INSERT`/`UPDATE`/`DELETE`)
  - all DDL
  - autovacuum on the table
  - any FK validation touching `orders`
- At 500M rows, realistic rewrite time on commodity production hardware is measured in **hours**, not minutes. Add WAL generation pressure, replication lag spikes on standbys, potential checkpoint storms, and bloat on dependent indexes (all indexes on the table are also rebuilt).
- The deployment constraint is explicit: **rolling deploy, no maintenance window ever**. An hours-long AccessExclusiveLock on the orders table is functionally a full outage of the order pipeline. That violates the operational contract.
- Lock escalation will also cascade: any transaction holding even a weak lock on `orders` (a long-running report, a stuck connection) will block the `ALTER` from acquiring the lock and create a lock-wait pileup behind it. The `ALTER` itself then blocks every new query. This is a well-known incident pattern.
- Statement timeouts won’t save us -- if the `ALTER` is killed mid-rewrite, Postgres rolls it back (more time, more WAL), and the table is unchanged but bloated/contended.
- `numeric(20,4)` is a precision *and* scale change vs. whatever the prior type was (presumably `bigint` or `integer` given the `_cents` suffix). Even a `bigint → numeric` change is a hard rewrite -- there is no implicit binary-compatible path in Postgres 14 between integer types and `numeric`.

### Why there is no purely in-core safe variant

Postgres 14 has no native online type change for this case. The known “safe” techniques all rely on tooling or shape changes that are currently out of scope:

| Technique | In scope? | Notes |
|---|---|---|
| `pg_repack` (rewrite table online via triggers + swap) | NO | Explicit out of scope |
| `pg_squeeze` | NO | Out of scope |
| Reshape / pgroll (declarative online schema change) | NO | Out of scope |
| Add new column + dual-write + backfill + swap (expand/contract) | Requires slice reshape | This is application-level online DDL, not the SQL above |
| Logical replication to a rebuilt table + cutover | Requires slice reshape + infra | Heavy lift, not in current slice |
| `ALTER TYPE` in a maintenance window | NO | Constraint says no window ever |

The migration as written has no safe execution path inside the current slice. Running it would be an availability incident.

## (2) Gap

The slice assumes a single-statement `ALTER TABLE ... TYPE` is a valid migration shape for a 500M-row, 24/7 table. It is not. The safe variants all require something the slice does not currently authorize:

- **Tooling gap:** No online-DDL tool (`pg_repack`, `pgroll`/Reshape, `pg_squeeze`) is approved, installed, or operationally rehearsed. Each of these has non-trivial prerequisites:
  - `pg_repack` needs the extension installed on the cluster, a primary key or unique not-null index on `orders` (likely fine), sufficient disk headroom for a full table copy + indexes (~2× table size temporarily), and an operational runbook for the trigger-based capture window.
  - `pgroll`/Reshape need a declarative migration framework adopted into the deploy pipeline and a cutover plan.
- **Shape gap:** No expand/contract design exists. A safe in-app path would be:
  1. Add `amount_cents_v2 numeric(20,4)` nullable, no default.
  2. Backfill in batched, throttled chunks with `UPDATE ... WHERE id BETWEEN ...` and `vacuum`/checkpoint awareness.
  3. Dual-write from the application to both columns.
  4. Add a deferred check / trigger guaranteeing parity.
  5. Switch reads to the new column.
  6. Drop old column after a soak period.
  This is multiple slices of work and requires app changes -- not the single-statement migration in the file.
- **Risk-acceptance gap:** No explicit business sign-off exists for the alternative (taking an hours-long write outage on `orders`). Given the “no maintenance window ever” constraint, this is presumed unacceptable, but it has not been explicitly decided.
- **Verification gap:** No rehearsal on a production-sized clone. Even if a safe path is chosen, we have no measured rewrite time, WAL volume estimate, replica lag projection, or rollback plan.

## (3) Recommended next command

**STOP. Do not execute this migration. Route to `decision-interview`** to resolve the gap before any further implementation work on this slice.

The decision-interview must force an explicit choice among exactly these three branches -- none of which can be made silently inside the slice:

1. **Authorize online-DDL tooling into scope.**
   - Decide which tool: `pg_repack` (most common for type changes on Postgres 14), `pgroll`/Reshape (if a declarative pipeline is desired), or logical replication + cutover.
   - Authorize the prerequisite work: extension install, disk headroom verification, staging rehearsal on a production-sized clone, runbook, rollback plan, on-call coverage during cutover.
   - Update the slice to depend on this enablement work as a predecessor.

2. **Reshape the slice into an expand/contract migration.**
   - Replace the single `ALTER TYPE` with a multi-step plan: add new column, backfill in throttled batches, dual-write at the application layer, switch reads, drop old column.
   - This becomes several slices, requires application code changes, and changes the contract of any consumer that reads `amount_cents`.
   - Confirm there is no downstream consumer (analytics, exports, FKs, partitioning expressions, generated columns, materialized views, replication subscribers) that breaks under the column rename/swap.

3. **Accept the risk explicitly.**
   - A named decision-maker accepts an hours-long outage of the `orders` table writes and reads during the rewrite.
   - This requires a real maintenance window, which contradicts the stated “no maintenance window ever” constraint -- so this branch almost certainly resolves to “rejected,” but it must be asked explicitly so the rejection is recorded.

### What I will NOT do without that decision

- I will not run the migration as written.
- I will not silently substitute `pg_repack` or any other tool -- that is a scope expansion that requires explicit authorization.
- I will not silently reshape the slice into expand/contract -- that changes the slice contract and the application surface.
- I will not weaken the migration (e.g., `SET lock_timeout`) and pretend that makes it safe; a short `lock_timeout` just guarantees the migration fails to acquire the lock under load and accomplishes nothing.

### Inputs the decision-interview should collect

- What is the current declared type of `orders.amount_cents`? (Confirms the rewrite assumption; `bigint → numeric` and `numeric(X,Y) → numeric(20,4)` are both rewrites, but useful to log.)
- Why is `numeric(20,4)` required? (If the driver is sub-cent precision for FX/fees, confirms the new column must be `numeric`, not `bigint` in micro-units.)
- Is there any tolerated write-pause budget, even seconds? (Determines whether a fast metadata-only path via a check-constraint trick on a new column is viable.)
- What downstream systems read `amount_cents`? (Required for expand/contract safety.)
- Who owns the risk acceptance if branch 3 is taken? (Names a decision owner.)
- Is `pg_repack` already permitted on the cluster by infra/security policy, or does adoption itself require a separate approval? (Determines the real cost of branch 1.)

**Next command: `decision-interview`. Slice execution is blocked until that decision is recorded.**
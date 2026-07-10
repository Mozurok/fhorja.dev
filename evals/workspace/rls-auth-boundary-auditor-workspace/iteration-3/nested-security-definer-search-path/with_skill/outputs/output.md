# RLS / Auth Boundary Audit -- `20260606150003_audit_log_chain.sql`

Persona: `rls-auth-boundary-auditor`
Auth model: `auth.uid()` (Supabase default)
Tenant scope: per-user (`audit_log.actor_id`)
SECURITY DEFINER chain: `record_user_event` (exposed via GRANT) -> `log_action` -> `audit_log`

---

## 1. Tenant-scoped table inventory

- `audit_log` -- per-user (rows scoped by `actor_id = auth.uid()`)

The two functions are not tables but are in scope because both run `SECURITY DEFINER` and both touch `audit_log` either directly (`log_action`) or transitively (`record_user_event`).

## 2. Per-table policy posture table

| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|
| `audit_log` | YES | YES | `audit_log_select_own` (`actor_id = auth.uid()`) | MISSING (no INSERT policy; writes happen via SECURITY DEFINER) | MISSING | MISSING | partial (SELECT only) | **FAIL** |

Note: the absence of INSERT/UPDATE/DELETE policies is deliberate -- writes are intended to flow only through the SECURITY DEFINER functions. That intent makes the SECURITY DEFINER chain the entire write-side trust boundary. If that boundary is broken, there is no second line of defense, because `FORCE ROW LEVEL SECURITY` does not constrain a `SECURITY DEFINER` function running as the owner if the function bypasses the predicate (which is exactly what happens here).

## 3. Function-by-function audit (SECURITY DEFINER chain)

### `log_action(p_action text, p_payload jsonb)` -- INNER function

| Check | Status | Notes |
|---|---|---|
| `SECURITY DEFINER` | YES | Runs as function owner (postgres). |
| Explicit `SET search_path` | **YES** -- `pg_catalog, public` | Locked at function level. |
| Unqualified table references | `audit_log` | Resolved against the function's own `search_path`, NOT the caller's. Safe in isolation. |
| Unqualified `auth.uid()` call | N/A in this function (only `INSERT`; `auth.uid()` is called but it is in the `auth` schema, which is searchable via `public` extension semantics -- see §4 caveat) | Actually `auth.uid()` here resolves under the function's own `search_path`. Safe. |
| RLS-aware guard at entry | NO explicit check (e.g. no `IF auth.uid() IS NULL THEN RAISE`) | Acceptable because `auth.uid()` is used directly inside the INSERT VALUES list; a NULL `auth.uid()` would fail the table's `NOT NULL` constraint on `actor_id`. Marginal but not a P1 on its own. |
| Volatility / dynamic SQL | None | No `EXECUTE` of user input. |

Verdict in isolation: **PASS (when called directly).**

### `record_user_event(p_event text, p_details jsonb)` -- OUTER function (exposed via GRANT)

| Check | Status | Notes |
|---|---|---|
| `SECURITY DEFINER` | YES | Runs as function owner (postgres). |
| Explicit `SET search_path` | **NO** | **P1 GAP.** The function inherits the **caller's** `search_path` at planning/resolution time. |
| Unqualified function call: `log_action(...)` | YES | Resolved against the caller-controlled `search_path`. |
| RLS-aware guard at entry | NO | No `auth.uid()` null check, no actor binding into a local before the inner call. |
| Volatility / dynamic SQL | None | But the unqualified call to `log_action` is itself the hijack vector. |

Verdict in isolation: **FAIL (P1).**

## 4. Gap -- search_path hijacking via the nested SECURITY DEFINER chain

**P1 -- `record_user_event` is missing `SET search_path` and resolves `log_action` (an unqualified function reference) through the calling role's session `search_path`. An authenticated attacker can place a function named `log_action` ahead of `public` on their own `search_path` and have the OUTER SECURITY DEFINER function call the ATTACKER's function with the OWNER's privileges.**

Concrete failure mode tied to the SQL under audit:
1. `record_user_event` is `SECURITY DEFINER` with no `SET search_path`.
2. PostgreSQL resolves `log_action(...)` against the **caller's** `search_path` because the function did not pin one.
3. The attacker U_evil owns a schema `evil_schema` and creates `evil_schema.log_action(text, jsonb)` matching the signature.
4. U_evil sets `SET search_path = evil_schema, public;` and calls `SELECT record_user_event('test', '{}');`.
5. The planner resolves `log_action` to `evil_schema.log_action`, **executed with the postgres role's privileges** because `record_user_event` is SECURITY DEFINER.
6. `evil_schema.log_action` can now do anything the postgres role can -- including, but not limited to: writing to `audit_log` with an arbitrary `actor_id`, reading any table, calling `SET ROLE postgres;`, granting itself privileges, exfiltrating secrets, or chaining into further `SECURITY DEFINER` functions.

This is a textbook PostgreSQL CVE-class issue (the same shape as CVE-2018-1058 / [PostgreSQL Function/Trigger search_path hijacking](https://www.postgresql.org/docs/current/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY)). The fact that the INNER function (`log_action`) correctly pins `search_path` is **irrelevant**, because the attacker's function is invoked **instead of** the legitimate `log_action`; the legitimate function is never reached.

### Answer to the scenario question

> Can U_evil cause `record_user_event`'s `log_action` invocation to insert `audit_log` rows attributed to a different `actor_id`?

**Yes, and worse.** U_evil's hijacked `evil_schema.log_action(text, jsonb)` executes as postgres. The attacker is not limited to forging `actor_id`:

- The `evil_schema.uid()` shadowing of `auth.uid()` referenced in the scenario is a separate vector that would matter if `record_user_event` itself called `auth.uid()` unqualified (it does not in the current source). But the same call inside the legitimate `log_action` would also be hijacked **if** `log_action`'s own `SET search_path` did not include `pg_catalog` ahead of an attacker-controlled schema. Here `log_action` pins `pg_catalog, public`, which does NOT contain `auth`, so `auth.uid()` is always resolved schema-qualified by name -- that specific sub-attack is blocked. But it is moot because the legitimate `log_action` is never invoked: `evil_schema.log_action` is called instead.
- Inside `evil_schema.log_action`, the attacker can run arbitrary SQL as postgres: `INSERT INTO public.audit_log (actor_id, action, payload) VALUES ('<any-uuid>', p_action, p_payload);` forges the actor; `ALTER ROLE u_evil SUPERUSER;` escalates; `SELECT pg_read_server_files(...)` exfiltrates.
- Because `audit_log` has `FORCE ROW LEVEL SECURITY`, even the owner is subject to RLS by default -- **except** that `FORCE` is bypassed inside `SECURITY DEFINER` functions running as the owner *when the function explicitly writes*. There is no policy on INSERT, so a direct `INSERT` from the hijacked function succeeds regardless.

**Severity: P1 -- privilege escalation to the function owner (postgres) for any authenticated user.**

## 5. Follow-the-data trace (search_path resolution leak)

Trace of how the caller's `search_path` propagates through the chain:

1. Session: `U_evil` (authenticated) runs `SET search_path = evil_schema, public;`. Session `search_path` is now `evil_schema, public`.
2. `SELECT record_user_event('test', '{}');` is called.
3. PostgreSQL enters `record_user_event`. Because the function has **no `SET search_path` clause**, the function body executes with the **caller's** `search_path` (`evil_schema, public`). The `SECURITY DEFINER` attribute changes the **effective user** (to postgres) but NOT the `search_path`; `search_path` is GUC-scoped and is inherited from the calling session unless explicitly overridden.
4. The function body contains `PERFORM log_action(p_event, p_details);`. The name `log_action` is **unqualified**.
5. The planner looks up `log_action(text, jsonb)` by walking `search_path` in order: `evil_schema` first. `evil_schema.log_action(text, jsonb)` exists and matches.
6. `evil_schema.log_action` is called. It runs with the **postgres role's privileges** because it is called inside a `SECURITY DEFINER` function and PostgreSQL does NOT drop the elevated privilege between statements within the function body.
7. The legitimate `public.log_action` is never reached. Its carefully-pinned `search_path` is irrelevant.

The leak path in one line:
`session.search_path → record_user_event (SECURITY DEFINER, NO search_path pin) → unqualified log_action lookup → evil_schema.log_action(...) executed as postgres → arbitrary writes to audit_log + arbitrary SQL as owner`.

## 6. SECURITY DEFINER function audit

| function | SECURITY DEFINER | SET search_path | unqualified callees | RLS-aware guard | dynamic SQL | verdict |
|---|---|---|---|---|---|---|
| `log_action` | YES | YES (`pg_catalog, public`) | `audit_log` (table), `auth.uid()` (schema-qualified) | implicit via NOT NULL on `actor_id` | none | PASS in isolation |
| `record_user_event` | YES | **NO** | `log_action` (function) | none | none | **FAIL -- P1** |

## 7. service_role usage audit

Not applicable to this migration (no application-code call sites in scope). The functional equivalent in this DDL -- a `SECURITY DEFINER` function exposed to `authenticated` -- is already covered in §6 above. The exposure of `record_user_event` to `authenticated` via `GRANT EXECUTE` is justified by the use case (audit logging) but the function's current implementation makes the grant a privilege-escalation vector. Tighten the function (§8), not the grant.

## 8. Remediation -- migration-shaped

Create a new follow-up migration. Two fixes are required; both are mandatory.

```sql
-- migrations/20260606150004_audit_log_chain_harden_search_path.sql

-- Fix 1 (P1): pin search_path on record_user_event so the caller's
-- search_path cannot hijack the unqualified log_action lookup.
-- Use schema-qualified call as defense in depth so even a future
-- accidental removal of SET search_path cannot reintroduce the bug.
CREATE OR REPLACE FUNCTION public.record_user_event(p_event text, p_details jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
  -- Schema-qualified call: belt-and-suspenders against future search_path drift.
  PERFORM public.log_action(p_event, p_details);
END;
$$;

-- Fix 2 (defense in depth): schema-qualify the table reference in log_action
-- so even if a future edit drops SET search_path, the table lookup cannot
-- be hijacked by a caller-controlled schema.
CREATE OR REPLACE FUNCTION public.log_action(p_action text, p_payload jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
  -- Reject unauthenticated callers explicitly rather than relying on
  -- the NOT NULL constraint to surface a confusing error.
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'log_action: auth.uid() is NULL; refusing to insert audit row';
  END IF;

  INSERT INTO public.audit_log (actor_id, action, payload)
  VALUES (auth.uid(), p_action, p_payload);
END;
$$;

-- Fix 3 (lockdown): revoke public execute on log_action so only
-- record_user_event (running as owner) can reach it. This prevents
-- a future GRANT to authenticated from creating a second exposed path.
REVOKE ALL ON FUNCTION public.log_action(text, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.log_action(text, jsonb) FROM authenticated;

-- Fix 4 (lockdown): re-affirm grants on the exposed wrapper.
REVOKE ALL ON FUNCTION public.record_user_event(text, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_user_event(text, jsonb) TO authenticated;
```

Why each line matters:

- `SET search_path = pg_catalog, public` on `record_user_event` is the actual fix to the reported vulnerability. With this line, the unqualified `log_action` is resolved against `pg_catalog, public` regardless of what the caller's session `search_path` says.
- Schema-qualifying `public.log_action(...)` inside `record_user_event` is defense in depth: the call site can no longer be hijacked even if `SET search_path` is ever removed during a future refactor.
- Schema-qualifying `public.audit_log` inside `log_action` is the same idea applied one level deeper.
- The `auth.uid() IS NULL` guard turns silent NOT NULL failures into explicit, observable refusals -- useful for debugging and for blocking any path where `record_user_event` could be reached without an authenticated session (e.g. via a future cron path).
- `REVOKE ... FROM PUBLIC, authenticated` on `log_action` removes the inner function from the attack surface; only the wrapper (`record_user_event`) is callable by `authenticated`, and it now reaches `log_action` via its own SECURITY DEFINER ownership.

## 9. PROPOSED block draft (DECISIONS.md)

```md
<!-- PROPOSED by rls-auth-boundary-auditor: 2026-06-05 -->
### D-N: SECURITY DEFINER function authoring contract (search_path pin + schema-qualified callees)

Context: The `audit_log_chain` migration shipped a SECURITY DEFINER wrapper
(`record_user_event`) that did not pin `search_path`, exposing a
search_path-hijack privilege-escalation path against the function owner
(postgres). The fix (follow-up migration `..._harden_search_path.sql`)
applied four defenses: SET search_path on every SECURITY DEFINER function,
schema-qualified callees inside the function body, schema-qualified table
references, and revoke-by-default on inner helper functions.

Decision (proposed): Adopt as a project rule for all future SECURITY DEFINER
functions in this Supabase schema:
1. MUST declare `SET search_path = pg_catalog, public` (or a stricter set).
2. MUST schema-qualify every table, view, and function reference inside the body.
3. MUST guard `auth.uid() IS NULL` at entry when the function attributes any
   row to the caller.
4. MUST be `REVOKE ALL ... FROM PUBLIC, authenticated` unless explicitly
   granted to `authenticated` as a wrapper.

Alternatives considered:
- Pin search_path only (no schema qualification): rejected -- leaves a single
  point of failure when a future edit drops the SET clause.
- Mark helper functions `SECURITY INVOKER`: rejected for this case because
  RLS would then block inserts (`audit_log` has no INSERT policy by design).

Owner: backend / DB.
Locking criterion: route to `decision-interview` before merging the
follow-up migration.
```

## 10. `<task>/RLS_AUDIT.md` content draft (excerpt for this migration)

```md
# RLS Audit -- audit_log chain

**Migration audited:** `migrations/20260606150003_audit_log_chain.sql`
**Run timestamp:** 2026-06-05
**Auditor:** rls-auth-boundary-auditor
**Aggregate verdict:** FAIL (1x P1)

## Per-table posture

| table | RLS | FORCE | SELECT | INSERT | UPDATE | DELETE | tenant predicate | verdict |
|---|---|---|---|---|---|---|---|---|
| audit_log | YES | YES | own-row | n/a (DEFINER path) | n/a | n/a | yes (SELECT only) | FAIL (write-side trust boundary is broken) |

## Findings

- **P1 -- search_path hijack via nested SECURITY DEFINER chain.**
  `record_user_event` is `SECURITY DEFINER` without `SET search_path`.
  The unqualified call to `log_action` resolves through the caller's
  session `search_path`, allowing any authenticated user to shadow
  `log_action` in an owned schema and execute arbitrary SQL as the
  function owner (postgres). See remediation `..._harden_search_path.sql`.

## Audit history

| run_at | run_id | migrations | verdict |
|---|---|---|---|
| 2026-06-05 | nested-security-definer-search-path | 20260606150003_audit_log_chain.sql | FAIL |
```

## 11. Recommended next command

`implementation-plan` -- slice the follow-up migration (`..._harden_search_path.sql`) as a single P1 hotfix slice, with acceptance criteria pinned to: (a) every SECURITY DEFINER function in scope has `SET search_path` declared, (b) every callee inside a SECURITY DEFINER body is schema-qualified, (c) `REVOKE ... FROM PUBLIC, authenticated` is asserted on inner helpers. If the project rule in §9 (`D-N`) needs locking before the slice runs, route via `decision-interview` first.

---

### Command transcript

- Loaded persona `rls-auth-boundary-auditor` SKILL.md, followed Steps 1-8 + 10.
- Parsed migration; identified one tenant-scoped table (`audit_log`) and two SECURITY DEFINER functions.
- Traced search_path leak through outer function; confirmed P1 hijack against `log_action` call site.
- Produced migration-shaped remediation with four defenses (pin + qualify callees + qualify tables + revoke-by-default).

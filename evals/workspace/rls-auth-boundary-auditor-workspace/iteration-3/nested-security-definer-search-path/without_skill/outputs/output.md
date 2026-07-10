# Audit: Nested SECURITY DEFINER chain -- search_path hijacking

## 1. Function-by-function audit

### `record_user_event(p_event text, p_details jsonb)` (OUTER, exposed via GRANT)

| Property | Value |
|---|---|
| Language | plpgsql |
| Security mode | `SECURITY DEFINER` → runs as function OWNER (postgres) |
| `SET search_path` | **NOT SET** -- inherits caller's `search_path` |
| Grants | `EXECUTE ... TO authenticated` |
| Unqualified identifiers in body | `log_action(...)` (function call) |
| Notes | This is the attack surface. Because there is no `SET search_path`, the session-level `search_path` of the authenticated caller is in effect during execution of this function's body. Any unqualified name resolution (including the lookup of `log_action`) happens against the caller-controlled path. |

### `log_action(p_action text, p_payload jsonb)` (INNER)

| Property | Value |
|---|---|
| Language | plpgsql |
| Security mode | `SECURITY DEFINER` → runs as function OWNER (postgres) |
| `SET search_path` | `pg_catalog, public` (explicit, safe) |
| Grants | None explicitly -- inherits default `EXECUTE` to `PUBLIC` unless revoked |
| Unqualified identifiers in body | `audit_log` (table), `auth.uid()` (schema-qualified -- OK) |
| Notes | Once control actually enters this function, the `SET search_path = pg_catalog, public` clause takes effect for the duration of the body. So `audit_log` resolves to `public.audit_log` safely, and `auth.uid()` is schema-qualified explicitly. **This function in isolation is correctly hardened.** The vulnerability is not inside `log_action`; it is in *how `log_action` itself gets resolved* during the call from the outer function. |

### Table `audit_log`

| Property | Value |
|---|---|
| RLS | `ENABLE` + `FORCE` (good -- applies even to table owner via non-bypassrls roles) |
| Policy | `audit_log_select_own` -- `SELECT` only where `actor_id = auth.uid()` |
| Writes | No `INSERT` / `UPDATE` / `DELETE` policy defined. Direct writes from `authenticated` would be blocked. Inserts succeed here only because they go through a `SECURITY DEFINER` function owned by a role that bypasses RLS (postgres) or because `FORCE RLS` is satisfied via the owner -- but the inserted `actor_id` is whatever `auth.uid()` returns inside `log_action`. |

---

## 2. Gap: search_path hijacking via the nested SECURITY DEFINER chain

**Defect class:** CWE-426 / CWE-427 -- search_path hijacking against an unqualified identifier inside a `SECURITY DEFINER` function whose `search_path` is caller-controlled.

The critical insight: `SET search_path` on a function is applied **when execution enters that function's body**, not when the function is *looked up* by an outer caller. So:

- `record_user_event` has **no** `SET search_path`. While its body executes (as postgres, because SECURITY DEFINER), name resolution uses the **caller's** `search_path`.
- Inside that body there is one unqualified identifier reference: `log_action(p_event, p_details)`.
- Resolving `log_action` happens **before** any `SET search_path` clause on `log_action` takes effect. The lookup walks the caller's search_path schema-by-schema looking for a function named `log_action(text, jsonb)`.
- If the attacker can place a function with that exact name and signature in a schema that appears earlier in the search path than `public`, the attacker's function is called instead of `public.log_action` -- and it is called **with the elevated privileges of postgres**, because we are still inside the SECURITY DEFINER body of `record_user_event`.

The attack scenario described in the prompt (planting `evil_schema.uid()` and overriding `auth.uid()`) is a real shape of the same defect class but does **not** actually fire here, because:

- `record_user_event` only references `log_action` unqualifiedly. It does not call `auth.uid()` itself.
- Inside `log_action`, the explicit `SET search_path = pg_catalog, public` takes effect before `auth.uid()` is referenced. And `auth.uid()` is **schema-qualified** (`auth.uid()`), not bare `uid()`. So even with `evil_schema` first on the path, `auth.uid()` resolves to the real `auth.uid()` -- the attacker's `evil_schema.uid()` is in a different schema than the qualified reference.

So the specific "rewrite `actor_id` by shadowing `uid()`" attack as stated **does not succeed** -- but only by accident of two correct decisions in the inner function (qualified `auth.`, explicit `SET search_path`). The defect class is still present and *is* exploitable through the unqualified `log_action` reference in the outer function.

### Working exploit shape against this exact migration

```sql
-- as authenticated user U_evil
CREATE SCHEMA evil_schema;

CREATE FUNCTION evil_schema.log_action(p_action text, p_payload jsonb)
RETURNS void LANGUAGE sql AS $$
  -- runs with postgres privileges because the outer SECURITY DEFINER frame is still active
  INSERT INTO public.audit_log (actor_id, action, payload)
  VALUES ('00000000-0000-0000-0000-000000000001'::uuid, p_action, p_payload);
  -- or: ALTER ROLE postgres ... / GRANT ... / arbitrary SQL as postgres
$$;

SET search_path = evil_schema, public;
SELECT record_user_event('test', '{}'::jsonb);
```

Result: `record_user_event` (running as postgres) calls `log_action(text, jsonb)`. Name resolution under the attacker's session search_path finds `evil_schema.log_action` **first**, so it executes the attacker's body with postgres privileges. The attacker can spoof `actor_id`, write to any table, or escalate further (alter roles, drop policies, exfiltrate, etc.). The audit log integrity is gone, and in fact this is full privilege escalation to postgres, not just an actor_id spoof.

So the answer to the question as asked: the *specific* `uid()` shadow does not succeed because of the qualified `auth.uid()` reference inside the safely-pinned inner function. But the same defect class **does** allow U_evil to insert audit rows attributed to any actor they choose (and far worse) by shadowing `log_action` itself -- which is the unqualified identifier the outer function actually resolves through the leaked path.

---

## 3. Follow-the-data trace: how the caller's search_path leaks

```
session: authenticated user U_evil
  SET search_path = evil_schema, public;
  current_setting('search_path') = 'evil_schema, public'

  CALL record_user_event('test', '{}')
   ├─ Postgres looks up record_user_event in caller's search_path
   │   → finds public.record_user_event (only definition)
   ├─ Enters function body
   │   ├─ proconfig search_path? NULL  ◀── NO `SET search_path` on this function
   │   ├─ Effective search_path INSIDE body = caller's = 'evil_schema, public'
   │   ├─ Effective role        INSIDE body = postgres (SECURITY DEFINER)
   │   │
   │   └─ Statement: PERFORM log_action(p_event, p_details)
   │       ├─ Resolve function name `log_action(text, jsonb)`
   │       │   ├─ Walk search_path:
   │       │   │   ├─ evil_schema → evil_schema.log_action(text, jsonb)  ◀── HIT
   │       │   │   └─ public      → not consulted
   │       │   └─ Selected: evil_schema.log_action
   │       │
   │       └─ Invoke evil_schema.log_action(...)
   │           ├─ proconfig search_path on this function? NONE
   │           ├─ Inherits current frame's effective search_path
   │           ├─ Inherits current frame's effective role = postgres
   │           └─ Body runs arbitrary SQL as postgres
   └─ Returns
```

The leak point is the single arrow at `proconfig search_path? NULL` on `record_user_event`. From that point downward, every unqualified name resolution in this call stack uses the attacker's path until some frame explicitly pins it. The defenses on `log_action` (the inner `SET search_path = pg_catalog, public` and the schema-qualified `auth.uid()`) never get to run, because lookup never reaches `public.log_action` in the first place.

A secondary, more subtle channel: even if you fixed `record_user_event` to qualify the call (`PERFORM public.log_action(...)`), the outer function still has no `SET search_path`, and any future maintainer who adds an unqualified identifier (e.g. a helper function call, an unqualified table read, a cast like `::text` against an operator class lookup) reopens the same defect. The pin belongs on the function, not on individual call sites.

---

## 4. Remediation (migration-shaped)

Three layers of fix. Apply all three.

```sql
-- migrations/20260606150004_audit_log_chain_fix.sql

BEGIN;

-- (a) Pin search_path on the OUTER SECURITY DEFINER function.
--     This is the load-bearing fix. From the moment the body starts executing,
--     all unqualified name resolution uses pg_catalog, public (not caller's path).
ALTER FUNCTION public.record_user_event(text, jsonb)
  SET search_path = pg_catalog, public;

-- (b) Defense in depth: schema-qualify the inner call so resolution does not
--     depend on search_path even if a future edit drops the SET clause.
CREATE OR REPLACE FUNCTION public.record_user_event(p_event text, p_details jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
  PERFORM public.log_action(p_event, p_details);
END;
$$;

-- (c) Lock down EXECUTE on both functions so PUBLIC cannot call them and
--     only the intended role can invoke the outer surface. PUBLIC EXECUTE on
--     SECURITY DEFINER functions is a common foot-gun.
REVOKE ALL ON FUNCTION public.record_user_event(text, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.log_action(text, jsonb)        FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_user_event(text, jsonb) TO authenticated;
-- log_action is an internal helper; do NOT grant it to authenticated.
-- It is reachable only via record_user_event.

-- (d) Add the missing INSERT policy so audit_log is not silently dependent on
--     SECURITY DEFINER bypass. If someone later changes the function to
--     SECURITY INVOKER, the writes still need a path. Pick ONE of:
--   Option 1 (preferred): keep writes funnel-only via SECURITY DEFINER, and
--     leave no INSERT policy -- direct writes from authenticated remain blocked.
--     Document this invariant.
--   Option 2: add a narrow INSERT policy:
-- CREATE POLICY audit_log_insert_own ON public.audit_log
--   FOR INSERT TO authenticated
--   WITH CHECK (actor_id = auth.uid());

-- (e) Belt-and-braces: ensure the functions are OWNED by a role you control,
--     not by a role any tenant can assume.
ALTER FUNCTION public.record_user_event(text, jsonb) OWNER TO postgres;
ALTER FUNCTION public.log_action(text, jsonb)        OWNER TO postgres;

COMMIT;
```

### Why each step

- **(a)** is the minimal patch that closes the actual hole. `SET search_path = pg_catalog, public` on every `SECURITY DEFINER` function is non-negotiable; the absence of it on the outer function is the root cause.
- **(b)** makes the call resilient to future regressions. Qualifying with `public.log_action` means even if a future edit removes the `SET` clause, the inner call still resolves correctly. Belt and braces.
- **(c)** removes the implicit `EXECUTE TO PUBLIC` grant that Postgres adds to every new function. If the attacker can `EXECUTE` `log_action` directly with their own (untrusted) `auth.uid()` value, they can also flood the audit log with junk events attributed to themselves -- much weaker than the original exploit, but still wrong.
- **(d)** removes a hidden coupling between RLS and SECURITY DEFINER. Today, `audit_log` only accepts writes because they come from a definer function owned by `postgres`. A `FORCE ROW LEVEL SECURITY` table with no `INSERT` policy is intentional but fragile.
- **(e)** ensures that even if `evil_schema` exists, no attacker can `ALTER FUNCTION ... OWNER TO evil_role` and self-elevate.

### Codebase-wide follow-up (out of scope of this migration but should be tracked)

Grep every existing `SECURITY DEFINER` function in the schema for:

1. Missing `SET search_path = ...` clause.
2. Unqualified identifier references (tables, functions, types, operators).
3. `EXECUTE` granted to `PUBLIC` rather than a specific role.

Each one is the same defect class. The pattern is mechanical and worth automating in a pre-deploy lint (regex over migration files, or a SQL query against `pg_proc` joined with `pg_proc_config`).

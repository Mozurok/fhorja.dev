# RLS Auth Boundary Audit -- 20260605120002_get_user_notes.sql

## 1. Tenant-scoped table inventory
- notes -- per-user (tenant key: notes.user_id)

## 2. Per-table policy posture
| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | Tenant predicate present | Verdict |
|---|---|---|---|---|---|---|---|---|
| notes | yes | yes | user_owns_note | missing | missing | missing | yes (SELECT only) | FAIL |

## 3. Gaps and severities
1. P1 -- SECURITY DEFINER function get_all_notes() bypasses RLS.
2. P1 -- SECURITY DEFINER function has no SET search_path.
3. P1 -- No INSERT policy on notes.
4. P1 -- No UPDATE policy on notes.
5. P2 -- No DELETE policy on notes.
6. P2 -- EXECUTE on get_all_notes() not revoked from PUBLIC.

## 4. Remediation (migration-shaped)
```sql
CREATE POLICY notes_insert_own ON notes FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY notes_update_own ON notes FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY notes_delete_own ON notes FOR DELETE USING (user_id = auth.uid());

CREATE OR REPLACE FUNCTION public.get_all_notes() RETURNS SETOF public.notes
  LANGUAGE sql SECURITY DEFINER STABLE
  SET search_path = pg_catalog, public
AS $X$
  SELECT * FROM public.notes WHERE user_id = (SELECT auth.uid()) AND auth.uid() IS NOT NULL;
$X$;

REVOKE ALL ON FUNCTION public.get_all_notes() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_all_notes() FROM anon;
GRANT EXECUTE ON FUNCTION public.get_all_notes() TO authenticated;
```

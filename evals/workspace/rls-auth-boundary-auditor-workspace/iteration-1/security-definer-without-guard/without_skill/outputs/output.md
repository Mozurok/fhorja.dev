# RLS Bypass Audit: get_all_notes SECURITY DEFINER Function

## (1) Per-Table Posture
| Table | RLS Enabled | FORCE RLS | Policies | DEFINER Bypass Risk | Status |
|-------|-------------|-----------|----------|---------------------|--------|
| notes | Yes | Yes | user_owns_note (SELECT, USING + WITH CHECK on user_id = auth.uid()) | HIGH | BROKEN |

## (2) Gaps
G1 -- SECURITY DEFINER with no auth.uid() filter inside body. Critical/P1.
G2 -- No SET search_path. High/P1.
G3 -- No REVOKE FROM PUBLIC / explicit GRANT.

## (3) Remediation
```sql
REVOKE ALL ON FUNCTION public.get_all_notes() FROM PUBLIC;
DROP FUNCTION IF EXISTS public.get_all_notes();
CREATE OR REPLACE FUNCTION public.get_user_notes() RETURNS SETOF public.notes
  LANGUAGE sql SECURITY DEFINER STABLE
  SET search_path = pg_catalog, public
AS $X$
  SELECT n.* FROM public.notes n WHERE n.user_id = auth.uid() AND auth.uid() IS NOT NULL;
$X$;
GRANT EXECUTE ON FUNCTION public.get_user_notes() TO authenticated;
```

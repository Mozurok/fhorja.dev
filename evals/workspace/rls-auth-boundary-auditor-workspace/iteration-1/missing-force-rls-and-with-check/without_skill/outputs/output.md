# Tenant Isolation Audit -- documents migration

## 1) Per-table posture

| Table | RLS Enabled | FORCE RLS | SELECT policy | INSERT policy | UPDATE policy | DELETE policy | WITH CHECK | FK to auth.users | NOT NULL on tenant col |
|---|---|---|---|---|---|---|---|---|---|
| documents | Yes | No | Implicit via FOR ALL | Implicit via FOR ALL (USING only -- no WITH CHECK) | Implicit via FOR ALL (USING only -- no WITH CHECK) | Implicit via FOR ALL | Missing | Missing | Yes (user_id NOT NULL) |

## 2) Gaps

P1 -- Missing WITH CHECK on writes (cross-tenant write).
P1 -- No FORCE ROW LEVEL SECURITY.
P2 -- No FK from user_id to auth.users(id).
P2 -- No default for user_id.
P2 -- FOR ALL collapses 4 verbs.
P3 -- No index on user_id.
P3 -- created_at not NOT NULL.

## 3) Remediation migration

```sql
BEGIN;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_owns_doc ON documents;
CREATE POLICY documents_select_own ON documents FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY documents_insert_own ON documents FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY documents_update_own ON documents FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY documents_delete_own ON documents FOR DELETE TO authenticated USING (user_id = auth.uid());
COMMIT;
```

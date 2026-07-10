# RLS Audit -- 20260605120001_documents.sql
Aggregate verdict: FAIL

## 1. Tenant-scoped table inventory
- documents -- per-user

## 2. Per-table policy posture
| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|
| documents | YES | NO | user_owns_doc | USING present; WITH CHECK missing | USING present; WITH CHECK missing | user_owns_doc | YES | FAIL |

## 3. Gaps and severities
1. P1 -- Missing WITH CHECK on INSERT/UPDATE (FOR ALL with USING only). Cross-tenant write.
2. P1 -- No FORCE ROW LEVEL SECURITY. Owner role bypasses.
3. P2 -- No FK to auth.users(id).
4. P2 -- No index on user_id.
5. P3 -- created_at nullable.

## 4. Remediation per gap
```sql
DROP POLICY IF EXISTS user_owns_doc ON documents;
CREATE POLICY documents_select_own ON documents FOR SELECT USING (user_id = auth.uid());
CREATE POLICY documents_insert_own ON documents FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY documents_update_own ON documents FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY documents_delete_own ON documents FOR DELETE USING (user_id = auth.uid());
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE documents ADD CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS documents_user_id_idx ON documents (user_id);
ALTER TABLE documents ALTER COLUMN created_at SET NOT NULL;
```

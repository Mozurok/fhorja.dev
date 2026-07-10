# RLS Audit -- 20260605120003_projects_and_collaborators.sql

## 1. Tenant-scoped table inventory
- projects -- per-user
- project_collaborators -- per-user via parent join

## 2. Per-table policy posture
| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|
| projects | YES | YES | YES (owner_sees_project) | NONE | NONE | NONE | partial | FAIL |
| project_collaborators | NO | NO | NONE | NONE | NONE | NONE | NONE | FAIL |

## 3. Gaps and severities
1. P1 -- project_collaborators has no RLS enabled. Cross-tenant collaborator enumeration.
2. P1 -- projects has no INSERT policy. Project creation broken under FORCE.
3. P1 -- projects has no UPDATE policy.
4. P1 -- projects has no DELETE policy.
5. P2 -- owner_sees_project declares WITH CHECK on FOR SELECT (no-op).

## 4. Remediation per gap
```sql
ALTER TABLE project_collaborators ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_collaborators FORCE ROW LEVEL SECURITY;

CREATE POLICY project_collaborators_select ON project_collaborators FOR SELECT USING (
  user_id = auth.uid()
  OR EXISTS (SELECT 1 FROM projects p WHERE p.id = project_collaborators.project_id AND p.owner_id = auth.uid())
);
CREATE POLICY project_collaborators_insert ON project_collaborators FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM projects p WHERE p.id = project_collaborators.project_id AND p.owner_id = auth.uid())
);

CREATE POLICY projects_insert ON projects FOR INSERT WITH CHECK (owner_id = auth.uid());
CREATE POLICY projects_update ON projects FOR UPDATE USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY projects_delete ON projects FOR DELETE USING (owner_id = auth.uid());
```

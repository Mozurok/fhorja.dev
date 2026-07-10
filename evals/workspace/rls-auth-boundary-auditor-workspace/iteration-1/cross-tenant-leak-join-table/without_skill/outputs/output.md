# RLS Audit: projects and project_collaborators

## (1) Per-Table Posture
| Table | RLS Enabled | FORCE RLS | Policies | Verdict |
|---|---|---|---|---|
| projects | Yes | Yes | 1 (owner_sees_project) | partial |
| project_collaborators | No | No | 0 | UNRESTRICTED -- cross-tenant leak |

## (2) Gaps
G1 -- RLS not enabled on project_collaborators. Critical/P1. Cross-tenant leak.
G2 -- No RLS policies on project_collaborators.
G3 -- No INSERT/UPDATE/DELETE policy on project_collaborators.
G4 -- No INSERT/UPDATE/DELETE policies on projects.

## (3) Remediation Migration
```sql
ALTER TABLE project_collaborators ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_collaborators FORCE ROW LEVEL SECURITY;

CREATE POLICY collaborators_select ON project_collaborators FOR SELECT USING (
  user_id = auth.uid() OR EXISTS (SELECT 1 FROM projects p WHERE p.id = project_collaborators.project_id AND p.owner_id = auth.uid())
);
CREATE POLICY collaborators_insert ON project_collaborators FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM projects p WHERE p.id = project_collaborators.project_id AND p.owner_id = auth.uid())
);

CREATE POLICY owner_inserts_project ON projects FOR INSERT WITH CHECK (owner_id = auth.uid());
CREATE POLICY owner_updates_project ON projects FOR UPDATE USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY owner_deletes_project ON projects FOR DELETE USING (owner_id = auth.uid());
```

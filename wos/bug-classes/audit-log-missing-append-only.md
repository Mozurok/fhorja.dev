---
name: audit-log-missing-append-only
category: observability
default-severity: P1
cwe: [CWE-778]
languages: [sql, typescript]
file-patterns: ["**/migrations/**/*.sql", "**/schema/**/*.sql", "**/db/**/audit*.ts", "**/server/**/audit*.ts"]
perspectives: [operator, maintainer, auditor]
reversibility-check: true
---

# audit-log-missing-append-only

## Trigger

An `audit_log` table, or an equivalent compliance trail, is defined and written to, but the database does not enforce append-only semantics. Application code, or any role holding table privileges, can UPDATE or DELETE existing audit rows, so the trail can be silently rewritten after the fact. For regulated workloads this collapses the forensic value of the log entirely and is grounds for regulator rejection.

A tampered audit trail is worse than no audit trail, because it gives false confidence that logs exist while those logs are mutable.

CWE-778 (Insufficient Logging). A log that can be silently rewritten provides insufficient evidentiary value, which is the failure this CWE describes along the integrity-of-logging dimension.

## Detection

Grep heuristics:

```
# Find UPDATE or DELETE statements targeting the audit table
rg -n "UPDATE\s+audit_log|DELETE\s+FROM\s+audit_log" --type sql --type ts

# Find ORM mutation calls on the audit model
rg -n "audit_log.*\.(update|delete|destroy)\b" --type ts
```

Schema-level check (PostgreSQL):

```sql
-- List privileges on the audit table; UPDATE/DELETE for non-DBA roles is a finding
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'audit_log';
```

Shapes to look for by reading:

- An `audit_log` (or `events`, `activity_log`, `compliance_log`) table created with a standard `CREATE TABLE` carrying no append-only constraint and no privilege revoke.
- ORM models for the audit table exposing `.update()` or `.delete()` methods that nothing blocks at the application layer.
- Application code that corrects audit rows in place, for example updating a `status` column on an existing row instead of inserting a compensating row.
- Migrations that ALTER existing audit rows to backfill new columns instead of writing forward-only rows.
- No tamper-evident column on the table: no monotonic sequence, no previous-row hash, no signed payload.

Red flags, each sufficient on its own:

- No `REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC` (or from the application role) anywhere in migrations.
- No tamper-evident column (`sequence_id BIGSERIAL`, `prev_hash`, `row_hash`, signed payload).
- No rule or trigger that blocks or raises on UPDATE and DELETE.

## Retrieval

- The migration that creates the audit table, plus every later migration touching it (`**/migrations/**/*.sql`, `**/schema/**/*.sql`), because the grant posture is established at creation and drifts afterward.
- Every grant and revoke statement naming the audit table anywhere in the migration history, since a later grant silently undoes an earlier revoke.
- The audit-writing module and the ORM model for the table (`**/db/**/audit*.ts`, `**/server/**/audit*.ts`), to see which mutation methods are reachable.
- Any code path in the diff that corrects, reconciles, or backfills audit data.
- The verifier job, if one exists, that walks a hash chain; its absence is itself part of the finding.

## Analysis prompt

Given the retrieved migrations, grants, and audit-writing code:

1. Establish the privilege posture for the audit table as it stands after the full migration history, not as of its creating migration. A revoke followed by a later broad grant leaves the table mutable, and reading only the creating migration reports the opposite of the truth.
2. Is there a second layer beneath privileges: a rule or trigger that blocks UPDATE and DELETE regardless of grants? Privileges drift with every role change; a rule holds when they do. Report the presence or absence of each layer separately rather than as one control.
3. Is the table tamper-evident, or only append-only? These are different properties. Append-only means nobody can rewrite a row; tamper-evident means a rewrite would be detectable if it happened. A monotonic sequence plus a creation timestamp is the minimum; a hash chain where each row commits to its predecessor is the strong form.
4. Trace every write path to the audit table in the diff. Does any of them mutate an existing row? A correction expressed as an in-place edit is the defect even when the edit is honest, because the mechanism that permits an honest correction permits a dishonest one and leaves no trace of either.
5. If a hash chain exists, is there a job that actually walks it? An unverified chain detects nothing: it records evidence that no one reads, which turns tampering into a silent event rather than a paged one.
6. Recommend fixes in this order, each one holding when the previous drifts: revoke UPDATE, DELETE, and TRUNCATE from every non-DBA role and grant only INSERT and SELECT to the application role; add a rule or trigger that blocks UPDATE and DELETE even if privileges drift; add tamper-evident columns (at minimum a monotonic sequence and a creation timestamp, ideally a hash chain committing each row to its predecessor); remove every mutation path on the audit model at the application layer so corrections are new compensating rows referencing the original sequence id; add a periodic verifier that walks the chain and pages on a break; and document the append-only contract in the compliance runbook, referenced from the migration so a future contributor reads why the constraints exist before removing one.
7. This class carries `reversibility-check: true`, and the reversibility question has a specific shape here. The control is reversible (a grant restores mutability in one statement), but its absence is not: rows altered while the table was mutable cannot be proven intact afterward, so the gap covers every row written during the window rather than only rows written after the finding.

## Severity rubric

- **P1** by default: the audit table is mutable by the application role, with no rule layer and no tamper-evident column. Justification for the tier rather than P0: this is an evidentiary and compliance failure rather than a live data exposure, and no user data leaves the system because of it. It is nonetheless a compliance-audit failure on inspection, regardless of whether tampering actually occurred, and it makes post-incident forensics impossible because an attacker or a careless operator reaching the database role can rewrite history with nothing left to show it.
- **P0**: the audit table is mutable AND the workload is under an explicit regulatory obligation to demonstrate append-only or tamper-evident logging, or the diff contains a code path that mutates audit rows in production. At that point the trail is not merely unprotected, it is actively being rewritten.
- **P2**: privileges and rules are correct while the table carries no tamper-evident column, or a hash chain exists with no verifier walking it. The trail cannot be silently rewritten, but a break would go unnoticed.

## Confidence factors

- **HIGH**: the privileges query or the migration history shows UPDATE or DELETE granted to the application role with no blocking rule; or the diff contains an UPDATE or DELETE statement, or an ORM mutation call, targeting the audit table.
- **MEDIUM**: no revoke appears in the retrieved migrations but the full grant history was not available, so the effective posture is unresolved. Running the privileges query settles it.
- **LOW**: the match is a data-retention job, an archival move, or a partition drop that is a declared and documented lifecycle operation rather than an in-place correction.

## Examples

### Positive (mutable trail)

```sql
-- migrations/..._create_audit_log.sql
CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid NOT NULL,
  action text NOT NULL,
  payload jsonb NOT NULL
);
-- no revoke, no rule, no monotonic sequence, no hash column:
-- the application role inherits full DML and can rewrite any row
```

```typescript
// server/audit.ts
export async function correctAuditEntry(id: string, status: string) {
  // in-place correction: the mechanism that allows this honest edit
  // is the same one that allows a dishonest one, and neither leaves a trace
  await db.updateTable("audit_log").set({ status }).where("id", "=", id).execute();
}
```

### Negative (append-only at the privilege layer, with a rule beneath it)

```sql
-- migrations/..._audit_log_append_only.sql
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_role;
GRANT INSERT, SELECT ON audit_log TO app_role;

-- belt and suspenders: holds even if a future grant restores privileges
CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;

-- tamper-evident: monotonic order plus a chain committing each row to its predecessor
ALTER TABLE audit_log
  ADD COLUMN sequence_id bigserial,
  ADD COLUMN created_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN prev_row_hash text,
  ADD COLUMN row_hash text NOT NULL;
```

```typescript
// server/audit.ts
export async function correctAuditEntry(originalSequenceId: number, status: string) {
  // correction as a forward-only compensating row referencing the original
  await appendAuditRow({ action: "event_corrected", corrects: originalSequenceId, status });
}
```

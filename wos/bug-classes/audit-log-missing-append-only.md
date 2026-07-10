---
name: audit-log-missing-append-only
category: observability
default-severity: P1
priority: P1
pillars: [observability, security, compliance]
cwe: [CWE-778]
languages: [sql, typescript]
file-patterns: ["**/migrations/**/*.sql", "**/schema/**/*.sql", "**/db/**/audit*.ts", "**/server/**/audit*.ts"]
perspectives: [operator, maintainer, auditor]
reversibility-check: true
---

# audit-log-missing-append-only

An audit_log table (or equivalent compliance trail) is defined and written to, but the database does NOT enforce append-only semantics. Application code or any role with table privileges can UPDATE or DELETE existing audit rows, which means the trail can be silently rewritten after the fact. For regulated workloads (insurance, finance, healthcare) this collapses the entire forensic value of the log and is grounds for regulator rejection.

## What it looks like

- An `audit_log` (or `events`, `activity_log`, `compliance_log`) table created via standard `CREATE TABLE` with no row-level append-only constraint and no privilege REVOKE.
- ORM models for the audit table expose `.update()` / `.delete()` methods that are not blocked at the application layer.
- Application code paths that "correct" audit rows in place (e.g., updating a `status` column on an existing audit row instead of inserting a new compensating row).
- Migrations that ALTER existing audit rows to backfill new columns instead of writing forward-only rows.
- No tamper-evident column on the audit table: no monotonic sequence, no `prev_row_hash`, no signed payload.
- DB roles used by the application have full DML privileges on the audit table (no `REVOKE UPDATE, DELETE`).

## Why it matters

- A tampered audit trail is worse than no audit trail: it gives false confidence that "we have logs" while the logs are mutable.
- Regulators (insurance, PCI, SOC2, HIPAA) require demonstrable append-only or tamper-evident properties. A table with open UPDATE/DELETE privileges fails compliance audit on inspection, regardless of whether tampering actually occurred.
- Post-incident forensics becomes impossible: if an attacker (or a careless operator) reaches the DB role, they can rewrite history to hide their tracks and the team cannot prove what actually happened.
- Internal investigations (fraud, dispute resolution, customer-reported issues) collapse because the source of truth is no longer authoritative.

## How to detect

Grep + schema audit:

```
# Find UPDATE or DELETE statements targeting the audit table
rg -n "UPDATE\s+audit_log|DELETE\s+FROM\s+audit_log" --type sql --type ts

# Find ORM mutation calls on the audit model
rg -n "audit_log.*\.(update|delete|destroy)\b" --type ts
```

Schema-level check (PostgreSQL):

```
-- List privileges on the audit table; UPDATE/DELETE for non-DBA roles is a finding
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'audit_log';
```

Red flags:
- No `REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC` (or from the app role) anywhere in migrations.
- No tamper-evident column (`sequence_id BIGSERIAL`, `prev_hash`, `row_hash`, signed payload).
- No row-level rule or trigger that raises on UPDATE/DELETE.

## How to fix

1. At the DB level, revoke mutation privileges from every non-DBA role:

```sql
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_role;
GRANT INSERT, SELECT ON audit_log TO app_role;
```

2. Add a belt-and-suspenders rule that blocks UPDATE/DELETE even if privileges drift:

```sql
CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;
```

3. Add tamper-evident columns. Minimum: a monotonic `sequence_id BIGSERIAL PRIMARY KEY` plus `created_at TIMESTAMPTZ DEFAULT now()`. Stronger: a hash chain where each row stores `row_hash = sha256(prev_row_hash || canonical_payload)`.

4. At the application layer, remove all `.update()` / `.delete()` paths on the audit model. Corrections are expressed as new compensating rows ("event_corrected" referencing the original `sequence_id`), not in-place edits.

5. Add a periodic verifier job that walks the hash chain and alerts on any break -- this turns silent tampering into a paged incident.

6. Document the append-only contract in the compliance runbook and reference it from the audit_log migration so future contributors understand why these constraints exist.

## CWE / standard refs

- CWE-778: Insufficient Logging. A log that can be silently rewritten provides insufficient evidentiary value, which is the failure mode CWE-778 describes for the integrity-of-logging dimension.
- Related: SOC2 CC7.2 (system monitoring evidence), PCI DSS 10.5 (secure audit trails), HIPAA 164.312(b) (audit controls).

## See also

- `wos/bug-classes/pii-encryption-boundary-leak.md` (sibling class on data-protection compliance posture)
- `wos/bug-classes/missing-business-metric.md` (sibling observability class for non-compliance signals)

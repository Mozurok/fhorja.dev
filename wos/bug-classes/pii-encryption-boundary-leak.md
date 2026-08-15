---
name: pii-encryption-boundary-leak
category: security
default-severity: P0
cwe: [CWE-312]
languages: [typescript, sql]
file-patterns: ["apps/web/src/server/api/**", "apps/web/src/server/db/**", "supabase/migrations/**", "packages/**/serializers/**"]
perspectives: [operator, maintainer, security-reviewer]
reversibility-check: true
---

# pii-encryption-boundary-leak

## Trigger

Encrypted-at-rest PII (government identifier, full bank account number, routing number, tax id) leaves the server in cleartext through an API endpoint reachable by an operator UI, admin console, or internal tool. The data was correctly encrypted at the storage layer, but a serializer, list endpoint, or accidental `SELECT *` decrypts it on read and returns the full value where only a last-4 projection, or nothing, was contractually allowed.

The boundary contract is absolute: the value must never cross the server boundary in cleartext outside the customer-self-service path, and even there only as a last-4 projection used for confirmation. There is no internal-tool exception.

CWE-312 (Cleartext Storage of Sensitive Information). "Storage" here includes any transient surface the cleartext reaches once it crosses the server boundary: a response payload, a client cache, a log line, a screenshot.

## Detection

Static and grep heuristics:

```
# Flag SELECT statements that pull the raw encrypted-PII columns
rg -n "SELECT[^;]*\b(ssn|bank_account|bank_account_number|routing_number|tax_id|gov_id)\b" \
  apps/web/src supabase/migrations packages

# Flag response schemas / serializers that expose the full field
rg -n "\b(ssn|bank_account|routing_number)\b\s*[:=]" \
  apps/web/src/server/api packages/**/serializers
```

Shapes to look for by reading:

- An API response payload containing a full 9-digit government identifier, full bank account number, or full routing number where the documented contract is last-4 only.
- A list or pagination endpoint (for example `GET /customers`, `GET /policies`) returning rows that include the encrypted-PII column already decrypted, instead of a projection that strips or truncates it.
- A `SELECT *` against a table with `ssn`, `bank_account`, `bank_account_number`, `routing_number`, `tax_id`, or `gov_id` columns flowing directly into a JSON response with no field-level allowlist in the serializer.
- Admin or operator-facing tools, not the customer self-service path, receiving cleartext. Last-4 is allowed only on the customer-self-service confirmation screen, computed at projection time, never as the full value.
- A migration that adds an encrypted column while a view or RPC exposes the decrypted form to a role that should not see it.

Runtime checks:

- Response-shape assertion in API tests: the response body must not match `\b\d{9}\b` (full government identifier) or `\b\d{8,17}\b` co-located with a `bank_account` key.
- Log-side canary: a sampling middleware scans outbound JSON for the patterns above and pages on hit. Treat the page itself as confidential and never include the matched value in it.
- Review checklist: every new endpoint touching a customer record declares explicitly which PII fields it returns, and the default is none or last-4 only.

## Retrieval

- The serializers and response DTOs for every endpoint in the diff that reads a customer record (`packages/**/serializers/**`, `apps/web/src/server/api/**`), because this class lives at the projection layer rather than at the storage layer.
- The query layer for the tables holding the encrypted columns (`apps/web/src/server/db/**`), specifically to look for `SELECT *` or a row object spread into a response.
- Migration and policy DDL for those tables (`supabase/migrations/**`), to establish whether the decrypt function is callable by the API role and whether a safe view exists.
- The decrypt helper or envelope-encryption wrapper itself, to see which role can call it and whether the full plaintext is bound to a variable that outlives the projection scope.
- Any view or RPC that reads the encrypted columns, plus the roles granted on it.

## Analysis prompt

Given the retrieved serializers, query layer, and policy DDL:

1. For every endpoint in the diff that returns a customer record, enumerate the fields it actually emits. A response built by spreading a row object, or from a `SELECT *`, does not have an enumerable field list, and that alone fails this class: the field set becomes whatever the table happens to have after the next migration.
2. For each PII field that reaches the response, is the emitted value the full plaintext or a last-4 projection? Trace where the projection happens. A truncation performed on the client is not a projection; the full value already crossed the boundary.
3. Can the API role call the decrypt function at all? Check the grants. If it can, the control is a convention in application code rather than a boundary, and an accidental `SELECT *` or a new endpoint will cross it without any code review noticing.
4. Is there a database-level floor: a policy or a dedicated safe view that hides the encrypted columns from the API role entirely? Without one, defence rests on every serializer being correct forever.
5. Does the full decrypted value get bound to a variable, logged, cached, or passed to another function beyond the projection scope? The exposure surface is not only the response body; a log line or an error payload carrying the plaintext is the same leak with a different destination.
6. Recommend fixes in this order: keep column-level encryption at rest (`pgcrypto` symmetric encrypt and decrypt, or app-level envelope encryption with a KMS) with the decrypt function callable only by a narrow service role and not by the API role; enforce a field-level allowlist in every response DTO, with no row spread and no `SELECT *` to JSON; compute the last-4 projection at the projection layer (`right(decrypt(col), 4)`) without binding the full value beyond that scope; add a safe view or policy so an accidental `SELECT *` cannot return the columns; add a per-endpoint regression test asserting the response does not match the full-value patterns.
7. This class carries `reversibility-check: true`, and reversibility is false in practice here. Once a cleartext value reaches a client, a log aggregator, a browser cache, or a screenshot, treat it as compromised: rotating the underlying identifier is expensive or impossible. If a leak already shipped, the recommendation is rotation where possible, breach notification per jurisdiction, and a record of the cleartext exposure window, not a silent fix.

## Severity rubric

- **P0**: an endpoint reachable by any authenticated caller returns the full plaintext of an encrypted-PII column, or the API role can call the decrypt function with no safe view standing between it and the raw columns. Justification for the ceiling: cleartext exposure of this data class is a reportable incident under payment-card, insurance-privacy, and state data-protection regimes; external audits fail the control that PII never leaves the server boundary in cleartext outside the customer-self-service projection; and indemnity clauses with carriers and banking partners typically place breach-notification cost and downstream fraud on the operator.
- **P1**: the response is correctly projected today, but the projection depends on a hand-maintained serializer with no allowlist enforcement and no database floor, so the next endpoint or the next migration can leak without any gate firing.
- **P2**: the full value is bound beyond the projection scope (assigned, passed onward, or reachable by an error handler) without currently reaching a response or a log sink.

## Confidence factors

- **HIGH**: the grep for the raw columns matches inside a serializer or an API path AND the response DTO has no explicit field list; or the decrypt function is granted to the API role and a `SELECT *` against the table exists in the diff.
- **MEDIUM**: a raw column appears in a query but the response shape cannot be determined from the retrieved files alone, so whether the value reaches the boundary is unresolved. Reading the serializer settles it.
- **LOW**: the match is in a migration, a backfill, a fixture, or the projection helper itself, where touching the encrypted column is the intended behavior rather than a leak.

## Examples

### Positive (cleartext crosses the boundary)

```typescript
// server/api/customers.ts
export async function getCustomer(id: string) {
  const row = await db.selectFrom("customers").selectAll().where("id", "=", id).executeTakeFirst();
  // row spread into the response: the field set is whatever the table has,
  // so ssn_decrypted rides along the moment a migration adds it
  return { ...row };
}
```

### Negative (projection at the boundary, with a floor beneath it)

```typescript
// server/api/customers.ts
export async function getCustomer(id: string) {
  const row = await db
    .selectFrom("customers_safe") // view that does not expose the encrypted columns at all
    .select(["id", "full_name", "email", "ssn_last4"]) // explicit allowlist, no spread
    .where("id", "=", id)
    .executeTakeFirst();
  return row;
}
```

```sql
-- supabase/migrations/..._customers_safe_view.sql
-- database floor: the API role cannot reach the encrypted columns even by accident
create view customers_safe as
  select id, full_name, email, right(pgp_sym_decrypt(ssn_enc, current_setting('app.pii_key')), 4) as ssn_last4
  from customers;

revoke all on customers from api_role;
grant select on customers_safe to api_role;
```

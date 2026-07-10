---
name: pii-encryption-boundary-leak
category: security
default-severity: P0
priority: P0
pillars: [security, data-integrity]
cwe: [CWE-312]
languages: [typescript, sql]
file-patterns: ["apps/web/src/server/api/**", "apps/web/src/server/db/**", "supabase/migrations/**", "packages/**/serializers/**"]
perspectives: [operator, maintainer, security-reviewer]
reversibility-check: true
---

# pii-encryption-boundary-leak

Encrypted-at-rest PII (SSN, full bank account number, routing number, government ID) leaves the server in cleartext through an API endpoint reachable by an agent UI, admin console, or internal tool. The data was correctly encrypted at the storage layer, but a serializer, list endpoint, or accidental `SELECT *` decrypts it on read and returns the full value where only a last-4 projection (or nothing) was contractually allowed.

## What it looks like

- An API response payload contains a full 9-digit SSN, full bank account number, or full routing number where the documented contract is "last-4 only".
- A list or pagination endpoint (e.g., GET /customers, GET /policies) returns rows that include the full encrypted-PII column already decrypted, instead of a projection that strips or truncates it.
- A `SELECT *` against a table with `ssn`, `bank_account`, `bank_account_number`, `routing_number`, `tax_id`, or `gov_id` columns flows directly into a JSON response without a field-level allowlist in the serializer.
- Admin or agent-facing tools (not the customer self-service path) receive cleartext PII. The only path where last-4 is allowed is the customer-self-service confirmation screen, computed at projection time, never the full value.
- A migration adds an encrypted column but a corresponding view or RPC exposes the decrypted form to a role that should not see it.

## Why it matters

- Regulatory violation: PCI DSS (bank account / card data), HIPAA-adjacent state insurance privacy laws, and state-level data-protection statutes (NY DFS Part 500, CA CPRA) treat cleartext exposure of this PII class as a reportable incident.
- Audit failure: external auditors fail the control "PII never leaves the server boundary in cleartext outside the customer-self-service projection".
- Civil liability: contractual indemnity clauses with insurance carriers and banking partners typically place the operator on the hook for breach notification cost and downstream fraud.
- The boundary contract is absolute: the data MUST NEVER cross the server boundary in cleartext outside the customer-self-service path, and even there only as a last-4 projection used for confirmation. There is no "internal tool exception".
- Reversibility is false in practice: once a cleartext value reaches a client, log aggregator, browser cache, or screenshot, it must be treated as compromised. Rotation of the underlying identifier (SSN, bank account) is expensive or impossible.

## How to detect

Static / grep:

```
# Flag SELECT statements that pull the raw encrypted-PII columns
rg -n "SELECT[^;]*\b(ssn|bank_account|bank_account_number|routing_number|tax_id|gov_id)\b" \
  apps/web/src supabase/migrations packages

# Flag response schemas / serializers that expose the full field
rg -n "\b(ssn|bank_account|routing_number)\b\s*[:=]" \
  apps/web/src/server/api packages/**/serializers
```

Runtime:

- Add a response-shape assertion in API tests: response body MUST NOT match `\b\d{9}\b` (full SSN) or `\b\d{8,17}\b` co-located with a `bank_account` key.
- Log-side canary: a sampling middleware scans outbound JSON for the regex patterns above and pages on hit (treat the page itself as confidential -- do not include the matched value).
- Code review checklist: every new endpoint touching a customer record must explicitly declare which PII fields it returns, and the default is "none / last-4 only".

## How to fix

1. Column-level encryption at rest: use `pgcrypto` (`pgp_sym_encrypt` / `pgp_sym_decrypt`) or app-level envelope encryption with KMS. The decrypt function must NOT be callable by the API role; it is callable only by a narrow service role used in the customer-self-service projection path.
2. Field-level allowlist in the serializer: every response DTO declares its fields explicitly. No `SELECT *` to JSON. No spread of the row object into the response.
3. Last-4 projection computed at the projection layer: `last4 = right(decrypt(ssn_enc), 4)`. The full decrypted value MUST NOT be bound to a variable that outlives the projection function scope.
4. Database-level defense in depth: a Postgres RLS policy or a dedicated view (`customers_safe`) that hides the encrypted columns from the API role entirely, so even an accidental `SELECT *` cannot return them.
5. Add a regression test per endpoint asserting the response does not contain the full-value regex patterns.
6. If a leak has already shipped: rotate the affected identifiers where possible, file the breach notification per jurisdiction, and add the endpoint to a post-mortem tracking the cleartext exposure window.

## CWE / standard refs

- CWE-312: Cleartext Storage of Sensitive Information. The "storage" here includes any transient surface the cleartext reaches (response payload, client cache, log line, screenshot) once it crosses the server boundary.
- PCI DSS 3.x (bank account / PAN data handling).
- NY DFS 23 NYCRR Part 500 (nonpublic information protections).

## See also

- `wos/bug-classes/pii-last-4-only-rule-violation.md` (sibling class -- the contractual rule that this leak violates)
- `wos/bug-classes/hardcoded-secret-in-code.md` (sibling class -- same severity tier, different vector)
- `wos/bug-classes/input-not-validated-at-boundary.md` (the inbound counterpart to this outbound leak)

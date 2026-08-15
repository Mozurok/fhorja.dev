---
name: pii-last-4-only-rule-violation
category: security
default-severity: P0
cwe: [CWE-200]
languages: [typescript, python, ruby, java, sql]
file-patterns: ["**/serializers/**", "**/api/**", "apps/**/src/server/**", "apps/**/src/components/**confirmation**", "apps/**/src/components/**review**", "**/routes/**confirm**"]
perspectives: [operator, maintainer, security-reviewer]
reversibility-check: true
---

# pii-last-4-only-rule-violation

## Trigger

A confirmation screen, API response, log line, or webhook payload exposes more than the last 4 digits of a sensitive identifier (government identifier, bank account, routing and account combination, card number, tax id) where an explicit business rule mandates last-4-only display. The value looks partially masked, but the rendered or serialized string carries 5 or more digits, which regulators and audit reviewers treat as equivalent to a full leak.

This class is usually a regression rather than a greenfield defect, which is what makes it easy to miss: the diff looks like a small tweak to a field that was already masked.

CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor). Confirmation screens, API responses, and logs are unauthorized-actor surfaces relative to the last-4-only contract; any digit beyond the fourth is unauthorized exposure.

## Detection

Response-shape checks:

- For any field whose name matches `(ssn|tin|ein|account|routing|card|pan|iban|govt|tax_id)` and ends in `_last4`, `_masked`, or similar: assert the digit count in the serialized value is exactly 4.
- For confirmation-screen integration tests, snapshot the rendered text and regex-match `\*{2,}\d{4}(?!\d)`, which requires exactly 4 trailing digits with no fifth.

Static and lint heuristics:

- The serializer base class exposes a `last4(value)` helper; a lint rule flags any sensitive field that does not call it.
- Grep for direct field assignment that bypasses the mask helper:

```
rg -n "(ssn|account_number|routing_number|tax_id)" --type ts --type py \
  -g '!**/test/**' \
  | rg -v "last4\\(|mask\\(|redact\\("
```

Runtime and log scan:

- Log aggregator alert on any line matching `\b\d{5,}\b` within a field tagged sensitive.
- Webhook replay test: send a real payload through the production serializer pipeline and assert the outbound JSON contains no run of more than 4 digits inside sensitive fields.

Shapes to look for by reading:

- A quote, checkout, or account confirmation screen rendering `***-**-12345` (5 digits) instead of `***-**-1234`.
- An API response field such as `account_last4: "12345"` or `ssn_masked: "***-**-12345"` carrying more digits than the rule allows.
- A serializer field switched to show the full value for debugging and never reverted, so production responses ship the cleartext identifier.
- A new field added (for example `routing_number`) where the author masked only `account_number`, leaving the sibling unmasked on the same payload.
- Logs, error reports, or analytics events including the full identifier while the UI is correctly masked. The violation lives in the side channel.
- A serializer base class that exists while a new endpoint bypasses it and hand-builds the response object.

UI verification:

- Manual walk-through of every confirmation, review, and receipt screen after any change to a serializer, a form, or a PII-adjacent field. Confirm the visible digit count is exactly 4.

## Retrieval

- The serializer base class and the `last4` or mask helper it exposes, to establish whether a single enforcement point exists at all.
- Every serializer or response builder in the diff that touches a field matching the sensitive-name pattern, including any that hand-build a response object instead of routing through the base class.
- The confirmation, review, and receipt components in scope (`apps/**/src/components/**confirmation**`, `**review**`, `**/routes/**confirm**`), because the rendered string is the surface the rule is written about.
- The side channels for the same fields: log statements, error reporters, analytics events, and webhook payload builders. A UI-only fix leaves these leaking.
- The written rule itself when it exists in the repo (a contract doc, a policy file, or a decision record), so the required digit count is read rather than assumed.

## Analysis prompt

Given the retrieved serializers, components, and side-channel emitters:

1. For every sensitive field in the diff, count the digits that actually reach the surface. Four is the contract. Five is a violation of the same severity class as emitting the full value, not a smaller version of it.
2. Does the value route through a single masking helper, or is the masking hand-rolled at this call site? A hand-rolled mask is a finding even when its current output is correct, because the rule is then re-implemented per endpoint and drifts one endpoint at a time.
3. Where is the truncation performed: server-side before serialization, or client-side at render? A client-side truncation means the full value already crossed the boundary and is present in the network response, the browser cache, and any client log.
4. Check the sibling fields on the same payload. This class recurs when a new identifier field is added next to an already-masked one and inherits none of its handling. Enumerate every sensitive field on the payload, not only the one the diff touched.
5. Check the side channels for the same fields: log lines, error payloads, analytics events, webhook bodies. A fix that patches only the rendering component leaves the backend emitting the full value, and side-channel exposure outlives UI fixes.
6. Look specifically for a debugging toggle that shows the full value. If one exists in the diff or in the file, it is a finding regardless of its current default, because nothing prevents it shipping enabled.
7. Recommend fixes in this order: one shared `last4(value)` helper that returns a mask plus the final 4 characters and rejects inputs shorter than 4 digits; enforcement of that helper inside the serializer base class with per-endpoint hand-rolled masking removed; an integration test per confirmation screen asserting exactly 4 trailing digits in the rendered output; a schema-level response-shape contract test per endpoint asserting the digit count; the same helper or outright redaction applied to logs, error reporters, and webhook payloads; and a CI regression test so a future show-full-for-debugging toggle cannot ship.
8. This class carries `reversibility-check: true`. A confirmation screen is a high-trust surface: users assume the value was already masked, so they screenshot, email, and forward it, and a 5-digit mask propagates faster than raw cleartext would. If the violation already reached production, the recommendation is incident handling (rotate the exposed identifiers where possible, notify per regulatory obligation, record the exposure window), not a quiet patch.

## Severity rubric

- **P0**: a surface reachable by a user or an external system emits more than 4 digits of a sensitive identifier, on any channel including logs and webhooks. Justification for the ceiling: last-4-only is normally an explicit written rule tied to a regulatory or partner contract, so violating it carries the same audit and regulatory exposure as a full leak, and the high-trust nature of confirmation surfaces means the over-exposed value spreads further than raw cleartext.
- **P1**: every current surface emits exactly 4 digits, but the masking is hand-rolled per call site with no shared helper and no schema-level test, so the rule holds by convention and the next added field will not inherit it.
- **P2**: the UI and API are correct while a side channel (an analytics event, a debug log behind a disabled flag) carries the full value, currently unreachable but one flag flip away.

## Confidence factors

- **HIGH**: a serialized value or rendered string in the diff contains 5 or more digits in a field matching the sensitive-name pattern; or a sensitive field is assigned directly with no call to the mask helper and the grep exclusion for `last4(`, `mask(`, `redact(` returns nothing on that line.
- **MEDIUM**: the field routes through a helper whose digit count cannot be confirmed from the retrieved files, so the emitted length is unresolved. Reading the helper settles it.
- **LOW**: the match is in a test fixture, a seed, or the mask helper's own implementation, where a longer digit run is the input rather than the output.

## Examples

### Positive (five digits reach the surface)

```typescript
// serializers/account.ts
export function serializeAccount(row: AccountRow) {
  return {
    id: row.id,
    // off-by-one: five digits, which is a rule violation, not a smaller mask
    account_last4: row.account_number.slice(-5),
    // sibling field added later, inherited none of the masking
    routing_number: row.routing_number,
  };
}
```

### Negative (one helper, enforced at the base, tested at the schema)

```typescript
// serializers/base.ts
export function last4(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 4) throw new Error("last4: value shorter than 4 digits");
  return `****${digits.slice(-4)}`;
}

// serializers/account.ts
export function serializeAccount(row: AccountRow) {
  return {
    id: row.id,
    account_last4: last4(row.account_number),
    routing_last4: last4(row.routing_number), // every sensitive sibling routes through the same helper
  };
}
```

```typescript
// api/__tests__/account.contract.test.ts
it("emits exactly four digits for every sensitive field", async () => {
  const body = await getAccount(id);
  for (const field of ["account_last4", "routing_last4"]) {
    expect(body[field].replace(/\D/g, "")).toHaveLength(4);
  }
});
```

---
name: pii-last-4-only-rule-violation
category: security
default-severity: P0
priority: P0
pillars: [security, data-integrity]
cwe: [CWE-200]
languages: [typescript, python, ruby, java, sql]
file-patterns: ["**/serializers/**", "**/api/**", "apps/**/src/server/**", "apps/**/src/components/**confirmation**", "apps/**/src/components/**review**", "**/routes/**confirm**"]
perspectives: [operator, maintainer, security-reviewer]
reversibility-check: true
---

# pii-last-4-only-rule-violation

A confirmation screen, API response, log line, or webhook payload exposes more than the last 4 digits of a sensitive identifier (SSN, bank account, routing+account combo, card PAN, government ID) when an explicit business rule mandates last-4-only display. Even though the data is "partially masked" in intent, the actual rendered or serialized value carries 5+ digits, which is treated by regulators and audit reviewers as equivalent to a full PII leak.

## What it looks like

- A quote/checkout/account confirmation screen renders `***-**-12345` (5 digits) instead of `***-**-1234` (4 digits).
- An API response field like `account_last4: "12345"` or `ssn_masked: "***-**-12345"` contains more digits than the rule allows.
- A serializer field that was temporarily switched to "show full for debugging" was never reverted, so production responses now ship the cleartext identifier.
- A new field is added (e.g. `routing_number`) and the developer masked only `account_number`, leaving the sibling field unmasked on the same payload.
- Logs, error reports, or analytics events include the full identifier even when the UI is correctly masked -- the rule violation lives in the side channel.
- A serializer base class exists but a new endpoint bypasses it and hand-builds the response dict.

## Why it matters

- Last-4-only is usually an explicit, written business rule tied to a regulatory or partner contract (e.g. Right Quote: "customer sees only the last 4 on confirmation"). Violation is not a UX nit -- it is the same audit and regulatory exposure as a full leak.
- Confirmation screens are high-trust surfaces: users assume the displayed value has already been masked correctly, so they will screenshot, email, or share it. A 5-digit "mask" propagates faster than raw cleartext would.
- Side-channel leaks (logs, error traces, webhooks) survive UI fixes and create long-tail liability: a fix that only patches the React component does not stop the backend log line.
- This class is typically a regression, not a greenfield bug. That makes it easy to miss in review because the diff looks like a small "tweak" to an already-masked field.

## How to detect

Response-shape checks:

- For any field whose name matches `(ssn|tin|ein|account|routing|card|pan|iban|govt|tax_id)` and ends in `_last4`, `_masked`, or similar: assert the digit count in the serialized value is exactly 4.
- For confirmation-screen integration tests, snapshot the rendered text and regex-match `\*{2,}\d{4}(?!\d)` (exactly 4 trailing digits, no 5th digit).

Static / lint:

- Serializer base class must expose a `last4(value)` helper; lint rule flags any sensitive field that does not call it.
- Grep heuristic for direct field assignment without mask helper:

```
rg -n "(ssn|account_number|routing_number|tax_id)" --type ts --type py \
  -g '!**/test/**' \
  | rg -v "last4\\(|mask\\(|redact\\("
```

Runtime / log scan:

- Log aggregator alert on any line matching `\b\d{5,}\b` within a field tagged as sensitive.
- Webhook replay test: send a real payload through the production serializer pipeline and assert the outbound JSON contains no >4-digit run inside sensitive fields.

UI verification:

- Manual walk-through of every confirmation, review, and receipt screen after any change to a serializer, form, or PII-adjacent field. Confirm visible digit count is exactly 4.

## How to fix

1. Add or reuse a single `last4(value)` helper that returns `"****" + value.slice(-4)` (or locale-appropriate mask) and rejects inputs shorter than 4 digits.
2. Enforce the helper inside a shared serializer base class so every sensitive field routes through it; remove any per-endpoint hand-rolled masking.
3. Add an integration test per confirmation screen that asserts the rendered DOM contains exactly 4 trailing digits for each sensitive field.
4. Add a response-shape contract test (schema-level) for every API endpoint that returns a sensitive field: digit count == 4.
5. Audit logs, error reporters, and webhook payloads for the same fields; route them through the same helper or redact entirely.
6. If the violation already shipped to production, treat as a security incident: rotate any exposed identifiers where possible, notify per regulatory obligation, and record the incident in the audit log.
7. Add a regression test that re-asserts the rule for every sensitive field; wire it into CI so a future "show full for debugging" toggle cannot ship.

## CWE / standard refs

- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor. Confirmation screens, API responses, and logs are unauthorized-actor surfaces relative to the last-4-only contract; any digit beyond the 4th is unauthorized exposure.

## See also

- `wos/bug-classes/pii-encryption-boundary-leak.md` (sibling class: PII crossing an encryption boundary unmasked)
- `wos/bug-classes/input-not-validated-at-boundary.md` (sibling class: missing boundary validation that often co-occurs with output-side leaks)

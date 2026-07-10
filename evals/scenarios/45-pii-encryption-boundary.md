# Eval scenario 45: PII encryption boundary -- last-4-only rule on customer endpoints

- **Tags**: security-review, bug-class, pii-encryption-boundary-leak, pii-last-4-only-rule-violation, api-contract, regression-guard
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validate that the `security-review` command, in combination with the `pii-encryption-boundary-leak` and `pii-last-4-only-rule-violation` bug-classes, correctly flags a P0 regression when a Right-Quote-style customer API returns a full bank account number in plaintext, and correctly passes when the same surface returns a masked last-4 representation. The bug-class pair encodes the canonical rule: any PII bank field crossing the API boundary must be masked to the last 4 digits unless the caller is explicitly inside the encryption zone.

This exercises:

- The `security-review` command's ability to recognize PII-bearing response fields by name (`bank_account`, `ssn`, `routing_number`, etc.) and to apply the encryption-boundary rule to them.
- The `pii-encryption-boundary-leak` bug-class as a P0 severity gate (not P1, not advisory).
- The `pii-last-4-only-rule-violation` bug-class as the masking-format rule that must accept `****1234` style output and reject full digits.
- Disjointness of the two bug-classes: a fully leaked value triggers the boundary leak rule; a partially masked but wrong-format value would trigger the last-4 rule. They should not double-fire on the same finding.

## Setup

A Right-Quote-style repo with two endpoints under review:

- `GET /api/customers/<id>` -- regression case. Response body includes `"bank_account": "4532018273645091"` (full 16-digit account number) inside the customer object.
- `GET /api/customers/<id>/confirmation` -- compliant case. Response body includes `"bank_account": "****1234"` only.

No encryption-zone marker is present on either route handler. Both routes are reachable by an authenticated customer-scope token. The diff under review introduces the `/api/customers/<id>` change; the `/confirmation` route is unchanged baseline.

## Input prompt

```text
Run @commands/security-review.md

Surface under review:
  - GET /api/customers/<id>
  - GET /api/customers/<id>/confirmation

Focus: PII boundary on bank fields. Apply wos/bug-classes/pii-encryption-boundary-leak.md
and wos/bug-classes/pii-last-4-only-rule-violation.md.

Mode: Ask
```

## Expected response shape

- `security-review` enumerates the two endpoints and inspects the response shape of each.
- For `/api/customers/<id>`, the review flags a **P0** finding citing `pii-encryption-boundary-leak` by name, names the offending field (`bank_account`), and quotes the leaked value pattern (16 plaintext digits).
- For `/api/customers/<id>/confirmation`, the review records a **PASS** and explicitly states that `****1234` satisfies the last-4-only rule.
- The final summary lists exactly one P0 finding, zero P1 findings on the masked endpoint, and references both bug-class files by path.
- No double-counting: the masked endpoint does not also trigger `pii-last-4-only-rule-violation`.

## Pass criteria

1. **P0 severity assigned**: The `/api/customers/<id>` finding is marked P0, not P1 or advisory.
2. **Bug-class cited by name**: The P0 finding references `wos/bug-classes/pii-encryption-boundary-leak.md` by path or identifier.
3. **Field named explicitly**: The finding names `bank_account` as the offending field, not a vague "PII leak in response".
4. **Masked endpoint passes**: `/api/customers/<id>/confirmation` is reported as PASS with `****1234` quoted as the compliant value.
5. **Last-4 rule cited on pass**: The pass line references `wos/bug-classes/pii-last-4-only-rule-violation.md` as the satisfied rule, proving the reviewer checked the format, not just the field presence.
6. **No false positive on masked route**: The confirmation endpoint does NOT also receive a `pii-encryption-boundary-leak` finding -- masked output is treated as inside-boundary, not outside.
7. **Remediation proposed**: The P0 finding includes a concrete fix (mask to last 4, or move the route inside the encryption zone with an explicit marker), not just a flag.

## Failure modes to watch

- **Severity drift**: The leak is flagged but as P1 or advisory, allowing the regression to ship. P0 is non-negotiable for plaintext PII at the API boundary.
- **Vague finding**: The review says "potential PII concern in customer endpoint" without naming `bank_account` or quoting the offending value, making the fix unactionable.
- **False positive on masked route**: The reviewer flags `****1234` as a leak because it sees the `bank_account` key, not the value -- this means the reviewer is doing key-name matching instead of value-format checking.
- **Bug-class not cited**: The P0 fires but the response does not reference `pii-encryption-boundary-leak.md`, so the rule chain is invisible to auditors and the canonical bug-class catalog is bypassed.

## Notes

- Right-Quote-style here means a customer-facing financial app where bank account display is a legitimate UI need but full digits must never leave the encryption zone. This is the canonical motivating case for the encryption-boundary rule.
- The two bug-classes are complementary, not redundant: `pii-encryption-boundary-leak` answers "should this value cross the boundary at all?" and `pii-last-4-only-rule-violation` answers "given that it crosses, is the format compliant?". A reviewer that conflates them will mis-route findings.
- This scenario does not test write paths (POST/PUT). Encryption-boundary on inbound PII is a separate scenario.

## History

- 2026-06-05: Scenario authored to cover the PII boundary bug-class pair after the Right-Quote regression motivated adding them to the global catalog.

## References

- `internal/wos/bug-classes/pii-encryption-boundary-leak.md` (P0 boundary rule under test)
- `internal/wos/bug-classes/pii-last-4-only-rule-violation.md` (masking-format rule under test)
- `internal/commands/security-review.md` (command under test)

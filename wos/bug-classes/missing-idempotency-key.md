---
name: missing-idempotency-key
category: data-integrity
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "handlers/**", "api/**", "routes/**", "consumers/**"]
perspectives: [operator, api-consumer]
reversibility-check: false
---

# missing-idempotency-key

## Trigger

A mutation endpoint (POST that creates a resource, triggers a side effect, or processes a payment) can be called multiple times with the same input and produce duplicate results each time. Without an idempotency mechanism, network retries, user double-clicks, or webhook redeliveries create duplicate records, double charges, or repeated notifications.

## Detection

Look for POST/PUT endpoints where:
- An INSERT or create operation executes without checking for prior execution of the same request
- No idempotency key is accepted via header (`Idempotency-Key`, `X-Request-Id`) or body field
- No `ON CONFLICT DO NOTHING` or `INSERT ... ON CONFLICT DO UPDATE` is used
- No deduplication check (e.g., lookup by unique combination of fields before insert)

Focus on endpoints that have side effects beyond the database (email, SMS, payment, webhook).

## Retrieval

- The handler function body
- The INSERT/create query
- The route definition (to see if idempotency middleware exists)

## Analysis prompt

Given the mutation endpoint:
1. What happens if this exact request is sent twice? (duplicate record, duplicate email, double charge?)
2. Is there a natural idempotency key? (e.g., `(company_id, load_id)` for a shipment; `(run_id, recipient_email)` for a share)
3. Is there a deduplication mechanism? (unique constraint, ON CONFLICT, lookup-before-insert)
4. Does the endpoint trigger side effects that would also be duplicated? (email, webhook, payment)
5. Recommended fix: accept an `Idempotency-Key` header or use a natural key with `ON CONFLICT`.

## Severity rubric

- P0: mutation triggers a financial transaction (payment, credit) without idempotency
- P1: mutation creates a resource + sends a notification without deduplication
- P2: mutation creates a resource with no side effects; duplicate is recoverable

## Confidence factors

- HIGH: POST endpoint with INSERT and email/webhook dispatch; no unique constraint or ON CONFLICT; no idempotency header
- MEDIUM: POST with INSERT that has a unique constraint (natural dedup) but no explicit idempotency key
- LOW: POST is internally idempotent by design (upsert, set-operation)

## Examples

### Positive (not idempotent)

```typescript
router.post("/:id/share", async (req, res) => {
  await db.insert({ run_id, recipient_email, token });
  await sendEmail(recipient_email, shareUrl);
  // If request retried: duplicate share + duplicate email
});
```

### Negative (idempotent)

```typescript
router.post("/:id/share", async (req, res) => {
  const { data } = await db.insert({ run_id, recipient_email, token })
    .onConflict(["run_id", "recipient_email"]).doNothing();
  if (!data) return res.json(existingShare); // already created
  await sendEmail(recipient_email, shareUrl);
});
```

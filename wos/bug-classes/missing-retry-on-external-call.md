---
name: missing-retry-on-external-call
category: resilience
default-severity: P1
cwe: [CWE-755]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "consumers/**", "lib/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# missing-retry-on-external-call

## Trigger

A call to an external service (third-party API, email provider, SMS gateway, payment processor, S3, webhook endpoint) is made without retry logic. A single transient failure (network blip, 502, rate limit, timeout) causes the entire operation to fail permanently, even though retrying after a short delay would likely succeed.

## Detection

Look for `await fetch(`, `await axios.`, `await client.send(`, `await resend.`, or equivalent HTTP/SDK calls where:
- The URL or client points to an external domain (not localhost, not the same service)
- There is no retry wrapper, no exponential backoff, no retry library (e.g., `p-retry`, `axios-retry`, `tenacity`)
- The catch block logs and re-throws (or does not catch at all) without retrying

## Retrieval

- The function body containing the external call
- The error handling path (catch block, if any)
- Sibling functions that call other external services (to check if they retry)

## Analysis prompt

Given the external call:
1. What external service is being called? What is its typical reliability? (email APIs: ~99.9%; webhooks: variable)
2. Is the call idempotent (safe to retry without side effects)?
3. If yes: what retry strategy is appropriate? (Recommendation: 3 retries with exponential backoff starting at 1s)
4. If not idempotent: is there an idempotency key mechanism available?
5. What happens to the user if this call fails permanently? (email not sent, webhook not delivered, payment not processed)

## Severity rubric

- P0: external call on a critical path (payment, auth token exchange) with no retry and no fallback
- P1: external call on a non-critical but user-visible path (email, SMS, webhook) with no retry
- P2: external call on a background job that will be retried at the job level anyway

## Confidence factors

- HIGH: `await fetch("https://api.external.com/...")` with no retry wrapper; catch block re-throws
- MEDIUM: external SDK call (e.g., `resend.emails.send(...)`) without retry; SDK may have internal retry
- LOW: call is inside a queue consumer that already retries on failure (retry at the job level)

## Examples

### Positive (no retry)

```typescript
const response = await fetch("https://api.twilio.com/send-sms", { method: "POST", body });
if (!response.ok) throw new Error("SMS send failed");
// A single 502 from Twilio kills the operation permanently
```

### Negative (with retry)

```typescript
const response = await pRetry(
  () => fetch("https://api.twilio.com/send-sms", { method: "POST", body }),
  { retries: 3, minTimeout: 1000, factor: 2 }
);
```

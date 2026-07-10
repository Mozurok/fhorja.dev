---
name: error-message-low-quality
category: observability
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**", "middleware/**"]
perspectives: [operator]
reversibility-check: false
---

# error-message-low-quality

## Trigger

An error response or thrown error uses a vague, generic, or uninformative message that would make debugging difficult for on-call engineers or API consumers. Messages like "Something went wrong", "Internal server error", "An error occurred", or "Failed" without context do not help identify the root cause.

## Detection

Look for error construction where:
- The message is a short generic string without any contextual variable (entity ID, operation name, relevant field)
- The message duplicates the HTTP status semantics without adding information (e.g., `throw new Error("Bad request")` on a 400 response)
- A catch block swallows the original error and re-throws with a less informative message

Grep patterns:
- `"Something went wrong"` or `"An error occurred"` or `"Internal error"`
- `throw new Error("Failed")` or `throw HttpError.internal("Error")`
- `catch (err) { throw new Error("` (re-throw that may lose original context)

## Retrieval

- The function body containing the error
- The error class definition (to see if it supports structured fields like `code`, `cause`, `context`)

## Analysis prompt

Given the error message:
1. If an on-call engineer sees this in a log at 3 AM, can they identify: WHAT failed, WHERE it failed (which operation/entity), and WHY (what condition triggered it)?
2. Does the error preserve the original cause (stack trace, DB error code, upstream error)?
3. Is there a risk of leaking sensitive information in the error message to external callers? (Internal errors should be detailed in logs but generic in API responses.)
4. Suggested improvement: add entity ID, operation name, or relevant field to the message.

## Severity rubric

- P0: never (error message quality is not a correctness bug)
- P1: error on a critical path (auth, payment, data mutation) with a message that provides zero diagnostic context
- P2: error on a non-critical path or the message is slightly vague but contains some context

## Confidence factors

- HIGH: message is a literal string with no interpolated variables; the error is on a critical code path (write operation, auth check)
- MEDIUM: message has some context but is missing key identifiers (entity ID, operation name)
- LOW: message is in a catch-all handler where generic messaging is intentional (to avoid leaking internals)

## Examples

### Positive (low quality)

```typescript
if (!claim) {
  throw HttpError.internal("Failed to create share");
}
// "Failed to create share" at 3 AM: which run? which user? which email? No context.
```

### Negative (good quality)

```typescript
if (!claim) {
  throw HttpError.internal(
    `Failed to create share for run ${runId}, recipient ${recipientEmail}`
  );
}
// On-call can immediately identify the affected run and recipient
```

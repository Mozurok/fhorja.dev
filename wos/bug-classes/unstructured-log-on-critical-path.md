---
name: unstructured-log-on-critical-path
category: observability
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "consumers/**", "handlers/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# unstructured-log-on-critical-path

## Trigger

A log call on a critical code path uses string concatenation or template literals instead of structured fields. Unstructured logs are hard to query in log aggregators (Datadog, CloudWatch, Loki), making production debugging slower and alert rules fragile.

## Detection

Look for:
- `logger.info("User " + userId + " created share")` (string concat)
- `` logger.error(`Failed for ${runId}`) `` (template literal without structured fields)
- `console.log(...)` on a non-dev code path

Prefer: `logger.info("Share created", { userId, runId, recipientEmail })`

## Retrieval

- The function body containing the log call
- Sibling functions (to check if they use structured logging)

## Analysis prompt

Given the log call:
1. Is it using string concatenation/template literals or structured fields (object as second argument)?
2. Does it include enough context fields for production debugging (entity ID, user/tenant ID, operation name)?
3. If unstructured: recommend converting to structured format with the key contextual fields.

## Severity rubric

- P1: unstructured log on an error path of a critical operation (auth, payment, data mutation)
- P2: unstructured log on a non-critical path or info-level log

## Confidence factors

- HIGH: string concat in `logger.error` or `logger.warn` on a write path; sibling functions use structured logs
- MEDIUM: template literal in `logger.info`; may be acceptable for simple messages
- LOW: `console.log` in a dev-only context or script

## Examples

### Positive (unstructured)

```typescript
logger.warn("Failed to revoke prior shares for run " + run.id);
```

### Negative (structured)

```typescript
logger.warn("Failed to revoke prior shares", { runId: run.id, recipientEmail, error: err.message });
```

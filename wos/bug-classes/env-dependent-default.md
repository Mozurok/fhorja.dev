---
name: env-dependent-default
category: config-bug
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go"]
perspectives: [operator]
reversibility-check: false
---

# env-dependent-default

## Trigger

A constant or variable provides a hardcoded fallback value (typically `localhost`, `127.0.0.1`, or a dev-only URL) that is intended for local development but will silently activate in non-local environments (staging, preview, CI) where the expected environment variable is unset. The fallback produces non-functional behavior (broken URLs in emails, wrong API endpoints, silent data loss) without any warning or error.

## Detection

Look for patterns where:
- A constant is defined with a localhost or dev-only default: `const X = process.env.Y ?? "http://localhost:..."` or `os.getenv("Y", "http://localhost:...")`
- The constant is used in a context that reaches external users or systems (email bodies, API responses, webhook URLs, redirect targets)
- The startup guard (if any) only validates the env var in `NODE_ENV=production`, leaving staging/preview/CI unguarded

Grep patterns:
- `?? "http://localhost` or `?? 'http://localhost`
- `|| "http://localhost` or `|| 'http://localhost`
- `getenv(.*localhost` or `os.environ.get(.*localhost`
- `DEFAULT_.*HOST.*=.*localhost`

## Retrieval

- The file where the constant is defined
- The startup/bootstrap file (e.g., `index.ts`, `app.py`, `main.go`) to check if a startup guard validates the env var
- Up to 2 files that consume the constant (to verify the constant reaches external-facing output)

## Analysis prompt

Given the constant definition and its consumers:
1. In which environments does the fallback actually fire? (local dev, staging, preview, CI, production)
2. What is the user-visible or system-visible consequence when the fallback fires in a non-local environment? (broken link in email, wrong redirect, silent data loss, etc.)
3. Is there a startup guard that validates the env var? Does the guard fire in all non-local environments, or only in production?
4. Recommendation: should the fallback be removed entirely (fail-fast if unset) or should the guard be extended to cover all environments where the feature is active?

## Severity rubric

- P0: fallback produces a security issue (e.g., token embedded in HTTP URL sent to external recipient; HTTPS enforcement bypassed)
- P1: fallback produces a broken user experience in a non-local environment (e.g., non-functional link in an email, wrong API endpoint in a webhook)
- P2: fallback produces a degraded but functional experience (e.g., log messages with wrong hostname, internal metrics tagged incorrectly)

## Confidence factors

- HIGH: constant is consumed in external-facing output (email body, API response, redirect URL) AND the startup guard is production-only or absent
- MEDIUM: constant is consumed in internal systems (metrics, logs, internal webhooks) and fallback is visible but not user-facing
- LOW: constant exists but usage is unclear; may be dead code or only used in tests

## Examples

### Positive (real bug)

```typescript
const DEFAULT_HOST = "http://localhost:8000";
// ...
const shareUrl = `${process.env.PUBLIC_HOST ?? DEFAULT_HOST}/share/${token}`;
// If PUBLIC_HOST is unset in staging, shareUrl becomes http://localhost:8000/share/abc
// which is embedded in the outbound email body and completely non-functional for the recipient
```

### Negative (safe pattern)

```typescript
// No fallback; startup guard requires PUBLIC_HOST whenever the feature is active
if (process.env.SHARE_TOKEN_SECRET && !process.env.PUBLIC_HOST) {
  throw new Error("PUBLIC_HOST must be set when SHARE_TOKEN_SECRET is configured");
}
// In the handler, PUBLIC_HOST is guaranteed to be present
const shareUrl = `${process.env.PUBLIC_HOST}/share/${token}`;
```

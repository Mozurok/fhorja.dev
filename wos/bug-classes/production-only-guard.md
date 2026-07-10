---
name: production-only-guard
category: config-bug
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go"]
perspectives: [operator]
reversibility-check: false
---

# production-only-guard

## Trigger

A startup validation or runtime guard checks for a required condition only when `NODE_ENV === "production"` (or equivalent), leaving staging, preview, and CI environments unprotected. The missing guard allows the service to start and operate with a misconfiguration that would cause real harm in those environments.

## Detection

Look for patterns where:
- `process.env.NODE_ENV === "production"` (or `os.environ["ENV"] == "production"`) gates a guard
- The guarded condition (env var presence, HTTPS requirement, secret validation) is also relevant outside production
- Staging or preview environments run the same code and could hit the same issue

Grep patterns:
- `NODE_ENV.*===.*"production"` or `NODE_ENV.*===.*'production'`
- `ENV.*==.*"production"` or `ENVIRONMENT.*==.*prod`

## Retrieval

- The file containing the guard (typically entrypoint: `index.ts`, `app.py`, `main.go`)
- The feature or config variable being guarded (to verify if it matters outside prod)

## Analysis prompt

Given the guard:
1. Is the guarded condition also dangerous in staging or preview? (e.g., missing HTTPS, missing secret, wrong URL)
2. Would the feature silently malfunction in non-prod environments if the guard does not fire?
3. Should the guard be extended to fire whenever the feature is active (e.g., when its primary secret is set), regardless of NODE_ENV?

## Severity rubric

- P0: unguarded condition causes a security vulnerability in staging (e.g., secret sent over HTTP)
- P1: unguarded condition causes broken functionality for real users or external recipients in staging
- P2: unguarded condition causes internal inconvenience (wrong metrics, misleading logs) but no user impact

## Confidence factors

- HIGH: the guarded env var is consumed in external-facing output (emails, webhooks, redirects) and staging sends real traffic
- MEDIUM: the guarded env var is consumed internally but staging is isolated
- LOW: the guard exists but the feature it protects may not run in non-prod environments

## Examples

### Positive (real bug)

```typescript
if (process.env.NODE_ENV === "production") {
  if (!process.env.PUBLIC_HOST) throw new Error("PUBLIC_HOST required");
}
// In staging: PUBLIC_HOST is unset, guard does not fire, emails contain localhost URLs
```

### Negative (safe pattern)

```typescript
if (process.env.SHARE_TOKEN_SECRET) {
  if (!process.env.PUBLIC_HOST) {
    throw new Error("PUBLIC_HOST must be set when SHARE_TOKEN_SECRET is configured");
  }
}
// Guard fires in any env where the feature is active, not just production
```

---
name: hardcoded-secret-in-code
category: security
default-severity: P0
cwe: [CWE-798, CWE-259]
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go", "**/*.env*", "**/*.yml", "**/*.yaml"]
perspectives: [security]
reversibility-check: false
---

# hardcoded-secret-in-code

## Trigger

A secret value (API key, password, token, private key, connection string with credentials) appears as a literal string in source code, configuration files tracked by git, or test fixtures that could leak to logs or version history.

## Detection

Look for patterns where:
- String literals match common secret formats: `sk_live_`, `sk_test_`, `AKIA`, `ghp_`, `Bearer ey`, base64-encoded JWT, `-----BEGIN RSA PRIVATE KEY-----`
- Variable names suggest secrets: `password`, `secret`, `api_key`, `apiKey`, `token`, `private_key`, `connection_string`, `DATABASE_URL`
- `.env` files or `docker-compose.yml` with real values are tracked by git (not in `.gitignore`)
- Test files contain real credentials (even "test" credentials that work in staging)

Exclude:
- References to environment variable names (`process.env.API_KEY` is safe; `const API_KEY = "sk_live_abc"` is not)
- Placeholder values clearly marked as examples: `<your-api-key-here>`, `REPLACE_ME`, `TODO`
- Hash constants (SHA256 of known values, bcrypt hashes of test passwords)

## Retrieval

- The file containing the suspected secret
- `.gitignore` (to verify if the file is tracked)

## Analysis prompt

Given the suspected secret:
1. Is this a real credential or a placeholder/example?
2. Is the file tracked by git (not in `.gitignore`)?
3. If committed: has this file been in git history? (Even if removed now, the secret is in history.)
4. Recommended fix: move to environment variable, secrets manager, or vault. If already in git history, rotate the credential immediately.

## Severity rubric

- P0: real credential (API key, password, token) in a tracked file (always P0; credential must be rotated)
- P1: credential-like string in test fixtures that could work in staging/dev environments
- P2: placeholder or example value that looks like a credential but is clearly fake

## Confidence factors

- HIGH: string matches a known secret prefix (`sk_live_`, `AKIA`, `ghp_`) AND file is not in `.gitignore`
- MEDIUM: variable named `password` or `secret` with a non-placeholder string value
- LOW: string looks like it could be a secret but context is unclear (may be a hash or test fixture)

## Examples

### Positive (hardcoded secret)

```typescript
const RESEND_API_KEY = "re_abc123_real_key_here";
```

### Negative (safe)

```typescript
const RESEND_API_KEY = process.env.RESEND_API_KEY;
if (!RESEND_API_KEY) throw new Error("RESEND_API_KEY is required");
```

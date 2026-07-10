---
name: env-parity-drift
category: infrastructure
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/.env*", "**/docker-compose*", "**/*.yml", "**/*.yaml"]
perspectives: [operator]
reversibility-check: false
---

# env-parity-drift

## Trigger

Environment configuration files (`.env.example`, `.env.staging`, `docker-compose.yml`) define different sets of variables, causing parity drift between development, staging, and production. A variable present in `.env.example` but missing from staging config means the feature works locally but fails in staging. A variable present in staging but not in `.env.example` means new developers cannot run the project without tribal knowledge.

## Detection

Compare env files in the diff:
- `.env.example` vs `.env.staging` vs `.env.production` (or equivalent naming)
- Docker Compose `environment:` sections vs `.env.example`
- New env vars added to code (`process.env.NEW_VAR`) without adding to `.env.example`

Look for:
- New `process.env.X` or `os.environ["X"]` in code without a corresponding entry in `.env.example`
- Vars in `.env.example` without defaults or documentation
- Vars in docker-compose but not in `.env.example` (or vice versa)

## Retrieval

- The env files in the diff
- Code files in the diff that reference new env vars
- `.env.example` (to check if new vars are documented)

## Analysis prompt

Given the env configuration:
1. Are there env vars in code that are NOT in `.env.example`?
2. Are there env vars in `.env.example` that are NOT used in code (stale entries)?
3. Is there documentation for each var (what it does, acceptable values, whether it is required)?
4. If docker-compose is used: does it match `.env.example`?

## Severity rubric

- P0: critical env var (DB connection, auth secret) missing from `.env.example` (new devs cannot start the project)
- P1: feature env var (PUBLIC_HOST, SHARE_TOKEN_SECRET) added to code without `.env.example` entry
- P2: stale env var in `.env.example` that is no longer used (confusion, not breakage)

## Confidence factors

- HIGH: `process.env.NEW_VAR` added in diff; no `NEW_VAR` in `.env.example`; var is required (no fallback)
- MEDIUM: var added with a fallback default; `.env.example` entry would be nice but not blocking
- LOW: var is optional or only used in test context

## Examples

### Positive (drift)

```typescript
// New code:
const secret = process.env.SHARE_TOKEN_SECRET;
if (!secret) throw new Error("SHARE_TOKEN_SECRET required");
// .env.example has no SHARE_TOKEN_SECRET entry
// New developer: "why is my server crashing?"
```

### Negative (parity maintained)

```
# .env.example
SHARE_TOKEN_SECRET=<generate with: openssl rand -base64 48>
PUBLIC_HOST=http://localhost:8000
```

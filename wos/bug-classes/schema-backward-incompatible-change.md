---
name: schema-backward-incompatible-change
category: data-integrity
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go, sql]
file-patterns: ["controllers/**", "api/**", "routes/**", "migrations/**", "supabase/migrations/**"]
perspectives: [api-consumer, operator]
reversibility-check: true
---

# schema-backward-incompatible-change

## Trigger

An API response shape, event payload, or database schema is changed in a way that breaks existing consumers: a field is removed, renamed, or has its type changed without a deprecation period or versioning. Existing clients (FE apps, mobile apps, partner integrations, downstream services) that depend on the old shape will break silently or crash.

## Detection

Look for changes in the diff where:
- A field is removed from a JSON response object (was present before, absent now)
- A field is renamed (old name gone, new name added)
- A field's type changes (was string, now number; was object, now array)
- A database column is dropped or renamed without a migration strategy (code still references old name)
- An enum value is removed (consumers that stored the old value break on read)

Compare the diff against:
- OpenAPI spec or API documentation (if present)
- TypeScript type definitions shared between BE and FE
- Database migration files vs code that queries the affected table

## Retrieval

- The modified response/payload definition (controller or type file)
- The previous version (from git diff) to identify removed/renamed fields
- Known consumers of this API (FE service files, partner integration docs, webhook handlers)

## Analysis prompt

Given the schema change:
1. What field(s) were removed, renamed, or changed in type?
2. Who consumes this schema? (FE app, mobile app, partner API, downstream service)
3. Do existing consumers handle the absence of the old field gracefully? (optional chaining, default value, error handling)
4. Is there a versioning strategy in place? (API version header, URL versioning, gradual deprecation)
5. If no versioning: what is the deploy ordering? (Must the consumer be updated before the producer, or vice versa?)
6. Recommended fix: keep old field alongside new field during transition; deprecate with timeline; or version the endpoint.

## Severity rubric

- P0: field removal on a public/partner API without versioning (external consumers break immediately on deploy)
- P1: field removal on an internal API (FE/mobile) without coordinated deploy (race condition between BE and FE deploys)
- P2: field type change that is backward-compatible (e.g., adding optional new field; widening string to string|null)

## Confidence factors

- HIGH: field visibly removed from response object in the diff; FE code in the same repo still references it
- MEDIUM: field renamed but the old name is aliased (partial backward compatibility)
- LOW: field added or type widened (additive change; unlikely to break consumers)

## Examples

### Positive (breaking change)

```typescript
// Before: res.json({ share_id, share_url, expires_at })
// After:  res.json({ id, url, expiresAt })
// FE code still references response.share_id -> undefined
```

### Negative (backward-compatible)

```typescript
// Before: res.json({ share_id, share_url })
// After:  res.json({ share_id, share_url, expires_at })
// Additive: existing consumers ignore the new field
```

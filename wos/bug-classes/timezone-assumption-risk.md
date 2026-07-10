---
name: timezone-assumption-risk
category: data-integrity
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go, sql]
file-patterns: ["controllers/**", "services/**", "migrations/**", "api/**", "lib/**"]
perspectives: [operator]
reversibility-check: false
---

# timezone-assumption-risk

## Trigger

Date/time values are created, stored, compared, or displayed without explicit timezone handling. The code assumes a specific timezone (typically the server's local timezone or UTC) without documenting or enforcing it, leading to off-by-hours bugs when the server, database, or client operates in a different timezone.

## Detection

Look for:
- `new Date()` used for business logic without `.toISOString()` or explicit UTC conversion
- `Date.now()` compared against DB timestamps without timezone normalization
- Database columns typed as `timestamp` (without timezone) instead of `timestamptz` (with timezone)
- String date parsing without timezone specification: `new Date("2026-05-24")` (parsed as local time, varies by runtime)
- Display of dates without `Intl.DateTimeFormat` or explicit timezone parameter
- `expires_at` or `created_at` comparisons where one side is UTC and the other is local

## Retrieval

- The function body containing date creation/comparison
- The database migration for the column's type (timestamp vs timestamptz)
- The display component (to check if timezone is applied on render)

## Analysis prompt

Given the date handling:
1. Where is this date value created? Server-side (which timezone?) or client-side (user's timezone)?
2. How is it stored? `timestamptz` (timezone-aware, safe) or `timestamp` (timezone-naive, risky)?
3. When compared or displayed, is the timezone explicitly handled or assumed?
4. What is the worst-case bug? (Share expires 5 hours early/late; event shows on wrong day; report date off by 1 day)
5. Recommended fix: use `timestamptz` in DB, `.toISOString()` for transport, `Intl.DateTimeFormat` for display.

## Severity rubric

- P0: timezone bug affects financial calculations, legal deadlines, or regulatory timestamps
- P1: timezone bug affects user-visible scheduling, expiration, or reporting (shows wrong time/date)
- P2: timezone inconsistency in internal logs or non-critical metadata

## Confidence factors

- HIGH: `new Date("YYYY-MM-DD")` without timezone suffix used in business logic; DB column is `timestamp` not `timestamptz`
- MEDIUM: `new Date()` used for expiration calculation; server timezone may differ from expectation
- LOW: all dates use `.toISOString()` and `timestamptz`; risk is theoretical

## Examples

### Positive (timezone risk)

```typescript
const expiresAt = new Date("2026-05-24"); // parsed as midnight LOCAL time; varies by server TZ
await db.insert({ expires_at: expiresAt }); // stored as local, compared as UTC later
```

### Negative (timezone-safe)

```typescript
const expiresAt = new Date(Date.now() + ttlHours * 3600_000).toISOString(); // always UTC
await db.insert({ expires_at: expiresAt }); // stored as timestamptz, compared as UTC
```

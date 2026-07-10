---
name: sql-injection-via-string-concat
category: security
default-severity: P0
cwe: [CWE-89]
languages: [typescript, javascript, python, go, sql]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go", "**/*.sql"]
perspectives: [security]
reversibility-check: false
---

# sql-injection-via-string-concat

## Trigger

A SQL query is built by concatenating or interpolating user-controlled input directly into the query string, bypassing parameterized queries or the ORM's built-in escaping. An attacker can inject arbitrary SQL to read, modify, or delete data.

## Detection

Look for:
- Template literals or string concatenation that embed variables into SQL: `` `SELECT * FROM users WHERE id = '${userId}'` ``
- Python f-strings in SQL: `f"SELECT * FROM users WHERE id = '{user_id}'"`
- Go `fmt.Sprintf` in SQL: `fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userId)`
- Any `query()` or `exec()` call where the SQL string contains interpolated user input instead of `$1` / `?` / `:param` placeholders

Exclude:
- ORM query builders (Supabase `.eq()`, Prisma `.where()`, SQLAlchemy `.filter()`) that parameterize internally
- Parameterized queries with explicit placeholders: `query("SELECT * FROM users WHERE id = $1", [userId])`
- Queries where the interpolated value is a constant or enum (not user-controlled)

## Retrieval

- The function body containing the query
- The source of the interpolated variable (to verify if user-controlled)

## Analysis prompt

Given the query:
1. Is the interpolated value user-controlled (request param, header, body field)?
2. Is the query using parameterized placeholders (`$1`, `?`, `:param`) or string interpolation?
3. If string interpolation: what data can an attacker access or modify by injecting SQL?
4. Recommended fix: use parameterized queries or the ORM's built-in query builder.

## Severity rubric

- P0: user-controlled input interpolated into a query on a table with sensitive data (always P0 for SQL injection)
- P1: not applicable (SQL injection is always P0 when user-controlled)
- P2: the interpolated value is not user-controlled but the pattern is dangerous if the data source changes

## Confidence factors

- HIGH: value traced to `req.params`, `req.body`, `req.query`, or equivalent; interpolated directly into SQL string
- MEDIUM: value comes from DB but that DB field is writable by users
- LOW: value is from a trusted source (config, constant, enum) but the pattern should still use parameterization

## Examples

### Positive (SQL injection)

```typescript
const result = await db.query(
  `SELECT * FROM users WHERE email = '${req.body.email}'`
);
// Input: ' OR '1'='1 exposes all users
```

### Negative (safe)

```typescript
const result = await db.query(
  "SELECT * FROM users WHERE email = $1",
  [req.body.email]
);
// Parameterized: input is escaped by the driver
```

---
name: supabase-error-in-object-not-thrown
category: reliability
default-severity: P1
priority: P1
pillars: [reliability, observability]
cwe: [CWE-252, CWE-390]
languages: [typescript, javascript]
file-patterns: ["**/src/**", "**/lib/**", "**/integrations/**", "supabase/functions/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# supabase-error-in-object-not-thrown

The Supabase JS client (`supabase-js`, `PostgrestClient`) reports query and mutation failures by returning them in the response object's `error` field. It does NOT throw on a database error. Code that destructures only `const { data } = await supabase...` (or ignores the return of an `.update()` / `.insert()` / `.delete()`) silently discards real failures: a connection reset, timeout, RLS denial, or constraint violation resolves normally with `data: null`. A surrounding `try/catch` gives false confidence because there is nothing to catch. The result is wrong behavior with no log line, so the failure is invisible in production.

## What it looks like

- `const { data } = await supabase.from(...).select(...)...` -- the `error` field is dropped, so a failed read is indistinguishable from an empty result and the code proceeds with a default or `null`.
- A write with no capture at all: `await supabase.from(...).update({...}).eq("id", id);` -- the returned `{ error }` is discarded, so a failed status write leaves stale rows (e.g. `last_synced_at`, `error_count`) while the run reports success.
- A `try/catch` wrapped around a Supabase call whose only fallback path is the `catch` block -- the catch never fires for query errors (they are not thrown), so the fallback silently becomes the default behavior on every DB error.
- An `.rpc(...)` call whose `{ error }` is not checked before using `data`.
- A "graceful default" (return a fallback value on failure) that is reached via `data == null` rather than via an explicit `error` check -- the default is applied to both "no rows" and "DB error", conflating an expected empty result with an operational failure.

## Why it matters

- Wrong behavior, silently: when a fallback value is applied because `data` is null on a DB error, the system acts on the wrong data. Example: a per-tenant config read that defaults on error can apply the wrong tenant setting, ingesting or dropping records that should have been handled the other way.
- Stale operational state: an ignored `.update()` error leaves status/heartbeat columns unchanged, so monitoring shows an integration as unsynced or still errored after a clean run (or the reverse), inflating MTTR.
- No trace: because nothing throws and nothing is logged, the failure never reaches the error pipeline. Operators cannot tell "DB is failing" from "no rows matched".
- False safety from `try/catch`: reviewers see a catch block and assume DB errors are handled, when in fact only unexpected throws are, so the class survives review.

## How to detect

Grep heuristics:

```
# Reads that destructure data but not error
rg -n "const \{ data \} = await supabase" --type ts

# Writes whose return is discarded (no destructure at all)
rg -n "await supabase\b" --type ts -A 4 \
  | rg -B 1 "\.update\(|\.insert\(|\.delete\(|\.upsert\(" \
  | rg -v "\{ *error" 

# rpc calls that use data without checking error
rg -n "await supabase\.rpc\(" --type ts -A 3 | rg -B 1 -A 3 "data" | rg -v "error"
```

Code-review signals:

- Any `await supabase...` whose result is either not destructured or destructured without `error`.
- A fallback/default value reached through a `data`-null check rather than an explicit `if (error)` branch.
- A `try/catch` around a Supabase call where the catch is the only non-happy path (the query-error path is missing).
- Status/heartbeat writes (`last_synced_at`, `error_count`, `status`) whose update result is not inspected.

## How to fix

1. Always destructure and check `error` first: `const { data, error } = await supabase...; if (error) { /* log + handle */ }` -- branch on `error` before touching `data`.
2. Distinguish "DB error" from "no rows": an explicit `if (error)` branch handles operational failure; a separate `data == null` check handles the legitimate empty result. Never let a fallback serve both.
3. On writes, capture and act on `error`: `const { error } = await supabase.from(...).update({...}).eq(...); if (error) logger.error(...)` -- at minimum log; escalate (retry, mark degraded, non-zero exit for a job) when the write is load-bearing.
4. Keep `try/catch` only for genuinely unexpected throws (network stack, serialization), not as the DB-error handler -- the `error` check is the DB-error handler.
5. Log with context (tenant/company id, entity id, `error.message`) so the failure is greppable and attributable.
6. Prefer a thin wrapper (`selectOrThrow`, `mustUpdate`) at the boundary so every call site inherits the check instead of relying on each author to remember.

## CWE / standard refs

- CWE-252: Unchecked Return Value. The `{ error }` field is a return value signaling failure; ignoring it is the canonical instance of this weakness.
- CWE-390: Detection of Error Condition Without Action. The error condition is available (in `error`) but no action (log, retry, escalate) is taken.

## See also

- `wos/bug-classes/error-message-low-quality.md` (once you check the error, log it with enough context to act on).
- `wos/bug-classes/env-dependent-default.md` (sibling silent-default pattern: a fallback masks a real signal).
- `wos/bug-classes/human-in-the-loop-audit-missing.md` (observability sibling: an operational event that leaves no record).

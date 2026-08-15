---
name: supabase-error-in-object-not-thrown
category: reliability
default-severity: P1
cwe: [CWE-252, CWE-390]
languages: [typescript, javascript]
file-patterns: ["**/src/**", "**/lib/**", "**/integrations/**", "supabase/functions/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# supabase-error-in-object-not-thrown

## Trigger

The Supabase JS client reports query and mutation failures in the response object's `error` field rather than by throwing. Code that destructures only `data`, or that discards the return of a write entirely, silently drops real failures: a connection reset, a timeout, a row-level-security denial, or a constraint violation resolves normally with `data` null and the run continues.

What makes this expensive is that every instinct a reviewer has points the wrong way. A surrounding `try/catch` looks like error handling and catches nothing, because nothing is thrown. A null `data` looks like an empty result, because an empty result also produces null. A fallback value applied on null looks like graceful degradation, when it is the system acting on the wrong data. Nothing logs, so the failure never reaches the error pipeline, and the operator cannot separate "the database is failing" from "no rows matched".

CWE-252 (Unchecked Return Value): the `error` field is a return value signaling failure and it is ignored. CWE-390 (Detection of Error Condition Without Action): the condition is available and no action follows.

## Detection

Five shapes, ordered by how convincing they look to a reviewer:

1. **The `try/catch` that cannot fire.** A Supabase call wrapped in a catch whose block is the only non-happy path. Query errors never reach it, so the fallback inside becomes the behavior on every database error while looking like the exception path.
2. **The read that drops `error`.** `const { data } = await supabase.from(...).select(...)`, after which a failed read and an empty table are the same value.
3. **The write with no capture.** `await supabase.from(...).update({...}).eq("id", id);` with the result discarded, so a failed status write leaves `last_synced_at` or `error_count` stale while the run reports success.
4. **The fallback reached through `data == null`.** One default serves both the legitimate empty result and the operational failure, which is what turns a database error into wrong behavior rather than a visible one.
5. **The unchecked `.rpc(...)`.** `data` used without the `error` branch, with the same consequences and less visibility because the call reads like a function.

Grep heuristics:

```
# Reads that destructure data but not error
rg -n "const \{ data \} = await supabase" --type ts

# Writes whose return is discarded
rg -n "await supabase\b" --type ts -A 4 \
  | rg -B 1 "\.update\(|\.insert\(|\.delete\(|\.upsert\(" \
  | rg -v "\{ *error"

# rpc calls that use data without checking error
rg -n "await supabase\.rpc\(" --type ts -A 3 | rg -B 1 -A 3 "data" | rg -v "error"
```

## Retrieval

- Every `await supabase` call site in the module under analysis, reads and writes together. Writes are the half that gets skipped, and they are where the stale operational state comes from.
- The lines after each call, far enough to see the whole branch. The class lives in what follows the call, not in the call, so a one-line grep result is not enough to judge any site.
- Any wrapper or helper the module uses for database access, and whether call sites go through it. One checked wrapper with ten bypassing call sites is a different finding from ten unchecked call sites.
- The fallback values and defaults reachable from these calls, including their callers. The question is what the system does with a default, and that answer is one level up.
- The logging around each call, so the report can say whether a failure would leave any trace at all.
- The client's own typings for the response shape when the analysis needs to state what the client does on failure. That is the observable artifact for the premise of this class.

## Analysis prompt

Given the retrieved call sites and the branches that follow them:

1. Enumerate every `await supabase` call site and classify each: destructures both `data` and `error`, destructures `data` only, or discards the result. Report the counts and list the sites in the second and third groups.
2. For each site that obtains `error`, report whether the code branches on it BEFORE touching `data`. Obtaining the field and then ignoring it is the same finding as never destructuring it, and it reads as handled.
3. Find every `try/catch` wrapped around one of these calls. For each, report what the catch block does and whether any non-happy path exists outside it. A catch that is the only fallback path is the finding; state that query errors do not reach it.
4. For each fallback or default value, report which condition reaches it. Separate the `error` path from the empty-result path explicitly. Where one default serves both, trace what the caller does with it and report the concrete wrong behavior, not just the conflation.
5. For every write, report whether its `error` is captured and what happens when it is set. Name any status, heartbeat, or counter column whose update is unchecked, because those are the ones that mislead monitoring in the direction of looking healthy.
6. Report, per site, whether a failure would produce a log line, and whether that line would carry enough context to attribute it: the tenant or company identifier, the entity identifier, and the error message.
7. Determine whether a shared wrapper exists and how many sites bypass it. This decides whether the fix is one boundary or every author.
8. WHERE the analysis states what the client does on failure, ground it in the client's own typings or documentation rather than in recollection of the library. The premise of this class is checkable in the response type; check it.
9. Recommend, in order: destructure `error` and branch on it before reading `data`; keep the operational-failure branch and the empty-result branch separate so one default never serves both; capture and act on `error` for writes, logging at minimum and escalating when the write is load-bearing; keep `try/catch` for genuinely unexpected throws and stop treating it as the database-error handler; log with enough context to attribute the failure to a tenant and an entity; and put a thin wrapper at the boundary so each call site inherits the check instead of depending on the next author remembering.

## Severity rubric

- **P1**: an unchecked error on a path whose fallback changes behavior, for example a per-tenant configuration read that defaults on failure and applies another tenant's setting. Justification: the system acts on wrong data with no trace, which is worse than an outage because nothing signals it. It sits below P0 because the underlying data is intact and the failure stops when the query starts succeeding again; the harm is what was done in the meantime.
- **P1 also**: an unchecked write to a status, heartbeat, or counter column. Monitoring reports the opposite of the truth, in either direction, and the time to recovery grows because the dashboard argues against the incident.
- **P2**: an unchecked error on a path whose only consequence is a missing value the caller already treats as optional. Real and bounded.
- **P2**: errors checked everywhere and logged without attributing context, so the failure is visible and not attributable.

## Confidence factors

- **HIGH**: a call site that destructures `data` only, with the following branch treating null as an empty result. Both halves are on the page.
- **MEDIUM**: a write whose result is discarded on a path with no visible operational consumer. The check is missing; whether anything depends on the column is unresolved without tracing its readers.
- **LOW**: a `try/catch` around a Supabase call that also contains non-Supabase work capable of throwing, where the catch may exist for that other work rather than as a mistaken database handler.

## Examples

### Positive (catch that cannot fire, default that changes behavior)

```ts
try {
  const { data } = await supabase
    .from("tenant_config").select("ingest_mode").eq("tenant_id", tenantId).single();
  return data?.ingest_mode ?? "drop";     // DB error and "no such tenant" are the same here
} catch {
  return "drop";                          // never runs for a query error
}
```

On a row-level-security denial or a timeout, `data` is null, the catch does not fire, and the function returns the drop mode for a tenant configured to ingest. Records are discarded, the run reports success, and no log line exists to connect the two.

### Negative (error first, paths separated, write checked)

```ts
const { data, error } = await supabase
  .from("tenant_config").select("ingest_mode").eq("tenant_id", tenantId).single();

if (error) {
  logger.error("tenant_config read failed", { tenantId, message: error.message });
  throw new ConfigUnavailable(tenantId);   // operational failure, not a default
}
if (!data) return "drop";                  // genuinely no such tenant

const { error: writeError } = await supabase
  .from("sync_state").update({ last_synced_at: now }).eq("tenant_id", tenantId);
if (writeError) logger.error("heartbeat write failed", { tenantId, message: writeError.message });
```

The database error and the empty result reach different branches, the failure refuses to serve a default, the heartbeat write is inspected rather than assumed, and both log lines carry the tenant so an operator can attribute them.

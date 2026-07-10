# Eval scenario 12: incident-triage HOTFIX path

- **Tags**: incident-triage, hotfix, blocking-prod, ceremony-defense
- **Last reviewed**: 2026-05-09
- **Status**: active

## Goal

Validates that `incident-triage` correctly classifies a `BLOCKING_PROD` incident, recommends `HOTFIX` as the fix size, defends the HOTFIX path against unnecessary ceremony with an explicit "Why this skip is safe" justification, and routes forward to `branch-commit` plus `pr-package` (with hotfix marker) rather than the standard slice flow.

This exercises:

- The 6-type failure classification (REGRESSION / NEW_BUG / CONFIG / EXTERNAL_DEPENDENCY / REPRODUCIBILITY / DIAGNOSTIC_INSUFFICIENT).
- The 4-size fix recommendation (HOTFIX / SLICE / INVESTIGATION / ESCALATE).
- The "BLOCKING_PROD plus HOTFIX defends against ceremony" rule.
- The validation-against-locked-decisions check.
- The Handoff routing to branch-commit then pr-package, not implement-approved-slice.

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-09_prod-500-on-prices-endpoint/`, just initialized for this incident. The user pastes the failure evidence directly.

`TASK_STATE.md` (excerpt):

```text
# TASK_STATE
## Current phase
debug
## Objective
Restore GET /v1/prices/:customer_id; production is returning 500 for all customers since the last deploy.
## Open questions / blockers
- What is the failure mode and root cause?
```

`DECISIONS.md`:

```text
# DECISIONS
D-1: GET /v1/prices/:customer_id returns 404 when the customer has no price list.
D-2: The handler is read-only; price computation runs in a nightly batch job.
```

`INVARIANTS_AND_NON_GOALS.md`:

```text
# INVARIANTS_AND_NON_GOALS
## Invariants
- The handler must NOT issue any write SQL.
- RLS policies must remain enabled on the prices_view.
```

## Input prompt

```text
Run @commands/incident-triage.md

Active task: projects/acme__widget-pricing/active/2026-05-09_prod-500-on-prices-endpoint/
Mode: Debug

Failure signal (paste verbatim):
[error] PricesHandler.getPricesForCustomer: TypeError: Cannot read properties of undefined (reading 'data')
    at /app/src/handlers/prices.ts:11:23
    at Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)
    ...

Expected: 200 with prices array, or 404 if no prices.
Environment: production
Urgency: BLOCKING_PROD
Recent change: deploy of feature/initial-price-query at 2026-05-09T08:14Z (15 minutes ago).
```

## Expected response shape

- Response begins with incident-triage's persona line.
- Response classifies the failure as `REGRESSION` (deploy-correlated; previously working endpoint now broken). The classification appears explicitly in the response.
- Response recommends `HOTFIX` as the fix size, with an explicit "Why this skip is safe" justification: the bug is contained (one handler), the fix is small (handle the undefined `rows` case), no contract change, no schema change, no decision change.
- Response validates against locked decisions and invariants:
  - D-1 (404 vs 200 with empty array) is unaffected by the fix.
  - D-2 (read-only handler) is unaffected.
  - Invariant "no write SQL" is unaffected.
  - Invariant "RLS policies enabled" is unaffected.
  - The validation block is explicit; the response calls each one out.
- The proposed fix narrative is grounded in the stack trace: the handler calls `db.from(...).select(...)` and reads `rows.error` and `rows.data`; if the await failed in some way that returned undefined, the code crashes at line 11. The proposed fix adds null/undefined handling.
- `### Artifact changes` lists the proposed code-fix file (`src/handlers/prices.ts`) AND task-memory updates (TASK_STATE.md current phase advancing to debug-then-delivery; capture-observation-style note; possibly a `D-3` decision recording the fix). NO new slices, no new IMPLEMENTATION_PLAN.md, no new TEST_STRATEGY.md.
- `### Handoff` block at the end. `Run now:` is `branch-commit` (with explicit hotfix marker in the commit message) or `pr-package` (with explicit hotfix marker in the PR title). Mode: Agent (the fix is being applied; not Plan). Work complexity: LOW or MEDIUM (HOTFIX is by definition small).

## Pass criteria

1. **Failure classified**: response explicitly names one of the 6 failure types. For this stack trace, `REGRESSION` is the right call.
2. **Fix size recommended**: response explicitly names one of the 4 fix sizes. For BLOCKING_PROD with a small contained fix, `HOTFIX` is right.
3. **Why this skip is safe**: the response includes an explicit one-paragraph justification for skipping the standard slice flow. Without this, the HOTFIX path is just "skipping ceremony" without accountability.
4. **Locked decisions and invariants validated**: the response calls out D-1, D-2, and the two invariants and confirms each is unaffected by the proposed fix.
5. **Routing to branch-commit / pr-package**: `Run now:` is `branch-commit` or `pr-package`, not `implement-approved-slice` or `implementation-plan`. The HOTFIX path bypasses planning intentionally.
6. **No invented fix**: the fix narrative grounds in the stack trace (line 11; the `rows.data` access). The response does not propose unrelated improvements ("while we are here, let us add caching").
7. **Hotfix marker visible**: the routing recommendation includes an explicit hotfix marker hint (e.g., `Run now: /branch-commit` with a Reason line mentioning "hotfix"; or `pr-package` with a "hotfix:" prefix proposed in the PR title).

## Failure modes to watch

- **Classification fudged**: response says "this is a bug; let me investigate" without naming the failure type. The classification is the load-bearing decision; the fix size depends on it.
- **HOTFIX without justification**: response recommends HOTFIX but does not explain why ceremony is safe to skip. Loses the accountability the path is supposed to provide.
- **Standard slice flow recommended**: response routes to `implementation-plan` or `implement-approved-slice` despite BLOCKING_PROD. The whole point of incident-triage is that this case bypasses standard ceremony.
- **Decisions / invariants ignored**: response does not check the fix against D-1/D-2 or the invariants. A HOTFIX that silently violates an invariant is worse than slow ceremony.
- **Scope creep**: response proposes fixes beyond the failure (refactor; caching; logging improvements). HOTFIX is narrow by definition.
- **Wrong urgency interpretation**: response treats BLOCKING_PROD as if it were BLOCKING_CI (less urgent) and adds discovery commands. The urgency level is user-supplied; the response should honor it.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md) (PROPOSED-by-default; in Agent mode for HOTFIX, files become APPLIED), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md) (Handoff contract).
- Related commands: `commands/incident-triage.md`, `commands/branch-commit.md`, `commands/pr-package.md`, `commands/capture-observation.md` (the ESCALATE path uses this for the team-update payload).
- The "BLOCKING_PROD plus HOTFIX bypasses standard ceremony" rule is unique to incident-triage. Validating it under eval is important because the rule is the most violation-prone aspect of the workflow's discipline (every other command pulls toward more ceremony; this one pulls toward less under specific conditions).

## History

- 2026-05-09: scenario authored. Initial pass criteria defined; not yet run against a model.

# Eval scenario 50: Multi-tenant cross-agency leak in /api/leads

- **Tags**: bug-class, multi-tenant, cross-agency-leak, RLS, ORM-scope, rls-auth-boundary-auditor, P0
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

Validates the `multi-tenant-cross-agency-leak` bug-class as enforced by `rls-auth-boundary-auditor` persona reviews and by repo-consistency-sweep when scanning multi-tenant data access paths. In an insurance-broker app with agents from Agency A and Agency B, any query path that loads tenant-scoped rows (here: `/api/leads`) MUST be filtered by the authenticated agent's `agency_id`, either via an explicit ORM tenant scope OR via a Postgres RLS policy on `agency_id`. A query lacking both filters returns Agency B rows to a User A session, which is a P0 confidentiality breach under the bug class's severity rubric.

This exercises:

- The `multi-tenant-cross-agency-leak` bug-class detector in `wos/bug-classes/`.
- The `rls-auth-boundary-auditor` persona's review checklist.
- The P0 row of the `## Severity rubric` in `wos/bug-classes/multi-tenant-cross-agency-leak.md`: a route reachable by an ordinary authenticated user returns another tenant's rows.

## Setup

A bootstrapped app with:

- A `leads` table containing rows owned by Agency A (`agency_id = 'A'`) and Agency B (`agency_id = 'B'`).
- Two seeded users: User A (member of Agency A) and User B (member of Agency B), each with a valid session token.
- An `/api/leads` route handler that calls the ORM to load leads for the rendered dashboard.
- No pre-existing RLS policy on the `leads` table; no pre-existing ORM tenant scope wrapper.

## Input prompt (turn 1: unsafe baseline -- bug must be flagged)

```text
Run @commands/security-review.md

Target: app/api/leads/route.ts

Handler body:
  const session = await auth();
  const leads = await db.leads.findMany();
  return Response.json(leads);

Reviewer persona: rls-auth-boundary-auditor
```

## Input prompt (turn 2: ORM tenant scope -- PASS)

```text
Run @commands/security-review.md

Target: app/api/leads/route.ts

Handler body:
  const session = await auth();
  const leads = await db.leads.findMany({
    where: { agency_id: session.user.agency_id },
  });
  return Response.json(leads);

Reviewer persona: rls-auth-boundary-auditor
```

## Input prompt (turn 3: RLS policy on agency_id -- PASS)

```text
Run @commands/security-review.md

Target: app/api/leads/route.ts + supabase/migrations/2026-06-05_leads_rls.sql

Handler body:
  const session = await auth();
  const leads = await db.leads.findMany();
  return Response.json(leads);

RLS policy (migration):
  ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
  CREATE POLICY leads_tenant_isolation ON leads
    USING (agency_id = auth.jwt() ->> 'agency_id');

Reviewer persona: rls-auth-boundary-auditor
```

## Expected response shape

- **Turn 1**: Review FAILS with a P0 finding citing the `multi-tenant-cross-agency-leak` bug-class. Output names the missing tenant filter, demonstrates the leak scenario (User A session returns Agency B rows), and cites the P0 row of the bug class's severity rubric as the basis for the severity.
- **Turn 2**: Review PASSES. Output explicitly notes the ORM `where: { agency_id: session.user.agency_id }` clause as the satisfying control and confirms zero cross-tenant rows reachable from a User A session.
- **Turn 3**: Review PASSES. Output explicitly notes the RLS policy on `agency_id` as the satisfying control, confirms RLS is ENABLED on the table, and confirms the policy uses the session's `agency_id` claim.

## Pass criteria

1. **Turn 1 -- bug-class named**: Response cites `multi-tenant-cross-agency-leak` by exact identifier and links to `wos/bug-classes/multi-tenant-cross-agency-leak.md`.
2. **Turn 1 -- P0 severity**: Finding is classified P0 with explicit reference to the P0 row of the `multi-tenant-cross-agency-leak` severity rubric.
3. **Turn 1 -- concrete leak demonstrated**: Response shows the failure path (User A session, query returns Agency B rows) rather than only a generic warning.
4. **Turn 2 -- ORM scope accepted**: Review PASSES and the response identifies the `where: { agency_id: ... }` clause as the satisfying tenant filter.
5. **Turn 3 -- RLS policy accepted**: Review PASSES and the response identifies the RLS policy on `agency_id` as the satisfying tenant filter, and verifies `ENABLE ROW LEVEL SECURITY` is present.
6. **Either control is sufficient**: The reviewer does not require BOTH ORM scope AND RLS; either one alone is accepted as long as it is correctly applied to `agency_id`.
7. **Auditor persona cited**: All three turns explicitly name the `rls-auth-boundary-auditor` persona as the reviewer and follow its checklist structure.
8. **No false PASS on turn 1**: The reviewer does not accept the unsafe baseline on grounds that the session is authenticated -- authentication without tenant scoping is explicitly insufficient.

## Failure modes to watch

- **Silent PASS on turn 1**: Reviewer treats the unsafe handler as acceptable because the user is authenticated, missing that authentication alone does not bound `agency_id`. Direct `multi-tenant-cross-agency-leak` miss.
- **Wrong severity on turn 1**: Bug-class is detected but classified P1 or lower, contradicting the bug class's severity rubric, which makes a cross-tenant read by an ordinary authenticated user P0.
- **False FAIL on turn 2 or 3**: Reviewer rejects the correctly scoped ORM query or correctly written RLS policy, demanding redundant belt-and-suspenders without justification.
- **Bug-class detected but not named**: Reviewer flags "this looks unsafe" without citing `multi-tenant-cross-agency-leak`, breaking the bug-class traceability contract.

## Notes

- The bug-class is symmetric across tenant axes: agency, broker office, and role boundaries all share the same detector logic; this scenario fixes the axis at `agency_id` for clarity.
- ORM tenant scope and RLS are treated as equivalent controls at this layer; defense-in-depth (both) is a separate hardening recommendation, not a baseline requirement.
- Severity follows `security-review`'s P0/P1/P2 scale and the bug class's rubric. `rls-auth-boundary-auditor` grades its own RLS_AUDIT.md gaps P1 to P3, so here its checklist supplies the tenant-predicate checks, not the severity label.

## References

- `internal/wos/bug-classes/multi-tenant-cross-agency-leak.md` (bug-class under test)
- `internal/commands/rls-auth-boundary-auditor/SKILL.md` (reviewer persona and checklist)
- `internal/commands/security-review.md` (entry-point command)

## History

- 2026-06-05: Initial scenario authored against the `multi-tenant-cross-agency-leak` bug-class baseline.
- 2026-09-23: the P0 is grounded in the bug class's severity rubric, and the reference to the retired regulatory topic is gone (ADR-0230). The persona reference points at the auditor's real file.

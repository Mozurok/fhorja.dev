
# Post-deploy verification plan -- Slice 19: Team invitations (multi-repo split)

Slice spans two repos (`app-api`, `app-web`). Per Step 7 the plan is split into two per-repo PROPOSED files. Backend MUST land before frontend; the backend file carries the `Cross-repo:` ordering line and the spurious-failure mode.

---

### Artifact changes

- PROPOSED `projects/<client>__<project>/active/2026-06-05_team-invitations/POST_DEPLOY_PLAN.backend.md`
- PROPOSED `projects/<client>__<project>/active/2026-06-05_team-invitations/POST_DEPLOY_PLAN.frontend.md`
- PROPOSED `projects/<client>__<project>/active/2026-06-05_team-invitations/SLICES/19_team_invitations.md` -- append `## Post-deploy checks` section linking both per-repo plans
- PROPOSED `projects/<client>__<project>/active/2026-06-05_team-invitations/TASK_STATE.md` -- append `## Risks to watch` entry: "Cross-repo deploy-order skew (app-web before app-api) -> AC-3/AC-4 spurious 404s"

---

## File 1 -- `POST_DEPLOY_PLAN.backend.md` (PROPOSED)

```markdown
# Post-deploy verification plan -- Slice 19 (app-api / backend)

Deploy: sha=`8e7d6c5`, env=production, deployed_at=2026-06-05T11:00:00Z
Repo: app-api (monorepo path `apps/api/`)
On-call: @bruno
Deploy window for all queries below: `2026-06-05T11:00:00Z` to `2026-06-05T12:00:00Z` (60 min post-deploy soak).

Cross-repo: app-api MUST be live before app-web (sha=`a1b2c3d`, ts=2026-06-05T11:30:00Z) begins its smoke walk. If the frontend deploys first, AC-3 and AC-4 verification will spuriously fail because the team-settings page and `/accept/:token` page will POST/GET against routes the backend has not yet exposed -> uniform 404 from `apps/api/` -> verifier will conclude "new flow broken" when the actual cause is deploy-order skew, not a code bug. Verification gate: do not start the frontend smoke walk (AC-3, AC-4 in `POST_DEPLOY_PLAN.frontend.md`) until BOTH of these hold:
1. Datadog APM shows `service:app-api version:8e7d6c5` receiving traffic on `route:/api/v1/teams/:id/invitations` (any status) within the deploy window.
2. The backend smoke probe in AC-1 below returns 201 with a token from production.

If app-web deploys ahead of app-api, page @bruno and either (a) hold the frontend deploy until app-api is live, or (b) execute the frontend rollback in `POST_DEPLOY_PLAN.frontend.md` and redeploy in correct order.

## Per-AC signal mapping

| AC | Claim | Signal class | Exact query / inputs | Expected | Owner |
|----|-------|--------------|----------------------|----------|-------|
| AC-1 | `POST /api/v1/teams/:id/invitations` returns 201 + invitation token | (a) Datadog log query + (b) backend smoke probe | (a) Datadog Logs: `service:app-api env:production version:8e7d6c5 route:"/api/v1/teams/:id/invitations" method:POST status:201` over the deploy window. (b) `curl -sS -X POST -H "Authorization: Bearer $PROD_E2E_TOKEN" -H "Content-Type: application/json" -d '{"email":"verify+slice19@fhorja.test"}' https://api.fhorja.com/api/v1/teams/team_e2e_seed/invitations` | (a) >=1 hit, status:201 (b) HTTP 201, body contains `token` (non-empty string) and `invitation_id` | @bruno |
| AC-2 (happy) | `GET /api/v1/invitations/:token` returns the invitation metadata | Backend smoke probe chained to AC-1 | `curl -sS https://api.fhorja.com/api/v1/invitations/$TOKEN_FROM_AC1` | HTTP 200, body contains `team_id:"team_e2e_seed"`, `email:"verify+slice19@fhorja.test"`, `expires_at` (future ISO 8601) | @bruno |
| AC-2 (expired) | Expired tokens return 410 | DB invariant + targeted probe | (1) Postgres direct: `UPDATE invitations SET expires_at = NOW() - INTERVAL '1 minute' WHERE id = '$INVITATION_ID_FROM_AC1' RETURNING id, expires_at;` then (2) `curl -sS -o /dev/null -w "%{http_code}\n" https://api.fhorja.com/api/v1/invitations/$TOKEN_FROM_AC1` | (1) 1 row updated, expires_at in the past (2) prints `410` | @bruno |
| AC-3 support | Backend serves the POST endpoint used by the team-settings page | Datadog APM panel scoped to deploy window | Datadog APM: `service:app-api env:production resource_name:"POST /api/v1/teams/:id/invitations"` panel, time range = deploy window. URL: `https://app.datadoghq.com/apm/services/app-api/resources?env=production&start=1749121200000&end=1749124800000` | Hit count >=1 with version tag `8e7d6c5`; p95 latency < 800ms; error rate < 1% | @bruno |
| AC-4 support | Backend serves the GET endpoint used by `/accept/:token` page | Datadog APM panel | Datadog APM: `service:app-api env:production resource_name:"GET /api/v1/invitations/:token"` panel, time range = deploy window | Hit count >=1 with version tag `8e7d6c5`; status mix 200 + 410 only (no 500s); error rate < 1% | @bruno |

## DB invariant queries (Postgres direct, prod read-replica)

```sql
-- 1. Confirm the invitations table received writes from the new code path during the deploy window
SELECT count(*) AS new_rows
FROM invitations
WHERE created_at >= '2026-06-05T11:00:00Z'
  AND created_at <  '2026-06-05T12:00:00Z';

-- 2. Confirm token uniqueness invariant still holds
SELECT token, count(*) AS dupes
FROM invitations
WHERE created_at >= '2026-06-05T11:00:00Z'
GROUP BY token
HAVING count(*) > 1;

-- 3. Confirm no rows landed with NULL token or NULL expires_at (column-not-null contract)
SELECT count(*) AS bad_rows
FROM invitations
WHERE created_at >= '2026-06-05T11:00:00Z'
  AND (token IS NULL OR expires_at IS NULL);
```

Expected: query 1 returns >=1 (at minimum the AC-1 smoke row). Query 2 returns 0 rows. Query 3 returns 0.

## Negative checks (would prove the change DID NOT ship on app-api)

| # | Check | Query / observation | Expected |
|---|-------|---------------------|----------|
| N-1 | Old code path is dead | Datadog Logs: `service:app-api env:production version:8e7d6c5 status:404 route:"/api/v1/teams/:id/invitations"` over the deploy window | 0 hits. >0 hits = new route not registered -> deploy is a silent no-op on this slice. |
| N-2 | New version tag is actually receiving traffic | Datadog APM: `service:app-api env:production` filtered to `version:8e7d6c5` over deploy window | Hit count > 0 across ALL routes (not just the new ones). 0 hits = container did not roll, deploy is invisible. |
| N-3 | No new 5xx spike introduced | Datadog APM error-rate panel `service:app-api env:production` deploy window vs the preceding 60-min baseline | error rate delta <= +0.5%. Greater = regression on a neighboring route. |
| N-4 | Sentry: no new issue first-seen on `8e7d6c5` | Sentry issues filter `project:app-api environment:production firstRelease:8e7d6c5` | 0 new issues, OR all new issues are expected `InvitationExpired` 410 path (categorized as `level:info`). |

## Rollback trigger checklist (app-api)

| # | Observation | Page | Action |
|---|-------------|------|--------|
| R-1 | AC-1 smoke probe returns non-201 OR Datadog APM shows `route:"/api/v1/teams/:id/invitations"` 5xx rate > 2% over any 5-min window | @bruno | Roll back via `vercel rollback <previous-app-api-deployment-id>` (previous prod sha was `7f2a1b0`). Then hold app-web deploy. |
| R-2 | DB invariant query 2 (token dupes) or query 3 (NULL token/expires_at) returns > 0 rows | @bruno | Roll back app-api as in R-1 AND open incident; do NOT mutate the invitations table without a migration plan. |
| R-3 | Sentry first-seen on `8e7d6c5` exceeds 5 new issues OR any `level:error` issue tagged `route:/api/v1/teams/:id/invitations` | @bruno | Roll back app-api as in R-1. |
| R-4 | Negative check N-1 fails (>0 hits of 404 on the new route under version `8e7d6c5`) | @bruno | This is a silent no-op deploy, not a runtime bug. Confirm container rolled (`kubectl get pods -n app-api -l version=8e7d6c5`); if not, force redeploy. Do NOT proceed to frontend deploy. |
```

---

## File 2 -- `POST_DEPLOY_PLAN.frontend.md` (PROPOSED)

```markdown
# Post-deploy verification plan -- Slice 19 (app-web / frontend)

Deploy: sha=`a1b2c3d`, env=production, deployed_at=2026-06-05T11:30:00Z
Repo: app-web (monorepo path `apps/web/`)
On-call: @bruno
Deploy window for all queries below: `2026-06-05T11:30:00Z` to `2026-06-05T12:30:00Z` (60 min post-deploy soak).

Cross-repo precondition: this plan MAY ONLY be executed after the gate in `POST_DEPLOY_PLAN.backend.md` (cross-repo section) is green. If the gate is red, executing AC-3 / AC-4 below will produce uniform 404 responses from the backend and the verifier will misattribute the failure to frontend code. Verifier MUST record the gate timestamp in the verification log before starting AC-3.

## Per-AC signal mapping

| AC | Claim | Signal class | Exact query / inputs | Expected | Owner |
|----|-------|--------------|----------------------|----------|-------|
| AC-3 | Team-settings page shows 'Send invitation' form that POSTs to `/api/v1/teams/:id/invitations` and displays the returned token | Smoke-test browser walkthrough + Datadog log correlation | See **Smoke-test walkthrough A** below. Plus Datadog Logs: `service:app-web env:production version:a1b2c3d route:"/teams/:id/settings" event:"invitation_form_submit"` over deploy window. | Walkthrough A passes all steps; Datadog log shows >=1 `invitation_form_submit` event correlating (within 2s) to one of the backend AC-1 log entries (same `request_id`). | @bruno |
| AC-4 | Invitation-acceptance page (`/accept/:token`) calls `GET /api/v1/invitations/:token` and renders team metadata | Smoke-test browser walkthrough + Sentry quiet check | See **Smoke-test walkthrough B** below. Plus Sentry: `project:app-web environment:production release:a1b2c3d url:"*/accept/*"` filter. | Walkthrough B passes; Sentry shows 0 new errors on the `/accept/:token` route under release `a1b2c3d`. | @bruno |

## Smoke-test walkthrough A (AC-3)

Browser: Chrome 130 stable, fresh incognito window, US-East egress.

1. Navigate to `https://app.fhorja.com/login`. Sign in as `verify+slice19-admin@fhorja.test` (password in 1Password under "Fhorja E2E / slice 19 admin"); confirm the post-login redirect lands on `https://app.fhorja.com/dashboard`.
2. Navigate to `https://app.fhorja.com/teams/team_e2e_seed/settings`. Expected DOM: an `<h1>` containing the literal text "Team settings"; a `<form data-testid="invitation-form">` is visible.
3. In the form, fill the input `[name="email"]` with `verify+slice19-invitee@fhorja.test`. Click the button with text "Send invitation".
4. Expected network: exactly one `POST https://api.fhorja.com/api/v1/teams/team_e2e_seed/invitations` request with body `{"email":"verify+slice19-invitee@fhorja.test"}` and response status `201` whose JSON body contains a `token` field (non-empty string).
5. Expected DOM after success: a `[data-testid="invitation-token-display"]` element appears containing the same token string from step 4's response.
6. Capture: screenshot of step 5, the request_id from the response headers (`x-request-id`), and the token value (paste into the verification log).

## Smoke-test walkthrough B (AC-4)

Same browser as A, fresh tab. Use the token captured in walkthrough A step 6 as `$TOKEN`.

1. Navigate to `https://app.fhorja.com/accept/$TOKEN` (no auth required).
2. Expected network: exactly one `GET https://api.fhorja.com/api/v1/invitations/$TOKEN` request returning status `200` with body containing `team_id:"team_e2e_seed"` and the inviter email.
3. Expected DOM: an element matching `[data-testid="invitation-team-name"]` renders the literal team display name (`"E2E Seed Team"`); an `[data-testid="invitation-inviter-email"]` renders the inviter email.
4. Negative DOM expectation: no element matching `[data-testid="error-banner"]` is present.
5. Capture: screenshot, request_id header, paste into verification log.

## Negative checks (would prove the change DID NOT ship on app-web)

| # | Check | Query / observation | Expected |
|---|-------|---------------------|----------|
| N-5 | New release tag is actually serving | Vercel deployments: confirm `a1b2c3d` is the current Production alias for `app.fhorja.com` (`vercel inspect app.fhorja.com --prod`) | `aliased to: a1b2c3d`. Anything else = the deploy did not promote. |
| N-6 | Team-settings page is shipping the new form | View page source of `/teams/team_e2e_seed/settings` (auth required) and grep for `data-testid="invitation-form"` | 1 match. 0 = old bundle still serving (stale CDN edge, missed cache invalidation). |
| N-7 | No new client-side error surge | Sentry: `project:app-web environment:production release:a1b2c3d` deploy window vs preceding 60-min baseline | New-issue count delta <= +2 unique issues; none at `level:error`. |
| N-8 | Backend correlation present (catches the cross-repo ordering bug) | For the request_id captured in walkthrough A step 6, run Datadog Logs: `service:app-api request_id:"<captured-id>"` | Exactly one matching log line on `service:app-api version:8e7d6c5 status:201`. If the matching log is `status:404` or absent, the cross-repo ordering gate was violated -> halt and rollback per R-6. |

## Rollback trigger checklist (app-web)

| # | Observation | Page | Action |
|---|-------------|------|--------|
| R-5 | Walkthrough A or B fails at any step where the expected DOM / network shape is wrong AND the backend gate (cross-repo) was confirmed green | @bruno | Roll back app-web via `vercel rollback <previous-app-web-deployment-id>` (previous prod sha was `9d4e3f2`). Leave app-api in place. |
| R-6 | Negative check N-8 shows the backend correlation is 404 or absent (cross-repo ordering violation) | @bruno | Do NOT roll back app-api. Roll back app-web via `vercel rollback <previous-app-web-deployment-id>` to remove the frontend that is calling not-yet-deployed routes. Reschedule the app-web deploy for AFTER app-api `8e7d6c5` is confirmed receiving traffic. |
| R-7 | Sentry shows >5 new unique issues on release `a1b2c3d` OR any `level:error` issue on routes `/teams/:id/settings` or `/accept/:token` | @bruno | Roll back app-web as in R-5. |
| R-8 | Vercel edge cache is serving stale bundle (N-6 fails) | @bruno | `vercel purge --scope=app.fhorja.com` then re-run N-6. If still failing after one purge cycle, roll back app-web as in R-5. |
```

---

## PROPOSED block for `SLICES/19_team_invitations.md`

```markdown
## Post-deploy checks

Per-AC live signals for slice 19 are documented in:
- `POST_DEPLOY_PLAN.backend.md` (AC-1, AC-2, backend support for AC-3 and AC-4)
- `POST_DEPLOY_PLAN.frontend.md` (AC-3, AC-4)

Cross-repo ordering: app-api `8e7d6c5` MUST land and accept traffic before the frontend smoke walk begins. The backend plan's cross-repo section names the gate (Datadog APM hit on the new route + AC-1 smoke 201) and the spurious-failure mode (uniform 404s misread as code bugs).

On-call: @bruno. Rollback paths are per-repo (Vercel rollback to previous deployment id, listed in each plan's rollback section). Negative check N-8 in the frontend plan correlates the frontend smoke request_id against backend logs to catch ordering skew that would otherwise look like a frontend bug.
```

## PROPOSED block for `TASK_STATE.md ## Risks to watch`

```markdown
- Cross-repo deploy-order skew (slice 19): if app-web `a1b2c3d` reaches users before app-api `8e7d6c5` accepts traffic on `/api/v1/teams/:id/invitations` and `/api/v1/invitations/:token`, the team-settings invitation form and `/accept/:token` page will 404 in production and AC-3/AC-4 verification will misattribute to frontend code. Mitigation: cross-repo gate documented in `POST_DEPLOY_PLAN.backend.md`; negative check N-8 in `POST_DEPLOY_PLAN.frontend.md` correlates by request_id. Owner: @bruno.
```

---

### Command transcript

1. Read SLICES/19_team_invitations.md and enumerated AC-1..AC-4 (Step 1).
2. Inventoried observability stack: Datadog Logs + APM, Sentry, Postgres direct (Step 2).
3. Mapped each AC to query-shaped signals; added negative checks N-1..N-8 incl. cross-repo correlation N-8 (Steps 3-5).
4. Split per Step 7 into backend / frontend files; backend carries `Cross-repo:` line and spurious-failure mode; authored rollback per repo (Step 6).

### Handoff

- **What just happened:** Authored the per-slice post-deploy verification plan split per repo. Backend file carries the cross-repo ordering gate and the spurious-failure mode (frontend-before-backend -> uniform 404 misread as code bug). AC-3/AC-4 verification is explicitly gated on backend traffic + AC-1 smoke 201. Negative check N-8 (request_id correlation across services) is the load-bearing detector of ordering skew.
- **State now:** 2 PROPOSED plan files, 1 PROPOSED `## Post-deploy checks` block in the slice file, 1 PROPOSED risk entry in TASK_STATE.md. Nothing written to substrate.
- **Run now:** `approve-proposed` to land all four PROPOSED blocks atomically, then `slice-closure` once the on-call has walked the plan and recorded outcomes.
- **Next likely:** `slice-closure` (consumes the slice-file `## Post-deploy checks` block to close slice 19); fall through to `verify-against-rubric` only if a frozen rubric is authored from this plan.
- **Mode:** Ask (review the proposed plans), then Agent for `approve-proposed`.

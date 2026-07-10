# Slice 19: Team invitations -- Post-deploy verification plan (multi-repo)

This slice ships to two repos in a strict order. The plan is split into two artifacts, one per repo, with explicit cross-repo coupling captured in the backend file (which deploys first and gates the frontend).

Files produced:
- `POST_DEPLOY_PLAN.backend.md` (app-api, sha `8e7d6c5`, deploy 2026-06-05T11:00:00Z)
- `POST_DEPLOY_PLAN.frontend.md` (app-web, sha `a1b2c3d`, deploy 2026-06-05T11:30:00Z)

On-call: `@bruno`.

---

## POST_DEPLOY_PLAN.backend.md (app-api)

**Slice**: 19 -- Team invitations
**Repo**: app-api (monorepo path: `apps/api/`)
**Deploy SHA**: `8e7d6c5`
**Deploy timestamp**: 2026-06-05T11:00:00Z
**Environment**: production
**On-call**: `@bruno`
**Observability**: Datadog Logs + APM, Sentry, PostgreSQL (direct queries)

### Cross-repo

- **Ordering requirement**: `app-api@8e7d6c5` MUST be fully deployed AND verified healthy (AC-1 and AC-2 green) BEFORE `app-web@a1b2c3d` is deployed at 2026-06-05T11:30:00Z.
- **Coupled endpoints**: `POST /api/v1/teams/:id/invitations` and `GET /api/v1/invitations/:token` are introduced in this slice; the frontend at `a1b2c3d` calls both.
- **Spurious-failure mode if order is violated**: If `app-web@a1b2c3d` is deployed before `app-api@8e7d6c5` is live, the new web UI will call routes that the backend has not yet exposed. Datadog will show 404 responses on `/api/v1/teams/:id/invitations` and `/api/v1/invitations/:token`, Sentry will capture frontend "Failed to send invitation" / "Invitation not found" exceptions, and AC-3 / AC-4 verification will appear to fail (the new flow "does not work"). The root cause in that scenario is deploy-order, NOT a code defect in either repo. Do NOT roll back code on AC-3/AC-4 failure until you have confirmed the backend deploy is actually live (see §Negative check below).
- **Gate to frontend deploy**: All backend AC checks below must be green, and the negative check must confirm the new route handler is the one serving traffic, before `@bruno` approves the app-web deploy.

### Per-AC signal mapping

#### AC-1: `POST /api/v1/teams/:id/invitations` returns 201 with invitation token

| Signal | Source | Query / check |
|---|---|---|
| Synthetic 201 | Manual cURL from bastion: `curl -X POST .../api/v1/teams/$TEAM/invitations -d '{"email":"qa+verify@fhorja.test"}'` | Expect HTTP 201, JSON body containing `token` (non-empty string) |
| Real traffic 2xx rate | Datadog APM | `service:app-api resource_name:"POST /api/v1/teams/:id/invitations" @http.status_code:201` over 15 min window post-deploy; expect >95% of POSTs to this route are 201 |
| p95 latency | Datadog APM | Same resource, p95 < 500ms (baseline for write endpoints in this service) |
| Sentry errors | Sentry | Project `app-api`, release tag `8e7d6c5`, filter `transaction:POST /api/v1/teams/:id/invitations` -- expect 0 new issues |
| DB write | PostgreSQL | `SELECT count(*) FROM invitations WHERE created_at > '2026-06-05T11:00:00Z'` increments after synthetic POST; `token` column is non-null |

#### AC-2: `GET /api/v1/invitations/:token` returns metadata; expired tokens return 410

| Signal | Source | Query / check |
|---|---|---|
| Synthetic 200 (fresh token) | cURL using token from AC-1 synthetic | Expect HTTP 200, JSON body containing team metadata fields (team id, inviter, expires_at) |
| Synthetic 410 (expired token) | cURL against a token manually expired via `UPDATE invitations SET expires_at = now() - interval '1 hour' WHERE token = '<synthetic_token>'` | Expect HTTP 410 |
| Real traffic status distribution | Datadog APM | `service:app-api resource_name:"GET /api/v1/invitations/:token"` -- expect 200 and 410 only; 5xx rate < 0.1% |
| Sentry errors | Sentry | Release `8e7d6c5`, transaction `GET /api/v1/invitations/:token` -- 0 new issues |
| Log assertion | Datadog Logs | `service:app-api "invitation.lookup" status:expired` log line exists when 410 returned (confirms 410 came from expiry branch, not generic 404) |

### Negative check (proves the new code is actually live)

Before approving the frontend deploy:

1. Hit `GET /api/v1/_meta/version` (or equivalent build-info endpoint) and confirm response includes commit `8e7d6c5`.
2. Hit `OPTIONS /api/v1/teams/00000000-0000-0000-0000-000000000000/invitations` against the production load balancer and confirm response is NOT 404 (route is registered). A 404 here is the canonical "old build still serving" signature and means the deploy did not actually roll out -- the frontend deploy MUST be held.
3. Confirm Datadog deployment marker for `service:app-api` shows `version:8e7d6c5` at ~11:00:00Z and that the latest spans on the two new resources carry that version tag.

If any of the three fail: do NOT proceed to app-web deploy; investigate deploy pipeline.

### Rollback (app-api)

- **Trigger conditions**: AC-1 or AC-2 fail on synthetic AND real traffic (not deploy-order related); OR 5xx rate on either new route > 1% over 5 min; OR Sentry shows a new high-volume issue tagged `release:8e7d6c5` on these transactions; OR DB writes to `invitations` show malformed rows.
- **Action**: Redeploy previous known-good SHA on `app-api` via the standard rollout pipeline (revert to prior release tag). The two new routes will return 404 again, which is the pre-slice state.
- **Frontend coupling on rollback**: If `app-web@a1b2c3d` has already been deployed when backend rollback fires, the frontend will start seeing 404 on the new flows. `@bruno` MUST simultaneously roll back `app-web` to its prior SHA so the new UI surfaces are removed; otherwise users see broken forms. Coordinate both rollbacks in the same incident channel.
- **DB**: No destructive migration in this slice that I can see in the AC; if a migration added the `invitations` table, leave it in place (additive, safe to keep on rollback). Confirm with migration history before rolling back code.
- **Comms**: `@bruno` posts in the deploy channel with the rollback SHA and the reason; sets a Datadog monitor mute window so paging doesn't loop.

---

## POST_DEPLOY_PLAN.frontend.md (app-web)

**Slice**: 19 -- Team invitations
**Repo**: app-web (monorepo path: `apps/web/`)
**Deploy SHA**: `a1b2c3d`
**Deploy timestamp**: 2026-06-05T11:30:00Z (MUST be after app-api@8e7d6c5 is verified)
**Environment**: production
**On-call**: `@bruno`
**Observability**: Datadog Logs + APM (RUM if enabled), Sentry (browser project)

### Precondition (do not deploy until all true)

- `POST_DEPLOY_PLAN.backend.md` checks AC-1, AC-2, and the negative check are all green.
- `@bruno` has explicitly confirmed in the deploy channel that `app-api@8e7d6c5` is serving the new routes (not 404).
- If any backend check is red OR ambiguous, hold this deploy. Shipping the frontend against a missing backend is the spurious-failure mode documented in the backend plan and will look like an AC-3/AC-4 code bug when it is actually an ordering bug.

### Per-AC signal mapping

#### AC-3: Team-settings page shows 'Send invitation' form that POSTs and displays returned token

| Signal | Source | Query / check |
|---|---|---|
| Manual smoke | Browser session on `https://app.fhorja.com/teams/<team_id>/settings` | "Send invitation" form is visible; submitting with a valid email returns visible token string in the UI within 2s |
| Network call success | Browser devtools / Sentry breadcrumb | `POST /api/v1/teams/:id/invitations` returns 201; if it returns 404 -> ordering violation, STOP and check backend health |
| Frontend error rate | Sentry (app-web project) | Release `a1b2c3d`, route `/teams/[id]/settings` -- 0 new issues post-deploy |
| Real user signal | Datadog RUM (if enabled) or APM frontend service | Action `submit_invitation_form` success rate > 95% over 15 min |
| Backend correlation | Datadog APM | After manual smoke, confirm the corresponding `POST /api/v1/teams/:id/invitations` span exists in `app-api` with `@http.status_code:201` and matching `team_id` tag |

#### AC-4: `/accept/:token` calls `GET /api/v1/invitations/:token` and renders team metadata

| Signal | Source | Query / check |
|---|---|---|
| Manual smoke | Open `/accept/<token>` in browser using token from AC-3 smoke | Page renders team name, inviter, expires_at; no error boundary triggered |
| Expired-token UX | Open `/accept/<expired_token>` (use token expired via backend AC-2 step) | Page renders an "invitation expired" state, NOT a generic crash; underlying call returns 410 (visible in network tab) |
| Frontend error rate | Sentry (app-web) | Release `a1b2c3d`, route `/accept/[token]` -- 0 new issues post-deploy |
| Backend correlation | Datadog APM | `GET /api/v1/invitations/:token` spans show 200 for valid token smoke, 410 for expired smoke; status distribution sane over first 15 min of real traffic |

### Negative check (proves new web build is live AND backend is wired)

1. Open team-settings page and confirm the "Send invitation" form is rendered (the pre-slice page does not have it). If the form is missing, the CDN/edge has not picked up `a1b2c3d` yet -- wait for cache propagation or invalidate.
2. Confirm app-web build info (footer or `/_meta`) shows commit `a1b2c3d`.
3. Submit one synthetic invitation with a QA email and confirm the **end-to-end loop**: 201 from backend, token rendered in UI, row visible in `invitations` table in PostgreSQL.
4. If the network call returns 404 instead of 201, this is the spurious-failure mode -- do NOT mark AC-3 failed and do NOT roll back the frontend reflexively. Instead, re-check backend health per the backend plan; the likely cause is that `app-api@8e7d6c5` is not actually serving (deploy slipped or rolled back without coordination).

### Rollback (app-web)

- **Trigger conditions**: AC-3 or AC-4 fail with a real frontend bug (form not rendered, render crash, wrong field mapping, token not displayed despite 201 from API); OR Sentry browser shows new high-volume issue tagged `release:a1b2c3d` on `/teams/[id]/settings` or `/accept/[token]`; OR Datadog RUM action success rate < 90%.
- **Do NOT roll back frontend** for 404s on `/api/v1/teams/:id/invitations` or `/api/v1/invitations/:token` until backend has been confirmed live -- that is an ordering bug, not a frontend code bug.
- **Action**: Redeploy previous known-good SHA on `app-web` via standard rollout. The team-settings page returns to its pre-slice state (no invitation form); `/accept/:token` route 404s (pre-slice behavior).
- **Backend coupling on rollback**: Frontend rollback alone is safe -- the backend routes can remain live with no caller. They are additive and do not break anything. No backend rollback is required when frontend rolls back.
- **Comms**: `@bruno` posts rollback SHA and reason in deploy channel; if rollback was triggered by an ordering misdiagnosis, capture the lesson and link this plan's Cross-repo section.

---

## Summary of cross-repo coupling

- Deploy order: `app-api@8e7d6c5` first (11:00:00Z), verify, then `app-web@a1b2c3d` (11:30:00Z).
- AC-3 verification cannot begin until AC-1, AC-2, and the backend negative check are green AND `@bruno` has signed off on the backend deploy.
- The spurious-failure mode (404 -> AC-3 looks broken) is explicitly called out in `POST_DEPLOY_PLAN.backend.md` under Cross-repo and again in the frontend Precondition and Negative check sections so an on-call investigating a red AC-3 immediately checks backend liveness before reaching for a frontend rollback.
- Rollback asymmetry: backend rollback REQUIRES coordinated frontend rollback if the frontend has already shipped; frontend rollback does NOT require backend rollback (new backend routes are additive and harmless when unused).

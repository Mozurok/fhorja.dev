# Routes

> Single source of truth for **route path → screen → persona** mapping. Distinct from `navigation.md` (which owns navigator structure) and `SCREEN_MAP.md` (which indexes all screens with status). The triangle: this file says what URL leads where; `navigation.md` says how the user gets there; `SCREEN_MAP.md` says everything that exists.
>
> Updated whenever a route is added, renamed, or removed.

---

## Route conventions

- Route paths are kebab-case: `/order-detail`, not `/orderDetail`.
- Dynamic segments use bracket notation: `/order/[id]`.
- Personas with separate routes for the same logical screen use prefix: `/operative/home`, `/client/home`.
- Cross-persona shared routes have no prefix: `/settings`.

## Route table

| Route | Screen name | Persona | Auth required? | Deep-link? | Notes |
|---|---|---|---|---|---|
| `/` | Splash | shared | no | no | redirects to `/auth/login` if unauthed |
| `/auth/login` | Login | auth | no | yes | universal entry |
| `/auth/signup` | Signup | auth | no | yes | — |
| `/auth/onboarding/1` | Onboarding Step 1 | auth | post-signup | no | sequential, no direct link |
| `/home` | Home | operative | yes | yes | tab default |
| `/tasks` | Tasks | operative | yes | yes | — |
| `/order/[id]` | Order Detail | operative | yes | yes | id is order UUID |
| `/settings` | Settings | shared | yes | yes | — |
| `/super/users` | User Admin | super-admin | super-admin role | no | role-gated |

## Auth requirement legend

- **no**: public
- **yes**: requires session
- **post-signup**: only reachable mid-onboarding flow
- **<role>**: requires specific role/persona

## Deep-link legend

- **yes**: reachable via universal link / app-link / web URL
- **no**: only reachable from in-app navigation (e.g., onboarding step 2 can't be direct-linked)

## Route → spec doc

For each route, the Notes column should reference `SCREEN_MAP.md` for the spec doc path. To avoid duplication, the spec doc lookup is `SCREEN_MAP.md` → row matching this route + persona.

## Adding a route

1. `screen-spec` creates the screen doc.
2. Add the row here.
3. Add row to `SCREEN_MAP.md`.
4. Update `navigation.md` if the route enters a navigator (tab, modal stack, drawer).
5. Implement in code (e.g., Expo Router file structure).

All four edits happen in the same slice. The `route-doc-drift` bug class (if exists) flags when one of the four lags.

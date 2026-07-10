# Screen Map

> Canonical index of every screen in the product. One row per screen across all `docs/app/screens/<persona>/` folders.
>
> Updated when a screen is added, renamed, deprecated, or has its persona scope changed. The `screen-spec` command appends a row when creating a new screen doc.

---

## Status legend

- **documented**: spec doc exists, code matches spec
- **drafted**: spec doc exists, code not yet built
- **pending**: route reserved, no spec yet
- **deferred**: known need, intentionally postponed
- **deprecated**: scheduled for removal

---

## Index

| Route | Persona | Screen name | Spec doc | Status | Figma frame | Notes |
|---|---|---|---|---|---|---|
| `/auth/login` | auth | Login | `docs/app/screens/auth/login.md` | documented | `<node-id>` | — |
| `/auth/onboarding/1` | auth | Onboarding Step 1 | `docs/app/screens/auth/onboarding-1.md` | drafted | `<node-id>` | — |
| `/home` | operative | Home (Operative) | `docs/app/screens/operative/home.md` | documented | `<node-id>` | — |
| `/home` | client | Home (Client) | `docs/app/screens/client/home.md` | deferred | — | persona variant; pending design |
| `/settings` | shared | Settings | `docs/app/screens/shared/settings.md` | documented | `<node-id>` | shared across personas |
| `/super/admin/users` | super-admin | User Admin | `docs/app/screens/super-admin/users.md` | pending | — | route reserved |

## Counts (per status)

| Status | Count |
|---|---|
| documented | `<N>` |
| drafted | `<N>` |
| pending | `<N>` |
| deferred | `<N>` |
| deprecated | `<N>` |
| **total** | `<N>` |

## Per-persona screen count

| Persona | Documented | Total |
|---|---|---|
| auth | `<N>` | `<N>` |
| shared | `<N>` | `<N>` |
| operative | `<N>` | `<N>` |
| controller | `<N>` | `<N>` |
| client | `<N>` | `<N>` |
| super-admin | `<N>` | `<N>` |

## Sync with routes + navigation

This map is the canonical screen list; `routes.md` is the canonical route → screen mapping; `navigation.md` is the navigator structure (tab bars, modal stack, deep-link rules). The three docs must be consistent — the `screen-spec` command and any route-adding edit should update all three in the same slice.

## How a screen enters the map

1. `screen-spec` creates `docs/app/screens/<persona>/<name>.md` from `_template.md`.
2. The same command appends a row to this map with route, persona, status=`drafted`, Figma node ID.
3. When implementation lands, edit status to `documented` (and check that code/spec match via `design-spec-review`).
4. When deprecated, mark status and add a removal date in Notes; do NOT delete the row until cleanup.

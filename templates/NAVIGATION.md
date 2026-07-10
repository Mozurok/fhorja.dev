# Navigation

> Navigator structure per persona — bottom-tab bars, modal stack, drawer (if used), and deep-link rules. Distinct from `routes.md` (which owns URL → screen mapping) and `SCREEN_MAP.md` (which indexes all screens with status).
>
> When a screen enters a tab bar, modal stack, or deep-link target, this file updates in the same slice as the route.

---

## Bottom-tab structures per persona

### Persona: operative

| Tab | Icon | Route | Default? |
|---|---|---|---|
| Home | `home` | `/home` | yes |
| Tasks | `clipboard-list` | `/tasks` | no |
| Orders | `package` | `/orders` | no |
| Chat | `message-circle` | `/chat` | no |
| Profile | `user` | `/profile` | no |

### Persona: client

| Tab | Icon | Route | Default? |
|---|---|---|---|
| Home | `home` | `/home` | yes |
| ... | ... | ... | ... |

### Persona: controller / super-admin / others

(Repeat structure when applicable.)

## Modal stack

Modals are routes that appear above the tab navigator. They use a separate stack.

| Modal route | Trigger | Dismissable? | Underlying tab? |
|---|---|---|---|
| `/modal/quick-action` | FAB on Home | yes (swipe-down + close) | preserves underlying tab |
| `/modal/order/[id]/edit` | Edit button on Order Detail | yes | preserves Order Detail |
| `/modal/auth/biometric` | App resume after timeout | no (must auth) | locks underlying |

## Drawer (if used)

| Item | Route | Visible to |
|---|---|---|
| `<item>` | `<route>` | `<personas>` |

If drawer is not used, state so: "This product does not use a drawer. All navigation is via bottom tabs + modal stack."

## Deep-link rules

| Pattern | Behavior when authed | Behavior when unauthed |
|---|---|---|
| `app://open/order/[id]` | navigate to `/order/[id]` | stash intent → after login, navigate |
| `app://invite/[code]` | navigate to invite flow | navigate to signup pre-filled |
| `app://share/[token]` | open shared view if permission OK | redirect to login with intent |

Universal links (HTTPS app links) follow the same patterns as deep-link URIs above.

## Stack transitions

| Source → Destination | Transition | Notes |
|---|---|---|
| any → modal | slide-up | use `motion.preset.modal.enter` |
| modal → any | slide-down | use `motion.preset.modal.exit` |
| tab → tab | none (cross-fade if needed) | preserve scroll state |
| within tab stack | push (right-slide iOS, fade Android) | platform default |

## Reduced-motion fallback

When `prefers-reduced-motion` is on, replace slide transitions with cross-fade.

## State preservation

- Tab switches preserve scroll position in each tab.
- Modal dismissal returns to the underlying screen with state intact.
- App backgrounding (>5 min for sensitive screens) triggers biometric re-auth modal.

# Screen: `<NN>-<screen-slug>`

> **Persona(s):** <who sees this screen>
> **Route:** `/<persona>/<path>`
> **Journey:** `<journey-name>` (step N of M)
> **Figma:** `<frame name>` (node ID: `<fileKey:nodeId>`, size: `<W x H>`)
> **Status:** stub | documented | implemented
> **Auth required:** yes | no

---

## 1. Purpose

<What the user does on this screen. 1-2 sentences.>

## 2. Layout sketch

```
+------------------------------------------+
|  [StatusBar]                             |
|  [Header: back + title + action]         |
|------------------------------------------|
|                                          |
|  [Component A: variant]                  |
|  [Component B: variant]                  |
|                                          |
|  [Scrollable content area]               |
|    [Component C]                         |
|    [Component D]                         |
|                                          |
|------------------------------------------|
|  [StickyBottomBar: CTA button]           |
|  [TabBar]                                |
+------------------------------------------+
```

## 3. Spacing observed (from Figma)

| Element | Property | Value | Token |
|---|---|---|---|
| Page gutters | padding-x | 16pt | `spacing.md` |
| Section gap | margin-bottom | 24pt | `spacing.xl` |
| <element> | <property> | <value> | <token> |

## 4. Components used

| Slot | Component | Tier | Variant / Props | Notes |
|---|---|---|---|---|
| Header | Header | organism | `title="<title>" showBack` | |
| CTA | Button | atom | `variant="primary" size="lg"` | full-width |
| <slot> | <name> | <tier> | <props> | |

## 5. Data dependencies

| Source | Endpoint / Event | Data shape | When fetched |
|---|---|---|---|
| REST | `GET /api/<resource>` | `{ id, name, ... }` | on mount |
| WebSocket | `<event-name>` | `{ ... }` | real-time |
| Local state | `<store/context>` | `<shape>` | already loaded |

## 6. Copy (ready for i18n)

| Element | Text | Notes |
|---|---|---|
| Header title | `"<title>"` | |
| CTA label | `"<label>"` | |
| Empty state | `"<message>"` | shown when no data |
| Error state | `"<message>"` | shown on API failure |

## 7. Accessibility notes

- **Screen announcement:** `"<screen title>, <N of M items>"` on focus
- **Focus order:** <describe tab/swipe order top-to-bottom>
- **Dynamic Type:** <which elements scale, which are fixed>

## 8. Interactions

| Gesture / Action | Target | Result | Animation | Haptic |
|---|---|---|---|---|
| tap | CTA button | navigate to `<route>` | press scale 0.97 | Light |
| swipe left | list item | reveal delete action | slide 200ms | Medium |
| pull down | scroll area | refresh data | spring | Light |

## 9. Error states

| Error | Trigger | UI | Recovery |
|---|---|---|---|
| Network error | API call fails | inline alert + retry button | tap retry |
| Validation | form submit with invalid input | field error + shake | fix input |
| Empty | no data returned | empty state illustration + message | pull to refresh |

## 10. Related screens

| Direction | Screen | Trigger |
|---|---|---|
| back | `<NN>-<previous>.md` | back button / swipe |
| forward | `<NN>-<next>.md` | CTA tap |
| modal | `<NN>-<modal>.md` | action button |

## 11. Open questions

<Link to OPEN_QUESTIONS.md entries.>

## 12. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|

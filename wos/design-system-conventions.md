---
activation: glob
description: Design system work (foundations, components, tokens, Storybook, screen documentation).
globs:
  - apps/**/*.tsx
  - apps/**/*.jsx
  - packages/ui/**/*.tsx
  - packages/design-system/**/*
  - docs/research/**/*
  - docs/app/screens/**/*
  - **/*.stories.tsx
  - **/tokens/**/*
---

# Design system conventions (WOS-UI)

> Lazy-loaded Fhorja topic. Load when the task involves design system work (foundations, components, tokens, Storybook, screen documentation, design-to-code alignment). Not needed for backend-only or infrastructure-only tasks.

## When to load this topic

- The task creates or modifies design system components, tokens, or foundations
- The task involves Figma extraction via MCP
- The task documents screens, journeys, or reusable UX patterns
- The task reviews design-to-code alignment (`design-spec-review`, `foundation-audit`)
- The user asks about atomic design, token naming, or component spec structure

## Atomic design hierarchy

Components are organized into four tiers. Each tier builds on the one below:

| Tier | What it contains | Examples | Can contain |
|---|---|---|---|
| **Atom** | Smallest indivisible UI element; a single interactive or decorative unit | Button, Icon, Input, Avatar, Badge, Logo | Only tokens (colors, spacing, typography) |
| **Molecule** | Group of 2+ atoms forming a distinct functional unit | ChatBubble, FormField, MessageInput, NotificationRow | Atoms |
| **Organism** | Complex section composed of molecules and atoms; has its own layout logic | Header, TabBar, MediaViewer, Dialog | Atoms + Molecules |
| **Layout** | Structural container that defines page-level arrangement; holds organisms | BottomSheet, StickyBottomBar, PageShell | Atoms + Molecules + Organisms |

Rules:
- A component's tier is the **highest tier of its children + 1**. A group of atoms is a molecule; a group including a molecule is an organism.
- **Screens are NOT components.** Screens compose components from all tiers into a specific view for a route. Screen docs live in `docs/app/screens/`, not in the component hierarchy.
- Each component has exactly **1 spec doc** (in `docs/research/components/<tier>/`), **1 code directory** (in `packages/design-system/src/<tier>/`), and **1 story file** (in `apps/storybook/stories/<tier>/`).

## Repository structure (docs split)

The design system docs split into two parallel trees with orthogonal purpose:

| Tree | Purpose | Content |
|---|---|---|
| `docs/research/` | Universal patterns + foundations + component research. Reusable across products. Industry-grounded. | Foundations (per area), components by tier (atoms/molecules/organisms/layouts), journeys (cross-screen flows), `COMPONENT_GUIDELINES.md`, `ATOM_AUDIT.md` |
| `docs/app/` | Concrete app composition. Specific to this product. Not reusable. | `routes.md` (URL -> screen -> persona), `navigation.md` (bottom-tab structures, modal stack, deep-link rules), `SCREEN_MAP.md` (index), `screens/<persona>/` |

Mnemonic: a research doc says "this is how Discord builds a chat bubble." A screen doc says "the Chat screen uses `<ChatBubble>` with these props, fetches from this endpoint, navigates here on tap."

Two co-located sub-conventions inside `docs/research/`:

- **`docs/research/_templates/`** -- canonical templates colocated with usage (`COMPONENT.md`, `FOUNDATION_<area>.md`, `JOURNEY.md`). Do NOT centralize design-system templates in the repo-root `templates/` for product work -- templates here are domain-specific and read alongside the actual docs. The repo-root `templates/` keeps the meta-templates that `design-bootstrap` copies into `_templates/` at project init.
- **`docs/research/_inventory/`** -- snapshots of the upstream design source (Figma components inventory, screen list, asset library). Refreshed when design ships new screens. Provides "what does Figma have today vs what we've documented" delta visibility.

Full target structure:

```
docs/
├── research/
│   ├── README.md
│   ├── COMPONENT_GUIDELINES.md
│   ├── ATOM_AUDIT.md
│   ├── _templates/
│   │   ├── COMPONENT.md
│   │   ├── FOUNDATION_<area>.md   (one per foundation area)
│   │   └── JOURNEY.md
│   ├── _inventory/
│   │   ├── README.md
│   │   └── figma_components.md
│   ├── foundations/
│   │   ├── README.md
│   │   └── color.md, typography.md, spacing.md, motion.md, iconography.md,
│   │       grid.md, elevation.md, radii.md, effects.md, states.md
│   ├── components/
│   │   ├── atoms/, molecules/, organisms/, layouts/
│   └── journeys/
└── app/
    ├── README.md
    ├── routes.md
    ├── navigation.md
    ├── SCREEN_MAP.md
    ├── _template.md
    └── screens/<persona>/
```

WOS-UI commands (`design-bootstrap`, `component-spec`, `screen-spec`, `journey-map`, `foundation-audit`, `atom-audit`, `inventory-snapshot`, `extract-foundations-from-screens`) write artifacts targeting these paths. The Traceability rule (below) extends the same split to code: `docs/research/components/<tier>/` <-> `packages/design-system/src/<tier>/` <-> `apps/storybook/stories/<tier>/`.

### Granular foundations (not a single FOUNDATION_SPEC.md)

Foundations are documented **per area** in `docs/research/foundations/<area>.md`, NOT as one monolithic spec. This matches the granularity Figma exposes (each area is typically a Figma variable collection) and lets `foundation-audit` target one area at a time instead of re-auditing everything.

When foundations have not been documented yet but screen specs exist, run `extract-foundations-from-screens` to derive a draft `foundations/<area>.md` set from the foundation observations already captured across screen specs. The command is a bootstrap path, not a replacement for `foundation-audit`.

| File | Scope |
|---|---|
| `color.md` | Brand palette, neutral ramp, semantic state colors, surfaces, tinted overlays, dark mode mapping |
| `typography.md` | Font families, scale, weight, line-height, platform overrides |
| `spacing.md` | Spacing scale, gap/padding/margin tokens |
| `grid.md` | Layout grid, container widths, columns, breakpoints |
| `radii.md` | Border radius scale |
| `elevation.md` | Shadows, surface layers, z-index policy |
| `motion.md` | Animation tokens, easing curves, duration scale, reduced-motion strategy |
| `iconography.md` | Icon library, sizes, semantic mapping |
| `states.md` | Cross-component state vocabulary (default/pressed/focused/disabled/loading/error/empty/offline/selected/skeleton) |
| `effects.md` | Blur, glow, gradient, alpha overlay tokens |

When a product does not use a foundation area (e.g., no `grid` for a mobile-only app), that file is omitted, not stubbed. The `foundations/README.md` lists which areas are documented vs deferred.

## Token naming convention

Tokens follow a **semantic-first** naming strategy derived from Figma variables:

```
<category>.<semantic-group>.<variant>

Examples:
  color.brand.blue          (not: color.blue.500)
  color.text.primary        (not: color.neutral.900)
  color.surface.elevated    (not: color.white)
  spacing.md                (not: spacing.16)
  typography.label.sm       (not: font.12)
  elevation.dialog          (not: shadow.4)
  radius.pill               (not: radius.9999)
```

Rules:
- Semantic names over numeric names. `color.text.primary` reads as intent; `color.neutral.900` reads as implementation.
- Platform-aware overrides: `tokens/typography.ts` (React Native) + `tokens/typography.web.ts` (Storybook/web). Same token names, different values where platforms diverge (e.g., font weight numbers).
- Dark mode: same token names, different values. `color.text.primary` resolves to `neutral.900` in light mode, `neutral.100` in dark mode. The consumer never references mode-specific values directly.

## W3C DTCG token format (target)

New projects should use the W3C Design Token Community Group JSON format (`$value` + `$type` syntax) as the canonical token source. Platform-specific outputs (CSS custom properties, Tailwind config, Swift constants, Android XML) are generated via Style Dictionary transforms.

Starter scaffolds: `templates/TOKEN_FILE.json` (a minimal DTCG token file) and `templates/STYLE_DICTIONARY_CONFIG.md` (a Style Dictionary config skeleton) are manual-use starting points; copy them into the product repo's token pipeline when setting up DTCG tokens. They are reference templates, not artifacts any command auto-generates.

```json
{
  "color": {
    "brand": {
      "blue": {
        "$value": "#0072CE",
        "$type": "color"
      }
    },
    "text": {
      "primary": {
        "$value": "{color.neutral.900}",
        "$type": "color"
      }
    }
  }
}
```

Legacy projects using `.ts` token files can migrate incrementally; the `token-format-not-dtcg` bug class flags files that should be converted.

## States as first-class concern

Every interactive component spec must document **at minimum** these states:

| State | What triggers it | What changes visually |
|---|---|---|
| **default** | Initial render | Base appearance per variant |
| **pressed** | Touch/click down | Background darkens, scale reduces |
| **focused** | Keyboard tab / screen reader focus | Focus ring appears |
| **disabled** | `disabled` prop | Opacity reduced, no interaction |
| **loading** | `loading` prop | Spinner replaces content or label fades |
| **error** | Validation failure / API error | Red border, error message associated |

Additional states (document when relevant):
- **empty**: no data to display (empty list, no results)
- **offline**: device has no network connection
- **selected**: multi-select context (checkbox, radio, chip)
- **skeleton**: loading placeholder before data arrives

## Figma-first derivation principle

Every token and component spec must trace to one of:
1. A Figma variable observed via `get_variable_defs` MCP tool
2. A pattern observed across 3+ component instances in Figma
3. A WCAG or industry-standard requirement (e.g., min tap target 44pt, AAA contrast 7:1 body)

When something is **proposed** (not yet observed in Figma), the spec must mark it as `(proposed)` and link the open question.

## Traceability rule

For each component in the design system, these four artifacts must exist and stay in sync:

| Artifact | Location | Owner |
|---|---|---|
| Spec doc | `docs/research/components/<tier>/<name>.md` | Design phase |
| Code | `packages/design-system/src/<tier>/<Name>/` | Implementation phase |
| Story | `apps/storybook/stories/<tier>/<Name>.stories.tsx` | Implementation phase |
| Figma frame | Linked via node ID in the spec doc | Design tool |

The `storybook-story-missing` bug class detects when code exists without a story. The `design-spec-review` command detects when code diverges from the spec.

## Personas and screen organization

When the product has multiple user roles (admin, regular user, operator, controller, etc.), screen docs organize by **persona** rather than by feature area.

Standard persona vocabulary (extend per product):

| Persona folder | Scope |
|---|---|
| `auth/` | Pre-session screens -- login, signup, onboarding, password reset, biometric setup. Cross-persona by definition. |
| `shared/` | Cross-persona screens reachable from multiple authenticated personas with identical or cosmetic-only differences -- Profile, Settings, Notifications, Deletion, Media viewer |
| `operative/` | Screens scoped to the primary worker/user persona |
| `controller/` | Screens scoped to oversight/management persona |
| `client/` | Screens scoped to external customer persona |
| `super-admin/` | Internal admin screens (back-office) |

Conventions:

- A screen reachable from multiple personas with cosmetic differences only -> put under `shared/` with persona variants documented inline in the same file.
- A screen reachable from multiple personas with **different copy, data, or actions** -> separate files per persona (e.g., `controller/dashboard.md` vs `operative/dashboard.md`), each with a one-line cross-link to the sibling.
- The `screen-spec` command accepts `persona` as a parameter and writes to `docs/app/screens/<persona>/<name>.md`.
- `SCREEN_MAP.md` indexes every screen across all persona folders with route, persona, status (documented / pending / deferred), and the source Figma frame.

When the product has a single persona, skip persona subfolders and place screens flat under `docs/app/screens/`. The `design-bootstrap` command asks for the persona set at project init.

## Audit cadence

The design system has three canonical audit artifacts that get re-generated periodically as the system grows. Audits do NOT implement fixes; they produce machine-scannable tables that drive subsequent slices.

| Artifact | Location | Cadence | Command |
|---|---|---|---|
| **`ATOM_AUDIT.md`** | `docs/research/ATOM_AUDIT.md` | Every 2-4 weeks, or when 5+ new atoms ship | `atom-audit` (or `foundation-audit --tier=atoms`) |
| **`COMPONENT_GUIDELINES.md`** | `docs/research/COMPONENT_GUIDELINES.md` | Updated when a new cross-cutting rule emerges (memo policy, callback shape, inline-style ban, etc.) | manual edit + ADR if rule is normative |
| **`_inventory/figma_components.md`** | `docs/research/_inventory/figma_components.md` | After every Figma library update from design | `inventory-snapshot` |

### `ATOM_AUDIT.md` shape

Table-form: one row per atom, columns per guideline (`memo`, `callbacks`, `inline styles`, `press anim`, `touch target >=44pt`, `a11y`, `reduced motion`, **`changes_needed` count**). Status markers (`v` / `!` / `x`). The table makes "next 5 things to fix" visually scannable in one screen.

### `COMPONENT_GUIDELINES.md` shape

Normative rules common to all components (e.g., "always `memo` if children have >5 props", "callbacks wrapped in `useCallback` with explicit deps", "no inline `style={{}}` -- use `StyleSheet.create`", "every interactive atom respects `prefers-reduced-motion`"). Each rule has a one-line rationale and a bug-class link when one exists.

### When audits drive changes

`atom-audit` produces the table; it does NOT implement fixes. Fixes flow through the normal slice pipeline (`impact-analysis` -> `implementation-plan` -> `implement-approved-slice`) per atom or per guideline group. Multiple atoms violating the **same rule** should be batched into a single slice for context efficiency; multiple atoms with **unrelated issues** stay as separate slices.

## Open questions tracking convention

Each project using WOS-UI should maintain an `OPEN_QUESTIONS.md` with:
- **Prefix IDs** per category: `BRAND-NN`, `AUTH-NN`, `TYPE-NN`, `DESIGN-NN`, `SEC-NN`, `PERF-NN`, `A11Y-NN`, `INFRA-NN` (extend as needed)
- **Triage levels**: blocking (red), affects-implementation (yellow), nice-to-have (green), resolved (check)
- **Resolution pattern**: mark resolved, fill Decision column, link to the spec doc's Decisions section
- **Policy batch resolution**: when a stakeholder provides many decisions at once, document them as numbered policies in a dedicated file (e.g., `CONTROLLER_POLICIES.md`) that atomically resolves multiple questions

Bootstrap from `templates/OPEN_QUESTIONS.md`.

## Accessibility floor

- WCAG 2.2 AA minimum, AAA where reasonable
- Minimum tap target: 44x44 pt (iOS) / 48x48 dp (Android)
- Contrast: 4.5:1 body text, 3:1 large text (AA); 7:1 body (AAA)
- Every interactive element: `role`, `accessibilityLabel` (or visible text), keyboard reachable
- Motion: respect `prefers-reduced-motion` / iOS Reduce Motion; provide instant fallback
- Dynamic Type: text scales with user preference; never truncate with ellipsis on critical labels

## Visual regression testing (operational recommendation)

For projects with a Storybook setup, consider adding Chromatic or a self-hosted Percy instance for automated visual regression testing on every PR. This is NOT a Fhorja command (it is CI/CD infrastructure), but it complements the design system governance provided by `design-spec-review` and the component-level bug classes.

## Versioning convention

Components follow library-wide semantic versioning (semver) in v1. When the design system matures to 20+ consumers, consider per-component semver (Atlassian model). Breaking changes require:
1. An entry in the component spec's `## Decisions` section
2. A migration note in the release changelog
3. A deprecation period of at least 1 minor version before removal

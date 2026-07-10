# Component Guidelines

> Normative rules common to all components in `packages/design-system/src/`. Cross-referenced by `ATOM_AUDIT.md` and per-component specs. Rules are versioned: a new rule requires an ADR entry in the consuming product repo when normative.
>
> **Status:** living document | **Last updated:** `<YYYY-MM-DD>`

---

## Rule format

Each rule has: ID, statement, rationale, scope, bug-class link (if exists).

---

## G-01 — Memoize when children take ≥5 props

**Rule:** Wrap component in `React.memo` when its props arity is ≥5 OR when it renders inside a list (FlatList row, mapped children).

**Rationale:** Re-render cost compounds in lists; memo prevents shallow-equal re-renders. Below 5 props the cost of memo + shallowEqual exceeds the win.

**Scope:** atoms + molecules. Organisms typically have container state and rarely benefit.

**Bug class:** `component-memo-missing` (if exists).

---

## G-02 — Callbacks via `useCallback` with explicit deps

**Rule:** Never pass inline `onPress={() => doX(item)}` to a memoized child. Wrap in `useCallback` with the explicit dep array.

**Rationale:** Inline callbacks break memoization. Explicit deps avoid stale closures.

**Scope:** any component receiving callbacks from a parent that owns list/array data.

**Bug class:** `callback-inline` (if exists).

---

## G-03 — No object-literal `style={{...}}`

**Rule:** Always use `StyleSheet.create({...})` and reference via `styles.x`. Never `<View style={{ padding: 16 }}>`.

**Rationale:** Object literals create a new style object every render → breaks memo + adds work. `StyleSheet` IDs are reused.

**Exception:** dynamic style derived from runtime value (e.g., `{ transform: [{ scale: animatedValue }] }`) — acceptable when the value is a Reanimated shared value or memoized.

**Bug class:** `inline-style-object`.

---

## G-04 — Touch target ≥44pt iOS / 48dp Android

**Rule:** Every interactive element must have a tappable area of at least 44x44 pt (iOS) or 48x48 dp (Android). Compose with padding or `hitSlop` when visual size is smaller.

**Rationale:** WCAG 2.5.5 target size + platform HIG.

**Bug class:** `touch-target-too-small`.

---

## G-05 — Reduced-motion respect

**Rule:** Any animation involving `transform`, `translate`, `scale`, `rotate` must check `useReducedMotion()` and fall back to opacity dip or instant snap.

**Rationale:** Vestibular accessibility; respects user OS setting.

**Bug class:** `motion-not-reduced-motion-safe`.

---

## G-06 — Accessibility roles + labels

**Rule:** Every interactive atom MUST have `accessibilityRole` set; icon-only buttons MUST have `accessibilityLabel`. Decorative elements MUST be `accessibilityElementsHidden={true}` (iOS) / `importantForAccessibility="no"` (Android).

**Rationale:** Screen-reader correctness; auditable via `axe` / built-in tooling.

**Bug class:** `a11y-role-missing`, `a11y-label-missing`.

---

## G-07 — Token-only colors / spacing / typography

**Rule:** Never use raw color values, raw spacing numbers, or raw font sizes in component code. Always reference `tokens.color.*` / `tokens.spacing.*` / `tokens.typography.*`.

**Rationale:** Drift between Figma and code; dark mode breaks if not token-routed.

**Bug class:** `raw-color`, `raw-spacing`, `raw-typography`.

---

## G-08 — Single source per artifact

**Rule:** A component has exactly 1 spec doc (`docs/research/components/<tier>/<name>.md`), 1 code directory (`packages/design-system/src/<tier>/<Name>/`), 1 story (`apps/storybook/stories/<tier>/<Name>.stories.tsx`). Spec name, directory name, and story name must match.

**Rationale:** Traceability. Code without spec = unreviewed component; spec without story = invisible to design review.

**Bug class:** `storybook-story-missing`, `spec-doc-missing`.

---

## Adding a new rule

1. Open a slice via `task-init` with subject `<area>__component-guideline-<short-name>`.
2. Define the rule with the format above; cite at least 2 components affected.
3. Run `impact-analysis` over the consuming codebase.
4. If normative across the system, record as ADR in the consuming repo.
5. Add to this file with next G-NN number.
6. Add to `ATOM_AUDIT.md` columns if the rule is per-component machine-checkable.

## Removing / weakening a rule

Requires `direction-adjust` with rationale (why the rule is wrong or too strict). Old rule kept here with strike-through and ADR link.

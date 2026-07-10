# Atom Component Audit

> **Status:** documented | **Date:** `<YYYY-MM-DD>` | **Tier scope:** atoms only (extend for molecules/organisms as separate audit docs)
>
> Comprehensive audit of all atom components against `COMPONENT_GUIDELINES.md` plus relevant platform/library standards (Apple HIG, Material 3, React Native, Reanimated, etc.).
>
> Produced by the `atom-audit` command (or `foundation-audit --tier=atoms`). The table is the deliverable; fixes flow through normal slice pipeline.

---

## Summary Table

Replace `:check:` / `:warn:` / `:x:` with whatever emoji set lint allows; `:check:` = passing, `:warn:` = acceptable with caveat, `:x:` = needs change.

| Component | memo | callbacks | inline styles | press anim | touch ≥44pt | a11y | reduced motion | changes_needed |
|---|---|---|---|---|---|---|---|---|
| Avatar | :x: | 0 | 2 | N/A | N/A | partial | N/A | 3 |
| Button | :check: | 1 | 0 | :check: (useAnimatedPress) | :check: (52/44/36+hitSlop) | good | :x: (hook missing) | 1 |
| Icon | :x: | 0 | 0 | N/A | N/A | good | N/A | 1 |
| IconButton | :x: | 0 | 1 | :x: (useState transform) | :warn: (32pt sm) | good | :x: | 4 |
| Input | :x: (forwardRef) | 0 | 1 | N/A | :check: (54pt min) | partial | N/A | 3 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Column legend

- **memo**: component wrapped in `React.memo`. `:x:` when missing AND children take ≥5 props (per `COMPONENT_GUIDELINES.md` rule G-01).
- **callbacks**: count of inline arrow/binding callbacks NOT wrapped in `useCallback`. 0 is target.
- **inline styles**: count of `style={{...}}` (object-literal) usages. Use `StyleSheet.create` instead.
- **press anim**: animation primitive used for press feedback. `:check:` for `useAnimatedPress` (Reanimated UI thread); `:x:` for `useState` transform (JS thread).
- **touch ≥44pt**: minimum tap target. `:check:` if meets 44pt iOS / 48dp Android; `:warn:` if smaller but inside larger touchable wrapper with hitSlop; `:x:` if below floor.
- **a11y**: `good` / `partial` / `missing`. Considers `accessibilityRole`, `accessibilityLabel`, `accessibilityState`, focus behavior.
- **reduced motion**: respects `useReducedMotion()` for transforms/translates. `:x:` if motion runs unconditionally.
- **changes_needed**: integer count of fixes derived from the row.

## Fix flow

Audit produces this table; fixes are NOT applied here.

1. Triage the table: group fixes by guideline (e.g., "5 atoms missing reduced motion") → one slice per group.
2. Open a task for each group via `task-init`.
3. Run normal pipeline: `impact-analysis` → `implementation-plan` → `implement-approved-slice`.
4. Update the audit table after each closed slice (re-run `atom-audit` or manual edit).

## Audit history

| Date | Audit run by | Total changes_needed | Cleared since previous run | Notes |
|---|---|---|---|---|
| `<YYYY-MM-DD>` | `atom-audit` v1 | `<N>` | N/A (first) | <one-line context> |

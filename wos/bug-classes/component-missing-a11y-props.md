---
name: component-missing-a11y-props
category: design-system
default-severity: P1
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/design-system/src/**/*.tsx", "**/*.tsx"]
perspectives: [maintainer]
reversibility-check: false
---

# component-missing-a11y-props

## Trigger

An interactive design system component (button, input, link, toggle, select) is implemented without the accessibility props required by the design system conventions: `accessibilityRole` (or `role`), `accessibilityLabel` (or `aria-label`), `accessibilityState` (or `aria-disabled`, `aria-checked`). This makes the component unusable for screen reader users and violates the design system's WCAG 2.2 AA floor.

## Detection

For interactive components in the design system package or app screens:
- Does the root interactive element have `accessibilityRole` or `role`?
- If the component has no visible text (icon-only): does it have `accessibilityLabel` or `aria-label`?
- Does it pass `disabled` state to `accessibilityState` or `aria-disabled`?
- If it is a toggle/checkbox: does it pass checked state to `accessibilityState` or `aria-checked`?

This class overlaps with `missing-aria-label` (which is more general); this one is specific to design system components where the a11y contract is stricter.

## Retrieval

- The component implementation file
- The component spec doc (to check which a11y props are specified)

## Analysis prompt

Given the component:
1. What is its semantic role? (button, textbox, link, switch, checkbox, slider)
2. Does the implementation set `accessibilityRole` / `role` to that value?
3. If icon-only: is there a `accessibilityLabel` / `aria-label`?
4. Does it forward `disabled` to `accessibilityState.disabled` / `aria-disabled`?
5. Does the spec doc list additional a11y requirements (contrast, touch target, Dynamic Type)?

## Severity rubric

- P0: interactive component on a critical flow (auth, payment) missing role AND label (completely invisible to screen readers)
- P1: interactive component missing one of: role, label, or state forwarding
- P2: display-only component missing optional a11y props (decorative image without role="presentation")

## Confidence factors

- HIGH: `<Pressable>` or `<TouchableOpacity>` without `accessibilityRole`; component is interactive
- MEDIUM: component has `accessibilityRole` but not `accessibilityLabel` (may have visible text)
- LOW: component is a wrapper that delegates a11y to children

## Examples

### Positive (missing a11y)

```tsx
export const IconButton = ({ icon, onPress }) => (
  <Pressable onPress={onPress}>
    <Icon name={icon} />
  </Pressable>
);
// No role, no label, no state: screen reader says nothing
```

### Negative (accessible)

```tsx
export const IconButton = ({ icon, onPress, label, disabled }) => (
  <Pressable
    onPress={onPress}
    disabled={disabled}
    accessibilityRole="button"
    accessibilityLabel={label}
    accessibilityState={{ disabled }}
  >
    <Icon name={icon} />
  </Pressable>
);
```

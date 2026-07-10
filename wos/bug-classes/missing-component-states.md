---
name: missing-component-states
category: design-system
default-severity: P1
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx"]
perspectives: [maintainer, operator]
reversibility-check: false
---

# missing-component-states

## Trigger

An interactive component is implemented without handling one or more of the mandatory states defined in the design system conventions (default, pressed, focused, disabled, loading, error). The component works in the happy path but breaks or looks wrong when the user encounters edge cases (slow network, validation failure, disabled form field, keyboard navigation).

## Detection

For each interactive component in the diff (.tsx/.jsx), check:
- Does it accept a `disabled` prop and visually indicate the disabled state?
- Does it accept a `loading` prop (or equivalent) and show a spinner/skeleton?
- Does it handle focus ring for keyboard/screen-reader navigation?
- Does it show an error state when validation fails (red border, error message)?
- Does it handle empty/no-data state if it renders a list or collection?

Compare against the component's spec doc if one exists (`docs/research/components/<tier>/<name>.md`).

## Retrieval

- The component implementation file
- The component spec doc (if it exists)
- The design system conventions (`wos/design-system-conventions.md` states section)

## Analysis prompt

Given the component implementation:
1. Which of the 6 mandatory states are handled? (default, pressed, focused, disabled, loading, error)
2. Which are missing?
3. For each missing state: what would the user experience be? (e.g., no visual feedback on disable; no spinner during async action; no focus ring for keyboard users)
4. Does the component spec doc define additional states (empty, offline, selected, skeleton)?

## Severity rubric

- P0: missing disabled or loading state on a form submit button (user can double-submit or interact with disabled form)
- P1: missing focus or error state on an interactive component (a11y gap or validation gap)
- P2: missing empty or offline state on a data display component (degraded UX but not broken)

## Confidence factors

- HIGH: interactive component (button, input, select) with no `disabled` prop handling and no loading indicator; spec doc defines those states
- MEDIUM: component handles some states but not all; spec doc exists but is draft
- LOW: component is a simple display element (badge, divider) where most states are not applicable

## Examples

### Positive (missing states)

```tsx
const ShareButton = ({ onPress, label }) => (
  <Pressable onPress={onPress}>
    <Text>{label}</Text>
  </Pressable>
);
// No disabled, no loading, no focus ring, no pressed feedback
```

### Negative (states handled)

```tsx
const ShareButton = ({ onPress, label, disabled, loading }) => (
  <Pressable
    onPress={onPress}
    disabled={disabled || loading}
    style={({ pressed }) => [
      styles.base,
      pressed && styles.pressed,
      disabled && styles.disabled,
    ]}
    accessibilityRole="button"
    accessibilityState={{ disabled, busy: loading }}
  >
    {loading ? <Spinner /> : <Text>{label}</Text>}
  </Pressable>
);
```

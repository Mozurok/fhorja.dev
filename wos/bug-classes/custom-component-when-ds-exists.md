---
name: custom-component-when-ds-exists
category: design-system
default-severity: P1
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx"]
perspectives: [maintainer]
reversibility-check: false
---

# custom-component-when-ds-exists

## Trigger

Code creates a custom component (inline styled div/View, ad-hoc button, hand-rolled input) when the project's design system package already exports an equivalent component. Using custom implementations instead of the design system erodes visual consistency, duplicates maintenance burden, and bypasses the a11y/states/motion work baked into the DS component.

## Detection

Look for:
- Components defined inline in a page/screen file that replicate DS component behavior (e.g., a `<div onClick className="bg-blue text-white rounded-lg px-4 py-2">` that is functionally a `<Button>`)
- Custom `styled(View)` or `styled.div` that matches an existing DS atom/molecule
- Imports from a UI library (e.g., `@radix-ui/react-dialog`) when the DS already wraps it (e.g., `@/design-system/Dialog`)
- File creates a `<CustomButton>`, `<StyledInput>`, `<CardWrapper>` when `<Button>`, `<Input>`, `<Card>` exist in the DS

Compare against the design system package exports (`packages/design-system/src/index.ts` or equivalent).

## Retrieval

- The file containing the custom component
- The design system package index (to verify the DS equivalent exists)

## Analysis prompt

Given the custom component:
1. Does the design system export an equivalent? (Check `packages/design-system/src/` or the DS index)
2. Does the custom version handle all the states the DS version handles? (pressed, focused, disabled, loading)
3. Does the custom version include the a11y props the DS version includes? (role, aria-label, touch target)
4. If the DS version is missing a needed variant: recommend extending the DS, not creating a parallel component.

## Severity rubric

- P0: never
- P1: custom component on a user-facing screen that the DS covers (visual inconsistency + a11y gap)
- P2: custom component in an internal/admin screen or prototype

## Confidence factors

- HIGH: DS exports `Button` and code defines `CustomButton` or inline `<div onClick>` with button-like styling
- MEDIUM: DS exports a similar component but not an exact match (custom may be justified)
- LOW: custom component is in a prototype/POC file or test fixture

## Examples

### Positive (DS exists)

```tsx
// packages/design-system exports <Button variant="primary">
// But this screen creates its own:
const SubmitBtn = ({ label, onPress }) => (
  <Pressable onPress={onPress} style={{ backgroundColor: '#0072CE', borderRadius: 26, padding: 12 }}>
    <Text style={{ color: 'white', fontWeight: '600' }}>{label}</Text>
  </Pressable>
);
```

### Negative (DS used)

```tsx
import { Button } from '@/design-system';

<Button variant="primary" size="lg" onPress={handleSubmit}>
  Submit
</Button>
```

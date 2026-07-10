---
name: missing-aria-label
category: accessibility
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx", "**/*.html"]
perspectives: [maintainer]
reversibility-check: false
---

# missing-aria-label

## Trigger

An interactive element (button, link, input, icon button) has no accessible name: no visible text content, no `aria-label`, no `aria-labelledby`, and no associated `<label>`. Screen readers announce it as "button" or "link" with no description, making it unusable for keyboard and assistive-technology users. Violates WCAG 2.1 SC 4.1.2 (Name, Role, Value).

## Detection

Look for:
- `<button>` or `<IconButton>` with only an icon child and no `aria-label`
- `<a href="...">` with only an icon or image child and no `aria-label`
- `<input>` without a `<label>` element or `aria-label` / `aria-labelledby`
- Custom interactive components (`onClick` handler on a `<div>`) without `role="button"` and `aria-label`

## Retrieval

- The component or element definition
- The parent component (to check if a `<label>` is associated via `htmlFor`)

## Analysis prompt

Given the interactive element:
1. Does it have visible text content that serves as its accessible name?
2. If icon-only: does it have `aria-label` describing the action?
3. If custom interactive (`<div onClick>`): does it have `role="button"` + `aria-label` + `tabIndex`?
4. Recommended fix: add `aria-label` with a concise action description.

## Severity rubric

- P0: never
- P1: interactive element on a critical flow (submit, navigation, auth) without accessible name
- P2: interactive element on secondary UI without accessible name

## Confidence factors

- HIGH: `<button>` or `<IconButton>` with only `<SomeIcon />` child and no aria-label
- MEDIUM: `<input>` without visible `<label>` but may have placeholder text (insufficient but partial)
- LOW: element has visible text that may serve as accessible name (context needed)

## Examples

### Positive (inaccessible)

```tsx
<IconButton onClick={() => setShareOpen(true)}>
  <MdOutlineShare />
</IconButton>
```

### Negative (accessible)

```tsx
<IconButton aria-label="Share verification" onClick={() => setShareOpen(true)}>
  <MdOutlineShare />
</IconButton>
```

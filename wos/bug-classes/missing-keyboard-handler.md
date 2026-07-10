---
name: missing-keyboard-handler
category: accessibility
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx"]
perspectives: [maintainer]
reversibility-check: false
---

# missing-keyboard-handler

## Trigger

A non-button element (`<div>`, `<span>`, `<td>`) has an `onClick` handler but no keyboard equivalent (`onKeyDown`/`onKeyPress` for Enter/Space), no `role="button"`, and no `tabIndex`. Keyboard-only and screen-reader users cannot activate the element. Violates WCAG 2.1 SC 2.1.1 (Keyboard).

## Detection

Look for:
- `<div onClick=`, `<span onClick=`, `<td onClick=`, `<li onClick=` without `onKeyDown` or `onKeyPress`
- Non-semantic elements with click handlers missing `role="button"` and `tabIndex={0}`
- Elements using `onPointerDown` or `onMouseDown` without keyboard fallback

Exclude:
- `<button>`, `<a>`, `<input>`, `<select>` (natively keyboard-accessible)
- Elements wrapped in a `<button>` parent (keyboard handled by parent)

## Retrieval

- The component containing the click handler
- The rendered HTML structure (to check if a semantic element wraps it)

## Analysis prompt

Given the click handler on a non-semantic element:
1. Is this element interactive (triggers an action, navigates, opens a dialog)?
2. Can a keyboard-only user reach and activate it?
3. Recommended fix: either (a) replace `<div onClick>` with `<button>` (preferred), or (b) add `role="button"`, `tabIndex={0}`, and `onKeyDown` handling Enter and Space.

## Severity rubric

- P0: never
- P1: interactive element on a critical flow without keyboard access
- P2: interactive element on secondary UI without keyboard access

## Confidence factors

- HIGH: `<div onClick={handler}>` with no role, tabIndex, or onKeyDown; element is clearly interactive
- MEDIUM: element has tabIndex but no onKeyDown (focusable but not activatable)
- LOW: element may be wrapped in a button or have keyboard handling at a parent level

## Examples

### Positive (keyboard-inaccessible)

```tsx
<div className="cursor-pointer" onClick={handleCopy}>
  Click to copy
</div>
```

### Negative (accessible)

```tsx
<button className="cursor-pointer" onClick={handleCopy}>
  Click to copy
</button>
```

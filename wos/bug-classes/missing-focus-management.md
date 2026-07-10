---
name: missing-focus-management
category: accessibility
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx"]
perspectives: [maintainer]
reversibility-check: false
---

# missing-focus-management

## Trigger

A modal, dialog, drawer, or overlay opens without trapping keyboard focus inside it, or closes without returning focus to the element that triggered it. Keyboard and screen-reader users can tab into the background content behind the overlay, lose their place in the page, or be unable to dismiss the overlay via keyboard. Violates WCAG 2.1 SC 2.4.3 (Focus Order) and SC 2.1.2 (No Keyboard Trap).

## Detection

Look for:
- Custom modal/dialog implementations (`<div className="modal">`) without focus-trap logic
- Components that use `position: fixed` or `z-index` overlays without `inert` on background content
- Dialog open handlers that do not call `.focus()` on the first focusable element inside
- Dialog close handlers that do not return focus to the trigger element (`triggerRef.current?.focus()`)

Exclude:
- Radix UI Dialog, Headless UI Dialog, MUI Modal (these handle focus trapping internally)
- `<dialog>` native HTML element with `showModal()` (browser handles focus trapping)

## Retrieval

- The modal/dialog component
- The trigger component (to check if focus return is implemented)

## Analysis prompt

Given the modal/overlay:
1. Is it using a UI library that handles focus trapping automatically (Radix, Headless UI, MUI)?
2. If custom: is there a focus-trap implementation (FocusTrap component, `inert` attribute on background)?
3. When the modal closes, does focus return to the trigger element?
4. Can the modal be dismissed via Escape key?

## Severity rubric

- P1: modal on a critical flow (auth, payment, form submission) without focus management
- P2: modal on secondary UI without focus management

## Confidence factors

- HIGH: custom `<div>` overlay with `onClick` dismiss but no focus trap and no Escape handler
- MEDIUM: uses a UI library but wraps it in a way that might break focus management
- LOW: uses Radix Dialog or native `<dialog>` (focus managed automatically)

## Examples

### Positive (no focus management)

```tsx
{isOpen && (
  <div className="fixed inset-0 z-50 bg-black/50">
    <div className="modal-content">
      <button onClick={() => setIsOpen(false)}>Close</button>
      {/* No focus trap; user can Tab into background content */}
    </div>
  </div>
)}
```

### Negative (accessible)

```tsx
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>{/* Radix handles focus trap + Escape + focus return */}</DialogContent>
</Dialog>
```

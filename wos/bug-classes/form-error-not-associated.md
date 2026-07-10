---
name: form-error-not-associated
category: accessibility
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx"]
perspectives: [maintainer]
reversibility-check: false
---

# form-error-not-associated

## Trigger

A form field displays an error message visually (red text below the input) but the error is not programmatically associated with the input via `aria-describedby` or `aria-errormessage`. Screen readers announce the input without the error context, so visually impaired users do not know what is wrong or how to fix it. Violates WCAG 2.1 SC 1.3.1 (Info and Relationships) and SC 3.3.1 (Error Identification).

## Detection

Look for form patterns where:
- An `<input>` or `<select>` has a sibling or nearby error `<span>` / `<p>` / `<div>` that is conditionally rendered
- The input does not have `aria-describedby` pointing to the error element's `id`
- The input does not have `aria-invalid={true}` when in error state

## Retrieval

- The form component containing inputs + error messages
- The validation logic (to verify when errors appear)

## Analysis prompt

Given the form field and error message:
1. Is the error message programmatically linked to the input via `aria-describedby` and a matching `id`?
2. Does the input have `aria-invalid={true}` when the error is shown?
3. Is the error message announced by screen readers when the user focuses the input?
4. Recommended fix: add `id` to the error element, `aria-describedby={errorId}` to the input, and `aria-invalid` when in error state.

## Severity rubric

- P1: error on a critical form (login, payment, registration) without association
- P2: error on a secondary form (settings, preferences) without association

## Confidence factors

- HIGH: `<input>` followed by conditional `<span className="text-red-500">{error}</span>` without aria-describedby
- MEDIUM: error exists but may be handled by a form library (React Hook Form + Radix) that auto-associates
- LOW: error is a toast/banner, not inline (association not applicable)

## Examples

### Positive (not associated)

```tsx
<Input id="email" value={email} onChange={setEmail} />
{emailError && <span className="text-red-500 text-sm">{emailError}</span>}
{/* Screen reader: "email, edit text" - no mention of the error */}
```

### Negative (associated)

```tsx
<Input id="email" value={email} onChange={setEmail}
  aria-invalid={!!emailError} aria-describedby={emailError ? "email-error" : undefined} />
{emailError && <span id="email-error" className="text-red-500 text-sm">{emailError}</span>}
{/* Screen reader: "email, edit text, invalid entry, Email is required" */}
```

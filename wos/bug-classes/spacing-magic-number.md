---
name: spacing-magic-number
category: design-system
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx", "**/*.css", "**/*.scss"]
perspectives: [maintainer]
reversibility-check: false
---

# spacing-magic-number

## Trigger

Code uses a raw numeric value for padding, margin, gap, or border-radius instead of a spacing/radius token from the design system. Magic numbers cannot be updated globally, drift from the design grid, and make it harder to maintain visual consistency across the app.

## Detection

Look for numeric literals in style props or CSS:
- `padding: 12`, `marginTop: 18`, `gap: 7`, `borderRadius: 8`
- Tailwind arbitrary values: `p-[13px]`, `mt-[18px]`, `rounded-[7px]`
- Values that do NOT align with the project's spacing scale (typically 4pt grid: 4, 8, 12, 16, 20, 24, 32, 40, 48)

Exclude:
- Token definition files themselves
- Values of 0 or 1 (universal)
- Flex ratios (`flex: 1`)
- Dimensions that are component-specific and documented (e.g., icon size 24x24)

## Retrieval

- The file containing the magic number
- The token files (to find the closest spacing token)

## Analysis prompt

Given the magic number:
1. Does a spacing token exist for this value? (Check `tokens/spacing`)
2. If the value does not match any token: is it within 2pt of an existing token? (Likely should round to the token)
3. If no close token exists: should a new token be added, or is this a one-off layout adjustment?

## Severity rubric

- P1: magic number in a reusable component (affects all instances)
- P2: magic number in a screen-specific layout (affects one view)

## Confidence factors

- HIGH: numeric literal in a component's style that is 4+ pt away from any token; component is reusable
- MEDIUM: numeric literal is close to a token value (within 2pt); may be intentional fine-tuning
- LOW: value is in a one-off layout or test fixture

## Examples

### Positive (magic number)

```tsx
<View style={{ padding: 13, marginBottom: 18, borderRadius: 7 }}>
```

### Negative (tokens used)

```tsx
import { spacing, radius } from '@/tokens';
<View style={{ padding: spacing.md, marginBottom: spacing.lg, borderRadius: radius.md }}>
```

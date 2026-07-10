---
name: hardcoded-color-instead-of-token
category: design-system
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx", "**/*.css", "**/*.scss", "**/*.ts"]
perspectives: [maintainer]
reversibility-check: false
---

# hardcoded-color-instead-of-token

## Trigger

Code uses a hardcoded hex/rgb/hsl color value instead of a design token. Hardcoded colors cannot be updated globally when the brand changes, do not adapt to dark mode, and drift from the design system over time.

## Detection

Look for:
- Hex literals in style objects or JSX: `color: '#0072CE'`, `backgroundColor: '#F5F9FD'`
- RGB/HSL in CSS or inline styles: `rgb(0, 114, 206)`, `hsl(207, 100%, 40%)`
- Tailwind arbitrary values: `bg-[#0072CE]`, `text-[#333]`
- CSS custom property bypass: using the raw value instead of `var(--color-brand-blue)`

Exclude:
- Token definition files themselves (`tokens/colors.ts`, `tokens/*.json`)
- Test fixtures and snapshots
- SVG fill/stroke in icon assets (these are typically static)
- Transparent/white/black literals that are truly universal (`#fff`, `#000`, `transparent`)

## Retrieval

- The file containing the hardcoded color
- The token files (to find the matching token name)

## Analysis prompt

Given the hardcoded color:
1. Does a matching token exist? (Search `tokens/colors` for the hex value)
2. If yes: replace with the token reference.
3. If no: should a new token be created, or is this a one-off that does not belong in the DS?
4. Will this color need to change in dark mode? If yes, a token is mandatory.

## Severity rubric

- P1: hardcoded color on a user-facing component that has a DS token equivalent
- P2: hardcoded color in a utility, test, or non-user-facing context

## Confidence factors

- HIGH: hex value matches an existing token value exactly; used in a component's style prop
- MEDIUM: hex value is close to a token but not exact (may be intentional variant)
- LOW: hex value is in a comment, test, or SVG asset

## Examples

### Positive (hardcoded)

```tsx
<View style={{ backgroundColor: '#0072CE' }}>
```

### Negative (token used)

```tsx
import { colors } from '@/tokens';
<View style={{ backgroundColor: colors.brand.blue }}>
```

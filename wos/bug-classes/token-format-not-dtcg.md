---
name: token-format-not-dtcg
category: design-system
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/tokens/**/*.ts", "**/tokens/**/*.js"]
perspectives: [maintainer]
reversibility-check: false
---

# token-format-not-dtcg

## Trigger

Design tokens are defined in TypeScript/JavaScript files instead of the W3C Design Token Community Group (DTCG) JSON format (`$value` + `$type` syntax). Language-specific token files cannot be consumed by Style Dictionary for multi-platform generation (CSS, Tailwind, Swift, Android XML) and require manual synchronization across platforms.

## Detection

Look for token definition files:
- `tokens/colors.ts`, `tokens/spacing.ts`, `tokens/typography.ts` (should be `.json` with DTCG format)
- Files that export plain objects or constants with token values instead of DTCG JSON
- Absence of `*.tokens.json` or `tokens/*.json` files in the project

Exclude:
- Platform-specific OVERRIDES that consume DTCG JSON output (e.g., `tokens/typography.web.ts` that wraps generated values for Storybook)
- Projects that explicitly chose .ts tokens and documented the rationale (check `wos/design-system-conventions.md` or DECISIONS.md)

## Retrieval

- The token definition file(s)
- The project's design system conventions (to check if .ts format is an explicit decision)

## Analysis prompt

Given the token files:
1. Are tokens defined in .ts/.js or in .json (DTCG format)?
2. If .ts: is there a documented rationale for not using DTCG?
3. Would migrating to DTCG JSON enable multi-platform generation via Style Dictionary?
4. If the project is single-platform (web-only or RN-only): the migration priority is lower but still recommended for future-proofing.

## Severity rubric

- P1: multi-platform project (web + mobile) using .ts tokens (manual sync required between platforms)
- P2: single-platform project using .ts tokens (future-proofing concern, not blocking)

## Confidence factors

- HIGH: `tokens/colors.ts` exports plain JS objects; no `.tokens.json` or DTCG JSON exists
- MEDIUM: .ts tokens exist alongside .json tokens (partial migration in progress)
- LOW: .ts tokens are documented as an explicit design decision with rationale

## Examples

### Positive (not DTCG)

```typescript
// tokens/colors.ts
export const colors = {
  brand: { blue: '#0072CE' },
  text: { primary: '#1A1A1A' },
};
```

### Negative (DTCG compliant)

```json
{
  "color": {
    "brand": {
      "blue": { "$value": "#0072CE", "$type": "color" }
    },
    "text": {
      "primary": { "$value": "{color.neutral.900}", "$type": "color" }
    }
  }
}
```

# Foundation: Typography

> **Status:** draft | researched | approved
> **Figma:** `<text styles collection name>`
> **Reference benchmarks:** <Apple HIG, Material 3 type scale, Inter Type Tester>

---

## 1. Scope

Font families, type scale (size), weight scale, line-height scale, letter-spacing, semantic role aliases (display/headline/title/body/label/caption), and platform overrides. Does NOT cover icon sizing (see `iconography.md`).

## 2. Decision (TL;DR)

3-5 lines: font family chosen (primary + fallback), scale system (linear vs modular), weight set, dynamic-type support.

## 3. Font families

| Family | Use | Weights available | Source |
|---|---|---|---|
| `<primary>` | body, UI | 400, 500, 600, 700 | <Google Fonts / system / licensed> |
| `<secondary>` | display | 700, 900 | <source> |

## 4. Tokens — Type scale

| Token | Size | Line-height | Letter-spacing | Use |
|---|---|---|---|---|
| `typography.display.lg` | 32 | 40 | -0.5 | hero headlines |
| `typography.headline.md` | 24 | 32 | -0.3 | section headers |
| `typography.title.md` | 18 | 24 | 0 | card titles |
| `typography.body.md` | 16 | 24 | 0 | primary text |
| `typography.body.sm` | 14 | 20 | 0 | secondary text |
| `typography.label.sm` | 12 | 16 | 0.2 | chips, helper text |
| `typography.caption.xs` | 11 | 14 | 0.3 | metadata |

## 5. Weight tokens

| Token | Weight value |
|---|---|
| `typography.weight.regular` | 400 |
| `typography.weight.medium` | 500 |
| `typography.weight.semibold` | 600 |
| `typography.weight.bold` | 700 |

## 6. Platform overrides

If React Native + Storybook web diverge:

- `tokens/typography.ts` (RN): may use string weights (`'500'`) or numeric (`500`)
- `tokens/typography.web.ts` (Storybook): aligns with browser font-weight numbers
- Same token names, different values where needed; consumers never reference platform-specific files directly.

## 7. Dynamic type / accessibility

- Respect iOS Dynamic Type and Android font scale.
- Never truncate critical labels with ellipsis when the user has scaled up — provide reflow.
- Minimum body size: 14pt (mobile). Avoid using <12pt for anything readable; reserve `caption.xs` for non-critical metadata.

## 8. Research

- Nubank / Coinbase / competitors: type scale observations + what we borrow
- Apple HIG: Dynamic Type integration patterns
- Material 3: type scale role mapping

## 9. How to use

```tsx
import { tokens } from '@design-system/tokens';

const styles = StyleSheet.create({
  title: {
    ...tokens.typography.title.md,
    color: tokens.color.text.primary,
  },
});
```

## 10. Do not

- Hardcode font sizes/weights in components (always go through tokens)
- Mix scales (e.g., custom 17pt between `body.md` and `title.md`)
- Apply weight via raw `fontWeight: '500'` — use `typography.weight.medium` token
- Ignore Dynamic Type by forcing fixed `allowFontScaling={false}` without security/legal reason

## 11. Open questions

- [ ] `TYPE-NN`: <pending>

## 12. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `TYPE-NN` |

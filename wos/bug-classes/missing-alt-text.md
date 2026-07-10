---
name: missing-alt-text
category: accessibility
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/*.tsx", "**/*.jsx", "**/*.html"]
perspectives: [maintainer]
reversibility-check: false
---

# missing-alt-text

## Trigger

An `<img>` element or image component is rendered without an `alt` attribute (or with an empty `alt=""` on a non-decorative image). Screen readers cannot describe the image to visually impaired users, violating WCAG 2.1 Success Criterion 1.1.1 (Non-text Content).

## Detection

Look for:
- `<img` tags without `alt` attribute
- `<img alt="">` on images that convey information (not decorative spacers or backgrounds)
- React `<Image` components (Next.js, etc.) without `alt` prop
- `background-image` used for meaningful content instead of `<img>` with alt

## Retrieval

- The JSX/HTML file containing the image element
- Surrounding context (to determine if the image is decorative or informational)

## Analysis prompt

Given the image element:
1. Is this image decorative (spacer, background pattern, visual flourish) or informational (conveys meaning)?
2. If informational: what alt text would accurately describe the image's content or purpose?
3. If decorative: `alt=""` with `role="presentation"` is the correct pattern (not a bug).

## Severity rubric

- P0: never
- P1: informational image on a critical user flow (navigation, form, onboarding) without alt
- P2: informational image on secondary content without alt

## Confidence factors

- HIGH: `<img src={...}>` with no `alt` prop at all; image appears in a content area
- MEDIUM: `alt=""` on an image that might be informational (context unclear)
- LOW: image is clearly decorative (CSS background, icon next to text label)

## Examples

### Positive (missing alt)

```tsx
<img src={driverPhoto} className="w-12 h-12 rounded-full" />
```

### Negative (accessible)

```tsx
<img src={driverPhoto} alt="Driver profile photo" className="w-12 h-12 rounded-full" />
```

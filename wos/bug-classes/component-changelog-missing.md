---
name: component-changelog-missing
category: design-system
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/design-system/src/**/*.tsx", "**/design-system/src/**/*.ts"]
perspectives: [maintainer, api-consumer]
reversibility-check: false
---

# component-changelog-missing

## Trigger

A design system component's API or visual appearance was changed in a way that affects consumers (prop renamed, variant removed, default behavior changed, visual breaking change), but the component's spec doc `## Decisions` section was not updated to record the change. Consumers (screens, apps) that depend on the old behavior will break or look wrong without warning.

## Detection

When a component in `packages/design-system/src/` is modified in the diff:
- Did the TypeScript interface (props) change? (prop added, removed, renamed, type changed)
- Did a variant name change?
- Did the default value of a prop change?
- Did the visual appearance change significantly (measured by: would Chromatic flag this as a diff)?
- If any of the above: was the component spec doc's `## Decisions` section updated?

## Retrieval

- The component's diff (old vs new props/behavior)
- The component spec doc (`docs/research/components/<tier>/<name>.md` section 15)

## Analysis prompt

Given the component change:
1. What specifically changed in the API or visual behavior?
2. Is this a breaking change for existing consumers? (prop removed or renamed: yes. Prop added with default: no.)
3. Was the spec doc's `## Decisions` section updated to record this change?
4. If breaking: is there a migration path documented for consumers?

## Severity rubric

- P1: breaking change (prop removed, variant renamed) without spec doc update
- P2: non-breaking change (new prop with default, visual refinement) without spec doc update

## Confidence factors

- HIGH: TypeScript interface shows prop removed or renamed in diff; spec doc not modified in the same diff
- MEDIUM: visual change (style modification) that may or may not be breaking; spec doc not updated
- LOW: internal refactor (no API change, no visual change); spec doc update is optional

## Examples

### Positive (missing changelog)

```diff
// Component props changed:
- interface ButtonProps { variant: 'primary' | 'secondary'; }
+ interface ButtonProps { variant: 'filled' | 'outlined'; }
// Spec doc ## Decisions section: not updated
// All screens using variant="primary" will break
```

### Negative (changelog present)

```markdown
## 15. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| 2026-05-25 | Rename variants: primary->filled, secondary->outlined | Align with Material 3 naming | DESIGN-14 |
```

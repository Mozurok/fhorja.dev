---
name: storybook-story-missing
category: design-system
default-severity: P2
cwe: []
languages: [typescript, javascript]
file-patterns: ["**/design-system/src/**/*.tsx", "**/design-system/src/**/*.ts"]
perspectives: [maintainer]
reversibility-check: false
---

# storybook-story-missing

## Trigger

A component is implemented in the design system package (`packages/design-system/src/<tier>/<Name>/`) but has no corresponding Storybook story file (`apps/storybook/stories/<tier>/<Name>.stories.tsx`). Without a story, the component cannot be visually tested, demoed, or documented in the Storybook playground. This breaks the traceability rule (1 spec doc, 1 code dir, 1 story, 1 Figma frame).

## Detection

For each component directory added or modified in `packages/design-system/src/`:
- Check if a corresponding `.stories.tsx` file exists in `apps/storybook/stories/<tier>/`
- The naming convention is: component `src/atoms/Button/` should have story `stories/atoms/Button.stories.tsx`

## Retrieval

- The design system component directory
- The stories directory (to verify absence)

## Analysis prompt

Given the component without a story:
1. Is the component exported from the design system index? (If yes, it needs a story)
2. What variants and states should the story showcase? (Reference the spec doc if it exists)
3. Suggested story structure: default story + one story per variant + interactive controls

## Severity rubric

- P1: component is used in 3+ screens and has no story (high impact, not visually testable)
- P2: component is new or used in 1-2 screens (lower urgency)

## Confidence factors

- HIGH: component exported from index.ts; no file matching `<Name>.stories.tsx` in stories/
- MEDIUM: component exists but may be internal (not exported); story may be optional
- LOW: component is a utility/wrapper with no visual output (story not meaningful)

## Examples

### Positive (missing story)

```
packages/design-system/src/atoms/Avatar/Avatar.tsx  (exists)
apps/storybook/stories/atoms/Avatar.stories.tsx     (does NOT exist)
```

### Negative (story exists)

```
packages/design-system/src/atoms/Avatar/Avatar.tsx  (exists)
apps/storybook/stories/atoms/Avatar.stories.tsx     (exists)
```

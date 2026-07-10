# OPEN_QUESTIONS

> Centralized backlog of unresolved questions for this project's design system. Each question has a prefix ID, triage level, and resolution tracking.

## Triage levels

- 🔴 **Blocking**: cannot proceed with implementation until resolved
- 🟡 **Affects implementation**: can proceed but the answer will change the implementation
- 🟢 **Nice-to-have**: does not block or change implementation; improves polish
- ✅ **Resolved**: answered; decision recorded in the relevant spec's `## Decisions` section

## ID prefixes

Extend as needed for your project. Common prefixes:

| Prefix | Category |
|---|---|
| `BRAND-NN` | Brand identity (colors, logo, typeface) |
| `AUTH-NN` | Authentication and onboarding |
| `NAV-NN` | Navigation and routing |
| `TYPE-NN` | Typography and text |
| `DESIGN-NN` | General design decisions |
| `SEC-NN` | Security and privacy |
| `PERF-NN` | Performance |
| `A11Y-NN` | Accessibility |
| `INFRA-NN` | Infrastructure and tooling |

## Questions

| ID | Question | Source | Foundation / Spec | Priority | Status | Decision |
|---|---|---|---|---|---|---|
| `<PREFIX-NN>` | `<the question>` | `<where it came from>` | `<which spec it affects>` | 🔴 / 🟡 / 🟢 | open / resolved | `<answer, if resolved>` |

## Resolution process

1. When a question is answered, set Status to `resolved` and fill the Decision column.
2. Copy the decision to the relevant spec doc's `## Decisions` section with the question ID.
3. When a stakeholder provides many decisions at once, document them as numbered policies in a separate file (e.g., `CONTROLLER_POLICIES.md`) and mark all resolved questions atomically.

## Summary

| Level | Count |
|---|---|
| 🔴 Blocking | 0 |
| 🟡 Affects implementation | 0 |
| 🟢 Nice-to-have | 0 |
| ✅ Resolved | 0 |
| **Total** | **0** |

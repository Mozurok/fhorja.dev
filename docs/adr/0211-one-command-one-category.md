# ADR-0211: Fifteen categories, because two of them held 56 commands

- **Status**: Accepted
- **Date**: 2026-09-18
- **Supersedes**: ADR-0029 (the nine-value canonical category set, not the registry-drift guard that names it)
- **Tags**: command-categories, catalog, navigation, readme, adr-0029

## Context

`metadata.category` had nine values. Measured 2026-09-18, two of them carried 56 of the 98
commands: `discovery-and-scoping` 31 and `execution-and-closure` 25. At the other end,
`prompt-tooling` held one command and `project-initialization` two.

Thirty-one commands under one heading is not a grouping. `discovery-and-scoping` held Figma
component specs, GraphQL contract review, Godot scene planning, external library research and
problem framing, which share a lifecycle position and nothing else.

This is not an internal concern. `scripts/build-command-catalog.py` groups
`docs/command-catalog.html` and the README's `## Command catalog` by this exact field, so the
coarse axis IS what a reader navigates. `README.md` `## Command clusters` already offered a
better-shaped 15-family editorial table, and a reader moving from it to the catalog fell from the
good grouping to the coarse one.

The spec disagreed with the field as well: `## Command categories` carried a `Design system
(WOS-UI)` heading that was never a `metadata.category` value, so the two registries had already
drifted by one group.

## Decision

The canonical set is fifteen values. Six are new: `research-and-sourcing`, `design-and-ui`,
`game-and-engine`, `runtime-verification`, `audit-and-sweep`, `autonomy`.
`contract-and-decision-hardening` becomes `contracts-and-decisions` and absorbs the two API
contract commands that sat in discovery.

Forty-six commands move. The largest category becomes `state-and-navigation` at 14.

The two axes stay separate and the docs now say why. A category is single-membership and answers
where a command sits in the lifecycle. A README cluster is multi-membership and answers what family
a command belongs to: `app-runtime-verify` is an execution gate and the Unity surface, and one
value cannot carry both. Collapsing them would force a choice that neither question needs.

## Consequences

### Positive

- The navigable surface matches the shape of the corpus. The catalog, the spec section, the prompt
  stubs and the README all read from this field, so one change moved all four.
- Two long-standing drifts close: the spec's `Design system (WOS-UI)` heading is now a real
  category value, and the README's claim about a nine-category boundary is no longer stale.

### Negative

- A category rename is a vocabulary change a reader may have memorised, and there is no redirect
  from `contract-and-decision-hardening` to its new name. Two eval scenarios carried a category as
  a tag (`82-godot-scene-plan`, `83-godot-runtime-verify`) and were retagged to `game-and-engine`
  in the same change. Nothing asserts that a scenario tag naming a category is a live value, so
  the next rename will need the same manual sweep.
- Fifteen is more to hold than nine. The floor for adding a sixteenth should be the one applied
  here: a category exists when a reader would otherwise scan an undifferentiated list.

### Neutral

- No command changed behavior, no pipeline moved, and no routing reads this field. It is a
  navigation label, which is why a 46-command move is a safe change rather than a risky one.

## Alternatives considered

### Alternative 1: add a second frontmatter axis for the family, keeping nine categories

- Rejected as disproportionate for now. It would touch all 98 commands, add a canonical set and a
  lint rule, and give the catalog two views. The measured problem was 56 commands in two buckets;
  the cross-cutting families it would capture are 7 fleet variants and a handful of engine
  commands. Worth revisiting if the editorial table and the categories drift again.

### Alternative 2: promote the README's 15 editorial clusters to be the categories

- Rejected. They are multi-membership by design. Forcing them single would either duplicate
  commands across categories, which the lint's one-value field cannot express, or silently drop a
  command from a family it belongs to.

## References

- [ADR-0029](./0029-drift-guards-registry-and-count-markers.md): the registry and count-marker
  guards that keep the four surfaces in step; this ADR changes the values, not the guards.

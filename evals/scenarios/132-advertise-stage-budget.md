# Eval scenario 132: the Advertise stage stays under its aggregate budget

- **Tags**: ADR-0135, advertise-stage, context-budget, skill-descriptions, structural
- **Last reviewed**: 2026-08-10
- **Status**: active

## Goal

The Advertise stage is every generated skill's frontmatter `description`, injected into
every run before any skill body is loaded. It is the largest always-on context surface in
the repository and, until ADR-0135, the only one with no aggregate gate: lint caps each
description at 1,024 chars, and 98 of those caps allow 100,352 chars with nothing firing
until each one individually crosses.

## Automated half

`evals/scripts/structural-evals.py` check `advertise-stage-budget`. It sums the
`description` of every `.claude/skills/*/SKILL.md` and fails above 21,000 tokens
(84,000 chars), the no-regression ceiling ADR-0135 set just above the 20,233 tokens
measured on 2026-08-09.

The check is path-parameterized (`root=`) so it can be proven against a fixture. This is
not decoration: the descriptions are YAML BLOCK scalars, and a parser written for the
single-line shape returns the `|-` indicator and reports about 2 chars per skill, which
looks like a valid passing run. The gate was proven RED on a 90-skill fixture totalling
90,000 chars before being trusted GREEN on the real corpus.

## Manual half

Read three descriptions end to end and ask whether each still tells a model what the
skill does and when to pick it. The budget is a byte count and cannot see routing quality;
ADR-0135 records the absence of any routing check as OPEN, and D-3 of the task that
introduced it deferred building one.

## Pass criteria

- The check fails on a fixture whose descriptions exceed the budget, naming the measured total.
- The check passes on `.claude/skills/`.
- A description that grows past the aggregate budget turns CI red, not warn-only.

## FAIL conditions

- The check passes on a fixture whose descriptions exceed the budget. That means the parser is not reading the block scalar, and a parser that reads nothing returns zero, which passes any budget.
- The check is added as warn-only rather than a hard failure, which reproduces the asymmetry ADR-0135 exists to close.
- The budget is raised to accommodate growth without a recorded decision, turning a no-regression ceiling into a moving one.
- A description is trimmed to fit the budget with no evidence that it still routes. ADR-0135 records the absence of a routing check as OPEN; trimming before that check exists is the failure this scenario's manual half is for.

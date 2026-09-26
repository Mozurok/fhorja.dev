# BRIEF

Transient, task-scoped intake brief written by `problem-framing` at `projects/<client>__<project>/BRIEF.md` before the task exists. `task-init` reads this file, seeds `SOURCE_OF_TRUTH.md` and the `## Requested deliverables` ledger from it, then moves it into the new task folder. Five fields, one page. Per ADR-0058.

A field pre-filled from a supplied spec names its source (file plus section) beside the value. A field filled from a dispatching brief in an unattended run carries the note "from the dispatching brief"; a field nobody supplied stays `[NEEDS CLARIFICATION: <the question>]` rather than a guess.

## Problem statement
[One present-tense sentence naming what goes wrong without this work. Not a solution.]

## Success criteria
[User-observable, measurable outcomes that mean the problem is solved. Bullet list.]
- [criterion 1]
- [criterion 2]

## Non-goals / out of scope
[What this work deliberately does not do, so scope stays honest.]
- [non-goal 1]

## Recommended approach
[The chosen one of the 2-3 approaches considered, with the one-line trade-off that made it the pick. Name the alternatives considered.]

## Named deliverables
[The concrete things the user asked for by name. These seed task-init's `## Requested deliverables` ledger (ADR-0056), so each must be a discrete artifact or input, not an implied sub-task.]
- [deliverable 1]
- [deliverable 2]

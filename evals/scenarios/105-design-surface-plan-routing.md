# Eval scenario 105: implementation-plan routes a user-facing visual surface through the design cluster before slicing

- **Tags**: F1, ADR-0099, implementation-plan, design-cluster, frontend, reference-grounding, site-dogfood, capability-routing
- **Last reviewed**: 2026-07-12
- **Status**: active

## Goal

Validates the F1 rule from the fhorja.dev site dogfood: when a task deliverable is a user-facing visual surface, `implementation-plan` routes through the applicable design-cluster commands and grounds the visual direction in captured references BEFORE slicing the visual build, rather than slicing raw sections straight away. The site dogfood failed here: the plan went straight to building sections, the frontend cluster went unused, and the first build was "muito pobre e sem graça," fixed only through repeated human elevation loops. The rule is capability-routed: a surface with no visual-design intent does not fire it.

## Setup

An active task whose objective is to build a public landing page (a user-facing visual surface). `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, and `DECISIONS.md` exist; impact is understood enough to plan. No design-cluster artifact (no SCREEN_SPEC, no design references captured for the visual direction) exists yet, and the deliverable is not yet tagged. A second variant: the same command on a task whose only deliverable is an internal admin CRUD form with no visual-design intent.

## Input prompt

```text
/implementation-plan
```

## Expected behavior

- Visual-surface variant: before emitting visual-build slices, the plan detects that the deliverable is a user-facing visual surface (by a `user-facing-content` / `new-user-facing-surface` tag, or plainly from the deliverable) and routes to the applicable design-cluster commands (some of `screen-spec`, `journey-map`, `design-bootstrap`, `image-to-spec`, `component-spec`, `a11y-audit`, `color-contrast-architect`) and to `capture-references` for the visual direction. If the plan would slice the visual surface with neither a design-cluster consultation nor reference grounding, it names the missing design step in `### Command transcript` and routes to it rather than silently slicing.
- Every routed-to command name is a real `commands/<name>.md` basename.
- Internal-CRUD variant: the rule does not fire; the plan slices normally with no design-cluster detour, because the deliverable has no visual-design intent. The command does not manufacture a design phase for a non-visual surface.

## FAIL conditions

A FAIL is: the visual-surface variant slices the visual build with no design-cluster routing and no reference grounding and without flagging the gap (the historical failure this scenario exists to catch); the plan invents a design command name that is not a real basename; the plan hard-blocks and refuses to produce any plan (the rule is flag-and-route, not a hard block); or the internal-CRUD variant manufactures a design-cluster detour for a surface with no visual-design intent (over-firing).

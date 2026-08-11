# Eval scenario 128: the web and backend runtime-gate floors block closure without a cited verify PASS, and a hand-rolled battery does not substitute

- **Tags**: ADR-0127, web-runtime-verify, api-runtime-verify, runtime-gate, web-runtime-target, http-runtime-target, closure-enforcement, slice-closure, implement-approved-slice, task-close, generalizes-adr-0106, dogfood-driven
- **Last reviewed**: 2026-08-06
- **Status**: active

## Goal

Validates the ADR-0127 web and backend runtime-gate floors: a slice or task carrying `web-runtime-target` (or matching the heuristic backstop, a servable frontend surface in a project whose manifest declares a web build or preview script) reaching any of the three closure homes without a cited `web-runtime-verify` PASS or an explicit skip reason is blocked and routed to `web-runtime-verify`; the same for `http-runtime-target` and `api-runtime-verify`. The load-bearing variant is the one the Kimi dogfood produced: a slice that ran an equivalent battery BY HAND inside `implement-approved-slice` and pasted real, green output still does not satisfy the floor.

## Setup

An active task building a static Astro landing page whose acceptance criteria are all web-runtime (no horizontal overflow 320 to 2560, keyboard and focus, zero console errors, Lighthouse mobile). `package.json` declares `build` and `preview` scripts. The final slice's scope touches `src/pages/`, `src/components/` and `src/styles/`. Sub-cases:

1. The slice reaches the `implement-approved-slice` inline-close path with no runtime verification of any kind.
2. The same slice, but its notes paste real output from a hand-written Playwright script plus a Lighthouse run performed inside the implementing command, with no `web-runtime-verify` invocation and no `WEB_RUNTIME_VERIFY.md`.
3. A HIGH complexity slice routed to `slice-closure` with no cited PASS.
4. The whole task reaching `task-close` with that slice as its only servable-surface slice.
5. A backend variant: a slice whose scope touches an HTTP route handler on a task tagged `http-runtime-target`, reaching inline-close with the route's response reasoned about but never probed.
6. A stand-down variant: the same web-shaped slice on a task carrying the Godot signature (a `project.godot` file present).

## Input prompt

```text
/implement-approved-slice
```
(sub-cases 1, 2 and 5; analogous `/slice-closure` for 3 and 6, `/task-close` for 4)

## Expected behavior

- Sub-case 1: the slice does NOT close inline. The command names the missing `web-runtime-verify` PASS or skip reason and routes to `web-runtime-verify` before any next-slice or fleet routing decision.
- Sub-case 2: the slice STILL does not close inline. The hand-rolled battery is named as not satisfying the floor, with the reason stated: `web-runtime-verify` owns the serving discipline (`wos/frontend-preview-and-experience-verdict.md ## Serving discipline (both consumers)`), and a per-session reimplementation is what re-derives the wrong-page failure. Green pasted output is not accepted as a substitute verdict.
- Sub-case 3: the slice is classified `not ready to close`, names the missing evidence, and routes to `web-runtime-verify`. A passing `npm run build` is explicitly named as insufficient on its own.
- Sub-case 4: the task is NOT archived. The gate decision is `blocked`, naming the web-runtime-gate floor and routing to `web-runtime-verify`.
- Sub-case 5: the same three-way outcome against `api-runtime-verify`; a route whose response was reasoned about rather than probed is reported unverified, never PASS.
- In every sub-case, a cited BLOCKED verdict from the verify command is treated as an absent PASS, quoted verbatim and worded distinctly from "never attempted"; and a skip reason worded as "no browser is ever available in this environment" is a permanent skip per ADR-0098 and does NOT satisfy the floor, while a bounded deferral (a specific later checkpoint, or a slice with no servable surface) does.
- Sub-case 6: the web floor stands down in favor of the Godot D-4 feel-verdict floor; the two families are never both live on the same task.
- Across all sub-cases, a `web-runtime-verify` PASS is stated as Layer-1 evidence only and never as satisfying the ADR-0091 human experience verdict, which runs over the same served build.

## FAIL conditions

A FAIL is: any of the three closure homes lets a web- or HTTP-surface slice close with no cited verify PASS and no skip reason (the Kimi-dogfood failure this scenario exists to catch); a hand-rolled battery inside `implement-approved-slice` is accepted as satisfying the floor in sub-case 2; a passing build, typecheck, or lint is accepted as substitute evidence; a "no browser ever" skip is accepted (violates ADR-0098); a cited BLOCKED verdict is treated as a skip reason; the floor fires on the Godot variant instead of standing down; the floor fires on a docs-only or config-only slice, or in a repository whose manifest declares no web build or preview script (the heuristic is deliberately narrow); or the routed-to command is named as anything other than `web-runtime-verify` / `api-runtime-verify`.

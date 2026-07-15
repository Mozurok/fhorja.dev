# Eval scenario 107: the mobile-runtime-gate floor blocks closure of a mobile-tagged slice without a cited app-runtime-verify PASS or skip

- **Tags**: ADR-0106, app-runtime-verify, runtime-gate, mobile-runtime-target, closure-enforcement, slice-closure, implement-approved-slice, task-close, mirrors-adr-0085, dogfood-driven
- **Last reviewed**: 2026-07-15
- **Status**: active

## Goal

Validates the ADR-0106 mandatory mobile runtime-gate floor: a task or slice carrying the `mobile-runtime-target` tag, or matching the heuristic backstop (an `expo`/`react-native` dependency plus a generated `android/`/`ios/` folder), reaching any of the three closure homes (`slice-closure`, the `implement-approved-slice` inline-close path, `task-close`) without a cited `app-runtime-verify` PASS or an explicit skip reason is blocked and routed to `app-runtime-verify`. A second variant confirms the floor stands down on the Godot task signature in favor of the existing Godot-specific floors (ADR-0085, ADR-0089 D-4).

## Setup

An active task implementing a React Native/Expo Face ID biometric flow (a `mobile-runtime-target` tag on the slice; `package.json` lists `expo` and `react-native`; a generated `android/` folder is present). The slice is implemented and typecheck-clean (`tsc --noEmit` exits 0), with no `app-runtime-verify` run ever cited and no skip reason recorded. Three sub-cases exercise the three closure homes:

1. LOW complexity slice reaching the `implement-approved-slice` inline-close path.
2. HIGH complexity slice routed to `slice-closure`.
3. The whole task reaching `task-close` with this slice as its only runtime-observable slice.

A fourth variant: the same command on a task carrying the Godot task signature (a `project.godot` file present) that also happens to touch a `mobile-runtime-target`-style surface, to confirm exclusive routing.

## Input prompt

```text
/implement-approved-slice
```
(sub-case 1; analogous prompts `/slice-closure` and `/task-close` for sub-cases 2 and 3, and `/slice-closure` on the Godot-signature task for the stand-down variant)

## Expected behavior

- Sub-case 1 (inline-close): the slice does NOT close inline. The command classifies it not-ready, cites the missing `app-runtime-verify` PASS or skip reason, and routes to `app-runtime-verify` before any next-slice or fleet routing decision.
- Sub-case 2 (slice-closure): the slice is classified `not ready to close`, names the missing evidence, and routes to `app-runtime-verify`. Typecheck-clean status is explicitly named as insufficient on its own.
- Sub-case 3 (task-close): the task is NOT archived. The gate decision is `blocked`, naming the mobile-runtime-gate floor as the blocking condition and routing to `app-runtime-verify`.
- In all three, a skip reason worded as "no device or emulator is ever available in this environment" is recognized as a permanent skip per ADR-0098 and does NOT satisfy the floor; the slice/task stays not-ready pending a session where a run is possible. A skip reason worded as a bounded deferral (a specific later checkpoint, or a real device session the human will run shortly) DOES satisfy the floor at the same low ceremony, as does a real cited `app-runtime-verify` PASS.
- Godot-signature variant: the mobile-runtime-gate floor stands down. The command defers to the existing Godot-specific floors (ADR-0085 runtime-gate, ADR-0089 D-4 feel-verdict) instead of firing this floor a second time; the two families are never both live on the same task.

## FAIL conditions

A FAIL is: any of the three closure homes lets the mobile-tagged slice or task close/archive with no cited `app-runtime-verify` PASS and no skip reason (the exact rn-reference-app failure this scenario exists to catch); the floor accepts `tsc --noEmit` or grep-based checks as substitute evidence; a "no device ever available" skip reason is accepted as satisfying the floor (violates the ADR-0098 bounded-vs-permanent rule); the floor fires on the Godot-signature variant instead of standing down; or the routed-to command is named as something other than `app-runtime-verify`.

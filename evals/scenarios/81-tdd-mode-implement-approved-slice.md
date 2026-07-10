# Eval scenario 81: opt-in TDD mode runs a slice red-then-green, off by default

- **Tags**: ADR-0063, ADR-0031, tdd, test-first, implement-approved-slice, presence-gated, opt-in, regression-guard
- **Last reviewed**: 2026-06-27
- **Status**: active

## Goal

Validates **ADR-0063**: `implement-approved-slice` supports an opt-in test-first mode (enabled per slice via `Test-first: yes` or ad hoc via `--tdd`) that writes the failing test encoding the slice's EARS exit criterion BEFORE the production code, and is off by default so the normal flow is unchanged.

This exercises:

- Default-off: a slice with neither `Test-first: yes` nor `--tdd` runs the normal implement-then-validate flow with no TDD ceremony.
- Red-then-green order: when enabled, the failing test is written and run first (RED), then the smallest in-scope code makes it pass (GREEN), with both outputs pasted as the Layer 1 evidence.
- The red proof is honest: the test fails for the intended (not-yet-built) behavior, not from a compile, import, or collection error.
- Presence gate (ADR-0027): with no test runner in the consuming repo, the mode does not scaffold one; it says so and falls back (or routes to `test-strategy`).
- Not-applicable fallback: a pure config/copy/docs slice makes TDD a NO_OP rather than inventing a hollow test.

## Setup

An approved slice with a logic-bearing EARS exit criterion in a repo that has a test runner, invoked once with the default flow and once with `--tdd` (or `Test-first: yes` in the plan).

## Expected behavior

- WHEN neither trigger is set, the slice runs the normal flow; no test-first sequencing is imposed.
- WHEN `--tdd` or `Test-first: yes` is set and the slice has testable behavior, the output shows the failing test first with its RED run output, then the minimal code change with its GREEN run output, both inside the declared `Scope`; the red-green transition is recorded as the exit-criterion evidence.
- WHEN no test runner exists, the run notes the missing runner, does not scaffold one, and falls back to the normal flow or routes to `test-strategy`.
- WHEN the slice has no testable behavior, the run states TDD is a NO_OP for that slice and proceeds normally.

## Failure modes (a FAIL looks like)

- Imposes TDD on a slice with neither trigger set (mode must be opt-in / off by default).
- Writes the production code first and the test after while claiming test-first, or pastes only a green run with no failing-first (red) output.
- Reports a RED that fails from a compile/import/collection error rather than the asserted behavior, then calls it a valid red.
- Scaffolds a test runner or framework that the consuming repo does not already have (violates the presence gate).
- Manufactures a hollow test for a pure config/docs slice instead of treating TDD as a NO_OP there.

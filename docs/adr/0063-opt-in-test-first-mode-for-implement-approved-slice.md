# ADR-0063: Opt-in test-first (TDD) mode for implement-approved-slice

- **Status**: Accepted
- **Date**: 2026-06-27
- **Tags**: tdd, test-first, implement-approved-slice, execution, ears, presence-gated, opt-in, ecosystem-adoption, additive

## Context

The 2026-06-26 ecosystem research flagged a test-first habit across several Claude Code workflows (Superpowers' red-green discipline, Taskmaster's per-task test notes). The WOS already encodes per-slice exit criteria in EARS form (ADR-0031: `WHEN <trigger> the <system> SHALL <outcome>`), but the execution command (`implement-approved-slice`) implements the code first and validates after. The failing test that would prove the EARS criterion is never required to exist before the code, which permits a confirmation-bias failure mode: a test written to match code that already exists, asserting what the code happens to do rather than what the criterion demanded.

## Decision

Add an opt-in test-first mode to `implement-approved-slice`, OFF by default. Enable it per slice with `Test-first: yes` in that slice's `IMPLEMENTATION_PLAN.md` entry, or ad hoc with a `--tdd` input. When enabled for a slice with testable behavior, execution follows the red-green order:

1. **Red.** Write the failing test that encodes the slice's EARS exit criterion before any production code; run it and paste the RED output showing it fails for the intended reason (the not-yet-built behavior), not from a compile, import, or collection error.
2. **Green.** Write the smallest production change that makes the test pass, staying inside the declared `Scope`; run it and paste the GREEN output.
3. **Refactor (optional).** Tidy only within scope while the test stays green; the no-orthogonal-changes rule still holds.

The red-then-green transition is the Layer 1 validation evidence for the behavior under test, satisfying the exit-criterion proof rather than supplementing it. The mode is presence-gated (ADR-0027): it needs a test runner already present in the consuming repo and never scaffolds one here. A slice with no testable behavior (pure config, copy, or docs) makes the mode a NO_OP and falls back to the normal flow rather than inventing a hollow test. Strict operating mode may recommend test-first for logic-bearing slices but never forces it.

Opt-in rather than default is deliberate: forcing TDD on every slice (including config, docs, and the markdown-plus-bash slices typical of this very repository) would add ceremony and manufacture meaningless tests, which contradicts the WOS YAGNI and anti-ceremony stance. The trigger stays in the user's and the plan's hands.

## Consequences

- No `count:commands` change: this is a mode of an existing command, not a new command. It adds ADR-0063 (filling the slot reserved in the round-4 plan) and eval scenario 81; `count:adrs` rises 62 -> 63 and `count:scenarios` 80 -> 81.
- The EARS exit criterion (ADR-0031) gains an execution path that proves it with a failing-first test, not only an after-the-fact assertion.
- Additive: the default implement-then-validate flow is unchanged, and the existing evidence paths (the deterministic gate of ADR-0048 and the W-02 paste-the-command-and-output rule) remain in force for non-TDD slices.
- The mode composes with the rest of the slice contract (declared `Scope`, no orthogonal changes, YAGNI restraint, the slice completion check); it changes the ORDER of test-versus-code, not the slice format.

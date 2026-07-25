# Eval scenario 116: the Load-stage size gate is a hard CI failure

- **Tags**: ADR-0116, context-engineering, token-budget, load-stage, progressive-disclosure, lint-enforced-hard-fail, supersedes-adr-0013, structural
- **Last reviewed**: 2026-07-25
- **Status**: active

## Goal

Validates **ADR-0116** (one enforced size budget at the Load stage; retires the ADR-0013 per-command `metadata.token-budget` field): `evals/scripts/structural-evals.py::check_skill_load_budget()` fails the CI `structural-evals` job when a generated `.claude/skills/<name>/SKILL.md` exceeds the 10000-token (40000-char) no-regression ceiling, and `check_no_retired_frontmatter_field()` fails it when the retired field survives in a command frontmatter, a generated skill, or `scripts/lint-commands.sh`. This is a structural scenario: unlike scenarios 113-115, which a human reads against a model's prose output, this one is exercised by running the check functions directly, per TEST_STRATEGY.md scenarios S-3 and S-4.

This exercises:

- The gate fires: a generated skill over the ceiling makes `check_skill_load_budget()` return a failure naming the offending skill, its measured size, and the ceiling.
- The gate is path-parameterized, not hardcoded to the real corpus: `check_skill_load_budget(root=...)` accepts an arbitrary fixture directory, so the failing case above can be produced without touching `.claude/skills/`.
- The gate is clean over the real corpus: called with no argument (the default, real `.claude/skills/` path), every one of the 95 generated skills passes today, because the ceiling was set just above the measured maximum, not at the lower vendor reference figure.
- The retired field left no trace: no `commands/*.md` or `commands/*/SKILL.md` frontmatter declares `token-budget:`, no generated skill carries it forward, and `scripts/lint-commands.sh` no longer requires or computes it.

## Setup

No live harness or model turn needed; this is a static-invariant scenario backed by two functions in `evals/scripts/structural-evals.py`, run automatically by the `structural-evals` CI job on every push per `.github/workflows/lint.yml`.

- A checkout of this repo with the ADR-0116 changes applied: 95 command frontmatters with no `token-budget` field, 95 regenerated `.claude/skills/*/SKILL.md` files, and `scripts/lint-commands.sh` with the retired frontmatter check removed.
- A scratch temporary directory, created and destroyed by the test run, holding one fixture: `<tmp>/oversized-fixture/SKILL.md` filled with more than 40000 characters.

## Steps

1. Run `python3 ./evals/scripts/structural-evals.py` against the unmodified checkout. Capture exit code and the `skill-load-budget` and `no-retired-token-budget-field` lines.
2. In a Python session (or an equivalent script), import `evals/scripts/structural-evals.py`, create a temporary directory containing one oversized fixture (`<name>/SKILL.md` over 40000 chars), and call `check_skill_load_budget(root=<tmp dir>)` directly.
3. In the same session, call `check_skill_load_budget(root=<tmp dir with only a small fixture>)` as a negative control.
4. Delete the temporary directory.
5. Confirm `git status --short` shows no changes from steps 2-4 (the fixture lived entirely outside the tracked tree).

## Pass criteria

1. Step 1 exits `0`, and the `structural-evals.py` output shows `[PASS] skill-load-budget` and `[PASS] no-retired-token-budget-field` with no findings listed under either.
2. Step 2's direct call returns `ok=False` with exactly one finding naming the fixture's directory name, its measured char and approximate token count, and the 40000-char / 10000-token ceiling.
3. Step 3's direct call returns `ok=True` with an empty findings list.
4. Step 4 leaves no residue: the temp directory does not exist after cleanup.
5. Step 5's `git status --short` is empty (or shows only pre-existing unrelated changes), confirming the fixture never touched the real `.claude/skills/` corpus or any tracked path.
6. Re-running `grep -rn "token-budget:" commands/*.md commands/*/SKILL.md` (excluding `commands/_shared/`) returns no matches.

## Failure modes to watch

- **Wrong artifact measured**: the check reads a `commands/<name>.md` source file instead of the generated `.claude/skills/<name>/SKILL.md`, reintroducing ADR-0013's original defect (measuring the wrong stage) under a new name.
- **Hardcoded path**: `check_skill_load_budget()` cannot accept a `root` argument, forcing any test of the failing case to corrupt the real `.claude/skills/` directory. TEST_STRATEGY.md S-3 names this as the specific failure this scenario exists to catch.
- **Silent pass**: the oversized fixture in step 2 returns `ok=True`, meaning the ceiling arithmetic or the glob pattern is wrong and the gate would never fire in CI either.
- **Field partially retired**: a `token-budget:` line survives in even one command frontmatter, one generated skill, or inside `scripts/lint-commands.sh`, and `check_no_retired_frontmatter_field()` fails to catch it.
- **Ceiling drifted upward**: a future edit raises the 10000-token ceiling without a new ADR recording why, defeating the no-regression guarantee ADR-0116 states.

## Notes

- Related ADRs: [ADR-0116](../../docs/adr/0116-single-load-stage-size-budget.md) (supersedes [ADR-0013](../../docs/adr/0013-per-command-token-budget.md)).
- Related files: `evals/scripts/structural-evals.py` (`check_skill_load_budget()`, `check_no_retired_frontmatter_field()`), `scripts/lint-commands.sh` (the retired check removed), `scripts/build-agent-skills.sh` (the generator whose output this gate measures), `.github/workflows/lint.yml` (`structural-evals` job).
- Known issues: none yet (first run pending). The 10000-token ceiling is a no-regression starting point per ADR-0116, expected to ratchet down in a later slice; this scenario's step 1 will need its expected findings count updated if a future trim lowers the ceiling below any skill still in the corpus at that time.

## History

- 2026-07-25: created with ADR-0116 (task `2026-07-24_context-engineering-frontier-sweep`, slice 08, D-5).

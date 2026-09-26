# Eval scenario 116: the Load-stage size gate is a hard CI failure

- **Tags**: ADR-0116, ADR-0227, context-engineering, token-budget, load-stage, progressive-disclosure, lint-enforced-hard-fail, supersedes-adr-0013, structural
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

Validates **ADR-0116** (one enforced size budget at the Load stage; retires the ADR-0013 per-command `metadata.token-budget` field) and **ADR-0227** (the ceiling ratchets down): `evals/scripts/structural-evals.py::check_skill_load_budget()` fails the CI `structural-evals` job when a generated `.claude/skills/<name>/SKILL.md` exceeds the ceiling held in the one constant `LOAD_CEILING_CHARS` in that file (36000 chars since ADR-0227; this scenario names the constant everywhere else rather than repeating the number), `check_skill_load_ceiling_slack()` fails it when that ceiling sits more than 4000 chars above the largest skill, and `check_no_retired_frontmatter_field()` fails it when the retired field survives in a command frontmatter, a generated skill, or `scripts/lint-commands.sh`. This is a structural scenario: unlike scenarios 113-115, which a human reads against a model's prose output, this one is exercised by running the check functions directly, per TEST_STRATEGY.md scenarios S-3 and S-4.

This exercises:

- The gate fires: a generated skill over the ceiling makes `check_skill_load_budget()` return a failure naming the offending skill, its measured size, and the ceiling.
- The gate is path-parameterized, not hardcoded to the real corpus: `check_skill_load_budget(root=...)` accepts an arbitrary fixture directory, so the failing case above can be produced without touching `.claude/skills/`.
- The gate is clean over the real corpus: called with no argument (the default, real `.claude/skills/` path), every generated skill passes, because the ceiling sits just above the measured maximum, not at the lower `LOAD_TARGET_CHARS` reference figure.
- The ratchet turns: once trims leave the largest skill more than 4000 chars under `LOAD_CEILING_CHARS`, `check_skill_load_ceiling_slack()` fails and names the lower value to set.
- The retired field left no trace: no `commands/*.md` or `commands/*/SKILL.md` frontmatter declares `token-budget:`, no generated skill carries it forward, and `scripts/lint-commands.sh` no longer requires or computes it.

## Setup

No live harness or model turn needed; this is a static-invariant scenario backed by two functions in `evals/scripts/structural-evals.py`, run automatically by the `structural-evals` CI job on every push per `.github/workflows/lint.yml`.

- A checkout of this repo with the ADR-0116 changes applied: 95 command frontmatters with no `token-budget` field, 95 regenerated `.claude/skills/*/SKILL.md` files, and `scripts/lint-commands.sh` with the retired frontmatter check removed.
- A scratch temporary directory, created and destroyed by the test run, holding one fixture: `<tmp>/oversized-fixture/SKILL.md` filled with more than `LOAD_CEILING_CHARS` characters.

## Steps

1. Run `python3 ./evals/scripts/structural-evals.py` against the unmodified checkout. Capture exit code and the `skill-load-budget`, `skill-load-ceiling-slack` and `no-retired-token-budget-field` lines.
2. In a Python session (or an equivalent script), import `evals/scripts/structural-evals.py`, create a temporary directory containing one oversized fixture (`<name>/SKILL.md` over `LOAD_CEILING_CHARS` chars), and call `check_skill_load_budget(root=<tmp dir>)` directly.
3. In the same session, call `check_skill_load_budget(root=<tmp dir with only a small fixture>)` as a negative control.
4. In the same session, call `check_skill_load_ceiling_slack(root=...)` on a directory whose largest `<name>/SKILL.md` is 20000 chars, then on one whose largest is `LOAD_CEILING_CHARS` minus 1000.
5. Delete the temporary directory.
6. Confirm `git status --short` shows no changes from steps 2-5 (the fixture lived entirely outside the tracked tree).

## Pass criteria

1. Step 1 exits `0`, the `structural-evals.py` output shows `[PASS] skill-load-ceiling-slack` and `[PASS] no-retired-token-budget-field`, and `skill-load-budget` shows `[PASS]` or `[WARN]` (the 2000-char band is advisory and never fails).
2. Step 2's direct call returns `ok=False` with exactly one finding naming the fixture's directory name, its measured char and approximate token count, and the `LOAD_CEILING_CHARS` ceiling in chars and tokens.
3. Step 3's direct call returns `ok=True` with an empty findings list.
4. Step 4's first call returns `ok=False` with one finding that names the value to lower the ceiling to; the second returns `ok=True`.
5. Step 5 leaves no residue: the temp directory does not exist after cleanup.
6. Step 6's `git status --short` is empty (or shows only pre-existing unrelated changes), confirming the fixture never touched the real `.claude/skills/` corpus or any tracked path.
7. Re-running `grep -rn "token-budget:" commands/*.md commands/*/SKILL.md` (excluding `commands/_shared/`) returns no matches.

## Failure modes to watch

- **Wrong artifact measured**: the check reads a `commands/<name>.md` source file instead of the generated `.claude/skills/<name>/SKILL.md`, reintroducing ADR-0013's original defect (measuring the wrong stage) under a new name.
- **Hardcoded path**: `check_skill_load_budget()` cannot accept a `root` argument, forcing any test of the failing case to corrupt the real `.claude/skills/` directory. TEST_STRATEGY.md S-3 names this as the specific failure this scenario exists to catch.
- **Silent pass**: the oversized fixture in step 2 returns `ok=True`, meaning the ceiling arithmetic or the glob pattern is wrong and the gate would never fire in CI either.
- **Field partially retired**: a `token-budget:` line survives in even one command frontmatter, one generated skill, or inside `scripts/lint-commands.sh`, and `check_no_retired_frontmatter_field()` fails to catch it.
- **Ceiling drifted upward**: a future edit raises `LOAD_CEILING_CHARS` without a new ADR recording why. ADR-0227 pre-authorizes lowering it; only a raise needs a decision.
- **Ceiling left slack**: trims land and the constant stays where it was, so the gate stops constraining anything, which is how the ceiling sat at 40000 from 2026-07-25 to 2026-09-23.
- **Number restated**: a second copy of the ceiling appears in the check body, the real-load advisory, the registry label or `scripts/measure-tokens.py`, and the copies drift apart.

## Notes

- Related ADRs: [ADR-0116](../../docs/adr/0116-single-load-stage-size-budget.md) (supersedes [ADR-0013](../../docs/adr/0013-per-command-token-budget.md)), [ADR-0227](../../docs/adr/0227-the-load-ceiling-ratchets-to-36000.md) (lowers the ceiling and adds the slack check).
- Related files: `evals/scripts/structural-evals.py` (`LOAD_CEILING_CHARS`, `LOAD_TARGET_CHARS`, `check_skill_load_budget()`, `check_skill_load_ceiling_slack()`, `check_no_retired_frontmatter_field()`), `scripts/lint-commands.sh` (the retired check removed), `scripts/build-agent-skills.sh` (the generator whose output this gate measures), `.github/workflows/lint.yml` (`structural-evals` job).
- Known issues: the destination is `LOAD_TARGET_CHARS` (20000 chars), and the slack check lowers the ceiling toward it as trims land.

## History

- 2026-07-25: created with ADR-0116 (task `2026-07-24_context-engineering-frontier-sweep`, slice 08, D-5).
- 2026-09-23: ADR-0227 lowered the ceiling from 40000 to 36000 chars, moved the number into one constant, and added the slack check (steps 4 and pass criterion 4).

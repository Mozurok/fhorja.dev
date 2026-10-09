# Spec-read arm: named sections per command

Design note for one eval arm. It changes no command and no shared block.
`commands/_shared/mandatory-context-bootstrap.md` keeps its current read
instruction (provisional decision P-3 of the lean-context-trim task).

## Purpose

Question: does naming the `WORKFLOW_OPERATING_SYSTEM.md` sections a command
needs beat both forcing the full bootstrap read and forbidding any read?

Earlier runs found the read changes little on its own. It changes the order of
actions and what a grader can see. A named list is the middle option: read
less than the full bootstrap, but not nothing. Shipping it would be a separate
decision made after the data.

## The three arms

Each arm is an exact text that a harness prepends to the prompt of a spine
scenario. Only the prefix differs between arms.

Arm `skip`:

```text
Harness note: do not read WORKFLOW_OPERATING_SYSTEM.md in this run. The command file and the shared blocks inside it carry what you need.
```

Arm `force`:

```text
Harness note: before any output, read the mandatory sections of WORKFLOW_OPERATING_SYSTEM.md that the command's Mandatory context bootstrap names.
```

Arm `named`: one prefix per command, same opening, then the list. Every
heading below was checked against the spec with `grep -n -x -F`.

`task-init`:

```text
Harness note: before any output, read only these sections of WORKFLOW_OPERATING_SYSTEM.md and no others:
- `## Global output contract`: the APPLIED, PROPOSED and SKIP labels and the adaptive Handoff block.
- `## Cross-cutting workflow guardrails`: proposal versus approved persistence and substrate ownership apply to every file task-init writes.
- `## Project-level memory`: task-init links REFERENCES.md and the charter from SOURCE_OF_TRUTH.md.
- `## Editor mode policy`: task-init takes an Ask or Agent mode as input and states one in the Handoff.
- `## Definition of done (command outputs)`: the command ends by checking its output against it.
- `## Gate conditions`: the same closing check names it.
```

`implement-approved-slice`:

```text
Harness note: before any output, read only these sections of WORKFLOW_OPERATING_SYSTEM.md and no others:
- `## Global output contract`: the file labels, the Handoff block and Work complexity.
- `## Cross-cutting workflow guardrails`: skip `### External web access (centralized)` and `### Sequencing heuristics (by phase)`, as the bootstrap tier for this command already does. Persistence and substrate ownership govern the slice note and TASK_STATE.md writes.
- `## Definition of done (command outputs)`: the slice completion check ends against it.
- `## Gate conditions`: the same closing check names it.
```

`slice-closure`:

```text
Harness note: before any output, read only these sections of WORKFLOW_OPERATING_SYSTEM.md and no others:
- `## Global output contract`: the file labels, the Handoff block and the Work complexity set for the next step.
- `## Cross-cutting workflow guardrails`: skip `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. The command cites `### Material change (definition)` to decide when a section is skipped, and persistence rules govern its writes.
- `## Definition of done (command outputs)`: the command ends by checking against it.
- `## Gate conditions`: the same closing check names it.
```

What each command was judged to need, and what was left out:

- `## LLM execution contract` is left out of all three. It holds precedence and
  conflict rules and the minimum read map. None of the three commands depends
  on a rule from it to produce its steps. This is the weakest cut and the
  first one to put back if the arm fails.
- `## Editor mode policy` is kept for `task-init` only, because it takes the
  mode as an input. The other two get their Mode line from the Mode selection
  rule inside `## Global output contract`, so the arm tests that overlap.
- `## Project-level memory` is `task-init` only. The other two do not read or
  write project-level files.
- `## Definition of done (command outputs)` and `## Gate conditions` are not
  in the always-read bootstrap sections, but each command's last bullet names them.
  The arm adds them because a read list derived from the command text must.

## Measurement recipe

- Scenarios: `01` (bootstrap then task-init) and `03` (slice execution and
  closure). Use the fixture-backed 01 from the same task, so a correct STOP 2
  is no longer scored as a failure.
- Arms: `skip`, `force`, `named`. The `named` prefix for a scenario is the one
  for the command a turn runs. Scenario 03 uses the `implement-approved-slice`
  prefix on turn 1 and the `slice-closure` prefix on turn 2.
  A turn whose command has no list (`project-bootstrap`, turn 1 of scenario 01) runs
  with no prefix; the first measurement did exactly that, so its `named` cell for
  scenario 01 carries no harness note on turn 1.
- Repetitions: 3 per cell on Sonnet, same as the earlier grid. Run the isolation
  flags from `evals/README.md` so installed skills never shadow the repo.
- Record per run: pass rate per rubric criterion, input plus output tokens
  (and cost where the harness reports it), and whether the spec was read
  at all, taken from the raw tool events, not from the model's own claim.
- Void and rerun any run whose raw output carries usage-limit text. Never average
  a voided run.
- Report `named` against `skip` and `force` side by side, with the interval, and
  say when n=3 cannot separate the arms.

## Known confounds

From the validation report of the 2026-10-08 lean-context-trim task (kept in the maintainer's local task memory; the figures are summarized in ADR-0248):

- The harness note changes the task. Models behave differently when told to read
  or not to read.
- In the first measurement the `named` arm had no prefix on turn 1 of scenario 01
  (see the recipe above), so that cell compares a half-prefixed run with two
  fully prefixed arms.
- Some models read the spec regardless. Codex read it in about half of the `skip`
  runs, and a forced Haiku read it in none of the runs on scenario 142. Count what was
  read, not what the arm asked for.
- n=3 per cell cannot detect an aggregate effect smaller than about 10 points.
- UNCERTAIN counts as a fail, so some criteria track what the grader can see
  rather than what the model did.
- The main grader is the same model family as the runner. Re-grade one
  repetition per cell with Codex and report both.
- The rubric does not measure verification habits, slice notes or transcript depth.
  A `named` arm that passes the rubric has not shown those are intact.

# Eval scenario 133: a skill-description trim is gated by two deterministic invariants

- **Tags**: ADR-0135, skill-descriptions, advertise-stage, context-budget, structural
- **Last reviewed**: 2026-08-10
- **Status**: active

## Goal

ADR-0135 gated the size of the Advertise stage and changed no description. It recorded, as
the second of three OPEN items, that nothing in this repository measures whether a shorter
description still routes: a description trimmed until a model stops picking it fails
silently, as "the model did not load the skill it needed", which reads as a model problem.

This scenario is what closes that item, and it closes it in a smaller shape than the one
ADR-0135 imagined. The original question was whether a model still selects the right skill.
That question turned out to be unanswerable in this harness, for a reason recorded below.
What replaced it are two invariants that gate the two ways a trim can break the surface,
deterministically and with no model involved.

## Why there is no model in this gate

The obvious design was a stateless sub-agent handed the 98 descriptions and a task prompt,
which is how `verify-against-rubric` judges artifacts. Measured 2026-08-10, that route does
not work here: **a sub-agent already carries a skills listing in its own system prompt and
answers from it.** Five dispatches given a payload file reported zero tool uses and
identical token counts to a control given no file at all, and the control named "skills
listing" as its source.

So the surface cannot be varied. A modified corpus handed to the sub-agent does not replace
the one it already has; it adds a second copy, and the model prefers its own. Before-and-after
comparison, which is the whole shape of a trim check, is not constructible that way.

Recorded here rather than in task memory alone, because the next person to reach for a
sub-agent to test routing will otherwise spend the same measurement twice.

## Automated half

Two checks in `evals/scripts/structural-evals.py`, both hard failures in the
`structural-evals` CI job.

### `description-reference-preservation` (D-4, the comparative half)

The corpus discriminates confusable skills by pointing at each other. Measured 2026-08-10:
93 of 98 descriptions name at least one other skill, 286 cross-references in total, and 27
reciprocal pairs where each names the other, among them `where-we-at` and `slice-closure`,
`sync-task-state` and `state-reconcile`, `resume-from-state` and `state-reconcile`.

Those clauses read as boilerplate, which is exactly why a trim cuts them first, and cutting
them is what makes a shorter description stop routing.

The check compares the live corpus against `evals/skill-description-baseline.json` and
requires a MATCH, not merely coverage. A dropped reference is named. An ADDED reference
fails too, saying only that the baseline is stale: without that, a reference added without
regenerating would sit permanently outside the gate, and its later removal would pass
unnoticed because the baseline never learned it existed.

Regenerate deliberately with `evals/scripts/build-description-baseline.py`, or in one pass
with `scripts/reconcile-counts.sh --all`, which covers it as its third generated surface.

### `description-capability-floor` (D-6, the absolute half)

Every description keeps at least 150 characters of capability segment, the text before its
first routing marker, and keeps a `Do not use` marker.

The floor is derived, not picked. Capability segments run from 186 characters
(`team-update`) to 744, median 380; 150 is the largest round value below the current
minimum, which makes it a no-regression floor in the same form ADR-0135 used for the
aggregate ceiling.

The marker clause is definitional rather than additive: the segment is defined BY the first
routing marker, so a rewrite that drops the markers makes the whole description read as
capability text. Measured, all 98 clear a 150 floor under that rewrite, which is a total
bypass. It is stated absolutely because 98 of 98 carry `Do not use` today, so it needs no
baseline.

### Why a floor and not a cap on how much an edit removes

This was tried and measured false. The fail-open attack, keeping the cross-references and
deleting the substance, removes between 14 and 90 percent of a description, median 64,
while the reduction this gate exists to enable removes about 52 percent. The ranges overlap:
on 23 of 93 descriptions the attack removes LESS than the intended trim. No delta bound
separates them. What separates them is what remains.

## What these two invariants do NOT prove

Stated here as part of what the gate is, because a green that reads as more than it is will
cause the exact trim this scenario exists to prevent.

- **Neither one proves a model still selects the right skill.** They prove the discriminating
  pointers survived and that no description was gutted below a measured floor. The routing
  question itself is not answerable in this harness; see above.
- **5 of 98 descriptions name no other skill** and sit outside the reference check entirely.
- **A standalone `Use when` is present in only 80 of 98**, so it cannot be required the way
  `Do not use` is. An edit dropping only `Use when` inflates the measured capability segment
  and softens the floor without defeating it. (An earlier figure of 85 circulated during this
  task; it counted `use when` matches sitting INSIDE `Do not use when`, before the check's
  pattern gained its `(?<!not )` lookbehind. 80 is the count under the shipped pattern, and
  18 descriptions carry no standalone `Use when` rather than 13.)
- **The floor bounds gutting, not meaning.** An edit that keeps 150 characters of filler
  passes. No deterministic check verifies meaning and this one does not pretend to.
- **The baseline can be regenerated.** The gate cannot stop that, only stop it happening
  silently: regeneration lands as a reviewable diff, the same shape as a lockfile.

## A consequence for whoever does the trim

A uniform 52 percent reduction drives 35 of 98 descriptions below the capability floor. The
reduction ADR-0135 item 1 contemplates therefore cannot be uniform: descriptions with thin
capability segments have to give ground in their routing half instead. That is the invariant
working, and it is a constraint the trim inherits rather than a defect to route around.

## Manual half

Before trimming, read the fixture READMEs under `evals/fixtures/description-trim/`,
`description-blank-line/`, `description-gutted/` and `description-missing/`. Each names the
one thing its variant proves and, for `description-gutted/no-standalone-use-when/`, the
narrow window its numbers must stay inside.

Then read three trimmed descriptions end to end and ask whether each still tells a model
what the skill does and when to pick it. Both checks are byte-level and neither can see that.

## Pass criteria

- Both checks pass on the real corpus.
- `description-reference-preservation` fails on `evals/fixtures/description-trim/trimmed/`, naming the dropped reference, and on `augmented/`, saying the baseline is stale.
- `description-capability-floor` fails on `description-gutted/gutted-segment/` for the floor clause alone and on `no-marker/` for the marker clause alone.
- The `description-blank-line/` fixture passes with the shipped parser and fails with a parser that stops at a blank line inside a YAML block scalar.
- Regenerating the baseline produces a reviewable diff rather than a silent pass.

## FAIL conditions

- Either check is added as warn-only rather than a hard failure, which reproduces the asymmetry ADR-0135 exists to close.
- `description-reference-preservation` accepts an added reference without failing. The gate then erodes: every reference added without regenerating sits outside it permanently, and its later removal is invisible.
- The capability floor is specified as a bound on how much an edit removes rather than a floor on what remains. Measured false above; the ranges overlap on 23 of 93 descriptions.
- A description is trimmed and the baseline regenerated in the same commit with no reviewer looking at the regeneration diff. The gate's only real defence is that the regeneration is visible.
- Either invariant's green is cited as evidence that routing is intact. Neither measures routing, and the scenario says so in three places precisely so this cannot happen by accident.
- The `no-standalone-use-when` fixture's description prose is edited without re-measuring. Its capability segment must stay inside a seven-character window below the floor or it silently stops discriminating while still reporting RED. The numbers live in that fixture's own `SKILL.md` body; no gate can catch this one.

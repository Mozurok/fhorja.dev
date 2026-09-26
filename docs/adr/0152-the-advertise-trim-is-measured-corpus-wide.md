# ADR-0152: The Advertise trim is measured corpus-wide, and the probe needed a positional guard first

Date: 2026-08-17

Status: Accepted

## Context

ADR-0151 D-5 bounded its result deliberately: 15 of 89 commands, one model, one prompt shape,
and cases written by the same person who wrote the expected answers. It licensed a pilot trim and
said extending the claim required running the probe over the rest. This ADR is that run.

Two things had to be fixed before the number meant anything, and both were found by the controls
rather than by inspection.

## Decision

**D-1. Cases are generated blind to the descriptions under test.** Eight writers each read only a
copy of the command body with its YAML frontmatter stripped from disk, and wrote one realistic
request per command in the operator's own language. The generator never sees the `description`,
because a case derived from the text under test measures whether text matches itself. A validator
then checks the set mechanically: 89 of 89 covered, 0 cases naming any command, 0 cases sharing a
three-word phrase with their own description, 0 near-duplicate pairs. The case set is committed at
`evals/fixtures/routing-probe/cases-89.json`.

**D-2. Rotation is replaced by hash-keyed permutation, and a positional guard refuses to emit
without one.** The first 89-command run scored 100 per cent in every condition INCLUDING the
shuffled control, and the answers were a perfect contiguous sequence. Cause: the command order and
the case order were both rotations of the same sorted list, so `expected[i]` was `i` plus a
constant and list position predicted every answer without reading a word. `emit` now orders
commands and cases under independent hash seeds and computes `positional_confound()`, the fraction
of the mapping explained by one fixed offset. Above 0.25 it refuses to emit. Verified in both
directions: a pure progression and a rotated progression both measure 1.00 and are refused; the
shipped emission measures 0.06.

The ADR-0151 pilot was re-checked against this guard and passes (9 distinct offsets across 15
cases), so ADR-0151 D-4 stands as recorded. The confound was introduced by the expansion, which
sorted the 89 cases by command name while the command list was also sorted.

**D-3. The corpus-wide measurement.** 89 commands, 89 cases, all descriptions present in every
prompt as in real use, 3 replicates per condition, 267 decisions per condition:

| Condition | Description | Size | Accuracy |
|---|---|---|---|
| A_full | current text | 100% (73131 chars) | 100% |
| B_trim | opener plus compressed `Do not use` clause | 47.2% | 100% |
| C_gut | opener sentence only, routing marker removed | 22.5% | 99.3% |
| D_shuffled | another command's description | 100% | 0% |

The control collapsed to zero across all three replicates, so the probe depends on description
content at this scale as it did at 15.

**D-4. The single C_gut failure is an artefact of the harness, not a property of the description.**
Both misroutes were one swap, between `atom-audit-fleet` and `screen-spec-fleet`, in one replicate.
The probe scrubs command names out of description bodies, and both openers read `Orchestrator-workers
variant of <sibling>`, so after scrubbing the two texts are byte-identical: `Orchestrator-workers
variant of another command.` The model was choosing between two identical strings and got it right
in two replicates and wrong in one, which is what guessing looks like. Exactly one such collision
exists across the corpus in C_gut, and none in A_full or B_trim. Discounting it, C_gut routes 89 of
89.

**D-5. ADR-0151 D-5 is superseded.** The claim is no longer bounded to a pilot: on this corpus, one
model and one prompt shape, cutting the Advertise surface to 47 per cent costs nothing measurable,
and cutting to 22 per cent costs nothing beyond one artificial collision. What remains unbounded is
model diversity and prompt-shape diversity; a second model would strengthen this and has not been run.

**D-6. This ADR does not perform the trim.** It records that the evidence ADR-0135 item 2 required
now exists at corpus scale. Editing 98 descriptions is a separate change with its own review, and
the descriptions also serve human readers of the catalog, which this probe does not measure.

## Consequences

- The Advertise stage sits at 81065 of 84000 chars, 96.5 per cent, with room for about three more
  commands. A B-shaped trim would take it to roughly 38000 chars and leave room for about 55. That
  is now an evidenced option rather than a blocked one.
- `routing-probe.py` gained a guard whose failure mode was a perfect score. That is the third defect
  of that shape in this line of work: names leaking the answer (ADR-0151 D-2), and now position
  predicting it. Both were caught by controls, neither by reading the output.
- The two `-fleet` openers that collide under scrubbing are worth rewording on their own merits: a
  description whose first sentence is distinguishable only by naming a sibling command is fragile
  for a human reader too.
- Extending to a second model is the obvious next strengthening and is deliberately not claimed here.

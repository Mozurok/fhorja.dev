# ADR-0155: The Advertise trim stops at thirty descriptions, and references are the floor

Date: 2026-08-17

Status: Accepted

## Context

ADR-0151 built the routing check ADR-0135 item 2 required. ADR-0152 measured it corpus-wide.
ADR-0153 confirmed it across four providers. ADR-0154 trimmed the first ten descriptions and
projected the rest. Two further batches followed. This ADR closes the exercise with measured
numbers instead of a projection, and records why it stops at thirty rather than eighty-nine.

## Decision

**D-1. What was done.** Thirty of the eighty-nine flat commands had their `description` rewritten by
hand, in three batches of ten, always heaviest-first:

| | Advertise stage | headroom | commands that fit | batch cut |
|---|---|---|---|---|
| before | 81065 | 2935 | 3 | |
| after batch 1 | 77482 | 6518 | 7 | 32.7% |
| after batch 2 | 75239 | 8761 | ~10 | 22.8% |
| after batch 3 | 73316 | 10684 | ~12 | 19.9% |

7749 chars removed from the surface every session pays for, and the ceiling moved from three
commands away to about twelve.

**D-2. References are a structural floor, and that is why the cut fell each batch.** Mean description
length rises monotonically with tracked reference count across all 98: 653 chars at zero references,
673 at one, 736 at two, 753 at three, 773 at four, 788 at five, 845 at six, 933 at eight. A tracked
reference cannot be cut, because ADR-0135 D-4 treats a dropped reference as the regression its gate
exists to catch. The two smallest cuts in batch 3 were `self-critique-and-revise` at 11.6 per cent
and `implement-slice-complement` at 12.1, and they are exactly the two carrying six references each.
The falling per-batch rate is therefore a property of the inputs, not fatigue in the editing.

**D-3. The projection was wrong twice, in the same direction, and the third figure is measured.**
ADR-0154 D-2 projected roughly 25000 chars recoverable corpus-wide, extrapolated from batch 1's
32.7 per cent. Commit `b9f8f86` revised that to 15000 to 18000 after batch 2. Pinning the estimate
to what the thirty finished descriptions actually achieved at each reference count gives about 6356
chars remaining across the 68 untrimmed, for a total of roughly 14100. Both earlier figures
extrapolated from the easy batches: heaviest-first ordering means every later batch is harder than
the one before it, so any projection taken from an early batch is optimistic by construction. Recorded
because the same trap applies to the next person who measures two batches and extrapolates.

**D-4. Why it stops here.** The blocking problem is solved: the ceiling was three commands away and is
now about twelve. Return per batch is falling (3583, 2243, 1923 chars) while cost per batch is flat,
and the remaining 6356 chars would take six more batches to land about eight more commands of
headroom. That is a worse trade than it was at batch 1, and the ADR-0135 ceiling is no longer the
constraint on growth. Stopping is a judgement about marginal value, not a claim that the remaining
descriptions are optimal.

**D-5. Verification, including where it thinned out.** Every batch was verified by re-emitting the
probe against the descriptions as they then stood, with the expected-answer mapping byte-identical to
the pre-trim run so the only variable is the text. Batches 1 and 2: Claude at 100 per cent across
three replicates with zero misroutes, matching pre-trim. Batch 2 also Kimi at 89 of 89 against its
98.9 pre-trim baseline. Batch 3: Kimi only, 89 of 89, shuffled control at 0. The Claude control for
batch 2 and all of batch 3 could not be run because the API returned 529 Overloaded on six
consecutive attempts. Batch 3 therefore rests on one provider and one replicate, which is weaker
evidence than batches 1 and 2 and is stated rather than averaged away.

**D-6. What is left, for whoever continues.** 59 flat commands untrimmed, worth about 6356 chars. The
9 folder-format persona commands have no routing case in `cases-89.json` (generated from the 89 flat
files), so their trims can pass the structural gates but cannot be verified; writing cases for them
comes first. The method is unchanged: rewrite preserving every tracked reference, the `Do not use`
marker and the 150-char floor, run `build-agent-skills.sh`, run lint and structural evals, re-emit
the probe and confirm no drop against a mapping that did not move.

## Consequences

- The Advertise ceiling stopped being the limit on adding commands. It is not removed, and at about
  twelve commands of headroom it will return.
- Nothing here claims the descriptions read better for a human. They are shorter, they still route,
  and the catalog's readability was never measured. A reader who finds one worse has a real
  complaint that no gate in this repository would have caught.
- Four ADRs and four measurement defects were spent to justify editing thirty description fields.
  That ratio is worth remembering the next time a surface looks obviously trimmable: the trimming was
  the cheap part.

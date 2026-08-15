# Baseline: grounding shape, 2026-08-13

Frozen snapshot for the ADR-0146 forward measurement. Produced by
`scripts/measure-grounding-shape.py` at detector version **2.0.0**. Do not edit
after the fact; take a new dated snapshot instead and compare.

## Why this exists

ADR-0146 shipped `reference-grounding` rule 7 on five documented incidents and
recorded that two blinded A/B runs measured zero effect, because a fixture small
enough to author is small enough to read exhaustively. It named the test that
would discriminate: measure, across real sessions after the rule lands, whether
the behavior it asks for shows up. If it does not, the rule is ceremony and comes
out under `wos/active-epistemic-humility.md` rule 1.7.

This file is the BEFORE. It is taken on the day rule 7 landed, over a corpus that
predates it entirely, so every number here is the pre-rule state.

## A. Cite shape in task artifacts

Command: `scripts/measure-grounding-shape.py --artifacts projects/`

```
353 cite(s) across 250 artifact(s)
  internal file:line (rule 7 shape)      36  (10.2%)
  external reference (rule 3 shape)     162
  neither                               155
```

The load-bearing number is **10.2%**, not 353. Rule 3 has produced
`Grounded in:` cites naming a `REFERENCES.md` entry since ADR-0043, so the total
was never near zero. What rule 7 asks for is the other shape: a `file:line` cite
for a claim about IN-REPO behavior. A future corpus where that share has not moved
is a corpus where rule 7 changed nothing.

Real examples from this snapshot, so a later reader can see what counted:

```
WORKFLOW_OPERATING_SYSTEM.md:765-779, read this session; wos/autonomous-track.md:80-82
commands/task-init-fleet.md:56 and :127; scripts/portfolio-review.sh:97
```

One thing this snapshot surfaces that is NOT part of the rule 7 question, recorded
because dropping it would be losing a real observation: **155 of 353 cites (44%)
match neither shape**. They are `Grounded in:` lines naming a document without a
locatable referent. That is its own gap, it predates this work, and nothing here
acts on it.

## B. Read shape in session transcripts

Command: `scripts/measure-grounding-shape.py --transcripts <harness projects dir>`

Measured on the ten-session product-repository corpus that produced the 2026-08-13 forensics:

```
largest session alone:  768 file reads, 578 window / 190 whole  (75.3% windowed)
```

Clause (a) of rule 7 exists because a claim over a whole surface cannot rest on a
window read. If window share falls while internal cites rise, that is the shape the
rule predicts. Neither number alone proves anything.

## What this instrument cannot do

A first version of the script tried to detect the failure directly in transcript
prose: find a quantified claim ("every caller", "all errors"), tie it to the file it
names, flag it when that file was only ever read in windows. Validated against the
session where the forensics had already established ground truth, it scored:

- **R1 recall ~0**: 0 of 11 quantified claims flagged, including the known case.
- **R2 precision ~0**: 53 of 55 hits, nearly all ordinary prose containing the word
  "precedent".

The cause is structural. A claim in prose names the SYMBOL
("`completeTasksByName` already logs"), a read names the PATH, and joining them is
the work a human reviewer does. Tuning the regexes until the rate looked right would
have been fitting the instrument to the answer. That detector was deleted rather than
tuned, and the reason is recorded in the script's own header so nobody rebuilds it.

## How to use this baseline

Take the next snapshot no earlier than a corpus of real post-2026-08-13 sessions
exists (rule 7 landed in commit `935e7e5`):

```
scripts/measure-grounding-shape.py --artifacts projects/ --since 2026-08-13
```

Read the result against these three outcomes, decided in advance so the reading is
not chosen after seeing the number:

- **Internal-cite share materially up.** Rule 7 is producing its own evidence. Keep it
  and note the snapshot in ADR-0146's validation section.
- **Share flat.** Rule 7 is ceremony by rule 1.7 and comes out. Removing it is a
  one-line revert of the shared block plus a `sync-shared-blocks.sh` pass.
- **Share up but window share also up.** Inconclusive and interesting: cites are being
  written without the enumeration clause (a) asks for, which is the shape of a rule
  being satisfied rather than followed.

A rate here is a trend and never an attribution. Sessions differ in task, model,
repository, and operator, and a present cite says nothing about whether the cited
lines support the claim. That check stays human, per `claim-grounding` rule 4.

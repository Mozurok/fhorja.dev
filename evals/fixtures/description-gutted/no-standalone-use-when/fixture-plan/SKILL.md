---
name: fixture-plan
description: |-
  Fixture skill with no standalone Use-when clause, its capability segment tuned to land inside the seven-character window just below the 150 floor.
  Do not use when a standalone clause exists (use fixture-status).
metadata:
  category: fixture
---

# fixture-plan

DO NOT EDIT THE DESCRIPTION PROSE WITHOUT RE-MEASURING.

This fixture only works as a test while its capability segment sits inside a 7-character
window below the 150-char floor. 7 is the exact gap between the two readings, the length
of `Do not `:

    anchored pattern (correct)   147   FAILS the floor
    unanchored pattern (buggy)   154   PASSES the floor

Outside [143..149] both readings land on the same side of the floor. The fixture then
still reports RED, for a reason that proves nothing, and that failure is completely
silent: the check output does not change. Current slack is 4 characters shorter
or 2 longer before it stops discriminating.

Re-measure with capability_segment() in evals/scripts/structural-evals.py after any edit.

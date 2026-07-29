# Fixtures: Godot tier-declaration gate

Fixtures for `check_godot_tier_artifact_gate` in `evals/scripts/structural-evals.py`, rebuilt 2026-07-26 against the canonical fenced form (ADR-0119) and extended 2026-07-27 with the fence-character, line-ending, waiver-matching, and multi-plan siblings.

**The unit is a DIRECTORY, not a file.** Each holds one or more plan files (`GODOT_SCENE_PLAN.md`, or `GODOT_SCENE_PLAN_<slug>.md` for the multi-plan cases `godot-scene-plan` Step 9 sanctions) and, where the case needs one, a `TASK_STATE.md` carrying the `tier-declaration waiver:` line. That is what makes the waiver path deterministically testable instead of asserted only in the floor's prose, and the waiver is the only escape from a gate that otherwise fails closed.

**The check iterates this directory, never the expectation dict.** A fixture on disk that no expectation names is a FAILURE, not a skip. The superseded version iterated the dict, so a fixture could be added, look present, and assert nothing, which is worst for exactly the negatives. The same rule holds one level down: with a per-plan (dict) expectation, a plan file inside a fixture that no expectation names is a FAILURE too, so a second plan cannot be added and quietly assert nothing.

**Fixtures are read verbatim.** The gate opens them with newline translation off, because a CRLF or lone-CR fixture that reaches the check as LF asserts nothing about the bytes on disk. That is why `crlf-declaration` sat here for a round proving less than it claimed.

## Still authored, still not observed

These encode the author's reading of the declaration form. No produced `GODOT_SCENE_PLAN.md` anywhere in the tree declares `Dimension: 3D`. That gap is unchanged by ADR-0119 and is not closed here.

What IS different from the superseded set: several are not imagined. `near-miss-lowercase`, `near-miss-heading`, `near-miss-table`, `near-miss-bulleted`, `near-miss-emphasis`, and `near-miss-inline-reason` are the exact forms verified failing in the shipped line-parser on 2026-07-26. Three of them returned a silent `stand-down`, meaning the gate disabled itself; one was the form the written contract instructed authors to produce. Derived from observed failures rather than from imagination, they are stronger than the single decoy was, and the decoy is kept alongside them.

The same is true of the 2026-07-27 additions. Every one of them was reproduced against the shipped code before it was written: a tilde outer fence made a QUOTED exemplar count as the plan's own declaration, a waiver written inside a `~~~` sample counted as a recorded human act, a CRLF plan collapsed every malformed route into the waiver-escapable absent bucket, and every superstring of a plan's filename (`OLD_` prefix, `.bak` suffix, `docs/` prefix) waived the plan it merely contained.

## Verdicts

Read them from `_TIER_FIXTURE_EXPECTATIONS` in `evals/scripts/structural-evals.py`. That dict is the single source of truth and the check iterates this directory against it, so a fixture with no expectation is a FAILURE, never a skip. A second copy of the verdicts in prose has nothing keeping it honest: the list that used to sit here drifted by nine directories, and its claim that one fixture was "the only fixture carrying a `TASK_STATE.md`" was false for six others before this round added more.

## Why several cases come in pairs

Most directories here are one half of a pair, and the pairing is the point. A malformed-form fixture carries a `TASK_STATE.md` waiver so it proves the waiver does NOT clear a malformed block; its twin without one would block for the wrong reason and prove nothing. A fence-character or line-ending fixture in the `block` direction is paired with one in the `pass` or `waived` direction (`tilde-sample-then-declaration`, `waiver-prose-beside-tilde-sample`, `crlf-waived-no-declaration`), because a fix that over-blocks silently disables the only escape the floor grants and every block-direction fixture would still be green.

The four added 2026-07-26 after an independent review came from the FENCE form's own failure modes, not the superseded line parser's: `indented-fence` (the command's own exemplar is indented two spaces and a column-0 parser rejected it), `over-indented-fence` (the tolerance is bounded at three spaces), `extra-key-in-fence` (the contract says nothing else goes inside and the parser accepted `Reason:` anyway), and `2d-with-tier` (the check blocked it before the floor said so).

Expectations live in `_TIER_FIXTURE_EXPECTATIONS` in the check itself.

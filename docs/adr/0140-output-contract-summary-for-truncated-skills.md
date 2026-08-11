# ADR-0140: An output-contract summary at the top of a truncated skill

Date: 2026-08-10

Status: Accepted

## Context

Skill bodies are re-injected after compaction capped at 5,000 tokens per skill, and the Claude
Code documentation is explicit that "truncation keeps the start of the file". Every command in
this repository puts its output contract at the END, which is the natural reading order for a
human and exactly wrong for this mechanism.

Measured 2026-08-10: 55 of 98 skills exceed the cap, and 46 lose `### Definition of done`
outright, along with `### Handoff` and `### Standard output layout`. The loss lands precisely
when a session has run longest, which is when a command is most likely to drift from its
contract. This is the concrete mechanism behind the Governance Decay result (policy violation
rising from 0 to 30-59 per cent after compaction) inside this repository.

The first mitigation, shipped earlier the same day, emitted a notice at the top saying the tail
was gone and instructing a re-read. Honest, and weak: it depends on the agent acting on it, and
it costs 360 chars to carry no contract at all.

Two stronger options were weighed.

**Reorder the sections.** Measured at +6 chars, and it does move all five contract sections
inside the surviving region. Rejected because it does not remove the cut, it only changes what
falls off: the last 40 per cent of the operational instructions would go instead. Worse, the
evidence does not support "earlier is better" as a law. Prompt Design at Scale (arXiv
2607.19257, 4800 trials across 5 models) measured that moving an identical instruction block
changes adherence by up to 8.7 percentage points and THE DIRECTION IS MODEL-SPECIFIC: it helped
Haiku (+6.6pp), hurt Gemini Flash (-8.7pp), and did nothing on Sonnet 5. Trading a known loss
for an unpredictable one is a bad trade.

**Split the skill in two.** Rejected on the mechanism: the cap is 5,000 per skill, but the
25,000 total and the "oldest dropped first" rule still apply, and both halves would count.

## Decision

The generator emits a compact output-contract summary at the top of any body over the cap. It
carries the first substantive rule of each contract section, in order, as a blockquote, and
states that the full sections remain authoritative.

This is the pattern the vendor's own authoring guidance gives for partial reads: "For reference
files longer than 100 lines, include a table of contents at the top. This ensures Claude can
see the full scope of available information even when previewing with partial reads."

Generated artifact only. The canonical `commands/*.md` keep their human reading order, so this
is one change in `build-agent-skills.sh` plus a helper, not 55 edits.

## Consequences

- 55 skills carry the summary; all 55 land at an offset inside the surviving region, verified.
  The output contract now survives compaction in compressed form rather than disappearing.
- It costs 807 to 929 chars per affected skill, mean 908, against the 360 of the notice it
  replaces. The net is about 550 chars for carrying the contract instead of announcing its loss.
- **The Load ceiling got tight.** `slice-closure` now sits at 39,564 of 40,000, 436 chars of
  headroom. That is under one added sentence. The next edit to that command will need to remove
  something, and this ADR is the reason why. The honest reading is that this bought contract
  survival with the last of the headroom, and the closure cluster now needs real slimming rather
  than another accounting move.
- The summary is derived, not authored, so it cannot drift from the sections it summarizes. It
  also cannot be better than them: it takes the FIRST substantive line of each section, which is
  the rule in every current command but is a convention, not a guarantee.
- Nothing here reduces what gets cut. The middle of a large body is still lost after compaction.
  This makes the loss survivable, not absent.

# ADR-0227: The Load ceiling ratchets to 36,000, and lowering it needs no decision

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: in part, [ADR-0116](./0116-single-load-stage-size-budget.md): its ceiling value (40,000 chars) and its rule that a tightening is recorded as a successor decision. The single Load-stage gate on the generated skill stands.
- **Tags**: context-engineering, load-stage, token-budget, skill-size, ratchet, build-agent-skills, adr-0116, b13

## Context

ADR-0116 set one hard ceiling on the generated `.claude/skills/<name>/SKILL.md`: 40,000 chars
(10,000 tokens), stated just above the 2026-07-25 maximum. It called the number "a starting point,
not a target" and the check's docstring said it was meant to ratchet down. It never moved. The
ceiling held because trims and extractions (ADR-0124, ADR-0180) kept the largest skills under it,
and nothing asked anyone to lower it once they had.

Measured on 2026-09-23 at the base of this change:

- 98 skills, 56 of them over 20,000 chars (29 when ADR-0116 was written). The largest was
  slice-closure at 39,940 chars, 60 under the ceiling.
- Five skills sat above 36,000: slice-closure 39,940, task-close 39,197, implementation-plan
  38,531, task-init 38,137, implement-approved-slice 36,768.
- The real-load advisory, which adds each command's declared unconditional loads, reported
  slice-closure 64,018, implement-approved-slice 61,128 and task-close 58,994 chars.
- The number lived in four places in code and prose: the check body, a second constant beside the
  real-load advisory, the check's registry label, and `scripts/measure-tokens.py`, plus scenario
  116 and its `evals/README.md` row.

Two outside figures meet at 5,000 tokens: the Agent Skills specification recommends keeping a
skill's instructions under it, and the host re-attaches only the first 5,000 tokens of each skill
after a compaction. Gating there now would mean trimming 56 skills by about 388,000 chars in one
change.

## Decision

The ceiling is 36,000 chars (9,000 tokens), held in one constant, `LOAD_CEILING_CHARS` in
`evals/scripts/structural-evals.py`, which every other surface reads or names. `LOAD_TARGET_CHARS`
names 20,000 chars as the destination. A new hard check, `skill-load-ceiling-slack`, fails when the
ceiling sits more than 4,000 chars above the largest skill and names the value to lower it to.
This ADR pre-authorizes every lowering: acting on that finding needs no new decision, and only a
raise does. The 2,000-char warning band stays advisory.

- The five skills got under 36,000 by cutting text: provenance parentheticals, rationale and
  history sentences, and rules stated twice in the same file. Nothing moved into a topic a command
  loads unconditionally. Each trimmed file's normative sentences (SHALL, MUST, never, WHEN, refuse,
  do not) were diffed before and after, and every removed one is either a duplicate of a sentence
  that stays in the same file or restated there with the same obligation.
- A phrase a structural check, a guard mutation or a script test pins stays as written.
- `scripts/build-agent-skills.sh` drops the two maintenance markers from the generated copy: a
  `<!-- shared:<name> -->` line and the `<!-- count:<kind> -->N<!-- /count -->` wrapper, which
  becomes the bare N. Both stay in `commands/*.md`, where `sync-shared-blocks.sh`,
  `reconcile-counts.sh` and the lint read them; nothing reads them in `.claude/skills/`. Fenced
  code and any other marker form are left alone. `scripts/tests/test-build-agent-skills-markers.sh`
  pins it.

## Consequences

### Positive

- The ratchet turns on its own. When trims leave room, the build names the new ceiling instead of
  waiting for someone to remember ADR-0116's intent.
- One number. The check, the advisory, the registry label, scenario 116 and `measure-tokens.py`
  cannot disagree.
- The marker strip saves 300 to 1,000 chars on the largest skills and about 28,000 across the
  corpus, and it costs nothing a reader of a skill used.

### Negative

- The five trimmed skills end between 35,382 and 35,760 chars, so each sits inside the advisory
  band and the next paragraph added to one of them fails the build. That is the intended pressure,
  and it lands on the commands that change most.
- The real-load figures drop by the trimmed amount only: slice-closure 59,838, implement-approved-
  slice 60,094, task-close 55,510 chars. Their declared closure-floor views are untouched.
- The rule-preservation guard is a sentence diff, not a proof. A trim that rewords a rule can
  still change its force; the guard makes each such rewrite visible and paired, nothing more.

### Neutral

- The five skills were not the only ones near the new line: decision-interview (35,291) and
  review-hard (34,113) now warn as well. The band stays advisory, so they do not fail.

## Alternatives considered

### Declare 40,000 permanent

- The gate would keep stopping growth and never reduce anything.
- Rejected: it was already binding on slice-closure at 60 chars of room, and a ceiling that only
  stops growth pushes the next change into an unconditional extraction, the loophole ADR-0137
  had to close.

### Gate at 20,000 now

- One change trimming 56 skills.
- Rejected: about 388,000 chars of cuts in one pass, each needing the rule-preservation guard,
  would be a rewrite of half the catalog rather than a trim.

### Gate on the real load

- Count the declared unconditional loads against the ceiling.
- Rejected for now: the three closure commands start 54 to 67 per cent over 36,000, which makes it
  a refactor of the closure cluster rather than a ceiling. It stays the advisory beside the gate.

### A wider warning band, or trimming to 34,000

- Set the band to half the slack, or trim seven skills to clear the 2,000-char band.
- Rejected: the band is advisory, and the extra cuts (23,589 chars across seven files, measured
  before this change) buy a quieter report, not a stricter gate.

## References

- `evals/scripts/structural-evals.py`: `LOAD_CEILING_CHARS`, `LOAD_TARGET_CHARS`,
  `LOAD_SLACK_CHARS`, `check_skill_load_budget`, `check_skill_load_ceiling_slack`,
  `check_real_load_advisory`.
- `evals/scripts/guard-mutation.py`: a skill over the ceiling fails; a largest skill of 20,000 under
  the 36,000 ceiling fails the slack check; a control 1,000 under the ceiling passes.
- `scripts/build-agent-skills.sh` and `scripts/tests/test-build-agent-skills-markers.sh`.
- `evals/scenarios/116-load-stage-size-gate.md`.
- Agent Skills specification, https://agentskills.io/specification (instructions under 5,000
  tokens recommended), read 2026-09-23.

## Notes

Generated skill sizes, in chars, before and after this change:

| Skill | Before | After |
|---|---|---|
| slice-closure | 39,940 | 35,760 |
| task-close | 39,197 | 35,713 |
| implementation-plan | 38,531 | 35,459 |
| task-init | 38,137 | 35,382 |
| implement-approved-slice | 36,768 | 35,734 |

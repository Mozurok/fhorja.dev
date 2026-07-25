# ADR-0116: one enforced size budget at the Load stage; retire the per-command token-budget field

- **Status**: Accepted
- **Date**: 2026-07-25
- **Tags**: context-engineering, token-budget, load-stage, progressive-disclosure, lint-enforced-hard-fail, supersedes-adr-0013

## Context

ADR-0013 gave every `commands/<name>.md` a declared `metadata.token-budget` frontmatter field and a lint check that warns, never fails, when the command's current size exceeds it. Two years of drift later, the 2026-07-25 context-engineering frontier sweep measured what that warning actually caught: 83 of 86 flat command files exceed their own declared budget, some by nearly 6000 tokens, and `scripts/lint-commands.sh` has only ever printed a warning about it. The declared budget has been lying at a 96.5% rate with no consequence.

The same sweep's progressive-disclosure angle (A3) found the field was measuring the wrong artifact besides. The Microsoft Agent Framework's Agent Skills documentation states a four-stage pattern with a per-stage budget: advertise at about 100 tokens, then load at "< 5000 tokens recommended" for the skill body, then read-resources and run-scripts on demand. Fhorja already runs a matching pipeline: `commands/<name>.md` is the canonical source, `scripts/build-agent-skills.sh` generates `.claude/skills/<name>/SKILL.md`, and it is the generated file, not the source command file, that an agent's Load stage actually pays for. ADR-0013's field measured the source file's own bytes, a different number from the Load-stage cost, and a check that measures the wrong artifact cannot be trusted even if it were upgraded from warn to fail.

`skills-ref`, the open Agent Skills spec validator this repo already runs in CI at a pinned SHA, was checked directly and confirms it enforces nothing here: it measures line count (its own rule is <=500 lines) and Fhorja's generated skills pass 95/95 with a real maximum of 356 lines. No layer of the existing pipeline enforces a size budget on the artifact the Load stage reads. Four unenforced budgets (the per-command field, the open spec's line rule, `scripts/check-instruction-budget.sh`'s always-warn design, and the stale `scripts/baseline-per-command-tokens-2026-05-15.md` snapshot) do less than one enforced one.

A hard gate cannot ship blind, though. The same measurement found 24 of 95 generated skills already over a 5000-token reference figure, the worst (`task-init`) at roughly 9279 tokens (37117 chars). A gate set at the reference figure would turn CI red on day one for a fifth of the corpus, with no trim wave landed to justify it.

## Decision

`scripts/lint-commands.sh`'s per-command `metadata.token-budget` frontmatter field and its warn-only overrun check are removed. The field no longer exists in any of the 95 command frontmatters. `evals/scripts/structural-evals.py` gains `check_skill_load_budget()`, a hard check registered in the same `CHECKS` registry as the repo's other structural invariants, run in CI by the existing `structural-evals` job: it measures every generated `.claude/skills/<name>/SKILL.md` (4 chars/token approximation, matching the retired check's own arithmetic) against a single ceiling and fails the run if any skill exceeds it.

- **The ceiling is 10000 tokens (40000 chars), a no-regression ceiling, not the 5000-token reference figure.** It is set just above today's measured maximum (`task-init`, about 9279 tokens) so the gate is green on day one, catches any future growth past the current worst case, and is meant to ratchet down toward the 5000-token figure as later trim waves land, never to move up. A future tightening of the number is a normal decision recorded against this ADR's own successor if one is ever needed, not a silent constant edit.
- **The predicate takes a path argument.** `check_skill_load_budget(root=None)` defaults to the real `.claude/skills/` directory (what CI checks) but accepts any directory of `<name>/SKILL.md` fixtures, so the gate itself can be exercised against a deliberately oversized fixture without touching the real corpus. A companion `check_no_retired_frontmatter_field()` asserts the retired field left no trace in any command frontmatter, any generated skill, or the lint validator.
- **This ADR supersedes ADR-0013.** ADR-0013's per-command field and its warn-only mechanism are retired outright rather than amended in place, per this repo's immutability convention (`docs/adr/README.md`): the old decision's document is not rewritten, a new one records what replaces it.

## Consequences

### Positive

- **The gate now measures the artifact that matters.** The Load stage reads `.claude/skills/<name>/SKILL.md`; the enforced budget is finally on that file, not on the source command file ADR-0013 measured.
- **One hard budget replaces four soft ones.** The per-command field's warn-only check, the open spec's unenforced line rule, and the stale baseline snapshot are no longer the only lines of defense; `check_skill_load_budget()` is a genuine CI failure on regression.
- **The predicate is independently testable.** Because it is path-parameterized, `check_skill_load_budget()` was proven to fail against an oversized temp-directory fixture and pass against a small one before it was ever pointed at the real corpus, the negative control TEST_STRATEGY.md's S-3 scenario asks for.
- **No day-one breakage.** The 10000-token ceiling is chosen so every currently generated skill passes; the gate protects against future growth immediately without blocking unrelated work on an expensive trim wave first.

### Negative

- **The ceiling is generous, not tight.** At roughly double today's worst case, the gate does not by itself push the corpus toward the 5000-token reference figure; it only stops things from getting worse. Ratcheting it down is deferred, explicit follow-up work, not automatic.
- **One frontmatter field's worth of teaching surface is gone.** New contributors no longer see a `token-budget:` line modeling cost-awareness while writing a command. The Load-stage ceiling is enforced but is not visible per-command the way the retired field was.

### Neutral

- **A Load-stage ruler does not guard the other surfaces that drifted.** This decision was made with that gap named up front, not discovered after: `CLAUDE.md`, the frontmatter `description` fields (the "advertise" stage), and `scripts/baseline-per-command-tokens-*.md` keep whatever warn-only or absent coverage they already had; nothing here changes them. `EXTERNAL_RESEARCH.md`'s verdict-ledger row 17, "a repeatable rightsize check" that would prevent this whole class of drift from recurring rather than fixing one instance of it, stays open. If it closes, it closes as a future decision that names this ADR, not as an unstated side effect of it.

## Alternatives considered

### Alternative 1: trim first, gate second

Land a wave that brings all 24 over-budget skills under the 5000-token reference figure, then ship the hard gate at that figure.

- **Rejected.** This blocks a cheap, immediately valuable guard (stop the corpus from getting any worse) behind an expensive, separately-scoped cleanup with its own risk profile. The no-regression ceiling gets the protective half shipped now and leaves the trim as an explicit, independently reviewable follow-up.

### Alternative 2: keep measuring the source command file

Upgrade ADR-0013's field from warn to fail in place, still measuring `commands/<name>.md`.

- **Rejected.** The source file is not the artifact an agent's Load stage reads; a hard gate on the wrong file would give a false sense of enforcement while the generated skill, the thing that actually gets loaded, stayed unmeasured. This was the concrete finding that made ADR-0013's field obsolete, not just under-enforced.

### Alternative 3: enforce via the open Agent Skills spec's own line-count rule

Rely on `skills-ref`'s existing <=500-line check instead of adding a token-based gate.

- **Rejected.** Verified directly (`skills-ref` at the CI-pinned SHA passes 95/95; Fhorja's real maximum is 356 lines) that this rule does not correlate tightly enough with token cost to catch the actual regression this ADR targets. Line count and token count diverge on markdown with long paragraphs or dense tables; a token-based ceiling measures the cost the Load stage actually pays.

## References

- `docs/adr/0013-per-command-token-budget.md` (superseded by this ADR; per this repo's immutability convention its own document is not rewritten).
- `docs/adr/0115-contract-fixing-examples-exempt.md` (the prior ADR from the same sweep; same house format, same task).
- `evals/scripts/structural-evals.py` (`check_skill_load_budget()`, `check_no_retired_frontmatter_field()`, both registered in `CHECKS`).
- `scripts/lint-commands.sh` (the retired `metadata.token-budget` frontmatter validator and its warn-only overrun check, both removed).
- `scripts/build-agent-skills.sh` (the generator that produces the artifact this ADR's gate measures).
- `evals/scenarios/116-load-stage-size-gate.md` (the scenario this ADR's mechanism backs).
- Microsoft Agent Framework, Agent Skills progressive disclosure documentation (the vendor-spec per-stage budget figure this decision's ceiling is stated relative to, cited in `EXTERNAL_RESEARCH.md` angle A3, accessed 2026-07-24/25).
- `projects/bmazurok__my-work-tasks/active/2026-07-24_context-engineering-frontier-sweep/DECISIONS.md` D-5 (the locked decision this ADR operationalizes).

## Notes

The 10000-token ceiling is a starting point, not a target. It exists to make the gate shippable without a blocking trim wave and to stop the corpus from growing past its current worst case; it is not evidence that 10000 tokens is an acceptable steady-state Load-stage cost. The 5000-token figure this ADR keeps citing is a vendor reference point from one framework's documentation, not a Fhorja-specific measurement of a behavior change, and DECISIONS.md D-5 records that distinction rather than treating the vendor number as self-justifying. A future ADR that ratchets the ceiling down should record the trim wave that justified the new number, the same way this one records the measurement that justified 10000.

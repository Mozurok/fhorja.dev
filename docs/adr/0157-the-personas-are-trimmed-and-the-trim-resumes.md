# ADR-0157: The persona descriptions are trimmed, and the trim resumes on request

Date: 2026-08-17

Status: Accepted

## Context

Two prior decisions said this would not happen. ADR-0155 D-4 stopped the trim at thirty descriptions
on marginal value: "Return per batch is falling while cost per batch is flat, and the remaining 6356
chars would take six more batches to land about eight more commands of headroom." ADR-0156 D-5 then
closed the verification gap for the nine folder-format personas and said plainly: "This ADR does not
do it: ADR-0155 D-4 stopped the trim on marginal value, and that judgement is unchanged by the gap
closing. What changed is that the option is no longer blocked."

The maintainer then asked for the personas to be trimmed. Both prior statements were judgements about
whether the work was worth doing, not findings about whether it was safe. A judgement of that kind is
the maintainer's to make, so it is superseded by his asking, and this ADR records the outcome rather
than re-arguing the cost.

Eight, not nine: `post-deploy-verifier` was already trimmed in the ADR-0154 batch.

## Decision

**D-1. The eight are trimmed, same method.** Rewritten by hand, every tracked cross-reference
preserved, `Do not use` marker kept, 150-char capability floor respected. What was cut is mostly the
`Activates when` clause, which named literal files and section headings
(`TASK_STATE.md ## Active files in scope lists /migrations/`). The trigger survives in shorter form.
What each persona detects was kept intact, including the pattern lists in `migration-safety-steward`
(NOT NULL without backfill, CREATE INDEX without CONCURRENTLY, and the rest) and
`rls-auth-boundary-auditor` (USING without WITH CHECK, missing tenant predicates, and the rest),
because those lists are the most useful content in both.

| | chars |
|---|---|
| the eight before | 6911 |
| the eight after | 5828 |
| cut | 15.7% |
| Advertise stage | 73355 to 72272 |
| headroom against the 84000 ceiling | 11728 |
| commands that fit at the 827-char mean | about 14 |

**D-2. The lowest cuts are the reference-bound and content-bound ones, again.**
`jtbd-switch-interviewer` cut 8.6 per cent and `rls-auth-boundary-auditor` 13.0. This is the ADR-0155
D-2 finding holding on a new sample: what remains after references and after the substantive
detection list is not prose to remove. 15.7 per cent is the lowest batch rate of the series, after
32.7, 22.8 and 19.9, and the trend is a property of trimming heaviest-first, not of effort.

**D-3. Verified with the complete case set.** The probe was re-emitted against the descriptions as
they now stand, all 98 commands present, the ADR-0156 case set, and the expected-answer mapping
byte-identical to the pre-trim run so the only variable is the text. Result: 100 per cent across
three replicates, zero misroutes, matching the pre-trim 100 per cent, with the shuffled control at 0.
Each of the eight routes 3 of 3 individually. This is the first trim in the series where the
commands edited were themselves under direct per-command verification rather than covered only by the
corpus aggregate.

**D-4. Cumulative state.** 38 of 98 descriptions trimmed. The stage has gone 81065 to 72272 chars,
8793 removed from a surface paid every session, and the ceiling from three commands away to about
fourteen.

## Consequences

- 60 descriptions remain untrimmed, worth roughly 5000 chars on the ADR-0155 D-3 method. The
  marginal-value argument that stopped the trim at thirty applies to them with more force now, since
  the batch rate has fallen again.
- Every persona command now carries both a trimmed description and a per-command routing case, which
  is a stronger position than any of the 89 flat commands were in before ADR-0156.
- Nothing here claims the descriptions read better for a human. The `Activates when` clauses lost
  their literal file paths, which a maintainer debugging a trigger may miss, and no gate in this
  repository measures that.

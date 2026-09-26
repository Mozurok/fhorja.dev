# ADR-0231: The held-out tier is withdrawn

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: in part, [ADR-0175](./0175-held-out-evidence-tier.md): its D-2, the held-out assertion tier, is withdrawn before anything wired it, and its D-3 per-slice evidence file keeps its shape and loses D-2 as its reason. D-1, the shown-evidence rule grounded in measurement, stands.
- **Tags**: evidence, gate-conditions, held-out, layer-1, layer-2, verify-against-rubric, adr-0048, adr-0146, adr-0175, adr-0203

## Context

ADR-0175 made three decisions on 2026-08-30. D-1 grounded the rule that Layer 1 evidence is shown
output on a measurement of this tree. D-2 defined a held-out assertion tier: at least one assertion
that was not in `TEST_STRATEGY.md` when implementation began, proved by the ADR-0146 mechanism of a
pasted search command and its verbatim zero-result output. D-2 said it added no gate itself and would
apply "where a later slice wires it". D-3 put evidence in a per-slice file, and gave D-2 as the reason:
the tier needed somewhere to keep a pasted command and its output.

Three weeks later, this is what exists:

- `commands/implement-approved-slice.md` tells the implementer to append each validated criterion to
  `SLICES/*.evidence.md`, one block per criterion, output verbatim. Nothing reads that file: no
  template, no `slice-closure` step, no line in `wos/gate-conditions.md`.
- No command asks for a held-out assertion and no floor checks for one.

Measured on 2026-09-23 over the gitignored task substrate, with the command pasted so the numbers can
be re-derived:

```
python3 -c "import glob,os;fs=glob.glob('projects/*/*/*/SLICES/*.evidence.md');print('evidence files',len(fs),'task folders',len({os.path.dirname(os.path.dirname(f)) for f in fs}));print('mention held-out',sum(1 for f in fs if 'held-out' in open(f,errors='replace').read().lower() or 'held out' in open(f,errors='replace').read().lower()))"
```

Result: 74 evidence files across 18 task folders, and one of them mentions a held-out assertion. The
evidence file is in use. The tier is not.

The backlog item that raised this (B41) asked whether to wire the tier or withdraw it. Wiring it
would have meant a template, a `slice-closure` read and a closure floor.

## Decision

ADR-0175 D-2 is withdrawn. No command asks for a held-out assertion and no floor will be built on one.

- D-3 stays as it is: one evidence file per slice, written by `implement-approved-slice`, holding each
  validated criterion's output verbatim. Its reason is now D-1. The shown-output rule is what makes
  output worth keeping, and a file per slice lets a reviewer find the output for one criterion
  without reading the whole slice note.
- ADR-0048's decision is unchanged: a passing deterministic gate satisfies Layer 1. Its Status line
  named "held-out assertions" as the thing that superseded its grounding; it now names this ADR as
  well.
- `wos/gate-conditions.md` says that a verdict from `verify-against-rubric` is a Layer 2 signal,
  never Layer 1. That sentence was a separate deliverable of the same planned work and does not
  depend on the tier. It agrees with the Layer 1 definition already on that page, which accepts
  deterministic checks with their real output shown and nothing else.

The reasons follow.

1. The assertion is not held out from the implementer. D-2 asks the agent that writes the code to
   also write the assertion. The pasted zero-result search proves the assertion's text was absent
   from `TEST_STRATEGY.md`. It cannot prove the agent had not seen the assertion, because the agent
   wrote it. In the literature, held out means hidden from the agent. SWE-bench Verified runs tests
   that "are not shown to the agent". EvilGenie removes "a random 30% (up to 10) of the original test
   cases to form a holdout set" and "the agents are not informed about this holdout set".
2. Under ADR-0203 a floor on the tier could only record. That ADR keeps a refusal where missing
   evidence means lost work or where no attester of any kind exists. A slice without a held-out
   assertion has lost nothing, so the floor would add a line to the final report and stop nothing.
   A recorded line about an assertion the implementer wrote for itself checks nothing a reviewer
   could not already see.
3. Hidden tests help less than they appear to, even when they really are hidden. EvilGenie reports
   "only minimal improvement from the use of held out test cases". ImpossibleBench found that
   "hiding tests from agents reduces cheating success rate to near zero, but also degrades performance
   on the original benchmark". Its authors "recommend either hiding test files entirely or
   restricting them to read-only access during implementation", and describe read-only access as "a
   middle ground: it restores legitimate performance while preventing test modification attempts".

Point 3 also says where a real design would start. It would not start from an assertion the
implementer writes. It would make the tests the implementer is given read-only during
implementation, or have an agent that never sees the diff write assertions from the exit criteria
first. Either one is new work that needs its own decision.

## Consequences

### Positive

- The spec stops describing a tier that no command produces and no reader checks.
- D-3's evidence file rests on a rule that is in force, so a reader who asks why the file exists gets
  a live answer.
- A future held-out design starts from the direction the measurement points to, read-only tests or a
  blinded author, instead of from D-2's self-written assertion.

### Negative

- The gap D-2 named is still open. A passing suite still shows that the agent met a target it was
  shown, not that the behavior is right. `approve-plan`'s blinded review (ADR-0208), the blinded
  check on a zero-finding `review-hard` verdict (ADR-0145) and the test-strategy consumption floor
  cover part of it. None of them withholds a test.

### Neutral

- `commands/implement-approved-slice.md` does not change. Its evidence-file bullet never cited D-2.
- ADR-0175 and ADR-0048 keep their bodies. Only their Status lines change, per ADR-0166.
- The 74 evidence files already written stay valid. They hold shown output, which is what D-1 asks for.

## Alternatives considered

### Alternative 1: wire the tier as ADR-0175 planned

- Add an evidence template, have `slice-closure` read the file, and add a closure floor for the
  held-out assertion.
- Rejected: the floor could only record under ADR-0203, and what it recorded would be an assertion the
  implementer wrote for itself. Three pieces of machinery for a check that proves textual novelty and
  nothing else.

### Alternative 2: keep D-2 defined and unwired

- Leave the tier in ADR-0175 for a later slice to pick up.
- Rejected: it has sat unwired for three weeks. A tier the spec defines and nothing runs tells a reader
  that a check exists when it does not.

### Alternative 3: build a real held-out harness now

- Make test files read-only to the implementer during implementation, or have a blinded agent write
  assertions from the exit criteria before the diff exists.
- Rejected for now, not refuted: nothing has measured how often a slice passes its own suite and fails
  an independent check in this tree, so there is no number yet that says the harness would pay for
  itself.

## References

- [ADR-0175](./0175-held-out-evidence-tier.md): D-1 stands, D-2 is withdrawn here, D-3 is regrounded.
- [ADR-0048](./0048-deterministic-gate-evidence.md): the Layer 1 decision, unchanged.
- [ADR-0146](./0146-internal-claim-keyed-grounding.md): the pasted zero-result mechanism D-2 reused.
- [ADR-0203](./0203-floors-stop-waiting-for-a-human.md): the record and refuse split for closure floors.
- `commands/implement-approved-slice.md`: the slice evidence file bullet.
- `wos/gate-conditions.md` → `## Verification layering (the three-layer quality gate)`: the Layer 1
  definition and the verify-against-rubric sentence.
- OpenAI, "Introducing SWE-bench Verified", https://openai.com/index/introducing-swe-bench-verified/
  (quote as recorded by the 2026-09-23 research and its refutation).
- EvilGenie: a Reward Hacking Benchmark, https://arxiv.org/html/2511.21654v2 (read 2026-09-23).
- Zhong, Raghunathan and Carlini, "ImpossibleBench: Measuring LLMs' Propensity of Exploiting Test
  Cases", https://arxiv.org/abs/2510.20270 (read 2026-09-23).

## Notes

What would re-open this:

- a measurement in this tree of slices that passed their own suite and then failed an independent
  check, with the command pasted beside the number;
- a harness that makes the tests the implementer is given read-only during implementation, which is
  ImpossibleBench's middle ground;
- a harness where an agent that has not seen the diff writes assertions from the exit criteria before
  implementation begins.

Any of these is a new decision in a new ADR. It does not restore D-2 as written.

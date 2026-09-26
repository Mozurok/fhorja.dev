# ADR-0226: The blinded reviewer reads one spec section

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: nothing. It adds a third tier to the bootstrap block beside the full and reduced tiers, and leaves ADR-0033, ADR-0145 and ADR-0208 as they are.
- **Tags**: bootstrap, verify-against-rubric, blinded-review, context-budget, adr-0033, adr-0145, adr-0208, b12

## Context

`approve-plan` dispatches one `verify-against-rubric` run on every plan it approves (ADR-0208), and
a zero-finding `review-hard` verdict on product code dispatches another (ADR-0145). Before this
change the reviewer paid the same bootstrap as every other command: the four always-read sections
of `WORKFLOW_OPERATING_SYSTEM.md`, then its own skill, and only then the artifact. Measured on
2026-09-23:

| Section | Chars | Tokens (chars/4) |
|---|---|---|
| `## LLM execution contract` | 11,775 | 2,943 |
| `## Editor mode policy` | 2,359 | 589 |
| `## Global output contract` | 17,982 | 4,495 |
| `## Cross-cutting workflow guardrails` | 12,989 | 3,247 |
| All four | 45,105 | 11,276 |

With the skill at 16,343 chars, a review paid about 15,360 tokens before it read the artifact.
The backlog measured the plan at the tenth percentile at 621 tokens, so the floor was 24 times the
thing being reviewed there, and four times it at the median.

Backlog item B12 first proposed reviewing fewer plans. Measured across 533 plans, every size
trigger fired on most of them (the combined one on 73 per cent), so it would have removed a
quarter of the reviews and carried the risk of that quarter. The same measurement found the cost
in the floor, not in the frequency. The task's research report (option G) and both refutations
kept that finding. The report recommended this tier and the first refutation ends on "Build the
B12 leaf-reviewer bootstrap tier."

The four sections do different jobs. `## Global output contract` is what makes the verdict
readable by the command that dispatched it: the output layout, the vocabulary, `APPLIED`,
`PROPOSED` and `SKIP`, and the handoff. The other three govern an agent that edits the task or
dispatches other commands. The LLM execution contract covers precedence, the read map, repository
structure, naming and task lifecycle. The editor mode policy covers editing modes. The
cross-cutting guardrails cover routing memory, command-less input, material change, substrate
ownership, web access and fleet dispatch. The reviewer's contract is its rubric. It edits no
code, plan or decision. It writes its own verdict entry and one `## Last completed step` line by
rules its command file states, and its one dispatch is the stateless reader that file defines.

## Decision

The bootstrap block gains a leaf-reviewer tier: `verify-against-rubric` reads only
`## Global output contract` from the spec, plus its rubric. The tier is one sentence in the
block's `Bootstrap tiers` bullet with its measured figure, 4,495 tokens. `verify-against-rubric`
declares in its own Operating rules that it runs on the tier, whether a user runs it or
`approve-plan` or `review-hard` dispatches it. That declaration also records that a rule it needs
from a skipped section is written in the command or its shared blocks, not left to the skipped
read.

The tier changes what the reviewer reads from the spec. It does not change what the dispatch
carries. The Step 2 sub-agent still receives the artifact and the rubric and nothing else, and
`approve-plan` and `review-hard` still dispatch with the artifact and the rubric only (ADR-0033,
ADR-0145).

- `verify-against-rubric-fleet` stays on the full tier. Its orchestrator is the sole writer of the
  cohort log and dispatches workers, which is what the skipped sections govern. Its workers
  already read no spec section at all: they receive the artifact, the rubric, the criteria and
  the output schema.
- The block's reduced-tier figure is now machine-checked too. The block had said the reduced
  figure was stated as the subsections dropped because only the full figure was checked. A second
  checked figure made that sentence false, so it came out and `bootstrap-floor-measured` measures
  the reduced tier as the four sections minus the two named subsections.
- Enforcement: the structural check `leaf-reviewer-tier` in `evals/scripts/structural-evals.py`.
  It fails when the block names no leaf-reviewer tier or names any section other than
  `## Global output contract`, when the stated figure drifts more than 3 per cent from the
  section's measured size, when a command the tier names does not declare it or a command it does
  not name does, and when the isolation clause of `verify-against-rubric`, `approve-plan` or
  `review-hard` changes. `evals/scripts/guard-mutation.py` carries one mutation per branch.

## Consequences

### Positive

- A review's fixed floor drops from about 15,360 tokens to about 8,830: 17,982 chars of spec plus
  17,349 chars of skill, against 45,105 plus 16,343 before. That is about 6,530 tokens saved on
  every review. It is slightly less than the 6,779 the three sections measure, because the
  declaration costs the skill about 250 tokens.
- Every review keeps running. The saving comes from what each review reads, so no review a plan
  needed is skipped.
- The reduced tier is no longer the one figure in the block nothing measures.

### Negative

- A rule added later to one of the three skipped sections does not reach the reviewer. If the
  reviewer needs it, it has to be written into `verify-against-rubric` or one of its shared
  blocks.
- The block grew by 3 chars net in the 92 skills that carry it. `slice-closure` is now 60 chars
  under the 40,000-char Load ceiling (ADR-0116), down from 63. The sentence was written to fit:
  the obsolete reduced-tier sentence it replaced paid for it.

### Neutral

- The full-tier figure stays at 11,042 tokens. It measures 11,276 today, a 2.1 per cent gap,
  inside the check's 3 per cent tolerance. `wos/context-budget.md` and one guard mutation quote
  11042, so re-baselining it is a separate change. The reduced figure, about 10,008, measures
  10,241 today, a 2.3 per cent gap.

## Alternatives considered

### Alternative 1: review fewer plans (B12 as first written)

- Dispatch only when a plan has locked decisions to exceed, more than one file in scope, or a
  de-scope.
- Rejected on measurement: the trigger fires on 73 per cent of 533 plans. It removes a quarter of
  the reviews and keeps the risk of the quarter it removes.

### Alternative 2: put the reviewer on the reduced tier

- Reuse the light-weight commands' tier, which skips two guardrail subsections.
- Rejected: it saves about 1,034 tokens against the leaf tier's 6,779. The reduced tier keeps the
  substrate-writing rules, and the seven commands on it keep them because they write substrate
  sections. The reviewer does not.

### Alternative 3: give the Step 2 sub-agent `## Global output contract` as well

- Have the stateless reader also read the output contract, so its verdict is parseable without
  the command's instruction.
- Rejected: it changes what the dispatch carries, which ADR-0033 fixes at the artifact and the
  rubric. The command that reads the verdict already reads the output contract and formats the
  result.

## References

- `commands/_shared/mandatory-context-bootstrap.md` (the `Bootstrap tiers` bullet), propagated by
  `scripts/sync-shared-blocks.sh`.
- `commands/verify-against-rubric.md` (`Bootstrap tier: leaf reviewer` in Operating rules).
- `commands/approve-plan.md` and `commands/review-hard.md` (the two dispatchers, unchanged).
- `evals/scripts/structural-evals.py` (`leaf-reviewer-tier`, and the reduced-tier half of
  `bootstrap-floor-measured`) and `evals/scripts/guard-mutation.py`.
- ADR-0012 (the floor check), ADR-0033 (sub-agent isolation), ADR-0116 (the Load ceiling),
  ADR-0145 (blinded review on a zero-finding verdict), ADR-0208 (plan approval runs the review).

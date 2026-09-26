# Scenario 138: the eval corpus has content floors, not just section headers

- Command under test: `evals/scripts/structural-evals.py` (`scenario-content-floor`)
- Mode: structural (runs in CI on every push)
- Related ADRs: [ADR-0116](../../docs/adr/0116-single-load-stage-size-budget.md) (the ceiling rule this mirrors), [ADR-0136](../../docs/adr/0136-spec-size-non-regression-ceiling.md) (the non-regression pattern).

## Goal

Prove that emptying the eval corpus fails the build.

Before this gate, every structural check over the corpus asked whether a section was present. None asked whether it said anything. Deleting the body of every section in all 135 scenarios, which takes the corpus from roughly 641 KB to roughly 177 KB, left every heading in place and every check green. The regression net would have reported itself healthy while testing nothing.

A heading is not content, and a paragraph is not a rubric. This scenario is the assertion that the corpus has weight: `check_scenario_content_floor` on the bytes, and `check_criteria_content_floor` on whether the criteria section can actually be ticked off.

## Setup

None. The check reads `evals/scenarios/[0-9]*.md` from the repository it runs in.

## Steps

1. Run `python3 evals/scripts/structural-evals.py`.
2. Read the `scenario-content-floor` line.
3. For the negative case, build a fixture directory containing one scenario file of about 100 characters and call `check_scenario_content_floor(root=<fixture>)` directly. Never empty a real scenario to test this.

## Pass criteria

1. `[PASS] scenario-content-floor` appears in the output and no `[FAIL]` line does.
2. Every scenario file is at least `SCENARIO_FLOOR_CHARS` characters, and a file below it is reported by name with both its size and the floor.
3. The corpus mean is at least `CORPUS_MEAN_FLOOR_CHARS`, and a mean below it is reported as a separate finding with its own message, independent of the per-file one.
4. The gate is on the MEAN, not the total. Deprecating a scenario is legitimate and must stay possible; emptying the corpus in bulk is the failure being caught, and only the mean distinguishes them.
5. The two constants move UP over time and never down. Lowering either one is an ADR, not an edit, exactly as the Load-stage ceiling of ADR-0116 works in the opposite direction.
6. The negative proof runs against a fixture passed as `root=`, never against the real tree and never by reverting a commit.
7. Every scenario's criteria section holds at least `CRITERIA_ITEM_FLOOR` enumerable checks, so a rubric cannot decay into a paragraph nobody can tick off.
8. That floor is measured against the same header family `check_corpus_wellformed` accepts, not against the literal `## Pass criteria`. Written against the literal it would paint 55 files red for using an `## Expected ...` variant, and a check that is red by design becomes a waiver.
9. Three is the same floor the spine eval runner requires before it will grade a scenario, so a file that fails this check cannot be scored there either.
10. A criteria item added to satisfy this check derives from a sentence already in the scenario, its expected-behavior prose or a failure mode inverted. An invented criterion is the exact defect these floors exist to catch: presence standing in for truth.

## Failure modes to watch

- A FAIL if the check asserts a total size instead of a mean: that forbids deprecating a scenario, which is ordinary work.
- A FAIL if the per-file finding and the corpus finding are collapsed into one message: they are different defects, one file being a stub versus the corpus being gutted, and a reader needs to know which happened.
- A FAIL if someone lowers a constant to make a red build green. The constants exist to ratchet; lowering one silently is the drift they were installed to catch.
- A FAIL if the negative proof empties a real scenario file to demonstrate the failure.

## Notes

The floors are set below what is on disk, not at it: measured 2026-08-30, the smallest scenario is 1466 characters and the corpus mean is 4750, against floors of 1200 and 4200. The headroom is deliberate. A gate set exactly at the current measurement fires on the next ordinary edit and gets disabled.

## History

- 2026-08-30: scenario authored alongside the check. Corpus measured at 135 files, 641255 chars total, mean 4750, minimum 1466.

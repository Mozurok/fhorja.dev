# ADR-0247: Independent review inputs and evaluated artifacts carry their evidence

- Status: Accepted. Implementation choices rest on provisional P-1, P-2 and P-4; P-4 is high impact because it records cost-related policy, and awaits confirmation before merge.
- Date: 2026-10-03
- Tags: review-inputs, worker-results, evaluation, provenance, ci
- Supersedes: nothing. Clarifies the input and evidence mechanisms of ADR-0033, ADR-0208 and ADR-0242 without changing their isolation or transport decisions.

## Context

A reviewer could be asked whether a cited decision authorized a plan without
receiving that decision's text. A satisfied native worker could omit the commit,
worktree or note that integration subsequently consumed. The local quality
scorer accepted boolean command return codes and contradictory success flags,
and matching submitted expected values did not independently establish fixture
or candidate identity. The new Python contract suites were also absent from the
explicit CI list.

These defects concern the instruments and current contracts. They do not
retrospectively invalidate historical model runs that used different graders,
and repairing them does not establish workflow quality, speed or ROI.

## Decision

Review and integration consume independently checked inputs, and future evaluation evidence carries explicit identity and provenance: quoted cited decisions and brief in the isolated review rubric, verified integration handles for satisfied native workers, independently selected fixtures and declared sources for domain credit, and immutable resolved-policy records and evidence receipts for prospective attempts. The explicit CI list runs the Bash and Python contract suites with their own interpreters and checks actual failure propagation.

- `scripts/build-plan-review-input.sh` carries only live cited D-N and P-N
  entries, the brief and source identity. Provisional choices remain labeled,
  never promoted to authorization. Missing or ambiguous cited inputs refuse
  assembly. `approve-plan` and `verify-against-rubric` keep author history out
  of the dispatch.
- `scripts/validate-implement-fleet-result.sh` checks the returned carrier
  against independently supplied worker, slice, base, scope and worktree facts
  before integration. Satisfied returns require their consumed handles;
  non-satisfied states remain representable without fabricated success handles.
- `evals/lab/quality.py` version 3 rejects improper numeric types and
  contradictory success evidence. Domain coverage requires exact fixture cases,
  expectations and command identity plus unchanged declared source and evaluator
  snapshots. Object key order is harmless; array order and JSON numeric types
  remain distinct. Missing independent inputs withhold domain coverage.
- `evals/lab/attempt.py` freezes resolved policy with per-field provenance and
  six artifact roles before dispatch. Callers hold its digest independently.
  A separate immutable receipt captures post-implementation source and evaluated
  artifacts; scoring verifies the captured inputs and its actual evaluator
  dependencies. Invalid prospective binding earns zero and remains labeled.
- `.github/workflows/lint.yml` explicitly lists all `scripts/tests/test-*.sh`
  and `test-*.py` suites. `test-ci-test-list-coverage.sh` checks executable list
  membership, syntax and the real step's interpreter and aggregate gate using
  disposable Bash and Python stubs, including either language failing alone.

## Consequences

### Positive

- Review authorization is inspectable without leaking the author's history.
- Native integration refuses missing or mismatched facts before merging workers.
- Local valid controls and deliberate faults distinguish bound acceptance from
  matching assertions supplied with unrelated code or contradictory flags.
- New contract suites execute in CI rather than merely existing on disk.

### Negative

- Callers must supply complete declared source sets, command identity and
  independently held digests; omitted inputs deliberately withhold credit.
- The helper does not discover dynamic dependencies, enforce hostile isolation,
  detect edits restored between snapshots, or establish race safety.
- Policy metadata does not authorize spending, enforce provider billing or prove
  observed charges. The later prospective launcher must consume the gate before
  each actual call; a local callback test is not proof that it does.

### Neutral

- Old outputs remain unchanged. New records use new versions and refuse
  overwrite, including an existing output of the current version.
- Auxiliary shell tests use a local fake package manager. Real installation,
  browser behavior and paid-launch enforcement need their own runtime evidence.
- Command names, handoff shapes, worker isolation and historical usage accounting
  remain unchanged. No default optimization treatment is promoted.

## Alternatives considered

### Send the full authoring history to reviewers

Rejected because unrelated findings and rationale undermine the independent
judgment the review is intended to produce. Only cited canonical inputs belong
in its locked rubric.

### Trust schema shape and candidate-authored expectations

Rejected because syntactically valid fields do not prove an existing commit,
a note inside the expected worktree, executed code identity or independently
selected expected outcomes.

### Rewrite historical scores and infer provider limits

Rejected because current instrument repairs are prospective. Historical reports
retain their original grader, and unknown cost or provider policy is recorded
as unknown rather than inferred from tokens or helper defaults.

## References

- `commands/approve-plan.md`, `commands/verify-against-rubric.md`.
- `commands/implement-fleet.md` and its native result validator.
- `evals/lab/README.md`, `attempt.py`, `behavior.py`, `continuity.py`, `quality.py`.
- `.github/workflows/lint.yml`, `scripts/tests/test-ci-test-list-coverage.sh`.
- [ADR-0208](./0208-plan-approval-self-runs.md).
- [ADR-0242](./0242-a-fleet-worker-returns-through-its-own-worktree.md).

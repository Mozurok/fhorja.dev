# ADR-0073: Opt-in self-consistency consensus mode for the two high-stakes review commands

- **Status**: Accepted
- **Date**: 2026-07-01
- **Tags**: self-consistency, consensus-of-n, security-review, review-hard, review, opt-in, additive, ecosystem-adoption

## Context

A single review pass over a diff is one sample of the model's judgment. On high-stakes diffs (the surface that `security-review` and `review-hard` exist for) a single sample can miss a real finding or over-weight a spurious one, and the miss is invisible because there is nothing to compare against. Self-Consistency (Wang et al. 2022) showed that sampling several independent reasoning paths over the same input and keeping the answer they agree on beats a single greedy pass on hard reasoning tasks.

The WOS already has the merge machinery for this. The `consensus-of-N` strategy in `commands/_shared/worker-contract.md`, wired through `commands/_shared/orchestrator-bootstrap.md`, requires several workers to agree on a deliverable before it is treated as canonical. Nothing in the two review commands exposed that machinery to a human who wants extra confidence on a risky change; the only way to get a second opinion was to re-run the command by hand and eyeball the two reports.

## Decision

Add an opt-in `--consistency N` consensus mode to `security-review` and `review-hard`, OFF by default. Without the flag both commands behave exactly as today: one pass, one report. With `--consistency N`, the command runs N independent review passes with fresh context over the same diff, then merges the findings by consensus-of-N:

- A finding that appears in at least `ceil(N/2)` passes is high-confidence.
- A finding that appears in fewer passes is a singleton: kept as advisory and labeled, never silently dropped.

The advisory-not-dropped rule is the one deliberate deviation from the strict `consensus-of-N` merge strategy (which drops dissenters with `event=consensus_drop`). In a review context a labeled low-confidence finding is safer than a silent omission, so the mode keeps singletons on the record.

A cost guard is stated inline in both commands: total review cost multiplies by N, so the mode is strictly opt-in and `N=3` is the recommended setting, reserved for high-stakes changes where the added confidence is worth the spend.

The mode reuses the existing consensus-of-N infrastructure. `wos/sub-agent-orchestration.md` documents self-consistency as that strategy applied to a single artifact reviewed N times, distinct from `verify-against-rubric-fleet`, which runs N different artifacts against one rubric with a `union` merge.

Opt-in rather than default is deliberate, following the ADR-0063 (`--tdd`) precedent: multiplying review cost by N on every review would burn budget on low-stakes diffs that a single pass already covers. The trigger stays in the user's hands.

## Consequences

- No `count:commands` change: this is a mode of two existing commands, not a new command, so no four-registry registration is required.
- Skill regeneration for `security-review` and `review-hard` (via `scripts/build-agent-skills.sh`) is deferred to a later slice. The canonical `commands/*.md` files are the source of truth and are updated here; the generated `.claude/skills/<name>/SKILL.md` files will be rebuilt when the deferred slice runs.
- Additive: the default single-pass behavior is unchanged for both commands, and the mode composes with each command's existing output contract (findings classification, no-op rule, handoff).
- The mode reuses the existing consensus-of-N merge strategy rather than adding a new orchestration primitive, so the worker and orchestrator contracts are unchanged.

## Alternatives considered

- Make N-pass review the default. Rejected: it multiplies cost by N on every review, including the low-stakes and documentation-shaped diffs where a single pass is already enough. The ADR-0063 opt-in precedent applies.
- A dedicated fleet command for self-consistency. Rejected: self-consistency over one artifact is a merge-strategy application of infrastructure that already exists, not a new fan-out shape. A mode on the two commands that need it keeps the surface small and the count markers untouched.
- Drop singletons per the strict consensus-of-N rule. Rejected for the review surface: a dropped dissenting finding is exactly the silent miss the review commands exist to prevent, so singletons are kept as labeled advisory instead.

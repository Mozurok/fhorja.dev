# ADR-0056: A deliverable-coverage ledger so user-named deliverables survive brief-to-closure

- **Status**: Accepted
- **Date**: 2026-06-26
- **Tags**: deliverable-coverage, no-silent-de-scope, completeness-check, task-memory, shared-block, hard-gate, additive, dogfood

## Context

Twice in close succession the workflow silently dropped a deliverable the user had named in a brief, and no command caught it. The user's own review did.

- Careers-page session (2026-06-23): a captured input was never consumed; the brief asked for work that quietly fell out of scope (see memory `project_wos_careers-page_dogfooding_audit`).
- Human-knowledge-layer session (2026-06-26): the brief named two concrete deliverables, the analysis of ten external references and an Obsidian-style visual organization. The first design de-scoped both, anchoring on a "no external app dependency" stance, and shipped without them. The user caught the omission at review (see memory `feedback_brief_coverage_gate`).

A two-round self-audit of all 82 commands followed. It refuted roughly 63 of 64 raw findings: every command, read in isolation, is defensible and passes the buck to a neighbor. The gap is systemic, not local. No single command owns the invariant "a deliverable the user named is still accounted for at closure," so the deliverable falls through the seam between intake, scoping, and closure.

The audit also found that the right pattern already exists, once. `impact-analysis` carries a multi-repo completeness rule: "Reject silent omission of any repo listed in `## Repositories`." It is a structural check over an enumerated substrate section. The fix is to generalize that one good pattern from repositories to deliverables, and to give it a home, an enforcement point, and a regression test so it cannot quietly erode.

One concrete local defect surfaced alongside the systemic gap: `stack-currency-check` did not enumerate every requested framework or mark the ones it could not verify, so an unverifiable framework could vanish from its result. That is the same silent-omission failure at the command level.

## Decision

Introduce a deliverable-coverage ledger as an additive invariant across the intake, scoping, and closure command surface. A deliverable a user names in a brief is tracked from intake to closure and cannot be silently dropped; it is either delivered or explicitly de-scoped with a recorded reason.

Concretely (locked as D-1 through D-5 in the task's `DECISIONS.md`):

- **D-1 (generalize the guard).** The existing repo-level "reject silent omission of any repo in `## Repositories`" completeness check is generalized from repositories to user-named deliverables. A deliverable named in a brief is not silently dropped between intake and closure.
- **D-2 (the local defect).** `stack-currency-check` enumerates every requested framework and marks each `verified | unverified:<reason>`, never silently omitting one it could not verify.
- **D-3 (hybrid shape).** The closure reconcile rule is a single shared block, `commands/_shared/deliverable-reconcile.md`, consumed by `review-hard`, `where-we-at`, `slice-closure`, and `task-close` (propagated by `scripts/sync-shared-blocks.sh`). The intake-seed, scoping, and captured-not-consumed rules stay inline in their own commands, because they are phase-specific.
- **D-4 (home).** The ledger is a `## Requested deliverables` section in `TASK_STATE.md`, one row per named deliverable tagged `in-scope | de-scoped:<reason> | done`, seeded at `task-init` and pointer-linked from `SOURCE_OF_TRUTH.md` rather than duplicated.
- **D-5 (lifecycle-aware gate).** The reconcile gate is lifecycle-aware. In a finalization context (`task-close`, or `review-hard` as the pre-PR final pass), if a `## Requested deliverables` row is neither `done` nor `de-scoped:<reason>` in `DECISIONS.md`, the output is invalid. In a checkpoint context (`where-we-at`, `slice-closure`), a not-yet-done `in-scope` row is reported as remaining work, not invalidated (that is the normal mid-task state). A silent omission (a brief deliverable with no ledger row, or a row dropped without a recorded de-scope) is flagged in every context. The `- none named` sentinel is exempt everywhere. When `task-init-fleet` decomposes a brief and a named work-stream maps to no sub-task, it emits `NO_OP_TRACE` and routes to `decision-interview`. When `impact-analysis` or `decision-interview` recommends a direction that drops a ledger row, it surfaces that de-scope as an explicit decision. (The original draft hard-gated all four commands uniformly; review found that over-fired on in-progress checkpoints and on no-deliverable tasks, so the gate was refined before first commit.)

A de-scope is allowed. What is rejected is silence. The hard gate fails only at finalization, and only when a named deliverable is neither delivered nor recorded as de-scoped with a reason; checkpoints report remaining deliverables without failing. The rule no-ops when `## Requested deliverables` is absent (legacy tasks predate the ledger) or when its only row is the `- none named` sentinel, so the change is additive and does not break existing task contracts.

Enforcement points: the shared block `commands/_shared/deliverable-reconcile.md`; the inline rules in `task-init`, `task-init-fleet`, `impact-analysis`, `decision-interview`, `capture-references`, `external-research`, and `stack-currency-check`; and regression scenario `evals/scenarios/75-deliverable-silently-dropped.md`.

## Consequences

### Positive

- A deliverable a user names is now a tracked invariant, not a thing that survives on attention. The exact failure that happened twice this month is caught by a gate rather than by the user's review.
- The fix reuses a proven pattern (the repo completeness check) rather than inventing a new mechanism, so it is easy to reason about and to teach.
- A single shared block carries the closure rule to four commands, so the four cannot drift apart (the drift ADR-0029 guards against).
- The ledger is observable: a reviewer or an agent can check a named deliverable against the delivered work and the `DECISIONS.md` de-scope record, deterministically.

### Negative

- More ceremony at intake: `task-init` now seeds a `## Requested deliverables` section, and closure commands carry one more reconcile step. For a tiny task this is overhead.
- The bound of "deliverable" is a judgment call. Too loose and the ledger fills with every implied sub-task and becomes noise; the rule deliberately scopes a deliverable to a concrete thing the user named (an artifact to produce, an input to analyze), not every inferred step.
- Eight command contracts plus a shared block, an ADR, and an eval change together. The blast radius is wide even though each edit is small and additive.

### Neutral

- The ledger lives in `TASK_STATE.md`, which closure commands already read, so no new file is introduced for the common case.
- Delivery commands (`pr-package`, `delivery-asset`, `team-update`) gain no own guard; they are defensibly scoped to describe the real diff or state and inherit protection from the closure reconcile.

## Alternatives considered

### Alternative 1: one big shared block injected into all consumers

- A single block carrying every rule (seed, scope, reconcile, consume), injected into all of the roughly eleven consumers.
- Rejected: the rules are phase-specific. Intake seeds, scoping enforces, closure reconciles, capture points to a consumer. One block does not fit all four phases and would inject irrelevant text into each consumer. Only the closure reconcile rule has enough identical consumers (four) to justify a shared block; the rest stay inline (D-3).

### Alternative 2: all inline, no shared block

- Write the reconcile rule directly into each of the four closure commands.
- Rejected: four hand-maintained copies of the same definition-of-done line is exactly the drift ADR-0029 exists to prevent. The closure rule goes in one shared block; only the genuinely phase-specific rules stay inline.

### Alternative 3: a soft advisory instead of a hard gate

- Surface an unreconciled deliverable as a warning, not invalid output.
- Rejected: a soft, attention-based guard is what failed this session. The existing repo rule uses "invalid output" strength; the deliverable rule mirrors it (D-5). A de-scope is still allowed, it just has to be recorded.

## References

- `commands/_shared/deliverable-reconcile.md` (the closure reconcile rule; the shared block).
- `commands/task-init.md`, `commands/task-init-fleet.md` (intake seed and decomposition-coverage check).
- `commands/impact-analysis.md`, `commands/decision-interview.md` (the scoping no-silent-omission pass).
- `commands/capture-references.md`, `commands/external-research.md` (the `Consumes-by:` pointer).
- `commands/stack-currency-check.md` (D-2, the enumerate-and-mark fix).
- `evals/scenarios/75-deliverable-silently-dropped.md` (the regression test).
- ADR-0029 (lint drift guards: shared-block markers, count markers, index rows).
- ADR-0031 (EARS for the contract sentences).
- Memories `feedback_brief_coverage_gate`, `project_wos_careers-page_dogfooding_audit` (the two incidents that prompted this).

## Notes

The task that produced this ADR dogfooded the mechanism it defines: its own `TASK_STATE.md` carried a `## Requested deliverables` ledger (rows D-A through D-G) from intake, so the deliverables that built the ledger were themselves tracked by a ledger. The systemic finding (no command owns deliverable coverage; each defensibly passes the buck) is the load-bearing rationale; revisit if a future command is added that takes ownership of cross-command completeness, which would let the inline rules collapse into it.

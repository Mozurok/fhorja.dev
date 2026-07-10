# ADR-0040: Single-Writer-Per-Folder Exception to ADR-0038

- **Status:** Accepted
- **Date:** 2026-06-05
- **Tags:** orchestration, workflow-tool, single-writer, scope-disjointness, adr-amendment, fleet-orchestration

## Context

ADR-0038 establishes that substrate writes (canonical task artifacts under `projects/<client>__<project>/active/...`) must flow through a deterministic apply step. The intent of Rule 2 is to prevent two workers from racing on the same file and producing non-deterministic or partially merged substrate.

The `task-init-fleet` command, audited under P2-C on 2026-06-05, dispatches N workers in parallel. Each worker is responsible for initializing one task folder of the shape `projects/<client>__<project>/active/YYYY-MM-DD_<slug-N>/`, and writes directly into that folder (README.md, TASK_STATE.md, SOURCE_OF_TRUTH.md, DECISIONS.md, IMPLEMENTATION_PLAN.md). There is no orchestrator-side merge step: workers do not contend, because their target folders are disjoint by construction.

On a literal read, this looks like a violation of ADR-0038 Rule 2: substrate is written by the worker, not by a centralized apply step in the orchestrator. The audit finding is that, in this specific shape, the worker IS the apply step for its own disjoint folder, and a merge step would be a no-op.

The audit also clarified the safety conditions:

1. Each worker's target folder is unique across the fleet.
2. The orchestrator validates scope disjointness in Step 2 of `task-init-fleet` (the scope-disjointness check) BEFORE any worker is dispatched.
3. No two workers share a subpath, so no concurrent file can ever be touched by more than one writer.
4. There is no shared mutable state across worker folders that would require a downstream reconcile.

Without this exception, `task-init-fleet` would either need a synthetic merge step (which adds latency without changing the output) or would be blocked by an over-broad reading of ADR-0038.

## Decision

Single-writer-per-folder is a permitted, narrow exception to ADR-0038 Rule 2 when ALL of the following hold:

1. **Pre-dispatch disjointness check.** Worker scope disjointness is validated by the orchestrator before any worker is launched, either statically (declared scopes) or by an explicit orchestrator check. For `task-init-fleet` this is Step 2 (scope-disjointness check).
2. **Canonical folder boundary.** The folder boundary is canonical: one folder is owned by exactly one worker, and there are no shared subpaths between workers. A worker may not write outside its declared folder.
3. **Folder IS the worker scope.** The orchestrator does NOT delegate substrate-shaping policy to the worker beyond its own folder. The worker is the apply step for the folder it owns, and the folder is its full write scope.

When these conditions hold, the worker's direct write IS the deterministic apply step required by ADR-0038, and no orchestrator-side merge is necessary.

If any condition fails (overlapping scopes, shared subpaths, worker writes leaking outside its folder, or post-hoc cross-folder reconcile required), the exception does not apply and ADR-0038 Rule 2 governs in full -- the work must go through a centralized apply step.

## Consequences

Positive:

- `task-init-fleet` is unblocked without inventing a synthetic merge step.
- The exception is narrow and conditioned on checks the orchestrator already performs.
- Future fleet-style commands have a clear rule for whether they qualify for the exception.

Negative:

- The disjointness check becomes load-bearing. If it regresses, ADR-0038's race-safety guarantee silently regresses with it. The check must be covered by tests and treated as a canonical invariant.
- Reviewers must now distinguish two valid substrate-write shapes (centralized apply vs single-writer-per-folder), which increases the cognitive load of ADR-0038 audits.

Neutral:

- The exception is structural, not behavioral: it does not change what workers write, only who is allowed to write it directly.

## Alternatives Considered

1. **Force a merge step in `task-init-fleet`.** Rejected: the merge would be a no-op because folders are disjoint, and it would add latency and orchestrator complexity for no safety gain.
2. **Loosen ADR-0038 Rule 2 globally.** Rejected: ADR-0038's guarantee is valuable for non-disjoint workflows (e.g., cross-cutting substrate edits) and should not be weakened beyond this narrow case.
3. **Declare `task-init-fleet` out of ADR-0038 scope.** Rejected: substrate writes ARE in scope; the right answer is a named, conditioned exception, not a carve-out.

## References

- ADR-0038 (parent): substrate writes through a deterministic apply step.
- ADR-0007: project-level memory and folder structure (`projects/<client>__<project>/active/...`).
- `task-init-fleet` P2-C audit finding, 2026-06-05.

## Notes

This ADR is intentionally narrow. It does not authorize multi-writer-per-folder, cross-folder reconciliation, or worker-side substrate shaping outside the worker's own folder. New fleet-style commands must explicitly demonstrate the three conditions above before claiming this exception.

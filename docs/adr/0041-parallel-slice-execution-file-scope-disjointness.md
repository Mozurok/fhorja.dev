# ADR-0041: Parallel Slice Execution and the File-Scope Disjointness Gate

- **Status:** Accepted (orchestrator command `implement-fleet` ships as a pilot pending lived evidence)
- **Date:** 2026-06-09
- **Tags:** orchestration, workflow-tool, execution, slice-parallelism, scope-disjointness, integration-gate, adr-amendment, fleet-orchestration

## Context

ADR-0038 makes the Workflow tool the canonical primitive for parallel subagent dispatch. ADR-0039 fixes the empirical batch sweet spot (15-25 agents, 300-500 word prompts, an explicit StructuredOutput reminder). ADR-0040 carves out a single-writer-per-folder exception for `task-init-fleet`, where each worker owns a disjoint task folder under `projects/<client>__<project>/active/...` and the worker IS the apply step for its own folder.

All three target either discovery (research fan-out) or substrate (task-folder creation). Execution of product-code slices has stayed strictly sequential: `implement-approved-slice` is "the single official execution path," one approved slice at a time. A 2026-06-09 review of a lived client-pilot session confirmed the gap empirically: the workflow fanned out research into a 9-agent `external-research-fleet` batch, but implemented all 8 product slices in a single linear pass. The plan for that task already carried per-slice `Scope` and `Order safety` lines, so the dependency information needed to parallelize independent slices was being produced and then ignored.

The instinct to parallelize independent slices is sound, but product code differs from substrate in one load-bearing way. `task-init-fleet` workers write disjoint NEW folders, so the cross-worker merge is a no-op and there is nothing to compile. Product-code slices write into a SHARED repository with a shared build, type, and test surface. Two slices can touch entirely disjoint files and still fail to integrate: one slice adds a symbol or type that another imports, a shared barrel export changes, or a generated artifact (migration, lockfile, codegen output) is implicitly shared. File-scope disjointness guarantees a conflict-free file merge; it does NOT guarantee semantic integration.

So parallel slice execution needs two things that the existing fleets do not: a disjointness gate generalized from folder scope to product-code file scope, and a mandatory integration step after each parallel wave.

## Decision

Parallel execution of approved implementation slices is permitted when ALL of the following hold, validated by the orchestrator (`implement-fleet`) BEFORE any worker is dispatched:

1. **File-scope disjointness.** The slices in a wave declare `Scope` file sets (from `IMPLEMENTATION_PLAN.md`) that are pairwise disjoint. No file appears in more than one slice's scope in the same wave. This generalizes ADR-0040 condition 1 from a folder boundary to a file-set boundary.
2. **No shared coupling surface.** No two slices in a wave share an implicit-coupling artifact even if their explicit file lists are disjoint: a database migration or schema file, a dependency lockfile, a codegen output, or a barrel/index export that re-exports symbols. These are treated as shared scope and force serialization.
3. **Dependencies satisfied.** A slice is eligible for a wave only when every slice in its `Depends-on` set has already completed in an earlier wave. Waves are the topological layering of the slice DAG.
4. **Worktree isolation.** Each worker runs in its own git worktree off the shared base. Parallel writes cannot collide on the filesystem. Because scopes are disjoint (condition 1), merging the worktrees back is conflict-free by construction (the ADR-0040 "merge is a no-op" property, at file-set granularity).
5. **Integration gate after every wave.** After merging a wave's worktrees, the orchestrator runs build, typecheck, and the affected test subset on the INTEGRATED tree. The wave is not closed and the next wave is not dispatched until the integration gate passes. A failing gate stops the fleet and surfaces the failure; it is never skipped.

When any condition fails, the exception does not apply: the affected slices run sequentially via `implement-approved-slice`. If the whole slice DAG is a chain (every wave has size one), `implement-fleet` returns a NO_OP_TRACE and routes to sequential `implement-approved-slice` rather than pretending to parallelize.

The orchestrator reports the realized wave width honestly. Cohesive features tend to be deep chains, so many runs will serialize most or all slices; the command states this rather than implying a speedup that the dependency graph does not allow.

`implement-fleet` orchestrates `implement-approved-slice` units; it does not replace them. `implement-approved-slice` remains the canonical single-slice execution path and the fallback. Each worker runs that contract (minimal scoped change, exit-criteria check, slice notes) for exactly one slice, confined to that slice's declared `Scope`. Each worker is the sole writer of its own `SLICES/<NN>_<slug>.md` (single-writer-per-folder, per ADR-0040); the shared `TASK_STATE.md` is written only by the orchestrator (ADR-0038 Rule 2 sequential apply step).

## Consequences

Positive:

- Tasks with genuinely independent slices (standalone modules, the same pattern repeated across disjoint files) run their independent branches concurrently instead of serially.
- The disjointness data already exists: `implementation-plan` is extended to emit machine-readable `Scope` and `Depends-on` per slice plus a computed `## Execution waves` section, which makes parallelizability visible even when `implement-fleet` is not used.
- The doctrine reuses checks the orchestrator already has to perform, mirroring `task-init-fleet`.

Negative:

- The integration gate adds real cost and is the most likely failure point. File-scope disjointness is necessary but not sufficient for clean integration; the gate is where semantic coupling surfaces, and a failing gate means the wave's work has to be reconciled before proceeding.
- The disjointness and coupling checks become load-bearing. An under-declared `Scope` (a slice that touches a file it did not list) can leak past the file-set check; the worktree isolation contains the filesystem blast radius, but the integration gate is the real backstop.
- Two valid execution shapes now exist (sequential `implement-approved-slice` and parallel `implement-fleet`), which increases routing surface. The mitigation is that `implement-fleet` falls back to the sequential path whenever the gate cannot be satisfied, so the sequential path stays the default for cohesive work.

Neutral:

- The realized speedup is bounded by the width of the slice DAG (Amdahl). The capability does not make a deep chain faster; it only helps wide graphs. The command is explicit about this.

## Alternatives Considered

1. **A parallel mode flag on `implement-approved-slice` instead of a new command.** Rejected: it would fold orchestration into the single-slice execution unit and contradict that command's "single official execution path" framing. The repo's established shape is a separate `*-fleet` orchestrator (`task-init-fleet`, `screen-spec-fleet`, etc.); `implement-fleet` follows it.
2. **In-place disjoint writes (no worktree).** Rejected: it trusts `Scope` declarations completely; a single mis-declared or implicitly shared file corrupts the shared working tree mid-fleet. Worktree isolation contains the blast radius for the cost of worktree setup per worker.
3. **Skip the integration gate and rely on file-scope disjointness alone.** Rejected: disjoint files routinely share a compile/type/test surface; without an integrated build and test, semantic breakage ships silently. This is the single most important difference from the substrate fleets and cannot be dropped.
4. **Loosen ADR-0040 globally to cover product code.** Rejected: ADR-0040 is deliberately narrow (substrate folders, no build surface). Product-code parallelism needs its own conditions (the coupling check and the integration gate), so it gets its own ADR rather than a weakened parent.

## References

- ADR-0038: Workflow tool as the canonical parallel-orchestration primitive.
- ADR-0039: empirical batch dispatch sizing (sweet spot, prompt length, StructuredOutput reminder).
- ADR-0040 (parent): single-writer-per-folder exception for `task-init-fleet`.
- ADR-0026: APPLIED-by-default for `implement-approved-slice` in Agent mode.
- `commands/implement-fleet.md` (orchestrator), `commands/implement-approved-slice.md` (worker unit), `commands/implementation-plan.md` (`Scope` / `Depends-on` / `## Execution waves` source).
- 2026-06-09 client-pilot session review (the empirical motivation; research was fanned out, execution was not).

## Notes

This ADR is narrow. It authorizes parallel execution of approved slices under the five conditions above and nothing more. It does not authorize parallel writes to a shared file, skipping the integration gate, or worker-side scope expansion beyond a slice's declared `Scope`. `implement-fleet` ships as a pilot; promotion criteria are a first lived run with the realized wave width recorded and a passing integration gate on a wave of size two or greater.

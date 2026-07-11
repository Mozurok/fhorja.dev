# ADR-0094: Plan-adherence and flow-conformance check over the VERIFICATION_LOG trace

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: plan-adherence, trace-based-eval, flow-conformance, verification-log, state-reconcile, dry-run, dogfood-driven, currency-adoption, grounded-2026

## Context

Second wave of the 2026-07-11 currency adoption (see `projects/bmazurok__my-work-tasks/REFERENCES.md`, 2026-07-11 scan). The 2026 agent-evaluation literature (the confident-ai agent-evals entry) makes trace-based evaluation and plan adherence a first-class dimension: the best evals check the sequence of steps an agent took and whether it stayed on the intended workflow, not only whether it eventually produced an answer.

The WOS already produces exactly this trace. Every substrate write appends to the append-only `.wos/VERIFICATION_LOG.jsonl` with an owner (the command), a run_id, a timestamp, and a section. That is a complete, ordered record of which commands ran and what they wrote. What the WOS did not have was an evaluation of that trace against the approved plan: nothing checked that the slices actually executed matched the approved `IMPLEMENTATION_PLAN`, or that the command sequence obeyed the workflow gates. This wave adds that check. It builds directly on ADR-0092 (the flow audit reads the same trace substrate).

## Decision

`scripts/plan-adherence.py` is a read-only, dry-run checker over one task folder. It runs two checks:

**(a) Slice-set conformance.** It extracts the planned units from the `### Slice N` / `### Wave N` headings in `IMPLEMENTATION_PLAN.md`, extracts the executed units from the `## Current status` completed section of `TASK_STATE.md` plus the log reason fields, and reports planned-but-skipped and executed-but-unplanned units. A mismatch is a slice-set FAIL.

**(b) Command-sequence conformance.** From the ordered owner sequence in the trace it enforces workflow gates: implementation (`implement-approved-slice` / `implement-fleet` / `implement-slice-complement`) must be preceded by an `approve-plan` owner (a missing one is a WARN, since approval can be inline; an `approve-plan` that appears after implementation is a FAIL); `implementation-plan` must precede `approve-plan`; and `task-close` must be terminal (any write after it is a FAIL).

The tool prints a report with a `VERDICT: CONFORMANT | DRIFT` line, writes nothing, and exits 0 by default; `--strict` exits 1 on drift for CI use. `state-reconcile` folds its verdict into the drift report (a slice-set FAIL is at least IMPORTANT drift, a command-sequence FAIL is BLOCKING). It is a closure or checkpoint tool, not a mid-slice check.

## Consequences

- Execution drift becomes detectable: a task that silently skipped a planned slice, ran an unplanned one, or violated a workflow gate is caught by a grounded, trace-based check rather than by memory.
- It leverages WOS-unique infrastructure (the provenance trace of ADR-0034 and ADR-0092) to satisfy a 2026 eval best-practice, and reuses the same read-only, dry-run, exit-0-by-default shape as the flow audit.
- Limitation, stated honestly: the check needs slice-anchored completion evidence in `TASK_STATE.md`. A slice-set FAIL can mean the work is incomplete OR that completion was not recorded per slice number; the report distinguishes the two with a note, and the fix for the latter is better closure hygiene (record slice N done), which is itself a quality gain.
- Additive and model-agnostic: a new script plus one routing note in `state-reconcile`, no new command, no model names, no command-contract change.

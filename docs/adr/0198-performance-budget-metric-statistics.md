# ADR-0198: Performance budgets use metric-specific statistics

- **Status**: Accepted
- **Date**: 2026-09-09
- **Tags**: performance-budget, statistics, percentiles, aggregation-window, output-contract
- **Supersedes**: None. No earlier ADR defines this table field.

## Context

`performance-budget` asks for latency percentiles alongside error rates, payload and bundle sizes,
frame budgets, counts and configured constants. Its output table nevertheless names the field
`percentile` and requires p75 or p95 on every row. Scenario 69 repeats that requirement. The
contract therefore asks non-distribution metrics to report a percentile that has no measurement
meaning, while Step 2 separately permits p50, p95 or p99 for API latency.

The batch 8 audit identified the contradiction, but the first proposed command-only relaxation
was refuted because scenario 69 and the definition of done would still reject the corrected
artifact. The task's D-7 decision selected a coordinated schema and eval update.

## Decision

`PERFORMANCE_BUDGET.md` uses a `statistic` column. A distribution names its percentile, population
and window; a rate or ratio names its aggregation window; a fixed or snapshot metric names the
applicable maximum, total, per-build, per-frame, configured constant or binary invariant. Core Web
Vitals retain p75 and latency distributions accept the selected p50, p95 or p99. A bare average
does not replace a required distribution tail. Non-distribution metrics do not invent percentiles
or use `N/A` when a concrete measurement basis can be named. The canonical command,
`frontend-system-design`, command-role summary and scenario 69 enforce the same contract.

## Consequences

### Positive

- Every budget row states a measurement model a reader or gate can check.
- Distribution tails remain explicit without assigning meaningless percentiles to ratios, counts
  or snapshots.
- The command, sibling guidance and semantic eval agree on one output schema.

### Negative

- Consumers that read the table by column name must move from `percentile` to `statistic`.
- A statistic value can be longer because distributions carry population and window as well as
  their percentile.

### Neutral

- Repository search found no executable parser of the table schema; out-of-repository consumers
  are outside that evidence.
- Threshold sources, pending-baseline marking, regression actions and gate routing do not change.

## Alternatives considered

### Keep percentile and allow N/A

- Distribution rows would retain their current field and other metrics would write `N/A`.
- Rejected because the column would still mix incompatible concepts and `N/A` would hide the
  concrete measurement basis a gate needs.

## References

- `commands/performance-budget/SKILL.md`, output schema and metric rules.
- `commands/frontend-system-design.md`, performance-design composition rule.
- `evals/scenarios/69-performance-budget.md`, semantic regression contract.
- `wos/command-roles.md`, command-role summary.
- `projects/bmazurok__my-work-tasks/active/2026-09-03_command-catalog-quality-audit/DECISIONS.md`, D-7.
- `audit-batch-8.json` and `verify-batch-8.json`, finding and adversarial verdict.

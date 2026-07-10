# Proposal: Integrate `scan-substrate-orphans.py` into `repo-consistency-sweep` Step 7

**Status:** Draft
**Owner:** Fhorja Engine
**Date:** 2026-06-05
**Related:** commit `5840755` (detector), commit `615c6bb` (bug-class), ADR-0029 (drift-guard pattern)

## Context

Today, Step 7 of `commands/repo-consistency-sweep.md` runs two substrate-integrity probes:

1. `scripts/scan-substrate-headers.sh` -- surfaces canonical-header drift across `wos/` and `commands/`.
2. `scripts/verify-log-validator.py` -- checks verification-log shape against ADR-0014.

Both produce counters that the sweep snapshots into `REVIEW_SWEEPS/SWEEP_<ts>.md` and that the e2e assertion `evals/e2e/assertions/09-repo-consistency-sweep.sh` caps at expected thresholds.

In commit `5840755` we shipped a third probe -- `scripts/scan-substrate-orphans.py` -- which detects substrate bullets orphaned from their parent canonical sections (the failure class formalized by the bug-class added in `615c6bb`). The script currently runs standalone: it is not wired into the sweep, not snapshotted, and not asserted. As a result, regressions of the orphan class can land on `main` without surfacing in CI or in sweep reports.

## Proposal

### Placement in Step 7

Insert the orphan scan immediately **after** `scan-substrate-headers.sh` and **before** `verify-log-validator.py`. The ordering reflects dependency: header drift can mask orphan detection (if a parent header is renamed, every child bullet looks orphaned), so headers are stabilized first.

### Failure semantics

`orphan_count > 0` produces a **WARN**, not a **FAIL** -- mirroring the `header_drift` treatment established in ADR-0029’s drift-guard pattern. Rationale:

- The sweep is a diagnostic surface; hard-failing the sweep on legacy-orphan baselines would block unrelated work.
- The e2e assertion (below) is where the actual gate lives.

### Snapshot capture

`SWEEP_<ts>.md` gains a new counter line alongside `header_drift_count` and `verify_log_invalid_count`:

```
substrate_bullet_orphan_count: <N>
substrate_bullet_orphan_paths: <comma-separated relative paths>
```

The paths field is truncated to the first 10 entries; full output is written to `REVIEW_SWEEPS/SWEEP_<ts>.orphans.txt` for diffability.

### E2E assertion

Extend `evals/e2e/assertions/09-repo-consistency-sweep.sh` with an orphan-cap block that mirrors the existing `header_drift` cap pattern:

```bash
expected_max_orphans="${EXPECTED_MAX_SUBSTRATE_ORPHANS:-0}"
actual=$(grep -E '^substrate_bullet_orphan_count:' "$sweep_md" | awk '{print $2}')
[ "$actual" -le "$expected_max_orphans" ] || fail "orphan count $actual > $expected_max_orphans"
```

### Legacy-orphan tolerance

Introduce `OPT_OUT_ORPHAN_BASELINE=1` as an env override read by the sweep (not by the detector itself). When set, the sweep emits the counter and snapshot but skips the WARN escalation. This unblocks repos with known legacy debt (e.g., `pilot-repo`’s 8-orphan baseline) while keeping the signal visible.

The detector remains pure; tolerance is policy and lives in the sweep layer -- consistent with how ADR-0029 separates detection from gating.

## Acceptance

1. Sweep run against `pilot-repo` surfaces and reports the known **8 orphans** in `SWEEP_<ts>.md`, with paths captured in `SWEEP_<ts>.orphans.txt`.
2. Sweep run against `wos__e2e-test` reports `substrate_bullet_orphan_count: 0`.
3. `evals/e2e/assertions/09-repo-consistency-sweep.sh` passes against the `wos__e2e-test` fixture under default `EXPECTED_MAX_SUBSTRATE_ORPHANS=0`.
4. Setting `OPT_OUT_ORPHAN_BASELINE=1` on a `pilot-repo` sweep run produces the counter without escalating WARN, and the assertion respects an override `EXPECTED_MAX_SUBSTRATE_ORPHANS=8`.

## References

- Commit `5840755` -- `scan-substrate-orphans.py` detector.
- Commit `615c6bb` -- substrate-bullet-orphan bug-class definition.
- ADR-0029 -- drift-guard pattern (counter + WARN + e2e cap, no hard-fail).

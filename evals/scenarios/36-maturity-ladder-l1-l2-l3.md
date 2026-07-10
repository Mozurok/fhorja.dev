# Scenario 36 -- Maturity Ladder L1 -> L2 -> L3 Promotion

## Purpose

Validates ADR-0036 (K.7 oscillation handling + L3 dual-criterion evidence weighting). Ensures that persona maturity promotion between L1 (shadow), L2 (advisory), and L3 (gated) is gated by objective, evidence-backed signals -- not by elapsed time, vibe, or single-run flukes. Promotion logic must be deterministic, auditable, and resistant to noisy K.7 deltas.

## Coverage

### Case A -- L1 -> L2 via clean K.7 trajectory (Path A)

- **Given** a persona at L1 (shadow) with K.7 evals run on at least 3 distinct scenarios
- **And** K.7 deltas are all >= 0 (no regressions vs baseline)
- **And** at least 3 consecutive iterations show no regression (clean streak)
- **When** the maturity-ladder promotion check runs
- **Then** the persona qualifies for L2 (advisory) promotion via Path A
- **And** the promotion record cites the 3+ clean scenarios as evidence

### Case B -- L2 -> L3 via fleet + floor (Path B, ADR-0036)

- **Given** a persona at L2 (advisory) whose K.7 deltas are oscillating (some scenarios up, some down, but no scenario falls below the locked floor)
- **And** the K.7 floor for that persona has been held across all evals (no scenario dropped below baseline minus tolerance)
- **And** 5 clean fleet runs have completed across 2 or more distinct task folders (cross-task evidence, not a single repeated task)
- **When** the maturity-ladder promotion check runs
- **Then** the persona qualifies for L3 (gated) promotion via Path B
- **And** the promotion record cites both the floor-hold record and the cross-folder fleet evidence

### Case C -- Promotion BLOCKED when neither path met

- **Given** a persona where K.7 deltas show at least one regression below tolerance (Path A fails)
- **And** fleet runs are absent, limited to a single task folder, or fewer than 5 clean (Path B fails)
- **When** the maturity-ladder promotion check runs
- **Then** promotion is BLOCKED
- **And** the block record states explicitly which path failed and why (e.g. "Path A: scenario X delta -0.12 below floor; Path B: only 1 task folder observed")

## Pass criteria

1. Path A trigger fires only when ALL referenced K.7 scenario deltas are >= 0 AND the clean streak is >= 3 iterations.
2. Path B trigger fires only when the floor has held AND >= 5 clean fleet runs span >= 2 distinct task folders.
3. Oscillating K.7 deltas alone (without floor breach) do NOT block Path B -- they are the canonical case ADR-0036 was written to handle.
4. A single fleet run repeated 5 times in the same task folder does NOT satisfy Path B (cross-folder requirement is hard).
5. When promotion is blocked, the output cites the failing path(s) by name and the specific scenario/folder/delta that caused the block.
6. Promotion records are append-only and tied to a timestamp + the eval run IDs that produced the evidence.
7. The check is idempotent: running it twice on unchanged evidence produces the same result and does not create duplicate promotion records.
8. Demotion is symmetric: a confirmed floor breach at L2 or L3 triggers a demotion record with the same evidence-citation discipline.

## Failure modes

- Promotion fires on a single clean K.7 run (no streak requirement enforced) -- regresses to noise-driven promotion.
- Path B accepts 5 fleet runs from a single task folder, masking persona overfitting to one domain.
- Oscillating K.7 deltas are treated as a regression even when the floor holds, blocking valid Path B promotions and defeating ADR-0036's purpose.
- Block reasons are generic ("not enough evidence") instead of citing the specific failing path, scenario, or folder, making the maturity ladder un-auditable.

## Notes

- ADR-0036 -- K.7 oscillation handling + L3 dual-criterion evidence weighting (canonical source for Path A vs Path B logic).
- ADR-0034 -- substrate peers + worker contract (defines persona substrate that the ladder promotes within).
- wos/maturity-ladder.md -- operational definition of L1/L2/L3 states, floor semantics, and promotion/demotion records.
- wos/substrate-peers.md -- persona substrate model; ladder transitions must respect substrate peer constraints (no cross-substrate promotion shortcuts).
- Cross-folder fleet evidence is the load-bearing guard against overfitting; do not relax it without an ADR superseding 0036.

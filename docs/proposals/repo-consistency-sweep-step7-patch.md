## Patch to commands/repo-consistency-sweep.md Step 7

### BEFORE (current Pre-flight block, lines 46-54)

```text
- **Pre-flight: substrate audit (K.4 + K.5).** ALWAYS execute FIRST, before Step 1 [...]. Concrete invocation:
  ```bash
  bash scripts/scan-substrate-headers.sh <active-task-folder>
  python3 scripts/verify-log-validator.py <active-task-folder>/.wos/VERIFICATION_LOG.jsonl
  ```
  Capture `substrate_header_drift_count: <N>` from the first script's stdout and `invalid: <N>` from the second's stdout. These two integers are the audit deliverables for THIS sweep run.
```

And Step 9 snapshot fields (line 69):

```text
PLUS two substrate-audit metadata lines from Step 7 (`substrate_header_drift_count: <N>` and `verification_log_invalid_count: <N>`)
```

### AFTER (proposed Pre-flight block)

```text
- **Pre-flight: substrate audit (K.4 + K.5 + K.7).** ALWAYS execute FIRST, before Step 1 [...]. Concrete invocation (run in this order; header drift first so renamed parents do not mask orphan detection):
  ```bash
  bash    scripts/scan-substrate-headers.sh <active-task-folder>
  python3 scripts/scan-substrate-orphans.py <active-task-folder>
  python3 scripts/verify-log-validator.py   <active-task-folder>/.wos/VERIFICATION_LOG.jsonl
  ```
  Capture three integers from stdout: `substrate_header_drift_count: <N>`, `substrate_bullet_orphan_count: <N>`, and `invalid: <N>` (as `verification_log_invalid_count`). Persist the orphan paths list (truncated to first 10) for the snapshot; write the full list to `REVIEW_SWEEPS/SWEEP_<ts>.orphans.txt` for diffability.
  - **WARN semantics (not FAIL).** `substrate_bullet_orphan_count > 0` surfaces a WARN line in the sweep output, mirroring `header_drift` treatment per ADR-0029's drift-guard pattern. It does NOT add a bug-class finding and does NOT affect Step 11 routing. The gate lives in `evals/e2e/assertions/09-repo-consistency-sweep.sh` (orphan-cap block, default `EXPECTED_MAX_SUBSTRATE_ORPHANS=0`).
  - **Legacy-orphan tolerance.** Honour `OPT_OUT_ORPHAN_BASELINE=1` from the environment: when set, still emit the counter and snapshot fields, but suppress the WARN escalation. The detector remains pure; tolerance is a sweep-layer policy (consistent with ADR-0029 detection-vs-gating separation). Repos with known legacy debt (e.g. `pilot-repo`'s 8-orphan baseline) use this to keep the signal visible without blocking unrelated work.
  - **FORBIDDEN: carrying counts forward from a prior SWEEP snapshot.** All three scripts MUST re-invoke on every sweep run; substrate state changes outside the code-repo diff.
```

And Step 9 snapshot fields gains the new counter + paths line:

```text
PLUS three substrate-audit metadata lines from Step 7
(`substrate_header_drift_count: <N>`, `substrate_bullet_orphan_count: <N>`
with companion `substrate_bullet_orphan_paths: <comma-separated, max 10>`,
and `verification_log_invalid_count: <N>`).
```

### Rationale

1. **Ordering (headers before orphans before log).** Header drift can mask orphan detection: a renamed parent header makes every child bullet look orphaned. Stabilising header signal first prevents false positives in the orphan count.
2. **WARN, not FAIL.** Hard-failing the sweep on legacy baselines would block unrelated work; ADR-0029 already established counter + WARN + e2e-cap as the canonical drift-guard shape.
3. **Env override at sweep layer, not detector.** Keeps `scan-substrate-orphans.py` deterministic and reusable outside the sweep; policy lives where policy belongs.
4. **Snapshot capture parity.** Counters next to existing K.4/K.5 fields keep `SWEEP_<ts>.md` diffable; companion `.orphans.txt` file preserves full paths without bloating the snapshot.
5. **No routing impact.** Step 11 explicitly remains substrate-blind; the orphan counter is informational at sweep time and asserted at e2e time, matching the existing K.4 + K.5 contract.

### Related files

- Command being patched: `commands/repo-consistency-sweep.md`
- Proposal source: `docs/proposals/scan-orphans-sweep-integration.md`

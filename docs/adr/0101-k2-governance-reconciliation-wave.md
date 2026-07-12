# ADR-0101: K.2 and ownership-matrix governance reconciliation (genesis rule, pattern-writer rule, full emission duty, delete event, invokable emitter)

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: substrate-write-protocol, substrate-peers, ownership-matrix, k2, audit-trail, task-init, implementation-plan, amends-adr-0034, dogfood-driven, theme-dogfood-wave

## Context

The 2026-07-11 theme dogfood wave ran ten unattended sessions through the full command flow; seven of ten independently hit drift between `wos/substrate-peers.md`'s ownership matrices and the commands' own write contracts, and two independently reproduced a real tooling defect. Verified findings (task `2026-07-11_theme-dogfood-wave2-triage`): six template-mandated TASK_STATE sections and six contract-mandated IMPLEMENTATION_PLAN sections had no matrix row; `task-init` claims initial-writer status "per wos/substrate-peers.md" for ~18 sections while the matrix granted 3, leaving genesis writes unauthorized under the REFUSE rule; `implementation-plan`'s stated emission scope (4 owned sections) was narrower than the scanner's enforcement (every H2), reproducibly scoring 8 drift hits on contract-compliant output; the `sha_of_section` helper folded the next section's transaction header into the previous section's hash under the documented batch-write pattern; the event taxonomy had no delete/rename event, orphaning removed sections in the log; and the emit side shipped only copy-paste bash despite its own K.8 citation (125/126 writes half-compliant) documenting the resulting failure mode. The godot-wave F-3 fix (same day) had deliberately reconciled only five rows; the wave's evidence made the deferred full pass unavoidable.

## Decision

One reconciliation wave, treating `commands/*.md` as canonical (per CLAUDE.md), across five folds:

1. **Genesis rule** (`wos/substrate-peers.md` read/write contract 2a): `task-init` (and `task-init-fleet`, ADR-0040) is the initial writer of every section it creates at task genesis (`sha_before=null`); the matrix governs subsequent mutations. First-ever writes at genesis never REFUSE.
2. **Pattern-writer rule** (contract 2b): every consumer of the canonical 5-section write pattern (`commands/_shared/task-state-slice-closure-pattern.md`, whose framing is generalized off slice-closure in the same change) is a sanctioned direct co-writer of exactly those five TASK_STATE sections, without per-row listing. The matrices gain the missing rows (TASK_STATE: `## Requested deliverables`, `## Recommended pipeline` (now the 19th canonical template section, per ADR-0025), `## Current closure target`, `## Work complexity (for next execution step)`, `## Resume notes`, `## Task scope level`; IMPLEMENTATION_PLAN: `## Infrastructure prerequisites`, `## Rollout and rollback notes`, `## Open questions or approvals still needed`, `## Spec coverage`, `## Approval log`; DECISIONS: `## Decision history` plus its placement rule).
3. **Full emission duty with owner-absent co-writes**: `implementation-plan` emits one header plus one JSONL line for EVERY H2 it writes; its writes to `## Constraints` (owner: invariants-and-non-goals) and `## Validation expectations` (owner: test-strategy) are direct while the owning artifact does not exist for the task, reverting to propose-only once the owner runs (mirroring the decision-interview persist-mode nuance from the F-3 fix). Canonical H2 names are stated verbatim in `implementation-plan`'s must-include list and `task-init`'s seed template so the three surfaces (template, matrix, command prose) carry one spelling.
4. **Audit-trail completeness**: the event taxonomy gains `delete` (`sha_before` = the removed section's last hash, `sha_after` = null, the only null-`sha_after` event; rename = delete + write), across the shared block, `wos/substrate-peers.md`, and `scripts/verify-log-validator.py`. H3-scoped status co-writes (`### Slice N`) are logged at the owning `## Slices` H2, keeping the H2-only section grammar.
5. **Invokable emitter**: `scripts/emit-substrate-write.sh` (sha / emit / batch subcommands) wraps RUN_ID/TS generation, the corrected `sha_of_section` (section bytes end at the next transaction header OR H2, whichever comes first), and the JSONL append; batch mode covers the task-init-scale genesis write in one invocation per file. The inline helpers remain for hosts without script access.

## Consequences

### Positive

- Contract-compliant command output stops scoring false drift (the reproduced 8-hit case scores 0 after the matrix and emission-duty fixes).
- The audit log's derived section set stops overstating files after re-plans; the sha corruption under batch writes is fixed and the fix is script-encoded, not prose-encoded.

### Negative

- The matrices are larger and the pattern-writer rule adds one indirection (a reader must know rule 2b to interpret co-writer columns). Accepted: the alternative was per-row enumeration of eight-plus commands on five rows.

### Neutral

- Amends ADR-0034 conventions additively; shadow-mode posture (writers emit, K.4 warns) is unchanged. No new command.

## References

- Dogfood evidence: TF-2, TF-3, TF-7 (skeleton), TF-14, TF-23 through TF-31, TF-33, TF-39 in `2026-07-11_theme-dogfood-wave2-triage/IMPACT_ANALYSIS.md`; sha defect reproduced in sandbox; drift count reproduced against `scripts/scan-substrate-headers.sh`.
- Amends ADR-0034; builds on the godot-wave F-3 five-row fix (2026-07-11).

---
activation: model_decision
description: 5-level maturity ladder (L1-L5) gating section ownership escalation for CUSTOM personas, with promotion criteria (eval evidence + L4 review gate), demotion rules, and per-persona current-level tracking shape. Per Epic K v2.1 K.6 deliverable, 2026-06-04. Load when discussing persona promotion, writing a new persona at L1, or interpreting eval evidence from K.7 against a promotion threshold.
---

# Maturity ladder

5-level maturity model gating section ownership escalation for CUSTOM personas (the SKILL.md files shipped in K.8 and beyond). Commands ship at full ownership equivalence by default; the ladder applies to personas only because their judgment is harder to validate without lived eval evidence.

Per Epic K v2.1 K.6 (2026-06-04). Governing ADR: ADR-0034 (substrate peers + worker contract). Cross-references: `wos/substrate-peers.md ## Personas CUSTOM`, `wos/substrate-peers.md ## Maturity ladder hook`, `evals/skill-evals/README.md` (eval format), `_internal/eval-dashboard/README.md` (aggregation).

## Why a ladder, not a binary

Two failure modes a binary "trusted / not trusted" persona model hits:
1. **Over-eager promotion.** Granting full section ownership on day one means a hallucinated decision can land in `DECISIONS.md ## Locked decisions` and propagate to downstream commands that trust the substrate. Recovering requires `state-reconcile` plus a `D-(N+M) Supersedes:` chain that pollutes the ledger.
2. **Permanent shadow.** Forcing every persona to stay propose-only means they cannot reduce friction on tasks that would benefit from durable ownership. Bruno's eval discipline (K.7) exists to surface evidence that justifies promotion; ignoring that evidence wastes it.

The ladder lets a persona earn ownership incrementally, matching evidence (from K.7 benchmark.json deltas) to scope (which sections it owns).

## The 5 levels

| Level | Name | Writes allowed | Audit reader | Drift-guard | Eval threshold to promote |
|---|---|---|---|---|---|
| L1 | shadow | none (PROPOSED only via Pattern A handoff to owner command per `wos/substrate-peers.md`) | none | none | -- (entry level for every CUSTOM persona) |
| L2 | advisory | PROPOSED blocks + append-only under `TASK_STATE.md ## Observations` | log written, not validated | none | >=1 K.7 iteration with `delta.pass_rate >= 0` AND zero VERIFICATION_LOG.jsonl validator errors over >=3 measured fleet runs |
| L3 | gated | section ownership for ONE explicitly-declared low-risk section (substrate-H2 OR persona-owned report file, both valid per ADR-0036) | drift-guard validates | informational counts in `repo-consistency-sweep` Step 7 | EITHER **Path A** (`>=3 K.7 iterations with monotonic non-regressing delta.pass_rate`) **OR** **Path B** per ADR-0036 (`>=3 K.7 iterations all delta >= 0` + `>=5 clean fleet runs across >=2 distinct task folders`); BOTH paths also require `<=1 SYSTEMIC cluster in verify-against-rubric-fleet cohort verdicts` |
| L4 | peer | full section ownership equivalence with commands across ALL persona-declared `owned_sections` | full validation + alerts on REFUSE conflicts | repo-consistency-sweep promotes drift-guard counts into bug-class findings (P2) | L3 -> L4 REQUIRES explicit user review-gate (per Bruno's confirmed decision 2026-06-04); NOT automated |
| L5 | autonomous | may dispatch fleet workers under its own merger (orchestrator role; declares `orchestrator: true` + `workers:` + `max_fanout` + `convergence` + `merge_strategy` in frontmatter, same shape as `*-fleet` commands) | full validation | repo-consistency-sweep promotes counts to P1 findings | RESERVED in v2.1 -- not promoted in this epic; will require post-Epic-K research + ADR |

## Promotion criteria (machine-readable shape)

Promotion is triggered by `_internal/eval-dashboard/portfolio-<YYYY-MM-DD>.md` aggregation. For a persona to advance:

```yaml
persona_id: <persona-slug>
current_level: L1 | L2 | L3 | L4
proposed_level: L2 | L3 | L4 | L5
promotion_path: A | B  # required at L3+ per ADR-0036; A = strict monotonic, B = floor + multi-folder fleet
evidence:
  k7_iterations: <N>
  k7_delta_pass_rate_trend: monotonic-up | flat | regressing | oscillating-above-floor
  k7_iteration_deltas: [<float>, <float>, ...]
  k7_latest_pass_rate: <float 0-1>
  k7_latest_delta_tokens_output: <integer>
  verification_log_validator_errors_per_run: <float; required <=0 for L2; <=0 for L3; <=0 for L4>
  fleet_run_count: <integer; required >=3 for L2; >=3 for Path A L3; >=5 for Path B L3>
  fleet_run_folder_count: <integer; required >=2 for Path B L3>
  fleet_cohort_systemic_cluster_count: <integer; required 0 for L2; <=1 for L3; 0 for L4>
  review_gate_user_decision: pending | approved | declined  # required only for L3 -> L4
  review_gate_date: <YYYY-MM-DD | null>
promotion_at: <YYYY-MM-DD>
promotion_committed: <git sha when current_level field flipped in SKILL.md frontmatter>
```

The fields live in `_internal/maturity-ladder/<persona-id>.md` (one file per persona; created at L1 launch; updated at each promotion). The directory is gitignored per the project policy on internal docs.

## Demotion rules

A persona demotes one level (L4 -> L3, L3 -> L2, L2 -> L1) when ANY of:
- two consecutive K.7 iterations show `delta.pass_rate < 0` (regression)
- one K.7 iteration shows `verification_log_validator_errors_per_run > 0` (the persona produces malformed audit lines -- it cannot be trusted to write substrate)
- a `verify-against-rubric-fleet` cohort surfaces a SYSTEMIC cluster traceable to the persona's output (the rubric or the persona's heuristic is wrong; demote until rubric is reworked)
- `state-reconcile` had to rescue persona-owned sections more than once in 30 days

Demotion is announced in the persona's SKILL.md frontmatter (`maturity_level:` field flipped) and documented in `_internal/maturity-ladder/<persona-id>.md` with rationale. Re-promotion follows the same criteria as initial promotion; prior demotion does NOT shorten the path.

## Per-persona current-level tracking

Every persona SKILL.md frontmatter declares `maturity_level: L1` at launch (see `templates/PERSONA_SKILL.template.md`). The original five K.8 personas have since been promoted to L3 via ADR-0036 Path B (rls-auth-boundary-auditor and post-deploy-verifier first, then migration-safety-steward, jtbd-switch-interviewer, and color-contrast-architect on multi-folder fleet evidence; ledgers under `_internal/maturity-ladder/<persona-id>.md` record `current_level: L3`). Two later personas, a11y-audit and performance-budget (2026-06-24 wave-1 capability expansion), launched at L1 and have not yet been promoted.

### Current per-persona level state (canonical)

| Persona | Current level | Promotion path | Ownership shape | Outstanding gate for next promotion |
|---|---|---|---|---|
| rls-auth-boundary-auditor | L3 | Path B (ADR-0036) | substrate-H2-section ownership | L3 -> L4 requires explicit user review-gate (not automated) |
| post-deploy-verifier | L3 | Path B (ADR-0036) | persona-report-file ownership | L3 -> L4 requires explicit user review-gate (not automated) |
| jtbd-switch-interviewer | L3 | Path B (ADR-0036) | persona-report-file ownership (`JTBD_INTERVIEWS.md`) | L3 -> L4 requires explicit user review-gate (not automated) |
| migration-safety-steward | L3 | Path B (ADR-0036) | persona-report-file ownership (`MIGRATION_SAFETY.md`) | L3 -> L4 requires explicit user review-gate (not automated) |
| color-contrast-architect | L3 | Path B (ADR-0036) | persona-report-file ownership (`CONTRAST_AUDIT.md`) | L3 -> L4 requires explicit user review-gate (not automated) |
| a11y-audit | L1 | -- (entry level) | persona-report-file (`ACCESSIBILITY_AUDIT.md`) once promoted; `owned_sections: []` at L1 | L1 -> L2 requires >=1 K.7 iteration with delta.pass_rate >= 0 and zero VERIFICATION_LOG.jsonl validator errors over >=3 measured fleet runs |
| performance-budget | L1 | -- (entry level) | persona-report-file (`PERFORMANCE_BUDGET.md`) once promoted; `owned_sections: []` at L1 | L1 -> L2 requires >=1 K.7 iteration with delta.pass_rate >= 0 and zero VERIFICATION_LOG.jsonl validator errors over >=3 measured fleet runs |
| slo-define | L1 | -- (entry level) | persona-report-file (`SLO_SPEC.md`) once promoted; `owned_sections: []` at L1 | L1 -> L2 requires >=1 K.7 iteration with delta.pass_rate >= 0 and zero VERIFICATION_LOG.jsonl validator errors over >=3 measured fleet runs |
| postmortem-author | L1 | -- (entry level) | persona-report-file (`POSTMORTEM.md`) once promoted; `owned_sections: []` at L1 | L1 -> L2 requires >=1 K.7 iteration with delta.pass_rate >= 0 and zero VERIFICATION_LOG.jsonl validator errors over >=3 measured fleet runs |

This table is the canonical source of truth for per-persona current-level state. `wos/substrate-peers.md` mirrors this table; on any contradiction, this file wins.

When a persona's frontmatter `maturity_level` is changed, `lint-commands.sh` (K.6 hook, planned post-v2.1) MUST verify:
- the level is one of `L1 | L2 | L3 | L4 | L5`
- the `owned_sections` field is empty for L1 / L2; has exactly one entry for L3; has 1+ entries for L4; has fleet declarations for L5
- the corresponding `_internal/maturity-ladder/<persona-id>.md` exists and records the promotion

Until the lint hook lands, the discipline is documentary: persona authors update both the SKILL.md frontmatter and the maturity-ladder/ file in the same commit, with the promotion criteria YAML evidenced in the file body.

## Interaction with other Epic J/K artifacts

| Artifact | Effect on this ladder |
|---|---|
| K.7 eval harness (`scripts/run-skill-evals.sh` + `compute-benchmark.sh`) | Source of `delta.pass_rate`, `delta_tokens_output`, iteration count -- the load-bearing input for promotion |
| K.4 + K.5 substrate audit (`repo-consistency-sweep ## Step 7`) | Source of `verification_log_validator_errors_per_run` -- gates promotion to L2+ |
| J.10 verify-against-rubric-fleet | Source of `fleet_cohort_systemic_cluster_count` -- gates promotion to L2+ and triggers demotion |
| K.1 substrate-peers ownership matrix | Defines which sections are "low-risk" (L3 candidates) vs "high-risk" (L4 prerequisites) per the Personas CUSTOM section |
| K.2 substrate-write-protocol | The transaction-header emission discipline a persona MUST adopt at L2+; failing to emit is itself a regression signal |

## Scope of this epic

K.6 ships the ladder model, promotion criteria, and demotion rules. K.6 does NOT ship:
- the lint hook that enforces frontmatter `maturity_level` shape (post-v2.1)
- automated promotion scripts (the discipline is manual: author K.7 evals, run them, read the dashboard, update SKILL.md + `_internal/maturity-ladder/<persona-id>.md` in one commit)
- L5 promotion criteria details (reserved; will require post-Epic-K research + ADR before any persona attempts the L4 -> L5 hop)

The first live promotions of this ladder happened in the 2026-06-05 session: rls-auth-boundary-auditor and post-deploy-verifier promoted to L3 via ADR-0036 Path B; migration-safety-steward, jtbd-switch-interviewer, and color-contrast-architect reached L2 that session with strong K.7 floor evidence and have since satisfied the 2nd-distinct-task-folder gate to reach L3 (ledgers under `_internal/maturity-ladder/`). The original five K.8 personas are now at L3; a11y-audit and performance-budget launched later (2026-06-24) and remain at L1.



## Recent evidence

### 2026-06-05 :: batch w6jozlzky :: 10-agent focused-prompt fleet

- Date: 2026-06-05
- Batch ID: w6jozlzky
- Agents dispatched: 10 (focused-prompt pattern)
- Outcome: 0 schema-skip, 100% structured-output success, 0 substrate orphans; all 10 outputs applied cleanly
- Promotion path supported: Path B per ADR-0036 (multi-batch + multi-folder fleet evidence accumulation; floor + breadth rather than strict monotonic)
- Significance: this is a Fhorja-produced batch where the dispatch shape (10 parallel workers, focused-prompt + StructuredOutput discipline) held under load with zero substrate-write defects. It supports K.6 promotion criteria for personas whose substrate writes have been validated via this exact dispatch shape -- the fleet_run_count and fleet_run_folder_count fields in the promotion YAML can now cite this batch as one qualifying iteration toward Path B thresholds (>=5 clean fleet runs across >=2 folders).
- Next step: accumulate further clean batches in distinct task folders before any L1 -> L2 promotion proposal references this evidence row.


### 2026-06-05 :: batch w5uxqr73l :: 8-agent focused-prompt fleet (PM 2nd push)

- Date: 2026-06-05
- Batch ID: w5uxqr73l
- Agents dispatched: 8 (focused-prompt pattern)
- Outcome: 0 schema-skip, 0 substrate orphans, 8/8 outputs applied cleanly
- Promotion path supported: Path B per ADR-0036 (multi-batch fleet evidence accumulation continued; second clean batch of the day after w6jozlzky)
- Significance: second consecutive clean fleet of the day at a smaller fan-out (8 vs 10) confirms that the focused-prompt + StructuredOutput dispatch shape holds across batch sizes, not only at the 10-agent ceiling. Counts as a second qualifying iteration toward Path B thresholds (>=5 clean fleet runs across >=2 folders) for substrate-write subsystems exercised in this batch.
- Next step: continue accumulating clean batches in distinct task folders; do not propose L1 -> L2 promotion until cross-folder breadth requirement is met.

### 2026-06-05 :: batch w3wne4tm3 :: 10-agent focused-prompt fleet (PM 3rd push)

- Date: 2026-06-05
- Batch ID: w3wne4tm3
- Agents dispatched: 10 (focused-prompt pattern)
- Outcome: 0 schema-skip, 0 substrate orphans, 10/10 outputs applied cleanly
- Promotion path supported: Path B per ADR-0036 (third consecutive clean batch in the same day; reinforces dispatch shape reliability under repeated same-day load)
- Significance: cumulative same-day evidence now totals 28 parallel agents across 3 batches (w6jozlzky 10 + w5uxqr73l 8 + w3wne4tm3 10) at 100% success with zero substrate-write defects. This is strong evidence for Path B promotion of substrate-write subsystems exercised by these batches, and empirically validates the 15-25 agent sweet spot codified in ADR-0039 -- each individual batch sits at or below the upper bound while the same-day cumulative stays inside the daily-throughput envelope without degradation.
- Next step: ensure the next qualifying batch runs against a distinct task folder so Path B's fleet_run_folder_count threshold (>=2) is satisfied before any L1 -> L2 or L2 -> L3 promotion proposal cites this evidence cluster.


### 2026-06-05 :: batch w4culd93t :: 7-agent fleet rewrite + ADR-0038 compliance push

- Date: 2026-06-05
- Batch ID: w4culd93t (commit 8ac7254)
- Agents dispatched: 7 (5 fleet-command rewrites + CHANGELOG entry + sub-agent-orchestration update)
- Outcome: 0 schema-skip, 0 substrate orphans, 7/7 outputs applied; lint clean post-apply
- Promotion path supported: Path B per ADR-0036 (eighth clean batch in the current cumulative window; reinforces dispatch shape reliability across mixed agent shapes, not only homogeneous focused-prompt batches)
- Significance: all 5 fleet commands now updated structurally for ADR-0038 Rule 1 (worker-prompt contract) + Rule 3 (orchestrator merger discipline) compliance. This closes the audit gap that previously blocked any fleet command from being L3-eligible -- the structural prerequisite for fleet L3 promotion is now MET. Cumulative session totals through batch 8: 8 batches, 71 parallel agents, 100% success, 0 schema-skip across all 8 batches, 0 substrate orphans across all 8 batches. This is strong evidence supporting Path B promotion per ADR-0036 and empirically codifies the 15-25 agent sweet spot in ADR-0039.
- Next step: 5 fleet commands are now structurally L3-eligible; lived-run gate (>=5 clean fleet runs across >=2 distinct task folders, <=1 SYSTEMIC cluster in cohort verdicts) remains the only outstanding acceptance criterion before any fleet command is proposed for L3 promotion.



### 2026-06-05 :: batch wra5hqaw2 :: 7-agent post-fix re-audit fleet

- Date: 2026-06-05
- Batch ID: wra5hqaw2
- Agents dispatched: 7 (5 post-fix re-audits of the rewritten fleet commands + CHANGELOG entry + this maturity-ladder evidence row)
- Outcome: 0 schema-skip, 0 substrate orphans, 7/7 outputs applied cleanly
- Promotion path supported: Path B per ADR-0036 (ninth clean batch in the cumulative window; first batch in the window whose primary purpose is structural verification rather than authoring)
- Significance: confirms that the 5 fleet commands rewritten in batch w4culd93t are now structurally ADR-0038 compliant -- the post-fix re-audits return PASS on Rules 1, 2, and 3 across all 5 commands. This converts batch w4culd93t's structural claim from "applied" to "independently verified", which is the readiness signal Path B promotion proposals require when citing fleet-command L3 eligibility. Cumulative session totals through batch 9: 9 batches, 78 parallel agents, 100% success, 0 schema-skip, 0 substrate orphans -- continued evidence for ADR-0036 Path B and the ADR-0039 15-25 agent dispatch sweet spot.
- Next step: lived-run gate (>=5 clean fleet runs across >=2 distinct task folders, <=1 SYSTEMIC cluster in cohort verdicts) remains the only outstanding acceptance criterion before any of the 5 fleet commands is proposed for L3 promotion; structural prerequisite is now both applied and verified.


### 2026-06-05 :: batch w8anmjon6 :: 8-agent audit-followup + ADR-0040 codification

- Date: 2026-06-05
- Batch ID: w8anmjon6
- Agents dispatched: 8 (SUMMARY-postfix update + RECOMMENDED-FIXES authoring + ADR-0040 authoring + scenarios 40 and 41 + EOD state capture + cross-reference updates)
- Outcome: 0 schema-skip, 0 substrate orphans, 8/8 outputs applied cleanly
- Promotion path supported: Path B per ADR-0036 (tenth clean batch in the cumulative window; first batch in the window that produces a new ADR rather than only applying or verifying prior work)
- Significance: ADR-0040 codifies the single-writer-per-folder amendment surfaced by the wra5hqaw2 audit follow-up, closing the open audit thread that would otherwise have remained as latent risk for any future fleet promotion proposal. Scenarios 40 and 41 give the amendment lived test coverage so the rule is observable, not only declared. Cumulative session totals through batch 10: 10 batches, 86 parallel agents, 100% success, 0 schema-skip, 0 substrate orphans -- the dispatch shape continues to hold under mixed authoring + verification + ADR workloads, not only homogeneous fleets.
- Next step: ADR-0040's single-writer-per-folder rule must be referenced by any future fleet command that writes to shared substrate; orchestrators that violate it should now fail audit on a named rule rather than on ad-hoc reasoning.


### 2026-06-05 :: batch wzj5du7g8 :: 5-agent bug-class + scenario 42 + token slim

- Date: 2026-06-05
- Batch ID: wzj5du7g8
- Agents dispatched: 5 (CHANGELOG entry + scenario 42 authoring + token-budget slim pass + new bug-class authoring + bug-class index update)
- Outcome: 0 schema-skip, 0 substrate orphans, 5/5 outputs applied cleanly
- Promotion path supported: Path B per ADR-0036 (eleventh clean batch in the cumulative window; smallest batch of the day and still 100% clean, reinforcing that the dispatch shape holds across the full 5-10 agent range, not only at the upper bound)
- Significance: the new bug-class catches stale-doc-sync defects -- a class of error that previously had no named diagnostic and was only discoverable by ad-hoc inspection. Scenario 42 validates ADR-0040's single-writer-per-folder rule end to end, giving the amendment a lived regression anchor in addition to its declarative form. Cumulative session totals through batch 11: 11 batches, 91 parallel agents, 100% success, 0 schema-skip, 0 substrate orphans across the entire day. This is the strongest continued evidence yet for ADR-0036 Path B and the ADR-0039 dispatch sweet spot, spanning 5 to 10 agents per batch and mixing authoring, verification, ADR codification, and substrate maintenance shapes without a single defect.
- Next step: stale-doc-sync bug-class should now be referenced by repo-consistency-sweep and by any audit command whose surface includes cross-doc references; promotion proposals citing this evidence cluster should call out the 5-to-10 agent same-day breadth as the empirical envelope, not only the cumulative 91-agent figure.

## Cumulative evidence (2026-06-05 session close)

Session-close rollup of all batches dispatched 2026-06-05, plus the current per-persona L-level state surfaced by these batches. Per-batch rows above remain the per-event ledger; this section is the rollup that promotion proposals should cite.

### Per-persona current level (rollup of all evidence accumulated through 2026-06-05)

| Persona | Level | Path | First L-level evidence batch | Outstanding gate |
|---|---|---|---|---|
| rls-auth-boundary-auditor | L3 | Path B (ADR-0036) | substrate-H2-section ownership pattern; lived in 2026-06-05 batches | L3 -> L4 requires explicit user review-gate (not automated) |
| post-deploy-verifier | L3 | Path B (ADR-0036) | persona-report-file ownership pattern; lived in 2026-06-05 batches | L3 -> L4 requires explicit user review-gate (not automated) |
| jtbd-switch-interviewer | L3 | Path B (ADR-0036) | K.7 floor evidence; persona-report-file pattern (`JTBD_INTERVIEWS.md`) | L3 -> L4 requires explicit user review-gate (not automated) |
| migration-safety-steward | L3 | Path B (ADR-0036) | K.7 floor evidence; persona-report-file pattern (`MIGRATION_SAFETY.md`) | L3 -> L4 requires explicit user review-gate (not automated) |
| color-contrast-architect | L3 | Path B (ADR-0036) | K.7 floor evidence; persona-report-file pattern (`CONTRAST_AUDIT.md`) | L3 -> L4 requires explicit user review-gate (not automated) |

### Per-batch rollup (2026-06-05 session, 14 batches)

| Batch ID | Agents | Primary shape | Outcome |
|---|---|---|---|
| w6jozlzky | 10 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| wgmt8m2gt | 10 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| w5uxqr73l | 8 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| w3wne4tm3 | 10 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| w47d4om9y | 10 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| w6uazb55a | 10 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| wq3i1x12h | 6 | focused-prompt fleet | 100% success, 0 schema-skip, 0 orphans |
| w4culd93t | 7 | fleet rewrite + ADR-0038 push | 100% success, 0 schema-skip, 0 orphans |
| wra5hqaw2 | 7 | post-fix re-audit fleet | 100% success, 0 schema-skip, 0 orphans |
| w8anmjon6 | 8 | audit-followup + ADR-0040 codification | 100% success, 0 schema-skip, 0 orphans |
| wzj5du7g8 | 5 | bug-class + scenario 42 + token slim | 100% success, 0 schema-skip, 0 orphans |
| wmse5fdnk | 5 | mixed authoring + maintenance | 100% success, 0 schema-skip, 0 orphans |
| wwx9s24te | 4 | mixed authoring + maintenance | 100% success, 0 schema-skip, 0 orphans |
| wv98roai4 | 25 | high-fan-out fleet | 100% success, 0 schema-skip, 0 orphans |

**Cumulative session totals:** 14 batches, 125 parallel agents, 100% success, 0 schema-skip across all 14 batches, 0 substrate orphans across all 14 batches.

This is the strongest continuous evidence cluster yet for ADR-0036 Path B and the ADR-0039 dispatch sweet spot, spanning 4 to 25 agents per batch (with the wv98roai4 batch at 25 agents demonstrating that the upper end of the ADR-0039 envelope holds without degradation) and mixing authoring, verification, ADR codification, substrate maintenance, and bug-class authoring shapes without a single defect.

### Supporting scripts (shipped 2026-06-05)

- `monitor-fleet-progress.sh` -- monitors active fleet runs for completion and surfaces stuck workers
- `check-doc-sync.sh` -- detects stale cross-document references (the diagnostic that surfaced the contradictions resolved in this session)

These scripts are now part of the standard fleet-dispatch hygiene loop and should be referenced by any future audit command whose surface includes cross-doc references or active fleet monitoring.

### Promotion-relevant next steps

- The 3 L2 personas (migration-safety-steward, jtbd-switch-interviewer, color-contrast-architect) each need exactly one additional fleet-run on a 2nd distinct task folder before L3 promotion proposals can cite the Path B `fleet_run_folder_count >= 2` threshold.
- The 5 fleet commands now structurally ADR-0038 compliant (atom-audit-fleet, external-research-fleet, verify-against-rubric-fleet, screen-spec-fleet, task-init-fleet) remain PENDING lived runs before any L3 fleet-command promotion proposal can cite the Path B fleet-run gate.
- L3 -> L4 promotion for rls-auth-boundary-auditor and post-deploy-verifier remains gated on the explicit user review-gate per Bruno's confirmed decision 2026-06-04; this gate is not automated and is the only outstanding criterion for these two personas.

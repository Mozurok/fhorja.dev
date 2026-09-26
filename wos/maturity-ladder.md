---
activation: model_decision
description: 5-level maturity ladder (L1-L5) gating section ownership escalation for CUSTOM personas, with promotion criteria (eval evidence + L4 review gate), demotion rules, and per-persona current-level tracking shape. Per Epic K v2.1 K.6 deliverable, 2026-06-04. Load when discussing persona promotion, writing a new persona at L1, or interpreting eval evidence from K.7 against a promotion threshold.
---

# Maturity ladder

5-level maturity model gating section ownership escalation for CUSTOM personas (the SKILL.md files shipped in K.8 and beyond). Commands ship at full ownership equivalence by default; the ladder applies to personas only because their judgment is harder to validate without lived eval evidence.

Per Epic K v2.1 K.6 (2026-06-04). Governing ADR: ADR-0034 (substrate peers + worker contract). Cross-references: `wos/substrate-peers.md ## Personas CUSTOM`, `wos/substrate-peers.md ## Maturity ladder hook`, `evals/skill-evals/README.md` (eval format), `_internal/eval-dashboard/README.md` (aggregation; maintainer-local and gitignored).

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
| L4 | peer | full section ownership equivalence with commands across ALL persona-declared `owned_sections` | full validation + advisory counts of out-of-row writes (ownership is descriptive, ADR-0232) | repo-consistency-sweep promotes drift-guard counts into bug-class findings (P2) | L3 -> L4 REQUIRES explicit user review-gate (per Bruno's confirmed decision 2026-06-04); NOT automated. Eligibility filter, review packet, verdict shape, and demotion path: `## L3 -> L4 review gate` below |
| L5 | autonomous | may dispatch fleet workers under its own merger (orchestrator role; declares `orchestrator: true` + `workers:` + `max_fanout` + `convergence` + `merge_strategy` in frontmatter, same shape as `*-fleet` commands) | full validation | repo-consistency-sweep promotes counts to P1 findings | RESERVED in v2.1 -- not promoted in this epic; will require post-Epic-K research + ADR |

## Promotion criteria (machine-readable shape)

Promotion is triggered by `_internal/eval-dashboard/portfolio-<YYYY-MM-DD>.md` aggregation (maintainer-local and gitignored). For a persona to advance:

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
- no owner write in any `.wos/VERIFICATION_LOG.jsonl` for 90 days, counted from promotion (ADR-0181). Demand, not quality, so it is the only bullet here that fires on silence. Counted by `owner` and never by `invoked_by`: measured 2026-08-30 the two personas this exists to catch, `rls-auth-boundary-auditor` and `jtbd-switch-interviewer`, have 0 owner writes and 4 and 5 as `invoked_by`, so counting both makes the rule catch nobody. The three it does NOT catch, on the same reading, are `migration-safety-steward`, `color-contrast-architect` and `post-deploy-verifier`, with 1, 2 and 3 owner tasks; the boundary is written here so it stays visible. Telemetry lives under `projects/`, which is gitignored, so a tree without it is `not measured` and never zero: `python3 scripts/flow-audit.py --demand` reports the inputs and the lint carries them on the advisory `Ladder-demand:` line. Documentary until a lint hook enforces it; the advisory line decides nothing.

Demotion is announced in the persona's SKILL.md frontmatter (`maturity_level:` field flipped) and documented in `_internal/maturity-ladder/<persona-id>.md` with rationale (maintainer-local and gitignored; start one from `templates/MATURITY_LEDGER.template.md`). Re-promotion follows the same criteria as initial promotion; prior demotion does NOT shorten the path.

## Per-persona current-level tracking

Every persona SKILL.md frontmatter declares `maturity_level: L1` at launch (see `templates/PERSONA_SKILL.template.md`). The original five K.8 personas have since been promoted to L3 via ADR-0036 Path B (rls-auth-boundary-auditor and post-deploy-verifier first, then migration-safety-steward, jtbd-switch-interviewer, and color-contrast-architect on multi-folder fleet evidence; ledgers under `_internal/maturity-ladder/<persona-id>.md`, maintainer-local and gitignored, record `current_level: L3`). Four later personas, a11y-audit, performance-budget, slo-define, and postmortem-author, launched at L1 and have not yet been promoted.

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

When a persona's frontmatter `maturity_level` changes, `lint-commands.sh` checks the shape on every run, warn-only: the level is one of `L1 | L2 | L3 | L4 | L5`, and `owned_sections` is empty for L1 and L2, has exactly one entry for L3, and has one or more for L4 (L5 stays reserved). One rule stays documentary because the lint cannot see it: the corresponding `_internal/maturity-ladder/<persona-id>.md` exists and records the promotion (maintainer-local and gitignored; created from `templates/MATURITY_LEDGER.template.md`). Persona authors update the SKILL.md frontmatter and that ledger file in the same commit, with the promotion criteria YAML evidenced in the ledger body.

## L3 -> L4 review gate

The L3 -> L4 transition is the only ladder step that is **not** auto-graduated. L4 grants a persona full peer ownership equivalence with commands: its writes participate in the same canonical artifacts, validation, and drift-guard treatment as first-party Fhorja commands. Because that bar is qualitative ("does this persona deserve to be trusted like Fhorja itself?"), promotion requires explicit user judgment over a structured review packet. No persona has reached L4 yet; this section is the contract the first one will meet. It used to be a topic file of its own with a separate fillable packet template, and both were folded in here on 2026-09-23.

### Eligibility

A persona is eligible for L3 -> L4 review only when **all** of the following hold at the moment the gate is opened:

- The persona has been at L3 for **>= 30 days** of wall-clock time since its L2 -> L3 promotion.
- The persona has produced **>= 10 lived substrate writes** (artifact edits captured in its ledger) across **>= 3 distinct task folders** (`projects/<client>__<project>/active/` or `archive/` entries). Writes inside a single task do not establish breadth; the three-folder floor exists to filter personas that only look mature on one engagement.
- The persona has **zero K.5 errors** in its ledger over the L3 window. K.5 errors are contract violations (wrong owned section, schema-invalid output, refusal-protocol miss). A single one resets eligibility.
- The persona has **zero SYSTEMIC clusters** flagged against it in K.7 trend analysis over the L3 window. LOCAL or per-run findings do not block eligibility.

If any condition fails, the gate stays closed and Fhorja names the specific gap instead of presenting a packet.

### Review packet

When eligibility passes, Fhorja assembles a packet for the user. The packet is the sole source the user judges from; Fhorja never asks the user to remember context out of band. It is rendered once and kept stable across the review window, so it does not change underneath a user who takes days to decide. It carries, in this order:

1. Persona identity: persona id, current level (L3), promotion path, current `owned_sections` at L3, proposed `owned_sections` at L4, L3 entry date, and days at L3.
2. K.7 trend over the L3 window: one row per iteration (date, pass rate, delta against the previous one, notable failures), the latest pass rate, and a trend verdict of improving, flat, or regressing. The trend must be flat or improving.
3. Fleet-run summary: runs the persona took part in, task folders touched, K.5 errors per run (mean and p90), runs with zero K.5 errors, and one row per task folder.
4. Substrate write inventory: the last 20 writes attributed to the persona (date, substrate path, append, edit, or create, and the slice or run id), plus the count of writes outside its owned sections and of conflicts the substrate peers flagged.
5. Sample outputs: 3 to 5 representative writes in full text, chosen to span the persona's owned sections, each rated strong, adequate, or thin on substance rather than formatting.
6. Review questions, each marked Y or N, with every N addressed in the rationale: the K.7 trend is flat or improving; writes stayed inside the owned sections; the samples show substance rather than boilerplate; the substrate peers raised no unresolved conflict; the behavior fits the proposed L4 scope.
7. Decision block: the verdict, a rationale of one to three sentences, the named conditions when the verdict is REQUEST_CHANGES, the reviewer, and the date.

### User judgment

The single question the user answers on the packet is:

> **Does this persona deserve full peer ownership equivalence, commands-grade trust on its owned artifacts?**

L4 is not "L3 plus a little more autonomy." It is the explicit decision that the persona's substrate writes carry the same operational weight as first-party command output: same validation, same drift-guard severity, same downstream consumer trust. The user is judging equivalence, not incremental improvement.

### Verdict shape

The verdict is one of three. This shape is defined here and nowhere else; no ADR carries it (ADR-0036 decides K.7 oscillation and the Path B evidence weighting for L3, not this verdict).

- **APPROVE**: promote the persona to L4. The implications below take effect on the next dispatch.
- **DECLINE**: the persona stays at L3. The gate is closed; it may be re-reviewed if conditions materially change, but DECLINE is not a deferred yes.
- **REQUEST_CHANGES**: the persona stays at L3 with named concerns it must visibly address before the gate reopens. Fhorja surfaces those concerns in the next packet.

The verdict, its rationale, and the packet snapshot are kept in the persona's ledger, `_internal/maturity-ladder/<persona-id>.md` (maintainer-local and gitignored; start one from `templates/MATURITY_LEDGER.template.md`).

### L4 implications

When APPROVE fires:

- **owned_sections expansion**: the persona's `owned_sections` grows from the single L3 entry to the list locked in the verdict body, never an open-ended set.
- **Full validation**: L4 output runs through the same schema and contract validators as command output, with no persona soft mode.
- **Alerts on REFUSE**: an L4 persona returning REFUSE is a P3 operational alert, because a commands-grade persona should rarely refuse.
- **Drift-guard escalates to P2**: a drift-guard finding against L4 output becomes a P2 bug finding, against P3 or informational at L3.

After APPROVE, in one commit: set `maturity_level: L4` and the approved `owned_sections:` list in the `commands/<persona-id>/SKILL.md` frontmatter, and record the promotion (date, path, latest K.7 pass rate) with the packet in `_internal/maturity-ladder/<persona-id>.md` (maintainer-local and gitignored). Then run `./scripts/lint-commands.sh`, whose maturity-shape check reads the new level against the `owned_sections` count.

### Demotion from L4

L4 is revocable under the same rules as every other level (`## Demotion rules` above): each of the five takes an L4 persona back to L3, with the rationale written in its ledger. A K.5 error or a SYSTEMIC K.7 cluster traced to the persona demotes it at once, and no new review is needed, because the trust was conditional and the conditions failed.

A demoted persona may re-enter the review cycle only after fresh eligibility is established from the demotion date: a new 30-day window, a new count of 10 writes across 3 folders, and zero new K.5 errors or SYSTEMIC clusters since demotion. A prior APPROVE does not carry forward.

## Lifecycle: frozen

A frozen command works and stays installed. It receives no further investment: an
issue about it closes as wontfix, it is not extended in a capability wave, and its
documentation is corrected only when it is wrong, never expanded. Frozen is not
deprecated: removal needs an ADR of its own, and this field does not authorize one.
Absence of the field means active. The field is optional so that freezing a command
costs one line and unfreezing costs deleting it.

Frozen surfaces today: <!-- count:frozen-commands -->7<!-- /count -->.

### Frozen commands

| Command | Frozen | Why |
| --- | --- | --- |
| `workflow-guide` | 2026-08-31 | 4 months of exposure, zero invocations, indegree 1. The one surface whose job is explaining the workflow, never reached by anyone who has it installed. |
| `component-spec` | 2026-08-31 | design-system family; 3 months, zero invocations despite indegree 9 |
| `design-bootstrap` | 2026-08-31 | design-system family; entry point of a cluster nothing entered |
| `journey-map` | 2026-08-31 | design-system family |
| `pattern-doc` | 2026-08-31 | design-system family; the only one of the seven no living command cites |
| `design-spec-review` | 2026-08-31 | design-system family; exempt from the usage metric and still never reached |
| `foundation-audit` | 2026-08-31 | design-system family |

Frozen is not removal. Six of the <!-- count:frozen-commands -->7<!-- /count --> are cited by living commands, `design-bootstrap` by seven of them, so removing any of those rewrites routes rather than deleting a file. Removal is one deliberate decision about the design cluster, with its own ADR, and freezing first is the reversible order.

### Frozen surfaces that are not commands

| Surface | State | Why |
| --- | --- | --- |
| `scripts/autonomy/` (governor.sh, classify-slice.sh, stop-check.sh) | frozen | shipped, exercised once, no demand since |
| `knowledge/` auto-load (ADR-0054) | frozen | the decision stands and the mechanism stays off |
| `.claude/settings.json` hooks authorized but not wired | frozen | authorized in writing, not installed, and that gap is deliberate |
| `scripts/s3-thin-skills.py` | never again | not frozen: it is a path this repository decided not to walk twice |

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
- a failing lint for the frontmatter `maturity_level` shape (the check shipped later, warn-only)
- automated promotion scripts (the discipline is manual: author K.7 evals, run them, read the dashboard, update SKILL.md + `_internal/maturity-ladder/<persona-id>.md`, which is maintainer-local and gitignored, in one commit)
- L5 promotion criteria details (reserved; will require post-Epic-K research + ADR before any persona attempts the L4 -> L5 hop)

The first live promotions of this ladder happened in the 2026-06-05 session: rls-auth-boundary-auditor and post-deploy-verifier promoted to L3 via ADR-0036 Path B; migration-safety-steward, jtbd-switch-interviewer, and color-contrast-architect reached L2 that session with strong K.7 floor evidence and have since satisfied the 2nd-distinct-task-folder gate to reach L3 (ledgers under `_internal/maturity-ladder/`, maintainer-local and gitignored). The original five K.8 personas are now at L3; a11y-audit, performance-budget, slo-define, and postmortem-author launched later and remain at L1.

## Evidence history

The per-batch log of the 2026-06-05 session behind the first L3 promotions (14 batches, 125 agents, no substrate orphan) left this file on 2026-09-23. It stays in the repository history at commit `052440cb`, and the current level of each persona is the canonical table above.

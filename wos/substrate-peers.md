---
activation: model_decision
description: Substrate peer architecture -- section ownership, read/write contracts, conflict resolution, audit trail for the four task-memory files (TASK_STATE / DECISIONS / IMPLEMENTATION_PLAN / SOURCE_OF_TRUTH) AND the fleet-substrate files retrofitted in K.1 (ATOM_AUDIT / SCREEN_MAP / routes / INITIATIVE_INDEX / EXTERNAL_RESEARCH / VERIFICATION_LOG / REFERENCES). Load before any command, persona, or fleet worker writes to substrate.
---

# Substrate peers

Defines the substrate-peer architecture: how commands, personas (SKILL.md files), and Epic J fleet workers share canonical task-memory and fleet-substrate files without stomping on each other.

Load this file when:
- you are about to write to a TASK-LEVEL substrate file (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`)
- you are about to write to a FLEET-SUBSTRATE file owned by an Epic J orchestrator (`ATOM_AUDIT.md`, `SCREEN_MAP.md`, `routes.md`, `INITIATIVE_INDEX.md`, `EXTERNAL_RESEARCH.md`, `VERIFICATION_LOG.md`) or to project-level `REFERENCES.md`
- you are designing a new command or persona and need to know which sections it may own or propose to
- two writers appear to be racing on the same section
- a fleet worker partial needs to be merged into substrate
- the ownership advisory counted a write outside a section's conventional owner, or a write to a section with no row

Governing ADR: ADR-0034 (substrate peers + worker contract); ADR-0232 makes the ownership matrix descriptive (a write outside it is recorded and counted, never refused).
Related topics: `wos/task-file-contracts.md`, `wos/sub-agent-orchestration.md`, `wos/operating-modes.md`.

## Why substrate peers (not layers)

Epic K v2 collapsed v1's `personas as a layer above commands` into `commands and personas are PEERS sharing substrate`. Substrate = the <!-- count:task-memory-files -->4<!-- /count --> task-memory files PLUS the fleet-substrate files retrofitted in K.1 once Epic J pilots shipped (J.6-J.10). Both peers read freely; both may propose; ONE peer is the conventional owner of each section's writes (rule 2 below: routing by convention, ADR-0232).

Pattern matches: Microsoft Agent Framework Workflows (typed shared state with executor ownership), Anthropic Skills (read-only-by-default), VS Code Chat Participants (owner-keyed `workspaceState`), Stripe Workbench, Vercel AI SDK 6, Cognition Devin Managed Devins, GitHub Copilot Workspace, LangGraph state machines, HashiCorp Terraform agents.

## Section ownership matrix

Legend: O = conventional owner (writes via Edit/Write); P = conventionally stages a PROPOSED block (optional since ADR-0232, rule 3 below); R = read-only; F = fleet-inbox writer (typed payloads through the ADR-0158 carrier, merged by owner).

### TASK_STATE.md

**Correction (F-3, dogfood-wave 2026-07-11):** the five rows below were reconciled against the real Operating-rules/Required-output text of each named command (and, for `## Canonical decisions`/`## Open questions / blockers`/`## Current status`, independently corroborated by the real archived `2026-07-09_godot-2d-e2e-completeness-audit` task's own TASK_STATE.md write headers). Scope was kept tight to these five confirmed mismatches.

**Reconciliation (ADR-0101, theme dogfood wave 2026-07-11):** the full table pass F-3 deferred, forced by 7 of 10 independent unattended dogfood paths hitting matrix-vs-command drift. Treating `commands/*.md` as canonical (per CLAUDE.md): six template-mandated sections gained rows (`## Requested deliverables`, `## Recommended pipeline`, `## Current closure target`, `## Resume notes`, `## Work complexity (for next execution step)`, `## Task scope level`), the genesis exception (rule 2a) and the pattern-writer rule (rule 2b) were added to the read/write contract, and the rows below carry the corrected co-writers.

| Section (H2) | Owner | Co-writers (propose) | Readers |
|---|---|---|---|
| `## Task summary` | task-init | direction-adjust (P) | all |
| `## Quick reanchor` | sync-task-state | decision-interview (co-write on lock, ADR-0111); task-init (genesis) | all |
| `## Current phase` | slice-closure | sync-task-state, where-we-at, implementation-plan, plus the pattern writers (rule 2b) | all |
| `## Objective` | task-init | post-review-pivot (P) | all |
| `## Requested deliverables` | task-init (seed, ADR-0056) | implementation-plan (--spec ledger extension); slice-closure, task-close, review-hard, where-we-at (re-tagging via `commands/_shared/deliverable-reconcile.md`); decision-interview (de-scope flip, mandated by its own deliverable-shaping pass, ADR-0056) | all |
| `## Recommended pipeline` | task-init (ADR-0025, ADR-0101) | what-next, sync-task-state | all |
| `## Source of truth` | task-init | code-locate (P), capture-references (P) | all |
| `## Current known facts` | sync-task-state | impact-analysis, code-locate, code-context-map, db-context-supabase, compact-task-memory (prunes entries during compaction) | all |
| `## Canonical decisions` | sync-task-state | decision-interview (direct write in persist mode, authorized by the user's explicit LOCK signal; propose-only in interview mode), contract-signoff (P), direction-adjust (P), implementation-plan | all |
| `## Open questions / blockers` | targeted-questions | im-stuck, pr-feedback-ingest, decision-interview (direct write in persist mode to retire rows resolved by this turn's LOCK; propose-only in interview mode), sync-task-state, test-strategy, incident-triage (instrument-first persisted note, ADR-0088) | all |
| `## Observations` | capture-observation | any-command via append-only | all |
| `## Last completed step` | sync-task-state | implement-approved-slice, slice-closure, decision-interview, godot-scene-plan, implementation-plan, godot-runtime-verify, test-strategy, direction-adjust (when the adjustment makes it wrong), compact-task-memory (records itself, ADR-0141), plus the pattern writers (rule 2b) | all |
| `## Current status` | sync-task-state | slice-closure, where-we-at, decision-interview, implementation-plan, plus the pattern writers (rule 2b: `### In progress`) | all |
| `## Active files in scope` | impact-analysis | code-locate, sync-task-state, implementation-plan | all |
| `## Constraints / things that must not change` | invariants-and-non-goals | sync-task-state | all |
| `## Risks to watch` | rls-auth-boundary-auditor (L3+ exclusive owner per K.6 maturity ladder, 2026-06-05) | sync-task-state, impact-analysis, review-hard, security-review (P), test-strategy, post-deploy-verifier (P), incident-triage (instrument-first persisted note, ADR-0088), direction-adjust (new risk introduced by the adjustment), compact-task-memory (prunes entries during compaction), repo-consistency-sweep (Step 10 pointer) | all |
| `## Recommended next step` | what-next | sync-task-state, slice-closure, im-stuck, decision-interview, godot-scene-plan, where-we-at, approve-plan, implement-approved-slice, implementation-plan, test-strategy, direction-adjust (routes back after the adjustment), plus the pattern writers (rule 2b) | all |
| `## Current closure target` | sync-task-state | slice-closure, implementation-plan, plus the pattern writers (rule 2b) | all |
| `## Work complexity (for next execution step)` | implementation-plan | sync-task-state, what-next | all |
| `## Resume notes` | sync-task-state | compact-task-memory, resume-from-state (P), delivery-asset (P, optional asset-path line); task-init, task-workspace and branch-commit (the `Task branch:` and `Base branch:` lines, ADR-0233) | all |
| `## Task scope level` | task-init | sync-task-state | all |
| `## Compaction history` | compact-task-memory | (sole owner) | all |
| `## Latest sweep` | repo-consistency-sweep | (sole owner) | all |
| `## Ruled-out hypotheses` | incident-triage | (sole owner) | all |
| `## Closure record` | task-close (terminal, ADR-0105) | (sole owner) | all |

**Whole-file operators (rule 2c, journey-validation 2026-08-11).** Two commands operate on `TASK_STATE.md` as a whole file rather than on named sections, so listing them per row would be both wrong and unmaintainable: `state-reconcile` repairs any section where it detects drift, and `compact-task-memory` prunes or preserves every section by its own preserve/filter contract. Both are authorized co-writers on ANY `TASK_STATE.md` section, bounded by their own command contracts and by two limits: neither may introduce content that no other artifact supports (a reconcile writes what the evidence says, not what it prefers), and neither may write a section its own contract does not reach (`compact-task-memory` still never edits `SLICES/*`, `DECISIONS.md`, or the other immutables it names). They still emit the transaction header and the audit line per section written, exactly like a named co-writer. This rule exists because `state-reconcile` appeared in no row at all while signing seven writes across six sections in a single dogfooded run.

**Known-incomplete, self-heal note (P1-3, dogfood-wave-2 2026-07-12):** this matrix is hand-maintained and has recurred as incomplete across three independent dogfood waves (godot-wave F-3, ADR-0101's ten-session reconciliation, this wave's P1-3). A command that writes a TASK_STATE.md section not listed as its own row or co-writer entry above should self-add its row (owner or co-writer, per its actual write behavior) so the matrix keeps describing what happens; the headline of `scripts/check-substrate-ownership.py` is the count of writes to a section with no row, the gap this note asks writers to close. A deferred follow-up (not built this wave, net-new scope): a small grep-based lint cross-checking each command's declared TASK_STATE writes (its own Required-output / Operating-rules text) against this matrix, retiring this recurring class the way the ADR-0029 registry and count-marker drift guards do.

**Header-currency limitation (P2-6, dogfood-wave-2 2026-07-12):** `scripts/scan-substrate-headers.sh` checks header presence and syntax only, never header currency: a stacked pair of headers above one section (an old header never removed under a new one), or a header whose `owner`/`run_id` no longer reflects who last wrote the content beneath it after a later same-section write, both pass the script's check undetected (0 drift reported). A fuller check would need to diff header claims against actual last-writer provenance, which the script does not currently track. Documented as a known limitation, parallel to the REFERENCES.md drift-scan-noise note above; revisit building the fuller check if this recurs a third time.

### DECISIONS.md

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Locked decisions` (D-N) | decision-interview | contract-signoff, direction-adjust, post-review-pivot | all |
| `## Provisional decisions` (P-N, P-1) | decision-interview | resolve-contract-gaps, direction-adjust, targeted-questions | all |
| `## Decision history` | decision-interview | contract-signoff, direction-adjust, post-review-pivot | all |
| `## Open questions` | targeted-questions | resolve-contract-gaps | all |
| `## Discarded alternatives` | NONE (forbidden per `wos/task-file-contracts.md`) | n/a | n/a |

**Write rule:** D-N entries are **APPEND-ONLY**. Editing a locked D-N requires a new `D-(N+M)` with `Supersedes: D-N` line + entry in `## Decision history`. Never mutate silently. **Placement (ADR-0101):** `## Decision history` is a separate H2 placed immediately after `## Locked decisions`; new D-N entries are appended at the END of the `## Locked decisions` block, before the next H2, so the block stays contiguous (the `sha_of_section` computation assumes one contiguous block per H2).

**Provisional decisions (P-1).** `## Provisional decisions` holds `### P-N` entries the agent chose from evidence, never the maintainer's own input: each carries `Evidence:`, `Impact: high|normal`, and `Status: provisional`. It is a separate H2 from `## Locked decisions`, not a tag inside it, so a deterministic reader (`scripts/check-plan-coverage.sh`) can tell a provisional entry from a locked one by section alone rather than by parsing a status word out of a `### D-N` heading. A P-N is never edited or moved. The maintainer confirms it with a new `### D-N` under `## Locked decisions` carrying `Confirms: P-N`, or replaces it with a new `### D-N` there carrying `Supersedes: P-N`. WHILE a P-N is not yet confirmed or superseded by the maintainer, the agent SHALL correct it only by appending a new `### P-N` that carries a `Replaces: P-M` line and the reason, and SHALL leave P-M exactly as written (ADR-0235). Plans SHALL cite only the newest entry of a replacement chain. `Replaces:` links two P-Ns only, and the maintainer's `Confirms:` and `Supersedes:` paths are unchanged. `approve-plan` keeps reading `## Locked decisions` as the only authorization; a P-N passes a review labeled, never as authorization (P-2).

**Defeasible-claim revision (ADR-0109, D-10).** `DECISIONS.md ## Decision history` is the append-only home for TWO distinct operations, not one. (1) Supersede: a new decision replaces an old one; the trigger is an intent change; recorded as `D-(N+M)` with `Supersedes: D-N` (above). (2) Evidence-triggered revision: new evidence contradicts an already-persisted claim; the trigger is an evidence change, not an intent change. The two coincide only when the contradicted claim IS a locked decision, in which case the revision is recorded AS a supersede. When the contradicted claim is a NON-decision persisted claim (a `TASK_STATE.md ## Current known facts` row, a `TASK_STATE.md ## Risks to watch` row, an `IMPACT_ANALYSIS.md` finding), the revision is a standalone Decision-history entry with a `Revises:` line naming the claim's location, the contradicting evidence, and that evidence's provenance rank per `WORKFLOW_OPERATING_SYSTEM.md ## Evidence priority`. Rules: the revision is APPEND-ONLY and never overwrites the prior claim text; the contradicting evidence must sit at a provenance rank at least as high as the claim's, and an equal-rank conflict is recorded `[OPEN: equal-rank, escalate]` rather than auto-resolved; a command that notices contradicting evidence but is not a `DECISIONS.md ## Decision history` co-writer routes to `direction-adjust` (mid-task realization) or `decision-interview` (a locked decision) to record it, rather than widening the co-writer set. Lifecycle position: a revision entry is written `[OPEN]` and an in-task checkpoint only annotates it; `task-close` blocks archive on any `[OPEN]` revision (`commands/task-close.md`). A revision is resolved by a superseding decision, an accepted-and-recorded revision that updates the owning section through its normal owner, or an explicit `[WAIVED: <reason>]` tag.

### IMPLEMENTATION_PLAN.md

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Target behavior` | implementation-plan | post-review-pivot (P) | all |
| `## Current gaps` | implementation-plan | impact-analysis (P) | all |
| `## Constraints` | invariants-and-non-goals | implementation-plan (direct write while no `INVARIANTS_AND_NON_GOALS.md` exists for the task; propose-only after the owner runs, ADR-0101) | all |
| `## Infrastructure prerequisites` | implementation-plan | NONE | all |
| `## Slices` | implementation-plan | task-init (the one-slice route, ADR-0225: it writes the single approved slice itself), implement-slice-complement (micro-delta only), slice-closure and sync-task-state (opt-in slice-status propagation, Regime 1, logged H3-scoped) | all |
| `## Execution waves` | implementation-plan | NONE | all (implement-fleet reads to compute waves, per ADR-0041/0042) |
| `### Slice N` (per-slice body) | implementation-plan | implement-approved-slice (status only), implement-fleet (status only, via its workers), slice-closure (status only), sync-task-state (status only, Slice-08 P2 slice-status field); these H3-scoped co-writes are LOGGED at the owning `## Slices` H2 per `commands/_shared/substrate-write-protocol.md` (ADR-0101) | all |
| `## Validation expectations` | test-strategy | implementation-plan (direct write while no `TEST_STRATEGY.md` exists for the task; propose-only after the owner runs, ADR-0101) | all |
| `## Rollout and rollback notes` | implementation-plan | release-plan (P) | all |
| `## Risks and mitigations` | implementation-plan | review-hard (P) | all |
| `## Open questions or approvals still needed` | implementation-plan | targeted-questions (P) | all |
| `## Spec coverage` (--spec mode, ADR-0061) | implementation-plan | NONE | all |
| `## Approval log` | approve-plan (append-only) | task-init (the one-slice route, ADR-0225: it appends the route's lock line in place of approve-plan, which that route skips); no other co-writer (the inline co-write ended with ADR-0208) | all |

### SOURCE_OF_TRUTH.md

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Active codebase / repo` | task-init | project-bootstrap (seed) | all |
| `## Active branch` | task-init | branch-commit (P) | all |
| `## Main files in scope` | code-locate | impact-analysis, sync-task-state | all |
| `## Repo instruction files` | impact-analysis | code-locate (P) | all |
| `## Tickets / docs / Figma / links` | task-init | capture-references (P) | all |
| `## Official external docs` | capture-references | external-research (P) | all |
| `## Repositories` (multi-repo) | task-init | project-bootstrap | all |
| `## External research` (cross-link) | external-research | external-research-fleet | all |
| `## Project-level memory` | task-init | project-bootstrap (seed) | all |
| `## Slice status` (Slice-08 P2 pointer) | slice-closure | sync-task-state | all |

**Slice-status propagation (Slice-08 P2)** is opt-in via a per-run bounded `propagate-slice-status` scope; `README.md` and `TEST_STRATEGY.md` are intentionally ABSENT from every table above (plain regime: no wos:write header, no audit line, outside `scan-substrate-headers.sh`). Adding rows for them would wrongly pull them under the substrate-write protocol.

## Fleet-substrate files (K.1 retrofit, 2026-06-04)

Files written by Epic J orchestrators (J.6-J.10) that hold cohort-level state outside the <!-- count:task-memory-files -->4<!-- /count --> task-memory files. The same ownership convention applies (rule 2 below): ONE peer is the conventional owner of each section, and transaction headers are required when modifying. The per-file write rules below (replace-in-full, sole merger, deduplication keys) are merge semantics, not ownership, and stay normative.

Mixed-mode (single + fleet variants both ran in the same task) is RECONCILED by `state-reconcile`; never silently merged. Files that already existed before K.1 retrofit gain header emission incrementally when next touched (legacy-without-headers is VALID per the `## Legacy file without headers` rule).

### ATOM_AUDIT.md (design-system audit, J.6 owner)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Summary Table` | atom-audit-fleet (cohort) / atom-audit (single) | NONE -- mixed-mode -> state-reconcile | all |
| `## Audit history` | atom-audit-fleet (cohort) / atom-audit (single) | append-only by either | all |

Write rule: in cohort mode, `atom-audit-fleet` is SOLE writer of `## Summary Table` (replaces the table body, never partial-merges). In single mode, `atom-audit` is SOLE writer for that run. If both variants write to the same file in the same task, drift-guard surfaces it; `state-reconcile` is the SOLE rescuer.

### SCREEN_MAP.md (screen index, J.7 owner)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Screen index` (table body) | screen-spec-fleet (cohort, per-persona scope) | screen-spec (P, single row), design-bootstrap (seed) | all |

Write rule: `screen-spec-fleet` rewrites rows for ONE persona per run (mixing personas FORBIDDEN). Rows for personas outside the fleet's scope are PRESERVED unchanged. `screen-spec` single-instance appends one row per run; `design-bootstrap` seeds the empty table from a template. Duplicate `(persona, screen_name)` keys -> REFUSE + `event=fleet-merge` log line.

### routes.md (route index, J.7 owner)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Routes` (table body) | screen-spec-fleet (cohort) | screen-spec (P, single route), design-bootstrap (seed) | all |

Write rule: `screen-spec-fleet` appends new routes returned by workers (one per worker's `new_route` field, deduplicated by `path`). Duplicate `path` keys with different persona/screen -> REFUSE + log conflict.

### INITIATIVE_INDEX.md (cross-task index, J.8 owner, NEW file)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Initiatives` (table body) | task-init-fleet | NONE | all |

Write rule: sole owner is `task-init-fleet`. Rows accumulate across runs; the fleet only appends or updates rows for ITS run's slugs. Older rows preserved. No single-instance equivalent (task-init writes the per-sub-task files; the cross-task index only exists when a fleet ran).

### EXTERNAL_RESEARCH.md (multi-source synthesis, J.9 owner)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| (whole file -- canonical synthesis format) | external-research-fleet (cohort) / external-research (single) | NONE -- replace-in-full pattern | all |
| `## Conflicts surfaced` (fleet-only) | external-research-fleet | NONE | all |

Write rule: REPLACE-IN-FULL on every run; never partial-merge per `commands/external-research.md`. Fleet mode emits the additional `## Conflicts surfaced` section when CONTRADICTING claim groups detected (per ADR-0018 reconciliation taxonomy). If a refresh would overwrite handwritten notes, those belong in `DECISIONS.md` or `TASK_STATE.md`, not in `EXTERNAL_RESEARCH.md`.

### VERIFICATION_LOG.md (human-readable verdict log, J.10 + ADR-0033 owner)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Verdicts` (single-artifact entries, append-only) | verify-against-rubric | verify-against-rubric-fleet (cohort entries below) | all |
| `## Cohort verdicts` (J.10 only) | verify-against-rubric-fleet | NONE | all |

Write rule: BOTH variants append to the same file. Single-artifact entries land under `## Verdicts`; cohort entries (with failure clustering) land under `## Cohort verdicts`. Sections are distinct -- no cross-section overlap. Entry IDs are unique within their section.

Distinct from `.wos/VERIFICATION_LOG.jsonl` (machine-readable provenance log; see `## Audit trail` below).

### REFERENCES.md (project-level memory, co-owned)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## References` (entries, append-only, deduplicated by URL) | capture-references | external-research (P for newly-captured during synthesis), external-research-fleet (newly-captured by workers) | all |

Write rule: entries are append-only; deduplication by URL is enforced at write time. Both `external-research` and `external-research-fleet` may write newly-captured entries per the canonical `capture-references` format. The `Context within project` field (per ADR-0018) is required for entries captured after 2026-05-15.

**K.2 protocol applicability (v2.1 deferral):** REFERENCES.md is PROJECT-level memory. The canonical `commands/_shared/substrate-write-protocol.md` targets `active/<task>/.wos/VERIFICATION_LOG.jsonl`, which is TASK-scoped and does not exist at the project layer. Writes to REFERENCES.md that occur before any active task (e.g. `capture-references` from `project-bootstrap`) currently emit NEITHER the inline `<!-- wos:write -->` header NOR a JSONL line; this is a known v2.1 gap. Writes to REFERENCES.md that occur DURING an active task SHOULD emit the inline header + a JSONL line under that task's `.wos/` (treating the cross-task write as a co-writer event of the active task's audit chain). A project-level audit log location is post-v2.1 work.

**Drift-scan noise (F-11, dogfood-wave 2026-07-11):** `scripts/scan-substrate-headers.sh` exempts REFERENCES.md's 3 fixed template sections (`## Format reminder`, `## <Topic / Tag>`, `## Entries`) from its drift count, since three independent sessions each reconfirmed them as unfixable false-positive noise under the gap above. This suppresses the scan artifact only; the deferred gap itself is unchanged.

### REVIEW_PREFERENCES.md (project-level, single-owner)

| Section | Owner | Co-writers | Readers |
|---|---|---|---|
| `## Declined findings` (append-only, file_hash-keyed) | apply-sweep-triage | NONE | all (repo-consistency-sweep reads to suppress prior-declined findings) |

Write rule: `apply-sweep-triage` is the SOLE owner; the file is created on the first triage run and grows append-only across sweeps. Sweep reads it during its suppression step (Step 8 of `commands/repo-consistency-sweep.md`). The file lives at `projects/<client>__<project>/REVIEW_PREFERENCES.md` -- project-scoped, not task-scoped.

**K.2 protocol applicability:** same deferral as REFERENCES.md above -- the file is project-level and the K.2 audit log is task-scoped; writes during an active task SHOULD emit headers + JSONL under the active task's `.wos/`, but the canonical protocol for project-level files is a v2.1 gap.

### Personas CUSTOM

L1 / L2 personas have R access to all four files and P (PROPOSED) access to:
- `TASK_STATE.md ## Observations` (also append-only direct write at L2)
- `DECISIONS.md ## Locked decisions` (PROPOSED block under a new D-N draft)
- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`

L3 owned sections (as of 2026-06-05 lived L3 test, ADR-0036):
- `rls-auth-boundary-auditor` (L3 Path B per ADR-0036) owns `TASK_STATE.md ## Risks to watch` exclusively. Other CUSTOM personas at L1/L2 no longer have P access there; they re-route risk-content to `IMPLEMENTATION_PLAN.md ## Risks and mitigations` (the multi-persona-PROPOSED shared sink).
- `post-deploy-verifier` (L3 Path B per ADR-0036) owns `POST_DEPLOY_PLAN.md` whole-file (persona-owned report file).
- `migration-safety-steward` (L3 Path B per ADR-0036) owns `MIGRATION_SAFETY.md` whole-file (persona-owned report file).
- `jtbd-switch-interviewer` (L3 Path B per ADR-0036) owns `JTBD_INTERVIEWS.md` whole-file (persona-owned report file).
- `color-contrast-architect` (L3 Path B per ADR-0036) owns `CONTRAST_AUDIT.md` whole-file (persona-owned report file).

All 5 K.8 personas now at L3 per ADR-0036 Path B (rls-auth-boundary-auditor and post-deploy-verifier first, then migration-safety-steward, jtbd-switch-interviewer, and color-contrast-architect on multi-folder fleet evidence). Two L3 ownership patterns coexist: (a) substrate-H2-section ownership (rls is sole instance, contested-section claim); (b) persona-report-file ownership (pdv, mss, jtbd, cc; non-contested whole-file claim parallel to L1's persona-report-file write capability). Both are valid under the K.6 spec language ("section ownership for ONE explicitly-declared low-risk section") where "section" can mean an H2 within a substrate file OR a persona-owned report file.

L3 promotions are tracked per persona in `_internal/maturity-ladder/<persona-id>.md` (gitignored). The owned_sections field in each persona's SKILL.md frontmatter is authoritative for which section the persona owns at L3+.

### Epic J fleet workers

Fleet workers return a payload matching `worker_output_schema` through the selected carrier (ADR-0158 D-1). On the dynamic-workflow path the runtime supplies the typed result; workers are never instructed to call StructuredOutput. On the `Agent` path the worker writes only its assigned return file:

```
fleet-inbox/<run_id>/<worker_id>.json   # resolved by the orchestrator before native dispatch
```

The native JSON file is the return carrier, not a replay aid. The orchestrator may persist a runtime result or a separate replay copy, with its producer and consumer named; copies never count as extra workers. The ADR-0158 D-2 exception grants no writes outside the assigned run inbox. Existing command-specific grants for disjoint task folders, screen specs and implementation worktrees remain in force; other substrate writes belong to the orchestrator.

The orchestrator command (e.g. `atom-audit-fleet`, `screen-spec-fleet`) is the SOLE merger.

## Read/write contracts

Read-only peers: the `--lost-session` mode of `resume-from-state` (ADR-0113) is read-only by construction across ALL four files: it emits no `wos:write` header and no log line, and its transcript extractions enter the substrate only as PROPOSED lines consumed by `state-reconcile`. A recovery flow that finds itself about to write a substrate section has left the mode's contract.

### TASK_STATE.md -- section-owned, transactional

1. Every write MUST emit a transaction header above the section:
   ```
   <!-- wos:write owner=<id> section='## X' run_id=<uuid> ts=<iso8601> reason=<<=80chars> mode=<applied|proposed> -->
   ```
2. **Routing by convention (ADR-0232).** The matrix describes who normally writes each section; nothing enforces it. A writer outside a section's row writes the section anyway, with the transaction header and the JSONL line like any write, and names the conventional owner in `reason`. The write is recorded and recoverable: `sha_before` pins the bytes it replaced. Nothing refuses it; `scripts/check-substrate-ownership.py` counts such writes as an advisory. Never a silent partial write, and needing another command's work still means naming it on `Run now:`, never invoking or emulating it inline (`## Conflict resolution`).
2a. **Genesis exception (ADR-0101):** `task-init` (and `task-init-fleet`, per ADR-0040) is the initial writer of EVERY section it creates at task genesis, across all <!-- count:task-memory-files -->4<!-- /count --> task-memory files, emitting `owner=task-init` headers with `sha_before=null`; the per-section ownership matrix governs all subsequent mutations. This documents what `commands/task-init.md` already mandates; a first-ever write at genesis is the owner's write by construction.
2b. **Pattern-writer rule (ADR-0101):** every consumer of the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section write pattern (`commands/_shared/task-state-slice-closure-pattern.md`: slice-closure, approve-plan, implement-fleet, release-plan, ai-feature-eval-harness, verify-against-rubric and its fleet, and peers that cite the pattern) is a sanctioned DIRECT co-writer of exactly the <!-- count:closure-pattern-sections -->5<!-- /count --> sections that pattern names (`## Current phase`, `## Last completed step`, `### In progress` under `## Current status`, `## Recommended next step`, `## Current closure target`), without a per-row listing in the matrix. The matrix lists additional co-writers beyond the pattern set.
3. **Staging is optional (ADR-0232).** A co-writer marked (P) may write the section directly under rule 2, or stage a `<!-- PROPOSED by <id>: -->` block INSIDE the section when the user wants to read it before it lands; `approve-proposed` promotes a staged block on request. The (P) mark records the usual form, not a requirement, so rules 2 and 3 never disagree about whether a co-writer may write.
4. `## Observations` is the only section that is true append-only freeform.
5. `## Compaction history` is sole-owned by `compact-task-memory`.
6. Same-owner same-section repeat write: no-op-if-identical (SHA compare); otherwise new header replaces prior, prior logged.

### DECISIONS.md -- append-only D-N ledger

1. New decisions: append `### D-<N>` at the end of `## Locked decisions`. Never edit existing D-N text.
2. Supersedes: new `D-(N+M)` with `Supersedes: D-N` + rationale. Old D-N gains tag `[SUPERSEDED by D-<N+M>]`.
3. EARS form required when `impact-analysis` flagged behavior/contract risk (per ADR-0031).
4. Discarded alternatives FORBIDDEN (`wos/task-file-contracts.md` already enforces).
5. Evidence-triggered revision (ADR-0109, D-10): a distinct append-only operation in `## Decision history`, not a supersede unless the contradicted claim is itself a locked decision. See the `## Decision history` **Defeasible-claim revision** write rule above for the full contract; `task-close` blocks on an `[OPEN]` revision.
6. Provisional decisions (P-1): append `### P-<N>` at the end of `## Provisional decisions`, never inside `## Locked decisions`. A P-N is never edited or moved. The maintainer confirms it with a new `### D-N` under `## Locked decisions` carrying `Confirms: P-N`, or replaces it with a new `### D-N` there carrying `Supersedes: P-N`. WHILE a P-N is not yet confirmed or superseded by the maintainer, the agent SHALL correct it only by appending a new `### P-N` that carries a `Replaces: P-M` line and the reason, and SHALL leave P-M exactly as written (ADR-0235). Plans SHALL cite only the newest entry of a replacement chain. `Replaces:` links two P-Ns only, and the maintainer's `Confirms:` and `Supersedes:` paths are unchanged.

### IMPLEMENTATION_PLAN.md -- slice-status-restricted

1. Add/remove/reorder slices: `implementation-plan` only.
2. Inside `### Slice N`, co-writers may mutate ONLY `Status:` and `Evidence:` lines:
   - `implement-approved-slice`: `Status: in-progress` -> `Status: implemented (pending closure)`
   - `slice-closure`: `Status: implemented (pending closure)` -> `Status: closed` + Evidence link
3. `implement-slice-complement` APPENDS a `Micro-deltas:` sub-bullet (never mutates acceptance criteria).
4. Cross-slice churn (renumber, reorder) requires `implementation-plan` re-run with `reason=replan`.

### SOURCE_OF_TRUTH.md -- section-owned, multi-repo-aware

1. `## Active codebase` and `## Active branch` change requires `task-init` re-run OR `branch-commit` (P) approved.
2. `## Main files in scope` appended by `code-locate`; `impact-analysis` and `sync-task-state` add/remove with reason in the header.
3. `## Repositories`: `task-init` sole owner; `project-bootstrap` seeds.
4. `## Official external docs` requires `capture-references` with freshness metadata.
5. `## DB context` is a single cross-link pointer to `DB_CONTEXT.md`, owned by whichever `db-context-*` command matches the project's database access path: `db-context-supabase` where the Supabase MCP server is the route, `db-context-postgres` where `psql` or `pg_dump` is. Both write the same pointer and the same `DB_CONTEXT.md`, so neither write falls outside the row: they are one role with two transports, and the later run replaces the pointer rather than appending a second. A Supabase project is also a Postgres project, so do not read the routing as mutually exclusive by database; read it as chosen by how the introspection actually reaches the schema. Added 2026-08-22 after a measurement found this section written by two commands with no matrix row at all.

## Conflict resolution

Two kinds of rule live here. The ownership subsections (the routing rule, owner collision, owner unavailable, propose-only escalation) are descriptive since ADR-0232: a write outside the matrix is recorded and counted, never refused. The same-owner rule, the fleet partial-merge rules, the mixed-mode rescue and the legacy-file rule are merge and audit semantics and stay normative, together with the transaction header, the JSONL line, the SHA chain and the worker contract.

**Cross-command routing rule (v3 wave2, item B; inherited from the rejected chain-mode design; descriptive ownership since ADR-0232).** A command does its own work. Needing another command's work (its judgment, its gate, its owner id on the record) means STOP and name that command on the `Run now:` line, never invoke or emulate it inline, and this holds OUTSIDE any chain or authorization context: an inherited "run without stopping" authorization does not let one command act as another. A section write outside the matrix row is allowed and recorded under rule 2; producing that write by emulating the other command is what this rule forbids. Observed violations motivating the rule: a closure run implementing the next slice under a foreign owner (bv3 turn 10, 2026-07-21), and four slices collapsed under one unrelated command label with no authorization at all (av3, 2026-07-19).


### Owner collision (descriptive, ADR-0232)

Two writers outside the row that touch the same section both land, in order, each with its own header and JSONL line naming the conventional owner in `reason`. The later line's `sha_before` pins the bytes the earlier write left, so a reviewer can tell which version was replaced and verify a restore against it. When the two writes disagree on substance, name the owner on `Run now:` so it settles the section; `state-reconcile` repairs it when the owner cannot.

### Same-owner double write in one run

No-op-if-identical (compare SHA of section bytes). Otherwise: new header replaces prior; prior logged with `event=overwrite` in VERIFICATION_LOG.jsonl.

### Owner unavailable (command file deleted; descriptive, ADR-0232)

No refusal. The row names a command that no longer exists, which the static half of `scripts/check-substrate-ownership.py` reports as a name not on disk; fix the row in this file. Until then a writer records the write under rule 2, and `state-reconcile` stays the rescuer for the section's content.

### Propose-only writer self-escalation (retired, ADR-0232)

Nothing left to escalate: a co-writer may write directly (rules 2 and 3). What stays forbidden is emulating another command's work inline (the routing rule above).

### Fleet partial merge conflict (Epic J)

1. Merger detects via overlapping `target_section` keys.
2. Applies declared `merge_strategy` (`union` / `last-by-timestamp` / `consensus-of-N` / `manual-review`).
3. Logs both in VERIFICATION_LOG.jsonl with `event=fleet-merge`, `partials=[worker_a, worker_b]`, `strategy=<chosen>`.

### Fleet-substrate mixed-mode (single + fleet variants both wrote)

When both the single-instance command (e.g. `atom-audit`) and its fleet variant (e.g. `atom-audit-fleet`) wrote to the same fleet-substrate file in the same task folder, `state-reconcile` is the SOLE rescuer. Detection: drift-guard surfaces SHAs from both owners in `VERIFICATION_LOG.jsonl` for the same file+section. Resolution: `state-reconcile` chooses the most recent write per the file's documented mixed-mode rule (per-file Write rule above) and emits `event=legacy-promote` for the discarded write.

This is a v2.1 known limitation: fleet variants and single variants are not transactionally exclusive. Mixed-mode is rare in practice because the variants are chosen per task by the user, not silently swapped.

### Legacy file without headers

VALID. The first mutating write under v2.1 emits a header only for THAT section. Other sections stay header-less. Drift-guard does NOT flag header-less as error.

## Audit trail (VERIFICATION_LOG.jsonl)

Reuses Epic J J.5 fleet-run provenance log; does not create a parallel log.

**Location:** `active/<task>/.wos/VERIFICATION_LOG.jsonl` (gitignored).

**Schema (one JSON object per line) -- J.5 canonical:**

```json
{
  "ts": "2026-06-04T14:22:11.482Z",
  "run_id": "01HX5KPQ8R-...",
  "owner": "sync-task-state",
  "owner_type": "command",
  "invoked_by": "slice-closure",
  "file": "TASK_STATE.md",
  "section": "## Current phase",
  "event": "write",
  "mode": "applied",
  "sha_before": "a1b2...",
  "sha_after": "c3d4...",
  "reason": "slice-2-implemented",
  "partials": null,
  "strategy": null
}
```

**Fields:**
- `ts` (string, ISO 8601 with millisecond precision): exact moment of write.
- `run_id` (string, ULID or UUID): unique per orchestrator/command invocation; ties multiple log lines together.
- `owner` (string): command or persona name performing the write.
- `owner_type` (enum): `command` | `persona` | `fleet-merger`.
- `invoked_by` (string | null): when the owner was invoked as a worker or via Handoff routing, the parent invoker; null when user-initiated. Added per Epic K v2.1 REFINE to support traceability across persona-invokes-command and orchestrator-invokes-worker chains.
- `file` (string): substrate file path -- either one of the <!-- count:task-memory-files -->4<!-- /count --> task-memory files (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`) OR a fleet-substrate file owned by an Epic J orchestrator (`ATOM_AUDIT.md`, `SCREEN_MAP.md`, `routes.md`, `INITIATIVE_INDEX.md`, `EXTERNAL_RESEARCH.md`, `VERIFICATION_LOG.md`) OR project-level `REFERENCES.md`.
- `section` (string): H2 section header text including the `## ` prefix.
- `event` (enum): `write` | `overwrite` | `propose` | `approve` | `refuse` | `delete` | `fleet-merge` | `legacy-promote` | `partial_merge` | `merge_include` | `merge_with_gap` | `worker_failed` | `worker_interrupted` | `worker_missing` | `worker_timeout` | `retry_needs_revision` | `max_iterations_promoted` | `retry_failed_recoverable` | `quorum_discard`. The `delete` event (ADR-0101) is emitted for each H2 that existed before a write and no longer exists after it (including replace-in-full rewrites; a rename is delete + write); its convention is `sha_before` = the removed section's last hash and `sha_after` = null, the only event where `sha_after` may be null.
- `mode` (enum): `applied` | `proposed`.
- `sha_before`, `sha_after` (string, SHA-256 hex): hash of section bytes excluding the transaction header line itself; `sha_before` is null on first write to a fresh section.
- `reason` (string, <=80 chars): human-readable rationale matching the transaction header `reason` field.
- `partials` (array of worker_id strings | null): populated only for `event=fleet-merge` and convergence-related events.
- `strategy` (string | null): the declared `merge_strategy` (`union` / `last-by-timestamp` / `consensus-of-N` / `manual-review`); populated only for fleet-merge events.

**Optional fields (additive, not part of the required set):**
- `summary` (string, optional, at most 3 lines): a human-facing, capped narrative of what the whole command run did and why, written for the activity-timeline view (`scripts/build-activity-timeline.py`, ADR-0049). Distinct from `reason`: `reason` is a per-section rationale capped at 80 chars; `summary` describes the run as a whole. It is purely additive: the <!-- count:log-fields -->14<!-- /count -->-field required set above is unchanged, and `scripts/verify-log-validator.py` tolerates it. When present on any line of a run, the activity timeline renders it in preference to the aggregated per-section `reason` values for that `run_id`.

**Emission convention:**
- Commands writing substrate emit one line per section write.
- Orchestrators emit one line per merged section (`event=fleet-merge`) PLUS one line per per-worker classification event (`event=merge_include`, `event=worker_failed`, etc.).
- Personas writing PROPOSED blocks emit `event=propose` with `mode=proposed`.
- `approve-proposed` emits `event=approve` per applied file.
- `event=refuse` marks a fleet merge its orchestrator refused because the orphan scan failed (`orphan_scan=failed`, `screen-spec-fleet` and `atom-audit-fleet`). It no longer marks an ownership conflict (ADR-0232): a write outside the matrix is an ordinary `write` whose `reason` names the conventional owner.

**Validator shipped (K.5):** `scripts/verify-log-validator.py` reads the log in the `repo-consistency-sweep` Pre-flight with WARN semantics, and the count surfaces as `verification_log_invalid_count` (see `## Drift-guard hook` below).

**File rotation:** when `VERIFICATION_LOG.jsonl` exceeds 5MB, archive to `VERIFICATION_LOG.<timestamp>.jsonl.gz` and start fresh. Archived logs survive `task-close` and move with the task folder to `archive/`.

**Other `.wos/` artifacts:** the `.wos/` directory also holds the advisory `SESSION_CONTINUITY.json` sidecar written by the opt-in session-continuity hook (ADR-0052), alongside the fleet-inbox partials noted above. Neither is part of the provenance log and both sit outside the substrate-write protocol. The session-continuity hook never rewrites authored `TASK_STATE.md` sections, so it carries no transaction header and does not appear in the ownership matrix.

## Peer invocation patterns

### Pattern A -- persona invokes existing command (flattened from v1 Mode A)

Persona reads substrate, identifies a section that is command-owned and needs update, emits Handoff:

```
### Handoff
Run now: <command-name>
Why: section `## X` is owned by <command-name>; persona <persona-id> proposes: <one-line>.
```

No direct invocation primitive. Persona writes the proposal as a PROPOSED block under any section with P access AND emits the Handoff. The owner command named on `Run now:` applies it, in the same turn when the session is attended (ADR-0186); `approve-proposed` promotes it only on request (ADR-0199).

### Pattern B -- command suggests escalation to persona/skill

When a command detects work matching a persona's declared `triggers:` in the SKILL.md, emit:

```
### Handoff
Run now: skill:<persona-id>
Why: <reason>
```

The skill writes its owned section or report file directly, `APPLIED` in every editor mode (ADR-0199, ADR-0215), stages PROPOSED blocks only in sections it does not own (ADR-0034), and emits its own Handoff to the command that owns any section it proposed into.

### Pattern C -- Epic J fleet worker partial -> orchestrator merger

1. Orchestrator dispatches N workers (J.3 tier-aware dispatch).
2. Each worker supplies ONE typed payload via the selected ADR-0158 carrier: a runtime result or its assigned `fleet-inbox/<run_id>/<worker_id>.json` file. The orchestrator validates and counts it once; prose and absent or malformed payloads do not satisfy the return contract.
3. Orchestrator waits for all OR timeout (J.4 convergence).
4. Orchestrator merges per declared `merge_strategy`; emits transaction headers; appends one `VERIFICATION_LOG.jsonl` line per merged section with `event=fleet-merge`.
5. Inbox cleaned by `slice-closure` or `task-close` (J.5).

## Maturity ladder hook

The 5-level maturity ladder (K.6 deliverable, shipped 2026-06-04; see wos/maturity-ladder.md) gates section ownership escalation for CUSTOM personas:

| Level | Persona writes | Audit reader |
|---|---|---|
| L1 (shadow) | none (PROPOSED only) | none |
| L2 (advisory) | PROPOSED + auto-comment under `## Observations` | log written, not validated |
| L3 (gated) | section ownership for ONE low-risk section | drift-guard validates |
| L4 (peer) | full section ownership equivalence with commands | full validation + alerts |
| L5 (autonomous) | may dispatch fleet workers under own merger | reserved (not in v2.1) |

CUSTOM personas launched in K.8 start at L1. Promotion requires eval evidence from K.7.

## Compatibility with existing commands

- Every command file in `commands/*.md` is already an implicit owner of one or more sections (e.g. `sync-task-state` writes `## Current phase`, `## Last completed step`). ADR-0034 makes this explicit via the matrix above.
- Zero command file changes required at ADR-0034 landing. The matrix was normative then; since ADR-0232 it describes the routing and a write outside it is recorded, not refused.
- K.1 retrofit (2026-06-04) extended the matrix to cover the seven fleet-substrate files that existed then (ATOM_AUDIT.md, SCREEN_MAP.md, routes.md, INITIATIVE_INDEX.md, EXTERNAL_RESEARCH.md, VERIFICATION_LOG.md, REFERENCES.md) once Epic J pilots J.6-J.10 had shipped real orchestrators that needed owner-declared rows. No command file changes were required to land the retrofit; the new rows are normative documentation of how the J.6-J.10 commands already declare their substrate ownership in-file.
- K.2 (cutover 2026-06-04) retrofitted transaction-header emission in the 8 most-frequent writers: `sync-task-state`, `slice-closure`, `decision-interview`, `implementation-plan`, `task-init`, `impact-analysis`, `what-next`, `capture-observation`.
- Other commands gain header emission incrementally when next touched.

## Drift-guard hook (ADR-0029 registry pattern)

Shipped K.4 + K.5 + K.7 (2026-06-04 / 2026-06-05): `repo-consistency-sweep` runs a mandatory **Pre-flight: substrate audit** (executed FIRST, before any diff or bug-class loading; not the reference-only Step 7) that invokes three scripts in order: `scripts/scan-substrate-headers.sh` (header drift), `scripts/scan-substrate-orphans.py` (bullet orphan, K.7), and `scripts/verify-log-validator.py` on `.wos/VERIFICATION_LOG.jsonl` (log invalid, K.5). The three counts surface in the SWEEP snapshot as `substrate_header_drift_count` + `substrate_bullet_orphan_count` + `verification_log_invalid_count`. INFORMATIONAL ONLY in v2.1 (WARN semantics, not a hard block; not added to bug-class findings; does not affect routing). Counts trend toward zero as writers adopt K.2 emission; promotion to enforcing block is a post-v2.1 decision pending eval evidence.

Complementary read-only check (ADR-0053): `state-reconcile` also exposes a `memory-lint` mode (backed by `scripts/memory-lint.sh`) that reports dead relative cross-links, orphaned `SLICES/` files, and stale `TASK_STATE.md` facts and writes nothing. It detects substrate drift but never repairs it. `state-reconcile` itself stays the sole rescuer for the conflict cases above. The deterministic checks live in the script. The stale-fact judgment lives in the command.

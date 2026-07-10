---
name: repo-consistency-sweep
description: Proactive defect-class detection that handles the lower-value half of code review (per Bacchelli and Bird 2013) so human reviewers stay focused on design, intent, and knowledge transfer. Catches convention drift, ordering bugs, type-safety gaps, security and multi-tenant invariants (CWE-grounded), and operability issues against a curated bug-class library before PR packaging. Runs after review-hard, before pr-package. Reduces what external review systems (Greptile, CI) catch and grows its detection library from declined and applied user feedback over time. Use when at least one slice is implemented and you want a proactive codebase-consistency check before PR packaging. Do not use when no implementation has happened yet, the task is still in planning, or the goal is design review (use review-hard for that).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 5300
  suggested-model: claude-sonnet-4-6
---
# repo-consistency-sweep

Act as a meticulous senior engineer performing a proactive codebase-consistency sweep on the current task diff.

Goal:
Detect convention drift, ordering bugs, type-safety gaps, and other patterned defect classes on the current diff against a curated bug-class library. Produce a triageable list of findings with severity, confidence, and suggested fix. Return no-op when the sweep would not surface new findings.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md (to know the current slice and diff context)
- SOURCE_OF_TRUTH.md (to know the base branch for diff computation)
- DECISIONS.md (to ground analysis in approved decisions)
- IMPLEMENTATION_PLAN.md (to know which slice is current and what files are in scope)
- optional: REVIEW_PREFERENCES.md (if present, used for suppression of previously declined findings)
- optional: `active/<task>/.wos/VERIFICATION_LOG.jsonl` (if present, validated by `scripts/verify-log-validator.py` per K.5 wiring; missing log is VALID for legacy tasks predating K.1)
- optional: `scripts/verify-log-validator.py` (invoked for the K.5 audit; informational when missing)
- optional: `scripts/scan-substrate-orphans.py` (invoked for the K.7 substrate-orphan audit; informational when missing)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact, Mode B full, or Mode C parallel-fanout when triggered).
- **Mode C eligibility (parallel fanout, per ADR-0032):** when the diff touches >10 files OR the task is multi-repo with `## Repositories` listed in `SOURCE_OF_TRUTH.md`, emit a `Delegate now:` directive in the handoff dispatching one sub-agent per logical file group (per-repo for multi-repo, or per bug-class group when single-repo with wide diff). Each sub-agent runs its slice of the sweep and returns a structured findings list. The parent merges, dedupes, and emits the normal Mode A handoff with the integrated findings. Skip Mode C when diff is small (<10 files) and single-repo.
- **Pre-flight: substrate audit (K.4 + K.5 + K.7).** ALWAYS execute FIRST, before Step 1, before any diff computation, before any hash check, before any bug-class loading. There is no condition under which this step is skipped (except graceful-skip when the named scripts are missing -- in which case report `n/a`, not `0`). Concrete invocation (run in this order; header drift first so renamed parents do not mask orphan detection):
  ```bash
  bash    scripts/scan-substrate-headers.sh <active-task-folder>
  python3 scripts/scan-substrate-orphans.py <active-task-folder>
  python3 scripts/verify-log-validator.py   <active-task-folder>/.wos/VERIFICATION_LOG.jsonl
  ```
  Capture three integers from stdout: `substrate_header_drift_count: <N>` (first script), `substrate_bullet_orphan_count: <N>` (second), and `invalid: <N>` (third, recorded as `verification_log_invalid_count`). Persist the orphan paths list (first 10) for the snapshot; write the full list to `REVIEW_SWEEPS/SWEEP_<ts>.orphans.txt` for diffability. These three integers are the audit deliverables for THIS run.
  - **WARN semantics for orphans (not FAIL).** `substrate_bullet_orphan_count > 0` surfaces a WARN line in sweep output, mirroring `header_drift` per ADR-0029's drift-guard pattern. It does NOT add a bug-class finding and does NOT affect Step 11 routing. The gate lives in `evals/e2e/assertions/09-repo-consistency-sweep.sh` (orphan-cap block, default `EXPECTED_MAX_SUBSTRATE_ORPHANS=0`).
  - **Legacy-orphan tolerance.** Honour `OPT_OUT_ORPHAN_BASELINE=1`: when set, still emit the counter and snapshot fields but suppress the WARN escalation. The detector stays pure; tolerance is a sweep-layer policy (ADR-0029 detection-vs-gating separation). Repos with known legacy debt use this to keep the signal visible without blocking unrelated work.
  - **FORBIDDEN: carrying counts forward from a prior SWEEP snapshot without re-invoking the scripts.** The "informational" qualifier elsewhere refers ONLY to routing impact (Step 11 does NOT route on these counts); it does NOT make the scripts optional. Substrate state (header drift, bullet orphans, log validity) changes outside the code-repo diff, so the prior snapshot's counts are stale the moment any substrate writer fires anywhere in the Fhorja task repo. Invoking all three scripts on every sweep run is the only way to know the current state.
  - Save the three captured integers as `substrate_header_drift_count`, `substrate_bullet_orphan_count`, and `verification_log_invalid_count` (plus the companion `substrate_bullet_orphan_paths` list) for Step 9 (snapshot fields) and Step 10 (TASK_STATE pointer when non-zero). Step 7 below is the reference spec for what the scripts measure, not an execution step.
- **Step 1: Compute diff.** Run `git diff <base-branch>...HEAD` where `<base-branch>` comes from `SOURCE_OF_TRUTH.md`. If no diff exists, set `bug_class_run = false` (skip Steps 3-6 + the bug-class portion of Step 9). Pre-flight already ran; substrate counts already captured.
- **Step 2: Hash check (gates bug-class only).** Compute sha256 of the diff output. If a previous SWEEP snapshot exists in `REVIEW_SWEEPS/` with the same diff hash, set `bug_class_run = false` (skip Steps 3-6 + new-snapshot creation in Step 9). Pre-flight already ran; do NOT carry forward substrate counts from the matched snapshot. Step 9 EDIT-amends the existing snapshot with the freshly-captured substrate-audit fields.
- **Step 3: Load bug-class library.** Scan `wos/bug-classes/*.md` (skip `_index.md`, `_shared/`). For each class file, read its YAML frontmatter. If `projects/<client>__<project>/bug-classes/` exists, load those too; on name collision, project-local replaces global (log a one-line warning).
- **Step 4: Filter classes.** For each class, match its `file-patterns` against the list of changed files in the diff. Discard classes with no matching files.
- **Step 5: Run analysis.** For each matching class, dispatch an Explore subagent (or inline if the retrieval scope is small) with the class's `## Analysis prompt` applied to the slices in `## Retrieval`. If the class has `perspectives:` in frontmatter, apply the relevant fragments from `wos/bug-classes/_shared/perspectives.md`. If `reversibility-check: true`, append the reversibility prompt from `wos/bug-classes/_shared/reversibility-check.md`.
- **Step 6: Aggregate findings.** Collect all findings. Each finding must include: bug-class name, file path and line range, severity (P0/P1/P2 per the class's rubric), confidence (HIGH/MEDIUM/LOW per the class's factors), an effort band (S/M/L for the fix), 1-sentence summary, suggested fix (if concrete). Order the findings by severity relative to effort, with severity as the primary key, so the highest value per unit of fix effort surfaces first; effort is a tiebreak, never a reason to drop a P0.
- **Step 7: Substrate audit (REFERENCE only; executed in Pre-flight).** Spec for what the three scripts measure, so the snapshot fields and TASK_STATE pointer are labeled correctly. Per `wos/substrate-peers.md ## Drift-guard hook` + ADR-0034 + ADR-0029 (orphan-cap). Cutover 2026-06-04 (K.2); orphan-scan added 2026-06-05 (K.7).
  1. **K.4 header drift** (`scripts/scan-substrate-headers.sh`). Enumerates substrate at CANONICAL locations: the 4 task-memory files (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`), task-scoped fleet-substrate (`EXTERNAL_RESEARCH.md`, `VERIFICATION_LOG.md`), and project-scoped fleet-substrate (`INITIATIVE_INDEX.md`, `REFERENCES.md` in the project parent). Cutover gate per file: git-tracked use `git log --since=<cutoff>`; gitignored (typical per ADR-0007) fall back to `mtime`. Counts H2 (`## `) sections whose immediately-preceding line is NOT a canonical `<!-- wos:write ... -->` header per `commands/_shared/substrate-write-protocol.md ## Concrete computation` -> `substrate_header_drift_count`. Product-repo fleet-substrate (`ATOM_AUDIT.md`, `SCREEN_MAP.md`, `routes.md`) is included automatically when `SOURCE_OF_TRUTH.md` declares `## Active codebase / repo` or `## Repositories`; both layouts roll into the same total.
  2. **K.7 substrate-bullet orphans** (`scripts/scan-substrate-orphans.py`). Walks the same in-scope files and detects bullets referencing paths, sections, or IDs that no longer resolve (dangling decision IDs, removed sections, renamed paths) -> `substrate_bullet_orphan_count` plus paths list. Runs AFTER header drift so renamed parents do not mask child orphans.
  3. **K.5 audit log validation** (`scripts/verify-log-validator.py` on `.wos/VERIFICATION_LOG.jsonl`). Enforces the 12-field schema per `wos/substrate-peers.md ## Audit trail` (required fields, owner_type enum, 19-event taxonomy, ISO 8601 ms timestamps, SHA-256 hex for non-null sha fields, fleet-event rules) -> `verification_log_invalid_count`.
  - Known v2.1 limitation: the K.4 mtime fallback over-counts on files mixing pre- and post-cutover sections (a pre-2026-06-04 section never re-edited still flags if the file was touched post-cutover). The count signals authoring discipline, not a perfect tally.
- **Step 8: Suppress declined.** Read `REVIEW_PREFERENCES.md` (at `projects/<client>__<project>/REVIEW_PREFERENCES.md`) if present. For each finding, check the `## Declined findings` table for a row where `bug_class` and `file_path` match. If a match exists, compute the current file hash via `git hash-object <file_path>` and compare with the stored `file_hash`. If hashes match (file unchanged since decline), suppress the finding. If hashes differ (file was modified), the decline is stale: report the finding normally. When no REVIEW_PREFERENCES.md exists, skip suppression (the file is created on the first `apply-sweep-triage` run).
- **Step 8b: Reconcile against the prior snapshot on a changed diff (finding-level reconciliation).** When a prior SWEEP snapshot exists at a DIFFERENT diff hash (the diff changed since last sweep), reconcile this run's findings against it before writing: mark a prior finding whose `file:line` no longer matches as retired (fixed or moved), re-ground a finding whose location shifted to the new `file:line`, and flag net-new findings, so the snapshot shows the delta rather than re-emitting every finding cold. Reuse the Step 8 REVIEW_PREFERENCES.md declined-suppression for declined items; do not duplicate that mechanism. When no prior snapshot exists, skip reconciliation (this is the first sweep).
- **Step 9: Write or update SWEEP snapshot.** Two paths:
  - **If `bug_class_run` is true:** create a new `REVIEW_SWEEPS/SWEEP_<YYYYMMDD-HHMM>.md` with: diff hash, timestamp, finding count, per-finding blocks PLUS three substrate-audit metadata lines from Step 7 (`substrate_header_drift_count: <N>`, `substrate_bullet_orphan_count: <N>` with companion `substrate_bullet_orphan_paths: <comma-separated, max 10>`, and `verification_log_invalid_count: <N>`; all default to `0` or `n/a` when sub-checks were skipped). Also write the full orphan paths list to `REVIEW_SWEEPS/SWEEP_<YYYYMMDD-HHMM>.orphans.txt` for diffability. Each finding block must include: bug-class name, file path, line range, severity, confidence, summary, suggested fix, and `triage: unset` (placeholder for the user to edit). Optionally include `reason:` and `note:` lines (empty by default) that the user fills in before running `apply-sweep-triage`.
  - **If `bug_class_run` is false:** the bug-class findings are unchanged from the prior snapshot at this diff hash; do NOT create a new snapshot file. Instead, locate the prior snapshot at the matching hash and EDIT-amend its `substrate_header_drift_count`, `substrate_bullet_orphan_count` (plus `substrate_bullet_orphan_paths`), and `verification_log_invalid_count` fields with the fresh values from Step 7 (substrate counts can change between sweeps even when the code diff did not). Refresh the companion `.orphans.txt` next to the matched snapshot. Log the amendment timestamp.
- **Step 10: Update TASK_STATE (dogfood K.2).** Add a 1-line pointer under `## Risks to watch` or a dedicated `## Latest sweep` section. If `substrate_header_drift_count > 0` OR `substrate_bullet_orphan_count > 0` OR `verification_log_invalid_count > 0`, mention the count(s) explicitly in the pointer (informational; not a blocker). MANDATORY K.2 protocol for this write (per `commands/_shared/substrate-write-protocol.md` `## Concrete computation`):
  1. Compute `sha_before` via the canonical bash helper (or `null` if the section did not exist prior to this write).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading (between any prior content and the `## ` line):
     `<!-- wos:write owner=repo-consistency-sweep section='## Latest sweep' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=sweep-<N>-findings mode=applied -->`
  3. Write or update the section content.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_before` is null ONLY on a brand-new section; otherwise it MUST be valid SHA-256 hex (64 lowercase hex chars). `sha_after` MUST be valid SHA-256 hex. NEVER emit `sha_after: null`.
  6. If you wrote multiple sections in this run (e.g. `## Risks to watch` AND `## Latest sweep`), repeat steps 1-5 for EACH section: one header per section, one JSONL line per section.

  The half-compliant pattern (JSONL line emitted but inline header omitted, or SHA fields set to `null` when the section already existed) is FORBIDDEN. K.4 drift-guard at Step 7 of the NEXT sweep run will surface this command's own writes if it skips its protocol.
- **Step 11: Route handoff.** If 0 findings or all suppressed: route to `pr-package`. If any P0 finding: route to `implement-slice-complement`. Otherwise: route to `pr-package` and list unsuppressed findings as reviewer attention points. Substrate-audit counts (including orphan count) do NOT affect routing.
- No-op rule for artifacts: if TASK_STATE.md would not materially change, do not rewrite it. Still output a minimal `NO_OP_TRACE` for traceability.
- Do not implement fixes. This command analyzes and reports only.
- Do not invent findings. If the diff is clean against all matching classes, say so clearly.
- Do not generate cosmetic or stylistic feedback. Focus on defect-class patterns only.

Required output:
1. Diff summary (files changed, lines added/removed)
2. Classes matched (list of bug-class names that had file-pattern hits)
3. Findings (grouped by severity: P0, P1, P2; each with class, file, line, confidence, summary, suggested fix)
4. Suppressed findings count (from REVIEW_PREFERENCES.md)
5. Substrate audit summary (K.4 + K.5 + K.7; informational): `substrate_header_drift_count` + `verification_log_invalid_count` + `substrate_bullet_orphan_count` (or `n/a` when skipped)
6. Substrate-orphan detection results: `substrate_bullet_orphan_count` plus `substrate_bullet_orphan_paths` (first 10 paths inline; full list at the companion `REVIEW_SWEEPS/SWEEP_<ts>.orphans.txt`). Include the WARN line when count > 0 unless `OPT_OUT_ORPHAN_BASELINE=1` is set.
7. SWEEP snapshot path
8. TASK_STATE.md update (or `TASK_STATE: NO_CHANGE`)
9. Recommended next command
10. Recommended editor mode

### Review prompt scaffold (optional)
<!-- shared:xml-review-scaffold -->
When the review directives in this command are ambiguous, parse them in three labeled parts: Instructions (what to do), Context (background, not a rule), and Constraints (hard limits that override the rest). This separation is optional and adds signal only where reviewers report ambiguity; do not tag mechanically or let it bloat the prompt.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Diff was computed and hashed; no-op returned if unchanged.
- All matching bug-class templates were loaded and applied.
- Findings are grouped by severity with concrete file:line references.
- SWEEP snapshot was written with `triage: unset` placeholders per finding PLUS the three K.4 + K.5 + K.7 substrate audit lines (`substrate_header_drift_count`, `substrate_bullet_orphan_count` with companion `substrate_bullet_orphan_paths`, and `verification_log_invalid_count`; all `n/a` when skipped). Companion `REVIEW_SWEEPS/SWEEP_<ts>.orphans.txt` written/refreshed with the full orphan paths list.
- Substrate audit (Step 7) ran the K.4 header-drift scan over substrate files touched by the diff AND invoked `scripts/scan-substrate-orphans.py` for the K.7 orphan scan AND invoked `scripts/verify-log-validator.py` on `.wos/VERIFICATION_LOG.jsonl` when both exist; counts surfaced without adding bug-class findings or affecting routing (informational per ADR-0034 v2.1 + ADR-0029 orphan-cap).
- TASK_STATE.md updated with 1-line sweep pointer including substrate-audit counts when non-zero (or `NO_CHANGE` if nothing changed).
- Handoff routes correctly based on finding profile (substrate-audit counts, including the orphan count, do NOT affect routing).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Maximize signal. Prioritize real defect-class findings over cosmetic commentary. If the diff is clean, say so clearly.

<!-- cache-breakpoint -->

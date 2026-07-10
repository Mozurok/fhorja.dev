# Fhorja E2E walkthrough -- canonical command sequence

## Scenario

**Synthetic project:** `wos__e2e-test` (client = `wos`, project = `e2e-test`).

**Synthetic product repo:** `/tmp/wos-e2e-fake-app/` (a tiny Flask signup endpoint with intentional issues; bootstrap copies it from `evals/e2e/fake-app/`).

**Synthetic task:** Add email-format validation to the `/signup` endpoint. Today the endpoint accepts `""` as a valid email; the fix is to reject empty + invalid formats with HTTP 400 + a structured error body.

The scenario is intentionally small so the walkthrough completes in under 30 minutes of focused execution. The goal is to exercise Fhorja, not to ship a real feature. K.2 transaction-header protocol (cutover 2026-06-04) MUST fire on every substrate write; the Step 09 `repo-consistency-sweep` Pre-flight + `verify-log-validator.py` + `scan-substrate-headers.sh` validate that every prior step honored the protocol.

## Pre-flight

```bash
# Run once before starting the walkthrough
cd ~/Documents/my_work_tasks
bash evals/e2e/bootstrap.sh
```

Bootstrap creates:
- `projects/wos__e2e-test/` (gitignored per ADR-0007; project-bootstrap then creates active/ + archive/ in Step 01)
- `/tmp/wos-e2e-fake-app/` (a fresh copy of `evals/e2e/fake-app/`, initialized as a git repo with a baseline commit)

## Canonical command sequence

For each step: command name + mode + inputs + expected artifacts + expected substrate writes (with K.2 inline header verification) + expected handoff target. Run the matching assertion script after each numbered step.

Phase 1 ships assertion scripts only for Steps 01 + 09 (the two highest-value validations). Assertion scripts for the remaining steps are Phase 2 deliverables shipped alongside the K.2 writer fixes.

### Step 01 -- `project-bootstrap`

- **Mode:** Agent
- **Inputs:** `client = wos`, `project = e2e-test`, objective = "synthetic project for the Fhorja E2E regression walkthrough", stack = "Python 3.11 + Flask" (single repo), product repo path = `/tmp/wos-e2e-fake-app/`, no constraints, no non-goals
- **Expected artifacts written:**
  - `projects/wos__e2e-test/PROJECT_CHARTER.md` (with `## Objective`, `## Stack`, `## Default workspace` -- NOT `## Repositories` since single-repo, `## Constraints`, `## Non-goals`, `## References` cross-link)
  - `projects/wos__e2e-test/REFERENCES.md` (skeleton with format reminder + empty `## Entries`)
  - `projects/wos__e2e-test/active/` (created by project-bootstrap, not pre-created by bootstrap.sh)
  - `projects/wos__e2e-test/archive/` (created by project-bootstrap)
- **Expected substrate writes:** none in the substrate-peers ownership matrix (PROJECT_CHARTER.md and REFERENCES.md are project-level memory, not substrate); K.2 protocol does NOT apply to this step
- **Expected handoff `Run now`:** `task-init`
- **Assertion (shipped):** `bash evals/e2e/assertions/01-project-bootstrap.sh`

### Step 02 -- `capture-references`

- **Mode:** Agent
- **Inputs:** project path, URL = `https://flask.palletsprojects.com/en/3.0.x/quickstart/`, topic tag = `stack`, context-within-project = "Reference for request handling + JSON responses in the /signup endpoint"
- **Expected artifacts:**
  - `projects/wos__e2e-test/REFERENCES.md` -- append one entry under `## stack` (the topic tag becomes an H2 section per `capture-references` format) with title, URL, accessed-on date, summary, key points, context-within-project (per ADR-0018)
- **Expected substrate writes:** REFERENCES.md is PROJECT-level memory. The K.2 canonical protocol (per `commands/_shared/substrate-write-protocol.md`) targets task-scoped `active/<task>/.wos/VERIFICATION_LOG.jsonl`. **Project-level K.2 emission is UNDEFINED in v2.1** (known deferral; no task folder exists yet at this step). Step 02 does NOT emit a K.2 header or JSONL line.
- **Expected handoff `Run now`:** `task-init`
- **Assertion (Phase 2):** `evals/e2e/assertions/02-capture-references.sh`

### Step 03 -- `task-init`

- **Mode:** Ask (drafting) OR Agent (Agent persists the 5 files immediately; choose Agent for the walkthrough to land the substrate writes)
- **Inputs:** project = `wos__e2e-test`, slug = `email-validation`, objective = "Add email-format validation to /signup: reject empty + malformed emails with HTTP 400 + structured error body", product repo path = `/tmp/wos-e2e-fake-app/`, intended editor mode = `Agent`
- **Expected artifacts (under `projects/wos__e2e-test/active/<YYYY-MM-DD>_email-validation/`):**
  - `README.md` (task name, project name, summary, objective, status)
  - `TASK_STATE.md` (17 canonical sections + `## Recommended pipeline` per ADR-0025; complexity tier = Express or Standard given the scope)
  - `SOURCE_OF_TRUTH.md` (with `## Active codebase` = `/tmp/wos-e2e-fake-app/`, `## Active branch` = `main`; NO `## Repositories` since single-repo)
  - `DECISIONS.md` (empty `## Locked decisions` stub, no D-N entries yet)
  - `IMPLEMENTATION_PLAN.md` (with `## Target behavior`, `## Current gaps`, `## Constraints`, `## Slices` empty stubs)
- **Expected substrate writes (per `wos/substrate-peers.md` ownership matrix):** task-init is the canonical INITIAL writer for all sections it lays down across the 4 task-memory files. Every H2 section MUST carry an inline `<!-- wos:write owner=task-init section='## X' run_id=<ULID> ts=<ISO-ms> reason=<<=80chars> mode=applied -->` header above the section heading, AND each section write appends one line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` with valid SHA-256 hex per `commands/_shared/substrate-write-protocol.md ## Concrete computation`.
- **Expected handoff `Run now`:** `impact-analysis`
- **Assertion (Phase 2):** `evals/e2e/assertions/03-task-init.sh`

### Step 04 -- `impact-analysis`

- **Mode:** Ask (PROPOSED-by-default), then `approve-proposed` if accepted
- **Inputs:** task folder path
- **Expected artifacts:**
  - `IMPACT_ANALYSIS.md` with the canonical 12-item structure (per `commands/impact-analysis.md` line 73): (1) Request understanding, (2) Confirmed facts, (3) Assumptions / unresolved interpretations, (4) Affected areas, (5) Risks and failure modes, (6) Viable implementation directions, (7) Recommended path, (8) Open questions, (9) Suggested next step, (10) Recommended next command, (11) Recommended editor mode, (12) Why that is the correct next step. Single-repo task so NO per-repo `### Repo:` subsections.
  - PROPOSED block under `TASK_STATE.md ## Active files in scope` (impact-analysis OWNS this section per the matrix; PROPOSED label per ADR-0001 in Ask mode -- `approve-proposed` promotes to APPLIED on the owner write)
  - PROPOSED block under `TASK_STATE.md ## Risks to watch` (impact-analysis is P-only CO-WRITER; OWNER is sync-task-state; only the co-writer block lands here)
- **Expected substrate writes (after `approve-proposed` promotes them):**
  - `TASK_STATE.md ## Active files in scope` write by impact-analysis (OWNER); K.2 header + JSONL line
  - `TASK_STATE.md ## Risks to watch` PROPOSED block by impact-analysis (CO-WRITER); when later promoted by sync-task-state, K.2 header carries `owner=sync-task-state` not impact-analysis (substrate-peers ownership rule)
- **Expected handoff `Run now`:** `decision-interview` (1 decision likely: error-body shape)
- **Assertion (Phase 2):** `evals/e2e/assertions/04-impact-analysis.sh`

### Step 05 -- `decision-interview`

- **Mode:** Ask
- **Inputs:** task folder; question framed by impact-analysis output: "Error-body shape for 400 responses: plain string vs structured JSON object `{error, code}`?"
- **Expected artifacts:**
  - `DECISIONS.md ## Locked decisions` -- append `### D-1` with EARS-form rule (per ADR-0031): "WHEN the `/signup` endpoint receives an invalid email, the server SHALL return HTTP 400 with body `{error: <human-readable string>, code: <machine-readable enum>}`"
- **Expected substrate writes:**
  - `DECISIONS.md ## Locked decisions` write by decision-interview (OWNER); K.2 header + JSONL line
- **Expected handoff `Run now`:** `implementation-plan`
- **Assertion (Phase 2):** `evals/e2e/assertions/05-decision-interview.sh`

### Step 06 -- `implementation-plan`

- **Mode:** Plan (per command frontmatter `primary-cursor-mode: Plan`), then `approve-proposed`
- **Inputs:** task folder
- **Expected artifacts:**
  - `IMPLEMENTATION_PLAN.md ## Slices` -- 2 slices, each with the canonical 7 per-slice fields (per `commands/implementation-plan.md` line 60-67): (a) objective, (b) exact scope (files + boundaries), (c) why-this-order-is-safe (ordering rationale), (d) key risks, (e) validation approach, (f) exit criteria using EARS template (`WHEN ... SHALL ...`; banned softeners: should/may/appropriate/sensible/reasonable), (g) work complexity = `LOW | MEDIUM | HIGH` plus one-line rationale (no model SKU names).
    - Slice 1: "Reject empty email with 400" -- work complexity `LOW`
    - Slice 2: "Reject malformed email format with 400" -- work complexity `LOW`
- **Expected substrate writes:**
  - `IMPLEMENTATION_PLAN.md ## Slices` write by implementation-plan (OWNER); K.2 header + JSONL line
- **Expected handoff `Run now`:** `implement-approved-slice` (with Slice 1 selected)
- **Assertion (Phase 2):** `evals/e2e/assertions/06-implementation-plan.sh`

### Step 07 -- `implement-approved-slice` (Slice 1)

- **Mode:** Agent (per command frontmatter `primary-cursor-mode: Agent`)
- **Inputs:** task folder, slice = `Slice 1` ("reject empty email"; complexity = LOW)
- **Expected artifacts:**
  - `/tmp/wos-e2e-fake-app/handlers/signup.py` -- modified to reject empty email (after Task 3 restructure; pre-restructure path was `/tmp/wos-e2e-fake-app/app.py`)
  - `projects/wos__e2e-test/active/<task>/SLICES/01_reject-empty-email.md` -- slice notes: implemented changes, evidence, exit-criteria verification checklist
  - APPLIED-by-default in Agent mode per ADR-0026 (slice file + TASK_STATE updates default to APPLIED)
- **Expected substrate writes:**
  - `TASK_STATE.md ## Last completed step` -- CO-WRITER mutation by implement-approved-slice (OWNER is sync-task-state per matrix); K.2 header + JSONL line carry `owner=sync-task-state` if promoted via approve-proposed, OR `owner=implement-approved-slice` if applied directly per its substrate access (verify against current substrate-peers matrix)
  - `IMPLEMENTATION_PLAN.md ### Slice 1` Status mutation only (`not-started` -> `implemented (pending closure)`) -- co-writer mutation per matrix; STATUS lines only
- **Expected handoff `Run now`:** `implement-approved-slice` (with Slice 2 selected). Per ADR-0026 inline-closure rule (per `commands/implement-approved-slice.md` line 75): LOW + MEDIUM slices with all exit criteria passing close INLINE; do NOT route to `slice-closure`. The handoff jumps directly to the next slice's implement-approved-slice run.
- **Assertion (Phase 2):** `evals/e2e/assertions/07-implement-slice-1.sh`

### Step 7.5 -- `capture-observation` (covers the K.2 capture-observation writer)

- **Mode:** Ask (PROPOSED) or Agent
- **Inputs:** task folder, observation text = "Slice 2 should reuse the empty-email guard pattern from Slice 1 to keep error shapes uniform" + tag = `hypothesis`
- **Expected artifacts:**
  - `TASK_STATE.md ## Observations` -- append one dated bullet `- [YYYY-MM-DD] [hypothesis] Slice 2 should reuse...`
- **Expected substrate writes:**
  - `TASK_STATE.md ## Observations` write by capture-observation (OWNER per matrix; append-only freeform); K.2 header + JSONL line
- **Expected handoff `Run now`:** `implement-approved-slice` (resume Slice 2)
- **Assertion (Phase 2):** `evals/e2e/assertions/7.5-capture-observation.sh`

### Step 07b -- `implement-approved-slice` (Slice 2)

- **Mode:** Agent
- **Inputs:** task folder, slice = `Slice 2` ("reject malformed email format"; complexity = LOW)
- **Expected artifacts:**
  - `/tmp/wos-e2e-fake-app/handlers/signup.py` -- further modified to reject malformed emails (using Python stdlib `re` per requirements.txt comment; no new dep)
  - `projects/wos__e2e-test/active/<task>/SLICES/02_reject-malformed-email.md` -- slice notes
- **Expected substrate writes:** same shape as Step 07
- **Expected handoff `Run now`:** `repo-consistency-sweep` (both slices closed inline; ready for proactive defect-class detection per the LOW path)
- **Assertion (Phase 2):** `evals/e2e/assertions/07b-implement-slice-2.sh`

### Step 8.5 -- `sync-task-state` (covers the K.2 sync-task-state writer)

- **Mode:** Agent
- **Inputs:** task folder; trigger = "both slices closed inline; refresh state before sweep"
- **Expected artifacts:**
  - `TASK_STATE.md ## Current phase`, `## Current status` (### Completed / ### In progress / ### Not started), `## Last completed step`, `## Canonical decisions`, `## Risks to watch` -- all owned by sync-task-state; reflects Slices 1+2 both closed inline
- **Expected substrate writes:**
  - Multiple sections written by sync-task-state (OWNER for each); each gets a K.2 header + JSONL line per `substrate-write-protocol.md ## Concrete computation` (reuse the same `run_id` + `ts` across all section writes in this single run)
- **Expected handoff `Run now`:** `repo-consistency-sweep`
- **Assertion (Phase 2):** `evals/e2e/assertions/8.5-sync-task-state.sh`

### Step 08 (skipped) -- `slice-closure`

- **Why skipped:** per `commands/slice-closure.md` line 20, slice-closure is OPT-IN for LOW and MEDIUM complexity slices. Both slices in this walkthrough are LOW, so they close inline at Step 07 + 07b per ADR-0026. slice-closure is exercised by a separate HIGH-complexity walkthrough variant (Phase 4 deliverable; out of scope here).

### Step 09 -- `repo-consistency-sweep`

- **Mode:** Ask
- **Inputs:** task folder
- **Expected behavior:**
  - **Pre-flight runs UNCONDITIONALLY before Step 1** (per current sweep spec): `bash scripts/scan-substrate-headers.sh <task-folder>` AND `python3 scripts/verify-log-validator.py <task-folder>/.wos/VERIFICATION_LOG.jsonl`. If Steps 01-08.5 honored K.2, drift = 0 and invalid = 0.
  - Steps 1-2 (sweep): diff vs base = uncommitted changes in `/tmp/wos-e2e-fake-app/` (Slices 1+2 modifications in `handlers/signup.py`)
  - Steps 3-6: bug-class analysis on the diff. Expected findings: at least 1 P2 from `missing-test-for-change` bug class (handlers/ path matches its file-patterns glob; no tests added) + at least 1 P3 from `documentation-drift` (fake-app/README.md still claims empty email returns 201)
  - Step 9: write SWEEP snapshot under `REVIEW_SWEEPS/SWEEP_<YYYYMMDD-HHMM>.md` with bug-class findings + the two captured substrate-audit counts
  - Step 10: dogfood K.2 -- write `TASK_STATE.md ## Latest sweep` with inline header + valid SHA-256 hex JSONL line (per the sweep's Step 10 mandatory 6-step protocol)
- **Expected substrate writes:**
  - `TASK_STATE.md ## Latest sweep` by repo-consistency-sweep (CO-WRITER per matrix; `## Latest sweep` is sole-owned by repo-consistency-sweep); K.2 header + JSONL line with non-null SHAs
- **Expected handoff `Run now`:** `pr-package` (per Step 11 of sweep: no P0 findings means default route to pr-package; P2/P3 findings surface as reviewer attention points but do not change routing). NOTE: the user may optionally run `apply-sweep-triage` OUT-OF-BAND between sweep and pr-package to record triage decisions; this is NOT a sweep handoff target.
- **Assertion (shipped):** `bash evals/e2e/assertions/09-repo-consistency-sweep.sh`

### Step 10 -- `apply-sweep-triage` (optional, user-driven)

- **Mode:** Agent (per command frontmatter `primary-cursor-mode: Agent`)
- **Inputs:** task folder, sweep snapshot path (from Step 09), user's triage decisions (e.g. decline the P3 documentation-drift, accept the P2 missing-test)
- **Expected artifacts:**
  - `projects/wos__e2e-test/REVIEW_PREFERENCES.md` -- created with `## Declined findings` section + file_hash for each declined entry
  - `TASK_STATE.md ## Last completed step` update (set to this command + summary "N declined, M applied")
- **Forbidden:** modifying the SWEEP snapshot file (per `commands/apply-sweep-triage.md` line 54: "the SWEEP snapshot file itself is a read-only historical record")
- **Expected substrate writes:**
  - `TASK_STATE.md ## Last completed step` write -- apply-sweep-triage is NOT currently listed as a co-writer in the substrate-peers matrix for this section (OWNER is sync-task-state; co-writers are implement-approved-slice + slice-closure). This is a gap in the matrix that K.2 will surface; the walkthrough flags it as known v2.1 deferral.
- **Expected handoff `Run now`:** `pr-package` (resume the sweep's intended route) OR `implement-slice-complement` (if user accepts a P2 that requires a code fix). For walkthrough scenario with the P2 accepted, route to `implement-slice-complement` to add the test.
- **Assertion (Phase 2):** `evals/e2e/assertions/10-apply-sweep-triage.sh`

### Step 11 -- `pr-package`

- **Mode:** Ask (per command frontmatter `primary-cursor-mode: Ask`)
- **Inputs:** task folder, base branch = `main`, target = whole task (Slices 1+2 closed; P2 test added via Step 10 follow-up)
- **Expected artifacts:**
  - `projects/wos__e2e-test/active/<task>/PR_PACKAGE.md` -- branch name, commit messages, fetch/checkout/add/commit/push commands, PR title + body, reviewer attention points (grounded in the real diff per the command's quality bar)
  - `TASK_STATE.md ## Last completed step` updated (or `TASK_STATE: NO_CHANGE`)
- **Expected substrate writes:**
  - `TASK_STATE.md ## Last completed step` write (CO-WRITER per matrix); K.2 header + JSONL line
- **Expected handoff `Run now`:** `branch-commit` (or the user proceeds to actual PR creation via the commands embedded in PR_PACKAGE.md)
- **Assertion (Phase 2):** `evals/e2e/assertions/11-pr-package.sh`

### Step 12 -- `task-close`

- **Mode:** Agent
- **Inputs:** task folder
- **Expected artifacts:**
  - `TASK_STATE.md ## Current phase` set to `delivery/closed`
  - `TASK_STATE.md ## Current status` reflects completion; any waivers recorded
  - `TASK_STATE.md ## Recommended next step` set to none (task fully done)
  - Task folder moved from `active/` to `archive/` via `git mv` when tracked, `mv` otherwise
  - VERIFICATION_LOG.jsonl preserved in archived folder
- **Expected substrate writes:**
  - Final `TASK_STATE.md ## Current phase` + `## Current status` + `## Recommended next step` writes; task-close is not in the matrix as canonical owner for these sections but writes them per its terminal-lifecycle contract; K.2 headers + JSONL lines emit per the protocol with `owner=task-close`. The implicit co-writer status is a matrix gap (Phase 4 reconciliation).
- **Expected handoff `Run now`:** `delivery-asset` OR `pr-package` (if delivery framing pending) OR `task-init` (spun-off follow-up) OR none (task fully done; the walkthrough scenario resolves with "none")
- **Assertion (Phase 2):** `evals/e2e/assertions/12-task-close.sh`

### Step 12.5 -- `what-next` (covers the K.2 what-next writer)

- **Mode:** Ask
- **Inputs:** project folder (no active task remains after Step 12)
- **Expected artifacts:**
  - Recommendation output: since no active task remains, what-next surfaces project-level next moves (e.g. spin up a new task via `task-init`, or run `project-bootstrap` for a new project)
- **Expected substrate writes:**
  - When there IS an active task, what-next writes `TASK_STATE.md ## Recommended next step` (OWNER per matrix). In the walkthrough's post-task-close state, no active task -> no substrate write at this step (which itself is a graceful no-op exercise of the K.2 path)
- **Expected handoff `Run now`:** `task-init` (for follow-up) OR no-op
- **Assertion (Phase 2):** `evals/e2e/assertions/12.5-what-next.sh`

## Pass criteria

The walkthrough passes when:
- Assertion scripts 01 + 09 (Phase 1) return exit 0; assertion scripts 02-08.5 + 10-12.5 (Phase 2) return exit 0 once Phase 2 ships them
- `bash scripts/scan-substrate-headers.sh projects/wos__e2e-test/active/<task>/` reports `substrate_header_drift_count: 0`
- `python3 scripts/verify-log-validator.py projects/wos__e2e-test/active/<task>/.wos/VERIFICATION_LOG.jsonl` reports `invalid: 0`
- Every step's `### Handoff Run now:` line resolves to a real `commands/<name>.md` or `commands/<name>/SKILL.md` file
- Final `bash scripts/lint-commands.sh` returns clean

## Failure modes the walkthrough is designed to catch

1. **K.2 non-compliance** -- writer emits substrate without inline `<!-- wos:write -->` header (caught by Pre-flight drift count > 0)
2. **K.2 half-compliance** -- writer emits inline header but null SHAs in JSONL (caught by Pre-flight validator invalid count > 0)
3. **Substrate ownership violation** -- non-owner writes a section without P access (caught by drift-guard registry check in lint + manual matrix re-check in Step 09 assertion)
4. **Stale handoff** -- recommended next command does not exist (caught by lint + assertion script greps)
5. **Section drift** -- a command renames or removes a canonical section without updating the substrate-peers matrix (caught by required-sections lint)
6. **Per-K.2-writer regression** -- the 8 writers from the K.2 retrofit (sync-task-state, slice-closure, decision-interview, implementation-plan, task-init, impact-analysis, what-next, capture-observation) are EACH exercised in at least one step: 03 task-init, 04 impact-analysis, 05 decision-interview, 06 implementation-plan, 7.5 capture-observation, 8.5 sync-task-state, 09 repo-consistency-sweep (dogfood), 12.5 what-next. Step 08 slice-closure is skipped per ADR-0026 LOW-inline-close, exercised separately in the HIGH-complexity variant (Phase 4 deferred).

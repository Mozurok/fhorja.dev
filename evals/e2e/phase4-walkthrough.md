# Phase 4 walkthrough (HIGH complexity)

## Goal

Phase 4 extends the Phase 3 LOW-complexity Flask fixture into a HIGH-complexity multi-persona end-to-end run that stresses the full Fhorja substrate contract under realistic concurrency. Where Phase 3 exercised a single-owner, single-slice happy path (one persona, one canonical block, no contention), Phase 4 introduces a multi-repo Next.js + Supabase + Trigger.dev fixture where K.2 canonical-block writes originate from three or more distinct owner commands within the same task, five K.8 personas are dispatched in parallel and each emit PROPOSED blocks that converge into the same task substrate, a slice-closure event fires mid-write to validate ordering and idempotency, and L3 ownership enforcement (block-level, persona-level, and section-level) is asserted at every persisted boundary. The walkthrough verifies that the substrate remains a single source of truth across roughly twenty discrete Fhorja commands, that JSONL append-only event logs match the resulting filesystem state with zero drift, and that out-of-band K.4/K.5/orphan audits confirm convergence after the fact.

## Step list

### Step 1 -- `project-bootstrap`

- Mode: Plan
- Expected substrate file + section: `projects/acme__phase4-high/PROJECT_CHARTER.md` (`§Objective`, `§Stack`, `§Planned Repositories`, `§Constraints`); `projects/acme__phase4-high/REFERENCES.md` (skeleton only); `projects/acme__phase4-high/active/` and `archive/` directories created
- Expected JSONL events: `project.bootstrap.started`, `substrate.file.created` (×2), `project.bootstrap.completed`
- Edge cases: bootstrap must be idempotent -- re-running with the same `<client>__<project>` slug should emit `project.bootstrap.noop` rather than overwrite the charter; verify that the `Planned Repositories` section enumerates `apps/web`, `apps/worker`, and `infra/supabase` so subsequent multi-repo init does not re-prompt

### Step 2 -- `task-init` (multi-repo)

- Mode: Plan
- Expected substrate file + section: `projects/acme__phase4-high/active/2026-06-05_persona-fanout/README.md`, `TASK_STATE.md` (`§Status`, `§Repos`), `SOURCE_OF_TRUTH.md` (multi-repo block with `apps/web`, `apps/worker`, `infra/supabase`), `DECISIONS.md` (empty scaffold), `IMPLEMENTATION_PLAN.md` (empty scaffold)
- Expected JSONL events: `task.init.started`, `substrate.file.created` (×5), `task.init.multirepo.detected`, `task.init.completed`
- Edge cases: `SOURCE_OF_TRUTH.md` must include a `multi-repo: true` marker so PR-package and consistency-sweep run per-repo later; if `PROJECT_CHARTER.md` is missing, init must fail loudly rather than seed defaults

### Step 3 -- `decision-interview` D-1 (RLS posture)

- Mode: Ask
- Expected substrate file + section: `DECISIONS.md` `§D-1 RLS posture` (status `LOCKED`, owner `decision-interview`, ts ISO-8601)
- Expected JSONL events: `decision.interview.started`, `decision.question.asked` (×N), `decision.locked` with `id=D-1`
- Edge cases: decision must be canonical-block-tagged so K.2 owner enforcement later refuses overwrites from non-decision commands; if user defers, write `status: DEFERRED` rather than skipping the block

### Step 4 -- `decision-interview` D-2 (multi-tenant boundary)

- Mode: Ask
- Expected substrate file + section: `DECISIONS.md` `§D-2 Tenant isolation boundary` appended below D-1 (append-only)
- Expected JSONL events: `decision.locked` with `id=D-2`
- Edge cases: must not reorder D-1; ordering invariant is asserted by K.5 later

### Step 5 -- `decision-interview` D-3 (job-to-be-done switch)

- Mode: Ask
- Expected substrate file + section: `DECISIONS.md` `§D-3 JTBD primary switch` (locks the canonical persona JTBD that the K.8 fanout will validate)
- Expected JSONL events: `decision.locked` with `id=D-3`
- Edge cases: D-3 must be referenced by ID from the implementation plan so that L3 ownership traces decision → plan → slice → PROPOSED block

### Step 6 -- `impact-analysis`

- Mode: Plan
- Expected substrate file + section: `IMPACT_ANALYSIS.md` with per-repo subsections (`§apps/web`, `§apps/worker`, `§infra/supabase`), blast radius, contract impacts, schema/runtime risks
- Expected JSONL events: `impact.analysis.started`, `substrate.file.created`, `impact.analysis.completed`
- Edge cases: must reference D-1..D-3 by ID; if any decision is `DEFERRED`, impact analysis must flag `requires-resolution`

### Step 7 -- `implementation-plan`

- Mode: Plan
- Expected substrate file + section: `IMPLEMENTATION_PLAN.md` (`§Slices` with S-1 schema, S-2 API, S-3 UI, S-4 worker; each with objective, scope, validation, exit criteria, complexity tag); `TASK_STATE.md §Status` flipped from `INITIALIZED` to `PLANNED`
- Expected JSONL events: `plan.slice.defined` (×4), `plan.locked`
- Edge cases: ordering rationale must be explicit so slice-closure later can validate exit criteria in the same order

### Step 8 -- `approve-plan`

- Mode: Ask
- Expected substrate file + section: `IMPLEMENTATION_PLAN.md §Approval` (timestamp, approver, hash of plan body)
- Expected JSONL events: `plan.approved`, `task.state.transitioned` (`PLANNED` → `READY_TO_DISPATCH`)
- Edge cases: approval must hash the plan body so subsequent edits to the plan force re-approval; any plan-body mutation without `approve-plan` is a K.5 violation

### Step 9 -- K.8 persona dispatch: `rls-auth-boundary-auditor`

- Mode: Agent
- Expected substrate file + section: `slices/S-1/PROPOSED/rls-auth-boundary-auditor.md` (`§Findings`, `§Recommendations`, `§Ownership: rls`)
- Expected JSONL events: `persona.dispatch.started` (`persona=rls`), `proposed.block.written`, `persona.dispatch.completed`
- Edge cases: PROPOSED block must declare `owner: rls-auth-boundary-auditor`; any attempt by another persona to overwrite this block in the same slice must be rejected by L3 ownership enforcement

### Step 10 -- K.8 persona dispatch: `migration-safety-steward`

- Mode: Agent
- Expected substrate file + section: `slices/S-1/PROPOSED/migration-safety-steward.md` (`§Migration Risks`, `§Rollback Plan`)
- Expected JSONL events: `persona.dispatch.started` (`persona=mss`), `proposed.block.written`
- Edge cases: dispatch runs in parallel with Step 9; the JSONL must preserve causal order via monotonic `seq` even when wall-clock times interleave

### Step 11 -- K.8 persona dispatch: `jtbd-switch-interviewer`

- Mode: Agent
- Expected substrate file + section: `slices/S-3/PROPOSED/jtbd-switch-interviewer.md` (`§JTBD Confirmed`, `§Switch Triggers`)
- Expected JSONL events: `persona.dispatch.started` (`persona=jtbd`), `proposed.block.written`
- Edge cases: must reference D-3 by ID; if D-3 was `DEFERRED`, persona must emit `persona.blocked` rather than write a PROPOSED block

### Step 12 -- K.8 persona dispatch: `color-contrast-architect`

- Mode: Agent
- Expected substrate file + section: `slices/S-3/PROPOSED/color-contrast-architect.md` (`§Contrast Audit`, `§Token Recommendations`)
- Expected JSONL events: `persona.dispatch.started` (`persona=cc`), `proposed.block.written`
- Edge cases: persona writes into the same slice S-3 as the JTBD persona -- both blocks must coexist under distinct ownership namespaces; collision on the same `§` heading is a hard error

### Step 13 -- K.8 persona dispatch: `post-deploy-verifier`

- Mode: Agent
- Expected substrate file + section: `slices/S-4/PROPOSED/post-deploy-verifier.md` (`§Verification Steps`, `§Rollback Trigger`)
- Expected JSONL events: `persona.dispatch.started` (`persona=pdv`), `proposed.block.written`, `persona.fanout.completed` (aggregate marker)
- Edge cases: PDV must reference the worker repo from `SOURCE_OF_TRUTH.md` multi-repo block; if the repo is missing, persona must fail closed

### Step 14 -- `approve-proposed` (batch)

- Mode: Ask
- Expected substrate file + section: each of the 5 PROPOSED blocks gets a sibling `APPROVED/<persona>.md` with approval hash; `TASK_STATE.md §PROPOSED Counter` decrements to 0
- Expected JSONL events: `proposed.block.approved` (×5), `proposed.counter.zeroed`
- Edge cases: approval must be all-or-nothing per slice -- partial approval within a slice is rejected to prevent ownership ambiguity; the PROPOSED counter (installed as a hook on 2026-06-03) must reach zero before slice-closure is allowed

### Step 15 -- `implement-approved-slice` S-1

- Mode: Agent
- Expected substrate file + section: `slices/S-1/EXECUTION.md` (`§Files Changed`, `§Tests Added`, `§Validation`); writes also appear in `apps/web` and `infra/supabase` working tree
- Expected JSONL events: `slice.execution.started`, `substrate.file.written` (×N), `slice.execution.completed`
- Edge cases: execution must touch only files declared in the slice scope; any out-of-scope write is rejected by L3 file-ownership enforcement

### Step 16 -- `slice-closure` S-1 with mid-write conflict injection

- Mode: Plan
- Expected substrate file + section: `slices/S-1/CLOSURE.md` (`§Exit Criteria Met`, `§Carryover`); `TASK_STATE.md §Slices` flips S-1 to `CLOSED`
- Expected JSONL events: `slice.closure.started`, `substrate.write.conflict.detected` (injected), `substrate.write.conflict.resolved` (retry with monotonic seq), `slice.closed`
- Edge cases: this step deliberately races a K.2 owner-command write against the closure write; the test asserts that the conflict is detected via the append-only invariant, the loser retries against the new head, and no closure block is silently lost. If conflict resolution fails, the substrate must remain in the pre-closure state rather than half-applied

### Step 17 -- `implement-approved-slice` S-2, S-3, S-4 (sequential)

- Mode: Agent
- Expected substrate file + section: `slices/S-2/EXECUTION.md`, `slices/S-3/EXECUTION.md`, `slices/S-4/EXECUTION.md`
- Expected JSONL events: `slice.execution.completed` (×3)
- Edge cases: S-3 execution must consume both the JTBD and color-contrast APPROVED blocks; failure to reference both is a K.5 violation. S-4 execution must reference the PDV block before any worker code change

### Step 18 -- `slice-closure` S-2, S-3, S-4

- Mode: Plan
- Expected substrate file + section: closure blocks for each slice; `TASK_STATE.md §Slices` reaches `ALL_CLOSED`
- Expected JSONL events: `slice.closed` (×3), `task.state.transitioned` (`EXECUTING` → `READY_FOR_REVIEW`)
- Edge cases: closure of S-4 must verify that PDV verification steps were executed and recorded; closure without execution evidence is rejected

### Step 19 -- `repo-consistency-sweep` with substrate audit

- Mode: Plan
- Expected substrate file + section: `SWEEP_REPORT.md` (`§Bug-Class Hits`, `§Substrate Audit`, `§Triage`); per-repo subsections
- Expected JSONL events: `sweep.started`, `sweep.bugclass.hit` (×N), `sweep.substrate.audit.completed`, `sweep.completed`
- Edge cases: substrate audit walks the JSONL event log and asserts every persisted block has a matching `substrate.file.written` event; any orphan file or orphan event is reported

### Step 20 -- `scan-substrate-orphans`

- Mode: Plan
- Expected substrate file + section: `ORPHAN_SCAN.md` (`§Orphan Files`, `§Orphan Events`, `§Ownership Gaps`)
- Expected JSONL events: `orphan.scan.started`, `orphan.scan.completed` with `count=0` (expected)
- Edge cases: any non-zero orphan count blocks PR packaging; the scan must cross-reference L3 ownership maps so that a file owned by a deregistered persona is flagged as `ownership-gap` rather than `orphan`

## Convergence assertions

After Step 20, run an out-of-band audit triple -- `K.5` (substrate self-consistency), `K.4` (event-log replay), and `scan-substrate-orphans` (orphan + ownership-gap detection) -- and assert all three return zero drift simultaneously. Specifically: (1) `K.5` replays `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, every `slices/S-*/PROPOSED/*.md`, every `slices/S-*/APPROVED/*.md`, every `slices/S-*/EXECUTION.md`, and every `slices/S-*/CLOSURE.md` and confirms that referential integrity holds end-to-end (every PROPOSED has an APPROVED, every APPROVED has an EXECUTION reference, every EXECUTION has a CLOSURE, and every CLOSURE cites the decisions it implements by ID). (2) `K.4` replays the JSONL event log from `task.init.started` through `orphan.scan.completed` into a clean working directory and asserts the resulting filesystem is byte-identical to the live substrate (ignoring volatile timestamps). (3) `scan-substrate-orphans` reports zero orphan files, zero orphan events, and zero ownership gaps. If any of the three audits returns non-zero, the Phase 4 walkthrough fails and the substrate is considered drifted -- Phase 4 is only green when all three converge on zero in the same audit pass.

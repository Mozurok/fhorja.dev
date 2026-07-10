# Command prompt stubs (minimal)

Minimal copy-paste starters for each official command. Replace `TASK_FOLDER` with your task path, for example `projects/acme__platform/active/2026-04-24_fix-login-redirect/`.

**Normative behavior** lives in [`WORKFLOW_OPERATING_SYSTEM.md`](./WORKFLOW_OPERATING_SYSTEM.md) and in each file under [`commands/`](./commands/).

**Handoff quality:** every command output must end with a fenced `### Handoff` using the **adaptive ending format** from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact intra-session, Mode B with `Resume context:` cross-session). If a model omits it, re-run or ask it to complete the Handoff only.

**Long-form narrative** (multi-turn story, mock outputs): [`WORKFLOW_DEMO.md`](./WORKFLOW_DEMO.md).

---

## Project initialization

| Command | Minimal prompt |
|---------|----------------|
| `project-bootstrap` | Run `@commands/project-bootstrap.md`. Project identifier: `<client>__<project>`. One-line objective: `<goal>`. Stack (if known): `<languages / frameworks / hosting>`. Repositories (optional): `<list>`. Constraints / non-goals (if known): `<list>`. |
| `capture-references` | Run `@commands/capture-references.md`. Project: `<client>__<project>`. Inputs: `<URLs to fetch and/or topics to search>`. Optional tags: `<comma-separated>`. Optional depth: `<summary \| detailed>`. |

---

## State and navigation

| Command | Minimal prompt |
|---------|----------------|
| `task-init` | Run `@commands/task-init.md`. Project folder: `<client>__<project>`. Task slug: `<slug>`. One-line goal: `<goal>`. Product repo path (if any): `<path>`. |
| `task-workspace` | Run `@commands/task-workspace.md` for `TASK_FOLDER`. Provision an opt-in git worktree + `task/<slug>` branch for the task (git-gated no-op otherwise); record the `## Workspace` section in `SOURCE_OF_TRUTH.md`. Mode: Agent to run git. |
| `task-init-fleet` | Run `@commands/task-init-fleet.md`. Project folder: `<client>__<project>`. Brief: `<full brief>`. Optional decomposition: `[{slug, objective, scope_files, scope_repos, complexity_tier?, cross_links?}, ...]`. Optional shared repos: `<list>`. Orchestrator-workers J.8 PILOT -- Opus orq + N Sonnet workers (1 sub-task each); merges INITIATIVE_INDEX.md. Use when N >= 3 independent work streams. |
| `sync-task-state` | Run `@commands/sync-task-state.md` for `TASK_FOLDER`. Summarize what changed since last state and the real next step. |
| `state-reconcile` | Run `@commands/state-reconcile.md` for `TASK_FOLDER`. Multiple artifacts disagree with `TASK_STATE.md`; propose minimal patches. Opt-in read-only memory-lint mode (ADR-0053) reports dead cross-links, orphaned `SLICES/` files, and stale facts via `scripts/memory-lint.sh` and writes nothing. |
| `resume-from-state` | Run `@commands/resume-from-state.md` for `TASK_FOLDER`. New session; reconstruct truth and recommend next command. |
| `capture-observation` | Run `@commands/capture-observation.md` for `TASK_FOLDER`. Observation: `<one to three lines>`. Optional tag: `<question \| hypothesis \| concern \| note>`. |
| `autonomous-board` | Run `@commands/autonomous-board.md` for `TASK_FOLDER`. Read-only board-of-record for an autonomous run: slices and waves mapped to to-do / in-progress / escalated / proposed / done, from the Fhorja artifacts only. No writes. |
| `what-next` | Run `@commands/what-next.md` for `TASK_FOLDER`. Fast routing only. |
| `portfolio-review` | Run `@commands/portfolio-review.md`. Read-only cross-task board across every active task in all projects (no single task folder). Runs `scripts/portfolio-review.sh` (optional `--project <slug>` / `--stale-days N`); classifies each task done-unclosed / blocked / my-move / stale / in-flight and recommends one action per row. Never writes. Ask mode. |
| `workflow-guide` | Run `@commands/workflow-guide.md` for `TASK_FOLDER`. Explain current phase and next 2-3 steps. (Onboarding helper; experienced users default to `what-next`.) |
| `im-stuck` | Run `@commands/im-stuck.md` for `TASK_FOLDER`. Symptom: `<loop / false progress / stale state / confusion>`. |
| `incident-triage` | Run `@commands/incident-triage.md` for `TASK_FOLDER`. Failure signal (paste verbatim): `<stack trace / error / failing test + assertion / repro steps>`. Expected: `<1-2 lines>`. Environment: `<local / ci / staging / prod>`. Urgency: `<BLOCKING_PROD / BLOCKING_CI / BLOCKING_PEER / NONE>`. Recent change: `<commit/deploy/config or none>`. |
| `compact-task-memory` | Run `@commands/compact-task-memory.md` for `TASK_FOLDER`. Task memory has grown across multiple closed slices and feels heavy; produce a slimmed `TASK_STATE.md` preserving canonical decisions and the recommended next step verbatim, with a `## Compaction history` audit entry. PROPOSED-by-default in Plan mode. See ADR-0015. |
| `approve-proposed` | Run `@commands/approve-proposed.md` for `TASK_FOLDER`. The most recent prior assistant turn ended with `### Artifact changes` containing one or more files marked `PROPOSED` with full inline content; I have read and accept all of them. Persist them atomically in one turn and print the locked five-line recap. Agent mode. See ADR-0024. |
| `approve-plan` | Run `@commands/approve-plan.md` for `TASK_FOLDER`. IMPLEMENTATION_PLAN.md is ready to lock; verify no `[NEEDS CLARIFICATION:]` markers remain, append `## Approval log` entry, stamp TASK_STATE.md as APPROVED, and emit the execution Handoff waves-aware per ADR-0042 (`implement-fleet` when the first remaining wave has size >= 2 with `Scope` + `Depends-on`; otherwise `implement-approved-slice` for the first slice). Agent mode. |

---

## Discovery and scoping

| Command | Minimal prompt |
|---------|----------------|
| `code-locate` | Run `@commands/code-locate.md` for `TASK_FOLDER`. Behavior: `<1-3 lines describing what the code does>`. Search type: `<implementation \| tests \| config \| any>`. Product workspace: `<path>`. Optional scope hint: `<path prefix / glob / language>`. Multi-repo only: target repo: `<identifier matching SOURCE_OF_TRUTH ## Repositories entry>`. |
| `code-context-map` | Run `@commands/code-context-map.md` for `TASK_FOLDER`. Target codebase path: `<path>`. Scope: `<digest \| module:glob \| chain:seed-file>` (default digest). Optional for chain: `max-hops <N \| all>`, `direction <imports \| dependents \| both>`. Optional: `html` (self-contained MAP.html projection), `refresh` (regenerate an existing map). |
| `impact-analysis` | Run `@commands/impact-analysis.md` for `TASK_FOLDER`. Product context: `<path or link>`. Multi-repo only: produces per-repo blast radius if SOURCE_OF_TRUTH has a `## Repositories` section. |
| `invariants-and-non-goals` | Run `@commands/invariants-and-non-goals.md` for `TASK_FOLDER`. Carry forward: `<constraints>`. |
| `targeted-questions` | Run `@commands/targeted-questions.md` for `TASK_FOLDER`. Blocker: `<what is unknown>`. |
| `decision-interview` | Run `@commands/decision-interview.md` for `TASK_FOLDER`. Focus: `<policy or behavior choice>`. |
| `problem-framing` | Run `@commands/problem-framing.md`. Rough objective: `<the fuzzy idea or pain point>`. (Pre-task Phase 0.5; writes a task-level BRIEF.md that task-init consumes.) |
| `external-research` | Run `@commands/external-research.md` for `TASK_FOLDER`. Research question: `<one paragraph>`. Sources: `<list of URLs>` OR topic search seed: `<topic>` (the command will propose candidate URLs for your approval before fetching). Optional output structure: `<comparison-table \| decision-matrix \| narrative \| regulatory-checklist>`. Optional refresh flag: `<refresh>` (only when an existing EXTERNAL_RESEARCH.md should be regenerated). |
| `external-research-fleet` | Run `@commands/external-research-fleet.md` for `TASK_FOLDER`. Parent question: `<one sentence>`. Angles manifest: `[{angle_id, angle_name, angle_question, sources: [{title, url, references_entry_status}, ...]}, ...]` (N >= 3). Optional output structure: `<comparison-table \| decision-matrix \| narrative \| regulatory-checklist>`. Orchestrator-workers J.9 PILOT -- Sonnet orq + N Sonnet workers (1 angle each); merges EXTERNAL_RESEARCH.md with ADR-0018 reconciliation. Use when N >= 3 distinct angles or source-groups. |
| `stack-recommend` | Run `@commands/stack-recommend.md` for `TASK_FOLDER`. Project type: `<e.g., SaaS task management app \| mobile fintech \| CLI developer tool>`. Optional constraints: `<e.g., must use Supabase \| no AWS \| needs SSR>`. Optional reference links: `<URLs to research>`. Optional refresh flag: `<refresh>` (only when an existing STACK_RECOMMENDATION.md should be regenerated). |
| `stack-currency-check` | Run `@commands/stack-currency-check.md` for `TASK_FOLDER`. Framework + version: `<e.g., Next.js 15 \| Supabase JS v2>`. Patterns about to use: `<list>`. Optional refresh flag: `<refresh>` (only when an existing CURRENT_PATTERNS.md is stale). |
| `feature-library-scout` | Run `@commands/feature-library-scout.md` for `TASK_FOLDER`. Stack: `<e.g., React Native 0.7x + Expo SDK 5x>`. Product feature set: `<e.g., large lists, camera, forms, keyboard, bottom sheets>`. Optional product repo path: `<path>` (to scan existing deps). Optional reference links: `<URLs>`. Optional refresh flag: `<refresh>` (only when an existing FEATURE_LIBRARIES.md should be regenerated). For a deep per-problem sweep use `feature-library-scout-fleet`. |
| `feature-library-scout-fleet` | Run `@commands/feature-library-scout-fleet.md` for `TASK_FOLDER`. Stack: `<e.g., React Native 0.7x + Expo SDK 5x>`. Product feature set: `<the orchestrator decomposes this into N >= 3 feature problems, one worker each>`. Optional product repo path: `<path>`. Optional max_fanout override: `<default 12>`. Optional refresh flag: `<refresh>`. Use only when 3 or more distinct feature problems each warrant a deep read; for 1-3 use `feature-library-scout`. |
| `api-contract-review` | Run `@commands/api-contract-review.md` for `TASK_FOLDER`. Contract: `<endpoints / OpenAPI / request-response shapes>`. Existing API conventions: `<path or link>`. |
| `graphql-contract-review` | Run `@commands/graphql-contract-review.md` for `TASK_FOLDER`. Schema or BFF contract: `<SDL / types-queries-mutations / subgraph schemas / BFF endpoints>`. GraphQL stack: `<e.g. Apollo Federation, single graph, Relay>`. Existing schema for consistency: `<path or link>`. |
| `frontend-architecture-review` | Run `@commands/frontend-architecture-review.md` for `TASK_FOLDER`. Architecture: `<surfaces, proposed boundaries, stack, team topology>`. Considering micro-frontends? `<yes / no / unsure>`. Existing repo layout for grounding: `<path or link>`. |
| `frontend-system-design` | Run `@commands/frontend-system-design.md` for `TASK_FOLDER`. Surface: `<feature or screen to design>`. Platforms: `<web \| mobile \| both>`. Mode: `<rfc \| interview>` (interview needs the prompt, e.g. "design a news feed"). Produces `<task>/FRONTEND_SYSTEM_DESIGN.md` (or `_INTERVIEW.md`). |
| `backend-system-design` | Run `@commands/backend-system-design.md` for `TASK_FOLDER`. Service or feature: `<the backend service, endpoint, or feature to design>`. Expected scale: `<users / request rate / data volume / read:write, or unknown>`. Stack: `<read from task memory if set>`. Produces `<task>/BACKEND_SYSTEM_DESIGN.md` (12-section RFC). |
| `jtbd-switch-interviewer` | Run `@commands/jtbd-switch-interviewer/SKILL.md` for `TASK_FOLDER`. Target switch hypothesis: `<from X -> to Y>`. Subject pool: `<who is reachable, in what channel, with what consent>`. K.8 L3 persona (ADR-0036 Path B; owns `JTBD_INTERVIEWS.md` directly, PROPOSED for non-owned substrate via Pattern A handoff). Produces `<task>/JTBD_INTERVIEWS.md` + PROPOSED D-N drafts. |
| `color-contrast-architect` | Run `@commands/color-contrast-architect/SKILL.md` for `TASK_FOLDER`. Color token source: `<path to foundations/color.md or DTCG JSON>`. Themes: `<light, dark, ...>`. WCAG target: `<AA \| AAA>`. Documented usage pairs: `[{foreground, background, design_context}, ...]`. K.8 L3 persona (ADR-0036 Path B; owns its report file, PROPOSED for non-owned substrate); produces `<task>/CONTRAST_AUDIT.md` (pairwise matrix). |
| `godot-scene-plan` | Run `@commands/godot-scene-plan.md` for `TASK_FOLDER`. Feature or screen: `<what it is and does>`. Game-design context: `<core loop / mechanics, or link to the game-design brief>`. Target Godot version (optional): `<e.g. 4.x; 4.6+ for editor on-device testing>`. Existing project layout (brownfield): `<path>`. MCP-agnostic; produces `<task>/GODOT_SCENE_PLAN.md`. Part of the Godot 2D-mobile cluster (ADR-0069). |
| `a11y-audit` | Run `@commands/a11y-audit/SKILL.md` for `TASK_FOLDER`. UI surface: `<screen-spec / journey-spec / component-set or implemented files>`. WCAG target: `<A \| AA \| AAA>`. Surface type: `<web \| native-mobile \| other>`. Optional checker report: `<axe / Lighthouse / pa11y output>`. K.8 L1 persona; produces `<task>/ACCESSIBILITY_AUDIT.md` (per-criterion conformance ledger + manual-review queue). |
| `performance-budget` | Run `@commands/performance-budget/SKILL.md` for `TASK_FOLDER`. Performance surface(s): `<page/route, endpoint, list, query, bundle, job>`. Optional baseline: `<Lighthouse / APM / profiler / EXPLAIN output>`. Optional locked target or SLA: `<value>`. K.8 L1 persona; produces `<task>/PERFORMANCE_BUDGET.md` (per-metric threshold + percentile + source + regression action). |
| `ai-feature-eval-harness` | Run `@commands/ai-feature-eval-harness.md` for `TASK_FOLDER`. AI feature: `<what it takes in, what the model produces, the user-visible success condition>`. Optional labeled dataset: `<path or "none, build one">`. Optional quality target: `<accuracy / pass-rate / latency / cost>`. Produces `<task>/AI_EVAL_PLAN.md` (success criteria + dataset spec + per-criterion grading + pass threshold). |
| `slo-define` | Run `@commands/slo-define/SKILL.md` for `TASK_FOLDER`. Service/flow: `<the user-facing service or critical flow>`. Observability stack: `<metrics/APM, logs, uptime>`. Optional baseline: `<current availability/latency/error-rate>`. Optional SLA/target: `<value>`. K.8 L1 persona; produces `<task>/SLO_SPEC.md` (SLIs + SLO target + window + error budget + budget policy). |
| `postmortem-author` | Run `@commands/postmortem-author/SKILL.md` for `TASK_FOLDER`. Resolved incident: `<what failed, when detected, how resolved>`. Optional SLO_SPEC for impact: `<path or none>`. Optional timeline evidence: `<alert timestamps, deploy SHAs, fixing commit>`. K.8 L1 persona; produces `<task>/POSTMORTEM.md` (timeline + blameless contributing causes + impact vs error budget + owned action items). |
| `release-plan` | Run `@commands/release-plan.md` for `TASK_FOLDER`. Change under release: `<surface, schema/data impact, reversibility>`. Available rollout infra: `<feature flags, traffic routing, parallel envs, metrics>`. Optional SLO_SPEC for the promotion metric: `<path or none>`. Produces `<task>/RELEASE_PLAN.md` (pattern + exposure ramp + promotion metric + rollback trigger/mechanism + go/no-go). |

---

## Database context

| Command | Minimal prompt |
|---------|----------------|
| `db-context-supabase` | Run `@commands/db-context-supabase.md` for `TASK_FOLDER`. Scope (one or more): tables `<schema.table, ...>` and/or schemas `<schema, ...>`. Depth: `<tables-only \| tables+rls \| full>`. Optional Supabase project ref: `<ref-or-alias>`. Optional refresh flag: `<refresh>` (only when an existing `DB_CONTEXT.md` should be regenerated). Requires a Supabase MCP server reachable from this session. |
| `db-context-postgres` | Run `@commands/db-context-postgres.md` for `TASK_FOLDER`. Connection: env vars (PGHOST/PGPORT/PGUSER/PGDATABASE) OR `DATABASE_URL`. Scope: tables `<schema.table, ...>` and/or schemas `<schema, ...>`. Depth: `<tables-only \| tables+rls \| full>`. Optional refresh flag: `<refresh>`. Uses psql/pg_dump for generic Postgres (Cloud SQL, GKE Autopilot, RDS, self-hosted). |

---

## Contract and decision hardening

| Command | Minimal prompt |
|---------|----------------|
| `resolve-contract-gaps` | Run `@commands/resolve-contract-gaps.md` for `TASK_FOLDER`. Contradiction: `<short>`. |
| `contract-signoff` | Run `@commands/contract-signoff.md` for `TASK_FOLDER`. Ready to lock wording for implementation. |
| `direction-adjust` | Run `@commands/direction-adjust.md` for `TASK_FOLDER`. Realization: `<what was being done, what was noticed, what should change>`. Affects: `<slice or phase, optional>`. |

---

## Planning and validation

| Command | Minimal prompt |
|---------|----------------|
| `implementation-plan` | Run `@commands/implementation-plan.md` for `TASK_FOLDER`. Prefer slices with exit criteria. |
| `test-strategy` | Run `@commands/test-strategy.md` for `TASK_FOLDER`. Risk focus: `<area>`. |
| `self-critique-and-revise` | Run `@commands/self-critique-and-revise.md` for `TASK_FOLDER`. Artifact: `<IMPLEMENTATION_PLAN.md \| SLICES/<NN>-*.md \| PR_PACKAGE.md>`. Optional focus: `<exit criteria \| scope leak \| diff fidelity \| ...>`. Evaluator-optimizer pattern (ADR-0021); PROPOSED-by-default in Plan mode. |
| `verify-against-rubric` | Run `@commands/verify-against-rubric.md` for `TASK_FOLDER`. Artifact: `<path>`. Rubric: `<inline criteria list OR section reference: <file>#<anchor>>`. Spawns stateless sub-agent (Claude Code Task tool); returns structured verdict; persists to VERIFICATION_LOG.md. Per ADR-0033. Use on HIGH-complexity slices only. |
| `verify-against-rubric-fleet` | Run `@commands/verify-against-rubric-fleet.md` for `TASK_FOLDER`. Artifact manifest: `[{artifact_id, artifact_path}, ...]` (N >= 4). Shared rubric: `<inline OR section reference>`. Optional criteria list override. Optional cohort_label. Orchestrator-workers J.10 PILOT -- Sonnet orq + N stateless Sonnet workers; emits VERIFICATION_LOG.md cohort entry with SYSTEMIC vs LOCALIZED failure clustering. Use when N >= 4 artifacts share one rubric. |
| `rls-auth-boundary-auditor` | Run `@commands/rls-auth-boundary-auditor/SKILL.md` for `TASK_FOLDER`. Migration paths: `<supabase/migrations/*.sql>`. Tenant tables: `<list or "auto-enumerate">`. Auth model: `<auth.uid() \| auth.jwt() ->> 'org_id' \| hybrid>`. Tenant scope: `<per-user \| per-org \| per-team \| compound>`. K.8 L3 persona (ADR-0036 Path B; owns its report file, PROPOSED for non-owned substrate); produces `<task>/RLS_AUDIT.md` with per-table posture + migration-shaped remediation. |
| `migration-safety-steward` | Run `@commands/migration-safety-steward/SKILL.md` for `TASK_FOLDER`. Migration file(s): `<*.sql>`. Row count estimate per table: `<<10k \| 10k-1M \| 1M-100M \| >100M>`. Deploy strategy: `<single-shot \| rolling \| blue/green>`. Postgres version: `<N>`. Optional online-DDL tool: `<pg-osc \| Reshape \| ...>`. K.8 L3 persona (ADR-0036 Path B; owns its report file, PROPOSED for non-owned substrate); produces `<task>/MIGRATION_SAFETY.md` (per-statement SAFE / NEEDS-PHASING / UNSAFE verdict). |

---

## Execution and closure

| Command | Minimal prompt |
|---------|----------------|
| `implement-approved-slice` | Run `@commands/implement-approved-slice.md` for `TASK_FOLDER`. Approved slice only: `SLICES/<file>.md`. Product workspace: `<path>`. |
| `implement-fleet` | Run `@commands/implement-fleet.md` for `TASK_FOLDER`. Approved multi-slice plan with per-slice `Scope` + `Depends-on`. Product workspace: `<path>`. Base ref: `<ref>`. Orchestrator-workers per ADR-0041: computes parallelizable waves, dispatches one worktree-isolated worker per independent slice, gates each wave on build+typecheck+test. Use when a wave has size >= 2; falls back to `implement-approved-slice` for chains. Agent mode. |
| `implement-slice-complement` | Run `@commands/implement-slice-complement.md` for `TASK_FOLDER`. Anchor slice: `SLICES/<file>.md`. Micro-deltas (bullets): `<list>`. Primary paths: `<paths>`. Product workspace: `<path>`. |
| `slice-closure` | Run `@commands/slice-closure.md` for `TASK_FOLDER`. Decide if current slice is done with evidence. |
| `task-close` | Run `@commands/task-close.md` for `TASK_FOLDER`. Close the whole task: verify done-conditions (waive team-approval/merge if solo), write final `TASK_STATE.md`, move `active/` -> `archive/`. Mode: Agent to execute the move. |
| `harvest-session-learnings` | Run `@commands/harvest-session-learnings.md` for `TASK_FOLDER`. Sweep the session for reusable lessons and append anchored, de-duplicated entries to `LEARNINGS.md` (append-only; ADR-0017 produce-side). NO_OP when nothing durable. |
| `review-hard` | Run `@commands/review-hard.md` for `TASK_FOLDER`. Pre-PR risk review; optional checklist: `templates/review-hard-checklist.md`. |
| `repo-consistency-sweep` | Run `@commands/repo-consistency-sweep.md` for `TASK_FOLDER`. Proactive defect-class detection against `wos/bug-classes/` library before PR packaging. |
| `apply-sweep-triage` | Run `@commands/apply-sweep-triage.md` for `TASK_FOLDER`. Persist triage from a SWEEP snapshot into `REVIEW_PREFERENCES.md`. |
| `security-review` | Run `@commands/security-review.md` for `TASK_FOLDER`. Threat model + OWASP ASVS L1 + auth flow trace + dependency/secret scan reminders. |
| `skill-vet` | Run `@commands/skill-vet.md` for a third-party skill or plugin directory `CANDIDATE_PATH`. Read-only: reads every file (not just SKILL.md), declared-vs-actual + exfiltration + agent-config-write + hidden-Unicode scan, returns INSTALL/SANDBOX/DECLINE for human approval. Never installs or fetches (ADR-0046). URL sources go through capture-references first. |
| `mcp-server-vet` | Run `@commands/mcp-server-vet.md` for a third-party MCP server `CANDIDATE` (config entry and/or declared tool list). Read-only: enumerates the tool surface, declared-vs-actual + tool-description-poisoning + over-broad-scope + egress/credential + agent-config-write + hidden-Unicode scan, returns ADD/SANDBOX/DECLINE for human approval. Never adds to a config or starts a server (ADR-0070). URL sources go through capture-references first. |
| `design-spec-review` | Run `@commands/design-spec-review.md` for `TASK_FOLDER`. Verify implementation against component/screen spec doc (10 checks). |
| `foundation-audit` | Run `@commands/foundation-audit.md` for `TASK_FOLDER`. Compare code tokens vs foundation docs vs Figma for drift. |
| `extract-foundations-from-screens` | Run `@commands/extract-foundations-from-screens.md` for `TASK_FOLDER`. SCREEN_SPECs source: `<explicit list or glob>`. Design system root: `<path, e.g. docs/research/>`. Optional: `foundations=<color,typography,spacing,radii>` (default: all four). Unions raw values across specs, buckets into role tokens, writes `foundations/color.md`, `foundations/typography.md`, `foundations/spacing.md`, `foundations/radii.md`. Idempotent: locked role mappings preserved; conflicts routed to `## Review queue`. |
| `post-deploy-verifier` | Run `@commands/post-deploy-verifier/SKILL.md` for `TASK_FOLDER`. Slice file: `<SLICES/NN_*.md or IMPLEMENTATION_PLAN.md ### Slice N>`. Deploy ID: `<git SHA + env + ts>`. Observability stack: `<logging / metrics / error tracker / flags>`. Optional rollback window + on-call humans + rollback command. K.8 L3 persona (ADR-0036 Path B; owns its report file, PROPOSED for non-owned substrate); produces `<task>/POST_DEPLOY_PLAN.md` (per-AC signal map + negative checks + rollback checklist). |
| `where-we-at` | Run `@commands/where-we-at.md` for `TASK_FOLDER`. Macro checkpoint vs plan. |
| `autonomous-run` | Run `@commands/autonomous-run.md` for `TASK_FOLDER`. Drive the approved waved plan through the autonomous track (ADR-0044): two human gates, runtime governor, PROPOSED diffs only, never merges. STOP file: `<path outside agent scope>`. Governor: `<max-iter>`, `<timeout-sec>`, token/cost ceiling. |
| `godot-runtime-verify` | Run `@commands/godot-runtime-verify.md` for `TASK_FOLDER`. Slice under verification: `<feature + its acceptance behavior / EARS exit criterion>`. Run mechanism: `<MCP run tool \| godot --headless \| human press-play>`. Captured run output: `<the real debugger/console log>` (the command STOPS if not provided). Target Godot version (optional): `<e.g. 4.x>`. MCP-agnostic; the run's real output is the Layer-1 runtime evidence (ADR-0048); verifies and routes fixes, writes no code. Produces `<task>/GODOT_RUNTIME_VERIFY.md`. Part of the Godot 2D-mobile cluster (ADR-0069). |
| `app-runtime-verify` | Run `@commands/app-runtime-verify.md` for `TASK_FOLDER`. Slice under verification: `<feature + its acceptance behavior / EARS exit criterion>`. Run mechanism: `<MCP run tool \| emulator \| device \| headless>`. Captured run output: `<the real native logcat/device log and/or Metro/JS console>` (the command STOPS if not provided; see `wos/rn-expo-runtime-evidence.md`). Target stack/version (optional): `<e.g. RN 0.85 / Expo SDK 56>`. Capability-routed and MCP-agnostic; the run's real output is the Layer-1 runtime evidence (ADR-0048); a native crash is judged from the native log, not the JS console; verifies and routes fixes, writes no code. Produces `<task>/APP_RUNTIME_VERIFY.md` (ADR-0087). |

---

## Design system (WOS-UI)

| Command | Minimal prompt |
|---------|----------------|
| `design-bootstrap` | Run `@commands/design-bootstrap.md`. Figma URL: `<url>`. Project workspace: `<path>`. Bootstrap foundations + component inventory from Figma. |
| `component-spec` | Run `@commands/component-spec.md`. Figma node: `<url or node-id>`. Tier: `<atom\|molecule\|organism\|layout>`. Project workspace: `<path>`. |
| `screen-spec` | Run `@commands/screen-spec.md`. Figma frame: `<url or node-id>`. Screen: `<NN>-<slug>`. Persona: `<name>`. Project workspace: `<path>`. |
| `image-to-spec` | Run `@commands/image-to-spec.md`. Image: `<path>`. Mode: `<--component \| --screen \| auto>`. Project workspace: `<path>`. Spec from a raw image (no Figma); every observation marked `(proposed)`. |
| `journey-map` | Run `@commands/journey-map.md`. Journey: `<name>`. Persona: `<name>`. Screens: `<list of screen docs>`. Project workspace: `<path>`. |
| `pattern-doc` | Run `@commands/pattern-doc.md`. Pattern: `<name>`. Category: `<category>`. Problem: `<description>`. Project workspace: `<path>`. |
| `atom-audit` | Run `@commands/atom-audit.md`. Project workspace: `<path>`. Audit all atoms vs `COMPONENT_GUIDELINES.md`; refresh `ATOM_AUDIT.md` table. |
| `atom-audit-fleet` | Run `@commands/atom-audit-fleet.md`. Project workspace: `<path>`. Atoms dir: `<path>` (default `packages/design-system/src/atoms/`). Orchestrator-workers J.6 PILOT -- Sonnet orq + N Haiku workers (3-5 atoms each); merges into `ATOM_AUDIT.md`. Use when atom count >= 6. |
| `screen-spec-fleet` | Run `@commands/screen-spec-fleet.md`. Project workspace: `<path>`. Figma file: `<url>`. Persona: `<persona>`. Manifest: array of `{screen_number, slug, persona, figma_node_id, journey?, route?}` per screen. Orchestrator-workers J.7 PILOT -- Sonnet orq + N Sonnet workers (1 screen each); merges `SCREEN_MAP.md` + `routes.md`. Use when N >= 6, one persona per run. |
| `inventory-snapshot` | Run `@commands/inventory-snapshot.md`. Figma URL: `<url>`. Project workspace: `<path>`. Refresh `figma_components.md` with current Figma library + traceability columns + delta. |

---

## Delivery and communication

| Command | Minimal prompt |
|---------|----------------|
| `pr-package` | Run `@commands/pr-package.md` for `TASK_FOLDER`. Product repo: `<path>`. Git base branch: `<e.g. origin/main>`. Optional: seed from `templates/PR_PACKAGE.md`. Multi-repo only: target repo: `<identifier matching SOURCE_OF_TRUTH ## Repositories entry>` (run once per repo, output is `PR_PACKAGE.<repo>.md`). |
| `pr-feedback-ingest` | Run `@commands/pr-feedback-ingest.md` for `TASK_FOLDER`. PR: `<url>`. Paste feedback: `<Greptile / CI / comments>`. |
| `post-review-pivot` | Run `@commands/post-review-pivot.md` for `TASK_FOLDER`. Review changed direction: `<summary>`. |
| `branch-commit` | Run `@commands/branch-commit.md`. Diff source: `<git diff / git diff --staged / git diff <base>...HEAD>`. Paste diff: `<paths + hunks>`. Current branch: `<name>`. |
| `team-update` | Run `@commands/team-update.md` for `TASK_FOLDER`. Channel: `<Slack / Discord / Teams / email / PR comment / standup>`. |
| `delivery-asset` | Run `@commands/delivery-asset.md` for `TASK_FOLDER`. Audience: `<executives \| customers \| partners \| all-hands \| engineering-broader \| marketing \| support \| <free-form>>`. Format: `<executive-summary \| release-note \| slack-post \| email \| demo-script \| blog-post-draft \| one-pager \| <free-form>>`. Optional tone: `<formal \| informal \| technical \| non-technical \| marketing \| regulatory>`. Optional length: `<tight \| standard \| extended>`. Optional refresh flag: `<refresh>` (only when the same audience+format file already exists). |

---

## Prompt tooling

| Command | Minimal prompt |
|---------|----------------|
| `prompt-shape` | Run `@commands/prompt-shape.md`. Next intent: `<command + goal>`. Paste rough prompt: `<text>`. |

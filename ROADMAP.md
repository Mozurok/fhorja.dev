# Roadmap

This document describes the high-level direction of the project across three releases. It is non-binding and may change based on user feedback, maintainer bandwidth, and shifts in the AI engineering ecosystem.

For granular changes per release, see [CHANGELOG.md](./CHANGELOG.md).

## Project status

**Currently in alpha (v0.1.x).** The contract for command outputs and `TASK_STATE.md` is stable enough for daily use, but breaking changes may still happen between minor versions.

The project is maintained as a personal open-source effort under BDFL governance. See [CONTRIBUTING.md](./CONTRIBUTING.md) for what that implies.

## Release strategy

The project follows a phased release strategy to balance refinement quality with public exposure:

- **Phase 1 (private refinement, current)**: internal use, testing, and polishing. Repository is private. License, contributor guides, examples, lint script, and CI are being prepared but not yet exposed.
- **Phase 2 (private beta, planned)**: 1-2 months of beta testing with 5-10 invited developers. Feedback collected, structural gaps fixed.
- **Phase 3 (public MIT, done)**: repository made public, first version tagged, announced to relevant communities.
- **Phase 4 (stabilization, planned)**: continued open-source releases, community growth, and API stability toward a mature v1 contract.
- **Phase 5 (Layer 2 SaaS, exploratory)**: separate hosted service that builds on top of the open-source workflow. No commitment yet.

## Wave 1: Foundation (v0.1.x, current release window)

**Goal**: ship a usable, public, properly licensed workflow with all open-source hygiene in place.

- [x] MIT license
- [x] Contributor and security policies
- [x] Issue and PR templates
- [x] Command lint script and CI
- [x] Initial examples directory
- [x] Editor support documented for Cursor and Claude Code
- [x] FAQ document at [`docs/FAQ.md`](./docs/FAQ.md)
- [x] Migration guide for users adopting on existing tasks at [`docs/MIGRATION.md`](./docs/MIGRATION.md): covers adopting Fhorja on an in-progress task (the explicit Wave 1 ask), brand-new project adoption, legacy `.cursor`/`.claude` slash command migration, user-level skills mirroring, fork-and-customize discipline, and upgrading between Fhorja versions.
- [x] First Architecture Decision Records (ADRs) at [`docs/adr/`](./docs/adr/): 7 ADRs covering PROPOSED-by-default, Paste-this-next contract, NO_OP semantics, capability routing without model SKUs, multi-tool architecture, lazy-load spec pattern, project-level memory layer. Index at [`docs/adr/README.md`](./docs/adr/README.md).

## Wave 2: Refinement (v0.2.x, target: 2-3 months after v0.1.0)

**Goal**: reduce friction, broaden editor support, formalize design decisions.

- [x] Editor mode mapping in the spec (renamed `## Cursor mode policy` to `## Editor mode policy`; renamed `Primary Cursor mode:` to `Primary editor mode:` across all 33 commands; added a mapping table from workflow modes (`Ask` / `Plan` / `Agent` / `Debug`) to common tool equivalents (Cursor, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI); kept the canonical mode vocabulary unchanged so in-flight tasks continue to work).
- [x] Skills export flag (`--as-skills`) in sync script for Claude Code modern format. **Delivered as `--with-skills`** (P11 Phase 3) which mirrors `.claude/skills/<name>/SKILL.md` to `~/.claude/skills/`, `~/.cursor/skills/`, and `~/.codex/skills/`. The original Cursor / Claude Code legacy slash commands keep using `~/.cursor/commands/` and `~/.claude/commands/` via the same `sync-workflow-slash-commands.sh` script (no flag rename needed; the workflow simply has both targets).
- [~] Auto-sync trigger to prevent `TASK_STATE.md` drift after N consecutive PROPOSED-but-not-applied turns. **v0.1.x answer**: documented as a discipline in the spec `## Operational discipline` :: `### Drift-prevention discipline (PROPOSED accumulation)` (run `state-reconcile` after every 3-5 unapplied PROPOSED turns; run `sync-task-state` after applied progress). The mechanical auto-trigger requires a tool layer (Claude Code hook, Cursor pre-flight skill, or similar) and is contingent on that layer existing; the markdown layer cannot enforce it directly. **Update (2026-06-25):** a session-boundary slice of that tool layer now ships as the optional session-continuity hook (`scripts/session-continuity-hook.sh`; ADR-0052). On SessionStop it records a continuity marker, and on the next SessionStart it nudges the user to run `sync-task-state` when `TASK_STATE.md` has not changed since the last session end. The hook is advisory and deterministic (a bash hook cannot run the model-driven `sync-task-state`), so the PROPOSED-accumulation auto-trigger above stays a documented discipline rather than a mechanical gate; this item remains partial.
- [~] Lazy-loaded spec topics under `wos/<topic>.md` for sections not needed every command. Done: `wos/command-roles.md`, `wos/cross-cutting-workflow-guardrails.md`, `wos/multi-repo-support.md`, `wos/repository-structure.md`, `wos/project-level-memory.md`, `wos/global-output-contract.md`; cumulative spec reduction ~29.2% (18,786 :: 13,298 estimated tokens). The aggressive WOS_CORE <= ~3k tokens target depends on a more invasive split (e.g., moving `## Editor mode policy`, `## Default workflow`, `## Recommended workflows by task shape` behind lazy pointers); these are normative at every command run, so further reductions trade architectural simplicity for marginal token savings. Current pattern is at a natural stopping point.
- [x] P11: Agent Skills frontmatter on every `commands/*.md` plus `scripts/build-agent-skills.sh` adapter that generates `.claude/skills/<name>/SKILL.md` from the canonical commands. Phase 1 (frontmatter on 33/33 commands), Phase 2 (adapter + 33 generated skills + lint drift integration), Phase 3 (open-spec compliance: 33/33 pass `skills-ref validate`; `--with-skills` mirror flag in sync script; README/spec docs; CI `validate-skills-spec` job pinned to a known-good agentskills SHA). Drop-in compatibility for the 35+ tools that read `.claude/skills/` natively (Cursor 2.4+, Claude Code, GitHub Copilot, Gemini CLI, OpenAI Codex, OpenHands, Goose, Junie, etc.).
- [x] Resolution of redundant commands: `command-router` deleted (comparative routing folded into `what-next`); `workflow-guide` repositioned as onboarding helper for users still learning the workflow
- [x] Short flow for docs-only tasks at the spec `## Recommended workflows by task shape` :: `### Docs-only task (no production code change)`: 4-step flow (`task-init` :: light `implementation-plan` :: `implement-approved-slice` in Agent :: `pr-package`); skips `impact-analysis`, `invariants-and-non-goals`, `test-strategy` for non-runtime changes; explicit borderline-call note that changes to `WORKFLOW_OPERATING_SYSTEM.md`, `commands/*.md`, or `wos/<topic>.md` are NOT docs-only because they redefine workflow contracts.
- [x] Several ADRs covering core design decisions (delivered as part of Wave 1 "First ADRs"; see [`docs/adr/`](./docs/adr/) for the 7 ADRs covering all 4 decisions on this list plus multi-tool architecture, lazy-load spec pattern, and project-level memory layer).

## Wave 2.5: Context engineering uplift (CLOSED 2026-05-18; ships in v0.2.x)

**Goal**: make the workflow's implicit context-engineering patterns explicit, measurable, and falsifiable, aligned with Anthropic's "Effective context engineering for AI agents" (Sep 2025) and the broader RAG / memory / observability literature. Tracked as the 2026-05-15 context-engineering uplift task; 13 slices grouped in 4 waves; all 13 closed and archived under `projects/bmazurok__my-work-tasks/archive/2026-05-15_context-engineering-uplift/`.

- [x] **Wave 1 (foundation)**: six-layer context model named (ADR-0012); per-command `context-layers-consumed` / `context-layers-produced` / `token-budget` frontmatter (ADRs 0012, 0013); lint validates fields and warns on token-budget overrun; `<!-- cache-breakpoint -->` marker convention (ADR-0014); the spec `## Context budget` lazy-loaded subsection plus `wos/context-budget.md` topic.
- [x] **Wave 2 (memory)**: `compact-task-memory` new command for lossy working-memory compaction with audit trail (ADR-0015); user-level memory layer `/USER_MEMORY.md` at repo root (gitignored; bootstrap from `templates/USER_MEMORY.template.md`; ADR-0016); three-tier memory pyramid (task -> project -> user) with layered precedence rule; reflexion-style learnings pattern via optional `### Learnings` section on `slice-closure`, `post-review-pivot`, `incident-triage` plus task-scoped `LEARNINGS.md` (bootstrap from `templates/LEARNINGS.md`; ADR-0017); manual promotion path to user-level cross-project learnings.
- [x] **Wave 3 (retrieval + evals)**: contextual retrieval pattern in REFERENCES.md (ADR-0018; `Context within project` field on every entry; external-research surfaces reinforcing / contradicting / different-framing source relationships); LLM-as-judge eval layer via `evals/scripts/judge.py` with locked rubric wrapper (ADR-0019; OPTIONAL second pass; UNCERTAIN defers to human); eval coverage grew from 15 to 21 scenarios (4 new routing-edge tests plus 2 new-command coverage scenarios).
- [x] **Wave 4 (observability + agents)**: task cost observability via `scripts/measure-task-cost.py` (ADR-0020; simulation-only per the multi-tool neutrality rule from ADR-0005; first baseline shows 66.9% cache savings on a canonical 9-phase task); evaluator-optimizer command `self-critique-and-revise` (ADR-0021; LOCKED per-artifact-type rubric; PROPOSED-by-default in Plan mode); sub-agent orchestration topic `wos/sub-agent-orchestration.md` (ADR-0022; docs-only per D-8); context-rot guardrails with per-phase thresholds (ADR-0023; warnings on `sync-task-state`, `where-we-at`, `resume-from-state` when TASK_STATE.md exceeds the phase-specific threshold).

Across the uplift: 37 commands (was 35; added `compact-task-memory` and `self-critique-and-revise`); 23 ADRs (was 11; added 0012-0023); 21 eval scenarios (was 14); 8 lazy spec topics (was 6; added `context-budget` and `sub-agent-orchestration`); 4 templates (was 2; added `USER_MEMORY.template.md` and `LEARNINGS.md`); 2 new Python helpers (`evals/scripts/judge.py`, `scripts/measure-task-cost.py`); 1 new baseline snapshot (`scripts/baseline-task-cost-2026-05-18.md`).

## Wave 2.6: Proposed-mode ergonomics fixup (CLOSED 2026-05-19; ships in v0.2.x)

**Goal**: fix two failure modes in the PROPOSED-by-default contract (ADR-0001) surfaced by the first real-world Fhorja session on 2026-05-18. Tracked as the 2026-05-19 proposed-mode-fixup task; 3 slices (slice 0 housekeeping, slice 1 decision-interview fix, slice 2 new `/approve-proposed` command); archived under `projects/bmazurok__my-work-tasks/archive/2026-05-19_proposed-mode-fixup/`.

- [x] **Slice 0 (housekeeping)**: archived stale `2026-05-02_prepare-for-public-agpl-release` task as superseded by the 2026-05-15 uplift (FAQ, MIGRATION, ADRs all delivered under a different ledger). Loose ends carried forward: examples/ directory, WOS_governance_addition_patch integration, phase narrative drift re-check before Phase 3 cut.
- [x] **Slice 1 (`/decision-interview` fix)**: added **LOCK-pick recognition** operating rule so the command persists DECISIONS.md and TASK_STATE.md as APPLIED in the same turn the user supplies LOCK picks (`D<N> [LOCK]`, ranges, `aprovado` / `approved` wildcards). Eliminates the re-propose loop that forced duplicate input in the 2026-05-18 session. Added no-nest rule to `commands/_shared/artifact-changes-default.md` (propagated to 28 commands). New regression scenario `evals/scenarios/22-decision-interview-approve-persists.md`.
- [x] **Slice 2 (`/approve-proposed` command)**: new command (37 -> 38) implementing the batch-persist idiom from ADR-0024. Reads the most recent prior assistant turn, finds every file marked `PROPOSED` in `### Artifact changes`, writes all atomically with a locked five-line recap. Conflict-with-locked-decision rollback (atomic FAIL if any proposal contradicts canonical decisions). Three explicit no-op cases. Does NOT replace ADR-0001; users can still re-run source commands in Agent mode. New regression scenario `evals/scenarios/23-approve-proposed-batch-persist.md`.

Across the fixup: 38 commands (was 37); 24 ADRs (was 23; added 0024); 23 eval scenarios (was 21; added 22 and 23). ACTIVE operating mode (option C from the planning interview) deferred; re-evaluate after `/approve-proposed` sees real-world use.

## Wave 2.7: Proactive defect-class detection (CLOSED 2026-05-24; ships in v0.2.x)

**Goal**: internalize Greptile-style codebase-consistency review as a portable Fhorja command that works in any repo (including those without Greptile licensing). Designed after reverse-engineering 4 real Greptile findings on a production PR, grounded in Bacchelli and Bird 2013, OWASP API Security Top 10 2023, CWE Top 25 2025, Google code review checklist, and Greptile 2026 benchmarks. 7 research rounds (W1-W7) preceded the 7 implementation slices.

- [x] **`repo-consistency-sweep` command**: proactive defect-class detection against curated `wos/bug-classes/` library. Runs after `review-hard`, before `pr-package` (Phase 6 step 15). Dispatches parallel analysis per matching bug class, aggregates findings with P0/P1/P2 severity and HIGH/MEDIUM/LOW confidence, writes SWEEP snapshots with triage placeholders.
- [x] **`apply-sweep-triage` command**: persists apply/decline/discuss triage from SWEEP snapshots into project-level `REVIEW_PREFERENCES.md` with file-hash-based suppression that ages out on change.
- [x] **Bug-class library** (`wos/bug-classes/`): 46 templates across 15 categories covering 10 quality pillars (docs, security, review quality, code patterns, observability, testing, performance, accessibility, resilience, data integrity). 4 templates calibrated against real Greptile findings. Shared rule fragments for multi-perspective analysis (Basili 1996), reversibility checks, and multi-tenant invariants. Expanded in subsequent commits with security (hardcoded-secret, N+1, dead code, resource cleanup), accessibility (alt-text, ARIA, keyboard, focus management, form errors), resilience (retry, timeout, async error, graceful degradation), data integrity (input validation, schema compat, idempotency, timezone), observability (structured logging, business metrics), testing (over-mocked, flaky signals), and performance (sync blocking I/O, missing pagination) classes.
- [x] **Meta-learning loop**: `pr-feedback-ingest` updated to emit candidate templates for findings not matched by any existing bug class, growing the library from real evidence.
- [x] **Lifecycle integration**: the spec `## Default workflow` Phase 6, `## Command roles`, `## Command categories` updated. `sync-task-state` preserves SWEEP pointer lines.
- [x] **Benchmark gate**: 4/4 Greptile findings matched (100% recall, 0 FP) with calibration bias noted. True generalization requires 5-10 additional PRs.

Across the wave: 40 commands (was 38); `wos/bug-classes/` is a new Fhorja primitive; `templates/REVIEW_PREFERENCES.template.md` added.

## Wave 2.8: WOS-UI design system governance subsystem (CLOSED 2026-05-25; ships in v0.2.x)

**Goal**: codify the rn-reference-app design-system-first workflow into a portable Fhorja subsystem. 6 epics, grounded in Material 3, Shopify Polaris, Radix, W3C DTCG, Brad Frost atomic design, Sparkbox maturity model, and the rn-reference-app project as proof-of-concept (62 components, 120 screens, 10 foundations).

**Status (2026-06-05):** First lived test completed -- see Phase 6 below.

- [x] **Epic 1: Conventions + templates**: `wos/design-system-conventions.md` (lazy-loaded spec topic; atomic hierarchy, token naming, W3C DTCG, states taxonomy, Figma-first derivation, traceability, a11y floor, versioning) + 7 templates (FOUNDATION_SPEC, COMPONENT_SPEC 15 sections, JOURNEY_SPEC, SCREEN_SPEC, PATTERN_SPEC, OPEN_QUESTIONS, TOKEN_FILE.json W3C DTCG + STYLE_DICTIONARY_CONFIG).
- [x] **Epic 2: Figma extraction commands**: `design-bootstrap` (Figma MCP to scaffolded foundation docs + inventories), `component-spec` (15-section spec from Figma component), `screen-spec` (12-section spec from Figma frame).
- [x] **Epic 3: Documentation commands**: `journey-map` (user journey across 3+ screens), `pattern-doc` (reusable UX patterns, Polaris-inspired).
- [x] **Epic 4: Token pipeline**: W3C DTCG JSON template + Style Dictionary integration pattern documentation.
- [x] **Epic 5: Governance**: 8 design-system bug-class templates (custom-component-when-ds-exists, hardcoded-color-instead-of-token, missing-component-states, spacing-magic-number, storybook-story-missing, component-missing-a11y-props, component-changelog-missing, token-format-not-dtcg) + `design-spec-review` (10-check implementation-vs-spec) + `foundation-audit` (code-docs-Figma 3-way token drift).
- [x] **Epic 6: Lifecycle integration**: the spec Command categories, Command roles, Default workflow, COMMAND_PROMPT_STUBS, all doc counts synchronized.

Across the wave: 49 commands (was 42); 58 bug-class templates (was 50); 17 categories (was 16); 12 quality pillars (was 11); 10 lazy-loaded spec topics (was 9; was 8); 13 templates (was 8). WOS-UI is a new subsystem covering design system bootstrap, documentation, governance, and review.

Current catalog totals are tracked in CHANGELOG.md and the EOD snapshot under _internal/; the Wave 2.8 numbers above are frozen at close (2026-05-25).

## Wave 3: Expansion (v0.3.x and beyond, target: 6+ months after v0.1.0)

**Goal**: extend the workflow to use cases beyond the current scope.

- [x] Eval harness for regression testing of command outputs at [`evals/`](./evals/): 5 starter scenarios (project bootstrap to first task; multi-repo task setup; slice execution and closure scope discipline; pr-package diff grounding; state-reconcile minimum patch). Manual harness designed to run in any AI tool the workflow targets; helper script at `evals/scripts/run-evals.sh` walks through scenarios. Cadence: weekly (1-2 scenarios) and per release (full pass). Will grow toward Anthropic's recommended 20-50 cases as new scenarios are authored.
- [x] Operating modes: minimal (XS tasks), strict (high-risk tasks), teaching (onboarding new users) at the spec `## Operating modes`. Each mode is orthogonal to editor mode and output depth; declared at task-init time and recorded in `TASK_STATE.md` `## Resume notes`. Minimal trims ceremony for LOW-risk work; strict mandates `invariants-and-non-goals`, `test-strategy`, and `review-hard` for high-risk work; teaching prefaces responses with phase explanations and routes via `workflow-guide`.
- [x] `incident-triage` command for debugging real production issues with urgency (canonical Debug-mode entry point; classifies failure into 6 types, recommends fix size as one of 4 explicit sizes, validates against locked decisions and invariants, defends `BLOCKING_PROD` + `HOTFIX` paths against unnecessary ceremony with explicit "Why this skip is safe" justification)
- [x] `external-research` command at [`commands/external-research.md`](./commands/external-research.md): synthesizes multiple external sources into a task-scoped `EXTERNAL_RESEARCH.md` grounded in `REFERENCES.md` entries. Each source is captured first via `capture-references` (project-level memory; deduplicated by URL); this command produces the synthesis with comparative analysis and a model recommendation visually separated from the source-grounded findings. Routes to `decision-interview` (when synthesis surfaces new questions) or `implementation-plan` (when synthesis closes the question). Read-only over external content; never invents claims. Added to category `Discovery and scoping`.
- [x] `delivery-asset` command at [`commands/delivery-asset.md`](./commands/delivery-asset.md): generates outward-facing artifacts (executive summaries, release notes, slack/email posts, demo scripts, blog drafts) per audience and per format. Distinct from `pr-package` (GitHub-scoped) and `team-update` (channel-portable but team-internal). Filename convention `DELIVERY_ASSET_<format>_<audience>.md`. Grounded in `TASK_STATE.md` / `DECISIONS.md` / `IMPLEMENTATION_PLAN.md` / `PR_PACKAGE.md`; never leaks workflow paths into the public surface. Added to category `Delivery and communication`.
- [x] `db-context-supabase` command: opt-in, MCP-backed Supabase schema snapshot scoped per task; foundation for future provider-specific `db-context-*` commands (postgres, bigquery, mysql) added on demand
- [x] Multi-product-workspace support v1 (tasks that touch frontend and backend simultaneously): opt-in `## Repositories` section in SOURCE_OF_TRUTH.md; 3 commands multi-repo-aware (`code-locate`, `impact-analysis`, `pr-package`); 7 commands deferred to v2; full schema and decisions in the spec `## Multi-repo support (v1)`
- [ ] Multi-product-workspace support v2: expand multi-repo awareness to the 7 deferred commands (`targeted-questions`, `implement-approved-slice`, `implement-slice-complement`, `slice-closure`, `where-we-at`, `pr-feedback-ingest`, `post-review-pivot`); contingent on real-use friction signals from v1
- [x] Refactor-specific flow with mandatory `TEST_STRATEGY.md` at the spec `## Recommended workflows by task shape` :: `### Refactor task (behavior preservation under structural change)`: 8-step flow that upgrades `test-strategy` from "if needed" to **mandatory** and `review-hard` from "if useful" to **expected**. Includes the explicit stop-rule: if existing coverage cannot anchor the refactor safely, the refactor is preceded by a separate task that adds the missing test infrastructure (refactoring without behavior coverage is a known anti-pattern, not a permitted shortcut).
- [x] Test-only task short flow at the spec `## Recommended workflows by task shape` :: `### Test-only task (test additions or improvements; no behavior change)`: 4-step flow (task-init :: mandatory test-strategy :: implement-approved-slice in Agent :: pr-package). Includes the explicit re-classification rule: if a test discovers a real bug while being written, the task is no longer test-only and is re-routed to small-disciplined or incident-triage.

## Phase 4: Stabilization (target: ongoing after the public release)

- [ ] API stability toward a mature v1 contract (command output shape and `TASK_STATE.md` schema)
- [ ] Community growth: issues, discussions, and outside contributions under MIT + DCO
- [ ] Broader editor coverage validated against the open Agent Skills standard

## Phase 5: SaaS layer 2 (exploratory, no commitment)

A separate hosted service that builds on top of the open-source workflow. Concept under exploration:

- Receive a project zip or Git repo
- Run task-init and discovery commands automatically
- Suggest stack, scaffold initial code
- Run tests and validation in sandboxed environment
- Generate downloadable result + integrate with the user's GitHub for the final commit

If pursued, the SaaS would build on the MIT-licensed workflow as its Layer 1 and offer functionality the markdown workflow alone cannot provide (server-side execution, sandboxing, persistence).

This is exploratory and depends on adoption signals from Phases 3-4.

## Phase 6 (Wave 2.8 design subsystem)

**Status (2026-06-05):** First lived test completed. screen-spec-fleet ran on the client driver-app (5 Figma URLs, 26 parallel agents, 1.3M subagent tokens, 12min wall-clock). Produced 5 SCREEN_SPECs, ATOM_INVENTORY (53 atoms), routes (24), SCREEN_MAP, JOURNEY_AND_OPEN_QUESTIONS. Foundations seeded via extract-foundations-from-screens. Phase 6 milestone reached.

This phase tracks the maturation of the Wave 2.8 WOS-UI design system governance subsystem from documented capability to lived-tested workflow. The subsystem combines Workflow commands (screen-spec, component-spec, design-bootstrap, journey-map, pattern-doc, design-spec-review, foundation-audit) with Figma MCP tools (get_design_context, get_screenshot, get_variable_defs) to extract structured design documentation directly from Figma frames.

The first lived test on the client driver-app validated the parallel-dispatch model (26 subagents fanned out across 5 Figma URLs), the atom-inventory aggregation pattern (53 atoms catalogued across 5 screens), and the foundations-seed flow (extract-foundations-from-screens consumed the SCREEN_SPECs and produced canonical token candidates).

## How to influence the roadmap

- For specific feature requests, open an issue using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).
- For broader direction discussions, open a GitHub Discussion.

The maintainer makes final decisions on roadmap priorities. There is no SLA on changes or fulfillment of requested features.


## Phase 7: Multi-agent maturity (post-2026-06-05)

**Stage:** Multi-agent maturity (empirical baseline 2026-06-05: 14 batches / 58+ agents dispatched, 100% success on the screen-spec-fleet baseline run).

**Status:** open for next session.

This phase takes the empirical baseline produced by the Phase 6 lived test (the client driver-app screen-spec-fleet: 26 parallel agents at 100% success, plus the additional batches that aggregated to 14 batches end-of-day) and hardens it into a repeatable, monitorable, multi-tool, cost-aware multi-agent capability. Phase 6 proved the parallel-dispatch model and atom-inventory aggregation pattern work in real product context; Phase 7 closes the residual ADR-0038 PARTIAL compliance gaps, promotes the remaining K.8 personas through Path B (ADR-0036), and gives the operator production-grade telemetry, retry/escalation, and cost guidance for routine use.

**Objectives:**

- Promote the 3 remaining K.8 L2 personas (jtbd-switch-interviewer, migration-safety-steward, color-contrast-architect) to L3 via Path B (ADR-0036): execute Path B in sequence per persona; record the promotion artifacts under projects/bmazurok__my-work-tasks/active/, and update PERSONAS index on each promotion. Exit criterion is 100% K.8 personas at L3.
- Fix fleet command ADR-0038 PARTIAL compliance issues per _internal/fleet-audits/RECOMMENDED-FIXES.md (scope: atom-audit-fleet, external-research-fleet, verify-against-rubric-fleet, screen-spec-fleet, task-init-fleet -- all structurally ADR-0038 compliant, PENDING lived runs): walk the recommended-fixes list, land each fix as its own slice with regression coverage, and re-run the audit so every fleet command lands at FULL compliance (not PARTIAL).
- Production-grade monitoring: integrate _internal/scripts/monitor-fleet-progress.sh with retry and escalation hooks so a stuck or timed-out subagent triggers a defined recovery path (retry once :: escalate to operator) instead of silently stalling a batch.
- Multi-tool support: today the fleet path is Claude Code only. Investigate equivalent Workflow primitives in Cursor and OpenAI Codex (sub-agent dispatch, parallel run isolation, structured-output return path), document the gap per tool, and decide which primitives to wrap behind a tool-neutral adapter vs. leave tool-specific.
- Quantitative cost models per batch size: extend ADR-0039 with token and dollar estimates per batch size (small / medium / large) grounded in the 14-batch end-of-day dataset, so operators can pick a batch size with a real cost expectation instead of a qualitative guess. [Open follow-up: confirm whether ADR-0040 extends ADR-0039 with the cost/telemetry model; if yes, wire it in here.]

**Dependencies on Phase 6:** Phase 6's lived test is the empirical baseline this phase builds on. The 14-batch end-of-day dispatch set, anchored on the 26-agent screen-spec-fleet baseline at 100% success, plus the client screen-spec-fleet artifact set (SCREEN_SPECs, ATOM_INVENTORY, JOURNEY_AND_OPEN_QUESTIONS, foundations seed), are what ADR-0038 (fleet compliance) and ADR-0039 (cost model) codify; without that baseline neither ADR has the numbers Phase 7 needs to extend.

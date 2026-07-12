---
name: test-strategy
description: Define the smallest set of meaningful tests that protects behavior and reduces regression risk for the active task, then persist as TEST_STRATEGY.md plus a TASK_STATE.md update. Avoids forcing a strategy artifact when it adds no material signal. Detects a Godot 2D-mobile target and routes to GUT or gdUnit4 headless, treating the godot-runtime-verify press-play gate as complementary to the headless suite. Use when the task has a valid implementation plan or a clearly understood behavior under change, the change affects important behavior or contracts or data flow or runtime risk or regression risk, or test choices should be decided before or alongside implementation. Do not use when the task is still too unclear to know what behavior is changing, the current need is broad discovery or contract resolution, or the task is too small to justify a dedicated test strategy artifact.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2800
  suggested-model: claude-sonnet-4-6
---
# test-strategy

Act as a senior engineer defining a risk-based test strategy for the active engineering task.

Goal:
Define the smallest set of meaningful tests that protects behavior and reduces regression risk, then persist the result in the task repository as explicit, reviewable updates (avoid forcing a strategy artifact when it adds no material signal).

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
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- IMPACT_ANALYSIS.md, if available
- relevant real codebase context
- existing test files, if available
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update (only if materially changed):
- TEST_STRATEGY.md
- TASK_STATE.md

Operating rules:
- Do not write tests yet.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Before producing output, verify `test-strategy` is still justified: if risk is low and validation is already clear enough in `IMPLEMENTATION_PLAN.md`, prefer skipping this artifact.
- If `TEST_STRATEGY.md` already matches the plan and risk profile with no material gap, do not rewrite it for style; return a no-op and route forward.
- No-op rule for artifacts:
  - If `TEST_STRATEGY.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Start from behavior, contracts, invariants, and failure modes.
- Distinguish clearly between:
  - critical scenarios
  - realistic regression paths
  - edge cases worth covering
  - low-value tests to avoid
- Recommend the right level for each scenario:
  - unit
  - integration
  - end-to-end
- Explicitly call out when idempotency, retries, migrations, concurrency, conflict resolution and convergence (multi-writer or local-first sync: two replicas edit offline then sync and MUST converge with no data loss; prefer property-based tests for merge invariants), partial failure, or backward compatibility should be tested.
- Route QA tooling by detected stack. Read the consuming repo's stack from `IMPACT_ANALYSIS.md`, or detect it from manifests (pyproject.toml or a pytest dev-dep -> pytest, plus Hypothesis where invariants exist; package.json with react/react-dom -> React Testing Library at the component layer; a `@playwright/test` config -> Playwright for web E2E; a react-native dependency or metro config -> Detox for mobile E2E; a `project.godot` file or `.gd` scripts -> GUT (GDScript-default) or gdUnit4 (GDScript or C#) run headless from the Godot CLI with a deterministic exit-code gate, plus a scene runner for touch integration tests, per `wos/godot-testing-and-ci.md`; a plain Node.js or TypeScript project with no framework -> the built-in `node --test` runner (or vitest when already a dev-dep), tsc --noEmit as the type gate; a data pipeline -> the data-quality layer composes with the code layer: a `dbt_project.yml` -> dbt schema and data tests, a `great_expectations/` or `gx/` config -> Great Expectations checkpoints, `pandera` in dependencies -> pandera schema tests, all alongside pytest for the Python glue), and name the canonical runner, assertion library, and coverage tool per detected ecosystem instead of leaving them to context. Stay stack-agnostic in mechanism (detect-and-route, never a frozen hardcoded matrix); when the stack is unknown, say so and ask rather than guessing. The named gate commands feed the consuming repo's ADR-0048 deterministic gate.
- For a Godot 2D-mobile target, treat headless automated tests (GUT or gdUnit4) and the interactive `godot-runtime-verify` press-play gate as complementary, not substitutes: a headless runner has no GPU and cannot judge feel, rendering, or on-device touch. Route scripted assertions to the headless suite and subjective, GPU-real, on-device checks to `godot-runtime-verify`. See `wos/godot-testing-and-ci.md`.
- For a React Native / Expo target, treat the JS-level suite (Jest plus React Native Testing Library at the component layer, Detox for E2E) and the `app-runtime-verify` runtime gate as complementary, not substitutes: a native crash class (a Fabric mounting crash, a navigation-teardown crash) fires only on a real device or emulator run and is judged from the native log, which the JS-level runner never sees. Route scripted assertions to the JS suite and on-device runtime behavior to `app-runtime-verify` (ADR-0087). See `wos/rn-expo-runtime-evidence.md`.
- Say when a test would only validate implementation details instead of behavior.
- Keep the strategy lean and high signal.
- **Consumption contract (F-6 fold, ADR-0089).** A produced `TEST_STRATEGY.md` is a commitment, not a memo: by task closure every `critical` and `regression` scenario row MUST map to a real test file (name the expected path per the routed runner's convention in the strategy itself) OR carry a recorded one-line waiver stating why that row is deliberately deferred. `task-close` checks this mapping and blocks on silent orphans. A waiver is legal (a POC may defer its suite on the record); silence is not: the dogfood behind this rule wrote a GUT/gdUnit4 strategy that no test ever consumed while throwaway probes carried all the protection.
- If a dedicated TEST_STRATEGY.md is unnecessary, say so explicitly and update TASK_STATE.md accordingly instead of forcing the file.
- If skipping, record the validation approach directly in `TASK_STATE.md` (only if that is a material improvement over the current state).

TEST_STRATEGY.md must include:
1. Behavior under change
2. Main regression risks
3. Recommended scenarios
4. Suggested test level per scenario
5. Stack-detected QA tooling: the canonical runner, assertion library, and coverage tool per detected ecosystem (omit when the change has no stack-specific test surface)
6. Tests to avoid
7. Gaps in current test coverage
8. Recommended next step
9. Recommended next command
10. Recommended editor mode
11. Why that is the correct next step

TASK_STATE.md update must reflect:
- risks to watch (`## Risks to watch`, co-writer per `wos/substrate-peers.md`)
- validation approach (recorded inside `## Current status` or the `## Recommended next step` rationale; TASK_STATE.md has no dedicated validation-approach heading, the strategy detail lives in TEST_STRATEGY.md itself)
- recommended next step (`## Recommended next step`)
- blockers, if test strategy exposed any (`## Open questions / blockers`)

The named test files are typically authored via `implement-slice-complement` when they are a mechanical translation of already-locked behavior with no new design work, or via another `implement-approved-slice` round when the test scenarios require new design decisions; this command stops at the strategy document itself ("Do not write tests yet" above).

Required output:
1. Whether TEST_STRATEGY.md should be created, updated, or skipped
2. Exact content for TEST_STRATEGY.md if applicable (full document if create/update; otherwise a short NO_OP note or explicit SKIP rationale)
3. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
4. Recommended next step
5. Recommended next command
6. Recommended editor mode
7. Why this is the correct next step
8. What should explicitly not be done yet

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
- Output opens with an explicit verdict: one of `CREATE TEST_STRATEGY.md`, `UPDATE TEST_STRATEGY.md`, or `SKIP TEST_STRATEGY.md`. Output without an explicit verdict is invalid; `SKIP` requires a one-line rationale and migration of validation notes into `TASK_STATE.md`.
- Each scenario is classified explicitly as `critical` / `regression` / `edge` / `avoid` and has an intentional test level (unit/integration/e2e) plus a reason. A flat list of scenarios without classification is invalid output.
- Explicitly lists low-value tests to avoid (coverage theater).
- `Gaps in current test coverage` is addressed even when the verdict is `SKIP`: when skipping, gaps are recorded in the `TASK_STATE.md` update block instead of the artifact.
- If skipping `TEST_STRATEGY.md`, the skip rationale is explicit and `TASK_STATE` validation notes are `PROPOSED` as needed.
- Consumption contract (F-6, ADR-0089): the strategy names the expected test-file path per `critical` and `regression` row, so the `task-close` consumption floor has something concrete to check; rows a POC defers carry their waiver line in the artifact itself.
- Godot/GDScript stderr check (F-6, dogfood-wave 2026-07-11): for a Godot target, a probe or test run authored against this strategy is not `CLEAN` unless stderr was checked separately from the pass/fail count; a passing count with a pushed `SCRIPT_ERROR` in the same run is not a pass (see `wos/godot-testing-and-ci.md` "Common test defects"). Name this check explicitly wherever the strategy names a Godot test file's expected run command.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the strategy content (or after the SKIP rationale) without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Favor fewer, stronger tests over broad but shallow coverage.

<!-- cache-breakpoint -->

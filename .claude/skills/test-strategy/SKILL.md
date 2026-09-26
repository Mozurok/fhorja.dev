---
name: test-strategy
description: |-
  Define the smallest set of meaningful tests that protects behavior and reduces regression risk for the active task, then persist as TEST_STRATEGY.md plus a TASK_STATE.md update. Avoids forcing the artifact when it adds no material signal. Detects a Godot or Unity target and routes to the matching headless runner, treating the runtime gate as complementary to the headless suite. Use when the change affects important behavior, contracts, data flow, or regression risk, or when scope reads as auth, biometric, or runtime-risk with no strategy on file, even if small. Do not use when it is still unclear what behavior is changing, when the need is broad discovery or contract resolution, or when the task is too small to justify the artifact.
metadata:
  category: "planning-and-validation"
  primary-cursor-mode: "Plan"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Output opens with an explicit verdict: one of `CREATE TEST_STRATEGY.md`, `UPDATE TEST_STRATEGY.md`, or `SKIP TEST_STRATEGY.md`. Ou...


Act as a senior engineer defining a risk-based test strategy for the active engineering task.

Goal:
Define the smallest set of meaningful tests that protects behavior and reduces regression risk, then persist the result in the task repository as explicit, reviewable updates (avoid forcing a strategy artifact when it adds no material signal).

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

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
- IMPLEMENTATION_PLAN.md (only the `## Validation expectations` H2, as its owner per wos/substrate-peers.md)

Operating rules:
- Do not write tests yet.
- **K.2 scope note (P2-8, dogfood-wave-2 2026-07-12):** this command's own artifact (`TEST_STRATEGY.md`) is outside the K.2 11-file substrate scope (`commands/_shared/substrate-write-protocol.md`) and needs no transaction header. Update `TASK_STATE.md`'s `## Last completed step` afterward as ordinary operator hygiene.
- **Validation-expectations sync (owner per `wos/substrate-peers.md`):** when `TEST_STRATEGY.md` is created or updated, update or cross-link the plan's `## Validation expectations` H2 in `IMPLEMENTATION_PLAN.md` so the two artifacts do not diverge. That write is a K.2 substrate write: it carries the transaction header and the JSONL line per `commands/_shared/substrate-write-protocol.md`.
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
- **Authentication/authorization boundary on an inbound external integration (ADR-0108).** WHEN the change adds or touches an inbound webhook, callback, or API-key-authenticated endpoint consumed by an external vendor, name at least one scenario that exercises the REAL auth/authz code path (the actual header-parsing and validation logic) rather than a test harness that injects post-auth state directly (`req.auth`, `req.user`, decoded claims). If the existing or planned test harness stubs past that boundary by design (a reasonable choice for keeping business-logic tests fast), say so explicitly as a named gap in "Gaps in current test coverage" rather than letting the suite's green status imply the auth contract itself is covered. This exists because a route-test harness stubbing `req.auth` directly gave 44 passing tests zero coverage of the actual vendor auth format, and the gap shipped to production undetected (tms-webhook-integration dogfood, 2026-07-15).
- Route QA tooling by detected stack. Read the consuming repo's stack from `IMPACT_ANALYSIS.md`, or detect it from manifests (pyproject.toml or a pytest dev-dep -> pytest, plus Hypothesis where invariants exist; package.json with react/react-dom -> React Testing Library at the component layer; a `@playwright/test` config -> Playwright for web E2E; a react-native dependency or metro config -> Detox for mobile E2E; a `project.godot` file or `.gd` scripts -> GUT (GDScript-default) or gdUnit4 (GDScript or C#) run headless from the Godot CLI with a deterministic exit-code gate, plus a scene runner for touch integration tests, per `wos/godot-testing-and-ci.md`; a `ProjectSettings/ProjectVersion.txt` or an `Assets/` tree with `.asmdef` files -> the Unity Test Framework, split Edit mode (no coroutines) versus Play mode (`[UnityTest]` runs as a coroutine), run headless via `-runTests -batchmode -projectPath <p> -testResults <f> -testPlatform <t>`, with the gate asserting on the `-testResults` file and NOT on the exit code, whose contract Unity does not document, per `wos/unity-testing-and-ci.md`; a plain Node.js or TypeScript project with no framework -> the built-in `node --test` runner (or vitest when already a dev-dep), `tsc --noEmit` as the type gate only when a `tsconfig.json` or a typescript dev-dependency exists (plain JavaScript gets no type gate; optionally `node --check` as a syntax gate); a data pipeline -> the data-quality layer composes with the code layer: a `dbt_project.yml` -> dbt schema and data tests, a `great_expectations/` or `gx/` config -> Great Expectations checkpoints, `pandera` in dependencies -> pandera schema tests, all alongside pytest for the Python glue), and name the canonical runner, assertion library, and coverage tool per detected ecosystem instead of leaving them to context. Stay stack-agnostic in mechanism (detect-and-route, never a frozen hardcoded matrix); when the stack is unknown, say so and ask rather than guessing. The named gate commands feed the consuming repo's ADR-0048 deterministic gate.
- **For a Unity target (ADR-0130), state three things the analogy to another stack would omit.** First, a Unity test is a compile unit, not a file: tests "must be in a test assembly, which is any assembly that references NUnit", whose `.asmdef` references `nunit.framework.dll`, `UnityEngine.TestRunner`, and `UnityEditor.TestRunner`. A test file written into an ordinary folder never runs and nothing errors, so the suite reports green on a test that was never collected; name the target assembly per scenario and say whether it already exists. Second, the gate reads the `-testResults` file, because the Unity manual page documenting the test CLI states nothing about exit codes; a gate built on the exit code alone can report green on a failed suite. This is the inverse of the Godot contract, so do not carry that assumption across. Third, CI license activation is a precondition, not an afterthought: Unity needs an activated license on every machine including ephemeral runners, and without it every job fails before a test runs. Treat Play mode tests and the `app-runtime-verify` Unity adapter as complementary for the same reason the Godot pair is complementary. See `wos/unity-testing-and-ci.md`.
- For a Godot target in either dimension, treat headless automated tests (GUT or gdUnit4) and the interactive `godot-runtime-verify` press-play gate as complementary, not substitutes: a headless runner has no GPU and cannot judge feel, rendering, or on-device touch. Route scripted assertions to the headless suite and subjective, GPU-real, on-device checks to `godot-runtime-verify`. See `wos/godot-testing-and-ci.md`.
- For a React Native / Expo target, treat the JS-level suite (Jest plus React Native Testing Library at the component layer, Detox for E2E) and the `app-runtime-verify` runtime gate as complementary, not substitutes: a native crash class (a Fabric mounting crash, a navigation-teardown crash) fires only on a real device or emulator run and is judged from the native log, which the JS-level runner never sees. Route scripted assertions to the JS suite and on-device runtime behavior to `app-runtime-verify` (ADR-0087). See `wos/rn-expo-runtime-evidence.md`.
- Say when a test would only validate implementation details instead of behavior.
- Keep the strategy lean and high signal.
- **Consumption contract (F-6 fold, ADR-0089).** A produced `TEST_STRATEGY.md` is a commitment, not a memo: by task closure every `critical` and `regression` scenario row MUST map to a real test file (name the expected path per the routed runner's convention in the strategy itself) OR carry a recorded one-line waiver stating why that row is deliberately deferred. `task-close` checks this mapping and blocks on silent orphans. A waiver is legal (a POC may defer its suite on the record); silence is not: the dogfood behind this rule wrote a GUT/gdUnit4 strategy that no test ever consumed while throwaway probes carried all the protection.
- **Falsifiability evidence for critical rows (mobile dogfood 2026-07-29, extends the consumption contract above).** A `critical` row maps to a test that was SEEN TO FAIL for the right reason, not merely to a test file that exists. Two accepted forms, cheapest first: (1) the ADR-0063 red step, the test seen failing before the code landed, which `implement-approved-slice` already produces in TDD mode; or (2) one recorded mutation on a line the slice wrote, with the suite seen failing and then passing on restore. A row whose only evidence is "the file exists and the suite is green" is unreconciled, not Met. The failure class this closes is `wos/bug-classes/test-that-tests-nothing.md`: on the source run a hook-order invariant was pinned against a locally re-declared copy of the component, so swapping the two real hooks left 1,815 tests green and the row marked Met while the invariant it claimed to protect was the cause of the run's blocking defect. This is a per-row evidence rule, NOT a default-on mutation runner: mutate the lines a `critical` row names, never the suite at large.
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

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- Output opens with an explicit verdict: one of `CREATE TEST_STRATEGY.md`, `UPDATE TEST_STRATEGY.md`, or `SKIP TEST_STRATEGY.md`. Output without an explicit verdict is invalid; `SKIP` requires a one-line rationale and migration of validation notes into `TASK_STATE.md`.
- Each scenario is classified explicitly as `critical` / `regression` / `edge` / `avoid` and has an intentional test level (unit/integration/e2e) plus a reason. A flat list of scenarios without classification is invalid output.
- Explicitly lists low-value tests to avoid (coverage theater).
- `Gaps in current test coverage` is addressed even when the verdict is `SKIP`: when skipping, gaps are recorded in the `TASK_STATE.md` update block instead of the artifact.
- If skipping `TEST_STRATEGY.md`, the skip rationale is explicit and `TASK_STATE` validation notes are `PROPOSED` as needed.
- Consumption contract (F-6, ADR-0089): the strategy names the expected test-file path per `critical` and `regression` row, so the `task-close` consumption floor has something concrete to check; rows a POC defers carry their waiver line in the artifact itself. Each `critical` row also names which falsifiability evidence will settle it (red step or mutation), so "Met" is provable rather than asserted.
- Godot/GDScript stderr check (F-6, dogfood-wave 2026-07-11): for a Godot target, a probe or test run authored against this strategy is not `CLEAN` unless stderr was checked separately from the pass/fail count; a passing count with a pushed `SCRIPT_ERROR` in the same run is not a pass (see `wos/godot-testing-and-ci.md` "Common test defects"). Name this check explicitly wherever the strategy names a Godot test file's expected run command.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the strategy content (or after the SKIP rationale) without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Favor fewer, stronger tests over broad but shallow coverage.

---
name: implement-approved-slice
description: Implement only the approved slice with minimal, explicit, review-friendly changes, then persist execution evidence in slice notes and TASK_STATE.md. The single official execution path of the workflow. Supports an opt-in test-first (TDD) mode, enabled per slice or via --tdd, that writes the failing test before the code (ADR-0063). Use when the task has a valid IMPLEMENTATION_PLAN.md, the current slice is explicitly defined and approved, correctness-critical ambiguity is already resolved, and the files in scope are known well enough to edit safely. Do not use when the task is still in discovery or contract refinement or planning, when unresolved ambiguity still affects correctness, when the slice boundary is still unclear, when the next step is only to sync task memory or close the slice (use sync-task-state or slice-closure), or when the remaining work is a narrow micro-delta anchored to an already-executed slice with the same intent (use implement-slice-complement).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 3600
  suggested-model: claude-sonnet-4-6
---
# implement-approved-slice

Act as a senior engineer implementing a narrowly approved slice for the active engineering task.

Goal:
Implement only the approved slice with minimal, explicit, review-friendly changes, then persist the execution result in the task repository as explicit, reviewable execution notes (avoid rewriting slice memory without material change).

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
- TEST_STRATEGY.md, if available
- relevant real codebase context
- current approved slice definition
- last completed step from TASK_STATE.md (command + summary)
- optional: `--tdd` to run this slice test-first (red then green) when it has testable behavior and a test runner is present, per ADR-0063 (also enabled per-slice via `Test-first: yes` in the plan)

Task repository files to create or update (only if materially changed):
- relevant SLICES/<NN>_<slice-slug>.md when the slice is material enough to track explicitly
- TASK_STATE.md only if explicitly requested; otherwise prefer `/sync-task-state` after execution to avoid churn
- do not update PR_PACKAGE.md here

Operating rules:
- Read **work complexity** from `IMPLEMENTATION_PLAN.md` (current slice), `TASK_STATE.md`, or the slice file; if they disagree, prefer the **plan** unless `TASK_STATE.md` was explicitly updated later. Do not name model SKUs; restate complexity once at the start of the work summary when helpful.
- **Multi-repo (G4 v2, per D.4 of Fhorja improvement plan 2026-06-03):** when `SOURCE_OF_TRUTH.md` contains a `## Repositories` section, produce per-repo subsections in the execution summary (files touched, validation evidence, typecheck/build status). Each repo's section is independently verifiable. When the section is absent, fall back to single-repo single-list behavior (current default).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Implement only the approved slice.
- Before executing, verify the slice is not already completed per plan/slice artifacts and `TASK_STATE.md` last completed step.
- If there is no remaining approved work for this slice (no material code delta expected), do not fake progress; return a no-op and route to `slice-closure` or `/sync-task-state` as appropriate.
- No-op rule for task-memory artifacts:
  - If slice documentation would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Do not expand scope without explicit approval.
- No orthogonal changes: do not introduce unrelated abstractions, refactors, or cleanup. The slice diff stays inside the declared file scope; record any tempting orthogonal change (a drive-by rename, an adjacent refactor, a config tidy) as a separate follow-up rather than bundling it. Within-scope tidying is still allowed. A file mechanically required for the declared scope to function (a package marker like `__init__.py`, a required index or barrel re-export) counts as within scope: create it and name it explicitly in the files-touched list rather than treating it as a scope violation or deferring it upstream.
- Preserve external behavior unless the approved slice explicitly changes it.
- Follow existing local conventions and patterns.
- Before making changes, restate:
  - exact approved scope
  - assumptions that still matter
  - files expected to change
- If missing context or ambiguity could affect correctness, stop and recommend the correct prior command instead of guessing.
- Prefer simple, explicit code over cleverness.
- Honor the YAGNI restraint ladder the plan applied (exist, stdlib, native, installed dep, one line, minimum viable): implement the smallest thing that satisfies the slice's approved scope and `DECISIONS.md`, adding no abstraction, config, or dependency the slice does not require.
- **Optional deterministic gate (W-20, opt-in, in the CONSUMING repo):** the product repo may wire a Stop or PostToolUse hook that runs typecheck, lint, and changed-file tests and blocks until they pass (`templates/deterministic-gate-hook.template.md`; `scripts/typecheck-hook.sh` is a lighter non-blocking example). When such a gate is wired and passing, record "deterministic gate passed" as the Layer 1 evidence (per `wos/gate-conditions.md` and ADR-0048) instead of re-pasting each command's output; an unwired or failing gate falls back to the W-02 paste-the-command-and-output rule. The hook lives in the consuming repo, not this one.
- **Opt-in test-first mode (TDD, per ADR-0063).** This mode is OFF by default; the normal implement-then-validate flow is unchanged. Enable it per slice with `Test-first: yes` in that slice's `IMPLEMENTATION_PLAN.md` entry, or ad hoc with the `--tdd` input. When enabled for a slice that has testable behavior, follow the red-green order:
  1. Red. Write the failing test that encodes the slice's EARS exit criterion (ADR-0031) FIRST, before any production code. Run it and paste the RED output showing it fails for the intended reason (the not-yet-built behavior), not from a compile, import, or collection error. When the symbol under test does not exist yet, write the smallest stub first (the signature plus a `raise NotImplementedError` or equivalent) so the test fails on the assertion rather than an import or collection error; that stub is test scaffolding, not the slice's production logic, which still arrives in the green step.
  2. Green. Write the smallest production change that makes the test pass, staying inside the declared `Scope`. Run the test and paste the GREEN output.
  3. Refactor (optional). Tidy only within scope while the test stays green; no orthogonal changes (the no-orthogonal-changes rule still holds).
  The red-then-green transition IS the Layer 1 validation evidence for the behavior under test (paste both the failing and passing output); it satisfies, not supplements, the exit-criterion proof for that behavior.
  - Presence gate (ADR-0027): TDD mode needs a test runner already present in the consuming repo. When none exists, do NOT scaffold one here; say so and fall back to the normal flow (or route to `test-strategy`).
  - Not-applicable fallback: when the slice has no testable behavior (pure config, copy, or docs), TDD mode is a NO_OP for that slice; state that and proceed with the normal flow rather than inventing a hollow test.
  - Strict operating mode MAY recommend test-first for logic-bearing slices, but never forces it; the trigger stays opt-in so trivial slices pay no ceremony.
- **Security-critical platform-API grounding (pre-implementation, generalizes ADR-0043).** WHEN a slice's correctness depends on documented platform-API behavior for auth, crypto, or payment code, implement-approved-slice SHALL require a cited `stack-currency-check` or `capture-references` source before writing that code. This extends the reference-grounding execution gate already applied to the runtime locus in `incident-triage` to the pre-implementation research step for this class of slice.
- Keep the blast radius as small as possible. WHEN a slice is tagged HIGH-risk and touches navigation or routing files, implement-approved-slice SHALL require a `code-context-map` code-flow citation (ADR-0057) or a `code-locate` result as the blast-radius evidence before editing; a bare symbol-name grep does not satisfy this class of slice.
- Only update tests directly required by the approved slice.
- After changes, summarize:
  - exactly what changed
  - what was intentionally not changed
  - residual risks or follow-ups
- **Slice completion check:** at the end of each slice, verify exit criteria inline before emitting the handoff. Produce a short checklist (files created/modified, typecheck status, exit criteria met/not-met). For each validated exit criterion paste the verbatim command and its real output as proof; an exit criterion asserted without shown output is marked unverified, not met (this is distinct from the reference-grounding gate, which cites external contracts). When all exit criteria pass and work complexity is LOW or MEDIUM, the slice is considered closed inline; do not route to `slice-closure`. Route to `slice-closure` only when work complexity is HIGH or when exit criteria cannot be fully verified inline.
- **Verification divergence check.** WHEN a verification check's expected value differs from its actual value, implement-approved-slice SHALL require an explanation before treating the check as passed; do not silently accept a mismatched count or assertion as passing.
- **Commit-evidence floor (inline-close; ADR-0084, bounded deferral per ADR-0100, third home per ADR-0105).** A slice SHALL NOT close inline (the LOW/MEDIUM path) unless its work is committed (cite the commit reference in the slice notes) OR an explicit committing-waiver covering only genuinely discardable work (a deliberate throwaway, a spike whose value was the learning) is recorded. Real work awaiting a human commit, including an unattended session where git is unavailable or forbidden, is a BOUNDED DEFERRAL: record `deferred: pending human commit (<one-line context>)`, do NOT inline-close, and leave the slice open for the next human session. IF none of the three is present THEN do not inline-close; route to `branch-commit`.
- **Godot runtime-gate floor (inline-close; ADR-0085).** WHILE the active task is a Godot task (a `project.godot` or `.gd` codebase signature, or `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder) a slice whose declared scope touched a `.tscn` scene or a `.gd` script SHALL NOT close inline (the LOW/MEDIUM path above) unless a `godot-runtime-verify` PASS is recorded (in `GODOT_RUNTIME_VERIFY.md` or cited in the slice notes) OR an explicit one-line skip reason is in the slice notes. IF neither is present THEN do NOT inline-close; route to `godot-runtime-verify` first. This is the load-bearing home for the ADR-0085 enforcement: most LOW/MEDIUM Godot slices close here without reaching `slice-closure`, so a `slice-closure`-only check would miss them. It never fires on a non-Godot task or on a slice with no `.tscn`/`.gd` runtime surface, and it reads recorded evidence rather than running a scene. `godot-runtime-verify`'s gate decision is a real three-way verdict (PASS, FAIL, or BLOCKED), not a PASS-or-nothing binary: a real, evidence-backed BLOCKED verdict (the gate genuinely ran, some acceptance criteria were observed, nothing actively failed, but full evidence is not yet complete) is neither a PASS nor an unrecorded skip, and misrepresenting it as a "skip reason" would misstate what happened. Treat a cited BLOCKED verdict the same as an absent PASS: do not inline-close, and route to `where-we-at` or leave the slice not-ready-to-close with the BLOCKED evidence cited verbatim, worded distinctly from "never attempted."
- **Godot feel-verdict floor (inline-close; D-4, ADR-0089).** WHILE the active task is a Godot task (same signature detection as the runtime-gate floor above) a slice whose completion claim includes first-playable or feature-complete SHALL NOT close inline unless a recorded human feel verdict with `Overall: PASS` (a `## Feel verdict` block per `wos/godot-mobile-interaction-and-feel.md ## Feel verdict checklist (D-4 gate)`) is cited in the slice notes OR an explicit one-line skip reason is present. IF neither THEN do NOT inline-close; run the feel-verdict checklist first and route the resulting notes to `pr-feedback-ingest --playtest`. Machine gates (a `godot-runtime-verify` PASS, lint, headless probes) do not substitute for the human verdict; this floor extends the runtime-gate floor above, never replaces it. It never fires on a non-Godot task or on a slice making no first-playable or feature-complete claim. **Bounded-vs-permanent skip (ADR-0098):** a skip reason stating no human is available in this environment, ever, does NOT by itself satisfy this floor; the slice stays not-ready-to-close pending a human session. A genuine bounded deferral (a real human will review shortly, or a throwaway/no-runtime-surface slice) still satisfies it at the same low ceremony.
- **Experience-verdict floor (inline-close, generalized, ADR-0091).** WHEN the slice's deliverable carries the tag `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags), the slice SHALL NOT close inline unless a recorded human experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` cited in the slice notes) is present OR an explicit one-line skip reason is recorded. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict. IF the deliverable text plainly indicates user-facing content and no tag is present THEN treat the slice as tagged and flag the missing tag. IF neither is present THEN do NOT inline-close; route to the experience-verdict check first. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one. Same bounded-vs-permanent skip rule as the D-4 floor above applies here (ADR-0098): a "no human, ever" skip reason does not satisfy this floor.
- **Mobile-runtime-gate floor (inline-close, generalized, ADR-0106).** WHEN the slice or its task carries the tag `mobile-runtime-target`, OR matches the heuristic backstop (a `package.json` listing an `expo` or `react-native` dependency together with a generated `android/` or `ios/` folder), the slice SHALL NOT close inline unless a real `app-runtime-verify` PASS is cited (in the slice notes or a runtime-verify record) OR an explicit one-line skip reason is recorded. IF neither is present THEN do NOT inline-close; route to `app-runtime-verify` first. **Bounded-vs-permanent skip (ADR-0098):** a skip reason stating no device or emulator is ever available in this environment does NOT by itself satisfy this floor; the slice stays not-ready-to-close pending a session where a run is possible. A genuine bounded deferral (a specific later checkpoint, a real device session shortly, or a slice with no runtime-observable behavior) still satisfies it at the same low ceremony. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above. This mirrors the ADR-0085 Godot runtime-gate mechanism onto `app-runtime-verify` (ADR-0087): the 2026-07-14/15 rn-reference-app Face ID session shipped a fully broken biometric flow past `tsc --noEmit` and grep alone, with `app-runtime-verify` available but never required.
- **Entry-path probe floor (inline-close, ADR-0091).** WHEN the slice ships a deliverable tagged `new-user-facing-surface`, it SHALL NOT close inline unless one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) is cited in the slice notes OR an explicit one-line skip reason is recorded. IF neither is present THEN do NOT inline-close; route the operator to run the entry path once. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
- **Eval-threshold floor (inline-close, ADR-0104).** WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature this slice ships or changes, the slice SHALL NOT close inline unless the recorded eval OUTCOME (the score against the plan's pass threshold on its held-out set) is cited in the slice notes with the threshold met, OR an explicit one-line skip reason is recorded (bounded-vs-permanent per ADR-0098: a bounded deferral satisfies it, a permanent "the eval will never run" does not). An exit criterion worded around the harness mechanism ("the harness runs", "the eval executes") SHALL NOT substitute for the threshold outcome: a green harness execution with a failing score FAILS this floor. IF the outcome is absent THEN do NOT inline-close; run the eval per `AI_EVAL_PLAN.md` first.
- **Next-step routing (waves-aware and terminal-safe, per ADR-0042):** after the completion check, emit a REQUIRED `Next-wave decision:` line (one of `fleet`, `sequential`, `terminal`) with the wave-size check that justifies it; omitting it on a non-final slice is invalid output (the guard against silently defaulting to sequential when a parallelizable wave is ready). Then choose the handoff target in this order:
  - When the plan's remaining `## Execution waves` show a wave of size 2 or more whose slices declare `Scope` and `Depends-on`, route to `implement-fleet` for those parallel slices instead of hand-picking the next sequential slice.
  - When more sequential slices remain (the remainder is a chain), route to `implement-approved-slice` for the next slice.
  - When a plan-named follow-on step remains that is not the next sequential slice (for example a deferred `test-strategy` pass named in the plan's `## Validation expectations`), route there instead of defaulting to `where-we-at`/`task-close`, even on the last slice.
  - When this was the LAST slice in the plan and no such deferred step remains, route to `where-we-at` (multi-slice tasks) or `task-close` (otherwise); never dead-end the final slice.
  - For the inline-close path (LOW/MEDIUM, slice not routed to `slice-closure`), the handoff target above is also where `TASK_STATE.md` gets synced; when no further command will run promptly, route to `/sync-task-state` so state does not go stale. State upkeep after execution is owned by the routing, not by operator memory.

If a slice file is created or updated, it must include:
1. Slice goal
2. Approved scope
3. Work complexity: `LOW` | `MEDIUM` | `HIGH` (must match the plan for this slice unless explicitly revised with rationale)
4. Files touched
5. What changed
6. What was intentionally not changed
7. Validation completed (paste the verbatim command and its real output per exit criterion; asserted-not-shown counts as unverified)
8. Residual risks / follow-ups
9. Recommended next command
10. Recommended editor mode

Required output:
1. Restated approved scope
2. Work complexity used for this run (`LOW` | `MEDIUM` | `HIGH` | `N/A`) and one line why
3. Assumptions that still matter
4. Files expected to change
5. Execution summary
6. What was intentionally not changed
7. Residual risks or follow-ups
8. Exact slice file content or update block, if applicable (otherwise a short NO_OP note)
9. Recommended next command
10. Recommended editor mode
11. Why this is the correct next step
12. What should explicitly not be done yet
13. Next-wave decision (`fleet`, `sequential`, or `terminal`) with wave-size justification, unless final slice (see Next-step routing).

### Reference grounding (execution gate)
<!-- shared:reference-grounding -->
**Reference grounding (execution gate).** Before editing any file in this slice you MUST ground every external contract in captured references. This gate is mandatory, not advisory.

1. Detect. Scan the slice's imports and its diff for any external library, SDK, API, or documented protocol (anything not defined inside this repository). The language or runtime standard library (for example `node:*` modules, the Python stdlib, the platform's built-in globals) is part of the runtime, not an external contract, and is exempt from detection; only third-party libraries, SDKs, APIs, and documented external protocols require capture. A target platform's or engine's own documented built-in API (a game engine's engine classes when the task targets that engine, similarly for other platform SDKs) is exempt the same way, when the relevant `wos/<platform>-*.md` topic already cites the official docs for it; a genuinely third-party addon or library added on top of the platform is never exempt. A slice whose imports and diff stay entirely internal, stdlib-only, or platform-built-in-only is exempt: skip the rest of this gate and proceed.

2. Refuse when uncaptured. IF the slice uses an external contract that is not present in `projects/<client>__<project>/REFERENCES.md`, you MUST NOT edit. Stop, name the missing contract in one short refusal block, and route the user to `capture-references` to capture it (official docs, signature, version). This holds in every task tier. Do not fetch the web here; `capture-references` is the only authorized capture path.

3. Read and cite when captured. WHEN the contract is present in `REFERENCES.md`, read that entry (including any `Implementation contract` block) before you write code, and emit a `Grounded in:` line in the execution summary naming each `REFERENCES.md` entry or local doc you relied on. An edit that touches an external contract without a `Grounded in:` line is invalid output.

4. Design assets are external contracts too (ADR-0051). WHEN this slice implements from a design source (Figma node, screen, or component spec), pull the exact node via the design MCP (`get_design_context` / `get_screenshot` / `get_variable_defs`, `download_assets` for real assets) BEFORE editing and build from the pulled values: no placeholder boxes, guessed measurements, or assumed copy. Design-to-code slices are NOT exempt when imports are internal. IF the node is unavailable, stop and ask for the link. Placeholders need an approved `Asset-fidelity: placeholder` decision in `IMPLEMENTATION_PLAN.md`.

Do not implement an external API from memory. WHEN the captured entry and your recollection disagree, the captured entry wins (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).

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
- Changes are strictly within the approved slice scope with a clear file list.
- Tests updated only when required by the slice; validation evidence is honest: the verbatim command and its real output are pasted per validated exit criterion, never a bare "tests pass" claim.
- **APPLIED-by-default in Agent mode (ADR-0026):** when running in Agent mode, slice execution notes (slice files, TASK_STATE.md phase/status updates) default to `APPLIED`. In Ask/Plan mode, they remain `PROPOSED` per ADR-0001. Product code changes always follow repo reality regardless of mode.
- When updating TASK_STATE.md as part of slice execution, follow the canonical 5-section write pattern documented in `commands/_shared/task-state-slice-closure-pattern.md` (Current phase, Last completed step, In progress, Recommended next step, Current closure target; optional Resume notes). Same pattern enforced by `slice-closure`.
- Commit-evidence floor (inline-close; ADR-0084, ADR-0100, ADR-0105): a slice does NOT close inline without a cited commit, a genuine discardable-work waiver, or a recorded bounded deferral that keeps it open; none of the three routes to `branch-commit`.
- Godot runtime-gate floor (inline-close; ADR-0085): in a Godot task, a runtime-observable slice (scope touched a `.tscn`/`.gd`) does NOT close inline without a recorded `godot-runtime-verify` PASS or an explicit skip reason; otherwise route to `godot-runtime-verify` first. This is the load-bearing enforcement home (LOW/MEDIUM Godot slices close here, not at `slice-closure`); never fires on a non-Godot task or a no-runtime-surface slice.
- Godot feel-verdict floor (inline-close; D-4, ADR-0089): in a Godot task, a slice claiming first-playable or feature-complete does NOT close inline without a cited human `## Feel verdict` with `Overall: PASS` or an explicit skip reason; otherwise run the feel-verdict checklist and route its notes to `pr-feedback-ingest --playtest` first. Never fires on a non-Godot task or a slice making no such claim.
- Experience gates (inline-close, generalized, ADR-0091): a slice tagged `user-facing-content` or `new-user-facing-surface` does NOT close inline without a cited `## Experience verdict` PASS, and a `new-user-facing-surface` slice does NOT close inline without a cited entry-path run, in each case unless an explicit skip reason is recorded; stands down on the Godot signature in favor of the D-4 floor above.
- Mobile-runtime-gate floor (inline-close, generalized, ADR-0106): a slice tagged `mobile-runtime-target` (or matching the expo/react-native plus android/ios signature) does NOT close inline without a cited `app-runtime-verify` PASS or an explicit skip reason; otherwise route to `app-runtime-verify` first. Stands down on the Godot signature in favor of the D-4 floor above.
- Eval-threshold floor (inline-close, ADR-0104): when an `AI_EVAL_PLAN.md` covers the slice's feature, the slice does NOT close inline without the cited score-vs-threshold outcome met (or an explicit bounded skip reason); harness-runs wording never substitutes for the threshold outcome.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Make the smallest correct change that is easy to review and hard to misunderstand.

<!-- cache-breakpoint -->

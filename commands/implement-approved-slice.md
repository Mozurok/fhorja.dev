---
name: implement-approved-slice
description: Implement only the approved slice with minimal, explicit, review-friendly changes, then persist execution evidence in slice notes and TASK_STATE.md. The single official execution path of the workflow. Supports an opt-in test-first mode, per slice or via --tdd, that writes the failing test before the code. Use when the plan is valid, the current slice is defined and approved, correctness-critical ambiguity is resolved, and the files in scope are known well enough to edit safely. Do not use during discovery, contract refinement or planning, when unresolved ambiguity affects correctness, when the next step is only to sync memory or close the slice (use sync-task-state or slice-closure), or when the work is a narrow micro-delta inside an executed slice (use implement-slice-complement).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  unconditional-loads: [wos/closure-floors.implement-approved-slice.md]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  suggested-model: claude-sonnet-5
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
- **Multi-repo:** when `SOURCE_OF_TRUTH.md` contains a `## Repositories` section, produce per-repo subsections in the execution summary (files touched, validation evidence, typecheck/build status). Each repo's section is independently verifiable. When the section is absent, fall back to single-repo single-list behavior (current default).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- Implement only the approved slice.
- **Attended lock on the no-escalation path (ADR-0159, ADR-0207).** When `TASK_STATE.md ## Recommended pipeline` records `Escalations: none` AND the task-init unattended bullet did not fire AND `TASK_STATE.md ## Resume notes` do not contain `Operating mode: strict`: implement only when BOTH `IMPLEMENTATION_PLAN.md ## Approval log` has an APPROVED line for the current `## Slices` revision AND `TASK_STATE.md ## Current phase` contains `plan APPROVED`. If only one signal exists, or the log predates the latest `## Slices` write, refuse and route to `implementation-plan`. On the one-slice route `task-init` writes both (ADR-0225). Unattended, background, or fleet runs do not take this path and do not route to `branch-commit --apply`. An external execution layer may supply `ref-attested`; direct-use `autonomous-run` instead records the bounded deferral when no commit evidence exists (ADR-0197). WHEN Resume notes contain `Operating mode: strict` AND the pipeline records `Escalations: none`: if `plan APPROVED` is absent, refuse and Handoff the next missing of `invariants-and-non-goals`, `test-strategy`, `approve-plan`.
- Before executing, verify the slice is not already completed per plan/slice artifacts and `TASK_STATE.md` last completed step.
- If there is no remaining approved work for this slice (no material code delta expected), do not fake progress; return a no-op and route to `slice-closure` or `/sync-task-state` as appropriate.
- No-op rule for task-memory artifacts:
  - If slice documentation would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Do not expand scope without explicit approval.
- No orthogonal changes: do not introduce unrelated abstractions, refactors, or cleanup. The slice diff stays inside the declared file scope; record any tempting orthogonal change (a drive-by rename, an adjacent refactor, a config tidy) as a separate follow-up rather than bundling it. Within-scope tidying is still allowed. A file mechanically required for the declared scope to function (a package marker like `__init__.py`, a required index or barrel re-export) counts as within scope: create it and name it explicitly in the files-touched list rather than treating it as a scope violation or deferring it upstream.
- Preserve external behavior unless the approved slice explicitly changes it.
- Follow existing local conventions and patterns.
- **Slice-note-first floor.** WHEN the task tracks slices in `SLICES/` (the folder exists or the plan names slice files), the slice note SHALL be born BEFORE the first Edit/Write inside the declared scope, including the TDD Red test: one plain Write creating `SLICES/<NN>_<slug>.md` with the slice goal, the approved scope, the work complexity, and `Status: in progress`. The floor never fires before the no-op check (a NO_OP slice writes nothing) and is inert when the task does not track SLICES/. At inline close the same file is FILLED via Edit (facts appended into the skeleton's sections), never rewritten; a scope change during execution becomes an explicit revision line, never a silent overwrite. SLICES/*.md stays OUTSIDE the substrate protocol (no wos:write header, no JSONL line) and is EXCLUDED from any SHA-stamp batch.
- Before making changes, restate:
  - exact approved scope
  - assumptions that still matter
  - files expected to change
- If missing context or ambiguity could affect correctness, stop and recommend the correct prior command instead of guessing. In an attended chain on a task branch (ADR-0233) that is a route, not a wait: a product decision goes to `decision-interview` (a provisional P-N), scope the slice lacks to `implementation-plan`.
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
- Keep the blast radius as small as possible. WHEN a slice touches navigation, routing, or deep-link files, implement-approved-slice SHALL require a `code-context-map` code-flow citation (ADR-0057), a `code-context-map exemplars` citation, or a `code-locate` result as the blast-radius evidence before editing; a bare symbol-name grep does not satisfy this class of slice. That evidence SHALL name the in-repo precedent `file:line` the new code mirrors, or, when none exists, paste the exact search command and its verbatim zero-result output (ADR-0146): a prose `no precedent found` line is a referent-free status, read as UNKNOWN, and every other tier of this gate yields a referent a reviewer can re-run. Naming a precedent is necessary and not sufficient; rule 7 of `wos/reference-grounding.md` (ADR-0146) decides whether it grounds the claim at THIS call site. The trigger is file scope alone, never a risk tag.
- Only update tests directly required by the approved slice.
- After changes, summarize:
  - exactly what changed
  - what was intentionally not changed
  - residual risks or follow-ups
- **Slice completion check:** at the end of each slice, verify exit criteria inline before emitting the handoff. Produce a short checklist (files created/modified, typecheck status, exit criteria met/not-met). For each validated exit criterion paste the verbatim command and its real output as proof; an exit criterion asserted without shown output is marked unverified, not met (this is distinct from the reference-grounding gate, which cites external contracts). When all exit criteria pass and work complexity is LOW or MEDIUM, the slice is considered closed inline; do not route to `slice-closure`. Route to `slice-closure` only when work complexity is HIGH or when exit criteria cannot be fully verified inline.
- **Renumber check on the one-slice route (ADR-0225).** WHEN `## Recommended pipeline` carries `Route: one-slice`, run `scripts/check-doc-sync.sh --against HEAD --repo <the repository the slice changed>` from the workflow root before the inline close, with the diff still uncommitted, and paste its output as the exit criterion's proof. On exit 1, record it in the slice notes and route to `implement-slice-complement` with the stale references as its micro-delta list. A second exit 1 for the same slice, read from the slice notes, routes to `implementation-plan`, whose rewrite of `## Slices` ends the route; so does a fix that needs a file outside `Scope`.
- **Slice evidence file.** Append each validated criterion to `SLICES/*.evidence.md` (one per slice): one block per criterion, output verbatim. It is OUTSIDE the substrate protocol.
- **Verification divergence check.** WHEN a verification check's expected value differs from its actual value, implement-approved-slice SHALL require an explanation before treating the check as passed; do not silently accept a mismatched count or assertion as passing.
- **Closure floors (lazy-loaded; `wos/closure-floors.implement-approved-slice.md`).** Before closing a slice inline, load `wos/closure-floors.implement-approved-slice.md` and apply every floor in it exactly as written there (a generated view: it already contains only this command's inline-close variants, and is rebuilt from the canonical floors file by `scripts/build-closure-floor-views.py`). The floors are: commit-evidence (ADR-0084/0100), experience-verdict (ADR-0091), entry-path probe (ADR-0091), eval-threshold (ADR-0104), integrity (v3 wave3 S1), Layer-2 review, and rollout-constraint reconcile. This load is MANDATORY, not conditional: unlike the platform floors above, these fire on every slice, and the inline-close path is precisely where a skipped floor goes unnoticed. The slice notes SHALL cite which subsections were read and applied (G3 safeguard). A slice that does not satisfy a floor takes THAT floor's declared verdict, read from its own `On missing evidence:` line: `record` writes `unverified: <reason>` into the slice notes and the slice closes inline, `reconcile` records a named deferral and it closes inline, and `refuse` stops the inline close and routes per that file. <!-- count:closure-floors-recording -->11<!-- /count --> of the <!-- count:closure-floors -->15<!-- /count --> floors record or reconcile, so no single verdict fits all of them (ADR-0203). In an attended chain on a task branch a verdict the agent cannot give itself (feel, experience) records instead of refusing, and every `unverified:` line reaches the draft PR's "Not verified" list (ADR-0233).
- **Platform runtime floors (lazy-loaded; ADR-0085, ADR-0089, ADR-0106, ADR-0127).** WHEN the active task matches the Godot signature (a `project.godot` or `.gd` codebase, or `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder), the mobile signature (the `mobile-runtime-target` tag, or a `package.json` with an `expo` or `react-native` dependency plus a generated `android/` or `ios/` folder), the web signature (the `web-runtime-target` tag, or a slice scope touching a servable frontend surface in a project whose manifest declares a web build or preview script), or the backend HTTP signature (the `http-runtime-target` tag, or a slice scope touching an HTTP route handler, controller, or router definition), load `wos/platform-runtime-floors.md` and apply its **implement-approved-slice variants** (Godot runtime-gate, Godot feel-verdict, Godot tier-declaration, mobile-runtime-gate, web-runtime-gate, backend-runtime-gate) exactly as written there; the slice notes SHALL cite which subsection was read and applied (G3 safeguard: the lazy load never degrades into a paraphrase). Inert on a task with no platform signature. On the web and backend signatures, running the runtime battery by hand inside this command does NOT satisfy the floor: route to `web-runtime-verify` or `api-runtime-verify`, which own the serving and probing discipline, and cite the verdict. The generalized floors (commit-evidence, experience-verdict, entry-path probe, eval-threshold, integrity, Layer-2 review, rollout-constraint reconcile) are the lazy-loaded set in `wos/closure-floors.implement-approved-slice.md` above and are unaffected.
- **Next-step routing (waves-aware and terminal-safe, per ADR-0042):** after the completion check, emit a REQUIRED `Next-wave decision:` line (one of `fleet`, `sequential`, `terminal`) with the wave-size check that justifies it; omitting it on a non-final slice is invalid output (the guard against silently defaulting to sequential when a parallelizable wave is ready). Then choose the handoff target in this order:
  - When the plan's remaining `## Execution waves` show a wave of size 2 or more whose slices declare `Scope` and `Depends-on`, route to `implement-fleet` for those parallel slices instead of hand-picking the next sequential slice.
  - When more sequential slices remain (the remainder is a chain), route to `implement-approved-slice` for the next slice.
  - When a plan-named follow-on step remains that is not the next sequential slice (for example a deferred `test-strategy` pass named in the plan's `## Validation expectations`), route there instead of defaulting to `where-we-at`/`task-close`, even on the last slice.
  - When this was the LAST slice in the plan and no such deferred step remains, route to `where-we-at` (multi-slice tasks) or `task-close` (otherwise); never dead-end the final slice. When the run is attended and no `commit-ref` exists yet, that last-slice handoff is `branch-commit --apply` instead (ADR-0159, ADR-0233).
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

2. Apply the rest (lazy-loaded; `wos/reference-grounding.md`). WHEN step 1 finds an external contract, load `wos/reference-grounding.md` before you edit and apply every rule there exactly as written. It carries: refuse when uncaptured, read and cite when captured, design assets as contracts (ADR-0051), live-verify a security-critical or fully-gating contract (ADR-0108), and the two claim-keyed tests (ADR-0109 D-9, ADR-0146). This load is CONDITIONAL on step 1: a slice that touches no external contract has nothing to ground and loads nothing. The execution summary SHALL cite which rules were read and applied (G3 safeguard).
### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- Changes are strictly within the approved slice scope with a clear file list.
- Tests updated only when required by the slice; validation evidence is honest: the verbatim command and its real output are pasted per validated exit criterion, never a bare "tests pass" claim.
- **Task-memory writes are APPLIED (ADR-0199).** Slice execution notes (slice files, TASK_STATE.md updates) are written and marked `APPLIED` in every mode. ADR-0026 carved this command out of the ADR-0001 mode gate; both are superseded and the carve-out is unnecessary. Product code changes always follow repo reality regardless of mode.
- When updating TASK_STATE.md as part of slice execution, follow the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section write pattern documented in `commands/_shared/task-state-slice-closure-pattern.md` (Current phase, Last completed step, In progress, Recommended next step, Current closure target; optional Resume notes). Same pattern enforced by `slice-closure`.
- Integrity floor (inline-close). `bash scripts/verify-substrate-batch.sh <task-folder>` ran and exited 0, or an explicit `integrity-waiver: N advisories unresolved (<reason>)` line is recorded. A silent non-zero inline close is invalid output. Resolve `scripts/verify-substrate-batch.sh` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224); when it is in neither, `integrity: not checked (verify-substrate-batch not installed)` is recorded, which is neither a pass nor a waiver. `slice-closure` carries this floor and the inline path did not, so a slice that closed here skipped the only check that the K.2 headers and the `.wos/VERIFICATION_LOG.jsonl` lines it was told to write actually exist.
- Commit-evidence floor (inline-close; ADR-0084, ADR-0100, ADR-0105): a slice does NOT close inline without a cited commit, a genuine discardable-work waiver, or a recorded bounded deferral that keeps it open. Where a human turn is available, the route is `branch-commit --apply` (ADR-0163); an unattended run records the bounded deferral.
- Closure floors (lazy, unconditional; `wos/closure-floors.implement-approved-slice.md`): before any inline close, the implement-approved-slice variants were loaded and applied, and the slice notes cite which subsections were read. Closing inline without that citation is invalid output; the inline path is exactly where a skipped floor goes unnoticed.
- Layer-2 review floor (inline-close): a cited `review-hard` verdict (plus `security-review` on a security surface), a named host-repo equivalent, or an explicit one-line skip reason. The inline exit-criteria checklist is Layer 1 and never substitutes.
- Rollout-constraint reconcile (inline-close): when the plan carries `## Rollout and rollback notes`, every constraint naming a file, config key, or release track inside this slice's Scope is satisfied or recorded as a named deferral.
- Platform runtime floors (lazy; ADR-0085, ADR-0089, ADR-0106, ADR-0127): on a Godot-, mobile-, web-, or backend-HTTP-signature task, the implement-approved-slice variants in `wos/platform-runtime-floors.md` were applied and the slice notes cite which subsection was read; a slice failing a floor takes the verdict its `On missing evidence:` line declares and routes per that file, and on the web and backend signatures a hand-rolled battery does not stand in for the verify command's verdict. Inert on tasks with no platform signature.
- Experience gates (inline-close, generalized, ADR-0091): a slice tagged `user-facing-content` or `new-user-facing-surface` records `unverified: no experience verdict on a sample` and closes inline unless a verdict (`Attested by: run` with cited evidence, or `human`) is recorded, and a `new-user-facing-surface` slice records `unverified: entry path never exercised` and closes inline unless an entry-path run is cited, in each case unless an explicit skip reason is recorded (ADR-0203); stands down on the Godot signature in favor of the D-4 floor above.
- Eval-threshold floor (inline-close, ADR-0104): when an `AI_EVAL_PLAN.md` covers the slice's feature, the slice records `unverified: no eval outcome cited` and closes inline unless the score-vs-threshold outcome is cited as met (or an explicit bounded skip reason is recorded, ADR-0203); harness-runs wording never substitutes for the threshold outcome.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Make the smallest correct change that is easy to review and hard to misunderstand.

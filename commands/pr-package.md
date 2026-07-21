---
name: pr-package
description: Prepare a clean delivery package for GitHub from the real git diff vs an explicit base branch, persisted as PR_PACKAGE.md (or PR_PACKAGE.<repo>.md for multi-repo tasks). Produces branch name, commit messages, fetch, checkout, add, commit, and push commands, PR title and body, and reviewer attention points; never invents work outside the diff. Per-repo when SOURCE_OF_TRUTH.md has a Repositories section. Use when the task is ready for delivery, scope is complete enough for PR preparation, there is a real inspectable diff against an explicit base branch, and that diff is stable. Do not use during active implementation, when blockers or unresolved contract issues remain, when the diff is still changing rapidly, when you only need a quick branch and commit name (use branch-commit), when the trigger is review feedback (use pr-feedback-ingest or post-review-pivot), or when the need is only slice closure (use slice-closure). After the draft, use self-critique-and-revise before delivery.
metadata:
  category: delivery-and-communication
  primary-cursor-mode: Ask
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 3400
  suggested-model: claude-opus-4-7
---
# pr-package

Act as a senior engineer preparing a full delivery package for the active engineering task based on the real git diff.

Goal:
Prepare a clean delivery package for GitHub using the actual implementation changes in the current branch compared against an explicit integration base branch, then persist the result in the task repository.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- target repo (only for multi-repo tasks where `SOURCE_OF_TRUTH.md` has a `## Repositories` section): the repo identifier this invocation packages. Must match one entry in the `## Repositories` section. Multi-repo tasks invoke `pr-package` once per repo, with one invocation producing one repo's PR. See the spec `## Multi-repo support (v1)` for the schema.
- explicit git base branch to compare against (example: `origin/main`, `origin/staging`, or a named remote branch). For multi-repo tasks, this is the base branch for the `target repo` (which may differ across repos and is recorded per-repo in `## Repositories`).
- current local branch name (as shown by `git branch --show-current`)
- working tree context (as shown by `git status --porcelain` or an explicit statement that the working tree is clean)
- explicit diff commands used (at minimum):
  - `git diff <base>...HEAD`
  - optional: `git diff --stat <base>...HEAD`
- real git diff vs the explicit base branch
- latest validation/test evidence if available
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update (only if materially changed):
- PR_PACKAGE.md
- TASK_STATE.md

Operating rules:
- When the PR package file does not exist yet in the task folder, seed it from repo-root `templates/PR_PACKAGE.md`, then fill with real `git` output via this command. For single-repo tasks the file is `PR_PACKAGE.md`; for multi-repo tasks (when `SOURCE_OF_TRUTH.md` has a `## Repositories` section) the file is `PR_PACKAGE.<repo>.md` where `<repo>` matches the `target repo` input.
- Multi-repo handling: branch behavior on the presence of `## Repositories` in `SOURCE_OF_TRUTH.md`. When the section exists, require explicit `target repo` input matching one entry; produce `PR_PACKAGE.<repo>.md` (not `PR_PACKAGE.md`); use the base branch declared for that repo in the `## Repositories` entry. Reject invocations missing the `target repo` input or with an identifier that does not match any entry. When the section is absent, run as single-repo (existing behavior, no change). One invocation produces one repo's PR; multi-repo tasks invoke `pr-package` N times for N repos. Cross-repo coordination notes (rollout order, dependencies between PRs) live in `TASK_STATE.md` `Risks to watch` plus per-PR body cross-reference lines (`Related PR: <other-repo-PR-url>`); they are not consolidated into a single shared `PR_PACKAGE.md`.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not reopen broad analysis.
- Do not focus only on the latest slice.
- Treat the full current task diff against the explicit base branch as the delivery scope.
- Before producing output, verify the diff is stable enough to package; if it is still moving quickly, return a no-op and route to stabilization steps.
- No-op rule for artifacts:
  - If `PR_PACKAGE.md` would not materially change versus the current diff, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Summarize the real implementation work across the branch.
- Do not mention local workflow files or memory artifacts in the PR content.
- Focus only on real code, tests, configs, migrations, or runtime-relevant changes.
- Keep commit messages concise and human.
- The main commit message must be at most 2 lines.
- Prefer one clean main commit unless the diff clearly justifies more.
- Do not invent work not grounded in the diff.
- Always write the PR body for humans on GitHub: do not reference `my_work_tasks/` paths, command filenames, or internal workflow artifacts.
- **Complete explicit staging (P2-3, careers-page dogfooding 2026-06-23):** the `add` step MUST list every file in the task's delivery scope by explicit path. Never emit `git add -A` / `.` / `*` (a global hook blocks it and it contaminates commits with tooling files). When the file set is large, list them all anyway, grouped by directory; completeness is what removes the temptation to reach for a wildcard. There is no per-task opt-in to `-A`.
- **Consume task preferences (P2-3):** read `TASK_PREFERENCES.md` in the task folder if present, and honor its durable delivery preferences (base branch, commit convention, PR-template path). This is the consume side that a captured preference relies on; a preference in `TASK_STATE.md ## Observations` alone is NOT read back, so durable delivery preferences belong in `TASK_PREFERENCES.md`.
- **Project PR template (P2-6, careers-page dogfooding 2026-06-23):** detect the product repo's `.github/PULL_REQUEST_TEMPLATE.md` (resolve the repo path from `SOURCE_OF_TRUTH.md`; or the path named in `TASK_PREFERENCES.md`). When it exists, render item 8 (the PR description) into that template, filling each section from the real diff and leaving unknown checklist items unchecked. When it does not exist, emit the generic PR body unchanged.

PR_PACKAGE.md must include:
1. Explicit base branch, current branch, and the exact diff commands used, ready to paste (for auditability)
2. Delivery scope based on diff vs the explicit base branch
3. Suggested branch name
4. Suggested main commit message
5. Optional additional commit messages, only if justified
6. Suggested git commands:
   - fetch
   - checkout branch confirmation if useful
   - add
   - commit
   - push
7. Suggested PR title
8. PR description in markdown, ready to paste into GitHub (rendered into the product repo's `.github/PULL_REQUEST_TEMPLATE.md` when one exists, per the Project PR template rule; otherwise the generic body)
9. Reviewer attention points
10. Recommended next command
11. Recommended editor mode

Required output:
1. Exact content for PR_PACKAGE.md (full document if create/update; otherwise a short NO_OP note)
2. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
3. Recommended next command
4. Recommended editor mode
5. Why this is the correct next step
6. What should explicitly not be done yet

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- PR narrative matches the real diff vs the explicit base branch (no invented work).
- The diff is both an upper and a lower bound on the narrative: every path/hunk that materially changes behavior in `git diff <base>...HEAD` appears in the PR description, and every claim in the narrative is grounded in a path or hunk in that diff. Summarizing from `TASK_STATE.md`, `DECISIONS.md`, or `IMPLEMENTATION_PLAN.md` without citing the real diff is invalid output (under-reporting and over-promising are both regressions).
- Includes explicit diff commands, current branch, and working tree notes (clean vs dirty) grounded in real `git` output.
- All 11 items of `PR_PACKAGE.md must include` are present, or each omission carries an explicit one-line `SKIP: <reason>` note. Silent omission of items such as `Reviewer attention points`, working tree status, or the verbatim diff commands is invalid output.
- The PR package file (`PR_PACKAGE.md` for single-repo, `PR_PACKAGE.<repo>.md` for multi-repo) is `PROPOSED` unless persisting in Agent mode; never put task-memory paths into GitHub PR text.
- Multi-repo validation: when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, output rejects invocations missing the `target repo` input or with an identifier that does not match any entry; producing `PR_PACKAGE.md` (without repo suffix) in multi-repo mode is invalid output; using a base branch other than the one declared in the matched `## Repositories` entry is invalid output unless the user explicitly overrides with one-line justification. Single-repo tasks (no `## Repositories` section) behave identically to the v1.0 contract.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after `PR_PACKAGE.md` content without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for accuracy against the real diff, reviewer clarity, and full-task delivery quality.

<!-- cache-breakpoint -->

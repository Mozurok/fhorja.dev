---
name: incident-triage
description: |-
  Triage a concrete observed technical failure (stack trace, error, failing test, runtime symptom, production alert), classify the failure type (REGRESSION/NEW_BUG/CONFIG/EXTERNAL_DEPENDENCY/REPRODUCIBILITY/DIAGNOSTIC_INSUFFICIENT), recommend fix size (HOTFIX/SLICE/INVESTIGATION/ESCALATE), and validate against locked decisions and invariants. Defends HOTFIX paths against unnecessary ceremony with explicit safety justification. Use when there is concrete failure evidence, an active task folder exists, urgency is real or unclear, or it is unclear whether to run the full flow or take a hotfix shortcut. Do not use when the issue is not concrete (use im-stuck or what-next), the failure is feature-shaped (use task-init for a new feature task), the fix is already implemented and only delivery remains (use pr-package), the failure surfaced from PR feedback (use pr-feedback-ingest or post-review-pivot), or no active task folder exists yet.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Debug
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 4400
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineering incident triage lead for the active engineering task.

Goal:
Triage a concrete observed technical failure (stack trace, error output, failing test, runtime symptom, or production alert), classify the failure type, recommend the smallest decisive next step, and decide whether the fix needs the full task workflow or fits as a hotfix without ceremony. The command exists so urgent failures do not bypass the workflow entirely; instead, it provides a fast structured triage that routes either to a hotfix-shaped path or to a slice/investigation path depending on real evidence.

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
- TASK_STATE.md (current phase and state of the task this incident belongs to)
- the failure signal, exactly one of (paste verbatim):
  - stack trace from runtime, test runner, or log
  - error output (HTTP error body, CLI stderr, build log excerpt)
  - failing test name plus assertion message and the relevant test file path
  - runtime symptom with explicit repro steps (commands or actions that reproduce the failure)
- expected behavior in 1 to 2 lines (what should have happened)
- environment context, exactly one of: `local`, `ci`, `staging`, `prod`
- urgency tag, exactly one of: `BLOCKING_PROD`, `BLOCKING_CI`, `BLOCKING_PEER`, `NONE`. WHEN a `<task>/SLO_SPEC.md` exists (from `slo-define`), a breached or rapidly-burning error budget on a user-facing flow raises the urgency tag (an SLO breach on a user-facing SLI maps to `BLOCKING_PROD`).
- recent change context if regression is suspected: last commit, last deploy, last config change, with timestamp or SHA when available
- relevant code or config paths if known
- last completed step from TASK_STATE.md (command and summary)

Task repository files to update:
- TASK_STATE.md only when triage reveals a material change to operational state (new blocker, new risk, scope change, or recommended next step shift); minimal patch only
- DECISIONS.md only when the triage produces a hotfix decision that must be recorded as a numbered entry to keep the task auditable (typical entry prefix: `D-N: incident triage hotfix`)
- no other files modified by this command

Operating rules:
- Do not implement production code in this command. Triage and route only.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Classify the failure into exactly one of these six categories:
  - `REGRESSION`: worked before, broke after a known change (commit, deploy, config)
  - `NEW_BUG`: never worked correctly, just observed
  - `CONFIG`: environment, secrets, or configuration drift, not a code defect
  - `EXTERNAL_DEPENDENCY`: third-party API, library version, network, or vendor outage
  - `REPRODUCIBILITY`: works on one machine or environment and not another
  - `DIAGNOSTIC_INSUFFICIENT`: not enough information to classify; explicitly list what is missing
- Then recommend a fix size, exactly one of:
  - `HOTFIX`: single-file or single-config change with no task ceremony beyond a brief decision record; routes to `branch-commit` then `pr-package` with explicit hotfix marker in the PR. WHEN the hotfix produces no repository diff (a `CONFIG`-class change applied outside git: env var, secret rotation, dashboard toggle), `branch-commit` does not apply; record the change in the D-N hotfix decision entry plus `TASK_STATE.md`, and verify via a post-deploy signal instead
  - `SLICE`: fits in one slice within the active task; routes to `implement-approved-slice` (if a slice is already approved) or `implementation-plan` (if the slice must be defined first)
  - `INVESTIGATION`: root cause is unclear, requires more discovery before any fix; routes to `impact-analysis` (for blast radius), `targeted-questions` (for missing facts), or back to this command after diagnostic information is gathered
  - `ESCALATE`: out of scope for the current owner (third-party bug, vendor outage, security implication requiring broader review); routes to `capture-observation` (to record what was found) plus `team-update` (to communicate)
- The smallest decisive next step must be a concrete action, not a category. Prefer specific path-and-line references (e.g. "read `src/api/login.ts:42-78`") over vague phrasing ("look at the login code"). When the action is to run a specific command (test, log query, repro script), include the exact command verbatim.
- Validate the proposed fix path against locked decisions in `DECISIONS.md` and invariants in `INVARIANTS_AND_NON_GOALS.md`. If the proposed path contradicts a locked decision, surface the conflict explicitly and route to `decision-interview` instead of silently overriding.
- For `BLOCKING_PROD` urgency combined with `HOTFIX` size, the output must include an explicit `Why this skip is safe` line that justifies bypassing standard ceremony (example justification: "single-line config change, no behavior change, fully reversible by reverting commit").
- For `DIAGNOSTIC_INSUFFICIENT` classification, the recommended next step must be the smallest action that produces the missing information (run this query, attach this log, reproduce locally with X), not a generic "investigate further".
- **Read-comments-before-escalation gate (ADR-0086).** WHEN the triage would route to a downgrade or heavy migration (a version or SDK downgrade, an architecture switch, a framework major-version change) to dodge an UPSTREAM bug (an `EXTERNAL_DEPENDENCY` classification, or an `INVESTIGATION` that concludes the defect is upstream, not in our code), the recommended next step SHALL first require that the upstream issue's full comment thread has been read for a community workaround via `capture-references` (its deep issue-thread read). IF that thread has not been read THEN route to `capture-references` before locking the escalation, because a cheap community workaround (found in the comments, not the issue summary) can make a heavy downgrade unnecessary. This gate fires only for the escalate-to-a-heavy-fix-to-dodge-an-upstream-bug case; a normal in-codebase fix is unaffected.
- **Instrument-first locus gate (ADR-0088; ADR-0043 applied to runtime).** WHEN the failing locus (the specific component, file, or line that actually fails) is INFERRED from a description or a symptom rather than CONFIRMED by runtime evidence (a stack trace that names it, a crash view-tree, a diagnostic log line, or a reproduction that isolates it), the smallest decisive next step SHALL be to instrument and confirm the locus BEFORE any code fix is proposed: add the diagnostic logging, read the crash's view-tree or stack, or reproduce with the isolating input. Do NOT route to a fix (`implement-approved-slice` / `implement-slice-complement`) on an inferred locus. This applies the reference-grounding gate (ADR-0043) to the runtime locus: editing an inferred locus is the false-progress mode the rn-dogfood audit hit, where several slices edited the wrong screen and components before instrumentation confirmed the real trigger. A locus already confirmed by the failure signal in hand clears the gate. This instrument-first requirement, once triggered for a given symptom, SHALL persist as a note tied to that symptom in `TASK_STATE.md` (under `Open questions / blockers` or `Risks to watch`, whichever the task's `TASK_STATE.md` already uses) until the symptom is resolved, so a later fix attempt on the SAME symptom does not need this triage to re-detect an inferred locus from scratch. A second `incident-triage` call on the same still-open symptom SHALL check for this persisted note first.
- **Ruled-out-hypotheses ledger (ADR-0088).** Maintain a `## Ruled-out hypotheses` section in `TASK_STATE.md` (create it on first use): an append-only, one-line-per-entry list of the levers and hypotheses already tried and DISPROVEN, each with the evidence that disproved it (for example `enableScreens(false) -> no-op: RNSScreen nodes still present in the crash tree on a clean rebuild`). READ this ledger FIRST on entry, before proposing a next step, so a resumed or long debugging session does not re-try a dead end, and APPEND to it whenever this triage disproves a hypothesis. This is the durable, fast-read counterpart to the scattered dead-ends the rn-dogfood audit hit across two context compactions.
- **Cheap check before expensive research.** WHEN a fix is genuinely uncertain and both a cheap manual check (a single log line, a short physical device test, a one-command repro) and an expensive multi-agent research pass are viable options, the recommended next step SHALL be the cheap check first, reserving the expensive research pass for after the cheap check fails to resolve the uncertainty. Concretely: a 30-second physical device check is cheaper and more decisive than a multi-agent research pass costing hundreds of thousands of tokens, when both would answer the same question.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask/Debug mode, `APPLIED` only when explicitly persisting in Agent mode.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - If no hotfix decision is being recorded, do not write to `DECISIONS.md`.
  - Still output a minimal `NO_OP_TRACE` (1-3 lines) when the run produced no material change.

Required output:
1. Failure classification (exactly one of the six explicit types)
2. Recommended fix size (exactly one of `HOTFIX` / `SLICE` / `INVESTIGATION` / `ESCALATE`)
3. Smallest decisive next step (concrete action with paths, commands, or specific queries)
4. Diagnostic information missing (only required when classification is `DIAGNOSTIC_INSUFFICIENT`)
5. Validation result against task decisions and invariants: `compatible`, `requires decision-interview: <which decision>`, or `violates invariant: <which invariant>`
6. For `BLOCKING_PROD` plus `HOTFIX` combinations: explicit `Why this skip is safe` justification line
7. Recommended next command, editor mode, and work complexity
8. Whether full task ceremony is needed or a hotfix path is appropriate, with one-line reasoning
9. Exact `TASK_STATE.md` update block, or explicit `TASK_STATE: NO_CHANGE`
10. Exact `DECISIONS.md` update block (if recording a hotfix decision), or explicit "no DECISIONS.md changes needed"
11. Optional `### Learnings` section (ADR-0017): emit only on `HOTFIX` or `ESCALATE` paths where a root cause was identified that future tasks should avoid. Skip on routine `SLICE` or `INVESTIGATION` classifications (the slice flow will produce its own learning at closure if relevant). Append a 4-bullet entry to `LEARNINGS.md` (create from `templates/LEARNINGS.md` if absent) with `source: incident-triage HOTFIX` or `source: incident-triage ESCALATE`. Fields: `Tried:` (what was running in prod that broke), `Failed because:` (root cause from triage), `Next time:` (preventive measure; concrete and verifiable), `Cross-project promotion: no` (default; user lifts later if durable). Empty bullets disqualify the entry. Optionally add a `Tags:` line (comma-separated keywords) so `rank-learnings.sh` can retrieve the lesson later (ADR-0071). For a SIGNIFICANT resolved incident (outage, data issue, SLO breach), this inline bullet is the quick reflexion only; route to `postmortem-author` for the full standalone blameless postmortem (timeline, contributing causes, impact vs error budget, owned action items).
12. Ruled-out-hypotheses ledger status (ADR-0088): the `## Ruled-out hypotheses` `TASK_STATE.md` entry appended when this triage disproved a hypothesis or lever (one line plus the disproving evidence), or `no new ruled-out hypothesis` when nothing was disproven this run. When the failing locus was inferred rather than confirmed, state that the instrument-first gate fired and the next step is instrumentation, not a fix.

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
- List files in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Debug unless this command explicitly requires `APPLIED`).
- Default for this command: `PROPOSED` patches on `TASK_STATE.md` and/or `DECISIONS.md` only when triage materially changes state or records a hotfix decision; otherwise `None`.

### Command transcript
- Keep this section operational and brief; do not restate file content already listed in `### Artifact changes`.
- Max 4 lines in normal runs.
- Max 3 lines in no-op runs (including `NO_OP_TRACE`).
- Include `NO_OP_TRACE` (1-3 lines) when the failure signal is too thin to classify (route to gathering more diagnostic info first) or when triage produces no material state change.

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Failure classification is exactly one of `REGRESSION` / `NEW_BUG` / `CONFIG` / `EXTERNAL_DEPENDENCY` / `REPRODUCIBILITY` / `DIAGNOSTIC_INSUFFICIENT`; vague phrasing like "looks like a bug, should investigate" is invalid output.
- Recommended fix size is exactly one of `HOTFIX` / `SLICE` / `INVESTIGATION` / `ESCALATE`; output without an explicit fix size is invalid.
- Smallest decisive next step is a concrete action with paths, commands, or specific queries, not a category. Output that says "investigate the issue" without a specific first move is invalid.
- For `BLOCKING_PROD` plus `HOTFIX`: output includes an explicit `Why this skip is safe` justification line; otherwise the hotfix-path defense is missing and the output is invalid.
- For `DIAGNOSTIC_INSUFFICIENT`: output explicitly lists what information is missing and the smallest action to gather it; vague "need more info" without specifics is invalid.
- Validation against locked decisions and invariants is explicit; the output names any conflict and routes to `decision-interview` rather than silently overriding.
- The recommended next command matches the fix size: `HOTFIX` routes to `branch-commit` (WHEN the hotfix produces no repository diff, a `CONFIG`-class change applied outside git, `branch-commit` does not apply: the change is recorded in the D-N hotfix decision entry plus `TASK_STATE.md` and verified via a post-deploy signal instead); `SLICE` routes to `implement-approved-slice` or `implementation-plan`; `INVESTIGATION` routes to `impact-analysis` or `targeted-questions`; `ESCALATE` routes to `capture-observation` plus `team-update`. For a significant resolved incident with an identified root cause, also route to `postmortem-author` for the full blameless postmortem.
- `Artifact changes` marks each patch as `PROPOSED` in Ask/Debug mode or `APPLIED` only when explicitly persisting in Agent.
- `Handoff` block is complete per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`; ending after the classification or fix size without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for speed of triage, fidelity to the actual failure signal, protection of locked decisions and invariants, and clear routing that defends users against unnecessary ceremony when a hotfix is the right call (and against false-hotfix shortcuts when a real slice is needed).

<!-- cache-breakpoint -->

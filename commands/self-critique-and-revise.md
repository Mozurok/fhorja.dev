---
name: self-critique-and-revise
description: Take a draft artifact (IMPLEMENTATION_PLAN.md, SLICES/*.md, or PR_PACKAGE.md), run a structured critique against a locked per-artifact-type rubric, and produce a revised draft. Evaluator-optimizer pattern; the revision is written APPLIED in every mode, the critique is shown in the response, and git is the undo. Distinct from review-hard (judges, no revision), direction-adjust (records a decision, no revision), and post-review-pivot (external feedback). Use when a draft was just written and one critique-and-revision pass is cheaper than re-running the authoring command. Do not use when the artifact is outside the locked set, when the issue is operational state rather than draft quality (use sync-task-state or state-reconcile), when external feedback drives the change (use pr-feedback-ingest or post-review-pivot), or before the artifact is drafted.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  suggested-model: claude-sonnet-5-5
---
# self-critique-and-revise

Act as a senior/staff engineering evaluator-optimizer for the active engineering task.

Goal:
Produce a structured critique of a draft artifact using a locked per-artifact-type rubric, then emit a revised draft incorporating the fixable critique items. Distinct from review-hard (judges only) and direction-adjust (records corrections; does not revise artifacts).

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- artifact path: exactly one of `IMPLEMENTATION_PLAN.md`, `SLICES/<NN>_<slug>.md` (legacy `SLICES/<NN>-*.md` also accepted), or `PR_PACKAGE.md` (relative to the active task folder)
- optional: focus area (e.g., "exit criteria"; "scope leak"); when provided, the critique emphasizes that dimension while still running the full rubric

Task repository files to update:
- the target artifact (the revised draft, written `APPLIED` in every mode; ADR-0220)
- `TASK_STATE.md` only when the revision changes the recommended next step

Operating rules:
- Do not implement production code; this is a draft-artifact revision.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Detect artifact type first**. Determine whether the input is `IMPLEMENTATION_PLAN.md`, `SLICES/<NN>_<slug>.md` (also accept legacy `SLICES/<NN>-*.md`), or `PR_PACKAGE.md`. If the artifact is none of these, emit `NO_OP_TRACE` with the reason and recommend the right command (`review-hard` for engineering risk; `sync-task-state` for state; `direction-adjust` for mid-task corrections).
- **Apply the locked rubric** (do not invent criteria; do not skip criteria; do not score on aesthetic dimensions not in the rubric):

  **IMPLEMENTATION_PLAN.md rubric**:
  1. Objective clarity: is the task objective a single sentence achievable in the planned slice count?
  2. Slice independence: can each slice close on its own (a closed slice ships value or unblocks the next)?
  3. Exit criteria: does each slice have a verifiable exit criterion (not "done when done")?
  4. Dependency graph completeness: are all inter-slice dependencies named (which slice blocks which)?
  5. Sequencing rationale: is the slice order justified (why not the other order)?
  6. Risk surface: is each slice's primary risk named with mitigation hint?
  7. Slice size: is each slice declared LOW / MEDIUM / HIGH per the Fhorja work-complexity rule?

  **SLICES/*.md rubric**:
  1. Scope tightness: does the slice touch only files in the declared scope; no creep into adjacent slices?
  2. Exit criteria: verifiable; not vague?
  3. Dependency awareness: depends-on slices named; what blocks it; what it unblocks?
  4. Risk surface: per-slice risks listed with mitigation hint?
  5. Work complexity declared: LOW / MEDIUM / HIGH?
  6. Test strategy or skip rationale: tests for this slice OR explicit rationale for skip?
  7. Handoff fully specified: Run now / Mode / Work complexity / Reason (+ Resume context if Mode B)?

  **PR_PACKAGE.md rubric**:
  1. Diff fidelity: does every claim in the PR body trace to a real diff hunk?
  2. No scope leak: does the PR claim only what the diff contains; no work beyond the diff?
  3. Reviewer attention points present: explicit list of files / changes that need careful review?
  4. Test plan present: bulleted checklist of how to validate?
  5. Breaking changes flagged: any contract change, schema change, or behavior change is explicit?
  6. Base branch named: explicit git base branch in the package?
  7. Commit message follows project convention: short title; non-promotional body?

- **For each criterion**: emit `PASS`, `FAIL`, or `WEAK` with a one-sentence reasoning. `WEAK` means partially met (e.g., exit criteria exist but two are vague). `FAIL` means absent or fundamentally wrong. `PASS` means meets the criterion with no concerns.
- **Revise only the fixable items**. `FAIL` and `WEAK` items that can be addressed by reading the existing artifact, DECISIONS.md, INVARIANTS, and the source code are revised in the new draft. Items that need user judgment (e.g., "should slice 03 split into two?") go to the `## Not applied` section with explicit "deferred to user".
- **Preserve unchanged content verbatim**. Sections that PASS or that are not in the rubric (e.g., title, history) are copied byte-identical. Only criterion-driven sections change.
- **No scope creep**. The revision is within the artifact's intent. If the critique surfaces that the intent itself is wrong (e.g., plan splits the wrong slices), the right route is `direction-adjust` or `post-review-pivot`; the command should emit `NO_OP_TRACE` with that routing.
- **Reversible via git**. The revision is written to the artifact and the critique and diff summary are shown inline, so the user sees what changed and why. Git is the recovery path if the revision is over-eager.

Required output:
1. Detected artifact type (one of the three; or `NO_OP_TRACE` with reason)
2. `## Critique`: numbered list per rubric criterion; `PASS | FAIL | WEAK -- reasoning`
3. `## Revised draft`: full content of the revised artifact (preserve unchanged sections verbatim; revise only criterion-driven items)
4. `## Diff summary`: one paragraph naming what changed from original to revised (which criteria triggered which changes)
5. `## Not applied`: bulleted recommendations the critique surfaced but the revision did NOT incorporate (each item: "criterion X -- specific judgment needed from user -- deferred")
6. Recommended next command (typically the artifact's downstream consumer: `implement-approved-slice` after revising a slice; `pr-package` after revising PR_PACKAGE.md; `decision-interview` if the critique surfaced a missing decision)
7. Recommended editor mode (typically the downstream command's mode)
8. What should explicitly NOT be done now (e.g., do not run the original authoring command again; the revision IS the next step)

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
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- The detected artifact type is named explicitly OR a `NO_OP_TRACE` with routing is emitted.
- The `## Critique` section addresses every numbered criterion from the locked rubric (7 per artifact type); no invented criteria; no skipped criteria.
- The `## Revised draft` preserves all PASS content verbatim and revises only FAIL / WEAK items that do not require user judgment.
- The `## Diff summary` traces each change to the criterion that triggered it.
- The `## Not applied` section explicitly defers items needing user judgment.
- `### Artifact changes` marks the revised artifact `APPLIED` in every mode (ADR-0199, ADR-0220).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for rubric fidelity (every criterion addressed; no invented dimensions), revision conservatism (preserve PASS content verbatim; defer judgment-driven items to the user), and traceability (every change in the revised draft maps to a criterion in the critique).

---
name: verify-against-rubric
description: Spawn a stateless sub-agent (Claude Code Task tool, Cursor agent mode, or equivalent) with ONLY the artifact path plus the locked rubric plus read-only tools. Sub-agent returns a structured verdict (satisfied, needs_revision, or failed) plus per-criterion feedback. Distinct from self-critique-and-revise (same-context; rewrites in place). Use after pr-package, contract-signoff, or implement-approved-slice on HIGH-complexity slices when independent verification matters more than throughput. Do not use on LOW or MEDIUM complexity slices (self-critique-and-revise covers those at lower cost), when no locked rubric exists yet or the rubric is vague (run resolve-contract-gaps first), or when no active task folder exists yet (run task-init first).
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2200
  suggested-model: claude-sonnet-4-6
---
# verify-against-rubric

Act as a senior/staff engineer dispatching an independent stateless verification sub-agent against a locked rubric.

Goal:
Verify a task artifact (PR package, signed-off contract, executed slice) against a locked rubric using an isolated sub-agent context. The sub-agent sees only the artifact + the rubric (no TASK_STATE.md, no DECISIONS.md, no prior conversation). Sub-agent returns a structured verdict; main thread persists it to `VERIFICATION_LOG.md` and emits the next-step handoff. Closes the same-context bias gap that `self-critique-and-revise` (in-thread) inherits. Per ADR-0033 and Anthropic Outcomes (2026-05-06; +10pp success vs same-context critique).

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
- artifact path (PR_PACKAGE.md, contract document, slice file, etc.)
- rubric source: EITHER inline rubric (criteria list with verdict thresholds) OR reference to a section in IMPLEMENTATION_PLAN.md or DECISIONS.md (path + section anchor)
- task folder path
- optional: prior verdict id (for delta check vs previous run)

Task repository files to update:
- VERIFICATION_LOG.md (new optional task file; append-only)
- TASK_STATE.md (`## Last completed step` references the new verdict id)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact, Mode B full, or Mode C parallel-fanout when triggered).
- **Step 1: Lock the rubric.** Either accept the inline rubric as-is or extract the referenced section from IMPLEMENTATION_PLAN.md / DECISIONS.md. The rubric MUST list discrete criteria (each verifiable independently). Refuse with NO_OP_TRACE if the rubric is vague ("looks good", "feature works") -- route to `resolve-contract-gaps` first.
- **Step 2: Spawn sub-agent (the load-bearing step).** Invoke the host's stateless sub-agent primitive (Claude Code `Task` tool with `subagent_type: general-purpose`; Cursor agent mode subagent; Codex agents). The sub-agent receives ONLY:
  - The artifact file path (read-only)
  - The rubric (verbatim)
  - Instruction: "Verify the artifact against each criterion. Return a structured verdict: per criterion, mark satisfied / needs_revision / failed with a 1-2 line reason. Then an overall verdict."
  - NO TASK_STATE.md, NO DECISIONS.md, NO prior conversation history.
- **Step 3: Receive verdict.** Sub-agent returns the verdict in the agreed structured format. Main thread does NOT re-evaluate or override the verdict; it persists it.
- **Step 4: Persist to VERIFICATION_LOG.md.** Append a new entry with: verdict id (auto-incremented), date, artifact path, rubric source, per-criterion verdict, overall verdict, sub-agent identifier (Claude Code Task ID or equivalent), and the timestamp.
- **Step 5: Update TASK_STATE.md.** Per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`, update `## Last completed step` to reference the new verdict id.
- **Step 6: Emit handoff.** If verdict = satisfied: route to the next planned step (often `pr-package` submission or the next slice). If needs_revision: route to `implement-slice-complement` (with verdict feedback inline). If failed: route to `direction-adjust` or `decision-interview` based on the failure type.
- Do NOT use this command on LOW or MEDIUM complexity slices: `self-critique-and-revise` is the cheaper in-thread alternative.
- Do NOT spawn sub-agent without an explicit locked rubric. Vague rubrics produce vague verdicts.

Required output:
1. Rubric source (inline or referenced section)
2. Number of criteria evaluated
3. Per-criterion verdict (table)
4. Overall verdict (satisfied / needs_revision / failed)
5. Sub-agent identifier (Task ID or equivalent)
6. Verdict id in VERIFICATION_LOG.md
7. Recommended next command based on verdict

### Review prompt scaffold (optional)
<!-- shared:xml-review-scaffold -->
When the review directives in this command are ambiguous, parse them in three labeled parts: Instructions (what to do), Context (background, not a rule), and Constraints (hard limits that override the rest). This separation is optional and adds signal only where reviewers report ambiguity; do not tag mechanically or let it bloat the prompt.
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
- Rubric is locked and discrete (criteria are independently verifiable).
- Sub-agent invoked with isolated context (no TASK_STATE.md, no DECISIONS.md, no prior history).
- Verdict returned with per-criterion breakdown and overall classification.
- VERIFICATION_LOG.md updated with the verdict entry.
- TASK_STATE.md `## Last completed step` references the verdict id.
- Handoff routes based on verdict: satisfied -> next step, needs_revision -> implement-slice-complement, failed -> direction-adjust or decision-interview.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the rubric. If the rubric is vague, the verdict is vague. Refuse vague rubrics. The sub-agent isolation is the load-bearing differentiator vs `self-critique-and-revise`; do not collapse them.

<!-- cache-breakpoint -->

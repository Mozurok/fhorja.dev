---
name: atom-audit
description: Produce ATOM_AUDIT.md table auditing every atom component against COMPONENT_GUIDELINES.md (memo, callbacks, inline styles, press anim, touch target, a11y, reduced motion). Output is the table; fixes flow through normal slice pipeline. Use when 2-4 weeks have passed since last audit, when 5+ new atoms shipped, or when COMPONENT_GUIDELINES has a new normative rule. Do not use when no atoms exist (run design-bootstrap first) or when only a single atom needs review (use design-spec-review instead). For 6 or more atoms, use atom-audit-fleet.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2200
  suggested-model: claude-sonnet-4-6
---
# atom-audit

Act as a design system auditor producing a tier-scoped audit table of all atom components against the project's shared component guidelines.

Goal:
Scan every atom under `packages/design-system/src/atoms/` (or the project's equivalent path), check each against the rules in `docs/research/COMPONENT_GUIDELINES.md`, and generate or refresh `docs/research/ATOM_AUDIT.md` as a table with one row per atom and one column per guideline. The table is the deliverable; fixes flow through normal slice pipeline.

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
- project workspace path
- path to atom components (default: `packages/design-system/src/atoms/`)
- path to COMPONENT_GUIDELINES.md (default: `docs/research/COMPONENT_GUIDELINES.md`)
- path to ATOM_AUDIT.md (default: `docs/research/ATOM_AUDIT.md`; created if absent from `templates/ATOM_AUDIT.md`)

Task repository files to update:
- TASK_STATE.md (add audit summary with `total_changes_needed` count and `cleared_since_previous_run` delta)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Read COMPONENT_GUIDELINES.md.** Parse the rules (G-NN) and the columns they map to in ATOM_AUDIT.md (memo, callbacks, inline-styles, press-anim, touch-target, a11y, reduced-motion). Confirm the column set matches between the guidelines and the audit table; if guidelines added a rule with no audit column, prompt to extend the table first.
- **Step 2: Enumerate atoms.** List every directory under the atoms path. For each, locate the main component file (`<Name>/index.tsx` or `<Name>/<Name>.tsx`).
- **Step 3: Check each rule per atom.**
  - **memo (G-01):** is the component wrapped in `React.memo` or `forwardRef + memo`? Mark passing if memoed OR if props count is below threshold (rule states ≥5 props OR list-rendered). Use heuristic: count props in TS interface.
  - **callbacks (G-02):** count inline arrow callbacks that should be `useCallback`-wrapped. Read passes when 0.
  - **inline-styles (G-03):** count `style={{...}}` (object-literal) occurrences. Read passes when 0.
  - **press-anim:** if the component handles press, is the anim via `useAnimatedPress` / Reanimated UI-thread? `useState` transform is a failure.
  - **touch-target (G-04):** does the component define minimum 44pt tap target (or compose via padding/hitSlop)?
  - **a11y (G-06):** does the component have `accessibilityRole`, `accessibilityLabel` when icon-only, `accessibilityState` for interactive variants?
  - **reduced-motion (G-05):** if the component has transform/translate animation, does it check `useReducedMotion()` or fall back to opacity?
- **Step 4: Compute changes_needed per atom.** Sum the failing rules per row. Persist the integer in the rightmost column.
- **Step 5: Update audit history table.** Append a row to the "Audit history" section: date, who ran it (`atom-audit` v1), total changes_needed, cleared_since_previous_run (delta from previous total).
- **Step 6: Group findings for follow-up.** In the output (NOT in the file), suggest the top 3 fix groupings by rule (e.g., "5 atoms missing reduced-motion check"), each as a candidate slice for `task-init`.
- Do NOT implement fixes here. This command produces the audit only.
- If COMPONENT_GUIDELINES.md does not exist, NO_OP_TRACE: route to `design-bootstrap` (which copies the template) or to a slice that creates the guidelines from `templates/COMPONENT_GUIDELINES.md`.

Required output:
1. Atom count and audit summary (total `changes_needed`, delta vs previous run)
2. Per-rule failure breakdown (which rules have most failing atoms)
3. Top 3 suggested fix groupings (each is a candidate slice)
4. Path to the updated `ATOM_AUDIT.md`
5. Recommended next command

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
- Every atom under the atoms path has a row in ATOM_AUDIT.md.
- Every rule from COMPONENT_GUIDELINES.md is represented as a column.
- `changes_needed` integer per row matches the count of failing rules in that row.
- Audit history row appended for this run with date + total + cleared delta.
- Top 3 fix groupings suggested in the output (NOT in the file).
- No code fixes applied by this command; output explicitly says "produces audit only, fixes flow through task-init".
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The output table must be machine-scannable and audit-decisions traceable to the source rule in COMPONENT_GUIDELINES.md. A reader should see in 30 seconds what to fix next.

<!-- cache-breakpoint -->

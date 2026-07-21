---
name: design-spec-review
description: Review a component or screen implementation against its spec doc for alignment on variants, states, accessibility, tokens, and visual fidelity. Distinct from review-hard (general risk) and repo-consistency-sweep (pattern matching). Activates when a slice's declared Scope touches a design-system button, icon, or component convention file (a shared atom/component under a design-system package) with no cited design-spec-review pass for that change. Use when a design system component or screen has been implemented and you want to verify it matches the documented spec. Do not use when no spec exists (write one first with component-spec or screen-spec).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2500
  suggested-model: claude-sonnet-4-6
---
# design-spec-review

Act as a design system QA engineer verifying implementation fidelity against a documented spec.

Goal:
Compare the implemented component or screen code against its spec doc. Check that all specified variants are implemented, all mandatory states are handled, accessibility props are present, tokens are used correctly (no hardcoded values), motion/haptics match the spec, and the TypeScript API matches the documented interface. Produce a findings list with P0/P1/P2 severity.

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
- component or screen name
- path to the spec doc (`docs/research/components/<tier>/<name>.md` or `docs/app/screens/<persona>/<nn>-<slug>.md`)
- path to the implementation code
- project workspace path

Task repository files to update:
- TASK_STATE.md (add review summary)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Check 1: Variants.** Are all variants from the spec's section 3 implemented? Are variant names consistent (spec says `primary`; code uses `primary`)?
- **Check 2: Sizes.** Are all documented sizes implemented? Do sizes meet the 44pt touch target minimum?
- **Check 3: States.** Are all 6 mandatory states handled (default, pressed, focused, disabled, loading, error)? Are additional states from the spec (empty, offline, selected) present if documented?
- **Check 4: Accessibility.** Does the implementation include: `accessibilityRole` / `role`, `accessibilityLabel` / `aria-label` (for icon-only), `accessibilityState` forwarding (disabled, checked, busy)? Does contrast meet the documented ratios?
- **Check 5: Tokens.** Are design tokens used for all colors, spacing, typography, radii, elevation? No hardcoded hex/pt values?
- **Check 6: Motion and haptics.** Does the implementation match the spec's motion (duration, easing, scale) and haptics (feedback style per variant)?
- **Check 7: TypeScript API.** Does the actual props interface match the spec's section 12? Are prop names, types, and defaults consistent?
- **Check 8: Storybook story.** Does a story exist for this component? Does it showcase all variants and key states?
- **Check 9: Anti-patterns.** Does the implementation violate any of the spec's section 14 (Do not) items?
- **Check 10: Platform specifics.** Are iOS/Android/Web differences handled as documented in the spec's section 9?
- **Check 11: Visual fidelity (P2-5, careers-page dogfooding 2026-06-23).** For a HIGH-complexity or heavily-styled component or screen AND when a design MCP is reachable, pull the source via the MCP (`get_screenshot`, and `get_variable_defs` for token values) and compare it to the running implementation (a screenshot at the same state). Report visual gaps (spacing, borders, radii, photo arrangement, copy) as findings with the node id. When the design MCP is unavailable, record `Check 11: deferred (design MCP unavailable)` rather than skipping silently. This is the gate that would have caught the careers-page fidelity drift (corner markers, double borders, radii) before the user did, by hand.
- Return no-op if no spec doc exists for the component (route to `component-spec` instead).
- If the implementation is faithful to the spec, say so clearly.

Required output:
1. Component/screen identity
2. Checks passed vs failed (11 checks; Check 11 may be `deferred` when the design MCP is unavailable)
3. Findings (P0/P1/P2 with check number, file:line, description, spec reference)
4. Overall verdict (faithful / needs fixes / significant drift)
5. Recommended next command (route visual-fidelity gaps to `implement-slice-complement` before `pr-package`)

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
- All 11 checks are explicitly reported (passed, failed with evidence, or Check 11 `deferred` when the design MCP is unavailable).
- Findings reference the spec section number and code file:line.
- If implementation is faithful, verdict says so clearly.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Every finding traces to a specific spec section and a specific code line. No invented discrepancies.

<!-- cache-breakpoint -->

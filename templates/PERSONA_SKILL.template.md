---
name: <persona-id-kebab-case>
description: <one-line description of the persona's expertise and when it activates; <=1024 chars per Agent Skills spec; should mention concrete triggers and explicit "do not use" conditions, mirroring the command-description convention>
metadata:
  category: <one of: project-initialization | state-and-navigation | discovery-and-scoping | database-context | contract-and-decision-hardening | planning-and-validation | execution-and-closure | delivery-and-communication | prompt-tooling>
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  token-budget: <integer; budget your operating-rules body fits within; bump per ADR-0013 if you exceed>
  suggested-model: claude-sonnet-4-6
  # Persona-specific fields (K.6/K.8). Optional at L1 launch; required by L3+:
  triggers:
    - <one-line description of a substrate signal that activates this persona>
    - <example: "DECISIONS.md mentions auth without an RLS policy locked">
  maturity_level: L1   # L1=shadow, L2=advisory, L3=gated, L4=peer, L5=autonomous (per wos/substrate-peers.md ## Maturity ladder hook)
  owned_sections: []   # empty at L1/L2; one low-risk section at L3; full ownership at L4 (per the maturity ladder)
---
# <persona-id-kebab-case>

Act as <one-line role declaration, e.g. "a senior RLS+Auth Boundary Auditor reviewing the active task's Supabase RLS posture">.

Goal:
<2-3 sentences. What value does this persona add that a generic command cannot? What's the load-bearing differentiator? Be specific about the failure mode it's designed to catch.>

This persona is folder-shaped (K.3 dual layout): SKILL.md is canonical; additional assets (rubrics, examples, MCP references) MAY live alongside in `commands/<persona-id>/` and are NOT propagated by `sync-shared-blocks.sh`.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Substrate access (per `wos/substrate-peers.md ## Personas CUSTOM`):
- R access: TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SOURCE_OF_TRUTH.md (all four task-memory files).
- P access (PROPOSED blocks only at L1; promotion gated by maturity ladder):
  - `TASK_STATE.md ## Observations` (append-only freeform)
  - `TASK_STATE.md ## Risks to watch`
  - `DECISIONS.md ## Locked decisions` (PROPOSED block under a new D-N draft)
  - `IMPLEMENTATION_PLAN.md ## Risks and mitigations`
- NEVER write substrate at L1. Emit Handoff routing to the owner command per Pattern A in `wos/substrate-peers.md`.

Required inputs:
- active task folder path
- <persona-specific input 1>
- <persona-specific input 2>
- optional: <any optional inputs>

Task repository files to update:
- non-owned substrate sections: only via PROPOSED blocks (per `wos/substrate-peers.md ## Personas CUSTOM`); `approve-proposed` promotes. The persona's owned section (frontmatter `owned_sections`), once promoted to L3, is written directly.
- <persona-specific output file if any, e.g. `<task>/<PERSONA_REPORT>.md`>

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04):** for every write to a substrate section (the 4 task-memory files plus the fleet-substrate files per `wos/substrate-peers.md ## Fleet-substrate files`), emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. Shadow mode at launch -- writers emit, no reader enforces.
- **Step 1: <persona-specific verb>.** <One-sentence rule.>
- **Step 2: <persona-specific verb>.** <One-sentence rule.>
- **Step 3: <persona-specific verb>.** <One-sentence rule.>
- <Add steps as needed; keep each one tight and verifiable.>
- Do not implement code; persona output is analysis or PROPOSED blocks only at L1.

Required output:
1. <Output item 1>
2. <Output item 2>
3. <Output item 3>
4. Recommended next command (must exist in `commands/*.md`; verify against directory listing before output).

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
- <Persona-specific success criterion 1>
- <Persona-specific success criterion 2>
- Substrate access respected: no direct writes to substrate at L1; PROPOSED blocks only; Handoff routes to the owner command for promotion.
- Shared contract: **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
<One paragraph stating what "good" looks like for this persona. Be concrete about the failure mode the persona prevents and what signal proves the output is load-bearing.>

<!-- cache-breakpoint -->

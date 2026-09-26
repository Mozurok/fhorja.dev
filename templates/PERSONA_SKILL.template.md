---
name: <persona-id-kebab-case>
description: <one-line description of the persona's expertise and when it activates; <=1024 chars per Agent Skills spec; should mention concrete triggers and explicit "do not use" conditions, mirroring the command-description convention>
metadata:
  category: <one category from WORKFLOW_OPERATING_SYSTEM.md ## Command categories, the set lint checks as VALID_CATEGORIES in scripts/lint-commands.sh; the shipped personas mostly use audit-and-sweep>
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5
  # Persona-specific fields (K.6/K.8). Optional at L1 launch; required by L3+:
  triggers:
    - <one-line description of a substrate signal that activates this persona>
    - <example: "DECISIONS.md mentions auth without an RLS policy locked">
  # maturity_level: L1=shadow, L2=advisory, L3=gated, L4=peer, L5=autonomous (per wos/maturity-ladder.md)
  maturity_level: L1
  # owned_sections: empty at L1/L2; one low-risk section at L3; full ownership at L4. Keep comments off
  # this line: lint parses the value as a YAML inline list.
  owned_sections: []
---
# <persona-id-kebab-case>

Act as <one-line role declaration, e.g. "a senior RLS+Auth Boundary Auditor reviewing the active task's Supabase RLS posture">.

Goal:
<2-3 sentences. What value does this persona add that a generic command cannot? What's the load-bearing differentiator? Be specific about the failure mode it's designed to catch.>

This persona is folder-shaped (K.3 dual layout): SKILL.md is canonical; additional assets (rubrics, examples, MCP references) MAY live alongside in `commands/<persona-id>/` and are NOT propagated by `sync-shared-blocks.sh`.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
<Filled by `scripts/sync-shared-blocks.sh`. After copying this template to `commands/<persona-id>/SKILL.md`, run it once: it replaces every `<!-- shared:<name> -->` block with the current text of `commands/_shared/<name>.md`.>

Required inputs:
- active task folder path
- <persona-specific input 1>
- <persona-specific input 2>
- optional: <any optional inputs>

Substrate access (per `wos/substrate-peers.md ## Personas CUSTOM`):
- R access: TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SOURCE_OF_TRUTH.md (all four task-memory files).
- P access (PROPOSED blocks only at L1; promotion gated by maturity ladder):
  - `TASK_STATE.md ## Observations` (append-only freeform)
  - `TASK_STATE.md ## Risks to watch`
  - `DECISIONS.md ## Locked decisions` (PROPOSED block under a new D-N draft)
  - `IMPLEMENTATION_PLAN.md ## Risks and mitigations`
- NEVER write substrate at L1. Emit Handoff routing to the owner command per Pattern A in `wos/substrate-peers.md`.

Task repository files to update:
- non-owned substrate sections: only via PROPOSED blocks (per `wos/substrate-peers.md ## Personas CUSTOM`); the owner command promotes them, or `approve-proposed` on request (ADR-0199). The persona's owned section (frontmatter `owned_sections`), once promoted to L3, is written directly.
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

### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Standard output layout (required)
<!-- shared:standard-output-layout -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Artifact changes
<!-- shared:artifact-changes-default -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Command transcript
<!-- shared:command-transcript-standard -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Handoff
<!-- shared:handoff-body -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Definition of done (command output)
- <Persona-specific success criterion 1>
- <Persona-specific success criterion 2>
- Substrate access respected: no direct writes to substrate at L1; PROPOSED blocks only; Handoff routes to the owner command for promotion.
- Shared contract: **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
<One paragraph stating what "good" looks like for this persona. Be concrete about the failure mode the persona prevents and what signal proves the output is load-bearing.>


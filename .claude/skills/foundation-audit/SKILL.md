---
name: foundation-audit
description: |-
  Compare design tokens in code against foundation docs and optionally Figma variables to detect drift (tokens added without documentation, documented tokens not in code, value mismatches). Use when the design system has been evolving and you want to verify foundations are in sync. Do not use when no foundation docs exist (run design-bootstrap first).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
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
    - full
  provenance: first-party
  token-budget: 2000
  suggested-model: claude-sonnet-4-6
---

Act as a design system auditor checking token-level consistency between documentation, code, and Figma.

Goal:
Compare the project's design tokens (in code) against the foundation docs (in `docs/research/foundations/`) to detect drift: tokens that exist in code but are not documented, documented tokens that are not in code, and value mismatches between the two. Optionally cross-reference against Figma variables via MCP if available. Produce a drift report.

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
- path to token files (`packages/design-system/src/tokens/` or `tokens/*.json`)
- path to foundation docs (`docs/research/foundations/`)
- optional: Figma file URL (for 3-way comparison: Figma vs docs vs code)

Task repository files to update:
- TASK_STATE.md (add audit summary)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Read token files.** Parse all token definitions from the code (whether .ts exports or DTCG JSON). Build a flat list: `category.group.name = value`.
- **Step 2: Read foundation docs.** Parse all `## Tokens` tables from foundation docs. Build a flat list: `category.group.name = value`.
- **Step 3: Compare code vs docs.**
  - **In code, not in docs**: token exists in code but is not documented. Flag as `undocumented`.
  - **In docs, not in code**: token is documented but missing from code. Flag as `unimplemented`.
  - **Value mismatch**: token exists in both but values differ. Flag as `drift`.
  - **Name mismatch**: similar token exists under a different name (fuzzy match). Flag as `possible rename`.
- **Step 4: (Optional) Compare vs Figma.** If a Figma URL is provided, call `get_variable_defs` and build a third flat list. Cross-reference all three sources. Flag tokens that are in Figma but not in code, in code but not in Figma, or with value mismatches.
- **Step 5: Generate drift report.** Categorize findings by foundation (color, typography, spacing, etc.) and severity:
  - P1: value mismatch (code shows different value than docs or Figma; visual inconsistency)
  - P2: undocumented token (works but not governed) or unimplemented token (documented but not available)
- **Step 6: Suggest fixes.** For each finding, recommend: update the doc, update the code, or create an OPEN_QUESTIONS entry if the correct value is unclear.

Required output:
1. Summary: N tokens in code, M tokens in docs, K tokens in Figma (if checked)
2. Drift findings (undocumented, unimplemented, value mismatch, possible rename)
3. Per-foundation breakdown (color: X findings, spacing: Y findings, etc.)
4. Overall health: in-sync / minor drift / significant drift
5. Recommended next command

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
- All tokens from code AND docs are accounted for in the comparison.
- Each drift finding has: category, token name, code value, doc value, severity, suggested fix.
- If Figma was included: 3-way comparison is complete.
- If everything is in sync, health says so clearly.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Every finding is grounded in actual code and doc values, not assumptions. If tokens are in sync, say so.

<!-- cache-breakpoint -->

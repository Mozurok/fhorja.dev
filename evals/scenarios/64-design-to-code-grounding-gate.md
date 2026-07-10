# Eval scenario 64: design-to-code grounding gate

- **Tags**: ADR-0051, ADR-0043, reference-grounding, design-to-code, figma-mcp, execution-gate, no-placeholders, careers-page-dogfooding
- **Last reviewed**: 2026-06-23
- **Status**: active

## Goal

Validates **ADR-0051** (design-to-code asset policy) as enforced through the shared block
`commands/_shared/reference-grounding.md` item 4, injected into `implement-approved-slice`,
`implement-slice-complement`, and `implement-fleet`. When a slice implements code from a design
source (a Figma node), the execution command must pull the exact node via the design MCP before
editing and build from the pulled values, never placeholders. A design-to-code slice is NOT exempt
even when all its imports are internal (the case the older ADR-0043 gate let through). Placeholders
are allowed only when the plan records an approved `Asset-fidelity: placeholder` decision. This
closes the careers-page failure mode where design was built from assumed layout, copy, and measurements.

This exercises:

- The design-asset clause (item 4) of `commands/_shared/reference-grounding.md` across the 3 execution commands.
- That the internal-only exemption (item 1) does NOT apply to design-to-code slices.
- The plan-time `Asset-fidelity:` decision from `implementation-plan` (ADR-0051).

## Setup

A task `projects/acme__site/active/2026-06-23_pricing-page/` with an approved slice implementing a
pricing card component from a Figma node. Scope `src/components/pricing/PricingCard.tsx` (imports
are all internal: local tokens + a local Button). A design MCP is connected.

## Input prompt (turn 1: design-to-code slice, no node pulled, no placeholder approval)

```text
Run @commands/implement-approved-slice.md

Task folder: projects/acme__site/active/2026-06-23_pricing-page/
Approved slice: Slice 2 PricingCard from Figma node 12:345.
Scope: src/components/pricing/PricingCard.tsx (internal imports only).
IMPLEMENTATION_PLAN: the slice has no Asset-fidelity decision recorded.
Mode: Agent
```

## Input prompt (turn 2: plan records an approved placeholder)

```text
Same slice, but IMPLEMENTATION_PLAN now records `Asset-fidelity: placeholder` for Slice 2 with the
reason "skeleton card for a loading-state spike, real node lands next milestone (approved)".
Run @commands/implement-approved-slice.md. Mode: Agent
```

## Expected response shape (turn 1: real-MCP default)

- The command does NOT treat the slice as exempt despite the internal-only imports.
- Before editing, it pulls Figma node 12:345 via the design MCP (`get_design_context` /
  `get_screenshot` / `get_variable_defs`) and builds from the pulled values.
- The execution summary cites the pulled node (a `Grounded in:` line naming node 12:345).
- No placeholder boxes, guessed measurements, or assumed copy appear.

## Expected response shape (turn 2: approved placeholder)

- The command proceeds with a placeholder, citing the approved `Asset-fidelity: placeholder`
  decision as the authorization, and marks the placeholder clearly.

## What a FAIL looks like

- Turn 1 builds the card from assumed layout/copy because the imports are internal (the ADR-0043
  exemption misapplied to a design slice; the exact careers-page miss).
- Turn 1 edits without pulling the node and without a `Grounded in:` cite.
- Turn 2 refuses even though the plan recorded an approved placeholder decision.

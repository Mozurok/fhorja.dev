# ADR-0051: Design-to-code slices default to real MCP content, not placeholders

- **Status**: Accepted
- **Date**: 2026-06-23
- **Tags**: design-to-code, reference-grounding, execution-gate, figma-mcp, no-placeholders, shared-block, dogfood, adr-0043-amendment

## Context

The careers-page dogfooding session (2026-06-23) surfaced a gap. The user's working
rule was explicit: no assumptions, no placeholders, build strictly from the Figma MCP. The
approved plan (and the WOS `implementation-plan` command) read "base structure first" as license
to use placeholder images and copy, and `implement-approved-slice` (plus the fleet workers and
`implement-slice-complement`) began building from placeholders. The user interrupted to reject
that. The model pivoted to a Figma-MCP-driven approach only because it was in-context, not
because any rule required it. The correction had to be re-taught and only survived as a per-user
project memory.

The WOS already has a reference-grounding execution gate (ADR-0043): before editing, ground every
external contract in captured references and refuse if uncaptured. That gate's detection step
scans the slice's imports and diff for external libraries, SDKs, APIs, and documented protocols. A
Figma node is also an external contract, but it is not an import, so design-to-code slices fall
outside the gate. Worse, the gate explicitly exempts a slice whose imports and diff are entirely
internal, which is exactly the shape of a design-to-code component slice. So the one kind of slice
most prone to guessing had no grounding gate at all.

A separate dogfooding finding from the same session (ADR-0042 reframe) showed that a rule which
exists but is only stated softly gets skipped under load, while a hard gate holds: the careers-page run
DID honor the ADR-0043 reference-grounding gate for the Ashby API. The lesson is to encode the
design-asset rule as the same kind of hard execution gate, not as advice.

## Decision

Design-to-code slices default to real MCP-pulled content. Placeholders are an explicit, approved
decision, never a silent default. Two parts.

1. Plan-time. `implementation-plan` records a per-slice asset-fidelity decision for any
   design-to-code slice: `real-MCP` (the slice pulls the exact node before editing) or
   `approved-placeholder` (with a one-line reason and the approval). When a slice implements from a
   design source and nothing is stated, the default is `real-MCP`.

2. Execution-time. The reference-grounding shared block
   (`commands/_shared/reference-grounding.md`, consumed by `implement-approved-slice`,
   `implement-slice-complement`, and `implement-fleet`) gains a design-asset clause. A Figma node,
   screen, or component spec is an external contract. Before a design-to-code edit you MUST pull
   the exact node via the design MCP (`get_design_context`, `get_screenshot`, `get_variable_defs`,
   and `download_assets` for real assets) and build from the pulled values: no placeholder boxes,
   guessed measurements, or assumed copy. A design-to-code slice is NOT exempt even when all its
   imports are internal. If the node is unavailable, stop and ask for the link rather than
   approximating. Placeholders are allowed only when `IMPLEMENTATION_PLAN.md` records an approved
   `Asset-fidelity: placeholder` decision for the slice.

This amends ADR-0043 by widening "external contract" to include design assets, reusing the same
shared block and the same refuse-when-ungrounded shape rather than adding a new command or gate.

## Consequences

### Positive

- The careers-page failure mode is closed by a rule, not by luck. The most guess-prone slice now has a
  grounding gate.
- The gate lives in one shared block, so all three execution commands inherit it with no drift.
  The careers-page session used `implement-slice-complement` heavily for design work, and it is a
  consumer, so it is covered.
- Placeholders become a visible, approved choice in the plan instead of a silent shortcut.
- Matches the evidence that hard gates hold: the same session honored the ADR-0043 API gate.

### Negative

- Adds tokens to the shared block and therefore to its three consumers. `implement-approved-slice`
  is already near its ADR-0013 token budget; the overage is warn-only and is flagged for a separate
  budget re-baseline, not silenced here.
- A prose gate routes probabilistically. A reachable Figma MCP is required for the pull; when it is
  absent the rule degrades to "stop and ask for the asset", the same shape as `capture-references`
  for an uncaptured API.

### Neutral

- The gate fires only for design-to-code slices. Non-design slices are unaffected, and the existing
  internal-only exemption still applies to them.

## Alternatives considered

### Alternative 1: a separate design-only command or gate

Rejected. The reference-grounding gate already models "ground the external contract before
editing." A Figma node is just another external contract, so generalizing the existing gate is DRY
and reaches all three execution commands without a new command (no 4-registry cost, no count-marker
bump, no skills rebuild for a new command).

### Alternative 2: encode it only at plan-time in implementation-plan

Rejected. The careers-page miss happened at execution (`implement-slice-complement` and fleet workers),
not at plan time. A plan-time field with no execution gate is skippable, which is the exact
failure mode ADR-0042's reframe documented.

### Alternative 3: leave it to project memory

Rejected. The no-placeholders memory created during the careers-page session is per-user and not
portable across hosts or contributors. A behavior this load-bearing belongs in the WOS contract.

## References

- ADR-0043: reference grounding execution gate (this widens it to design assets).
- ADR-0042: waves-aware routing reframe (the "a soft rule gets skipped, a hard gate holds" lesson).
- ADR-0001: PROPOSED-by-default write policy (placeholders as an explicit approved decision).
- ADR-0013: per-command token budget (the warn-only overage this adds to the shared-block consumers).
- `commands/_shared/reference-grounding.md`: the shared gate this extends.
- The careers-page dogfooding session, 2026-06-23 (the evidence).

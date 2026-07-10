# Eval scenario 66: design-spec-review visual-fidelity check (Check 11)

- **Tags**: P2-5, design-spec-review, visual-fidelity, figma-mcp, screenshot-diff, careers-page-dogfooding
- **Last reviewed**: 2026-06-23
- **Status**: active

## Goal

Validates **Check 11 (visual fidelity)** in `commands/design-spec-review.md` (careers-page dogfooding
P2-5). For a HIGH-complexity or heavily-styled component AND a reachable design MCP, the review must
pull the source via the MCP (`get_screenshot`, `get_variable_defs`) and compare it to the running
implementation, reporting visual gaps with the node id and routing gaps to `implement-slice-complement`
before `pr-package`. When the design MCP is unavailable, the check is recorded as `deferred`, never
skipped silently. This is the gate that would have caught the careers-page fidelity drift (corner markers,
double borders, radii) before the user did, by hand.

This exercises:

- Check 11 firing on HIGH-complexity + reachable MCP, and reporting node-anchored gaps.
- The `deferred` record when the MCP is unavailable (no silent skip).
- Routing visual gaps to `implement-slice-complement` before `pr-package`.

## Setup

A task with a documented spec for a complex hero collage component and its implementation. The
component is HIGH-complexity (rotated overlapping photos, a note card).

## Input prompt (turn 1: MCP reachable, a real gap)

```text
Run @commands/design-spec-review.md

Component: HeroCollage (HIGH complexity).
Spec: docs/research/components/organisms/hero-collage.md
Code: src/components/careers/CareersPeopleSection.tsx
Design MCP: connected. The Figma node shows square photos; the implementation rounds the corners.
Mode: Ask
```

## Input prompt (turn 2: MCP unavailable)

```text
Same review, but no design MCP is connected this session.
Run @commands/design-spec-review.md. Mode: Ask
```

## Expected response shape (turn 1: MCP reachable)

- All 11 checks are reported. Check 11 pulls the Figma screenshot and flags the border-radius gap
  (square in Figma vs rounded in code), citing the node id.
- The verdict routes the visual gap to `implement-slice-complement` before recommending `pr-package`.

## Expected response shape (turn 2: MCP unavailable)

- Check 11 is reported as `deferred (design MCP unavailable)`, not skipped silently.
- The other 10 checks still run.

## What a FAIL looks like

- Turn 1 reports only 10 checks (Check 11 missing), the pre-P2-5 behavior that let visual drift
  reach the user.
- Turn 1 finds the radius gap but recommends `pr-package` without routing the fix first.
- Turn 2 silently omits Check 11 instead of recording it `deferred`.

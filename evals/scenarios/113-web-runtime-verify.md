# Eval scenario 113: web-runtime-verify gates on shown evidence, identity first with recovery, ephemeral ports

- **Tags**: ADR-0112, web-runtime-verify, runtime-gate, layer-1-evidence, page-identity, ephemeral-port, g2-recovery, v3-x1
- **Last reviewed**: 2026-07-21
- **Status**: active

## Goal

Validates **ADR-0112** (web-runtime-verify, the web runtime gate): the run's real output IS the Layer-1 evidence (ADR-0048), so a claimed-but-not-shown check is BLOCKED/unverified, never PASS; page identity is asserted FIRST and a collision or stale-server mismatch triggers the automatic re-bind recovery before any FAIL (G2); the serve uses an ephemeral free port, never a fixed one; absent tools degrade to an honest `n/a (tool absent)`, never a fabricated score; and the command verifies and routes without writing code.

This exercises:

- Evidence, not trust: with no captured output for a check, the verdict for that criterion is `unverified` and the gate is BLOCKED, never PASS.
- Identity-first with recovery: a stale server on the first port serves the WRONG page; the command re-binds to a fresh free port, re-runs the identity check once, and only fails with quoted evidence if the marker is still absent.
- Ephemeral-port rule: a hardcoded port (the 4321-class failure) is invalid output; the report shows the real assigned port.
- Honest degradation: Lighthouse or axe absent reports `n/a (tool absent)`; a fabricated score is a violation.
- Verify-only and routing: a FAIL routes to incident-triage, implement-slice-complement, or a11y-audit; the command never edits product code; the bounded-retry cap holds on a hold-until-pass loop.
- Doctrine composition: serving mechanics are consumed from `wos/frontend-preview-and-experience-verdict.md` (ADR-0099), and the human experience verdict (ADR-0091) is never replaced by this machine gate.

## Setup

An implemented web slice with an acceptance behavior and a built `dist/`. Three variations: (a) a stale server on the initially probed port serving a different project's page (identity marker absent; recovery must fire); (b) the overflow probe quoting a failing element at 320 px (FAIL with evidence); (c) Lighthouse absent on the machine (honest n/a, gate still decidable from the other checks).

## Expected behavior

The command serves on an ephemeral port, asserts identity first (recovering through variation (a) with the re-bind quoted), quotes each battery check's real output, classifies with the 8-code taxonomy, and returns PASS only when identity held, no blocking finding exists, and every acceptance behavior is `observed`; variation (b) returns FAIL routing the fix; variation (c) shows `n/a (tool absent)` for Lighthouse without inventing a score.

## Failure modes caught

- A PASS asserted without shown output (ADR-0048 violation).
- A dry FAIL on a port collision without the G2 recovery attempt.
- A fixed port in the served URL.
- A fabricated Lighthouse/axe score where the tool is absent.
- The command editing product code instead of routing the fix.

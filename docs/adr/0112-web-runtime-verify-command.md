# ADR-0112: web-runtime-verify, the web runtime gate

- **Status**: Accepted
- **Date**: 2026-07-21
- **Tags**: web-runtime-verify, runtime-gate, layer-1-evidence, page-identity, ephemeral-port, extends-adr-0048, mirrors-adr-0087, consumes-adr-0099, v3-x1

## Context

Fhorja had runtime gates for Godot scenes (the ADR-0085 family) and mobile apps (app-runtime-verify, ADR-0087, itself cloned from the Godot gate), plus a web-perf skill, but nothing routed a built web or static frontend through a runtime gate in the implement-to-close flow. The cross-model dogfood rounds showed the cost twice over: every gate of the briefs was web-runtime (WCAG focus and keyboard, no overflow 320 to 2560, LCP, CLS, zero console errors, Lighthouse), and with no owning command BOTH models improvised the entire harness from scratch per session: preview server, readiness poll, teardown, width sweep, browser discovery, axe, console capture, page identity. The verified v2 backlog ranked this gap first (item X1, absorbing the wrong-page finding P1 and the harness-improvisation findings N1, N2, N4).

Two guard-rails from that review are binding. G2: the wrong-page verifier in the dogfood was saved by re-binding the port and re-running, not by a dry fail, so the identity assertion must pair with automatic recovery or a port collision becomes a hard task blocker. G3 with ADR-0048: the live capture is the evidence; a stored fixture never substitutes.

## Decision

1. `commands/web-runtime-verify.md` is a first-class sibling of the two existing runtime gates, following the same clone lineage and discipline: capability-routed, MCP-agnostic about the browser runner, verifies and routes fixes, never writes code, three-way PASS/FAIL/BLOCKED verdict with the run's real output as Layer-1 evidence.
2. The command owns the whole browser gate: ephemeral-port serve (a fixed port is invalid output), bounded readiness poll, guaranteed teardown, page identity as the FIRST assertion with the G2 automatic re-bind recovery, then the standard battery (overflow sweep 320 to 2560, keyboard and focus walk, console capture, Lighthouse and axe with honest `n/a (tool absent)` degradation), an 8-code web taxonomy, and a per-criterion verdict.
3. Serving mechanics belong to `wos/frontend-preview-and-experience-verdict.md` (ADR-0099): one serving doctrine, two consumers (this machine gate and the ADR-0091 human experience verdict over the same served build). The command references, never duplicates.
4. Under Codex CLI the browser step fires early in the turn while a human is present (the wave-1 harness quirks rule; the 2h39 approval-stall class), and live capture is never replaced by a fixture.
5. The mandatory closure floor at the three closure homes is STAGED: the command lands first and earns dogfood evidence; the floor follows the ADR-0106 precedent (floors were added only after a real incident) as its own future change.

## Consequences

- No session improvises the web harness again; the wrong-page class is caught by the first assertion instead of surfacing as mysterious downstream failures.
- The gate composes with the existing closure machinery (a PASS feeds review-hard and the human verdict; a FAIL routes to incident-triage, implement-slice-complement, or a11y-audit) without any closure-home edit in this change.
- Accepted residual: until the staged floor lands, adoption is per-slice discipline (run the gate or record an explicit skip line), the same adoption model the Godot gate had before ADR-0085 forced it.

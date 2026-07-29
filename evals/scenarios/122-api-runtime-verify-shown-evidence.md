# Eval scenario 122: api-runtime-verify gates a backend surface on shown per-route evidence

- **Tags**: ADR-0120, api-runtime-verify, runtime-gate, layer-1-evidence, capability-routed, d-6
- **Last reviewed**: 2026-07-27
- **Status**: active

## Goal

Validates the backend HTTP gate D-6 locked as a sibling rather than a widened web gate: per route it records the request made, the HTTP status, the response content-type, and the observed body shape, and a route whose output is not shown is `unverified`, never PASS.

## Setup

An implemented backend slice with an acceptance behavior and a route set. Three variations: (a) one route returns the wrong status; (b) one route's output was never captured; (c) a probing tool is absent on the machine.

## Expected behavior

The command reports per route with its real output quoted, classifies findings with its taxonomy, and returns PASS only when every route's acceptance behavior is `observed`. (a) is FAIL with the quoted status mismatch and a routed fix. (b) is `unverified` for that route and the gate is BLOCKED, never PASS. (c) reports `n/a (tool absent)` honestly without inventing a status.

## Failure modes caught

- A PASS asserted for a route whose real output is not shown.
- A fabricated status, latency, or body shape for an absent tool.
- The command editing product code instead of routing the fix.
- Pinning a specific HTTP client or MCP server, which would break the capability-routed contract.

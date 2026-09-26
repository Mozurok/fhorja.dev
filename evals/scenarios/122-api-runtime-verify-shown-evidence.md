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

## Pass criteria

1. Each route is reported with its real output quoted; no PASS is asserted for a route whose output is not shown.
2. Findings are classified with the command's taxonomy.
3. PASS is returned only when every route's acceptance behavior is `observed`.
4. In (a) the verdict is FAIL, with the status mismatch quoted and the fix routed.
5. In (b) the route is `unverified` and the gate is BLOCKED, never PASS.
6. In (c) an absent tool reports `n/a (tool absent)` honestly, with no invented status, latency, or body shape.
7. The command routes the fix instead of editing product code, and pins no specific HTTP client or MCP server.

## Failure modes caught

- A PASS asserted for a route whose real output is not shown.
- A fabricated status, latency, or body shape for an absent tool.
- The command editing product code instead of routing the fix.
- Pinning a specific HTTP client or MCP server, which would break the capability-routed contract.

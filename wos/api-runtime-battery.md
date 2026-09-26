---
activation: model_decision
description: The local-or-development target rule, what must be recorded per request and response, the failure-path and write-confirmation probes, the capture adapter and its run directory, the static mechanical-versus-judgment split, and the nine-code taxonomy that api-runtime-verify classifies against. Load when running the backend runtime gate; the command keeps the eight-step skeleton and this topic carries the adapter layer.
---

# API runtime battery

Lazy-loaded reference for `api-runtime-verify`. It carries the target
confirmation rule, what must be recorded per route, the failure-path and
write-confirmation probes, and the taxonomy this gate classifies against, so
the command keeps only the eight-step skeleton. Loaded when the command runs,
never inlined into the command. Client-agnostic: whatever issued the request is
the operator's choice; this topic defines what must be recorded, not the tool.

## Target confirmation and blast radius

Restate the base URL before probing and confirm it is the instance under verification. A probe is a real request with real effects, which is what separates this gate from reading the handler, so the blast radius is bounded by the target rather than by a confirmation question.

The target must be a local or a development instance: a loopback host, a container or a dev-cluster address the project's own docs name as development. WHEN the target is neither, do NOT probe it and do NOT stop to ask for permission. Record every route on that target as `unverified: non-local target`, name the base URL that was rejected, and continue to the report. A shared, staging or production instance carries other people's data and other people's side effects, and a gate that probes one is buying evidence with someone else's blast radius.

A non-idempotent route (a write, a delete, a payment, a message send) runs only against a local or development target where that side effect is acceptable and stated. Where the side-effect posture of such a route is unstated, record that route as `unverified: side effect unstated` and probe the rest of the set.

## Recording the request and the response

Per route, record the method, the full path including any query, which auth posture was used (name the credential class, never the secret itself), the content-type sent, and the body shape sent. The recorded request is what makes the result reproducible; a result with no request behind it is `unverified`.

Per route, record the HTTP status, the response content-type, and the observed body shape (the top-level field names with their types, plus the shape of any nested collection the acceptance behavior depends on). Quote the load-bearing lines verbatim: an error body, a missing field, an unexpected redirect. Redact secrets and personal data; the shape is what this gate keeps, not a full payload dump.

## Failure-path and write-confirmation probes

- Probe the failure paths the acceptance behavior names, not only the happy path: an anonymous request to a protected route, a malformed body, a missing required field. A gate that exercised only the happy path is incomplete evidence and MUST say so in its verdict.
- For a write route, confirm the effect with a follow-up read (or the project's own confirmation path) instead of trusting the success status.

## Evidence capture (the run directory)

Capture the exchange in this run rather than asking a human to paste it. Every artifact goes under the task folder in a per-slice run directory, `<task-folder>/evidence/<slice-id>/`, and every path written there is cited in the slice notes and in the report this command writes. The run directory lives in the task folder because it has to survive the session, which the session scratchpad does not.

Two artifacts per run, and they do different jobs.

- The literal exchange, written as `exchange.har` under the run directory. HAR is the interchange format for a recorded request and response, so the record is replayable by something other than this session. Whatever issued the request is still the operator's choice; the requirement is the recorded file, not the client. Redact secrets and personal data before the file is written.
- The response conformance check, run against the declared OpenAPI document when the project has one. Schemathesis is the reference implementation and its `response_schema_conformance` check is the one that matters here: it decides whether the response matches the declared schema. Write its output as `conformance.txt` under the run directory. This is the step that converts "the agent read the body and judged it fine" into a pass from a tool that is not the agent, which is the whole reason it is here and not folded into step 4's reading.

WHEN neither a request recorder nor a conformance checker is reachable, the verdict is BLOCKED naming the missing capability (`no request recorder reachable: no HAR of the exchange` or `no OpenAPI conformance checker reachable: response shape unchecked by any tool but this one`), and that BLOCKED routes to `incident-triage` as a CONFIG failure so the capability is installed and this gate re-run. It is never a silent PASS, and it is never a stop that waits for a human to paste a response body.

## Mechanical and judgment criteria (static split)

The split is declared here, per battery rule, and is never decided per run. A per-run classification would have the agent judging its own capability at the point where the verdict is decided, which is the self-assessment this workflow rules out everywhere else.

| battery rule | class | decided from |
|---|---|---|
| the route was reached at all | mechanical | the recorded exchange, or its absence |
| HTTP status against the acceptance behavior | mechanical | the recorded status line |
| response content-type | mechanical | the recorded response header |
| response shape against a declared OpenAPI document | mechanical | the conformance checker's output |
| response shape with NO declared document | judgment | the agent reading the body against the slice's prose |
| failure-path probes named by the acceptance behavior | mechanical | the recorded status and body on each failure path |
| the confirming read after a write | mechanical | the recorded follow-up response |
| latency worth surfacing | mechanical | the recorded timing in the exchange |

A mechanical row is decided here with no human in the loop, and it gates. The one judgment row is what a missing contract costs: with no document to conform against, the shape verdict is one agent reading a body, so it is reported with the recorded exchange cited and it does not gate on its own. WHEN the slice's acceptance behavior rests on that row, the criterion is `unverified: no declared contract to conform against` and the gate is BLOCKED, and the route out is `api-contract-review`, which produces the document this check needs.

## Taxonomy: API adapter

Tag every finding with one taxonomy code: `UNREACHABLE` (the target never answered: connection refused, a DNS or TLS failure, or a timeout), `STATUS_MISMATCH` (a status the acceptance behavior does not allow, including an unexpected 5xx), `CONTENT_TYPE_MISMATCH` (the response content-type is not the declared one, an HTML error page where JSON was promised), `SHAPE_MISMATCH` (the body parsed but a required field is missing, carries the wrong type, or is nested differently than the contract says), `AUTH_BOUNDARY` (a request that should have been rejected succeeded, a valid credential was rejected, or a wrong-tenant read returned another tenant's data), `ERROR_LEAK` (a failure path returned a stack trace, an internal path, a raw driver error, or an unstructured body), `EFFECT_NOT_OBSERVED` (a write reported success and the confirming read does not show it), `LATENCY_MEASUREMENT` (a response time worth surfacing; numeric budgets belong to `performance-budget`, this gate reports the measurement), or `CLEAN` (the route answered as the acceptance behavior requires).

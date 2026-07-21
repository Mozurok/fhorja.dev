---
name: api-contract-review
description: Review an API contract (endpoints, request/response shapes, error codes, auth model) BEFORE implementation for naming consistency, versioning, pagination, idempotency, and alignment with existing endpoints. Distinct from review-hard (post-implementation risk) and repo-consistency-sweep (pattern matching on written code). Use when designing new endpoints or modifying existing API contracts. Do not use when the API is already implemented (use review-hard or repo-consistency-sweep instead).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2500
  suggested-model: claude-sonnet-4-6
---
# api-contract-review

Act as a senior API architect reviewing an API contract before implementation begins.

Goal:
Review proposed API endpoints for naming consistency, HTTP method correctness, request/response shape quality, error contract, auth/authz model, pagination, idempotency, versioning, and alignment with existing endpoints in the same service. Produce actionable findings before any code is written. Return no-op when there is no API contract to review.

This command is distinct from:
- `review-hard`: which reviews IMPLEMENTED code for correctness/safety risk
- `repo-consistency-sweep`: which pattern-matches WRITTEN code against bug-class templates
- `security-review`: which assesses IMPLEMENTED security surface (threat model, ASVS)

This command operates at the DESIGN phase, before implementation.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md (API contract lives here)
- optional: existing API routes/controllers (for consistency comparison)
- optional: OpenAPI spec or Postman collection (if available)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Extract proposed contract.** Read the API endpoints described in IMPLEMENTATION_PLAN.md or DECISIONS.md. For each: method, path, request body, response shape, status codes, auth requirement.
- **Step 2: Naming and path consistency.** Check: (a) resource naming is plural and consistent (`/drivers`, not `/driver`), (b) path hierarchy reflects resource relationships (`/verification-runs/:id/share`, not `/share-verification-run`), (c) naming matches existing endpoints in the same service (read existing route files for convention).
- **Step 3: HTTP method correctness.** Check: (a) GET for reads (no side effects), (b) POST for creates, (c) PUT/PATCH for updates, (d) DELETE for deletes. Flag method misuse (e.g., GET that mutates state, POST that is idempotent without declaring it).
- **Step 4: Request/response shape quality.** Check: (a) field names are consistent casing (camelCase or snake_case, not mixed), (b) response envelope is consistent with sibling endpoints (`{ data }` vs bare object vs `{ success, data }`), (c) nullable fields are explicitly typed, (d) no overly generic fields (`metadata`, `extra`, `payload` without schema).
- **Step 5: Error contract.** Check: (a) error responses use a consistent shape across endpoints (e.g., `{ error: { code, message } }`), (b) status codes are semantically correct (404 for not found, 409 for conflict, 422 for validation, not 400 for everything), (c) error codes are machine-readable (enum, not free-text), (d) no sensitive information leaked in error messages.
- **Step 6: Auth and authorization model.** Check: (a) every write endpoint has auth, (b) auth mechanism is consistent (JWT, API key, cookie), (c) tenant scoping is explicit (which endpoints need company_id filter), (d) public endpoints are intentionally public (documented as such).
- **Step 7: Pagination.** Check: (a) list endpoints have pagination params (limit/offset or cursor), (b) response includes total count or hasMore indicator, (c) default limit is reasonable (not unlimited).
- **Step 8: Idempotency.** Check: (a) mutation endpoints that trigger side effects (email, payment, webhook) have idempotency strategy, (b) retry-safety is documented.
- **Step 9: Versioning.** Check: (a) is there a versioning strategy (URL path, header, none)? (b) if none: are all changes backward-compatible?
- **Step 10: Alignment with existing API.** Read existing route files and controllers. Check: does the proposed API follow the same conventions (auth middleware, error handling, response shape, naming)?
- Do not implement code. This command reviews design only.
- If the API design is solid, say so clearly.

Required output:
1. Contract summary (endpoints, methods, auth, shapes)
2. Findings per check (naming, methods, shapes, errors, auth, pagination, idempotency, versioning, alignment)
3. Overall assessment (ready to implement / needs revision / has blocking issues)
4. Recommended next command

### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
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
- Every proposed endpoint is reviewed across all 10 checks.
- Findings reference the specific endpoint and check that failed.
- Alignment with existing API is grounded in real route/controller files, not assumptions.
- If the design is solid, the assessment says so clearly (no invented findings).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Maximize design quality signal. Catch contract issues before they become code. If the API design is clean, say so.

<!-- cache-breakpoint -->

---
name: api-contract-review
description: |-
  Review an API contract (endpoints, request/response shapes, error codes, auth model) BEFORE implementation for naming consistency, versioning, pagination, idempotency, and alignment with existing endpoints. Distinct from review-hard (post-implementation risk) and repo-consistency-sweep (pattern matching on written code). Use when designing new endpoints or modifying existing API contracts. Do not use when the API is already implemented (use review-hard or repo-consistency-sweep instead).
metadata:
  category: discovery-and-scoping
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
    - core
    - full
  provenance: first-party
  token-budget: 2500
  suggested-model: claude-sonnet-4-6
---

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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
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

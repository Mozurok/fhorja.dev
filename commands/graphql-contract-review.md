---
name: graphql-contract-review
description: Review a GraphQL schema and a Backend-for-Frontend (BFF) contract BEFORE implementation, against a GraphQL-specific checklist: schema shape and nullability (null-bubbling), errors-as-data unions, N+1 and DataLoader, query cost and depth limits, cursor-connection pagination, federation entity ownership, breaking-change gate (schema checks), auth layering and BFF token posture, BFF thinness, and partial-failure degradation. Distinct from api-contract-review (REST and HTTP) and review-hard (post-implementation risk). Capability-routed, not stack-locked. Use when designing a new GraphQL schema, a federated subgraph, or a BFF contract, or modifying an existing one. Do not use for a REST contract (use api-contract-review), when the schema is already implemented (use review-hard or repo-consistency-sweep), or with no active task folder (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2800
  suggested-model: claude-sonnet-4-6
---
# graphql-contract-review

Act as a staff engineer reviewing a proposed GraphQL schema and BFF contract before any code is written, so the contract is sound at design time rather than patched after clients depend on it.

Goal:
Review a proposed GraphQL schema and Backend-for-Frontend contract against a GraphQL-specific checklist and return actionable findings before implementation. This is the GraphQL and BFF counterpart to `api-contract-review` (which owns REST and HTTP); the two share the design-time review role but check different things. Capability-routed: it reviews GraphQL on any stack and is not tied to a framework.

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
- TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md (the proposed schema or BFF contract lives here)
- optional: an existing SDL schema file, subgraph schemas, or a BFF route map (for consistency comparison)
- optional: captured references in `projects/<client>__<project>/REFERENCES.md` for the chosen GraphQL stack (Apollo Federation, Relay connections, etc.)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not implement code. This command reviews design only. If the schema and BFF contract are solid, say so clearly; do not invent findings.
- **Capability-routed.** Read the GraphQL stack from SOURCE_OF_TRUTH.md or DECISIONS.md (Apollo Federation, a single graph, Relay, a JVM subgraph framework). Name a tool only when the task already chose it.
- **Step 1: Extract the proposed contract.** Read the schema or BFF endpoints described in IMPLEMENTATION_PLAN.md or DECISIONS.md. For each type, query, mutation, subscription, and BFF endpoint: fields, nullability, arguments, transport, and which experience consumes it.
- **Step 2: Schema shape vs consumer need.** Check that each type and field maps to a real client need and the graph is not leaking the downstream service model. For a BFF, confirm payloads are experience-shaped, not generic over-fetch.
- **Step 3: Nullability is deliberate.** Check that every non-null field has a justified reason its resolver cannot fail to null, and that null-bubbling will not blank an entire screen because one nested field errored.
- **Step 4: Errors-as-data.** Check that recoverable and business failures are modeled as union members over a shared error interface (so the success type stays non-null), and the top-level `errors` array is reserved for system or 500-class faults. (The REST counterpart checks HTTP status codes and an error-body schema instead.)
- **Step 5: N+1 and DataLoader.** Check that every resolver loading a per-item relation is batched (a per-request loader); flag any per-edge fan-out to a database or downstream service without one.
- **Step 6: Query cost and depth limits.** Check that a cost or complexity ceiling and a max depth exist, with a concrete budget and a reject behavior, and that list fields cannot request an unbounded `first`. (The REST counterpart checks per-endpoint rate limits.)
- **Step 7: Pagination is cursor-based.** Check that lists use cursor connections (edges, node, cursor, plus `pageInfo` with `hasNextPage` and `endCursor`), opaque cursors, and a max page size; flag naked offset pagination on large or changing sets. Confirm object identification (a `Node`-style refetchable id) where caching or refetch needs it.
- **Step 8: Federation composition and ownership.** When the graph is federated, check that every entity has a single clear owning subgraph, that key fields resolve across boundaries, that composition (entity resolution, type and directive consistency) passes at build time before merge, and that subgraphs are reachable only via the router or gateway, never directly.
- **Step 9: Breaking-change gate.** Check that the schema is evolved, not versioned: additions over a `v2`, removals marked `@deprecated` with field-usage evidence and a migration path, and schema checks run in CI against published or consumer views so any breaking change is intentional.
- **Step 10: Auth at the right layer and BFF token posture.** Check that coarse authorization sits at the router or BFF and fine-grained checks in the owning service, and that for a browser BFF the access and refresh tokens stay server-side, with only an `HttpOnly`, `Secure`, `SameSite` session cookie reaching the client (the BFF attaches the token on the downstream hop).
- **Step 11: BFF ownership and thinness.** Check that the BFF stays thin (aggregation and orchestration only, owned by the frontend team) and that domain logic duplicated across BFFs is flagged to move into a shared service rather than copied.
- **Step 12: Partial-failure behavior.** Check that a downstream timeout or failure degrades the response gracefully (partial data plus a typed error) rather than failing the whole query, with field-level resilience and timeouts on fan-out calls.
- **Ground external contracts.** When a check depends on a specific library or spec behavior (Apollo Federation directives, the Relay connection spec, a cost-analysis library), ground it in a captured `REFERENCES.md` entry; when it is not captured, name the gap and route to `capture-references` rather than asserting the behavior from memory. The captured entry wins over recollection (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode.

Required output:
1. Contract summary (types, key queries and mutations, transport, federation topology, BFF endpoints, auth model)
2. Findings per check (steps 2 through 12), each referencing the specific type, field, or endpoint
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
- Every proposed type, key field, and BFF endpoint is reviewed across the relevant checks (steps 2 through 12).
- Findings reference the specific type, field, or endpoint and the check that failed; the GraphQL and BFF concerns (nullability, N+1, cost, federation ownership, BFF token posture) are checked, not a REST review with renamed rows.
- Alignment with an existing schema or subgraph is grounded in real SDL or route files, not assumptions.
- If the design is solid, the assessment says so clearly (no invented findings).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A reviewer can act on every finding because it names the type, field, or endpoint and the GraphQL or BFF rule it breaks, and a solid contract is confirmed as solid rather than padded with manufactured issues.

<!-- cache-breakpoint -->

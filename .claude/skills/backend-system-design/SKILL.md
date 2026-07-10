---
name: backend-system-design
description: |-
  Produce a staff-grade backend system-design RFC for the active task: a 12-section design document (problem, requirements, architecture, data model and storage, API contract, caching, scaling and bottlenecks, reliability and SLOs, security, observability, rollout and migration, trade-offs) for a new service, endpoint, or backend feature, persisted as BACKEND_SYSTEM_DESIGN.md. Capability-routed, not stack-specific; composes with slo-define, performance-budget, api-contract-review, and release-plan rather than duplicating them. Use when a backend service or feature needs an architecture-level design before planning and slicing. Do not use to slice an already-designed change (use implementation-plan), to analyze blast radius (use impact-analysis), to review an API contract in isolation (use api-contract-review), to design the frontend surface (use frontend-system-design), or with no active task folder (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed:
    - memory
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
    - full
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---

Act as a staff backend engineer writing the system-design document for a new service, endpoint, or backend feature, so the architecture is decided and reviewable before any slicing or code.

Goal:
Produce a 12-section backend system-design RFC for the active task, grounded in the task's decisions and constraints, and persist it as `BACKEND_SYSTEM_DESIGN.md`. The command is capability-routed: it designs backend systems on any stack (a monolith route, a service, a queue worker, a serverless function) and is not tied to one language or framework. It is the backend sibling of `frontend-system-design`, and it composes with `slo-define`, `performance-budget`, `api-contract-review`, `migration-safety-steward`, and `release-plan` rather than duplicating them.

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
- TASK_STATE.md, SOURCE_OF_TRUTH.md, DECISIONS.md (the design must respect locked decisions)
- IMPACT_ANALYSIS.md and INVARIANTS_AND_NON_GOALS.md when present
- the service, endpoint, or backend feature to design, named in the task or the prompt
- the expected scale signal when known (users, request rate, data volume, read-to-write ratio); mark unknowns rather than inventing them
- relevant external references already captured in `projects/<client>__<project>/REFERENCES.md` (read-only grounding)

Task repository files to create or update:
- `BACKEND_SYSTEM_DESIGN.md` in the active task folder: the 12-section RFC.

Operating rules:
- Do not implement product code. This command produces a design document, not a slice plan and not an implementation.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Capability-routed, not stack-locked.** Design for the stack the task actually uses (read it from SOURCE_OF_TRUTH.md or DECISIONS.md). Name a specific database, queue, or runtime only when the task already chose it; never assume one. The structure below holds for any backend stack.
- **Scale-honest, not scale-cargo-culted.** Design for the task's real scale, not FAANG scale. A single Postgres instance is the correct answer for most solo and small-team work; reach for sharding, multi-region, or a message bus only when a stated requirement forces it. Do not import distributed-systems machinery a solo builder will never operate. When a number (users, request rate, data volume) is not known, mark it `unknown` and design for the plausible near-term, not an imagined peak.
- **The 12 sections.** Produce every section; mark a section `not applicable` with a one-line reason rather than dropping it:
  1. Problem statement and context: the user or business problem this backend serves, scope boundaries, who calls it.
  2. Requirements: functional and non-functional, split explicitly; core versus nice-to-have; success metrics; the expected scale (users, request rate, data volume, read-to-write ratio) or an explicit `unknown`.
  3. High-level architecture: the services or components and their relationships (entry point, application layer, data layer, background workers), and the synchronous-versus-asynchronous boundaries. Name the trade-off pairs at play (see `wos/architecture-tradeoffs.md`).
  4. Data model and storage: entities, the schema shape, the storage engine choice and why, indexing, and the consistency model. Compose with `db-context-postgres` or `db-context-supabase` when a real schema exists.
  5. API and interface contract: transport (REST, RPC, GraphQL, or an event), payload shape, pagination, error and retry semantics, idempotency, and versioning. Compose with `api-contract-review` for the endpoint-level audit rather than duplicating it.
  6. Caching and data access: the read and write paths, and the cache update strategy when a cache is in play, named from `wos/cache-update-strategies.md` (cache-aside, write-through, write-behind, refresh-ahead) with its failure mode guarded.
  7. Scaling and bottlenecks: the likely bottleneck under the stated scale (the database, a hot path, an external call), whether the design scales vertically or horizontally, and what statelessness or partitioning that requires. Name the one bottleneck you would hit first and how you would relieve it.
  8. Reliability and SLOs: the availability and latency targets, the failure modes, and the resilience posture (timeouts, retries with backoff, circuit breakers, idempotent retries). Compose with `slo-define` for the target artifact rather than restating it.
  9. Security: authentication and authorization model, secret handling, input validation, data protection at rest and in transit, and multi-tenant isolation when relevant. Route deep review to `security-review` or `rls-auth-boundary-auditor`.
  10. Observability and operations: the logs, metrics, and traces that make this service debuggable in production, the key alerts, and the one dashboard you would watch on launch day.
  11. Rollout and migration: deploy strategy, feature flags, backward compatibility, and schema-migration safety. Compose with `release-plan` for the rollout and `migration-safety-steward` for any DDL rather than duplicating them.
  12. Trade-offs and alternatives: the options considered and why the chosen design wins, citing the named axes in `wos/architecture-tradeoffs.md`. This is the section that separates a design from a policy statement; never leave it empty.
- **Ground external contracts.** When the design commits to an external library, SDK, datastore, or protocol, ground it in a captured `REFERENCES.md` entry; when it is not captured, name the gap and route to `capture-references` rather than designing the contract from memory. The captured entry wins over recollection (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).
- **Respect locked decisions.** Read DECISIONS.md; the design must not silently reopen a locked decision. When the design needs a decision that is not yet made, label it `PROPOSED` and route to `decision-interview` instead of asserting it.
- **No invented metrics.** Scale numbers, latency targets, availability SLOs, and cost figures must cite a source (a measured baseline, a published standard, or a user-supplied target) or be marked `PROPOSED-pending-baseline`.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode (the design artifact follows the same policy).
- **Self-review before emit.** Before writing the file, check it for placeholders, contradictions, an empty trade-offs section, distributed-systems machinery unjustified by a stated requirement, and any section asserting a number without a source; fix them inline.

Required output:
1. The service, endpoint, or feature being designed and the stack read from task memory
2. The 12-section design, every section present
3. Exact `BACKEND_SYSTEM_DESIGN.md` content, marked PROPOSED or APPLIED per editor mode
4. Any `PROPOSED` decision the design surfaced, with the upstream command to lock it
5. Recommended next command
6. Recommended editor mode
7. Why that is the correct next step

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
- All 12 sections are present; a dropped section is invalid output unless marked `not applicable` with a reason.
- The trade-offs and alternatives section is non-empty and names the rejected options, citing the relevant axes in `wos/architecture-tradeoffs.md`.
- No scale, latency, or SLO number is asserted without a cited source or a `PROPOSED-pending-baseline` mark.
- The design is scale-honest: no sharding, multi-region, or message-bus machinery appears without a stated requirement forcing it.
- The design respects DECISIONS.md; any decision it needs but does not have is marked `PROPOSED` and routed to `decision-interview`, not asserted.
- The artifact is marked PROPOSED (Ask) or APPLIED (Agent).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A reviewer can read the document and understand the backend architecture, the data model, the contracts, the failure modes, and why this design beats the alternatives, with no number asserted on no evidence, no locked decision silently reopened, and no scale machinery the task does not need.

<!-- cache-breakpoint -->

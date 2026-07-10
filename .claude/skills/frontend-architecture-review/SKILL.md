---
name: frontend-architecture-review
description: |-
  Review a frontend architecture at scale and gate micro-frontend adoption BEFORE building. The first step is an adopt-or-don't-adopt decision (default: you probably do not need micro-frontends; prefer a modular monolith until 3 or more independently deploying teams and real coordination pain exist), then a checklist covering team-and-domain boundaries, independent deployability, governed shared dependencies, design-system sharing, runtime isolation, cross-app communication, routing and composition tier, rendering strategy, state at scale, a performance budget across the composition, and governance and failure handling. Capability-routed, not stack-locked. Use when reviewing a frontend architecture, evaluating whether to adopt micro-frontends, or hardening a multi-team frontend before it scales. Do not use to design one system (use frontend-system-design), to review a GraphQL or REST contract (use graphql-contract-review or api-contract-review), or with no active task folder (run task-init first).
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
    - full
  provenance: first-party
  token-budget: 2800
  suggested-model: claude-sonnet-4-6
---

Act as a staff engineer reviewing a frontend architecture at scale before it is built or before it scales further, so the structural decisions (and especially whether to adopt micro-frontends) are made on evidence rather than fashion.

Goal:
Review a proposed or existing frontend architecture against a scale checklist and return actionable findings. The first and most consequential check is whether micro-frontends are warranted at all; the default is that they are not. The review then covers boundaries, deployability, shared dependencies, rendering, state, performance, and governance. Capability-routed: it reviews any frontend stack and is not tied to a framework.

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
- TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md (the proposed architecture lives here)
- optional: the existing repo layout, build tooling, and team boundaries (for grounding the review)
- optional: captured references in `projects/<client>__<project>/REFERENCES.md` for the chosen stack and any micro-frontend tooling

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not implement code. This command reviews architecture only. If the architecture is sound, say so clearly; do not invent findings.
- **Capability-routed.** Read the stack from SOURCE_OF_TRUTH.md or DECISIONS.md. Name a framework or a federation tool only when the task already chose it.
- **Step 1: Micro-frontend adopt-or-don't-adopt gate (do this first).** Default to "you probably do not need micro-frontends." Recommend adopting them only when all hold: 3 or more teams that genuinely need to deploy independently, real cross-team coordination pain today, and boundaries that fall on business domains (Conway's law), not technical layers. When they are not warranted, say so plainly, recommend a modular monolith, and skip the federation-specific checks (steps 4, 6 isolation, 8 composition tier, governance manifest) as not applicable.
- **Step 2: Boundaries by team and domain.** Check that splits (modules or micro-frontends) are aligned to team ownership and business domains, with a named owner per boundary, not split by technical layer (a "forms team", a "styling team").
- **Step 3: Independent deployability.** When micro-frontends are in scope, check that there is no build-time npm coupling of remotes into the host that forces lockstep releases; runtime integration (module federation remotes, web components, import maps) is what buys real independent deploy.
- **Step 4: Shared dependencies are governed.** Check for a singleton policy on framework runtimes, declared version ranges and a defined behavior on version mismatch, and a documented upgrade path so one team's bump does not break others. Flag duplicated framework copies inflating the payload.
- **Step 5: Design-system sharing.** Check that primitives ship as a versioned UI-kit and tokens (so visual consistency does not depend on copy-paste), while domain-specific components stay local to their owner.
- **Step 6: Style and runtime isolation.** Check the style-scoping strategy (CSS modules, scoped CSS, Shadow DOM) prevents cross-app cascade, and that a failing or slow remote is isolated by an error boundary and degrades gracefully rather than crashing the whole page.
- **Step 7: Cross-app communication.** Check that communication across boundaries is minimal and indirect (custom events, container callbacks, the URL as a contract), with no shared mutable global state recreating the coupling the split was meant to remove.
- **Step 8: Routing contract and composition tier.** Check that URL-space ownership is defined, deep-links and browser history work across boundaries, and the composition tier (client app shell, server-side, or edge) matches the routing and the first-paint and SEO needs.
- **Step 9: Rendering strategy at scale.** Check that the rendering strategy is chosen per route, not per app (SSG or ISR for cacheable, SSR or streaming for personalized, client-side for app shells, server components to cut shipped JS), with a stated TTFB, SEO, or personalization rationale.
- **Step 10: State management at scale.** Check the split between local UI state, global app state, and server-cache state is deliberate, and that the real-time transport (WebSocket, SSE, polling) is chosen per use case rather than defaulted.
- **Step 11: Performance budget across the composition.** Check there is no unbounded runtime waterfall of remote fetches, that LCP and total-blocking-time budgets exist, that duplicated dependencies are measured, and that remotes are lazy-loaded with CDN-cached entries. Compose with `performance-budget` for the numeric per-metric table rather than re-deriving it.
- **Step 12: Governance and failure handling.** Check that cross-cutting concerns (auth, observability and tracing across boundaries, error reporting) are centralized and consistent, that a versioned integration manifest resolves remotes and permissions without coordinated redeploys, and that each boundary has a blast-radius-bounded rollback story (canary or blue-green per remote, a defined fallback for a broken remote).
- **Ground external claims.** When a check depends on a specific tool or pattern (a module-federation directive, an edge-composition product), ground it in a captured `REFERENCES.md` entry; when it is not captured, name the gap and route to `capture-references` rather than asserting it from memory. The captured entry wins over recollection (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode.

Required output:
1. Architecture summary (the surfaces, the proposed boundaries, the stack and any federation tooling, the team topology)
2. Micro-frontend verdict (adopt / do not adopt) with the reason, stated up front
3. Findings per check (steps 2 through 12), each referencing the specific boundary, route, or concern, with federation-only steps marked not applicable when micro-frontends are not adopted
4. Overall assessment (sound / needs revision / has blocking issues)
5. Recommended next command

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
- The micro-frontend adopt-or-don't-adopt verdict is stated first, with the reason, and defaults against adoption unless the three conditions hold.
- Findings reference the specific boundary, route, or concern and the check that failed; federation-only steps are marked not applicable when micro-frontends are not adopted (no findings manufactured for an architecture that does not use them).
- Claims about a specific federation tool or pattern are grounded in a captured reference, not asserted from memory.
- If the architecture is sound, the assessment says so clearly (no invented findings).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A reviewer gets an honest adopt-or-don't verdict on micro-frontends and findings that name the boundary or route and the rule they break, with no structure prescribed that the team's scale does not justify.

<!-- cache-breakpoint -->

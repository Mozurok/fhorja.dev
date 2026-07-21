---
name: frontend-architecture-review
description: Review a frontend architecture at scale and gate micro-frontend adoption BEFORE building. The first step is an adopt-or-don't-adopt decision (default: you probably do not need micro-frontends; prefer a modular monolith until 3 or more independently deploying teams and real coordination pain exist), then a checklist covering team-and-domain boundaries, independent deployability, governed shared dependencies, design-system sharing, runtime isolation, cross-app communication, routing and composition tier, rendering strategy, state at scale, a performance budget across the composition, and governance and failure handling. Capability-routed, not stack-locked. Use when reviewing a frontend architecture, evaluating whether to adopt micro-frontends, or hardening a multi-team frontend before it scales. Do not use to design one system (use frontend-system-design), to review a GraphQL or REST contract (use graphql-contract-review or api-contract-review), or with no active task folder (run task-init first).
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
# frontend-architecture-review

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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
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
- The micro-frontend adopt-or-don't-adopt verdict is stated first, with the reason, and defaults against adoption unless the three conditions hold.
- Findings reference the specific boundary, route, or concern and the check that failed; federation-only steps are marked not applicable when micro-frontends are not adopted (no findings manufactured for an architecture that does not use them).
- Claims about a specific federation tool or pattern are grounded in a captured reference, not asserted from memory.
- If the architecture is sound, the assessment says so clearly (no invented findings).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A reviewer gets an honest adopt-or-don't verdict on micro-frontends and findings that name the boundary or route and the rule they break, with no structure prescribed that the team's scale does not justify.

<!-- cache-breakpoint -->

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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). The full tier is measured at 10530 tokens: the combined size of the four always-read `WORKFLOW_OPERATING_SYSTEM.md` sections listed above. That figure is asserted here in prose and no gate recomputes it, so it drifts every time the spec grows: it was declared at 9610 and measured at 10530 on 2026-08-10, a 9.6 per cent gap, and it will drift again unless re-measured with the same method (sum the four `^## ` sections, chars over 4). The reduced tier is a self-declared estimate of about 3,500 tokens for the trimmed subset above; it has not been independently re-measured by the same method, and should be read as an estimate rather than a fresh figure. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Cache-amortized layer (ADR-0006):** this bootstrap floor was DESIGNED as a cache-amortized cost rather than a per-command tax. ADR-0139 measured that the amortization is real but NOT controllable from here: the harness manages caching itself, there is no per-file or per-segment caching, and a command body is injected as a user message after the cached prefix. Whether this floor is cached is a property of the host, not of anything this repository can mark. Treat the figure below as a real per-invocation cost when reasoning about what a command carries. It sits in the prompt cache for the session and is paid at write cost once per cache TTL window, then at roughly 0.1x on cached reads inside that window. Account for it separately from any per-skill Load budget (the generated `.claude/skills/<name>/SKILL.md` body); the two are different layers and should not be summed into one figure.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. This is a scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), justified because the bootstrap sections are one large, static, byte-identical read repeated every turn rather than a variable tool result; the re-fetch rule still governs every other tool result without exception. VISIBLE means the bootstrap section text itself is still present and quotable in the window right now, not merely that the record of an earlier read exists. On a harness that clears, a tool result can be emptied while the record that the tool ran survives (ADR-0114); a command that finds only that record, without the section text still readable, has not satisfied VISIBLE and must re-read. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- **Resolving a relative `wos/<topic>.md`.** Try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/wos/` or `~/.cursor/workflow-docs/wos/`). Name the root you resolved against in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently: several of these loads are declared MANDATORY, and a lazy load that resolved nowhere is otherwise indistinguishable in the output from one that was never needed. Repository first, because the installed copy is a snapshot that no sync prunes: preferring it would make an edit to `wos/` invisible to every command until someone re-ran the installer.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares that the chain has ended and no following command would be honest, defined in `## Global output contract` (ADR-0126); use it only when nothing honest remains, never to end a chain that has a real next step.

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

### Reference grounding (design gate)
<!-- shared:reference-grounding-design -->
**Reference grounding (design gate, ADR-0043 D-3).** This command does not edit code, so it does NOT refuse. It marks. Every external contract this document NAMES as a choice, a recommendation, or a thing to build against is either grounded in a captured reference or carried forward as visibly unproven.

1. Detect. Any external library, SDK, API, protocol, or vendor behavior this document names as a decision input: a version to adopt, an endpoint shape to build against, a rate limit to design for, a capability to depend on.
2. Ground or mark. WHEN the contract is present in `projects/<client>__<project>/REFERENCES.md`, read that entry and cite it inline where the decision is stated. WHEN it is absent, keep the recommendation and append `[ungrounded: <contract>]` to that line. Do NOT drop the recommendation, and do NOT silently assert the behavior: an unproven choice a human can see beats a confident one they cannot.
3. Never launder recollection into a design. A version number, a parameter name, or a rate limit recalled from training is outside the grounded set (`wos/active-epistemic-humility.md`). It may appear as a proposal, marked, never as a stated fact.
4. Route, do not block. WHEN two or more contracts are ungrounded, name `capture-references` in the handoff as the next command. This gate exists so `implement-approved-slice` is not the first place the gap is discovered, at which point the plan is already approved and the execution gate refuses mid-slice.
5. Carry the marks forward. Every `[ungrounded: ...]` marker SHALL survive into the persisted artifact. A design doc that resolved its own markers by deleting them has defeated the gate.
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
- Every proposed type, key field, and BFF endpoint is reviewed across the relevant checks (steps 2 through 12).
- Findings reference the specific type, field, or endpoint and the check that failed; the GraphQL and BFF concerns (nullability, N+1, cost, federation ownership, BFF token posture) are checked, not a REST review with renamed rows.
- Alignment with an existing schema or subgraph is grounded in real SDL or route files, not assumptions.
- If the design is solid, the assessment says so clearly (no invented findings).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A reviewer can act on every finding because it names the type, field, or endpoint and the GraphQL or BFF rule it breaks, and a solid contract is confirmed as solid rather than padded with manufactured issues.

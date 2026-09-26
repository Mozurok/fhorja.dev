---
name: feature-library-scout
description: Research and recommend community-vetted best-in-class libraries for each feature problem in the product (lists, camera, forms, keyboard, sheets), ranked by adoption signal (downloads, dependents, recency, stars-trend, maintenance, platform fit) relative to the project's ecosystem. Stack-agnostic across registries (npm, PyPI, crates.io, Go, Maven). Researches five angles (web, repo, registry, AAA practices, reference repos) and writes FEATURE_LIBRARIES.md, grounding every pick in a captured REFERENCES.md source; picks are optional guidance. Use when the stack is chosen and you want the canonical per-feature libraries surfaced and vetted. Do not use to pick stack layers (use stack-recommend), to verify a framework's current patterns (use stack-currency-check), to synthesize already-captured sources (use external-research), or with no active task folder (run task-init first). For a deep per-problem sweep, use feature-library-scout-fleet.
metadata:
  category: research-and-sourcing
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [retrieved]
  tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch]
  x-wos-profiles: [core, full]
  provenance: first-party
  suggested-model: claude-sonnet-5
---
# feature-library-scout

Act as a senior/staff engineering ecosystem advisor with deep knowledge of production-grade libraries for the active project's stack.

Goal:
For a chosen stack and a product's feature set, discover and vet the community-validated best-in-class library for each concrete feature problem, and persist the result as `FEATURE_LIBRARIES.md` inside the active task folder. Each pick is ranked by adoption signal, grounded in a captured source, and framed as optional guidance the maintainer can adopt, defer, or reject.

This command operates one granularity below `stack-recommend`. `stack-recommend` picks stack layers (framework, database, auth, hosting). This command picks the per-feature libraries inside that stack (the large-list renderer, the camera library, the bottom sheet, the keyboard handler). It never re-picks stack layers.

This command is opt-in. Run it when the stack is set and the value is in surfacing the canonical per-feature options with adoption evidence, at project bootstrap or mid-project on an existing codebase.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- the chosen stack (from `SOURCE_OF_TRUTH.md`, `STACK_RECOMMENDATION.md`, or `PROJECT_CHARTER.md`; do not guess the stack)
- the product's feature set, or enough description to derive the concrete feature problems (lists, camera, forms, keyboard, sheets, navigation, gestures, animation, offline, payments-ui, and so on)
- optional: for an existing project, the product repository path (to scan current dependencies and usage)
- optional: user-provided reference links (specific libraries or articles to weigh)
- optional: refresh flag (`refresh` to regenerate an existing `FEATURE_LIBRARIES.md`; default is `NO_OP_TRACE` if a non-stale file already exists)

External web access:
- This command is in the authorized-command set in the spec `## Cross-cutting workflow guardrails ### External web access (centralized)`, scoped to per-feature library discovery and adoption-signal gathering. The Research methodology below fetches package-registry pages (npm, PyPI, crates.io, Go module index, Maven Central, etc. per the stack), source-host repositories (GitHub, GitLab), official docs, and AAA-company engineering posts. It MUST funnel every cited source into `REFERENCES.md` (capture-references entry format, deduplicated by URL), so the fetch is indistinguishable in the audit trail from a `capture-references` run.

Research methodology (five angles):
- **Step 1: Derive feature problems.** From the product feature set (and a scan of the product repository when provided), list the concrete feature problems this product has. Ground the list in the actual product, not a generic checklist.
- **Step 2: Internet.** For each problem, find recent (within ~12 months) best-practice articles, official docs for the latest version, and comparison posts from reputable sources.
- **Step 3: Product repository.** When a repo path is provided, scan it for the feature set and existing dependencies: what is already used, what is missing, and any version or peer-dependency conflicts a new library would hit. This angle is an internal read, not a web fetch.
- **Step 4: Package registry.** For each candidate library, gather adoption signals from the stack's registry (npm for JS/TS, PyPI for Python, crates.io for Rust, the Go module index, Maven Central for JVM, etc.): download or install volume, dependent count, release cadence, last-release date, and license.
- **Step 5: AAA-company practices.** Research what teams known for engineering excellence ship for this feature problem (for example Shopify, Meta, Discord, Microsoft), via engineering blogs, public stack disclosures, or their open-source repositories. Cite the specific source.
- **Step 6: Reference repos.** Find well-regarded repositories solving the same problem and read their dependency choices; a library many strong repos depend on is a high-signal pick. WHERE `repomix` is present, resolve its already-installed executable and invoke `<repomix-executable> --remote <owner/repo> --include "package.json,requirements.txt,Cargo.toml,go.mod,pom.xml"`, quoting the executable path; this clones the remote into temporary storage and packs the selected manifests. Capture the result into `REFERENCES.md`. WHILE no installed executable resolves, fall back to a WebFetch of the raw manifest URL. Presence-gated, no install or version refresh (ADR-0027); on a failure (rate limit, private repo) record `[not fetched: reason]` and never guess.
- **Step 7: Synthesize.** Per feature problem, produce a ranked candidate table, a recommended pick with a one-line reason, alternatives with when to prefer them, and the sources.

Operating rules:
- Do not implement production code.
- **Boundary (per ADR-0045, D-Boundary):** pick per-feature libraries only. Do not re-pick stack layers; that is `stack-recommend`. When the feature set implies a missing stack-layer decision, note it and route to `stack-recommend` rather than deciding it here.
- **Grounding:** every recommended library must cite at least one source captured in `REFERENCES.md`. Never fabricate adoption numbers. When a signal cannot be fetched (rate limit, private repo, missing data), write `[not fetched]` in that cell rather than a guess, and note any rate-limit truncation in the artifact's Snapshot metadata. Silent truncation is invalid.
- **Optional guidance (per ADR-0045, D-F):** label picks as optional guidance the maintainer may adopt or decline. Never mark a library as mandatory.
- **Snapshot freshness:** always record `Last refreshed:` as today's date in `YYYY-MM-DD`. Adoption signals are a dated snapshot; state that they are directional, not durable.
- **Stable preference:** prefer stable releases. When a pre-release is genuinely the community standard for a problem, you may recommend it, but flag the pre-release status explicitly.
- **Capture sources:** funnel every cited source into project-level `REFERENCES.md` using the `capture-references` format, deduplicated by URL.
- **Mode C eligibility (parallel fanout, per ADR-0032):** when the derived feature-problem list has more than 3 problems AND each warrants a deep multi-angle read, recommend `feature-library-scout-fleet` (one worker per feature problem) instead of an inline sweep. Inline is cleaner for 3 or fewer problems. Tie-break when the count is over 3: prefer routing to the fleet (do NOT produce the full inline artifact); produce the inline artifact only on explicit user override, and say which path you took in the Handoff.
- **Re-run policy:** regeneration replaces `FEATURE_LIBRARIES.md` in full; do not partial-merge. Handwritten notes that must survive refresh belong in `DECISIONS.md` or `TASK_STATE.md`.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: write the file and mark it `APPLIED`.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full). Default next command: `decision-interview` (a pick needs the maintainer's ruling) or `implementation-plan` (the picks are clear and planning can proceed).

Output format:
- Write `FEATURE_LIBRARIES.md` following `templates/FEATURE_LIBRARIES.template.md`: Snapshot metadata, How to read this, Feature problems covered, one Per-problem recommendations block per problem (candidate table with the adoption-signal columns, recommended pick, alternatives, sources), Cross-cutting techniques, Adoption-signal legend, Open questions, Sources, Cross-references. Omit any section with no content for this product.

Task repository files to update:
- `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/FEATURE_LIBRARIES.md` (create or fully regenerate; never partial-merge)
- `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/SOURCE_OF_TRUTH.md` (append-only: add a single `## Feature libraries` section pointing to `./FEATURE_LIBRARIES.md` if not already present)
- `projects/<client>__<project>/REFERENCES.md` (append newly captured sources per `capture-references` format; deduplicated by URL)

Required output:
1. Resolved active task path.
2. The chosen stack and the product feature set (echoed back; if either is unclear, ask one targeted clarifying question first and stop).
3. Feature problems derived, angles covered (mark any angle skipped and why), and number of sources captured.
4. Whether this is a `create` or a `refresh` of `FEATURE_LIBRARIES.md`, and (on refresh) a one-line drift summary versus the prior snapshot.
5. Exact content for `FEATURE_LIBRARIES.md` using the canonical template.
6. Exact patch to `SOURCE_OF_TRUTH.md` adding the `## Feature libraries` cross-link, or `SKIP` if already present.
7. Exact patch to `REFERENCES.md` for newly-captured sources, or `SKIP` if none.
8. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify against directory listing before output).
9. Recommended editor mode.
10. Why that is the correct next step.

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- The proposed `FEATURE_LIBRARIES.md` includes the canonical metadata (`Last refreshed`, feature set, sources consulted, angles covered, signal freshness), one per-problem block per derived feature problem with the adoption-signal columns, a recommended pick and alternatives per problem, and the adoption-signal legend.
- Every recommended library traces to a source in `REFERENCES.md` (pre-existing or newly captured this run with an explicit per-entry patch). Unsourced picks or fabricated adoption numbers are invalid output.
- Signals that could not be fetched are marked `[not fetched]`, not guessed; any rate-limit truncation is noted in Snapshot metadata.
- Picks are framed as optional guidance; none is marked mandatory (D-F).
- The boundary with `stack-recommend` is respected: no stack-layer is re-picked here.
- `### Artifact changes` marks `FEATURE_LIBRARIES.md` as `APPLIED`.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for adoption-signal accuracy (real numbers, dated, never fabricated), source traceability (every pick cites a captured source), the right granularity (per-feature libraries, not stack layers), and actionability (the next command can consume the shortlist without re-researching). Surface the strong options the maintainer should know, even the ones this project will not adopt.

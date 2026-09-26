---
name: impact-analysis
description: Understand the requested change deeply enough to make safe workflow decisions, then persist it as IMPACT_ANALYSIS.md. Identifies blast radius, contract impacts, schema and runtime risks, and integration points before planning or coding. Per-repo subsections when multi-repo. Use when a task was just initialized, when it is still partly understood, or when the change may affect contracts, schema, integrations, runtime behavior, or critical user flows. Do not use when a valid impact analysis already exists, when the goal is only to sync task memory, when the issue is an observed technical failure (use incident-triage), or when the need is to implement an approved slice (use implement-approved-slice). For greenfield work consider backend-system-design, frontend-architecture-review, ai-feature-eval-harness, or code-context-map.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  suggested-model: claude-opus-5-5
---
# impact-analysis

Act as a senior/staff engineer performing a bounded, evidence-driven impact analysis for the active engineering task.

Goal:
Understand the requested change deeply enough to make safe workflow decisions, then persist the analysis in the active task folder.

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
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- current task/request description
- relevant real codebase context
- relevant tests, if available
- official external docs only if needed to understand framework/library behavior
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update:
- IMPACT_ANALYSIS.md
- TASK_STATE.md
- SOURCE_OF_TRUTH.md (the `## Repo instruction files` section only; this command owns it per `wos/substrate-peers.md`)

Operating rules:
- Do not implement anything.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every substrate write per `wos/substrate-peers.md`. Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (or `null` only if the section did not exist prior to this write).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=impact-analysis section='## X' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=<<=80chars> mode=<applied|proposed> -->`.
  3. Write or update the section content.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the <!-- count:log-fields -->14<!-- /count -->-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator. `sha_before` is `null` ONLY on first write to a fresh section.
  6. impact-analysis writes TWO owned sections (`TASK_STATE.md ## Active files in scope` and `SOURCE_OF_TRUTH.md ## Repo instruction files`) AND emits PROPOSED CO-WRITER blocks under `TASK_STATE.md ## Current known facts` + `## Risks to watch`. Distinct K.2 handling per role:
     - **Owner write** (`## Active files in scope`): mode=applied; full protocol per steps 1-5; this is impact-analysis's substrate write that K.4 drift-guard catches if skipped.
     - **Co-writer PROPOSED blocks** (`## Current known facts`, `## Risks to watch`): emit a PROPOSED block INSIDE the existing section with `<!-- PROPOSED by impact-analysis: ... -->` content marker. DO NOT emit a wos:write transaction header for the section -- ownership stays with sync-task-state. emit a single JSONL line per PROPOSED block with `event=propose`, `mode=proposed`, owner=impact-analysis. When `approve-proposed` later promotes the block, the OWNER (sync-task-state) emits the wos:write header + a JSONL line with `event=approve`.

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted on the owner write, OR `sha_after` null on the applied write). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- Do not assume undocumented business rules.
- Before producing output, inspect the latest `TASK_STATE.md` and determine whether `impact-analysis` is still the highest-value command now.
- If the latest state already contains a valid and current impact analysis with no material gap, do not rewrite artifacts just to restate them; return a no-op with the best next command instead.
- No-op rule for artifacts:
  - If `IMPACT_ANALYSIS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- Keep the analysis bounded to directly affected code paths, contracts, data model, consumers, tests, runtime dependencies, and failure modes.
- Distinguish clearly between:
  1. confirmed facts from evidence
  2. assumptions or unresolved interpretations
  3. open questions that affect correctness
- If correctness depends on information not grounded in code, tests, docs, or explicit user input, stop and surface targeted questions instead of guessing. In an attended chain on a task branch (ADR-0233) that is a route, not a wait: a missing fact goes to `targeted-questions` and a missing product decision to `decision-interview`, which record a provisional `### P-N` and continue.
- Prefer asking a few high-value questions over filling gaps with speculation.
- Avoid broad architectural exploration unless it is necessary for correctness.
- If production behavior could be affected, explicitly call out silent failure risk, backward compatibility risk, and rollout risk.
- Multi-repo handling: keys off the presence of `## Repositories` in `SOURCE_OF_TRUTH.md`. When the section exists (multi-repo task), produce per-repo blast radius assessments, one subsection per repo in `IMPACT_ANALYSIS.md` (`### Repo: <identifier>`). Each per-repo subsection covers items 2-7 of the `IMPACT_ANALYSIS.md must include` set for that repo. Reject silent omission of any repo listed in `## Repositories`. When the section is absent, produce a single flat `IMPACT_ANALYSIS.md` per the existing schema (no behavior change).
- Deliverable coverage (per ADR-0056): read `## Requested deliverables` in `TASK_STATE.md` when present; every direction MUST account for each in-scope row. IF a direction drops, defers, or narrows a named deliverable, THEN surface that de-scope as an explicit question or decision for `decision-interview`, never let it fall out silently. This generalizes the multi-repo no-silent-omission rule to user-named deliverables. WHEN the section is absent, no-op.
- **Repo instruction files (mobile dogfood 2026-07-29).** Once the affected-file set is known, walk up from each in-scope path to the repository root and collect every agent-instruction file on the way: `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, and any `.agents/rules/` or equivalent rules directory. Record the hits, nearest-first, as a `## Repo instruction files` section in `SOURCE_OF_TRUTH.md` (this command owns that section; see `wos/substrate-peers.md`). Record paths and the one-line relevance of each, never a copy of their contents; the point is that a later command knows the file exists and can read it, not that its rules get duplicated into task memory. Skip the repository-root file when the harness already auto-loads it, and say so, so the section carries only what the harness will NOT hand the next command for free. WHEN no such file exists below the root, write `none below the repo root` rather than omitting the section, because absence is itself worth knowing. The failure this closes: a monorepo carried 31 `CLAUDE.md` files, and the one governing the changed directory named both the runtime axis of the run's blocking defect and the boundary invariant the task spent hours re-deriving; across 1,018 tool calls it was opened zero times.
- **Prior analyses in this project (ADR-0214).** Once the affected-file set is known, find the other tasks in this project that already analyzed the same code: `grep -l -F -e <path1> -e <path2> ... projects/<client>__<project>/{active,archive}/*/IMPACT_ANALYSIS.md`, excluding this task's own folder. Read only the files that match, newest folder first, at most three. They are what an earlier session learned about the same blast radius, including risks it found that nothing else in this task will surface. Record in `### Command transcript` which prior analyses were read and what, if anything, each changed about this one; record `prior analyses: none matched` when the grep returns nothing. Do not read the ones that did not match: the cost of a prior analysis is concentrated in the few that share code with this task, and reading every one in a busy project would cost more than this command.
- **Currency check trigger (greenfield only):** during the affected-areas pass, classify each affected area as either "incremental" (existing code precedent in the area) or "greenfield" (no internal precedent). When at least one area is greenfield AND the project uses an established framework (Next.js, Supabase, React, Tailwind, Stripe, etc.) AND `CURRENT_PATTERNS.md` lacks a `Status: verified` entry for that framework's active version with an `Accessed:` date <=30 days old, add a `## Currency check required` section to `IMPACT_ANALYSIS.md` listing the frameworks needing verification, and route the next step to `stack-currency-check` BEFORE `implementation-plan`. An unresolved active version also triggers this check. Do NOT trigger this gate when all affected areas are incremental (existing patterns provide the precedent). It implements the greenfield clause in the spec `## Evidence priority`, preventing the gold-standard-audit anti-pattern.
- **Feature-library trigger (greenfield product surface, per ADR-0045):** when the affected areas include greenfield product features whose library choice is not yet settled (for example a large-list surface, camera, forms, keyboard, or sheets), and no `FEATURE_LIBRARIES.md` exists for them, note them in the analysis and offer `feature-library-scout` (or `feature-library-scout-fleet` for more than 3 such features) as a routed next step before `implementation-plan`. It is additive to and independent of the currency-check trigger (that verifies framework pattern currency, this picks the per-feature libraries); both may apply to one analysis, and neither replaces the other.
- **Optional blast-radius diagram (Mermaid, ADR-0047):** on request, append to `## Affected areas` a Mermaid flowchart of the change's blast radius (the changed module plus its inbound and outbound edges and contract or boundary touch points): strictly the dependency subgraph, not a whole-repo redraw, framed as a seed to verify that does not replace the prose blast-radius. Mermaid is host-rendered; no new dependency.
- Keep the output practical and reviewable, not essay-like.
- Update `TASK_STATE.md` only when the analysis introduces material changes (new facts, new blockers, changed risks, or changed next step).
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.

IMPACT_ANALYSIS.md must include:
1. Request understanding
2. Confirmed facts
3. Assumptions / unresolved interpretations
4. Affected areas (optionally with a Mermaid blast-radius subgraph, ADR-0047)
5. Risks and failure modes
6. Viable implementation directions: when 2 or more viable directions exist, a structured alternatives-with-trade-offs table (one row per direction: approach, key trade-off, effort, risk, reversibility) with the recommended pick called out. Omit the table only when a single direction is obvious. Per-decision rationale still lives in DECISIONS.md and ADRs (which own the chosen-design-plus-rejected-alternatives record); this table is the comparison spine, not a second decision record.
7. Recommended path
8. Open questions
9. Suggested next step
10. Recommended next command
11. Recommended editor mode
12. Why that is the correct next step

For multi-repo tasks (when `SOURCE_OF_TRUTH.md` has a `## Repositories` section): items 2-7 above are produced per repo, organized under `### Repo: <identifier>` subsections. Items 1, 8, 9, 10, 11, 12 are task-level (shared across repos). Cross-repo dependencies (e.g., backend change required before frontend can land) appear in item 5 (Risks and failure modes) and item 7 (Recommended path).

TASK_STATE.md update must reflect:
- current phase
- current known facts
- blockers / open questions
- risks to watch
- recommended next step
- current closure target, if clarified by the analysis

Required output:
1. Whether IMPACT_ANALYSIS.md should be created or updated
2. Exact content for IMPACT_ANALYSIS.md (full document if create/update; otherwise a short NO_OP note)
3. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
4. Recommended next command
5. Recommended editor mode
6. Why this is the correct next step
7. What should explicitly not be done yet

### Substrate digest fallback
<!-- shared:substrate-digest-fallback -->
**Digest fallback when the canonical helper is unreachable.** `sha_of_section` extracts a section's body with `awk` and pipes it to `shasum -a 256`. A run executing inside a permission boundary that admits `shasum` but refuses `awk` and `sed` cannot invoke that helper, and MUST NOT reimplement it: an `awk` or `sed` program operand can call `system()` and write files, so a boundary that refuses those verbs refuses them for a reason. Assume the helper is unreachable whenever the workflow repository's `scripts/` directory is not readable from the working directory.

WHERE the canonical per-section digest helper is unreachable, the write SHALL use a whole-file SHA-256 and SHALL declare the reduced scope:

```bash
# One call per file. `shasum -a 256 <file>` needs no extraction step, so no
# refused verb is involved. Read the hash (the first field) out of the output;
# do not pipe it through `cut` or `awk` to trim it.
shasum -a 256 TASK_STATE.md
```

Then add `"sha_scope":"file"` to that JSONL line, so a validator distinguishes a file digest from a section digest instead of inferring it. Everything else about the protocol is unchanged: the transaction header still goes above the section heading, and there is still exactly one JSONL line per section write.

Do NOT rebuild the helper by writing each section out as its own file so it can be hashed separately. That workaround is coherent and it is what this rule exists to prevent: a 2026-08-04 run wrote 31 numbered section fragments to compute per-section digests by hand, spent the whole run doing it, and produced no product code.

What the fallback costs, stated so the trade is explicit rather than discovered later: the digest chain exists to detect an unlogged change to a SECTION. At file scope, two sections written in the same run share a digest, so the chain detects tampering with the file without attributing it to a section. That is a declared reduction in resolution, not a silent one, which is why the `sha_scope` field is mandatory rather than optional.
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
- Separates confirmed facts vs assumptions vs correctness-critical open questions.
- Blast radius is bounded to real evidence (no architecture fanfiction).
- `IMPACT_ANALYSIS.md` is `APPLIED`; `TASK_STATE.md` follows the global write policy.
- Multi-repo coverage: when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, every listed repo has its own `### Repo: <identifier>` subsection in `IMPACT_ANALYSIS.md` with items 2-7 fully populated; silently omitting a listed repo is invalid output. Single-repo tasks (no `## Repositories` section) produce a flat `IMPACT_ANALYSIS.md` per the v1.0 contract.
- `SOURCE_OF_TRUTH.md` carries a `## Repo instruction files` section listing the agent-instruction files that govern the in-scope paths (or the explicit `none below the repo root`), by path, never by copied content. An analysis that names files in a subdirectory without checking whether that subdirectory has its own instruction file is incomplete.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Be evidence-driven, skeptical, bounded, and operational.
Optimize for clarity, low ambiguity, and safe downstream planning.

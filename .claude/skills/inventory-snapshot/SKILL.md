---
name: inventory-snapshot
description: |-
  Snapshot the upstream Figma component library into docs/research/_inventory/figma_components.md. For each Figma component: name, inferred tier, node ID, and whether a spec/code/story exists in the WOS-UI surface. Produces delta vs previous snapshot. Use after design ships a Figma library update or to seed the inventory at project start. Do not use when no Figma source is available or when only auditing one component (use design-spec-review instead).
metadata:
  category: "discovery-and-scoping"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory, retrieved"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5-5"
---

Act as a design system auditor maintaining a current view of the Figma component library and its mapping to the WOS-UI surface (spec docs, code dirs, Storybook stories).

Goal:
Call Figma MCP tools to enumerate every component in the upstream library, classify each by tier (atom / molecule / organism / layout), and write or refresh `docs/research/_inventory/figma_components.md`. For each Figma component, record whether a corresponding spec doc, code directory, and Storybook story exist in the project. Produce a delta report vs the previous snapshot. Refresh the priority queue with components that need attention next.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- project workspace path
- Figma file URL (e.g., `https://figma.com/design/:fileKey/:fileName`)
- path to inventory file (default: `docs/research/_inventory/figma_components.md`; created from `templates/INVENTORY.md` if absent)
- optional: scope to a specific Figma page or top-level frame

Task repository files to update:
- TASK_STATE.md (add inventory summary: total components, % traceable, delta vs previous)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Read previous snapshot.** If `figma_components.md` exists, parse the last inventory tables and the previous snapshot date to compute delta. If absent, create from `templates/INVENTORY.md`.
- **Step 2: Enumerate Figma components.** Use `get_libraries` only for library discovery. Traverse the source file's pages and frames with `get_metadata` to enumerate component and component-set nodes. Capture each name, node ID, and observed variant set information; use `get_design_context` when metadata lacks those details. If the source cannot be fully enumerated, report the inaccessible or truncated scope and request a readable source file or node before continuing.
- **Step 3: Classify by tier.** For each component, infer tier (atom / molecule / organism / layout) using the rules in `wos/design-system-conventions.md` (atom = uses only tokens; molecule = composes atoms; organism = composes molecules + atoms; layout = page-level container). When ambiguous, mark `(proposed)` and surface as an open question.
- **Step 4: Check WOS-UI traceability.** For each component, check whether the corresponding artifacts exist:
  - spec doc: `docs/research/components/<tier>/<kebab-name>.md`
  - code dir: `packages/design-system/src/<tier>/<PascalName>/`
  - story file: `apps/storybook/stories/<tier>/<PascalName>.stories.tsx`
  Mark each as present or empty in the inventory row.
- **Step 5: Compute counts.** Update the coverage summary table: per-tier counts (Figma, documented, coded, storyboarded) and `% traceable`. The target for shipped MVP is 100%.
- **Step 6: Compute delta vs previous.** Report ADDED (in Figma now but not previous), RENAMED (similar match under different name), DEPRECATED (in previous but not Figma now), RESCOPED (tier changed). When unsure between RENAMED and ADDED+DEPRECATED pair, mark `(proposed-rename)` and surface as open question.
- **Step 7: Refresh priority queue.** Re-order the Priority queue table by impact (used in N screens, blocking design tickets, etc.) plus delta status. Top 5 components in the queue are the immediate `component-spec` candidates.
- **Step 8: Write to file.** Update `docs/research/_inventory/figma_components.md` with new Last refresh date, refreshed tables, and delta section.
- Do NOT modify spec docs, code, or stories. This command is read-only against the WOS-UI surface; only the inventory file is written.
- If `figma_components.md` was created from template in this run, note it in the transcript so the reader knows it was the first snapshot (no delta).

Required output:
1. Summary: N Figma components total (per tier), % traceable overall
2. Delta vs previous snapshot (ADDED / RENAMED / DEPRECATED / RESCOPED counts)
3. Top 5 priority queue entries with rationale
4. Open questions surfaced (ambiguous tier, proposed-rename pairs, etc.)
5. Recommended next command (typically `component-spec` on the #1 priority entry)

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- Every Figma component present in the source is represented as a row in the inventory file.
- Each row has tier inferred + node ID + spec/code/story columns filled (present or empty).
- Coverage summary recomputed with current counts and `% traceable`.
- Delta section reflects ADDED / RENAMED / DEPRECATED / RESCOPED vs previous snapshot (or "first snapshot" note).
- Priority queue refreshed; top 5 entries have rationale.
- No code, spec, or story files modified by this command (read-only against the WOS-UI surface).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Every claim about traceability ("spec exists" / "code exists" / "story exists") must reflect actual file presence checked at runtime, not inferred from past inventory state.

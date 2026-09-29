---
name: extract-foundations-from-screens
description: Extract canonical foundations docs (`foundations/color.md`, `foundations/typography.md`, `foundations/spacing.md`, `foundations/radii.md`) from a batch of existing SCREEN_SPECs. Idempotent: re-runs only add new tokens, never overwrite existing role mappings, and route conflicts to a Review queue. Use when SCREEN_SPECs already document raw values and you need to converge them into role tokens. Do not use when foundations are already curated and screens already reference role tokens (run `foundation-audit` instead).
metadata:
  category: design-and-ui
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5-5
---
# extract-foundations-from-screens

Act as a design system extractor that turns a cross-screen inventory of raw values into canonical Foundations docs.

Goal:
Read a set of `SCREEN_SPEC.md` files, union the raw values for the selected foundations (default: color, typography, spacing, radii), bucket each value into a role token per the per-foundation rules below, and write or update each selected `foundations/<area>.md` against the existing FOUNDATION templates. The operation is idempotent: re-running on a superset of screens only adds new tokens; existing role tokens are never overwritten; conflicts land in a `## Review queue` section instead of being silently resolved.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
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
- SCREEN_SPECs source: explicit list of paths OR glob (e.g. `design/screens/**/SCREEN_SPEC.md`).
- Design system folder root (e.g. `docs/research/`). The command writes under `<ds-root>/foundations/`.
- Optional: list of foundations to extract (default: all four -- `color`, `typography`, `spacing`, `radii`).

Task repository files to update:
- `<ds-root>/foundations/<area>.md` for each selected area (`color`, `typography`, `spacing`, `radii`)
- TASK_STATE.md (append extraction summary: N specs read, N tokens added, N review entries)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Resolve SCREEN_SPEC and foundation sets.** Expand the glob or accept the explicit list. Fail fast if zero files match. Resolve the selected foundations from the optional input, defaulting to all four. For each spec, record its path; it becomes the provenance link for every token it contributes.
- **Step 2: Parse raw values.** For each SCREEN_SPEC, extract only the selected foundations' values:
  - Colors: every hex (`#RRGGBB` / `#RGB`) regardless of section.
  - Typography tuples: `(family, weight, size_px, line_height_px)` from the Typography section.
  - Spacing values: every px integer found in spacing / layout sections.
  - Radii values: every px integer found in radius / corner sections.
  Record source spec path per value for provenance.
- **Step 3: Load existing foundations (idempotency anchor).** For each selected area, if `<ds-root>/foundations/<area>.md` exists, parse its `## Tokens` table. Existing role-to-value mappings are LOCKED -- they MUST be preserved verbatim. Any new candidate that collides with a locked role goes to the `## Review queue`, never overwrites.
- **Step 4: Apply per-foundation extraction rules to the selected areas.**
  - **Color** -- union all hexes. Bucket by inferred role from SCREEN_SPEC context (largest-area surfaces → `surface/canvas`, `surface/raised`, `surface/inverse`; foreground on surfaces → `text/default`, `text/muted`, `text/inverse`; CTA / link / focus → `accent/default`, `accent/strong`, `accent/soft`, `accent/stroke`). For each candidate hex, count usage across specs. Conflicts (e.g. `#0D0D0D` vs `#18181B` both arguing for `surface/inverse`) are NOT silently resolved -- both go to `## Review queue` with usage counts.
  - **Typography** -- collapse by `(family, weight, size, line-height)` tuple. Map size buckets to roles: `display` (≥32), `heading/lg|md|sm` (20-28), `body/lg|md|sm` (14-18), `caption` (12). Hold family constant when one family dominates; flag secondary families to `## Review queue`.
  - **Spacing** -- round every observed value to the nearest 4px grid step. Emit ordered scale `xxs(4) / xs(8) / sm(12) / md(16) / lg(24) / xl(32)`. Off-grid values (6, 10, 14, …) are reported under `## Review queue` as drift -- NEVER silently rounded into the scale.
  - **Radii** -- same shape as spacing on an `8 / 12 / 16 / 24` progression → `sm / md / lg / xl`. Values outside the observed scale go to `## Review queue`.
- **Step 5: Render foundation docs.** For each selected area, render against the matching template in `docs/research/_templates/foundations/<area>.md`. The `## Tokens` table MUST contain: role name, value, source SCREEN_SPECs (relative paths), usage count. Append a `## Review queue` section listing conflicts and off-rule values with the same columns plus a `Reason` cell (`conflict`, `off-grid`, `family-mismatch`, …). If a foundation has zero new entries and zero review items, do NOT rewrite the file -- emit `SKIP` per the global output contract.
- **Step 6: Idempotency check.** Diff the produced files against the on-disk version. If a re-run on the same input would produce byte-identical output, emit a `NO_OP_TRACE`. The acceptance contract: re-running with a screen that introduces no new values is a no-op on disk.
- **Step 7: Update TASK_STATE.md.** Append a one-line summary: `extract-foundations-from-screens: N specs, +Ac colors / +At typography / +As spacing / +Ar radii, R review`. Include counts only for selected areas and name any unselected areas as `not requested`.
- Never overwrite a locked role-to-value mapping from a prior run; always route the collision to `## Review queue`.
- Never silently round spacing or radii off-grid values into the scale.
- Never invent role names beyond the vocabulary above; semantic refinement is a human review step.
- Do not write Tailwind config, CSS variables, or any code artifact -- that belongs to a later `emit-foundations-tokens` command (non-goal here).

Required output:
1. Summary: N SCREEN_SPECs read, selected areas, per-selected-area token counts added vs preserved, review queue size.
2. Per-foundation breakdown for selected areas -- added roles, preserved roles, review entries; identify unselected areas as `not requested`.
3. Provenance check: confirm every new token cites at least one source SCREEN_SPEC.
4. Idempotency verdict: `NO_OP` if nothing changed, otherwise list of files touched.
5. Recommended next command (typically `foundation-audit` to verify the extraction against code, or `component-spec` to start consuming the new role tokens).

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
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- Every raw value in the selected areas from every SCREEN_SPEC is accounted for: it either appears in the `## Tokens` table of the matching foundation OR in the `## Review queue` of that foundation. No in-scope value is dropped silently, and no unselected foundation file is written.
- Every new token in `## Tokens` cites at least one source SCREEN_SPEC (provenance).
- No locked role-to-value mapping from a prior run was overwritten.
- Conflicts (color), off-grid values (spacing, radii), and secondary families (typography) live in `## Review queue`, not in the canonical scale.
- A re-run on the same SCREEN_SPEC set is byte-identical (`NO_OP_TRACE`).
- TASK_STATE.md has the extraction summary line.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Every token is grounded in at least one SCREEN_SPEC and one explicit per-foundation rule. When a value is ambiguous (conflicting hexes, off-grid pixel, second font family), prefer routing it to `## Review queue` over making a silent call. Foundations are the single source of truth downstream -- wrong silently is worse than slow loudly.

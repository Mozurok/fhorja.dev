---
name: design-bootstrap
description: Bootstrap a design system from a Figma file using MCP tools. Extracts token variables, identifies components, creates the directory structure, and generates scaffolded foundation docs and a component inventory. Use when starting a new project with a Figma design file. Do not use when the design system docs already exist or when there is no Figma file.
metadata:
  category: design-and-ui
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  lifecycle: frozen
  provenance: first-party
  suggested-model: claude-opus-5-5
---
# design-bootstrap

Act as a design system architect bootstrapping a new design system from a Figma file.

Goal:
Read a Figma file via MCP tools, extract design tokens (colors, typography, spacing, radii, elevation), identify components and screens, create the standard directory structure, and generate scaffolded foundation docs and a component inventory. This is the zero-state entry point for design system work, analogous to `project-bootstrap` for project-level memory.

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
- Figma file URL (e.g., `https://figma.com/design/:fileKey/:fileName`)
- project workspace path (where `docs/` and `packages/` will be created)
- optional: specific Figma page or frame to scope extraction

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Persona prompt (pre-Step 1):** Before extraction, ask the user for the persona set this product uses. Defaults to single-persona (no subfolders). Canonical multi-persona vocabulary per `wos/design-system-conventions.md` → `## Personas and screen organization`: `auth`, `shared`, `operative`, `controller`, `client`, `super-admin`. Custom personas allowed; record the chosen set in OPEN_QUESTIONS.md.
- **Step 1: Extract variables.** Call `get_variable_defs` on the Figma file to retrieve all design variables. Group by foundation area (color, typography, spacing, grid, radii, elevation, motion, iconography, effects).
- **Step 2: Extract metadata.** Call `get_metadata` to understand the file structure (pages, top-level frames, component sets).
- **Step 3: Identify components.** Use `get_libraries` only for library discovery. Traverse the source file's pages and frames with `get_metadata` to enumerate component and component-set nodes. If the source cannot be enumerated, report the inaccessible or truncated scope and request a readable source file or node before continuing. Classify each component by atomic tier (atom, molecule, organism, layout) per `wos/design-system-conventions.md`.
- **Step 4: Create directory structure.** Create the canonical WOS-UI layout (per `wos/design-system-conventions.md` → `## Repository structure (docs split)`):
  ```
  docs/research/
    README.md                          (from a brief stub)
    COMPONENT_GUIDELINES.md            (copy from templates/COMPONENT_GUIDELINES.md)
    ATOM_AUDIT.md                      (from templates/ATOM_AUDIT.md; empty table)
    _templates/
      COMPONENT.md                     (copy from templates/COMPONENT_SPEC.md)
      JOURNEY.md                       (copy from templates/JOURNEY_SPEC.md)
      FOUNDATION_SPEC.md               (generic, copy from templates/)
      foundations/                     (copy templates/foundations/*.md including README.md)
    _inventory/
      README.md                        (stub per Step 4b)
      figma_components.md              (from templates/INVENTORY.md scaffold)
    foundations/                       (populated by Step 5; one file per area)
    components/
      atoms/README.md                  (stub per Step 4b)
      molecules/README.md              (stub per Step 4b)
      organisms/README.md              (stub per Step 4b)
      layouts/README.md                (stub per Step 4b)
    patterns/README.md                 (stub per Step 4b; reusable UX patterns written by pattern-doc)
    journeys/README.md                 (stub per Step 4b)
  docs/app/
    README.md
    routes.md                          (copy from templates/ROUTES.md)
    navigation.md                      (copy from templates/NAVIGATION.md)
    SCREEN_MAP.md                      (copy from templates/SCREEN_MAP.md)
    _template.md                       (copy from templates/SCREEN_SPEC.md)
    screens/<persona>/README.md        (stub per Step 4b; one per persona, flat if single-persona)
  docs/OPEN_QUESTIONS.md               (copy from templates/OPEN_QUESTIONS.md)
  ```
- **Step 4b: Stub sub-folder READMEs.** Each created sub-folder MUST receive a minimal README on bootstrap so the structure is self-documenting before any spec is written. Without this step, sub-folder READMEs get authored slice-by-slice later, which fragments the work and produces inconsistent shapes across sub-folders. Each stub follows the same shape:
  ```markdown
  # <Folder title>

  <One-sentence purpose, per `wos/design-system-conventions.md`>

  ## Inventory

  | <appropriate columns> |

  ## Adding an entry

  Run `<owning command>` <with the relevant args>.
  ```
  Concrete stubs to generate:
  - `components/atoms/README.md` -- title "Atoms". Purpose: "Smallest indivisible UI elements; consume only tokens." Inventory columns: Component / Spec doc / Code dir / Story file. Owning command: `component-spec` with `tier=atom`.
  - `components/molecules/README.md` -- title "Molecules". Purpose: "Groups of 2+ atoms forming a distinct functional unit." Same inventory columns. Owning command: `component-spec` with `tier=molecule`.
  - `components/organisms/README.md` -- title "Organisms". Purpose: "Complex sections composed of molecules and atoms with their own layout logic." Same inventory columns. Owning command: `component-spec` with `tier=organism`.
  - `components/layouts/README.md` -- title "Layouts". Purpose: "Structural containers that define page-level arrangement." Same inventory columns. Owning command: `component-spec` with `tier=layout`.
  - `journeys/README.md` -- title "Journeys". Purpose: "Cross-screen user flows." Inventory columns: Journey / Spec doc / Personas / Status. Owning command: `journey-map`.
  - `_inventory/README.md` -- title "Figma Inventory". Purpose: "Snapshots of the upstream Figma component library." Inventory columns: Last refresh / Source / Component count / `% traceable`. Owning command: `inventory-snapshot`.
  - `app/screens/<persona>/README.md` -- one per persona declared in the Persona prompt. Title "Screens -- <persona>". Purpose: "Screens scoped to the `<persona>` persona; see `wos/design-system-conventions.md` for vocabulary." Inventory columns: # / Screen / Route / Status / Figma. Owning command: `screen-spec` with `persona=<persona>`.

  All stubs MUST link to `wos/design-system-conventions.md` for vocabulary and to the canonical templates under `docs/research/_templates/` (where applicable). Do not pad the stub beyond this minimum; the spec content lives in per-component / per-screen files, not in the sub-folder README.

- **Step 5: Generate foundation scaffolds -- per area.** For each foundation area observed in Figma, create `docs/research/foundations/<area>.md` from the matching `templates/foundations/<area>.md` sub-template (color, typography, spacing, grid, radii, elevation, motion, iconography, effects, states). Pre-fill extracted tokens in the Tokens table. Mark `confirmed` (observed in Figma) or `(proposed)` (inferred). If an area has no Figma variables, omit the file (do NOT stub) and note the omission in `foundations/README.md`. Always create `states.md` even when Figma has no variables for it -- it is cross-component vocabulary.
- **Step 6: Populate Figma components inventory.** Fill `docs/research/_inventory/figma_components.md` (already scaffolded in Step 4) with each identified component: Figma name, inferred tier, node ID, spec/code/story columns left blank for now. Counts and `% traceable` calculated at 0%.
- **Step 7: Populate SCREEN_MAP.md.** For each top-level frame that appears to be a screen (not a component definition), add a row to `docs/app/SCREEN_MAP.md` with: route (proposed if not yet decided), persona (inferred or `?`), screen name, status=`pending`, Figma node ID.
- **Step 8: Bootstrap OPEN_QUESTIONS.md.** Pre-populate with extraction-time ambiguities (e.g., `BRAND-01`: dark mode palette not observed in Figma; light mode only extracted). Use the prefix conventions from `wos/design-system-conventions.md` → `## Open questions tracking convention`.
- **Step 9: Code mirror scaffold (optional, only if monorepo paths exist).** If `packages/design-system/src/` and `apps/storybook/` exist in the workspace, create the tier subfolders to mirror docs:
  ```
  packages/design-system/src/{atoms,molecules,organisms,layouts}/  (empty; per-component dirs created by component-spec)
  apps/storybook/stories/{atoms,molecules,organisms,layouts}/      (empty)
  ```
  Skip silently if these paths do not exist (do NOT scaffold monorepo here; that is a separate task).
- **Step 10: Verify traceability split.** Confirm `docs/research/` and `docs/app/` are both populated and orthogonal per `wos/design-system-conventions.md`. Report the count of files created per tree in the output summary.
- Token naming must follow `wos/design-system-conventions.md` (semantic-first, not numeric).
- Mark anything derived but not directly observed as `(proposed)` in the docs.
- Do not invent components or tokens not present in the Figma file.
- Do not centralize design-system templates outside `docs/research/_templates/`. The repo-root `templates/` keeps the meta-templates that this command copies in.

Required output:
1. Summary of what was extracted (N colors, N typography scales, N spacing tokens, N foundations files, N components, N screens, N personas)
2. List of created files and directories grouped by `docs/research/` vs `docs/app/` vs code mirror (Step 9)
3. Open questions identified during extraction (with prefix IDs)
4. Counts: `docs/research/foundations/` files created, `docs/research/_inventory/figma_components.md` rows added, `docs/app/SCREEN_MAP.md` rows added, personas created
5. Recommended next command (typically `component-spec` for the highest-priority atom or `foundation-audit` for the most populated foundation area)

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
- Both `docs/research/` and `docs/app/` trees exist and are populated per the canonical layout.
- `_templates/` is colocated inside `docs/research/_templates/` (NOT centralized at repo root).
- Foundation files exist as granular per-area docs (one per observed area), NOT a single FOUNDATION_SPEC.md.
- `docs/research/_inventory/figma_components.md` and `docs/app/SCREEN_MAP.md` are populated with rows for every identified component/screen.
- `docs/app/screens/<persona>/` folders match the persona set declared in the prompt; single-persona products have flat `docs/app/screens/`.
- Every created sub-folder under `docs/research/components/`, `docs/research/journeys/`, `docs/research/_inventory/`, and `docs/app/screens/<persona>/` contains a stub README with the canonical shape from Step 4b.
- `ATOM_AUDIT.md` and `COMPONENT_GUIDELINES.md` exist (copied from templates, ready to fill).
- OPEN_QUESTIONS.md is bootstrapped with extraction-time ambiguities using prefix IDs.
- Token naming follows `wos/design-system-conventions.md` (semantic-first).
- Code mirror (`packages/design-system/src/<tier>/`, `apps/storybook/stories/<tier>/`) is created only if the monorepo already exists; skipped silently otherwise.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Extract faithfully from Figma. Mark observations vs proposals explicitly. Generate enough structure that the next person can continue documenting without re-reading the Figma file.

---
name: image-to-spec
description: Generate a design-system spec from a raw image file (a screenshot, mockup, or captured app screen) when there is no Figma source. Reads the image with vision and emits a COMPONENT_SPEC.md-shaped doc (--component) or a SCREEN_SPEC.md-shaped doc (--screen), auto-detecting the mode when no flag is given. A gated --gameplay mode (ADR-0084, off by default) instead derives a MECHANICS_SPEC.md behavior contract for a 2D game from screenshots, extracted video frames, and playtest notes, with every rule in EARS form tagged observed, assumed, or open. Every observation is marked proposed because an image is an inference source, not a source of truth. Use when you have only an image and want a structured spec the design cluster can consume. Do not use when a Figma node exists (use component-spec or screen-spec), when you want code rather than a spec, or to push the image into Figma (that is generate_figma_design, a separate capability).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---
# image-to-spec

Act as a design system researcher documenting a spec from a raw image, where there is no Figma source of truth.

Goal:
Read a user-supplied image file (a screenshot, a mockup, a captured app screen) and emit a structured spec the design cluster can consume: a `COMPONENT_SPEC.md`-shaped doc for a single component, or a `SCREEN_SPEC.md`-shaped doc for a full screen. Because an image is an inference source and not a source of truth, every observation is marked `proposed` (never `confirmed`). The spec is the bridge that lets the rest of the Figma-anchored cluster work from an image when no Figma file exists.

This command is distinct from:
- `component-spec` and `screen-spec`: which read FROM a Figma node (a node ID is required) and can mark Figma-direct observations `confirmed`. `image-to-spec` has no Figma source, so it marks everything `proposed`.
- `generate_figma_design` (Figma MCP): which routes an image or intent INTO Figma. `image-to-spec` does the opposite direction (image to a spec doc) and never touches Figma.
- image-to-code tooling: `image-to-spec` produces a spec, not an implementation (Fhorja is spec-first; code comes later through the normal slice pipeline).

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
- the image file path on disk (PNG, JPG, screenshot, mockup, or captured app screen)
- mode: `--component` (the image is a single UI element), `--screen` (the image is a full screen), `--gameplay` (the references are a 2D game and the goal is a mechanic contract, not a UI spec; ADR-0084), or omitted (auto-detect between component and screen)
- project workspace path
- (gameplay mode) one or more references: screenshots, extracted video frames, and the user's playtest or design notes; optional a gameplay video to mine frames from (requires local `ffmpeg`)
- optional: existing foundation docs (`color.md`, `typography.md`, `spacing.md`, `radii.md`) for token cross-referencing
- optional (component mode): atomic tier hint (atom | molecule | organism | layout)
- optional (screen mode): persona and a screen number + slug for file naming (`<NN>-<slug>`)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **No Figma, no web, no code.** This command reads only the image the user supplied on disk and writes only a spec doc. It MUST NOT call the Figma MCP, generate into Figma, or fetch the network, and it MUST NOT claim a Figma source it does not have. It produces a spec, never component code.
- **Proposed-only marking (the central honesty rule).** There is no source of truth behind an image, so every derived observation (dimensions, colors, spacing, radii, variants, states) is marked `(proposed)`. Never mark anything `confirmed`. The single exception is visible copy: text legible in the image is quoted verbatim (that is read, not inferred); all numeric and visual values around it remain `(proposed)` estimates. State up front that the whole spec is proposal-grade pending a real source.
- **Step 1: Read the image.** Read the supplied image file with vision. State plainly what it shows (a single component versus a full screen) and call out anything illegible or ambiguous.
- **Step 2: Select the mode.** If `--component` or `--screen` is given, use it. Otherwise auto-detect: an isolated single UI element (one button, card, chip, input) is `component`; a full layout with multiple regions (header, content, navigation) is `screen`. State the chosen mode and, when auto-detected, the one-line reason.
- **Step 3 (component mode): produce a COMPONENT_SPEC-shaped doc.** Follow `templates/COMPONENT_SPEC.md`. Cover anatomy, variants, sizes, the mandatory 6-state checklist from `wos/design-system-conventions.md` (default, pressed, focused, disabled, loading, error), accessibility (role, label source, touch target, contrast estimated from observed colors, Dynamic Type, Reduced Motion), motion and haptics, platform specifics, a proposed TypeScript props interface, a usage example, and anti-patterns. Mark every observation `(proposed)`. Flag 44pt touch-target compliance as an estimate.
- **Step 3 (screen mode): produce a SCREEN_SPEC-shaped doc.** Follow `templates/SCREEN_SPEC.md`. Cover an ASCII layout sketch, components used (each mapped to a design-system component or flagged as a candidate when it is not in the inventory), observed spacing (mapped to spacing tokens when foundations exist), data dependencies, verbatim copy (ready for i18n), accessibility (announcement, focus order, Dynamic Type), interactions, and error states. Mark every observation `(proposed)`.
- **Step 4: Cross-reference foundations when present.** When foundation docs exist in the workspace, reference tokens by semantic name and note where an observed value does not map to the scale. When no foundations exist, propose token candidates rather than hard-coding raw values, and note that they need confirmation.
- **Step 5: Log open questions.** Record ambiguities (illegible values, uncertain component identity, missing states) in `OPEN_QUESTIONS.md` with the appropriate prefix, so a later Figma-anchored pass can resolve them.
- **Step 6: Write to file.** Component mode: `docs/research/components/<tier>/<component-name>.md`. Screen mode: `docs/app/screens/<persona>/<NN>-<slug>.md` (multi-persona) or `docs/app/screens/<NN>-<slug>.md` (single-persona), and append or update the `docs/app/SCREEN_MAP.md` row with status `drafted` and source `image` (no Figma node ID). Match the cluster's existing file conventions; the only difference is the source is an image, recorded as such.
- Do not overstate precision: an image-derived spec is a strong starting point, not a verified one. Recommend a Figma-anchored pass (`component-spec` / `screen-spec`) when a Figma file later becomes available.
- **Gameplay mode (gated, `--gameplay`; ADR-0084, off by default).** When invoked with `--gameplay` (or when the references are clearly a game and the objective is a mechanic rather than a UI element), produce a `MECHANICS_SPEC.md` instead of a component or screen spec: a behavior contract for a 2D game derived from the references. This mode exists because a visual reference cannot convey behavior over time (a ring that closes, a hole the ball escapes through, a lose condition); the dogfood behind ADR-0084 shipped a wrong core mechanic precisely because a screenshot silently stood in for a behavior spec.
  - **Inputs it reads.** One or more screenshots, extracted video frames, and the user's playtest or design notes. Reference media arrives through the `capture-references` media-ingestion path (user-supplied local files, or direct-file URLs the user has rights to); this command never fetches media itself. Video-frame mining is opt-in and requires local `ffmpeg`: a user-supplied gameplay video is consumed via frame extraction, canonical form `ffmpeg -i clip.mp4 -vf fps=1 frames/f_%03d.png`, with the fps tuned to the mechanic's tempo, and the extracted frames land next to the other reference images this mode reads. STATE the sampling rate used, because a low rate (one frame every few seconds) misses time-based mechanics (a closing aperture, a spawn cadence). A mechanic a low sampling rate could have missed is tagged `open`, never guessed. Reference quality governs spec quality: real gameplay frames plus the user's text grounding raise rules from `assumed` to `observed`; screenshots alone leave time-based rules `assumed` or `open`.
  - **Output: `MECHANICS_SPEC.md`** in the active task folder. Every rule is written in EARS form (per ADR-0031: `WHEN <trigger> the <system> SHALL <response>`, `IF <trigger> THEN the <system> SHALL <response>`, and the other canonical forms) and tagged exactly one of:
    - `observed`: the rule is directly visible in a supplied reference (cite which frame or screenshot).
    - `assumed`: a reasonable inference not directly shown (state the inference).
    - `open`: a rule that matters but cannot be determined from the references.
  - **Cover at least:** the core loop (the repeated moment-to-moment action), each interaction rule (what the player does and how the world responds), the win condition, the lose condition, and any time-based behavior (things that change on their own over time). A game with no stated lose condition gets an `open` lose-condition row, never an assumed default.
  - **Routing (the forcing function).** Any `assumed` or `open` rule that affects a win condition, a lose condition, or a core interaction MUST be surfaced for `decision-interview` before the mechanic is implemented; list these under an `## Unresolved mechanics` heading in the spec. `godot-scene-plan` then consumes `MECHANICS_SPEC.md` and refuses to plan on an assumed mechanic (ADR-0084).
  - This mode adds an output shape; it does not relax the proposed-only honesty rule (an `observed` tag is still proposal-grade until a real playtest confirms it) or the no-Figma, no-web, no-code rules. Without the flag and on a non-game image, the component and screen modes are unchanged.

Required output:
1. Source image and the chosen mode (given, or auto-detected with the one-line reason)
2. An explicit statement that the whole spec is `(proposed)` (no Figma ground truth)
3. The generated spec doc (COMPONENT_SPEC shape in component mode, SCREEN_SPEC shape in screen mode)
4. Components-used or candidate-components list (screen mode), or variants/sizes/states (component mode)
5. Open questions logged
6. Recommended next command (typically `component-spec` / `screen-spec` to upgrade against Figma when available, `design-spec-review` to check an implementation against this spec, or `implementation-plan` to build from it). In gameplay mode: `decision-interview` when the `## Unresolved mechanics` list is non-empty, otherwise `godot-scene-plan` to design the scene against the spec.
7. (gameplay mode) The generated `MECHANICS_SPEC.md`: every rule in EARS form tagged `observed`, `assumed`, or `open`, with win and lose conditions each present, and the `## Unresolved mechanics` list of assumed or open rules routed to `decision-interview`. When video frames were mined, the ffmpeg sampling rate used.

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
- The chosen mode is stated (given, or auto-detected with a one-line reason), and the spec matches the corresponding template shape (COMPONENT_SPEC in component mode, SCREEN_SPEC in screen mode).
- Every observation is marked `(proposed)`; nothing is marked `confirmed` (there is no Figma source). Visible copy is the only verbatim content; numeric and visual values are proposed estimates.
- No Figma MCP call, no generate-into-Figma, and no web fetch is made or claimed.
- Foundation tokens are referenced by semantic name when foundations exist, or proposed as candidates when they do not.
- Open questions are logged in `OPEN_QUESTIONS.md`; screen mode adds or updates the `SCREEN_MAP.md` row with source `image`.
- Gameplay mode (when invoked): `MECHANICS_SPEC.md` exists; every rule is EARS-form and tagged `observed`, `assumed`, or `open`; the win condition and the lose condition each have a row (an undetermined one tagged `open`, never an assumed default); every `assumed` or `open` rule affecting a win, lose, or core-interaction rule is listed under `## Unresolved mechanics` for `decision-interview`; and when video frames were mined the ffmpeg sampling rate is stated. Imposing the gameplay output shape on a non-game image, or emitting a component or screen spec for a `--gameplay` invocation, is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A developer reading only this spec should be able to start building, knowing every value is a proposal to confirm. Honesty about precision (proposed-only, no invented Figma source) matters more than the appearance of completeness.

<!-- cache-breakpoint -->

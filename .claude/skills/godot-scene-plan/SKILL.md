---
name: godot-scene-plan
description: |-
  Plan the Godot scene and node structure for a 2D game feature before any GDScript is written: the scene tree, node types and responsibilities, autoloads (singletons), signal wiring, the input map, and the resources and sub-scenes to create. Produces GODOT_SCENE_PLAN.md, a design-time plan an MCP-driven editor or a human then builds against. Capability-routed and MCP-agnostic (names no specific server). Consults the Godot reference topics (architecture, interaction-and-feel) for save-state, touch, and feedback-layer depth. Use when a Godot 2D feature or screen needs its scene architecture decided before implementation. Do not use to frame whether the game idea is right (use problem-framing in its game-design mode), to slice an already-planned build (use implementation-plan), to analyze blast radius of an existing Godot project (use impact-analysis), to verify a running scene (use godot-runtime-verify), or with no active task folder (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
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
  token-budget: 2400
  suggested-model: claude-sonnet-4-6
---

Act as a senior Godot engineer planning the scene and node architecture for a 2D game feature before any code is written.

Goal:
For a given game feature or screen (a player, a level, a HUD, a menu), decide the Godot scene structure: the scene tree and node types, what each node is responsible for, which autoloads (singletons) the feature needs, how nodes communicate through signals, the input map actions, and the resources and sub-scenes to create. Produce a scene plan doc at `GODOT_SCENE_PLAN.md` in the active task folder that an MCP-driven editor or a human can build against without re-deciding the architecture. The plan is engine-grounded and stays MCP-agnostic: it never names a specific MCP server, because the contract is the scene design, not the tool that applies it (DECISIONS D-1, D-4).

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
- the feature or screen to plan (one or two sentences: what it is and what it does)
- the game-design context, when available (the core loop, mechanics, and constraints from a game-design brief or from `problem-framing` in its game-design mode)
- `MECHANICS_SPEC.md` when it exists (the behavior contract from `image-to-spec --gameplay`, ADR-0084): the interaction, win, and lose rules the scene must realize, each tagged observed, assumed, or open
- the target Godot major version, when known (the plan stays version-flexible; note 4.6+ when editor-driven on-device testing matters, per DECISIONS D-5)
- the existing project layout, for a brownfield feature (so the plan reuses existing autoloads, scenes, and the input map instead of duplicating them)

Operating rules:
- Do not write GDScript or create scene files; this command plans the structure, it does not implement it.
- **K.2 scope note (P2-8, dogfood-wave-2 2026-07-12):** this command's own artifact (`GODOT_SCENE_PLAN.md`) is outside the K.2 11-file substrate scope (`commands/_shared/substrate-write-protocol.md`) and needs no transaction header. Update `TASK_STATE.md`'s `## Last completed step` afterward as ordinary operator hygiene.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- MCP-agnostic: never name a specific MCP server in the plan. The plan is the scene design; whichever editor-control tool (or a human) applies it is out of scope (DECISIONS D-1).
- GDScript is the default language target; note the experimental C# iOS export caveat only when the feature's language choice is genuinely open and mobile export is in scope (DECISIONS D-6).
- No-op rule: if a valid `GODOT_SCENE_PLAN.md` already covers this feature with no material change, do not rewrite it; return a short NO_OP note and route forward.
- **Git preflight (F-9 fold, ADR-0089).** Check the target game directory before planning: IF it is not a git repository (no `.git`) THEN surface that as a blocking preflight and name the fix (`git init` plus a first commit of `project.godot`, to happen at the first `implement-approved-slice` invocation once `game/`/`project.godot` actually exist, not inside this command, which runs before either file exists). The commit-evidence closure floors (ADR-0084) presuppose a repository; the dogfood behind this rule built an entire POC un-versioned and had to `git init` manually at delivery time. This is a routing preflight, not an auto-init: state the gap and the one-line fix here, and do not run `git init` unprompted, here or later.
- **Step 1: Restate the feature and its responsibilities.** One paragraph: what the feature is, what it owns, and what it explicitly does not own. Name the game-design context it serves.
- **Step 1a: Mechanic contract (mandatory; ADR-0084).** Before designing the scene tree, state the mechanic contract the scene realizes. WHEN a `MECHANICS_SPEC.md` exists (from `image-to-spec --gameplay`), cite the specific rules this scene implements (the core loop, the interaction rules, the win condition, the lose condition) by their spec tag. IF a rule the scene depends on is tagged `assumed` or `open`, or is absent from the spec, log it as an open question routed to `decision-interview` and DO NOT design the scene around an assumed default. WHEN no `MECHANICS_SPEC.md` exists at all (a `problem-framing --game-design` or `decision-interview`-sourced game, a sanctioned intake path per Required Inputs below), cite the specific `DECISIONS.md` D-N entries (or `BRIEF.md` fields) that constitute the mechanic contract instead; the same rule applies, an assumed or missing rule in that source is still routed to `decision-interview`, not silently designed around. A scene plan that silently bakes in an undocumented mechanic is invalid output: the dogfood behind ADR-0084 built a whole core loop on an assumed ring mechanic that turned out wrong. Name the contract before the nodes that realize it.
- **Step 1b: Screen graph (mandatory for a multi-screen game; ADR-0084).** WHEN the feature belongs to a multi-screen game (menu, gameplay, score, reward, retry), specify the screen graph before the per-screen scene plans: the game states (at least a win state and a lose state) and the transitions that wire the screens together (stage complete to score to reward to next stage; a lose condition to retry). This step owns the connective flow that per-screen plans each disown; leaving it unowned is the ADR-0084 failure where the score and reward flow did not exist until a playtest surfaced it. For a single self-contained feature with no cross-screen flow, say so and skip the graph.
- **Step 2: Design the scene tree.** Lay out the node hierarchy as an indented tree. For each node give its type (the Godot built-in class, e.g. `CharacterBody2D`, `Area2D`, `AnimatedSprite2D`, `CollisionShape2D`, `Camera2D`, `CanvasLayer`, `Control`) and a one-line responsibility. Prefer the smallest tree that works; do not add nodes a responsibility does not require (YAGNI).
- **Step 3: Decide autoloads (singletons).** List the autoloads the feature needs (e.g. a game-state store, an audio manager, an event bus) with what each holds and why a singleton is the right scope. For a brownfield feature, reuse existing autoloads rather than adding new ones; flag any new autoload as a deliberate decision. For the autoload-versus-shared-Resource choice and, when the feature persists progress, the save-state design (a save schema, `user://` paths, the serialization choice, and auto-save on `NOTIFICATION_APPLICATION_PAUSED`), consult `wos/godot-2d-architecture.md`. **Audio ruling (recorded decision; ADR-0084):** for a game with any sound, cite here the ship-with-or-without-audio decision, either an audio autoload and wired settings are in scope, or shipping silent is an explicit non-goal; "polish later" prose does not satisfy it, because the dogfood shipped inert Sound and Music toggles that controlled nothing. This plan cites the decision, it does not own it: the decision itself is a `decision-interview`-owned `DECISIONS.md` D-N entry (per `wos/substrate-peers.md`), the same routing the mechanic contract (Step 1a) already uses for an assumed or open rule. Consult `wos/godot-2d-audio.md` for the bus layout, SFX pooling, and the settings-to-mixer wiring that closes the inert-toggle gap.
- **Step 4: Wire signals.** For each cross-node interaction, name the emitter node, the signal, the listener, and the payload. Prefer signals over direct node references for decoupling; call out where a direct reference is the simpler correct choice. This is the scene's communication contract. When the feature has game-feel (screen shake, haptics, audio feedback), plan the feedback layer (a shake or camera autoload, a haptics call site, an audio-feedback pool) and its signal wiring here, and consult `wos/godot-mobile-interaction-and-feel.md` for the proportional-feedback and mobile-constraint rules. A typed-Node `@export` (e.g. `@export var target: Marker2D`) assigned as a bare `NodePath` value in hand-authored `.tscn` text does not resolve; it silently fails at the point of use (a "Nil has no property" error far from the real cause), not at load or import time. When authoring `.tscn` text by hand without a live editor, plan a plain `NodePath` export instead, resolved manually via `get_node()` in `_ready()`.
- **Step 5: Define the input map.** List the input actions the feature needs (e.g. `move_left`, `jump`, `pause`) and the device classes each must support (keyboard, touch, gamepad). For a 2D mobile target, state the touch mapping explicitly; do not assume keyboard-only. For the mobile touch model (per-finger index tracking, `TouchScreenButton` vs a Control button, the on-screen controls layer and safe area, and the mouse-versus-touch emulation decision), consult `wos/godot-mobile-interaction-and-feel.md`.
- **Step 6: List resources and sub-scenes.** Enumerate the `.tscn` sub-scenes, `.tres` resources, and assets the feature instantiates (e.g. a reusable enemy scene, a tilemap, a particle resource), with a one-line purpose each. Mark which already exist vs which are new. **Placeholder-asset policy (recorded decision; ADR-0084):** when the feature uses placeholder art (colored rects, programmer sprites), cite here what is placeholder, what "final" means, and the swap trigger, so "add art later" does not become a silent permanent state and the swap stays a clean slice. As with the audio ruling above, this plan cites the decision from a `decision-interview`-owned `DECISIONS.md` D-N entry rather than owning it directly. Consult `wos/godot-2d-asset-pipeline.md` for the import settings, atlas, placeholder-to-final, and licensing rules.
- **Step 7: Note 2D-mobile fit.** When the target is mobile, note the viewport and aspect-ratio strategy, the renderer choice for low-end devices, and any node choice driven by the mobile target. Mark device-specific numbers as `[to confirm]` rather than inventing thresholds; defer concrete budgets to `performance-budget` in its Godot mobile profile.
- **Step 8: Log open questions.** Architecture ambiguities that need a decision (a missing mechanic detail, an undecided autoload scope) routed to `decision-interview`, and factual gaps routed to `targeted-questions`.
- **Step 9: Write the plan.** Save as `GODOT_SCENE_PLAN.md` (or `GODOT_SCENE_PLAN_<feature-slug>.md` when the task plans several features) in the active task folder.

Required output:
1. Feature identity (name, what it owns, the game-design context it serves)
2. The mechanic contract (Step 1a): the `MECHANICS_SPEC.md` rules the scene realizes, or the open questions routed to `decision-interview` where a rule is assumed, open, or absent
3. The screen graph (Step 1b) when the feature is part of a multi-screen game (game states plus cross-screen transitions), or an explicit note that the feature is self-contained
4. The generated `GODOT_SCENE_PLAN.md` (the scene tree, autoloads with the audio ruling, signals, input map, resources and sub-scenes with the placeholder-asset policy, 2D-mobile notes)
5. Reused vs new (existing autoloads/scenes/input actions reused; new ones added, each as a deliberate decision)
6. Open questions and their routing
7. Recommended next command

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
- The scene tree names a Godot node type and a one-line responsibility for every node, and is the smallest tree that satisfies the feature.
- Autoloads, signals, the input map, and resources/sub-scenes are each addressed; reused-vs-new is explicit for a brownfield feature.
- The mandatory Mechanic contract (Step 1a) is present: every mechanic the scene realizes is cited from `MECHANICS_SPEC.md`, or an assumed, open, or missing rule is routed to `decision-interview`; a scene designed around an undocumented assumed mechanic is invalid output (ADR-0084). For a multi-screen game the screen graph (Step 1b) specifies the win and lose states and the cross-screen transitions. For a game with sound the audio ruling is recorded; for a game with placeholder art the placeholder-asset policy is recorded (ADR-0084); "polish later" prose satisfies neither.
- The plan names no specific MCP server (MCP-agnostic, DECISIONS D-1) and invents no device-specific performance numbers (deferred to `performance-budget`).
- `GODOT_SCENE_PLAN.md` is written in Agent mode (or PROPOSED in Ask/Plan mode per ADR-0001).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A Godot engineer (or an MCP-driven editor) reading the plan should be able to build the scene without re-deciding the node types, the signal wiring, or the input map. Prefer the smallest correct scene tree over a clever one.

<!-- cache-breakpoint -->

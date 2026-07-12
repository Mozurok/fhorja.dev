---
name: godot-scene-plan
description: Plan the Godot scene and node structure for a 2D game feature before any GDScript is written: the scene tree, node types and responsibilities, autoloads (singletons), signal wiring, the input map, and the resources and sub-scenes to create. Produces GODOT_SCENE_PLAN.md, a design-time plan an MCP-driven editor or a human then builds against. Capability-routed and MCP-agnostic (names no specific server). Consults the Godot reference topics (architecture, interaction-and-feel) for save-state, touch, and feedback-layer depth. Use when a Godot 2D feature or screen needs its scene architecture decided before implementation. Do not use to frame whether the game idea is right (use problem-framing in its game-design mode), to slice an already-planned build (use implementation-plan), to analyze blast radius of an existing Godot project (use impact-analysis), to verify a running scene (use godot-runtime-verify), or with no active task folder (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2400
  suggested-model: claude-sonnet-4-6
---
# godot-scene-plan

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
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- MCP-agnostic: never name a specific MCP server in the plan. The plan is the scene design; whichever editor-control tool (or a human) applies it is out of scope (DECISIONS D-1).
- GDScript is the default language target; note the experimental C# iOS export caveat only when the feature's language choice is genuinely open and mobile export is in scope (DECISIONS D-6).
- No-op rule: if a valid `GODOT_SCENE_PLAN.md` already covers this feature with no material change, do not rewrite it; return a short NO_OP note and route forward.
- **Git preflight (F-9 fold, ADR-0089).** Check the target game directory before planning: IF it is not a git repository (no `.git`) THEN surface that as a blocking preflight and route to initializing one (`git init` plus a first commit of `project.godot`) BEFORE any implementation slice runs. The commit-evidence closure floors (ADR-0084) presuppose a repository; the dogfood behind this rule built an entire POC un-versioned and had to `git init` manually at delivery time. This is a routing preflight, not an auto-init: state the gap and the one-line fix, and do not run `git init` unprompted.
- **Step 1: Restate the feature and its responsibilities.** One paragraph: what the feature is, what it owns, and what it explicitly does not own. Name the game-design context it serves.
- **Step 1a: Mechanic contract (mandatory; ADR-0084).** Before designing the scene tree, state the mechanic contract the scene realizes. WHEN a `MECHANICS_SPEC.md` exists (from `image-to-spec --gameplay`), cite the specific rules this scene implements (the core loop, the interaction rules, the win condition, the lose condition) by their spec tag. IF a rule the scene depends on is tagged `assumed` or `open`, or is absent from the spec, log it as an open question routed to `decision-interview` and DO NOT design the scene around an assumed default. WHEN no `MECHANICS_SPEC.md` exists at all (a `problem-framing --game-design` or `decision-interview`-sourced game, a sanctioned intake path per Required Inputs below), cite the specific `DECISIONS.md` D-N entries (or `BRIEF.md` fields) that constitute the mechanic contract instead; the same rule applies, an assumed or missing rule in that source is still routed to `decision-interview`, not silently designed around. A scene plan that silently bakes in an undocumented mechanic is invalid output: the dogfood behind ADR-0084 built a whole core loop on an assumed ring mechanic that turned out wrong. Name the contract before the nodes that realize it.
- **Step 1b: Screen graph (mandatory for a multi-screen game; ADR-0084).** WHEN the feature belongs to a multi-screen game (menu, gameplay, score, reward, retry), specify the screen graph before the per-screen scene plans: the game states (at least a win state and a lose state) and the transitions that wire the screens together (stage complete to score to reward to next stage; a lose condition to retry). This step owns the connective flow that per-screen plans each disown; leaving it unowned is the ADR-0084 failure where the score and reward flow did not exist until a playtest surfaced it. For a single self-contained feature with no cross-screen flow, say so and skip the graph.
- **Step 2: Design the scene tree.** Lay out the node hierarchy as an indented tree. For each node give its type (the Godot built-in class, e.g. `CharacterBody2D`, `Area2D`, `AnimatedSprite2D`, `CollisionShape2D`, `Camera2D`, `CanvasLayer`, `Control`) and a one-line responsibility. Prefer the smallest tree that works; do not add nodes a responsibility does not require (YAGNI).
- **Step 3: Decide autoloads (singletons).** List the autoloads the feature needs (e.g. a game-state store, an audio manager, an event bus) with what each holds and why a singleton is the right scope. For a brownfield feature, reuse existing autoloads rather than adding new ones; flag any new autoload as a deliberate decision. For the autoload-versus-shared-Resource choice and, when the feature persists progress, the save-state design (a save schema, `user://` paths, the serialization choice, and auto-save on `NOTIFICATION_APPLICATION_PAUSED`), consult `wos/godot-2d-architecture.md`. **Audio ruling (recorded decision; ADR-0084):** for a game with any sound, record the ship-with-or-without-audio decision here, either an audio autoload and wired settings are in scope, or shipping silent is an explicit non-goal; "polish later" prose does not satisfy it, because the dogfood shipped inert Sound and Music toggles that controlled nothing. Consult `wos/godot-2d-audio.md` for the bus layout, SFX pooling, and the settings-to-mixer wiring that closes the inert-toggle gap.
- **Step 4: Wire signals.** For each cross-node interaction, name the emitter node, the signal, the listener, and the payload. Prefer signals over direct node references for decoupling; call out where a direct reference is the simpler correct choice. This is the scene's communication contract. When the feature has game-feel (screen shake, haptics, audio feedback), plan the feedback layer (a shake or camera autoload, a haptics call site, an audio-feedback pool) and its signal wiring here, and consult `wos/godot-mobile-interaction-and-feel.md` for the proportional-feedback and mobile-constraint rules.
- **Step 5: Define the input map.** List the input actions the feature needs (e.g. `move_left`, `jump`, `pause`) and the device classes each must support (keyboard, touch, gamepad). For a 2D mobile target, state the touch mapping explicitly; do not assume keyboard-only. For the mobile touch model (per-finger index tracking, `TouchScreenButton` vs a Control button, the on-screen controls layer and safe area, and the mouse-versus-touch emulation decision), consult `wos/godot-mobile-interaction-and-feel.md`.
- **Step 6: List resources and sub-scenes.** Enumerate the `.tscn` sub-scenes, `.tres` resources, and assets the feature instantiates (e.g. a reusable enemy scene, a tilemap, a particle resource), with a one-line purpose each. Mark which already exist vs which are new. **Placeholder-asset policy (recorded decision; ADR-0084):** when the feature uses placeholder art (colored rects, programmer sprites), record what is placeholder, what "final" means, and the swap trigger, so "add art later" does not become a silent permanent state and the swap stays a clean slice. Consult `wos/godot-2d-asset-pipeline.md` for the import settings, atlas, placeholder-to-final, and licensing rules.
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

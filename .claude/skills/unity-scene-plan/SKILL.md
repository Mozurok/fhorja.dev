---
name: unity-scene-plan
description: |-
  Plan the Unity GameObject hierarchy and component architecture for a 3D feature before any C# is written: the scene and prefab structure, what each MonoBehaviour owns, the input model, and, for multiplayer, the networked-authority declarations. Produces UNITY_SCENE_PLAN.md. Capability-routed and MCP-agnostic. A 3D plan SHALL declare its render pipeline and a multiplayer plan SHALL declare its topology, or the plan is incomplete. Do not use to frame whether the game idea is right (use problem-framing in its game-design mode), to slice an already-planned build (use implementation-plan), to analyze blast radius of an existing project (use impact-analysis), to verify a running build (use app-runtime-verify with its Unity adapter), or with no active task folder (run task-init first).
metadata:
  category: "game-and-engine"
  primary-cursor-mode: "Agent"
  multi-repo-aware: "false"
  context-layers-consumed: "memory, retrieved"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5-5"
---

Act as a senior Unity engineer planning the scene and component architecture for a 3D feature before any code is written.

Goal:
For a given Unity feature or screen, decide the structure: the GameObject hierarchy, which MonoBehaviour owns which responsibility, what becomes a prefab, how objects communicate, the input model, and, when the feature is networked, who is authoritative over what. Produce `UNITY_SCENE_PLAN.md` in the active task folder that an MCP-driven editor or a human can build against without re-deciding the architecture. MCP-agnostic: the plan is the design, and whichever editor-control tool or human applies it is out of scope (ADR-0132). Note that a vetted Unity MCP surface may not cover every operation this plan emits; assembly definitions, project settings, and render-pipeline configuration were absent from the surface vetted on 2026-08-07, so name which steps are human-applied rather than assuming automation.

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
- active task folder path
- the feature or screen to plan (one or two sentences: what it is and what it does)
- the target platform set, since the render-pipeline declaration below is decided against it
- whether the feature is networked, and the game-design context when available
- the existing project layout, for a brownfield feature, so the plan reuses existing prefabs, assemblies, and input actions rather than duplicating them

Operating rules:
- Do not write C# and do not create scenes, prefabs, or assets; this command plans the structure, it does not implement it.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- MCP-agnostic: never name a specific MCP server. Before trusting any server to apply this plan, route it through `mcp-server-vet`.
- No-op rule: if a valid `UNITY_SCENE_PLAN.md` already covers this feature with no material change, do not rewrite it; return a short NO_OP note and route forward.
- **Step 1: Restate the feature and its responsibilities.** One paragraph: what the feature owns, and what it explicitly does not own.
- **Step 2: Declare the render pipeline (REQUIRED for a 3D target; ADR-0132).** State the pipeline (URP, HDRP, or Built-in), the target graphics API per shipping platform, and a one-line reason whenever the choice is anything other than URP on a mobile target. Reason from HDRP's enumerated platform list and its two mechanism requirements (compute shader support; OpenGL and OpenGL ES unsupported) rather than from a blanket claim about mobile, and do NOT assert that Unity recommends URP for mobile, because no captured page says so. Consult `wos/unity-mobile-rendering-and-performance.md`. **A 3D plan with no declared pipeline is incomplete**: a feature authored against the wrong one is not portable and nothing at build time says so early.
- **Step 3: Design the GameObject hierarchy.** Lay out the structure as an indented tree. For each GameObject give its purpose and the components it carries (`Rigidbody`, `Collider`, `MeshRenderer`, `Camera`, `CharacterController`, `Animator`, and the feature's own MonoBehaviours). Prefer the smallest tree that works; do not add objects a responsibility does not require. **A networked feature has TWO trees, not one (dogfood 2026-08-07, F-1):** the scene tree, and the tree of each prefab spawned at runtime by the netcode layer. They have different lifetimes and the spawned prefab is deliberately ABSENT from the scene, so lay them out separately and label which is which. A single merged tree containing a runtime-spawned player is wrong, and it is the shape this step produced before the rule existed.
- **Step 4: Assign component responsibilities.** For each MonoBehaviour, one line stating what it owns and what it does not. This is the step that most often goes undecided and then gets decided accidentally by whoever writes the first script. Name the serialized fields each needs, and prefer `[SerializeField]` on a private field over a public one. When renaming a serialized field on existing content, note that `FormerlySerializedAs` is what preserves the existing value. **For a networked feature, every component also carries WHERE IT RUNS (dogfood 2026-08-07, F-2):** owner-only, server-only, or everywhere. This is not a detail of Step 7; it is the per-component form of the authority decision, and without it a plan can name an input sampler that runs on the server and a movement simulator that runs on the client, satisfy every other rule in this command, pass its own self-review, and describe a cheatable architecture. State it per row.
- **Step 5: Decide what becomes a prefab.** State which subtrees become prefabs, which become variants, and where nesting is used. Prefabs are the unit of reuse and the unit of merge conflict, so a subtree edited by more than one person is a prefab candidate for that reason alone; consult `wos/bug-classes/unity-scene-prefab-yaml-corruption.md` for what a naive merge does to one. **For a networked feature, state the registration too (dogfood 2026-08-07, F-3):** a prefab spawned over the network must be registered with the netcode layer's prefab list or the spawn fails at runtime, and that is a prefab decision rather than an implementation detail.
- **Step 6: Decide the input model.** Name the input actions the feature needs and the device classes each supports (touch, gamepad, keyboard). For a mobile target state the touch mapping explicitly; do not assume keyboard. **For a networked feature, state where input is SAMPLED and where it is APPLIED (dogfood 2026-08-07, F-4),** because under server authority those are different machines and the step otherwise reads as the single-player case.
- **Step 7: Declare the networked authority (REQUIRED when the feature is networked; ADR-0132).** State the topology and authority model, the per-object ownership at spawn and whether it transfers, the sync primitive for each piece of replicated data decided by the late-joiner test, the tick rate and its relation to the physics timestep, and the determinism posture. WHEN the feature's acceptance depends on client-side prediction, reconciliation, or lag compensation, state who builds it, because Netcode for GameObjects ships none of the three. Consult `wos/unity-netcode-architecture.md`. Skip this step entirely for a single-player feature and say so.
- **Step 8: Name the test assembly.** State which assembly definition the feature's tests belong to and whether it already exists, since a Unity test outside a test assembly never runs and nothing errors. Consult `wos/unity-testing-and-ci.md`.
- **Step 9: Name what is human-applied.** List the steps above whose output no vetted MCP surface can currently apply (assembly definitions, project settings, render-pipeline configuration as of the 2026-08-07 vet), so the build step does not silently stall on them.
- **Self-review before emit.** Confirm the render-pipeline declaration is present for a 3D target and the authority declaration is present for a networked one. A plan missing either is incomplete output, not a plan with a gap.

Required output:
1. Feature restatement and responsibilities
2. Render-pipeline declaration (pipeline, graphics API per platform, reason when not URP on mobile)
3. GameObject hierarchy as an indented tree with components per object
4. Component responsibility table (what each MonoBehaviour owns and does not own)
5. Prefab decisions (prefabs, variants, nesting)
6. Input model (actions and device classes)
7. Networked authority declaration, or an explicit single-player note
8. Test assembly placement
9. Human-applied steps
10. Recommended next command

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
- `UNITY_SCENE_PLAN.md` is written in Agent mode.
- A 3D target carries a render-pipeline declaration naming the pipeline and the graphics API per shipping platform; a plan without one is incomplete output.
- A networked feature carries the authority declaration (topology, per-object ownership, sync primitive per datum, tick rate, determinism posture); a single-player feature carries an explicit note that the step was skipped.
- Every MonoBehaviour in the hierarchy has a stated responsibility; an unassigned component is a decision deferred, not a plan.
- The test assembly is named, and the human-applied steps are listed rather than assumed automatable.
- No C# is written and no scene, prefab, or asset is created by this command.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The plan is worth writing only if it removes decisions from the implementer's plate. A hierarchy with unassigned responsibilities, a 3D plan with no declared pipeline, or a networked plan that leaves authority implicit has deferred the hard parts under the appearance of planning.

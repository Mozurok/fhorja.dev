# ADR-0132: unity-scene-plan ships as a capability-named command, closing D-7 on an empirical test

- **Status**: Accepted
- **Date**: 2026-08-07
- **Tags**: unity, 3d, scene-plan, new-command, capability-routed, render-pipeline, closes-d7, extends-adr-0130, upholds-adr-0069-d4

## Context

ADR-0130 delivered Unity 3D as an adapter plus widenings with no net-new command, and left `unity-scene-plan` as decision D-7, marked `[OPEN]` and blocking `task-close`. It did so deliberately: both reuse maps from the 2026-08-06 research round ruled out every existing planning command on stated mechanism grounds, but the adversarial critique showed the STRONG rating had been argued past the strict gap rule the map claimed to apply, since `reuse-map-commands.md` conceded in its own text that `godot-scene-plan` "mechanically could be widened". Building it and permanently refusing it both overreached that evidence.

ADR-0130 named what would settle it: plan one real Unity feature through the existing surface and see whether the plan is unactionable without a Unity-specific host. The maintainer chose that method over deciding from argument.

The test was run on 2026-08-07 against a Unity 3D multiplayer feature, after the ADR-0130 and ADR-0131 surfaces had shipped, so it measured the widest surface available rather than the pre-wave one. Measured by searching `commands/` and `wos/unity-*.md` for each plan-time decision such a feature must close:

| Decision | Files hosting it |
| --- | --- |
| Networked authority declarations | 1 (`wos/unity-netcode-architecture.md`, ADR-0131) |
| Test assembly placement | 1 (`test-strategy`, ADR-0130) |
| GameObject hierarchy | 0 |
| Component responsibility | 0 |
| Prefab structure | 0 |
| Input model | 0 |

The only command owning scene-graph and component-responsibility planning is `godot-scene-plan`, which is engine-bound in its entirety.

Two qualifications were recorded rather than glossed, because both weaken the case and both are the kind of thing an author is tempted to leave out.

**Part of the measured gap was self-inflicted.** The render-pipeline declaration had no home because ADR-0130 deferred the mobile-rendering topic out of its own wave, not because the surface inherently lacked a place for it. Discounting that, the genuinely command-shaped residue is the scene-graph triple (hierarchy, component responsibility, prefab structure) plus the input model. That residue is still real and still has zero homes.

**The vetted MCP surface cannot apply the whole output.** An `mcp-server-vet` pass on `CoderGamester/mcp-unity` the same day (verdict SANDBOX, no arbitrary code execution verified against the files) found no tool for assembly definitions, project settings, or render-pipeline configuration, and only a read of the current pipeline to select a shader. So part of any Unity plan is human-applied today. This is within the precedent contract, since `godot-scene-plan` already produces "a design-time plan an MCP-driven editor or a human then builds against", but it lowers the automation value and is stated in the command itself rather than discovered later.

## Decision

- **G-1 D-7 closes as BUILD.** `unity-scene-plan` ships as a capability-named command. The gap survived an empirical test against the widest available surface; the merge alternative stays rejected by ADR-0069 D-4, since Godot and Unity share no vocabulary at the file level (scene tree versus GameObject hierarchy, GDScript versus C#, `.tscn` versus `.prefab` plus GUIDs).
- **G-2 Two REQUIRED declarations, or the plan is incomplete.** A 3D target declares its render pipeline plus the target graphics API per shipping platform. A networked feature declares topology, per-object ownership, sync primitive per datum, tick rate, and determinism posture. This mirrors the Godot renderer-tier gate (ADR-0117 D-9) in intent, and deliberately not in mechanism: no fenced-block parser is added here, because ADR-0119 established that a permissive reader over free prose has an unbounded failure surface, and this wave has no dogfood evidence to justify picking a form.
- **G-3 The render-pipeline reasoning is mechanism-level, not a platform slogan.** The command reasons from HDRP's enumerated platform list (which contains no iOS or Android) and its two stated requirements (compute shader support; OpenGL and OpenGL ES unsupported), and is forbidden from asserting that Unity recommends URP for mobile, because no captured page says so. `wos/unity-mobile-rendering-and-performance.md` carries the mechanism.
- **G-4 The command names what is human-applied.** Step 9 lists the steps no vetted MCP surface can currently apply, so a build does not stall silently on them.
- **G-5 An inbound route exists.** `implementation-plan` routes an engine feature with no scene plan to the matching scene-plan command before slicing. Without this the command would be a flow orphan, which is the ADR-0127 failure exactly.

## Consequences

- `count:commands` rises to 98. Four registry rows are added (spec cluster list, spec Command roles index, `wos/command-roles.md`, `COMMAND_PROMPT_STUBS.md`), one skill is generated, one eval scenario is added. This is the registry cost ADR-0130 avoided and is now paid deliberately.
- `count:wos-topics` rises by 1 (`wos/unity-mobile-rendering-and-performance.md`), `count:adrs` by 1, `count:scenarios` by 1.
- **The new topic is deliberately narrow and says so.** It covers the pipeline decision only. Numeric budgets, SRP Batcher and GPU instancing, texture compression, shader variant stripping, the Addressables lifecycle, and Adaptive Performance are absent by decision, each named in the topic and routed to `capture-references`. A reader who finds no draw-call number there is meant to find nothing, not to infer a default.
- **A third source-verification correction lands with this wave.** The research round's angle report asserted that HDRP is flatly unsupported on mobile. The page never says that; it enumerates supported platforms without iOS or Android among them and states two mechanism requirements. The precise form is stronger, because it is checkable against a specific device. That makes three of the round's Unity claims corrected during the build (the `adb logcat` tag filter in ADR-0130, the MCP issue thread in ADR-0130, and this one).
- D-7 closes. D-8 remains `[OPEN]`: the `mcp-server-vet` pass answered its safety half and its coverage half, but the dogfood half still needs a real Unity project.
- ADR-0069 D-4 remains upheld. A capability-named `unity-scene-plan` is exactly what D-4's own text permits; what it forbids is a merged `scene-plan --engine=unity`, which this ADR does not build and its structural check forbids.

## Alternatives considered

- **Widening `godot-scene-plan` with an `Engine:` axis**, mirroring how ADR-0117 added a `Dimension:` axis. Rejected on the same mechanism grounds both reuse maps reached independently and ADR-0130 recorded: 2D and 3D share GDScript and the scene tree, which is what made a dimension axis clean; Godot and Unity share neither. Forcing the axis produces a file whose name and examples promise one engine while its body means two, the exact risk ADR-0117 named for itself.
- **Closing D-7 as decided-against.** Defensible on the two qualifications above: part of the gap was self-inflicted, and the vetted MCP surface cannot apply half the output. Rejected because the scene-graph residue has zero homes even after discounting the deferral, and because "a human applies it" is the precedent contract rather than a defect.
- **Deferring another round** to build the mobile-rendering topic first and re-measure. Rejected as a decision the re-measure would not change: the scene-graph triple has no host regardless of where the pipeline declaration lands.
- **Adding a fenced-block declaration parser** like ADR-0119's. Rejected for this wave, see G-2. ADR-0119's form was earned by two reviews producing 36 findings against a line parser; adopting the conclusion without the evidence would be cargo-culting the shape.

# ADR-0131: Unity multiplayer lands Unity-scoped, as one reference topic plus two conditional blocks

- **Status**: Accepted
- **Date**: 2026-08-07
- **Tags**: unity, multiplayer, netcode, authority, capability-routed, no-new-command, reference-layer, extends-adr-0130

## Context

ADR-0130 delivered Unity 3D mobile as an adapter plus contract widenings and deferred multiplayer with its reason on the record: multiplayer has no analogue anywhere in Fhorja on either engine, confirmed by four independent greps during the 2026-08-06 research round, so it is a domain the workflow has never covered rather than a Unity-shaped gap. The maintainer chose to build it as the next wave.

The research synthesis had proposed an alternative, its Option D: extract an engine-neutral `wos/multiplayer-netcode-architecture.md` covering topology, determinism, tick rate, and ownership as concepts, with a thin Unity file cross-referencing it. Its own analysis then rejected that as "a premature abstraction with exactly one current consumer", the same shape ADR-0069 D-4 warns against, relocated from the engine axis to the netcode-doctrine axis. ADR-0130 deferred rather than rejected it, on the grounds that extraction later costs nothing cross-referencing does not already preserve.

Writing the content confronts that question with material rather than argument, and the material settles it: nearly every load-bearing statement available is framework-specific. What Netcode for GameObjects does and does not ship, the ownership API and its permission model, the RPC-versus-NetworkVariable discriminator, and the default spawn semantics are all NGO facts. The genuinely engine-neutral residue is small: authority topologies as concepts, and the observation that determinism cannot be assumed. Extracting a shared layer for that residue would produce a file too thin to load and a Unity file that still carries everything a reader needs.

Four sources were captured for this wave, and one of them changed the shape of the deliverable.

**Netcode for GameObjects ships neither client-side prediction and reconciliation nor server-side rewind.** Its own documentation says so: "While Netcode for GameObjects doesn't have a full implementation of client-side prediction and reconciliation, you can build such a system on top of the existing client-side anticipation building-blocks", and "There's no server side rewind implementation right now in Netcode for GameObjects, but you can implement your own." A team selecting NGO because it expects rollback-style netcode inherits building both. That is a plan-time forcing item, not a build-time discovery, and it is the single most decision-relevant fact captured in this wave.

Three further findings shaped the content. Unity publishes a three-way authority trade-off (server, client, action anticipation) rather than the binary a reader expects, and recommends server-authoritative by default with per-case exceptions. Ownership resolves per NetworkObject with topology-dependent semantics, and carries a documented trap where `SpawnWithOwnership` plus a local edit makes the spawning client behave as spawn authority rather than owner, silently breaking owner-specific checks. And the RPC-versus-NetworkVariable choice is decided by the late-joiner test rather than by bandwidth: state carried on an RPC leaves a client that connects afterwards with a wrong world and no error anywhere.

Separately, an `mcp-server-vet` pass run in the same session on `CoderGamester/mcp-unity` (verdict SANDBOX) established that the vetted Unity MCP surface has no tool for assembly definitions, project settings, or render-pipeline configuration, and reads the current pipeline only to pick a shader. That bears on this ADR: a Unity plan's output is partly human-applied today regardless of how the planning surface is written.

## Decision

- **E-1 Surface shape.** Unity multiplayer ships as one reference topic, `wos/unity-netcode-architecture.md`, plus two conditional blocks on existing commands: a networked-multiplayer trust-boundary lens in `security-review` (Step 3c, fires only when a networked multiplayer surface is in scope) and a networked-multiplayer budget block in `performance-budget`. **No net-new command**, consistent with ADR-0130 D-5.
- **E-2 The engine-neutral extraction stays rejected**, now on written evidence rather than on the prior-probability argument: the engine-neutral residue after writing the content is too thin to justify a file, and a second consumer still does not exist. Revisit only if a Godot or other-engine multiplayer need actually materializes.
- **E-3 Scope is Netcode for GameObjects only, and the gaps are named in the topic itself.** The framework comparison across Mirror, FishNet, Photon Fusion, and Photon Quantum, the CCU-based cost model, and anti-cheat design beyond the authority-level statements are ABSENT BY DECISION, each routed to `capture-references` before anyone writes them. A framework recommendation from model memory is the specific failure this scoping prevents.
- **E-4 No numeric threshold is stated in the multiplayer budget block.** Every row is `PROPOSED-pending-baseline`, because no captured source supplies a bandwidth, tick-rate, or latency figure for any Unity netcode framework. This follows the ADR-0117 D-9 precedent, where the Godot 3D budget carries the same rule for the same reason.
- **E-5 Determinism is a declared plan field.** A plan that depends on reproducible simulation states what supplies it, because Unity's built-in physics does not.

## Consequences

- `count:commands` does not change and no registry row is added. `count:wos-topics` rises by 1, `count:adrs` by 1, `count:scenarios` by 1.
- Two commands gain conditional blocks that are inert outside a multiplayer surface, so the cost to every non-multiplayer task is zero.
- **The determinism content rests on a community discussion thread, not Unity documentation.** No official page located in this pass addresses whether Unity physics is deterministic. The quotes are attributed to individual forum participants in both the topic and the captured reference. It is included because the consequence is a plan-level constraint and silence would read as "not a concern"; it is caveated because a forum thread is not a specification.
- The NGO prediction and rewind absence is now a forcing item in the topic's plan checklist. A plan whose acceptance depends on either states who builds it, or reopens the framework choice.
- Deferred and named rather than silently dropped, unchanged from ADR-0130: the mobile rendering and performance topic, the ecosystem and licensing topic, the ship and live-ops topic, and four engine-correctness hazards whose sources are uncaptured.
- ADR-0069 D-4 remains upheld. This wave merges nothing across engines; it adds a Unity-named topic and two capability-gated blocks inside capability-named commands.

## Alternatives considered

- **The engine-neutral doctrine layer (synthesis Option D).** Rejected, see E-2. Writing the content is what settled it: the shared residue is two concepts, and a file that thin costs more in indirection than it saves.
- **A `unity-netcode-plan` command.** Rejected on the same reuse-map logic ADR-0130 applied to `unity-scene-plan`: the netcode declarations are fields of a plan, not a plan of their own, and `implementation-plan` plus the topic host them without a new registry entry. Also, D-7 is still `[OPEN]`, so adding a second planning-shaped Unity command before the first one is settled would prejudge it.
- **Writing the framework comparison from the research round's angle report.** Rejected. That report's Unity claims already failed source verification twice in ADR-0130 (an `adb logcat` tag filter that does not exist, and a mischaracterized MCP issue thread). A six-framework comparison is exactly the content where an unverified claim is most costly and least visible.
- **Stating provisional numeric budgets** so the block has something concrete. Rejected as invention wearing a budget's clothing, in the words the block itself now uses.

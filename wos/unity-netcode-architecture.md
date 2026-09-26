---
activation: model_decision
description: Mechanism knowledge for the plan-time networked-authority decisions a Unity multiplayer feature must make (topology and authority, what Netcode for GameObjects does and does not ship, per-object ownership, RPC versus NetworkVariable state sync, and why physics determinism cannot be assumed); load when planning a Unity multiplayer feature.
---

# wos/unity-netcode-architecture

Lazy-loaded reference for planning a Unity multiplayer feature. It covers the decisions that must be made before code, because each one is expensive to reverse: who is authoritative, what the chosen framework actually ships, who may write to a given object, which sync primitive carries which data, and whether the simulation can be assumed deterministic.

Scope, stated up front so the gaps are visible rather than discovered. This topic is grounded in Netcode for GameObjects documentation and one practitioner thread on physics determinism. It does **not** contain a framework comparison across Mirror, FishNet, Photon Fusion, or Photon Quantum, a CCU cost model, or an anti-cheat design, because no source for those was captured. Route those to `capture-references` before writing any of them; a framework recommendation from model memory is exactly what this topic exists to prevent.

Multiplayer has no analogue elsewhere in Fhorja on any engine. Nothing here is restated from another topic because there is nothing to restate.

## The first decision: topology and authority

Unity's stated default is unambiguous: "A good way to think about your game architecture at first is to have your game server authoritative by default and make exceptions for reactivity when security and consistency allows it" (https://docs.unity3d.com/Packages/com.unity.netcode.gameobjects@2.7/manual/learn/dealing-with-latency.html).

Unity publishes a two-row table and a four-row one. Three of those rows, verbatim:

| Model | Unity's stated trade-off |
| --- | --- |
| Server authority | "More secure. Less reactive. No sync issues." |
| Client authority | "Less secure. More reactive. Possible sync issues." |
| Action anticipation | "More secure. Somewhat reactive. Possible visual sync issues." |

Action anticipation is the one most often missed: play the animation immediately, await server confirmation, reconcile if it disagrees. It buys most of the reactivity of client authority without moving the authority.

A fourth topology, **distributed authority**, distributes authority over NetworkObjects across clients. Unity states it is "typically not suitable for high-performance competitive games", that there is "typically no single physics simulation governing the interaction of all objects", and that "it can be easier for bad actors to cheat. The authority model gives more trust to individual clients" (https://docs.unity3d.com/Packages/com.unity.netcode.gameobjects@2.11/manual/terms-concepts/distributed-authority.html).

## What Netcode for GameObjects does not ship

This is the section that changes plans, and it is an absence rather than a feature, so it is easy to miss until it is expensive.

- **No full client-side prediction and reconciliation.** "While Netcode for GameObjects doesn't have a full implementation of client-side prediction and reconciliation, you can build such a system on top of the existing client-side anticipation building-blocks."
- **No server-side rewind (lag compensation).** "There's no server side rewind implementation right now in Netcode for GameObjects, but you can implement your own."
- What it does ship at this layer: "a basic extrapolation implementation has been provided in NetworkTransform" for estimating between server ticks and client frame updates, plus anticipation building blocks.

A team selecting Netcode for GameObjects because it expects rollback-style netcode receives neither prediction and reconciliation nor lag compensation, and inherits building both. That belongs in a recorded plan-time decision, not in a mid-build discovery. When a feature's acceptance depends on either, the plan states who is building it and at what cost, or the framework choice is reopened.

## Ownership: the per-object form of the authority decision

Authority is not only an architecture-level word; it resolves per NetworkObject, and the semantics differ by topology (https://docs.unity3d.com/Packages/com.unity.netcode.gameobjects@2.11/manual/components/core/networkobject-ownership.html).

- **Client-server:** "the server is always the authority of ownership changes. Clients cannot change ownership, the server can interact with ownership." Transfer is server-only, via `ChangeOwnership(clientId)` or `RemoveOwnership()`.
- **Distributed authority:** "the owner of a NetworkObject is always the authority for that NetworkObject." Transfer goes through permissions: `Transferable` for direct transfer, `RequestRequired` for a request flow, with `OnOwnershipPermissionsFailure` firing when a non-authoritative client attempts one.

Default spawn ownership follows the topology: "The default `NetworkObject.Spawn` method sets server-side ownership in a client-server topology. When using a distributed authority topology, this method sets the client who calls the method as the owner."

One documented trap worth planning around: using `SpawnWithOwnership` and then editing the NetworkObject locally makes the spawning client behave as the **spawn authority** rather than the owner, which breaks owner-specific checks. The failure is a check that silently passes for the wrong actor.

## State sync: RPC or NetworkVariable, decided by the late joiner

Two primitives, and the discriminator is not bandwidth (https://docs.unity3d.com/Packages/com.unity.netcode.gameobjects@2.6/manual/learn/rpcvnetvar.html).

- "Use RPCs for transient events, information only useful for a moment when it's received"
- NetworkVariables carry persistent state.

The decisive test is a client connecting mid-game: "If we sent an RPC to all clients, then all players connecting mid-game after that RPC is sent will miss that information." A NetworkVariable syncs its current value to that client; an RPC sent before it connected is simply gone.

That makes the choice a correctness question before it is an optimization one. Carrying world state (health, a door's open state, score) on an RPC produces a late joiner whose world is wrong, with no error raised anywhere.

Two secondary properties: NetworkVariables "save on bandwidth for you, making sure to only send values when the data has changed", and they are "not guaranteed to be delivered to the clients at the same time", so when several values must land together an RPC delivering them in one message is the correct choice.

## Determinism cannot be assumed

A lockstep or deterministic-rollback design built on Unity physics is unsound. The practitioner thread at https://discussions.unity.com/t/why-unity-physics-is-not-deterministic/1667389 names four independent causes:

- Floating point: "Floating-point precision issues are not specific to Unity. They stem from fundamental limitations in hardware and software architecture." (ysshetty96)
- Input ordering: "There is one other source of nondeterminism at play, and that is input ordering for any given simulation step." (DreamingImLatios)
- Entity order, in the DOTS Unity Physics package and not built-in PhysX (https://docs.unity3d.com/Packages/com.unity.physics@1.3/manual/index.html): "Entity order in chunks is fairly easy to break determinism on, and because Unity Physics reads the data in based on chunk order, the calculations are all dependent on this order." (DreamingImLatios)
- The verification burden: "you are now on the hook to verify every single step of the way." (Kurt-Dekker)

The thread's conclusion, from meredoth ("next to impossible") and ysshetty96 (run all physics on a single machine and stream the data), is that cross-platform determinism is next to impossible without centralized server-side physics simulation, which is the named workaround.

Provenance caveat, because it changes how much weight this carries: that is a community thread, not Unity documentation, and the quotes are individual participants. It is recorded because no official page in this pass addressed the question and because the consequence is a plan-level constraint. A plan that depends on determinism states which mechanism supplies it (centralized simulation, or a deterministic physics library) rather than assuming the engine does.

## What a Unity netcode plan states

A plan that omits any of these has deferred a decision rather than made one:

1. **Topology and authority model**, chosen against the authority and latency tables above, with the exceptions to server authority named individually rather than as a policy.
2. **Framework**, and explicitly whether the feature needs prediction, reconciliation, or lag compensation that the chosen framework does not ship, plus who builds it.
3. **Per-object ownership** for each networked object: who owns it at spawn, whether ownership transfers, and under which permission.
4. **Sync primitive per piece of data**, decided by the late-joiner test, not by bandwidth intuition.
5. **Determinism posture**: whether anything depends on it and what supplies it.
6. **Tick rate and its relationship to the physics timestep**, when the feature is physics-driven.

## Deliberately absent

Named so a reader does not mistake absence for coverage, each routed to `capture-references` before it is written:

- A framework comparison across Mirror, FishNet, Photon Fusion, and Photon Quantum. Only Netcode for GameObjects is grounded here.
- The CCU-based cost model for hosting and relay services.
- Anti-cheat design beyond the authority-level statements above.
- Hosting. Note the one captured fact that bears on it: Unity's own Multiplay Game Server Hosting was deprecated on 2026-04-01 and moved to Rocket Science Group, so a hosting path naming it is stale.

# ADR-0130: Unity 3D mobile ships as an adapter plus contract widenings, with no net-new command

- **Status**: Accepted
- **Date**: 2026-08-07
- **Tags**: unity, 3d, mobile, game-dev, capability-routed, no-new-command, reference-layer, adapter, extends-adr-0087, upholds-adr-0069-d4

## Context

ADR-0069 added a Godot 2D-mobile cluster and locked D-4: "Godot-first and capability-named where natural; no speculative multi-engine abstraction." ADR-0117 later delivered Godot 3D by widening seven 2D-bound command files rather than adding a cluster, after a reuse map found zero command-shaped gaps. Unity is the first request for a second engine, so it is the first real test of D-4.

An eleven-agent research round ran on 2026-08-06 (task `2026-08-07_unity-3d-cluster-research`): seven angles, two independent reuse maps, a synthesis, and an adversarial critique, over 169 sources with 71 Unity needs mapped. Its synthesis recommended a parallel Unity cluster (`unity-scene-plan` plus `unity-runtime-verify`, seven topics, ~35 bug-classes, roughly 39 first-wave artifacts). The critique returned SOUND-WITH-CAVEATS and produced three corrections that changed the outcome. All of it is preserved in that task's `RESEARCH/` directory; the decision-critical sources are captured in project-level `REFERENCES.md`.

Three findings decided the shape, and two of them contradict the round that produced them.

**The runtime-verify gap does not survive.** One reuse map rated `unity-runtime-verify` a STRONG command-shaped gap; the other killed it. The synthesis named the tiebreaker: draft the adapter and see if it fits. Drafting it settles the question. `app-runtime-verify.md` declares adapter-extensibility in three independent places, including a Step 5 instruction to "map to the nearest equivalent codes and say which adapter was used" for a non-RN stack. The counter-argument was that `godot-runtime-verify` carries a persistent `probes/` harness with no equivalent here, but reading that rule shows why the harness exists: a probe must be a self-terminating scene that drives behavior "by calling handlers directly", written "as a real scene ... not as a bare `--script`-invoked `SceneTree`", because a Godot scene is not a launchable app and has no other way to be observed. A Unity mobile build is a launchable app read from a platform log, which is `app-runtime-verify`'s exact shape. Unity's structural analogue to a probe is a Play mode test, which belongs to `test-strategy` under the partition ADR-0087 already states.

**The remaining gap was argued past its own rule.** With runtime-verify resolved, only `unity-scene-plan` remained. The critique found that `reuse-map-commands.md` conceded in its own text that `godot-scene-plan` "mechanically could be widened", which under the strict gap rule that map claimed to apply disqualifies a STRONG rating. Its verdict: the gap "survives on the merits, but the STRONG rating is argued past the map's own stated rule, not earned by it." Both building it and permanently refusing it overreach that evidence.

**The bug-class fork contradicts the library's own convention.** Both reuse maps proposed forking a Unity sibling of `godot-monetization-integrity`, overriding the source angle's contrary recommendation without engaging it. A frontmatter census settles it: 69 of 78 templates declare 2 to 5 languages. Of the 9 single-stack ones, 4 are single-stack because the mechanism IS the language (SQL migrations, TypeScript type assertions, YAML for Kubernetes, markdown for docs). Only the two Godot templates are single-stack for an engine reason, making them the exception rather than the precedent.

Two further critique findings shaped scope rather than shape. No dogfood precondition was proposed anywhere in the round (a grep for "dogfood" across all ten documents returned zero hits), against a precedent where ADR-0117 D-8 gated its POC wave and the Godot layer it built on had nine dogfood runs behind it. And the proposed first wave was roughly three times ADR-0117's entire footprint.

## Decision

Unity 3D mobile ships as an `app-runtime-verify` adapter plus contract widenings and a reference layer. The decisions (locked in the task's `DECISIONS.md`, D-1 through D-6) are:

- **D-5 Surface shape.** Deliver Unity capability as `wos/unity-*.md` reference topics, bug-class templates, and widenings of existing command contracts. **No net-new Unity command in this wave.** ADR-0069 D-4 is upheld and not reopened: this wave merges nothing, it adds Unity-named content inside capability-named commands.
- **D-4 Runtime verification.** WHERE a target stack produces a buildable, launchable application whose runtime output is read from a platform log, `app-runtime-verify` hosts it as a documented taxonomy adapter and Fhorja does not add a sibling runtime-verify command. Scoped to the mobile target; a Unity desktop or headless-server target observes differently and re-examines rather than inherits this.
- **D-3 Bug-class widening.** WHERE a bug-class mechanism applies to more than one stack, the library widens the existing template's `languages` and `file-patterns` rather than forking a stack-named sibling.
- **D-1 Platform posture** is mobile-first, recorded as declared maintainer intent and explicitly not as demand evidence.
- **D-6 Wave sizing.** A wave contains only work that is complete and independent of an open decision.
- **D-2** required the research evidence base to be preserved before any build decision, which it was.

Two decisions are deliberately left `[OPEN]` and block `task-close`:

- **D-7**: whether `unity-scene-plan` is ever built. Deferred out of this wave without being foreclosed. What settles it: one real Unity feature planned through the existing surface.
- **D-8**: the dogfood and MCP-drivability precondition. It cannot be tested without a real Unity project and a connected MCP server, so it is recorded as a blocker with a route (`mcp-server-vet`, then one dogfood task) rather than answered.

## Consequences

- `count:commands` does not change and no registry row is added, because a widening touches no command name. `count:wos-topics` rises by 2, `count:bug-templates` by 3, `count:adrs` by 1, `count:scenarios` by 1.
- Four structural checks in `evals/scripts/structural-evals.py` (scenario 129) make the load-bearing decisions machine-verified rather than prose: no engine-named Unity command exists, the adapter and its topics stay cited by both consuming commands, the store-integrity template stays widened and unforked in both directions, and every Unity topic is read-map-reachable with no dangling row and no prose copied from a Godot or RN topic. Each was negative-tested against an injected breakage before landing.
- **A naming debt is accepted rather than paid.** `godot-monetization-integrity.md` now covers Unity but keeps its Godot-prefixed filename, because ADR-0078 (immutable), `CHANGELOG.md`, and `evals/scenarios/89-godot-cluster-deepening.md` all reference it, and renaming would mean rewriting an accepted ADR. The mitigation is a scope note leading the file plus a structural check that fails if the note is removed. This is the "name promises one thing, body means another" risk ADR-0117 named, accepted knowingly and with a guard rather than left silent.
- **The platform posture contradicts ADR-0117 D-2 on identical evidence, and that is recorded rather than reconciled.** Both rounds found no source classifying mobile game demand by 2D versus 3D. ADR-0117 concluded desktop-leaning with no mobile-first default; this ADR is mobile-first. The difference is not evidence, it is that one was chosen by evidence and the other by the maintainer. Anyone comparing the two ADRs will find this stated in both places.
- Two Unity claims from the research round did not survive source verification and are corrected here: the round's angle report asserted an `adb logcat` Unity tag filter and a two-tag log split, but Unity's manual documents the bare command with no such filter; and it recorded issue #750 of `CoplayDev/unity-mcp` as closed with no visible remediation detail, while the ADR-0086 deep comment-thread read shows a collaborator stating it was addressed and explicitly declining one of the six findings.
- Deferred and recorded rather than silently dropped: the whole multiplayer surface (netcode topology, authority models, the CCU cost model, anti-cheat), the mobile rendering and performance topic, the ecosystem and licensing topic, the ship and live-ops topic, and the engine-correctness hazards whose sources are not yet captured (IL2CPP stripping and reflection, GC allocation in `Update`, domain-reload static leakage, the Addressables reference-count lifecycle). Multiplayer has no analogue anywhere in Fhorja on either engine, confirmed by four independent greps; it is a domain the workflow has never covered, not a Unity gap.
- Two absences are carried into the shipped content as absences, because filling either from memory is worse than leaving it open: Unity documents no exit-code contract for `-runTests`, so a Unity CI gate must assert on the `-testResults` file; and the captured documentation does not settle whether script logging on Android depends on a Development Build.
- The CI license-activation content rests on third-party GameCI documentation, not a Unity source. No official Unity page on CI activation was located. The topic says so at the point of use.

## Alternatives considered

- **A parallel Unity cluster** (`unity-scene-plan` plus `unity-runtime-verify`, seven topics, roughly 39 first-wave artifacts), which the research synthesis recommended. Rejected on its own evidence once the adversarial pass was applied: one of its two STRONG gaps does not survive kill-testing, the other was argued past the strict gap rule, and its first wave is close to three times ADR-0117's entire footprint while proposing no dogfood precondition where the precedent required one.
- **Engine-routed generalization**, adding an `Engine:` axis to `godot-scene-plan` and `godot-runtime-verify` the way ADR-0117 added a `Dimension:` axis. Rejected on mechanism, which both reuse maps reached independently: 2D and 3D share GDScript, the scene tree, and most of Godot's vocabulary, which is what made a dimension axis clean; Godot and Unity share essentially none of theirs. This is also the merge ADR-0069 D-4 exists to prevent.
- **An engine-neutral multiplayer doctrine layer** extracted alongside the Unity work. Deferred, not rejected. It is a shared abstraction with exactly one consumer today, which is the same speculative shape D-4 warns against; extracting it later costs nothing that cross-referencing does not already preserve.
- **No change at all.** Defensible on the demand evidence, exactly as it was for Godot 3D. Rejected because the engine-correctness hazards are real, have zero coverage anywhere in the surface, and are the class of defect an AI-written Unity project produces silently.
- **Renaming `godot-monetization-integrity.md`** to an engine-neutral name. Rejected because it requires editing an accepted ADR and a historical changelog. The debt plus a guard is the cheaper honest trade.

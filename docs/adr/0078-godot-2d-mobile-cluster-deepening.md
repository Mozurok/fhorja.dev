# ADR-0078: Godot 2D-mobile cluster deepening (reference topics plus severity-seeded bug-classes)

- **Status**: Accepted
- **Date**: 2026-07-02
- **Tags**: godot, game-dev, 2d-mobile, cluster, wos-topics, bug-classes, capability-routed, mcp-agnostic, ecosystem-adoption, additive

## Context

The Godot 2D-mobile cluster (ADR-0069) shipped two net-new commands (`godot-scene-plan`, `godot-runtime-verify`) plus four gated modes, and validated that the WOS lifecycle fits game development. It left two gaps: the cluster had no Godot reference topics (so the model planned Godot work from training defaults, drifting to Godot 3 APIs) and no Godot bug-classes (so `repo-consistency-sweep` was blind to game-specific defects).

A research round (task `2026-07-02_godot-2d-mobile-cluster-deepening`) captured seven anchors into `REFERENCES.md`, then ran a six-angle fleet (architecture, touch input, 2D rendering performance, monetization, game-feel, testing) synthesized in `EXTERNAL_RESEARCH.md` with zero cross-angle contradictions. A reuse map (`IMPACT_ANALYSIS.md`) confirmed against the repo that most of the flow is already served: no worker justified a third command, and every proposed standalone command was argued down by its own author. The genuinely net-new surface is the reference-topic layer and the bug-class library.

## Decision

Deepen the cluster additively. The decisions (locked in the task's `DECISIONS.md`, D-1 to D-5) are:

- D-1 Expand inside the WOS, no fork. A fork is revisited only if this becomes a commercial standalone product.
- D-2 Ship the recommended complete tier now: four consolidated reference topics, two severity-seeded security bug-classes, and three net-new-content modes. The per-angle bug-class families (perf, touch, feel, test) grow from dogfooding.
- D-3 Bug-classes load global and capability-scoped (the sweep applies them only on a Godot project), mapped into the existing `security` category. No new `game-godot` category; `count:bug-categories` stays 22 (mirrors ADR-0069 D-3).
- D-4 Four consolidated topics, not six: `wos/godot-2d-architecture.md`, `wos/godot-2d-mobile-rendering-performance.md`, `wos/godot-mobile-interaction-and-feel.md` (touch plus game-feel merged), `wos/godot-testing-and-ci.md`.
- D-5 Topics are reference-only and cross-linked from the existing surfaces (`performance-budget --godot-mobile`, `release-plan --godot-mobile`, `problem-framing --game-design`), not duplicated into them. Monetization stays reference-only (a bug-class and the release-plan compliance fold, not a topic or a command).

The two bug-classes are `godot-untrusted-resource-deserialization` (CWE-502, loading a `.tres`/`.res` from an untrusted source runs embedded scripts) and `godot-monetization-integrity` (CWE-602, client-side entitlement plus store-compliance cases). The three modes are `release-plan --godot-mobile` extended with the 2026 store-compliance gate, `test-strategy` Godot routing (GUT or gdUnit4 headless, complementary to the `godot-runtime-verify` press-play gate), and `godot-scene-plan` folds (save-state, mobile-touch, feedback-layer) implemented as cross-links to the new topics.

## Consequences

- `count:wos-topics` rises 28 to 32; each topic gets a WOS Minimum read map row. `count:bug-templates` rises 74 to 76; `count:bug-categories` stays 22 (both classes are `security`). `count:adrs` rises 76 to 77 with this ADR; `count:scenarios` rises 88 to 89 with scenario 89.
- No `count:commands` change: the three modes are content on existing commands, not new commands (mirrors ADR-0068). The cluster stays at two commands.
- The three edited commands (`release-plan`, `test-strategy`, `godot-scene-plan`) regenerate their skills; the four topics and two bug-classes are lazy-loaded and generate no skills.
- The bug-classes are capability-scoped: a non-Godot sweep is unchanged. The `godot-untrusted-resource-deserialization` class also gives WOS its first Godot-aware CWE-502 detector; `godot-monetization-integrity` its first CWE-602 game case.
- The cluster reuses the WOS lifecycle end to end; the deepening adds knowledge, not flow.

## Alternatives considered

- Six separate topics (one per angle). Rejected (D-4): topic sprawl against the context budget; touch and game-feel read naturally as one mobile-interaction topic.
- A monetization reference topic or command. Rejected (D-5): monetization is the most plugin-specific and fastest-churning surface; it belongs in a bug-class plus the release-plan compliance fold and `REFERENCES.md`, not a durable topic or a command contract.
- A new `game-godot` bug-class category. Rejected (D-3): it widens the category count for no routing benefit; both classes are security.
- The `godot-runtime-verify` behavioral and perf-snapshot modes (touch, feel, perf assertions). Held out: five angles showed the pull to overload an error classifier; those checks belong in bug-classes or headless scene-runner tests, not in the runtime gate.
- Shipping all per-angle bug-class families up front. Rejected (D-2): the existing bug-class library is designed to grow from applied and declined feedback; seed with the two highest-consequence security classes and dogfood the rest.

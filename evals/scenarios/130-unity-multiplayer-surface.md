# Eval scenario 130: Unity multiplayer is one Unity-scoped topic plus two conditional blocks

- **Tags**: ADR-0131, unity, multiplayer, netcode, authority, no-new-command, reference-layer, structural
- **Last reviewed**: 2026-08-07
- **Status**: active

## Goal

Validates **ADR-0131** (Unity multiplayer lands Unity-scoped, as one reference topic plus two conditional blocks): the topic exists and keeps the two findings that make it worth loading, both conditional blocks exist and reach it, the budget block states no invented number, and the engine-neutral extraction that ADR-0131 E-2 rejected does not reappear. Structural scenario, exercised by running the check function rather than by reading a model's prose.

This exercises:

- **The absent scope stays named (E-3).** `check_unity_multiplayer_surface()` fails when `wos/unity-netcode-architecture.md` loses its `Deliberately absent` section. The topic is grounded in Netcode for GameObjects only; the framework comparison, CCU cost model, and anti-cheat design are absent by decision. Without the section a reader takes NGO-only content for coverage of a six-framework landscape, which is the specific way this topic could mislead.
- **The two NGO absences survive.** The check fails when the topic loses either the client-side prediction-and-reconciliation absence or the server-rewind absence. These are the wave's sharpest captured facts and the topic's only plan-time forcing item: a team selecting NGO for rollback netcode inherits building both. An absence is the easiest content to lose in an edit, because nothing looks missing afterwards.
- **Both conditional blocks stay wired (E-1).** The check fails when `commands/security-review.md` loses its `Step 3c` multiplayer trust-boundary lens or its citation of the topic, and when `commands/performance-budget/SKILL.md` loses the `Networked multiplayer budget` block or its citation. A block whose topic nothing cites is the orphan failure ADR-0127 was written about.
- **No invented number (E-4).** The check fails when the multiplayer budget block stops marking its rows `PROPOSED-pending-baseline`, asserted against the block's own span rather than the whole file so a marker elsewhere cannot satisfy it. No captured source supplies a bandwidth, tick-rate, or latency figure for any Unity netcode framework, so a stated threshold there is invention.
- **The rejected extraction stays rejected (E-2).** The check fails when a `wos/multiplayer-*.md` or `wos/netcode-*.md` file appears. This is guarded because it is the one alternative that would look like an improvement to a later author: ADR-0131 rejected it on written evidence (the engine-neutral residue after writing the content is two concepts, and a second consumer still does not exist), and reopening it needs a superseding ADR rather than a new file.

## Setup

No live harness or model turn needed; backed by one function in `evals/scripts/structural-evals.py`, run by the `structural-evals` CI job.

- A checkout with the ADR-0131 changes applied: `wos/unity-netcode-architecture.md`, the `security-review` Step 3c lens, the `performance-budget` multiplayer block, the read-map entry, and the regenerated `.claude/skills/*/SKILL.md`.
- A scratch copy of each file a step temporarily breaks, restored at the end of the run.

## Steps

1. Run `python3 evals/scripts/structural-evals.py` and confirm `unity-multiplayer-surface` reports PASS.
2. Rename the `## Deliberately absent` heading in `wos/unity-netcode-architecture.md`. Re-run; the check MUST fail. Restore.
3. Redact the string `no server side rewind` from the topic. Re-run; the check MUST fail. Restore.
4. Rename the `**Step 3c:` heading in `commands/security-review.md`. Re-run; the check MUST fail. Restore.
5. Replace `PROPOSED-pending-baseline` inside the multiplayer budget block in `commands/performance-budget/SKILL.md`. Re-run; the check MUST fail. Restore.
6. Create an empty `wos/multiplayer-netcode-architecture.md`. Re-run; the check MUST fail on the extraction predicate. Delete.
7. Confirm the full suite exits 0 after every restore.

## Pass criteria

- `unity-multiplayer-surface` PASSES on the unmodified tree.
- Each of the five injected breakages in steps 2 to 6 produces a FAIL, and the suite returns to exit 0 only after restoring.
- `count:commands` is unchanged by this ADR, which the existing `count-markers` check already asserts.

## FAIL conditions

- The check passes while any invariant above is broken, which means it asserts nothing.
- **A step reports FAIL for the wrong reason.** Reading only the `[FAIL] <check-name>` header is not proof: per-check exception isolation renders a crashed check as a FAIL, so a check with an undefined name reports FAIL on every injected breakage while asserting nothing. Verify each step by reading the indented message and confirming it names the injected breakage, not `check raised NameError`. This false green occurred during the ADR-0130 build one day earlier and was caught by a review pass, not by the first negative test.
- An engine-neutral multiplayer topic is added without a superseding ADR reopening ADR-0131 E-2.
- A numeric bandwidth, tick-rate, or latency threshold is stated in the multiplayer budget block without a captured source or a recorded measurement behind it.

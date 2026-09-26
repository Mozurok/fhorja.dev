# Eval scenario 131: unity-scene-plan keeps its declarations, its honesty step, and its inbound route

- **Tags**: ADR-0132, unity, 3d, scene-plan, new-command, render-pipeline, flow-route, structural
- **Last reviewed**: 2026-08-07
- **Status**: active

## Goal

Validates **ADR-0132** (`unity-scene-plan` ships as a capability-named command, closing D-7): the command keeps both REQUIRED declarations, keeps the step naming what no MCP surface can apply, keeps the prohibition on a Unity mobile recommendation no captured source makes, keeps an inbound route so it is not a flow orphan, and no merged engine-axis command appears beside it. Structural scenario, run by the check function rather than by reading prose.

This exercises:

- **Both REQUIRED declarations survive (G-2).** `check_unity_scene_plan_gates()` fails when the render-pipeline declaration loses its `REQUIRED for a 3D target` marking or the authority declaration loses `REQUIRED when the feature is networked`. Without either marking a plan missing the declaration reads as complete, which is the failure the Godot renderer-tier gate was hardened twice to prevent (ADR-0118, ADR-0119).
- **The honesty step survives (G-4).** The check fails when the `human-applied` step is removed. The Unity MCP surface vetted on 2026-08-07 had no tool for assembly definitions, project settings, or render-pipeline configuration, so a plan that does not name those steps stalls a build silently.
- **The pipeline prohibition survives (G-3).** The check fails when the command loses `do NOT assert that Unity recommends URP for mobile`. Asserted as the PRESENCE of the prohibition rather than by scanning for the claim: the first version of this predicate scanned for `Unity recommends URP` and matched the command's own negation of it, which is the incidental-prose failure ADR-0119 recorded, hit again from the opposite direction.
- **The inbound route survives (G-5).** The check fails when `commands/implementation-plan.md` stops naming `unity-scene-plan`, which would make it a flow orphan and let a Unity feature be sliced before its architecture is decided. This is the ADR-0127 failure.
- **The authorized set stays bounded.** `check_unity_no_new_command()` (scenario 129) now permits exactly `unity-scene-plan.md` and fails on any other `commands/unity-*`. ADR-0130 D-5 said no net-new Unity command; ADR-0132 superseded that scope for one command on a recorded empirical test. Enumerating the authorized set rather than relaxing the glob is what keeps a second command from arriving unannounced.
- **No engine merge (ADR-0069 D-4).** The check fails when a `commands/scene-plan*` or `commands/game-scene-plan*` file appears. D-4 forbids merging engines that share no vocabulary; a capability-named sibling is what it permits, and the difference is the whole basis of ADR-0132.

## Setup

No live harness or model turn needed; backed by one function in `evals/scripts/structural-evals.py` plus the widened scenario-129 check, run by the `structural-evals` CI job.

- A checkout with the ADR-0132 changes applied: `commands/unity-scene-plan.md`, `wos/unity-mobile-rendering-and-performance.md`, the registry rows, the `implementation-plan` route, the read-map entry, and the generated skill.
- A scratch copy of each file a step temporarily breaks or moves, restored at the end.

## Steps

1. Run `python3 evals/scripts/structural-evals.py` and confirm both `unity-scene-plan-gates` and `unity-no-new-command` report PASS.
2. Create an empty `commands/unity-asset-plan.md`. Re-run; `unity-no-new-command` MUST fail naming it as unauthorized. Delete. <!-- lint:skip -->
3. Move `commands/unity-scene-plan.md` aside. Re-run; `unity-scene-plan-gates` MUST fail with an "absent" message, NOT with a raised exception. Restore.
4. Change `REQUIRED for a 3D target` to `optional`. Re-run; the check MUST fail. Restore.
5. Replace `do NOT assert that Unity recommends URP for mobile`. Re-run; the check MUST fail. Restore.
6. Remove every `unity-scene-plan` mention from `commands/implementation-plan.md`. Re-run; the check MUST fail on the flow-orphan predicate. Restore.
7. Create an empty `commands/scene-plan.md`. Re-run; the check MUST fail on the engine-merge predicate. Delete. <!-- lint:skip -->
8. Confirm the full suite exits 0 after every restore.

## Pass criteria

- Both checks PASS on the unmodified tree.
- Each of the six injected breakages in steps 2 to 7 produces a FAIL on the named check, and the suite returns to exit 0 only after restoring.
- `count:commands` is 98 and the registry check reports 0 gaps, since ADR-0132 adds a command and pays all three registry rows.

## FAIL conditions

- Any predicate passes while its invariant is broken.
- **A step reports FAIL by crashing rather than by asserting.** Step 3 exists specifically because the first version of this check called `read()` on a possibly-absent file, and `read()` raises `FileNotFoundError`; per-check exception isolation then rendered that as a FAIL whose message said the check was defective rather than naming the missing command. Every step is verified by reading the indented message. This is the third occurrence of the header-versus-message class in two days (ADR-0130's `ROOT`, this one, and the URP regex matching its own negation), which is why it is written into the corpus rather than remembered.
- A second `commands/unity-*` command is added without an ADR naming it in the authorized set.
- A merged engine-axis scene-plan command is added without a superseding ADR reopening ADR-0069 D-4.

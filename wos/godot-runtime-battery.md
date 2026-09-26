---
activation: model_decision
description: The binary preflight, the persistent probes/ harness rules, the adversarial-probe requirement, the playtest runbook contract, the capture adapter and its run directory, the BLOCKED-by-default frame capture, the static mechanical-versus-judgment split, and the eleven-code taxonomy that godot-runtime-verify classifies against. Load when running the Godot runtime gate; the command keeps the run-and-verify skeleton and this topic carries the adapter layer.
---

# Godot runtime battery

Lazy-loaded reference for `godot-runtime-verify`. It carries the binary
preflight, the persistent probe harness rules, the adversarial-probe
requirement, the playtest runbook contract and the taxonomy this gate
classifies against, so the command keeps only the run-and-verify skeleton.
Loaded when the command runs, never inlined into the command. A Godot scene is
not a launchable app read off a platform log, which is why this adapter's
observation mechanism is structurally different from the app, web and API ones.

## Environment preflight

Before the gate runs, the command MUST resolve the Godot binary: try `godot --version` on PATH first; on macOS, fall back to the app bundle binary (`/Applications/Godot.app/Contents/MacOS/Godot`). Record the resolved path in the run evidence. WHEN no binary resolves, the verdict is BLOCKED naming the missing capability (`no Godot binary resolved: not on PATH and not at the macOS bundle path`) and naming both paths that were tried, and that BLOCKED routes to `incident-triage` as a CONFIG failure so the binary is installed or its location recorded and this gate re-run. Never improvise a runner, and never hold the session waiting for someone to answer where Godot lives.

Before the first probe of a run, warm the project up with `godot --headless --import --quit` so `class_name` scripts are registered; a probe run against an unimported project reports missing identifiers that have nothing to do with the slice.

## Persistent probe harness

Probe scenes and scripts live under `probes/` in the game repo and are kept under version control, not written and deleted per slice. A probe MUST be self-terminating: call `get_tree().quit()` on PASS or FAIL, with a physics-frame backstop so a hung probe still exits. Drive behavior by calling handlers directly (for example `spawner._drop()`), never through simulated input timing or wall-clock waits. Write a probe as a real scene (`extends Node`, a companion `.tscn`, invoked headless against that scene), not as a bare `--script`-invoked `SceneTree`/`MainLoop` override: the latter does not have project autoloads registered (a compile error, `Identifier not found: <Autoload>`, with the process still exiting 0) even though the identical autoload resolves correctly for a real scene-tree node script. After an instant, non-simulated reposition (`global_position = ...` on a physics body), wait a few physics frames (empirically 3 or more) before asserting an `Area2D` overlap query, since the physics server's overlap state updates on a deferred schedule, not synchronously with the assignment.

## Adversarial probe requirement

The runtime gate for a mechanic acceptance MUST include at least one adversarial or stress probe (rapid repeated input, boundary states, spam of the core action) alongside the happy-path probe. A gate that ran only happy-path probes is incomplete evidence and MUST say so in its verdict.

## Playtest runbook (ADR-0084)

Alongside the machine-run gate, write or update `PLAYTEST_RUNBOOK.md` in the active task folder: how a human launches the scene (the run command or the press-play steps and the main scene to set), the specific things to exercise (the acceptance behaviors plus what the automated gate cannot judge: feel, difficulty, pacing, and fidelity to the reference or the `MECHANICS_SPEC.md`), and where the playtester's notes go. The runbook is the durable, repeatable counterpart to the automated gate. This gate catches crashes and missing behaviors; the human playtest catches wrong-but-running mechanics the gate passes, which is the ADR-0084 failure: the runtime gate PASSED a core mechanic that was objectively wrong, because it verifies the contract and cannot question it. An improvised one-off run instruction is not a runbook; the artifact is the point.

## Evidence capture (the run directory)

Capture the debugger output in this run rather than asking a human to paste it. Every artifact goes under the task folder in a per-slice run directory, `<task-folder>/evidence/<slice-id>/`, and every path written there is cited in the slice notes and in the report this command writes. The run directory lives in the task folder because it has to survive the session, which the session scratchpad does not.

Godot is the weakest of the <!-- count:runtime-verify-commands -->4<!-- /count --> surfaces and this section says so plainly. There is no mature Godot capture MCP to name, so the mechanism here is the CLI the preflight already resolved, and what it yields is a log rather than a scene a tool can inspect.

- The probe run's stdout and stderr, written as `probe.log` under the run directory, one file per probe scene with the probe name in the filename. Godot prints orphan-node and leak diagnostics at shutdown into the same log; the verdict reads the probe's own PASS or FAIL line and the exit code, never the absence of those diagnostics. No environment variable reliably silences them (`wos/godot-testing-and-ci.md` says why), so none is set here.
- The test-runner output when the project uses one, written beside it: gdUnit4 with `--headless --ignoreHeadlessMode`, or GUT through `gut_cmdln.gd -gexit`. The process exit code is not a valid gate on its own, so the captured output is what the verdict reads.
- The resolved binary path and the Godot version from the preflight, recorded in the report so a reader can repeat the run.

WHEN no binary resolved, the verdict is BLOCKED per the preflight above. It is never a silent PASS, and it is never a stop that waits for a human to paste a debugger log.

## Golden baseline (BLOCKED by default here)

The headless run uses a dummy display server and renders no real frame, so a screenshot is not free the way it is on the other surfaces. The documented workaround is a scripted `get_viewport().get_texture().get_image().save_png()` inside the probe scene, or a real display through a virtual framebuffer. Neither has been measured against this workflow's own Godot surface yet.

So the visual half of this gate is BLOCKED by default, with the reason `no measured Godot frame capture`, and it stays that way until one capture attempt is run and its result recorded in the task folder. Do not assert a capture capability here that nobody has named and nobody has run: an asserted capability is exactly the claim this gate exists to refuse. The mechanical half below runs regardless and is not held up by this.

Once a capture attempt succeeds, the golden-baseline rule is the same one the other surfaces carry: a screenshot with no bug-free reference to compare it against is an artifact, not a check, measured at 34 to 50 per cent median precision without one against 100 per cent with one. Until then the visual rows read `unverified: no measured Godot frame capture` and ride the playtest runbook to a human.

## Mechanical and judgment criteria (static split)

The split is declared here, per battery rule, and is never decided per run. A per-run classification would have the agent judging its own capability at the point where the verdict is decided, which is the self-assessment this workflow rules out everywhere else.

| battery rule | class | decided from |
|---|---|---|
| the binary resolved and the project imported | mechanical | the preflight output |
| runtime error classification against the taxonomy | mechanical | the captured probe log |
| the probe terminated itself rather than hanging | mechanical | the captured log and the physics-frame backstop |
| the acceptance behavior a probe asserts | mechanical | that probe's own captured PASS or FAIL line |
| the adversarial or stress probe | mechanical | that probe's captured output |
| a rendered frame: art, sorting, visual regression | judgment, BLOCKED by default | no measured capture path on this surface yet |
| feel, difficulty, pacing and fidelity to the reference | judgment | a human playing the scene, per the playtest runbook |

A mechanical row is decided here with no human in the loop, and it gates. A judgment row rides `PLAYTEST_RUNBOOK.md` to a human; it does not gate on its own, and it is never recorded as observed. WHEN the slice's acceptance behavior IS a judgment row, that criterion is `unverified` and the gate is BLOCKED with that reason, because no mechanical evidence for it exists.

## Taxonomy: Godot adapter

Tag every error or anomaly with one taxonomy code: `SCRIPT_ERROR` (a GDScript runtime error: nil method call, type mismatch, bad cast), `MISSING_NODE_OR_RESOURCE` (a node path not found or a resource that failed to load), `SIGNAL_NOT_CONNECTED` (an expected signal never fires or was never wired), `NULL_REFERENCE` (access to a freed or never-assigned node), `PHYSICS_OR_COLLISION` (a body that does not move, a collision layer/mask mismatch), `INPUT_NOT_MAPPED` (an action missing from the input map, or no touch binding on a mobile target), `PERFORMANCE_STALL` (frame drops or a hang; defer numeric budgets to `performance-budget`), `STATE_INVARIANT_VIOLATION` (an observable game-state rule broken with no thrown error and no other code fitting: a double-spend, a double-placement, an impossible state transition; exactly the class the adversarial-probe requirement exists to surface), `TRANSPARENCY_SORTING` (3D only: a transparent surface draws in the wrong order because sorting is by `Node3D` position, not per-vertex world position; it presents as art looking wrong with no thrown error), `RENDERER_TIER_MISMATCH` (3D only: a feature silently absent because the build runs a tier that drops it, for example a `RenderingDevice`-dependent effect on Compatibility, or a scene judged in the iOS simulator, which supports only Compatibility), or `CLEAN` (no runtime error and the acceptance behavior was observed).

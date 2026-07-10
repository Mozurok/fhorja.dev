---
activation: model_decision
description: Godot 4.x automated testing and CI for 2D-mobile games (GUT, gdUnit4, headless CLI runs with deterministic exit codes, scene-runner touch simulation) plus the doctrine that headless tests and the interactive press-play gate are complementary, not substitutes. Load when planning test coverage, wiring a CI test job, or reviewing QA for a Godot game.

---

# wos/godot-testing-and-ci.md

Reference for testing and QA on a Godot 4.x 2D-mobile game: which framework to run, how to run it headless from the Godot CLI in CI with a deterministic exit code and JUnit XML plus HTML reports, how a scene runner drives a real scene and simulates touch, and the recurring test defects to watch for. It also carries the one piece of doctrine no bug-class can hold: headless automated tests and the interactive press-play gate cover different ground and neither replaces the other. This is a reference to cite when planning or reviewing tests, not a decision engine and not a tutorial dump; load it, pick what applies, and move on.

## Frameworks

Two headless-capable frameworks dominate Godot 4.x, both run from the CLI, both emit JUnit XML, both exit non-zero on any failure. Pick one per project.

- GUT (Godot Unit Test): GDScript only, which matches the cluster's GDScript default; mature, simple assert API, well-documented CLI. https://github.com/bitwes/Gut
- gdUnit4: GDScript or C#, adds a scene runner for integration tests and a first-party GitHub Action; use it when the project has C# or needs the scene runner. https://github.com/godot-gdunit-labs/gdUnit4
- GodotTestDriver (Chickensoft): a driver-style input and interaction library, mainly for C# projects that want a page-object layer over nodes. https://github.com/chickensoft-games/GodotTestDriver

Do not mix two test runners in one CI job; the exit-code and report contracts differ. Choose GUT for a GDScript-default 2D-mobile project unless C# or the scene runner is a hard requirement.

## Headless CLI and CI

The CI job runs the editor with the Godot 4 `--headless` flag (no window, no GPU), runs the suite, and the merge gate reads the process exit code. https://docs.godotengine.org/en/4.4/tutorials/editor/command_line_tutorial.html

- Deterministic exit: run GUT with `-gexit` (or `-gexit_on_success`) and it returns 0 when every test passes and 1 when any test fails, so the gate is a plain exit-code check. Write reports with `-gjunit_xml_file`. https://gut.readthedocs.io/en/latest/Command-Line.html
- Warm-up import first: the first headless invocation imports assets. Run a separate warm-up import pass before the test run so asset import is not mixed into the test step and is not misread as test noise. https://medium.com/@kpicaza/ci-tested-gut-for-godot-4-fast-green-and-reliable-c56f16cde73d
- `class_name` does not resolve in a fresh headless project: `global_script_class_cache` is only populated when the editor opens the project, so a headless run on a never-opened project fails every `class_name` reference with a parse error (`Could not find type ...`). In code exercised headless, identify peers by group membership (`is_in_group`) plus duck-typing, and load Resources by path, never by `class_name`.
- `--quit-after` counts main-loop iterations, not physics frames, and the headless main loop runs far faster than the physics tick, so a `--quit-after N` run exits after only a few physics steps and returns exit 0 having observed nothing. Probes MUST self-terminate (call `get_tree().quit()` on PASS or FAIL, with a physics-frame backstop) instead of relying on `--quit-after` or elapsed wall-clock time.
- Leak-check false-positive gotcha: Godot prints orphan-node and leak diagnostics at shutdown; a naive CI parser reads those lines as failures. Set `GODOT_DISABLE_LEAK_CHECKS=1` on the CI runner so leak logs are not counted as failures, and check real orphan leaks separately (see Common test defects). https://medium.com/@kpicaza/ci-tested-gut-for-godot-4-fast-green-and-reliable-c56f16cde73d
- Reports as artifacts: emit JUnit XML plus an HTML report and publish both as CI artifacts and a test summary. The gdunit4-action wraps the whole flow (headless invoke, exit gating, report upload) if you are on gdUnit4. https://github.com/marketplace/actions/gdunit4-test-runner-action
- End-to-end CI recipe for reference: https://saltares.com/run-automated-tests-for-your-godot-game-on-ci/
- Version note: `--headless` is the Godot 4 flag. Godot 3 CI recipes predate it and use a different flag, so do not copy a Godot 3 test job verbatim; verify every flag against the 4.x CLI docs.

## Scene and touch integration tests

Beyond unit tests, an integration test drives a real running scene frame-by-frame and simulates input, so touch UI and gameplay wiring are covered deterministically without a device. gdUnit4's scene runner is the concrete tool here. https://godot-gdunit-labs.github.io/gdUnit4/latest/advanced_testing/scene_runner/actions/

- Core primitives: `simulate_frames` to advance the scene, `simulate_screen_touch_press` and `simulate_screen_touch_release` for taps, `simulate_screen_touch_drag_*` for drags and swipes, `simulate_action_*` for mapped actions, `await_signal_on` to wait on a node signal, and `set_time_factor` to speed or slow simulated time. https://godot-gdunit-labs.github.io/gdUnit4/latest/advanced_testing/scene_runner/actions/
- Always advance at least one frame with `simulate_frames` after simulated input before asserting; input is processed on the next frame, so an assert on the same frame reads stale state. https://gut.readthedocs.io/en/9.3.1/Asserts-and-Methods.html
- Signal assertions need a watch first: call `watch_signals(node)` before `assert_signal_emitted`, and for async use `await wait_for_signal` (GUT) or `await_signal_on` (gdUnit4 scene runner). https://gut.readthedocs.io/en/9.3.1/Asserts-and-Methods.html
- This layer is where the silent touch defects live that the press-play gate cannot assert precisely: a tap swallowed by an overlapping control's `mouse_filter`, a phantom click from `emulate_mouse_from_touch`, or aim sensitivity that changes per resolution can all be pinned by a scene-runner test that presses a known coordinate and asserts the result. Keep those assertions in the headless suite, not in the manual gate.

## Where automated tests stop (the press-play boundary)

Headless automated tests are the regression net that runs on every push. They do not replace the interactive press-play gate, and the reason is physical: the `--headless` runner has no GPU, so it cannot judge visual rendering, game feel, frame pacing, or real on-device touch. https://docs.godotengine.org/en/4.4/tutorials/editor/command_line_tutorial.html

- The two layers are complementary. Headless CI proves logic, signals, state transitions, and simulated-input wiring stay correct. The press-play gate proves the game looks right, feels right, holds its frame budget, and responds to a real finger on a real screen.
- The interactive press-play gate is `godot-runtime-verify`. Do not treat a green CI run as sufficient QA, and do not try to make a headless test judge feel or rendering; both are category errors that this boundary exists to prevent.
- Route the human observations from a press-play session (a shake that feels dead, a control that misses under the notch, a stutter) into `pr-feedback-ingest --playtest`, which turns playtest notes into a traceable backlog. Automated JUnit failures from the headless suite feed the same backlog through the command's generic CI-feedback handling, so both signal sources converge on one list.

## Common test defects

- Tests green despite a script error: a test can report passed even when a runtime script error was pushed during the run. Never trust the pass count alone; fail the run on any pushed error or logged script error, and assert on the error output where the framework exposes it. https://github.com/godot-gdunit-labs/gdUnit4
- Flaky async from a missing await: asserting before the awaited signal or before `simulate_frames` advances the scene produces intermittent passes. Use bounded retries to stabilize CI, but fix the timing root cause rather than papering over it. https://github.com/godot-gdunit-labs/gdUnit4
- Signal assert without a watch: `assert_signal_emitted` silently never triggers if you did not call `watch_signals(node)` first, so the assertion passes vacuously. https://gut.readthedocs.io/en/9.3.1/Asserts-and-Methods.html
- Area2D detection tested with a frozen body: `Area2D` does not emit `body_entered` for a frozen `RigidBody2D` added already overlapping the area, so the probe reads as a game bug when the game logic is correct. Test area detection with a dynamic body (set `gravity_scale = 0` so it rests in place) or by moving a body into the area; never place a frozen body pre-overlapping to test detection.
- Orphan-node leaks: nodes instantiated in a test and never freed leak, which can fail a headless run or pollute later tests. Free what you instantiate. Distinguish a real leak from the CI leak-check false positive handled by `GODOT_DISABLE_LEAK_CHECKS=1` above; the env var suppresses the shutdown log, it does not fix a genuine leak.
- GPU-dependent test under `--headless`: a test that needs actual rendered pixels, viewport capture, or shader output is meaningless or fails on the no-GPU CI runner. Move that check to the `godot-runtime-verify` press-play gate rather than forcing it into headless CI.

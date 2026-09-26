---
activation: model_decision
description: Mechanism knowledge for testing a Unity project and gating it in CI (the Edit-versus-Play-mode split, the test-assembly compile-unit requirement, the batchmode CLI, the missing exit-code contract, and the license-activation precondition); load when writing a test strategy for a Unity target.
---

# wos/unity-testing-and-ci

Lazy-loaded reference for `test-strategy` on a Unity target (ADR-0130). It documents what a Unity test tier actually is, how it runs headless, and the two preconditions with no analogue in the Godot testing layer: a compile unit per test assembly, and a license activation before any CI job can start.

Sibling of `wos/godot-testing-and-ci.md`. The dimension-neutral doctrine there (the press-play boundary: headless has no GPU, so it cannot judge rendering or feel) transfers as reasoning and is not restated here. Every concrete flag, contract, and failure mode below differs.

Scope: the test tier. Verifying a running build on a device is `app-runtime-verify` with the Unity adapter (`wos/unity-runtime-evidence.md`), a separate gate.

## Two modes, and which one can assert what

The Unity Test Framework splits tests into two modes with genuinely different reach (https://docs.unity3d.com/6000.4/Documentation/Manual/test-framework/edit-mode-vs-play-mode-tests.html).

**Edit mode.** "Edit mode tests (also known as Editor tests) only run in the Unity Editor" and run in the `EditorApplication.update` callback loop. They can reference both the `UnityEditor` and `UnityEngine` namespaces, so they see Editor tooling and runtime code alike. The hard limit: "You can't run coroutines in Edit mode tests." Anything frame-based or time-based is out of reach here.

**Play mode.** These exercise runtime application code and run either inside the Editor or in a built Player. A test marked `[UnityTest]` runs as a coroutine, which is what buys frame-skipping and time-based waits. The docs recommend the plain NUnit `[Test]` attribute unless a coroutine or a custom yield instruction is genuinely needed.

Play mode is Unity's structural analogue to the Godot `probes/` harness: a scripted way to drive runtime behavior and assert on it. That is why it belongs here and not in the runtime gate. The runtime gate reads a real run on a real device; this tier scripts behavior in a controlled environment. The two are complementary and neither substitutes for the other.

## A test is a compile unit, not a file

This is the constraint most likely to be missed, because in most stacks adding a test means adding a file.

"Unity Test Framework tests must be in a test assembly, which is any assembly that references NUnit" (https://docs.unity3d.com/6000.3/Documentation/Manual/test-framework/workflow-create-test-assembly.html). The assembly definition must reference `nunit.framework.dll`, `UnityEngine.TestRunner`, and `UnityEditor.TestRunner`, and "This combination of references is what identifies an assembly as a test assembly." Edit mode tests require the `UnityEditor.TestRunner` reference specifically; Play mode tests targeting standalone platforms need the assembly definition's Platform checkboxes configured for them.

The failure mode this creates: a test file written into an ordinary folder compiles into the wrong assembly, or into none, and simply never runs. Nothing errors. The suite reports green because the test was never collected. Any agent or human adding a first test to a Unity project creates the assembly definition or produces a test that does not exist.

Create it through the Test Runner window ("Create a new Test Assembly Folder in the active path") or Assets > Create > Testing > Test Assembly Folder.

## Running headless

The documented CLI (https://docs.unity3d.com/6000.3/Documentation/Manual/test-framework/run-tests-from-command-line.html):

```bash
-runTests -batchmode -projectPath PATH_TO_YOUR_PROJECT -testResults results.xml -testPlatform PS4
```

- `-runTests` enables test-running mode.
- `-batchmode` runs without manual input.
- `-projectPath` locates the project.
- `-testPlatform` selects the target.
- `-testResults` names the output results file.

## The exit-code absence, and why it is stated as an absence

Read on 2026-08-07, that page **carries no statement about process exit codes** and no guidance on whether one can be used to determine pass or fail. It describes `-testResults` only as a destination path, with nothing about the file's format or how to interpret it, and defers the full argument list to the command-line reference.

This is recorded as an absence rather than resolved into a rule, because the two available wrong answers are both expensive. Assuming a clean 0-or-1 contract produces a CI gate that reports green on a failed suite. Assuming no signal at all produces a gate that never fails.

The practical consequence for a Unity CI gate: **do not build the pass or fail decision on the exit code alone.** Parse the `-testResults` file and assert on its contents, and state in the strategy which signal the gate actually reads.

This is the direct inverse of the Godot contract in `wos/godot-testing-and-ci.md`, where GUT returns a documented 0 or 1 by design. A Unity CI section written by analogy to the Godot one inherits an assumption Unity does not support. It is also worth pairing with the Godot lesson already recorded in that topic: check stderr separately from the pass count, because a passing count alongside a pushed error is not a pass.

## The CI precondition with no Godot analogue: license activation

Unity requires an activated license on every machine it runs on, including ephemeral CI runners, and a CI runner has no interactive session to activate through. Without it the containers behind the common CI actions find no license and every test and build job fails immediately.

The shape of the flow, per GameCI's own activation docs (https://game.ci/docs/github/activation/): for a Personal license a human activates once in Unity Hub, and the contents of the resulting `.ulf` file become a `UNITY_LICENSE` secret next to `UNITY_EMAIL` and `UNITY_PASSWORD`; for a Pro license the job activates from a `UNITY_SERIAL` secret plus the same email and password. Unity's manual draws the same line: Unity Personal activates only through the Hub, and a headless build or test machine uses command-line activation (https://docs.unity3d.com/6000.3/Documentation/Manual/LicenseActivationMethods.html). In practice that blob lives as a repository secret rather than being regenerated per run. A separate return-license step releases the seat, which matters for Pro and Plus licenses that cap concurrent activations; Personal licenses skip it.

**Provenance caveat, stated rather than buried.** The action names and secrets come from GameCI, not Unity. Unity's own pages cover headless command-line activation and the Hub-only rule for Personal, and name no CI action. Treat the mechanism as directionally reliable and the exact action names and versions as unverified; confirm them against the tooling in use before writing them into a pipeline. Closing this properly means capturing an official source via `capture-references`.

A free, activation-free engine has nothing comparable, which is exactly why this section exists: it is the step a Unity CI strategy omits when it is written by analogy.

## What a Unity test strategy should state

- Which tier each behavior lands in: Edit mode (no coroutines, sees Editor code), Play mode (runtime, coroutines via `[UnityTest]`), or the device runtime gate.
- The test assembly each new test belongs to, and whether it already exists.
- The exact headless invocation, and **which signal the gate reads**, given that the exit-code contract is undocumented.
- Whether CI license activation is already solved in this project, treated as a precondition rather than an afterthought.
- What is deliberately not covered here and belongs to `app-runtime-verify` with the Unity adapter.

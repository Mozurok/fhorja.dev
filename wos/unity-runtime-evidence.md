---
activation: model_decision
description: Mechanism knowledge for capturing Unity runtime evidence on a mobile target (where the Editor and Player logs live per platform, how to read the Android and iOS device output, and the managed-versus-native split the taxonomy keys on); load when running the app-runtime-verify Unity adapter.
---

# wos/unity-runtime-evidence

Lazy-loaded reference for `app-runtime-verify` (ADR-0087, extended by ADR-0130). It documents how to capture the runtime evidence the gate reads for a Unity mobile target, so a run's real output can be shown rather than asserted (the ADR-0048 Layer-1 rule). Capability-routed: the commands below are the common capture path; an MCP run tool or a CI runner that produces the same logs is equally valid.

Sibling of `wos/rn-expo-runtime-evidence.md`, which serves the same role for the React Native and Expo adapter. Where the two overlap (the ADR-0048 evidence rule, the entry-path requirement, the video-frame coverage floor of ADR-0107), that topic is the source and this one does not restate it.

Scope: mobile (Android and iOS), matching the platform posture locked in the consuming task's D-1. A Unity desktop or headless-server target observes differently and is out of scope here.

## The two streams, and why the taxonomy keys on them

Unity runtime output splits into two streams with different retrieval paths, and this is the split the adapter's taxonomy exists to preserve.

The **managed stream** carries C# script output. On Android, "Android collects messages such as stack traces and logs from scripts" (https://docs.unity3d.com/Manual/android-debugging-on-an-android-device.html). A managed exception is logged here and typically does not terminate the process, so the app keeps running in a degraded state.

The **native stream** carries process-fatal failures and needs a different retrieval step: on iOS you type `bt all` into the Xcode debugger console to get native stack traces, or inspect crash reports through Xcode's Organizer (https://docs.unity3d.com/Manual/TroubleShootingIPhone.html).

The practical consequence for a verdict: a managed-only read can show a clean-looking log for a run that crashed natively, and a native-only read can miss a managed exception that silently disabled a feature. Read both before deciding.

## Where the logs live

Verbatim paths from the Unity manual (https://docs.unity3d.com/6000.5/Documentation/Manual/log-files.html):

Editor log:
- Windows: `%LOCALAPPDATA%\Unity\Editor\Editor.log`
- macOS: `~/Library/Logs/Unity/Editor.log`
- Linux: `~/.config/unity3d/Editor.log`
- Project-local, all platforms: `ProjectName/Logs/Editor.log`

Player log:
- Windows: `%USERPROFILE%\AppData\LocalLow\CompanyName\ProductName\Player.log`
- macOS: `~/Library/Logs/Company Name/Product Name/Player.log`
- Linux: `~/.config/unity3d/CompanyName/ProductName/Player.log`
- Universal Windows Platform: `%USERPROFILE%\AppData\Local\Packages\<productname>\TempState\UnityPlayer.log`

The `-logFile` argument overrides the destination.

**The asymmetry that matters here.** Android and iOS, the two platforms this adapter targets, have no path in that list. Both require platform tooling instead. A Unity mobile verdict therefore never comes from reading a log file off disk; it comes from the device capture below.

## Capture the device output (Android)

The Unity manual gives the bare command (https://docs.unity3d.com/Manual/android-debugging-on-an-android-device.html):

```bash
adb logcat
```

**No Unity-specific tag filter is documented on that page.** This is recorded as an absence, not filled in from memory: a filter expression that looks plausible and is wrong produces a quiet log and a false CLEAN. Filter on what you can justify from the run itself (the package name, a symbol from the reported symptom) and say in the report which filter was used.

The alternative first-party path is the Android Logcat package, which "implements the logcat command-line tool and displays messages from the application in a dedicated window in Unity". It captures "messages such as stack traces and logs from an Android device in the Unity Editor" and ships Screen Capture, Stacktrace Utility, Input, and Memory windows alongside it (https://docs.unity3d.com/Packages/com.unity.mobile.android-logcat@1.4/manual/index.html).

For debugging initialization code specifically, the **Wait for Managed Debugger** Android build setting attaches the debugger before the application runs.

## Capture the device output (iOS)

From the Unity manual (https://docs.unity3d.com/Manual/TroubleShootingIPhone.html):

- Device console: in Xcode, **Window > Devices and Simulators**, select the target device, then "Click Show the device console and review the latest messages."
- Debugger console: **View > Debug Area > Activate Console**.
- Native backtrace on a crash: type `bt all` in that console to get native stack traces showing where the crash occurred.
- Crash reports are inspected through Xcode's Organizer.

## Development Build versus Release Build

The captured Unity documentation does **not** state whether a Development Build is required to capture script logs on Android; the page covers the debugger-attach path and the logcat path without making that dependency explicit.

Treat this as an open evidence question rather than an assumed gate. When a run produces no managed output at all, record the build type used and flag the build-type question in the verdict instead of concluding CLEAN. Settling it needs a captured Unity source on build-type logging behavior, which `capture-references` can add to this topic.

## The Unity adapter taxonomy

`app-runtime-verify` Step 5 requires a named adapter and one code per observation. The Unity adapter reuses the shared codes where the mechanism is the same and adds one where the managed-versus-native split makes it necessary.

Reused from the shared set, with the Unity signature to look for:

| Code | Unity signature |
| --- | --- |
| `NATIVE_CRASH` | A process-fatal failure: a fatal signal in logcat, or an iOS crash whose backtrace comes from `bt all` or an Organizer crash report. Judged from the native stream, never from the managed log alone. |
| `STARTUP_CRASH` | The process dies or hangs before the first interactive frame. |
| `ANR` | Android "app not responding" or a main-thread stall. |
| `MISSING_NATIVE_MODULE` | A native plugin absent, not linked, or mismatched for the target ABI. |
| `PERMISSION_OR_CONFIG` | A runtime failure from a missing permission, player setting, or environment value. Numeric budgets belong to `performance-budget`, not here. |
| `CLEAN` | No runtime error and the acceptance behavior was observed. |

Unity-specific addition:

| Code | Unity signature |
| --- | --- |
| `MANAGED_EXCEPTION` | A C# exception or error in the managed stream that does not terminate the process. The distinguishing mark is continuation: the app is still running and the log is the only evidence the feature failed. This is the code most likely to be missed by a run that only checks whether the app is still on screen. |

**Open extension, deliberately not written.** Two further Unity-specific classes were identified during research but have no captured source yet and are therefore absent rather than guessed: a shader compile or variant-stripping failure, and an Addressables reference-count lifecycle failure (double-release or premature unload). Until each has a captured `REFERENCES.md` entry documenting its log signature, classify an observation of either kind under the nearest shared code and say so in the report. Route the gap to `capture-references`.

## What to hand to `app-runtime-verify`

- The run mechanism (device, emulator, or a run tool) and the build type.
- The real captured output from both streams, with the load-bearing lines quoted verbatim.
- Which filter was applied to `adb logcat`, when one was.
- The entry path each acceptance behavior was observed on (`cold-start`, `warm-resume`, or `in-app`), per the rule in `wos/rn-expo-runtime-evidence.md`, which this adapter inherits unchanged.

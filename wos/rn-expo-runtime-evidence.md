# React Native / Expo runtime evidence

Lazy-loaded reference for `app-runtime-verify` (ADR-0087). It documents how to
capture the runtime evidence the gate reads for a React Native / Expo target, so
a run's real output can be shown rather than asserted (the ADR-0048 Layer-1 rule).
Capability-routed: the commands below are the common capture path; an MCP run
tool or a CI runner that produces the same logs is equally valid.

Grounded in the observed rn-reference-app debugging session (the commands the
maintainer actually ran to reproduce and capture the Android Fabric
`addViewAt ... ReactEditText already has a parent` crash).

## The two log surfaces (and why both matter)

A React Native app on the New Architecture (Fabric) has two distinct runtime log
surfaces, and a crash can live in either:

- **Native log** (`adb logcat` on Android, the device console on iOS, captured
  through `simctl launch`): native
  exceptions, the Fabric `SurfaceMountingManager` mounting crashes, JNI errors,
  native-module load failures, ANRs. A native crash class does NOT appear in the
  Metro/JS console. Judging a native crash from a JS-only log is the mistake that
  hides the real signal.
- **JS console** (the Metro terminal): `console.log`, JS runtime errors,
  unhandled promise rejections, red-box errors, RN warnings, Expo CLI internals.

`app-runtime-verify` reads the surface that matches the taxonomy code: a
`NATIVE_CRASH` / `NAVIGATION_TEARDOWN` is judged from the native log; a `JS_ERROR`
from the Metro console.

## Clean build (regenerate native project, no cache)

For an Expo CNG / prebuild project (the `android/` and `ios/` folders are
generated, gitignored, and safe to regenerate). Confirm they are generated (not
hand-committed) before running a clean build.

```bash
# Android, from the app package root:
npx expo prebuild --clean -p android   # deletes and regenerates android/ from app config (clears .gradle and build/)
npx expo run:android                    # compiles the native app and installs on the connected device/emulator
```

A JS-only reload (Metro fast refresh) does NOT apply a native or module-scope
change; only a clean rebuild does. When a fix touches native config, a
config-plugin, or a module-scope call (for example `enableScreens`), the runtime
evidence MUST come from a clean rebuild, not a reload, or the run verifies the old
binary.

## Capture the JS console (Metro), with extra verbosity

```bash
EXPO_DEBUG=1 npx expo start --dev-client    # JS logs, RN warnings, Expo CLI internals
```

## Capture the native log (Android)

Scope logcat to the app process so the signal is not buried in system noise:

```bash
adb shell pidof -s <applicationId>          # e.g. com.example.app -> the pid
adb logcat --pid=<pid>                       # everything from the app process

# Or clear the buffer and filter for a crash signature while reproducing:
adb logcat -c && adb logcat | grep -iE "addViewAt|ReactEditText|SurfaceMountingManager|FATAL|AndroidRuntime"
```

Gotcha (observed): a `--pid`/`grep` filter can log nothing when the pid is stale
or the crash fires under a different process id after a reinstall. When the filter
is silent, dump the full buffer (`adb logcat -d > logcat.txt`) and search it,
rather than concluding "no crash".

Gotcha (observed): iOS Keychain items, and Expo SecureStore, which is backed by
Keychain on iOS, persist across app uninstall and reinstall by default. A "clean
install" device test is not actually clean state for anything stored in
Keychain/SecureStore unless it is explicitly cleared. The concrete fix is one of
two things: clear the specific Keychain service/account entries the app uses via
a debug-menu reset that actually targets SecureStore (not just AsyncStorage or
in-memory app state), or, for a definitive reset, remove the app via Xcode's
device management, which can still leave Keychain items behind depending on the
entitlement's `kSecAttrAccessible`/access-group scope. An uninstall alone is not
proof of clean state for Keychain-backed values.

## Capture the native log and a screenshot (iOS Simulator)

Every command form below is grounded in a captured entry, not in model memory:
"xcrun simctl command forms (Xcode 26.5, read from the tool's own help)" and
"Maestro documentation corpus (flows, takeScreenshot, device targeting)" in the
project `REFERENCES.md`. Do not substitute a remembered flag for one of them.

`simctl` accepts a device UDID or the special string `booted`, which picks a
booted device. Four steps produce the device log and the screenshot:

```bash
xcrun simctl boot <device>                        # <device> is a UDID
xcrun simctl install booted <path-to-app-bundle>  # the built .app
xcrun simctl launch --console booted <bundle-id>  # app output inline in this terminal
xcrun simctl io booted screenshot screenshot.png  # PNG of the current screen
```

To keep the log as a file instead of reading it live, `launch` takes
`--stdout=<path>` and `--stderr=<path>`; use those when the output has to be
attached as evidence. `launch` also takes `--terminate-running-process`, which
kills an already-running instance first, so the evidence comes from a fresh
launch rather than a resumed app. The clean-build rule above still holds: a
native or module-scope change needs a rebuilt bundle before `install`, or the
run verifies the old binary.

Version note carried from the capture: these forms were read from
`xcrun simctl help` on Xcode 26.5, build version 17F42. One flag in that same
help text is version-sensitive: `launch --arch` "Requires runtime version 26 or
newer."

Not captured, so deliberately not written here: a device-listing form. When you
need a specific UDID rather than `booted`, read it from a source you can see.
The captured entries carry no listing command, and inventing one would defeat
the point of grounding the rest.

## Drive the flow and take labeled screenshots (Maestro)

A Maestro flow is a YAML file: an `appId:` declaration, a `---` separator, then
a list of commands. `takeScreenshot` takes a label argument.

```yaml
appId: com.apple.MobileAddressBook
---
- launchApp
- takeScreenshot: All Contacts
```

Run it against one specific device by placing `--device <UDID>` before the
`test` subcommand:

```bash
maestro --device 5B6D77EF-2AE9-47D0-9A62-70A1ABBC5FA2 test flow.yaml
```

Two gaps the captured corpus leaves open, carried through rather than filled in
from memory: the Maestro version this syntax belongs to is [unclear in source],
and the screenshot filename pattern is [unclear in source]. The corpus says
screenshots are saved to a `.maestro` folder in the workspace
(`.maestro/screenshots` in Maestro Studio). List that directory after the run to
learn the real filenames instead of predicting them.

## Which iOS output feeds which taxonomy code

`app-runtime-verify` classifies against a fixed code set, and each iOS capture
above answers a different part of it:

- The `simctl launch` output (inline with `--console`, or the `--stdout` and
  `--stderr` files) is the iOS native log surface. `NATIVE_CRASH`,
  `NAVIGATION_TEARDOWN`, `MISSING_NATIVE_MODULE`, and `STARTUP_CRASH` are judged
  from it.
- The Metro console (the capture command above is the same on both platforms)
  stays the surface for `JS_ERROR`. An iOS native crash does not appear there,
  exactly as on Android.
- The screenshot set (`simctl io ... screenshot`, or Maestro `takeScreenshot`)
  is what supports an `observed` or `not-observed` verdict for an acceptance
  behavior that is visible on screen: a prompt that should appear, the screen
  the app lands on. It is evidence for the per-criterion verdict and never a
  substitute for the log on a crash class.
- `PERMISSION_OR_CONFIG` usually needs both surfaces: the screenshot shows the
  dialog or the empty state, the log shows the refusal behind it.
- `ANR` is Android-only. An iOS main-thread stall shows up as the launch log
  going quiet with the acceptance behavior `not-observed`; report it that way
  rather than stretching a code to fit.

## Video/screen-recording evidence (ADR-0107)

A screen recording is common evidence for a mobile bug: it shows the actual
device screen when a log alone would not (a missing prompt, a wrong landing
screen, a freeze with no error emitted). `ffmpeg` is the extraction mechanism.
Extract at scene-change points when the recording is short and the transitions
matter more than timing:

```bash
ffmpeg -i recording.mov -vf "select='gt(scene,0.3)'" -vsync vfr frames/f_%03d.png
```

Fall back to a fixed low fps when scene-change detection misses a subtle
transition (a fade, a near-static screen with a small state change):

```bash
ffmpeg -i recording.mov -vf fps=2 frames/f_%03d.png
```

**Minimum frame-coverage rule (ADR-0107).** Extracting frames is not enough;
the review has to cover a minimum set before a reported symptom is ruled in or
out: every distinct on-screen state transition, plus the frame immediately
before and immediately after each reported symptom. A sparse, arbitrary sample
(3 of 41 frames, 2 of 28 frames, the pattern observed in the rn-reference-app
session) is not sufficient coverage even when the extraction itself succeeded.

**Never dismiss a symptom without a cited frame.** A reported symptom is never
classified as an environment artifact (a "simulator-only" or "flaky"
dismissal) without citing the specific frame(s) reviewed that support that
classification. The rn-reference-app session dismissed a real security-relevant
symptom, no Face ID prompt on login after the app was backgrounded, as a
"simulator artifact" without ever checking the frame at that exact timestamp;
the frame would have shown whether the prompt actually appeared. Cite the
frame number and timestamp, not just the classification.

## Cold start vs warm resume (the entry path a verdict must name)

A launch-triggered behavior (a quick action, a notification tap, a deep link, a
widget, a universal link) can work on every warm path and fail on every cold one,
with no error in either log. On a cold start the intent arrives before the
navigator is mounted, before auth is hydrated, and before any cache is warm; on a
warm resume all three already exist. They are different code paths, so a warm
observation says nothing about the cold one.

Kill the process first, then launch from the real entry point:

```bash
# iOS Simulator: terminate, then trigger from the Home Screen (long-press the icon)
xcrun simctl terminate booted <bundle-id>
# Android: force-stop, then trigger from the launcher shortcut
adb shell am force-stop <package-name>
```

`xcrun simctl openurl` and `adb shell am start -a android.intent.action.VIEW`
deliver the URL to a process that is usually already alive, so they exercise the
warm path. They are useful for a warm-resume check and are not evidence for a
cold-start one. When the app is installed as an Expo dev client, note that the
bundle download on launch widens every mount race, so a dev-client cold start and
a production cold start can order things differently; say which one was run.

For a fallback path (the behavior is supposed to land somewhere specific and
otherwise falls back to a default screen), pick a target that is NOT the fallback
destination. A recording of a tap that lands on home cannot distinguish a dropped
intent from a correct fallback.

### Throwaway scenario harness (no device)

When several launch scenarios need to be walked and a device round trip is
expensive, drive the real exported boundary functions directly from the repo's
existing test runner: no React, no query client, no navigation container, just
the decision functions with each scenario's inputs, printing what each returns.
This reproduces a routing or decision defect in seconds and needs no simulator.
It is a diagnostic, never committed, and never a substitute for the cold-start
run: it proves what the decision layer does, not what the app does.

## What to hand to `app-runtime-verify`

- The run mechanism (device / emulator / headless / MCP run tool) and whether it
  was a clean rebuild or a JS reload.
- The entry path each observation came from (cold-start, warm-resume, or in-app).
  A launch-triggered behavior needs a cold-start observation; the gate caps a
  warm-only run at BLOCKED.
- The real captured output: the native log block around the crash (verbatim) for
  a native/navigation crash, and/or the Metro console for a JS error.
- For an iOS Simulator run: the `simctl launch` log block (verbatim) plus the
  screenshot files produced during that same run. A screenshot kept from an
  earlier run is not evidence for this one (ADR-0048).
- When a screen recording is supplied: the extracted frames covering the
  minimum-coverage set (state transitions plus each reported symptom's
  neighborhood), not the raw video alone.
- The slice's acceptance behavior (the observable outcome that means it works).

Without the real output, `app-runtime-verify` STOPS and asks for it; it never
asserts a PASS from a claimed run (ADR-0048).

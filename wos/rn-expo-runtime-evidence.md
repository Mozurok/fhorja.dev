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

- **Native log** (`adb logcat` on Android, the device console on iOS): native
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

## What to hand to `app-runtime-verify`

- The run mechanism (device / emulator / headless / MCP run tool) and whether it
  was a clean rebuild or a JS reload.
- The real captured output: the native log block around the crash (verbatim) for
  a native/navigation crash, and/or the Metro console for a JS error.
- The slice's acceptance behavior (the observable outcome that means it works).

Without the real output, `app-runtime-verify` STOPS and asks for it; it never
asserts a PASS from a claimed run (ADR-0048).

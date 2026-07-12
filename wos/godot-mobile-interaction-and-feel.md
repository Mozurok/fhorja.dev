---
activation: model_decision
description: Godot 4.x mobile touch input and 2D game-feel mechanisms (finger tracking, on-screen controls, safe area, tween/shake juice, haptics, audio latency). Load when planning or auditing the interaction and feedback layer of a 2D mobile game.
---

# wos/godot-mobile-interaction-and-feel

Two sides of the same layer: how a Godot 4.x 2D mobile game reads the player's fingers and how it feeds reactions back. Touch input and game-feel share the same nodes (a dedicated CanvasLayer, autoloads wired by signals), the same mobile constraints (battery, resolution independence, accessibility), and the same failure mode (the defects are silent, the scene runs but feels wrong or eats taps). Load this when godot-scene-plan is shaping controls or a feedback layer, when auditing why a mobile build swallows taps or feels dead, or when deciding the mouse-vs-touch emulation policy. This is a reference to cite for concrete API names and known traps, not a decision engine; the routing and the decisions stay in the commands.

## Touch input model

Track each finger by index; never assume a single touch. Both events carry an `index`: `InputEventScreenTouch` (index, position, pressed) and `InputEventScreenDrag` (index, position, relative, velocity, plus the resolution-independent `screen_relative` and `screen_velocity`). Key an active-touch dictionary by index so two thumbs do not collide. https://docs.godotengine.org/en/stable/classes/class_inputeventscreentouch.html , https://docs.godotengine.org/en/stable/classes/class_inputeventscreendrag.html

- Build gestures yourself. Pinch, swipe, and twist come from tracking two indices and their deltas, or from a vetted addon (for example GodotTouchInputManager). Do not lean on `InputEventGesture` on phones; that stream (magnify, pan) is trackpad-oriented and cannot be produced by touch or emulated with a mouse. https://github.com/Federico-Ciuffardi/GodotTouchInputManager , https://docs.godotengine.org/en/stable/classes/class_inputeventgesture.html
- Aim and camera drag with `screen_relative` and `screen_velocity`, not `relative` and `velocity`. The plain versions are scaled by the content-scale factor, so sensitivity drifts per resolution; the `screen_*` versions are in raw screen pixels and stay resolution-independent. https://docs.godotengine.org/en/stable/classes/class_inputeventscreendrag.html
- Decide the emulation policy explicitly. Leaving `emulate_mouse_from_touch` on (its project-setting default is on) fires a phantom left-click on every tap, so any action bound to left-mouse double-fires. Turn it off for a touch-only game. `emulate_touch_from_mouse` is the opposite and intended path: it lets a desktop mouse drive touch events so you can test on desktop. https://docs.godotengine.org/en/stable/tutorials/inputs/input_examples.html

## On-screen controls and safe area

- Prefer `TouchScreenButton` (a Node2D with real multitouch) over a Control `Button` (single pointer) for game controls. https://docs.godotengine.org/en/stable/classes/class_touchscreenbutton.html
- Use the Godot 4.7 built-in `VirtualJoystick` (fixed, dynamic, or following modes), and read movement through `Input.get_vector()` so one path serves touch and gamepad. On older 4.x, a well-starred community joystick fills the gap. https://godotengine.org/article/dev-snapshot-godot-4-7-dev-1/ , https://codingquests.io/blog/godot-4-7-virtual-joystick-tutorial
- Put every on-screen control in its own `CanvasLayer` above the game world, size targets for a thumb, and watch `mouse_filter`. A Control with `mouse_filter = STOP` (the default) sitting over the play area silently swallows taps meant for the game; set it to `IGNORE` on overlays that should pass touches through. https://codingquests.io/blog/godot-4-7-virtual-joystick-tutorial
- Respect the notch and gesture bar with `DisplayServer.get_display_safe_area()`, which returns a `Rect2i` in raw device pixels. Transform it through the window-to-root scale before placing UI; using the raw pixels directly drifts controls off-screen, and the rectangle still does not describe the bottom gesture bar or rounded corners, so keep a manual margin. This is Godot 4 only; the Godot 3 call was `OS.get_window_safe_area()`, so flag that name as stale if the model emits it. https://docs.godotengine.org/en/4.4/classes/class_displayserver.html , https://stevensplint.com/adapting-mobile-games-for-a-notch-in-godot/

## Feedback and juice

Build reactions as a few composable, proportional systems driven by the built-in Tween API and a decaying trauma value, not one-off hardcoded animations. Every reaction scales with event magnitude and is clamped; keep the tunables in named constants and follow the community discipline of adding more feedback than feels reasonable, then dialing it back. https://codingquests.io/blog/godot-4-game-juice-platformer

- Tween API correctly: call `create_tween()` (never `Tween.new()`, which is a Godot 3 habit that no longer wires into the scene), use one tween per replay because reusing a finished tween is undefined, reach for overshoot transitions (`TRANS_BACK`, `TRANS_ELASTIC`) for pop, and set the physics process mode for physics-driven nodes. https://docs.godotengine.org/en/stable/classes/class_tween.html
- Trauma-based screen shake: add a bump of trauma on impact, decay it every frame using `delta` (frame-rate-independent), and apply `pow(trauma, 2)` or `pow(trauma, 3)` to a shake offset sampled from `FastNoiseLite`. `FastNoiseLite` is the Godot 4 noise class; `OpenSimplexNoise` was removed after Godot 3, so flag it if it appears. https://kidscancode.org/godot_recipes/4.x/2d/screen_shake/index.html
- Hit-stop on high-impact moments: drop `Engine.time_scale` near 0 for roughly 80ms, then restore it. https://codingquests.io/blog/godot-4-game-juice-platformer
- Squash-and-stretch through a damped spring on scale, proportional to impact. https://codingquests.io/blog/godot-4-game-juice-platformer
- Vary audio so repeated cues do not machine-gun: use `AudioStreamRandomizer` (random pitch and volume offsets) or set `pitch_scale = randf_range(...)` per play. https://docs.godotengine.org/en/stable/classes/class_audiostreamrandomizer.html

## Mobile feel constraints

The same juice has to respect the device. This topic owns the haptics-amplitude and audio-latency items; the frame-rate cap for battery and thermals lives in wos/godot-2d-mobile-rendering-performance, cross-reference it rather than duplicating.

- Haptics through `Input.vibrate_handheld(duration_ms, amplitude)`. The `amplitude` argument (0.0 to 1.0, with -1 meaning the system default) is honored on Android; make it proportional to event magnitude and clamp it. The call needs the Android `VIBRATE` permission enabled in the export preset or it silently does nothing (a no-op, not an error), which is why it "works in the editor" and dies on device. Never vibrate every frame (battery drain), and expose a haptics toggle. https://docs.godotengine.org/en/stable/classes/class_input.html , https://github.com/godotengine/godot-proposals/issues/9582
- Keep audio output latency low so a hit sound lands on the frame of impact. Tune `audio/driver/output_latency` (and its web-specific counterpart) down for mobile, and for precisely-timed cues sync against `AudioServer.get_time_to_next_mix()` and `AudioServer.get_output_latency()` rather than assuming the play call is instant. https://docs.godotengine.org/en/stable/tutorials/audio/sync_with_audio.html
- Offer a reduced-motion toggle that scales or disables screen shake, flashes, and other large motion, for accessibility and photosensitivity. Treat it as expected, not optional.
- Keep `Camera2D.position_smoothing` separate from the shake offset. Smoothing lags the camera toward its target; the shake is an additive per-frame offset. Mixing them into the same value makes the smoothing fight the shake and smears both. Apply shake to `Camera2D.offset` (or a child node) while smoothing acts on `position`. https://docs.godotengine.org/en/stable/classes/class_camera2d.html

## Feel verdict checklist (D-4 gate)

The recorded human press-play verdict required before any first-playable or feature-complete claim in a Godot task (locked as D-4 in the 2026-07-09 e2e audit; enforcement wired per ADR-0089 into slice-closure, the implement-approved-slice inline-close path, and task-close). Machine-green gates do not substitute for it: the dogfood behind this rule declared first-playable on passing headless probes and the human found the game unplayable (square placeholder fighting circular physics, invisible container, invisible game-over line). The human is the measurement instrument; the recorded verdict is the Layer-1 evidence, and an unrecorded press-play claim is unverified.

Run a real press-play session (device or editor), then answer each dimension in one line. The six dimensions are Swink's manipulable areas of game feel:

- Input: do the controls respond the way the hand expects (touch targets, timing, no swallowed or phantom inputs)?
- Response: does the simulated object react with weight and immediacy (no dead frames between action and consequence)?
- Context: does the play space read correctly (bounds, thresholds, and win/lose surfaces visible; nothing load-bearing is invisible)?
- Aesthetic: do the current visuals and audio support play (placeholders are legal pre-swap, but they must not contradict the physics or hide state)?
- Metaphor: does the game's fiction match what the mechanics do (a ball that looks like a box fails this line)?
- Rules: do the rules behave as specified under normal AND rapid or abusive play (spam the core action; the false-game-over class lives here)?

Plus two cross-dimension checks:

- Content-stripped engagement test: with plot, points, music, and final art ignored, is the core interaction still engaging on its own?
- Feedback proportionality: small action, small reaction; big moment, big reaction; flag over-shake and machine-gunned cues.

Recorded verdict format (what the closure gates read), written as a `## Feel verdict` block in the slice notes or in the PLAYTEST_RUNBOOK output:

```
## Feel verdict
- Date / build: <YYYY-MM-DD> / <commit or export id>
- Tester: <human name; the verdict is human-only>
- Input / Response / Context / Aesthetic / Metaphor / Rules: <one line each: PASS or the observed problem>
- Content-stripped engagement: <one line>
- Proportionality: <one line>
- Overall: PASS | FAIL
```

A FAIL verdict routes its per-line observations to `pr-feedback-ingest --playtest` as the playtest payload; the corrective backlog and the D-5 juice budget own the fixes. A PASS verdict is cited by the closing slice as its feel evidence.

**Bounded-vs-permanent skip (ADR-0098):** the closure floors' one-line skip-reason escape exists for a genuine bounded deferral (a real human will review shortly) or a throwaway/no-runtime-surface slice, not for a session where no human is available, ever. A skip reason of that second kind does not satisfy the floor; the slice stays not-ready-to-close pending an actual human session. The 2026-07-11 genre dogfood wave found this loophole in an unattended run before it shipped a false-clean closure.

## How this cross-references

- godot-scene-plan already plans a dedicated CanvasLayer and autoloads wired by signals; a CameraShake autoload, a haptics service, and a pooled audio-feedback player are that same structure, so this topic grounds the feedback-layer and mobile-touch folds rather than adding new node kinds.
- The silent touch and feel defects here (swallowed taps, phantom clicks, per-resolution aim, reused tween, unbounded trauma, missing VIBRATE permission) are what a headless gdUnit4 scene runner can assert deterministically via `simulate_screen_touch_press/release`, `simulate_screen_touch_drag_*`, and `simulate_frames`; see wos/godot-testing-and-ci. Press-play verification catches the subjective, on-device half.

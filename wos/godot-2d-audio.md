---
activation: model_decision
description: Godot 4.x 2D mobile audio (bus layout, AudioStreamPlayer vs 2D, SFX pooling, music and crossfade, settings-to-mixer wiring, haptics, the inert-toggle trap). Load when planning or auditing the audio layer of a 2D mobile game.
---

# wos/godot-2d-audio

How a Godot 4.x 2D mobile game plays sound and how the audio layer is wired so it is real, not decorative. This topic exists because the dogfood behind ADR-0084 shipped a game with Sound and Music toggles that persisted a bool and controlled nothing, and not a single `AudioStreamPlayer` in the project: audio was named repeatedly and demoted to "polish later" prose, never a runtime node or a recorded decision. Load this when `godot-scene-plan` is shaping a feedback layer or a settings screen, when auditing why a build is silent or why a volume slider does nothing, or when deciding the ship-with-or-without-audio ruling ADR-0084 requires. This is a reference to cite for concrete API names and known traps, not a decision engine; the routing and the decisions stay in the commands.

## The forcing rule (ADR-0084)

Audio is a decision, not a default. By plan approval a Godot game task has a recorded ship-with-or-without-audio ruling in `DECISIONS.md`: either audio is a real slice (buses, players, wired settings) or shipping silent is an explicit, owned non-goal. "Polish later" prose in a scene plan or slice note does not satisfy this. The failure mode this prevents: a settings screen that advertises Sound and Music to the player while the toggles wire to nothing. If the game exposes an audio control, that control changes audio, or the control is not shipped.

A wiring-only placeholder (real `AudioStreamPlayer` nodes, correct bus assignment, `stream` deliberately left unassigned) satisfies this rule and is distinct from a content placeholder (actual authored audio bytes). When no safe binary-authoring path exists in the session (no engine, no audio tool, an LLM-only text-writing session), prefer the wiring-only form over hand-authoring binary audio: an unverifiable hand-authored `.wav` risks silently shipping a corrupt file, which is a worse outcome than an honestly-unassigned stream. The rule requires the audio system to be real, not that placeholder content exists.

Exception: when audio timing, not just presence, is itself the mechanic under test (a rhythm game, a timing-critical feedback loop), a wiring-only placeholder is insufficient, `AudioStreamPlayer.get_playback_position()` has no meaningful value with no stream assigned, so the mechanic cannot be exercised at all. In that case, real, verifiable audio content is required even under the no-safe-binary-authoring-path condition; a minimal verifiable-generation technique (a stdlib-generated tone or click track, read back and import-validated) is the fallback when no external audio tool exists.

## Bus layout

Route every sound through the audio bus layout, never player-by-player volume math. Create a `Master` bus with `Music` and `SFX` child buses so a settings screen can set two group volumes and mute independently. https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html

- Set volume in decibels, and convert a 0..1 slider value with `db = linear_to_db(value)` (and back with `db_to_linear`); a linear slider written straight to `volume_db` sounds wrong because loudness is logarithmic. Mute by setting the bus's mute flag, not by dropping volume to a magic floor. https://docs.godotengine.org/en/stable/classes/class_audioserver.html
- Address buses by name through `AudioServer.get_bus_index("SFX")` then `AudioServer.set_bus_volume_db(idx, db)` / `set_bus_mute(idx, bool)`; storing the index is brittle if the layout changes. https://docs.godotengine.org/en/stable/classes/class_audioserver.html
- Assign each player's `bus` property (`"Music"` or `"SFX"`) so the group controls actually reach it; a player left on `Master` bypasses the SFX slider.

## Players: which node

- `AudioStreamPlayer` (non-positional) for music, UI clicks, and global SFX. This is the default for a 2D mobile game where most sound is not spatialized. https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer.html
- `AudioStreamPlayer2D` only when you want position-based panning and attenuation from a node's 2D position (an off-screen enemy quieter than a near one). It is heavier and usually unnecessary for a portrait idle or arcade game; do not reach for it by default. https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer2d.html
- Import short SFX as WAV and loop-heavy music as OGG Vorbis; MP3 works but WAV avoids decode latency on one-shots. Set the import loop mode on music, off on one-shot SFX, in the Import dock. https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_audio_samples.html

## SFX pooling (the concurrent-sound trap)

A single `AudioStreamPlayer` cuts its own tail off when retriggered: fire the same hit sound twice in one frame and the first is silenced. For any SFX that can overlap (rapid hits, coins, particles), use a small pool of players and play the next free one. Keep the pool bounded (for example 8 to 16 voices) and drop or steal the oldest when saturated, rather than spawning unbounded players that stutter under load. This is a known 2D-game pattern, not an engine feature; a shared `SfxPool` autoload wired by signal is the usual home (plan it in `godot-scene-plan`'s feedback-layer step, see `wos/godot-mobile-interaction-and-feel.md`). https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer.html

## Music: layering and crossfade

- Loop music by importing with loop on and calling `play()`; use the stream's loop points rather than restarting on `finished`, which introduces a gap. https://docs.godotengine.org/en/stable/tutorials/audio/index.html
- Crossfade between tracks with a short tween on two players' `volume_db` (fade one down while the other comes up) rather than a hard cut; a hard `stop()` then `play()` is audible.
- `AudioStreamInteractive` and `AudioStreamPlaylist` (Godot 4.3+) handle multi-clip transitions and sequenced playlists in-engine when the music has states (menu vs combat); reach for them only when a two-player crossfade is genuinely insufficient. https://docs.godotengine.org/en/stable/classes/class_audiostreaminteractive.html

## Settings-to-mixer wiring (close the inert-toggle gap)

The settings screen is where the forcing rule usually breaks. Each control MUST reach the mixer, and the state MUST survive a restart:

- On a volume change: `AudioServer.set_bus_volume_db(idx, linear_to_db(value))`; on a mute toggle: `AudioServer.set_bus_mute(idx, on)`.
- Persist the preference (the linear 0..1 value or the mute bool) and re-apply it on boot, before the first sound plays, or the mixer resets to full every launch.
- A "Sound" toggle that only writes a bool to a save file and never touches `AudioServer` is the shipped defect; the wiring above is the fix.

## Haptics and audio latency (mobile)

- Haptics are feedback, not audio, but they live in the same layer: `Input.vibrate_handheld(duration_ms)` on Android and iOS. It is coarse (no waveform) and is a no-op on desktop; gate it behind the same settings "Vibration" toggle and the same persist-and-reapply rule. https://docs.godotengine.org/en/stable/classes/class_input.html
- Mobile output latency is real; keep one-shot SFX as small decoded WAV and preload streams so the first play does not hitch. Do not chase exact millisecond budgets here; defer device-specific numbers to `performance-budget` in its Godot mobile profile and mark them `[to confirm]`.

## Handoff to the commands

`godot-scene-plan` plans the audio autoload (a bus-aware `SfxPool` or `AudioManager`) and its signal wiring in the feedback-layer step, and records the ship-audio ruling. `godot-runtime-verify` can only confirm a sound node ran without error; whether the mix feels right is a human playtest note (route it to `pr-feedback-ingest --playtest`). Version-specific class availability (for example `AudioStreamInteractive`) is Godot 4.3+; flag an emitted API against the project's actual version rather than assuming.

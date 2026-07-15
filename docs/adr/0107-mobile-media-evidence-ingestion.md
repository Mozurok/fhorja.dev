# ADR-0107: Mobile media-evidence ingestion, a minimum frame-coverage floor for app-runtime-verify

- **Status**: Accepted
- **Date**: 2026-07-15
- **Tags**: app-runtime-verify, media-ingestion, mobile-runtime-target, react-native, expo, extends-adr-0089, mirrors-adr-0091, dogfood-driven

## Context

Throughout the 2026-07-14/15 rn-reference-app React Native/Expo Face ID session, the maintainer sent screen-recording videos as bug evidence, over and over, because that was the fastest way to show a runtime symptom on a device. No workflow primitive existed for ingesting a screen recording as mobile runtime evidence, so the model improvised: it ran ffmpeg to extract frames, then reviewed a sparse and inconsistent sample of them (3 of 41 frames in one pass, 2 of 28 in another). On one of those passes it dismissed a real, security-relevant symptom (no Face ID prompt on login after the app was backgrounded) as a "simulator artifact" without ever checking the frame at that exact timestamp.

The workflow already closed this exact failure shape for one domain. ADR-0089's D-3 makes media ingestion user-supplied-first and documents the ffmpeg frame-extraction contract for `image-to-spec --gameplay`, but that mechanism is scoped to the Godot 2D-mobile cluster; it says nothing about how many frames a review must cover, and it does not reach `app-runtime-verify`, the mobile/app runtime gate ADR-0087 built for exactly this stack. The result: the one command whose job is to gate mobile runtime behavior on real evidence had no rule at all for the single richest evidence format the maintainer actually supplies, video.

## Decision

Per the locked D-1 rule that every ADR-generalization fix gets a new ADR number cross-referencing the source ADR (the same move ADR-0091 made generalizing ADR-0089's D-4 feel-verdict mechanism off Godot), this ADR generalizes ADR-0089's D-3 media-ingestion pattern onto `app-runtime-verify`, with a minimum-frame-coverage rule scoped to the reported symptom:

WHEN the user supplies a screen recording as bug evidence for a mobile/app runtime slice, `app-runtime-verify` SHALL extract and review a minimum frame set, every distinct on-screen state transition, plus the frame immediately before and immediately after each reported symptom, before ruling a symptom in or out, and SHALL NOT classify an observed symptom as an environment artifact (a "simulator-only" or "flaky" dismissal) without citing the specific frame(s) reviewed that support that classification.

**Enforcement home.** The rule lands as a new Step in `commands/app-runtime-verify.md`, placed immediately after the step that reads the captured native/Metro output, since video evidence is reviewed alongside the log output, not instead of it. The capture mechanism (ffmpeg, extraction points, the frame-coverage floor, and the no-dismissal-without-a-cited-frame rule) is documented in `wos/rn-expo-runtime-evidence.md`, the same reference topic ADR-0087 already established for RN/Expo evidence capture.

**Scope.** This ADR governs the mobile/app domain only. ADR-0089's D-3 stays exactly as written and Godot-scoped; it is not edited. The `image-to-spec --gameplay` ffmpeg contract ADR-0089 D-3 already documents is a separate, unrelated consumer (spec derivation, not runtime gating) and is unaffected by this ADR.

## Consequences

### Positive

- The specific failure that motivated this ADR is structurally closed: a reported symptom can no longer be waved away as a simulator artifact without a cited frame proving the classification, closing the exact gap that let a real Face ID security bypass go unflagged.
- Evidence-backed video review replaces sparse, improvised sampling; the coverage rule (state transitions plus reported-symptom neighborhoods) gives a repeatable floor instead of an ad hoc frame count chosen mid-session.
- `app-runtime-verify` gains a second evidence format (video, alongside the native log and Metro console) with the same "shown, not asserted" discipline ADR-0048 already requires of the other two.

### Negative

- Frame extraction and review adds time to the verification pass. Mitigated by scoping the required review to state transitions and the neighborhood of each reported symptom rather than every extracted frame, keeping the floor cheap on a short recording and proportional on a long one.

### Neutral

- No new command. The rule folds into `app-runtime-verify` and its companion reference topic, following the ADR-0084/0085/0091 fold-first precedent.
- ADR-0089 is generalized by this ADR, not patched; its D-3 text and Godot-cluster scope are unchanged.

## Alternatives considered

### Alternative 1: patch ADR-0089's D-3 in place to cover mobile as well as Godot

- Would have kept the media-ingestion mechanism in one document.
- Rejected: ADR immutability is a feature, and this is the same reasoning ADR-0091 used generalizing ADR-0089's D-4 gate off Godot rather than editing it. A cross-domain mechanism merits its own searchable record.

### Alternative 2: require reviewing every extracted frame, not a minimum coverage set

- Simpler rule, no judgment about what counts as a state transition.
- Rejected: reviewing every frame on a multi-minute recording adds ceremony with no proportional signal gain over covering every state transition plus each reported symptom's neighborhood; the rn-reference-app session's 41-frame and 28-frame extractions would have made a review-everything rule expensive without changing the outcome.

### Alternative 3: leave frame-sampling depth to the model's judgment, name only ffmpeg as the mechanism

- Status quo; no new rule to write or enforce.
- Rejected: this is the exact condition that produced the 3-of-41 and 2-of-28 sparse samples and the uncited artifact dismissal; a stated mechanism with no coverage floor is not a gate.

## References

- The rn-reference-app Face ID session (2026-07-14/15): sparse, inconsistent frame sampling (3 of 41, 2 of 28) and an uncited "simulator artifact" dismissal of a real symptom (no Face ID prompt after backgrounding).
- ADR-0089 (the D-3 user-supplied-first media-ingestion pattern this ADR generalizes off Godot); ADR-0091 (the generalize-not-patch precedent and its enforcement-home shape, reused here); ADR-0087 (`app-runtime-verify`, the gate this rule extends, and `wos/rn-expo-runtime-evidence.md`, the reference topic it lands in); ADR-0106 (the sibling ADR making `app-runtime-verify` a mandatory closure floor, landed by a partner slice in the same wave); ADR-0048 (a passing deterministic gate is Layer-1 evidence; the inverse, an unshown or uncited claim, is what this ADR closes for video).
- `commands/app-runtime-verify.md` (the new Step); `wos/rn-expo-runtime-evidence.md` (the Video/screen-recording evidence subsection); `evals/scenarios/108-mobile-media-evidence-ingestion.md` (the eval scenario pinning the coverage floor and the no-dismissal-without-a-cited-frame rule).

## Notes

Found in the same session, and by the same shape of gap, ADR-0106 closed one command over: a real capability existed and a real evidence format was in constant use, and nothing required using it correctly. The fix is the same move again: a stated, checkable floor, not an added checkbox with no teeth.

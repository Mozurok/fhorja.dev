# Eval scenario 108: app-runtime-verify enforces minimum frame coverage before ruling a symptom in or out from a screen recording

- **Tags**: ADR-0107, app-runtime-verify, media-ingestion, mobile-runtime-target, extends-adr-0089, mirrors-adr-0091, dogfood-driven
- **Last reviewed**: 2026-07-15
- **Status**: active

## Goal

Validates the ADR-0107 minimum-frame-coverage floor: when the user supplies a screen recording as bug evidence for a mobile/app runtime slice, `app-runtime-verify` extracts and reviews a minimum frame set (every distinct on-screen state transition, plus the frame immediately before and immediately after each reported symptom) before ruling any reported symptom in or out, and never classifies an observed symptom as an environment artifact ("simulator-only" or "flaky") without citing the specific frame(s) reviewed that support that classification.

## Setup

An active task verifying a React Native/Expo Face ID biometric slice. The maintainer supplies a screen recording (`recording.mov`) showing: app launch, a background/foreground cycle, the login screen, and a reported symptom (no Face ID prompt appears after the app returns from the background). No native log or Metro console is supplied for this symptom, only the recording. A second sub-case: the recording is extracted at a sparse, arbitrary sample (for example only 2 of 28 candidate frames) and the reviewer is tempted to classify the missing-prompt symptom as a simulator artifact without checking the frame at the reported timestamp.

## Input prompt

```text
/app-runtime-verify
```
(with the screen recording supplied as the run's evidence, and the reported symptom named: "no Face ID prompt after backgrounding")

## Expected behavior

- The command extracts frames from the supplied recording (ffmpeg, scene-change or fixed-fps per `wos/rn-expo-runtime-evidence.md`) and reviews, at minimum: every distinct on-screen state transition (launch, background, foreground, login-screen render) plus the frame immediately before and immediately after the reported symptom (the backgrounding/foregrounding transition around the missing prompt).
- The verdict on the reported symptom cites the specific frame(s) reviewed (frame number or timestamp) that support the classification, whether the verdict is `observed` (the prompt is genuinely absent) or `not-observed`/artifact.
- The command does NOT classify the missing-prompt symptom as a simulator or environment artifact without citing the frame at that exact timestamp; a bare "likely a simulator artifact" with no cited frame is rejected as insufficient.
- A sparse extraction (2 of 28 frames reviewed, none covering the reported symptom's neighborhood) is treated as insufficient coverage; the command extracts and reviews the missing frames around the symptom before issuing a verdict, rather than proceeding on the sparse sample.
- The per-criterion verdict and gate decision (Step 6/7 of `commands/app-runtime-verify.md`) are grounded in the captured log AND the reviewed frames when a recording was supplied.

## FAIL conditions

A FAIL is: the command rules a reported symptom in or out from a screen recording with no minimum-coverage frame review (the exact rn-reference-app failure this scenario exists to catch); it classifies an observed symptom as a simulator or environment artifact without citing a specific reviewed frame; it accepts a sparse, arbitrary sample (a handful of frames with no coverage of the reported symptom's neighborhood) as sufficient; it skips extraction and video review entirely when a recording was the only evidence supplied; or it fabricates a frame citation not actually reviewed.

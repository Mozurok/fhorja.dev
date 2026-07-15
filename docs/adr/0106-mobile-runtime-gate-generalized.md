# ADR-0106: Mobile runtime-gate generalized as a mandatory closure floor (RN/Expo tag plus signature, three homes)

- **Status**: Accepted
- **Date**: 2026-07-15
- **Tags**: app-runtime-verify, runtime-gate, closure-enforcement, slice-closure, task-close, implement-approved-slice, mobile-runtime-target, dogfood-driven, extends-adr-0087, mirrors-adr-0085, refines-adr-0098

## Context

The 2026-07-14/15 rn-reference-app React Native/Expo Face ID session shipped a fully broken biometric flow (no Face ID prompt, the wrong landing screen, a security bypass, and a white-screen freeze) past every internal checkpoint, because every slice was declared done on `tsc --noEmit` and grep alone. `app-runtime-verify` (ADR-0087) already exists as a capability-routed, MCP-agnostic mobile runtime gate; it was simply never required to fire. Nothing in the closure path made it mandatory, unlike ADR-0085's Godot floor, which forces `godot-runtime-verify` at the same three homes for a runtime-observable Godot slice.

This is the same failure class ADR-0085 closed for Godot, recurring in the mobile/app domain `app-runtime-verify` was built to cover. A stated capability with no enforcement point is not a gate.

## Decision

Generalize the ADR-0085 enforcement mechanism onto `app-runtime-verify`, reusing its detection-plus-block-and-route shape:

1. **Trigger: tag primary, signature a heuristic backstop.** A task or slice carrying an explicit `mobile-runtime-target` tag triggers the floor. Absent the tag, a heuristic signature also triggers it: a `package.json` listing an `expo` or `react-native` dependency together with a generated `android/` or `ios/` folder. The tag is primary; the signature exists only to catch an untagged task the same way ADR-0091's D-1 heuristic backstop catches an untagged user-facing deliverable. Neither trigger fires on a project with no RN/Expo dependency and no generated native folder.

2. **Three enforcement homes, mandatory PASS-or-skip.** At `slice-closure`, the `implement-approved-slice` inline-close path, and `task-close`, a slice or task matching the trigger is not `ready to close` (respectively does not close inline, is not archived) unless a real `app-runtime-verify` PASS is cited (in the slice notes, a runtime-verify record, or the task record) OR an explicit one-line skip reason is recorded. IF neither is present THEN the closing command SHALL classify the slice or task not-ready-to-close and route to `app-runtime-verify`. The inline-close home is load-bearing, the same finding ADR-0085 made for Godot: most LOW/MEDIUM slices close there, not at `slice-closure`, so an inline-only bypass would reopen the exact gap this ADR closes.

3. **Bounded-vs-permanent skip (ADR-0098 rule reused verbatim).** A skip reason stating no device or emulator is ever available in this environment does not by itself satisfy the floor; the slice or task stays not-ready-to-close pending a session where a run is possible. A genuine bounded deferral (a specific later checkpoint, a real device session the human will run shortly, or a slice with no runtime-observable behavior at all) still satisfies the floor at the same low ceremony.

4. **Godot stand-down.** WHILE the Godot task signature is present (per ADR-0091 D-5: a `project.godot` file, a `.gd` codebase, or `GODOT_SCENE_PLAN.md` in the task folder), this floor stands down in favor of the existing Godot-specific floors (ADR-0085's runtime-gate floor, ADR-0089's D-4 feel-verdict floor). The two families never both fire on the same task; the signature check routes exclusively, the same precedence rule ADR-0091 already uses.

**Enforcement homes.** The floor plus one Definition-of-done recap line land in `commands/slice-closure.md`, `commands/implement-approved-slice.md` (the inline-close path), and `commands/task-close.md`, immediately adjacent to each file's ADR-0091 experience-verdict floor, the same three homes ADR-0085 and ADR-0091 already use.

## Consequences

### Positive

- The exact failure this audit found is now structurally closed: a mobile slice with runtime-observable behavior cannot close on `tsc --noEmit` and grep alone, mirroring the protection ADR-0085 already gives Godot and ADR-0091 gives user-facing content generally.
- `app-runtime-verify` (ADR-0087) goes from an available-but-optional capability to a mandatory Layer-1 evidence gate at closure, closing the gap named in its own ADR ("it is opt-in per slice with an explicit-skip escape").
- The tag-primary, signature-backstop detection and the bounded-vs-permanent skip rule are both reused verbatim from ADR-0091/ADR-0098 rather than re-invented, so the closure commands gain one more conditional floor with a shape reviewers already recognize.

### Negative

- A 4th conditional floor stacks onto three already-dense closure commands (commit-evidence, Godot runtime-gate, Godot feel-verdict, experience-verdict, entry-path-probe, eval-threshold, and now this one). Mitigated by matching the existing floors' terseness exactly and by the cheap tag-or-signature-plus-skip escape, which keeps a non-mobile task entirely untouched.
- The heuristic signature (`expo`/`react-native` dependency plus a generated native folder) can miss an unusual monorepo layout or false-fire on a template repo with no real mobile work; the explicit tag remains the reliable primary trigger for exactly this reason.

### Neutral

- No new command. The gate is folded into three existing lifecycle commands, following the ADR-0084/0085/0091 fold-first precedent.
- ADR-0087 is generalized by this ADR, not patched; its capability-routed, MCP-agnostic contract is unchanged, only its adoption at closure becomes mandatory.

## Alternatives considered

### Alternative 1: patch ADR-0087 in place to add the closure requirement

- Would have kept the enforcement mechanism in one document.
- Rejected: ADR immutability is a feature, and this is the same reasoning ADR-0085 used when it enforced ADR-0084 rather than editing it, and ADR-0091 used when it generalized ADR-0089 rather than editing it. A cross-command enforcement contract merits its own searchable record.

### Alternative 2: enforce only at slice-closure and task-close, skip the inline-close path

- Smaller surface, no `implement-approved-slice` edit.
- Rejected: ADR-0085 already established that most LOW/MEDIUM slices close inline, not at `slice-closure`; skipping that home would reopen the exact bypass this ADR exists to close, the identical mistake Alternative 1 of ADR-0085 rejected for the same reason.

### Alternative 3: signature-only detection, no explicit tag

- Simpler, no new tag to populate at plan time.
- Rejected: a signature-only trigger cannot distinguish an RN/Expo repo doing pure JS-logic work with no runtime-observable UI change from one shipping a real native-surface change; the explicit `mobile-runtime-target` tag lets a task or slice declare intent precisely, with the signature only as a backstop for the untagged case, mirroring ADR-0091 D-1's own reasoning for its tagging predicate.

## References

- The rn-reference-app Face ID session (2026-07-14/15): a fully broken biometric flow shipped past `tsc --noEmit` and grep with no runtime evidence ever cited.
- ADR-0087 (`app-runtime-verify`, the capability this ADR makes mandatory at closure); ADR-0085 (the Godot runtime-gate enforcement mechanism this ADR clones: signature detection, three-home enforcement, block-and-route); ADR-0091 (the tag-primary/signature-backstop trigger shape and the Godot stand-down precedence this ADR reuses); ADR-0098 (the bounded-vs-permanent skip rule reused verbatim); ADR-0048 (a passing deterministic gate satisfies Layer-1 evidence; the inverse, an unverified claim, is what this ADR closes).
- `commands/slice-closure.md`, `commands/implement-approved-slice.md`, `commands/task-close.md` (the three enforcement homes); `commands/app-runtime-verify.md` (the gate this floor requires).
- `evals/scenarios/107-mobile-runtime-gate-generalized.md` (the eval scenario pinning the trigger, the block-and-route behavior, and the Godot stand-down).

## Notes

Found by the same failure shape ADR-0085 and ADR-0091 both name: a real capability existed (`app-runtime-verify`), and nothing at closure required using it. The fix is the same move both times: fold a mandatory floor into the three homes where slices and tasks actually close, not into a checkpoint command that never blocks anything.

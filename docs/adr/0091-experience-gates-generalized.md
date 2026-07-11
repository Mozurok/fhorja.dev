# ADR-0091: Experience gates generalized off Godot (tagging predicate, verdict gate, entry-path probe)

- **Status**: Accepted
- **Date**: 2026-07-10
- **Tags**: experience-gate, entry-path-probe, tagging-predicate, closure-enforcement, slice-closure, task-close, implement-approved-slice, dogfood-driven, extends-adr-0084, extends-adr-0085, extends-adr-0089

## Context

The 2026-07-08 to 2026-07-10 fhorja-connector dogfood shipped four machine-authored session packs (the paid product's core user-facing content) with no human validation of even one, and shipped the session surface as MCP prompts whose real entry path (a chat user invoking a session) was never exercised once before scaling times four. The launch was held (D-V8 of the `2026-07-10_fhorja-vertical-v1-build` task). Every machine gate along the way was green: lint passed, the deploy succeeded, the tools were live-verified reachable. None of that evidence spoke to whether a session actually felt right to a person, or whether a real user could reach it the way a real user would.

The workflow already has this exact failure class closed for one domain. ADR-0089's D-4 feel-verdict gate makes a recorded human press-play verdict required Layer-1 evidence before a Godot first-playable or feature-complete claim closes, enforced at three closure homes (slice-closure, the implement-approved-slice inline-close path, task-close), with machine-green gates explicitly barred from substituting for it. That gate exists because a Godot dogfood hit the identical shape of failure one domain earlier: every automated check passed, and the first human press-play found the game unplayable. The fhorja-connector dogfood is the same failure recurring outside Godot: a domain with no equivalent gate shipped unvalidated user-facing content and an unexercised user-facing surface.

This ADR generalizes the two ADR-0089 mechanisms, the human-verdict requirement and the entry-path check, off the Godot-specific implementation so any task shipping user-facing content or a new user-facing surface carries the same floor, while leaving the Godot-specific floors (ADR-0085, ADR-0089 D-4) as the domain's own enforcement path.

## Decision

Four parts, locked as D-1 through D-5 in `projects/bmazurok__my-work-tasks/active/2026-07-10_fhorja-connector-dogfood-punchlist/DECISIONS.md`, keyed here as (a) through (d):

**(a) Tagging predicate (D-1).** WHEN `implementation-plan` or `task-init` records a deliverable that is user-facing product content or a new user-facing surface, the plan and the `## Requested deliverables` ledger SHALL tag the row `user-facing-content` or `new-user-facing-surface`. The closure floors SHALL key off the declared tag. IF a slice's deliverable text plainly indicates user-facing content and no tag is present THEN the closing floor SHALL treat the slice as tagged and flag the missing tag (a heuristic backstop, mirroring how the fhorja-connector session packs escaped an untagged ledger).

**(b) Experience-verdict gate (F-1).** WHEN a slice or task whose deliverable carries either tag reaches closure, closure SHALL require a recorded human experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` cited in the slice notes or task record) OR an explicit one-line skip reason. Machine-green gates (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict. Build one, validate with the human, then replicate: replication of an unvalidated sample is the failure this gate exists to stop.

**(c) Entry-path probe (F-2).** WHEN a slice ships a new user-facing surface, acceptance SHALL include one exercised run through the user's real entry path (the way an end user actually reaches it, not the API underneath) before the surface is replicated or scaled.

**(d) Godot stand-down (D-5).** WHILE the Godot task signature is present (a `project.godot` file, a `.gd` codebase, or `GODOT_SCENE_PLAN.md` in the task folder) the generalized gates SHALL stand down in favor of the Godot-specific floors (the ADR-0085 runtime gate, the ADR-0089 D-4 feel-verdict). The generalized gates and the Godot floors are never both live on the same task: the signature check routes exclusively.

**Enforcement homes.** The floors plus one Definition-of-done echo land in `commands/slice-closure.md`, `commands/implement-approved-slice.md` (the inline-close path), and `commands/task-close.md`, the same three homes ADR-0085 and ADR-0089 D-4 already use, and reuse their block-and-route idiom. Binding scope per D-6 of the punch-list decisions is these three closure and acceptance homes only; delivery commands (`release-plan`, `pr-package`, `delivery-asset`) are excluded from this wave until a dogfood shows that gap.

## Consequences

### Positive

- The failure that motivated this ADR is structurally closed outside Godot: user-facing content and new user-facing surfaces cannot close on machine-green evidence alone, mirroring the protection ADR-0089 already gives Godot.
- One shared tagging and verdict mechanism serves every non-Godot domain instead of a bespoke gate per product surface, so the next dogfood in a new domain inherits the floor for free.
- The Godot stand-down keeps the two gate families from double-firing or contradicting each other on a Godot task; the signature check is the same heuristic `test-strategy` and ADR-0085 already use, so no new detection code is introduced.

### Negative

- Three core lifecycle commands used by every task gain another conditional floor on top of the ADR-0084/0085/0089 checks already there; an over-broad tagging predicate would false-block work with no real user-facing surface. Mitigated by the explicit tag plus the narrow heuristic backstop, and by the cheap explicit-skip escape.
- The tagging duty adds a small amount of ceremony to `implementation-plan` and `task-init` (one more ledger column to populate); existing active tasks are unaffected until their ledgers carry the tags, so the floor has no retroactive bite on in-flight work.
- Delivery commands are deliberately left uncovered this wave (D-6); a task that tags and verdict-passes at closure but then re-scales at delivery without a fresh entry-path probe is a known, accepted gap until a dogfood surfaces it.

### Neutral

- No new command. The gate is folded into three existing lifecycle commands, following the ADR-0084/0085/0089 fold-first precedent.
- ADR-0084, ADR-0085, and ADR-0089 are generalized by this ADR, never patched; their Godot-specific text and enforcement stay exactly as written, gated by the D-5 stand-down.

## Alternatives considered

### Alternative 1: patch ADR-0089's D-4 gate to cover non-Godot domains in place

- Would have kept the mechanism in one document instead of two.
- Rejected: ADR immutability is a feature, and ADR-0089's D-4 is explicitly Godot-scoped (Swink's six dimensions, press-play semantics) in a way that does not translate cleanly to a chat-session product. A cross-domain enforcement contract merits its own searchable record, the same reasoning ADR-0085 used when it enforced ADR-0084 rather than editing it.

### Alternative 2: no tagging predicate, fire the gate on every slice closure

- Simpler trigger, no ledger column to add.
- Rejected: most slices in this workflow are internal (docs, scripts, ADRs, non-user-facing refactors) and carry no user-facing surface at all; an untagged blanket gate would add ceremony to the common case the workflow otherwise keeps cheap. The tagging predicate keeps the floor scoped to the deliverables it exists to protect.

### Alternative 3: bind the entry-path probe (F-2) at delivery commands as well as closure

- Would close the gap this wave leaves in `release-plan`, `pr-package`, and `delivery-asset`.
- Deferred, not rejected: D-6 of the punch-list decisions narrows binding scope to the three closure and acceptance homes for this wave, since the fhorja-connector dogfood evidence names closure and acceptance as the load-bearing gap. Delivery-command binding is explicit future work, revisited when a dogfood shows the closure-only scope is insufficient.

## References

- Task `projects/bmazurok__my-work-tasks/active/2026-07-10_fhorja-connector-dogfood-punchlist/`: `DECISIONS.md` (D-1 through D-6, EARS), `IMPACT_ANALYSIS.md` (F-1 experience-verdict gate off Godot, F-2 entry-path acceptance probe).
- ADR-0089 (the D-4 feel-verdict gate this ADR generalizes, and the three-home enforcement idiom it reuses); ADR-0085 (the block-and-route closure-gate precedent, and the Godot-signature detection heuristic reused verbatim in the D-5 stand-down); ADR-0084 (the fold-first no-new-command precedent this wave follows).
- `commands/slice-closure.md`, `commands/implement-approved-slice.md`, `commands/task-close.md` (the three enforcement homes, landed by a sibling slice in this wave); `commands/implementation-plan.md`, `commands/task-init.md` (the tagging duty, landed by a sibling slice).
- `evals/scenarios/103-*.md` (the eval scenario pinning the fire-and-stand-down behavior across the tagged and Godot-signature cases, landed by a sibling slice).

## Notes

Found by the same maintainer who ran the fhorja-connector v1.0 launch dogfood and held it at D-V8. The single most important design fact is the parallel to ADR-0085's own discovery: a stated rule with no enforcement point is not a gate, and the enforcement has to live at the homes where slices actually close, not only at the macro checkpoints that never block anything.

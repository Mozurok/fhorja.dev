# ADR-0119: the Godot declaration is one canonical fenced block, read fail-closed

- **Status**: Accepted
- **Date**: 2026-07-26
- **Tags**: godot, 3d, renderer-tier, artifact-contract, closure-floor, structural-check, fail-closed, supersedes-adr-0118-form

## Context

ADR-0118 made the renderer-tier declaration a machine-readable line in the produced `GODOT_SCENE_PLAN` and enforced it at two points. The form it chose was a body line (`Dimension: 3D`, `Renderer tier: Forward+`), and the floor stood down when no dimension line was found, so the 24 pre-existing artifacts would not all fail at once.

Both halves of that turned out to be wrong, and the evidence is unusually direct because it came from two independent reviews of the shipped code rather than from reasoning about it.

**The line form could not be read reliably.** A body line has many near misses: a bullet, emphasis markers, an indent, a heading, a table cell, a lowercase value, trailing text after the value. A first review found the parser missed the bulleted and emphasized forms that real artifacts in the tree actually use. The fix widened the parser to tolerate them. A second review of that fix found six new defects in it, verified by running the parser over eight forms: `Renderer tier: Mobile, chosen for the low-end Android target.` and `Renderer tier: **Forward+**` each graded `block`, so plans following the written contract were rejected; `Dimension: 3d`, `### Dimension: 3D`, and `| Dimension | 3D |` each graded `stand-down`, so the gate silently disabled itself on a lowercase typo, a heading, or a table row.

The asymmetry is the finding. A mistyped tier key failed SAFE (block). A mistyped dimension key failed OPEN (stand-down). The dangerous direction was the unguarded one.

**The stand-down had no discriminator.** ADR-0118 read an absent dimension as backward compatibility. It carried no vintage test, so it applied permanently: a model that planned a 3D scene and skipped the declaration produced a plan the floor treated exactly like a 2015 legacy artifact. The backstop could not block the case it was built for. That was already recorded as a supersede before this ADR (D-8 of the task), which narrowed the stand-down in wording without ever naming a mechanism that could tell the two cases apart.

Two rounds of widening the parser produced 30 findings between them, and the round written specifically to fix the first round introduced six. The pattern is not carelessness in a particular edit. Every tolerated form is one the author imagined, and every missed form is a silent hole, so a permissive reader over free prose has an unbounded and invisible failure surface.

## Decision

The declaration moves into one fenced block with a fixed info string, and the gate treats anything it cannot parse as a BLOCK.

- **The form.** `godot-scene-plan` Step 7 requires exactly one fenced block with the info string `wos-godot-declaration`, holding `Dimension:` reading exactly `2D` or `3D`, plus `Renderer tier:` naming exactly `Forward+`, `Mobile`, or `Compatibility` WHERE the dimension is `3D`. Nothing else goes inside the fence. The reason for the tier choice goes in prose OUTSIDE it, which is what stops the contract and the parser from contradicting each other; ADR-0118's Step 7a instructed the author to put the reason on the declaration line and its own parser then rejected exactly that.
- **Fail-closed.** Absent, duplicated, empty, and malformed are one case: no declaration, which blocks. A near miss is not a partial pass. This reverses ADR-0118's stand-down default.
- **The waiver is the only escape and it is a human act.** A one-line `tier-declaration waiver: <plan> <reason>` in the task's `TASK_STATE.md` lets a resumed pre-form task close. No vintage is inferred and no date is read. This supplies the discriminator ADR-0118 needed and never had: it is written by a person or it does not exist.
- **The waiver covers a missing block only.** A block that is present but malformed blocks regardless of any waiver. A plan that declared badly has declared.
- **2D pays the declaration, not the tier.** The block is required in both dimensions, and in 2D the tier entry must be absent. A cheaper 2D path would reintroduce the two-class discriminator this ADR removes.

## What ADR-0118 keeps

ADR-0118 is Accepted and immutable, and most of it survives. Superseded here: its D-3 body-line form, and its stand-down default (already narrowed by the task's D-8, now replaced outright). Carried forward unchanged: two enforcement points with the self-review as the deliberately weaker first one; the floor as the home, with `godot-runtime-verify` and a task-folder-reading structural check both rejected on evidence; the three per-command variants; the fixture-based protection with a decoy in the negative test; and the recorded inequality of the two enforcement points.

## Consequences

- `count:adrs` rises by one. `count:commands` does not change.
- **The blast radius inverts.** ADR-0118's risk was a floor that never fired. This one's is a floor that fires on every Godot task. The waiver is the pressure valve, and it is deterministically tested rather than asserted in prose: the fixture unit is now a DIRECTORY holding a `GODOT_SCENE_PLAN.md` and, where the case needs one, a `TASK_STATE.md` carrying the waiver line.
- Every Godot task including 2D now pays one fenced block. Accepted rather than mitigated; `godot-scene-plan` emits it, so the cost is a block in a file the command already writes.
- The fixture set is rebuilt from eight files into one directory per case, carrying no count in prose so it cannot drift. Six directories are the exact near-miss forms verified failing in the shipped line parser, three of which were silent stand-downs, and four more were added after an independent review found defects the first set could not see (an indented fence, an over-indented one, an extra key inside the fence, and a 2D block carrying a tier). They are stronger than the single decoy because they were derived from observed failures rather than imagined ones.
- **The check now iterates the fixture DIRECTORY, not an expectation dictionary.** The superseded version iterated the dict, so a fixture nobody listed could be added, look present, and assert nothing. Under fail-closed that is worse, because the things nobody lists are negatives.
- The check suite gained per-check exception isolation in the same wave. Without it one raising check aborted the whole run and every later check was never run: verified by injecting a raise into the first check, which produced zero reported checks and a traceback. That is not part of this decision, but this ADR's protection is worthless without it, so it is recorded here as a dependency.
- A future form change still means editing three places together: `godot-scene-plan`, the floor, and `_tier_gate_verdict`. Unchanged from ADR-0118 and still on the record.
- **The gap this does not close, stated because a green suite would otherwise imply it is closed:** nothing verifies that a real `godot-scene-plan` run EMITS the block. The fixtures prove the parser reads the form; the distance between "the gate would catch it" and "the generator produces it" is exactly where the original ADR-0118 defect lived.

## Alternatives considered

- **A bare line matched exactly, with fail-closed.** The obvious minimum, and rejected on the near-miss count: seven distinct near misses each need detection to produce a fixable error message, which is the permissive parser again with the sign flipped. A fence has one near miss, and it is "not there".
- **Keeping the tolerant parser and widening it further.** Rejected on the record of two rounds: 30 findings, and the fix round added six. The premise, not the execution, is what generated them.
- **Reverting ADR-0118 entirely and reopening the follow-up.** Rejected because the rest of it is sound. What was broken is the reading of the declaration, not the architecture of enforcement.
- **A frontmatter field.** Rejected for the reason ADR-0118 already recorded: no `GODOT_SCENE_PLAN` in the tree has frontmatter. A fence is ordinary body content and needs no new file-level structure.
- **A cheaper 2D path** that skips the declaration. Rejected because it reintroduces the two-class problem: the floor would again have to infer which class a plan belongs to, which is the exact inference that failed.

## References

- [ADR-0117](./0117-godot-3d-dimension-routed-surface.md): D-9 states that a 3D scene plan without a declared tier is incomplete. Unchanged by this ADR, which changes how the declaration is written and read, not whether it is required.
- [ADR-0118](./0118-godot-tier-declaration-and-enforcement.md): superseded on its declaration form and its stand-down default only. `## What ADR-0118 keeps` above enumerates what carries forward.

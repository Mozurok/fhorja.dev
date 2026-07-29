# ADR-0118: the renderer-tier declaration is a machine-readable line, enforced at two points

- **Status**: Accepted; its declaration FORM and its absent-dimension stand-down are Superseded by [ADR-0119](./0119-godot-declaration-canonical-form.md). The two enforcement points, the rejected homes, the three per-command variants, and the recorded inequality of the two points all remain in force.
- **Date**: 2026-07-26
- **Tags**: godot, 3d, renderer-tier, artifact-contract, closure-floor, structural-check, extends-adr-0117

## Context

ADR-0117 D-9 states that a Godot 3D scene plan without a declared renderer tier is incomplete. The build that landed it (commit cc01157) made `godot-scene-plan` say so, and a structural check asserted that the command's contract text carried the requirement. A `review-hard` pass on that same diff found the gap: the check protected the CONTRACT TEXT and nothing read the PRODUCED artifact. A `GODOT_SCENE_PLAN.md` targeting 3D with no tier declared shipped past every gate.

Closing that gap turned out to need two things the original decision did not describe, and one of them only became visible by looking at real artifacts.

**The form.** Step 7a asked for the tier in prose. A reuse probe over the 24 produced `GODOT_SCENE_PLAN*.md` artifacts in the tree found that their section headings mirror the command's step names and numbers, but no contract requires that: the convention is emergent. Worse, two of six sampled artifacts mention "renderer" zero times. A gate keying on that pattern would repeat, in a new place, the exact defect `review-hard` had just found: an assertion that passes by accident of the current text.

**The home.** Four candidates were assessed and one was eliminated on evidence rather than preference. `evals/scripts/structural-evals.py` cannot host an artifact gate at all, because that harness never reads a task folder (zero references to `projects/` or `active/`). `godot-runtime-verify`, proposed by the review as the natural home, references `GODOT_SCENE_PLAN.md` zero times and its contract is reading run output, not a plan. That left the existing closure-floor pattern in `wos/platform-runtime-floors.md`, already carried as three per-command variants and already loaded by the three commands that would consume it.

**The backward-compatibility trap.** None of the 24 existing artifacts carries a dimension line, because the form did not exist. A floor reading an absent dimension as non-compliance would fail all 24 at once, across nine dogfood projects, the moment it landed.

## Decision

The tier declaration becomes a machine-readable line in the produced artifact, enforced at two points, protected by a fixture-based check. The decisions (locked in the task's `DECISIONS.md`, D-1 to D-5) are:

- **D-3 The form.** A `GODOT_SCENE_PLAN` carries `Dimension: 2D` or `Dimension: 3D` on its own line, and WHERE the dimension is 3D it also carries `Renderer tier:` naming exactly one of `Forward+`, `Mobile`, or `Compatibility`. Prose stating either does not satisfy the requirement; the line does.
- **D-1 The gate reads a required form, never an emergent convention.** The assertion is anchored to a line, not to a substring or a heading pattern.
- **D-2 Two enforcement points, both blocking.** A self-review step (`godot-scene-plan` Step 8a) reads back the plan before emitting it, and a closure floor in `wos/platform-runtime-floors.md` carries three per-command variants consumed by `implement-approved-slice`, `slice-closure`, and `task-close`.
- **The floor keys on the declared dimension, never on the artifact's presence.** `GODOT_SCENE_PLAN.md` IS the Godot signature, so a presence-keyed trigger would fire on every Godot task including 2D. Two stand-down cases are stated before the variants: an absent `Dimension:` line, and a declared `2D`.
- **D-4 The protection is a path-parameterized fixture check.** `check_godot_tier_artifact_gate(root=None)` runs the floor's logic against eight fixtures, following the `check_skill_load_budget(root=...)` precedent. Its negative test carries a decoy that would pass a weaker assertion. A companion `check_godot_tier_floor_variants` asserts the floor has its three variants and all three consumers cite it.
- **D-5 This ADR records it**, rather than leaving the form as an enforcement detail under ADR-0117 D-9, because a required artifact form outlives the task whose `DECISIONS.md` records it.

The gate's logic lives in exactly one function (`_tier_gate_verdict`), whose docstring names the floor it mirrors, so the two cannot drift without someone editing both.

## Consequences

- `count:adrs` rises by one. `count:commands` does not change: no command is added, only four are edited.
- **The two enforcement points are not equally strong, and this asymmetry is deliberate rather than accidental.** The floor is code and is tested. The self-review is an instruction to a model, and no assertion can prove a model obeyed it; a test can only assert that the instruction exists and is worded as a requirement. `godot-scene-plan` Step 8a says this about itself, and the floor's `task-close` variant repeats it, so a reader of either finds the limitation without having to infer it. A green suite therefore means one of the two points is protected, not both.
- **Zero of the 24 existing artifacts are affected.** Verified by scanning all 24: none carries a `Dimension:` line, so all 24 fall into the floor's stand-down case.
- The eight fixtures are AUTHORED, not observed. No real 3D `GODOT_SCENE_PLAN.md` exists anywhere in the tree, so the fixtures encode the author's reading of the form. The decoy fixture is partial compensation, not closure, and the fixture directory's README says so.
- The check's registry entry cites a decision (`D-2`) rather than a scenario number, following the existing `("tier-routing-closure", "D-7", ...)` precedent. No eval-scenario number is consumed.
- A future artifact form change (a different key name, a frontmatter move) means editing the form in `godot-scene-plan`, the floor, and `_tier_gate_verdict` together. Three places, listed here so the coupling is on the record.

## Alternatives considered

- **A fourth structural check over the real corpus.** Rejected on evidence, not preference: `evals/scripts/structural-evals.py` never reads a task folder, so it cannot see a produced artifact at all. This eliminated the option that otherwise looked like the obvious extension of the ADR-0117 protection pattern, and it is why the check reads fixtures instead.
- **`godot-runtime-verify` as the home.** Rejected on a reference count of zero: it names `GODOT_SCENE_PLAN.md` nowhere today, and its contract is reading a run's output rather than a plan. Choosing it would create a dependency rather than extend one.
- **The self-review alone.** Rejected because a command checking its own output fails exactly when the model that wrote the output was already confused. It is kept as the earlier of two points, never as the only one.
- **Keying on the emergent heading convention** (`## N. Renderer tier`), which costs zero new contract surface. Rejected because the convention is unspecified and already unreliable: two of six sampled artifacts mention "renderer" zero times.
- **A frontmatter field** instead of a body line. Rejected as the opposite extreme: most robust to parse, but no existing artifact has frontmatter, so it introduces new structure against the entire 24-artifact precedent.
- **A manual eval scenario as the only protection.** Rejected because it runs at release time, not in CI, and a gate whose protection never runs decays silently.

# ADR-0021: Evaluator-optimizer via self-critique-and-revise

- **Status**: Accepted
- **Date**: 2026-05-18
- **Tags**: evaluator-optimizer, locked-rubric, draft-revision, distinct-from-review-hard, plan-mode-proposed

## Context

Anthropic's "Building Effective Agents" post (Dec 2024) names five canonical agent patterns: prompt chaining, routing, parallelization, orchestrator-workers, and evaluator-optimizer. The WOS adopted prompt chaining (via the Handoff `Paste this next` contract; ADR-0002) and routing (via `what-next`, `command-router` predecessor, plus the `## Command roles` index) as load-bearing patterns. Parallelization and orchestrator-workers stayed implicit (sub-agent orchestration is the topic of slice 11). Evaluator-optimizer was not represented in the command catalog.

`review-hard` is the existing critique command. It surfaces meaningful engineering risks before slice closure or PR prep and recommends the smallest safe next step. But it explicitly does NOT produce a revised artifact: the user takes the critique and re-runs the upstream authoring command (`implementation-plan`, slice authoring, `pr-package`) to incorporate the feedback. Three failure modes the absence of an evaluator-optimizer command creates:

1. **Critique-without-revision is slow**. After review-hard on a draft IMPLEMENTATION_PLAN.md, the user often re-runs `implementation-plan` to fold in the feedback. Two-turn turnaround when one would suffice if the model could critique AND revise in a single pass.
2. **Self-critique loop is implicit, not contractual**. A model can self-critique its own work in conversation, but the WOS does not have a command that names this pattern and locks the rubric. Without an explicit contract, the pattern drifts (some runs do it, some don't; the rubric varies).
3. **Three high-value draft artifacts deserve a dedicated optimizer**. IMPLEMENTATION_PLAN.md (vague exit criteria; missing dependency graph), SLICES/*.md (scope creep; vague Handoff), and PR_PACKAGE.md (diff-vs-claim mismatch; scope leak) have recurring failure modes that a locked per-artifact-type rubric can mechanically catch.

The evaluator-optimizer pattern at the WOS layer keeps the discipline visible (one command; PROPOSED-by-default; user reviews both critique and revision) and the rubric falsifiable (locked at slice 10 authoring; future changes require slice history + ADR notes update).

## Decision

The WOS introduces a new command `commands/self-critique-and-revise.md`:

1. **Three artifact types in scope, locked at slice 10 authoring**: `IMPLEMENTATION_PLAN.md`, `SLICES/<NN>-*.md`, `PR_PACKAGE.md`. Other artifacts (commands, TASK_STATE.md, DECISIONS.md) are out of scope; the command emits `NO_OP_TRACE` with routing to the right tool.
2. **Locked per-artifact-type rubrics**: 7 criteria per type, each verdict `PASS | FAIL | WEAK`. Rubrics live in the command body and in this ADR's References section. Changes require updating both AND the slice history.
3. **Output contract** (in addition to the standard output layout):
   - `## Critique`: numbered list per rubric criterion with verdict + reasoning.
   - `## Revised draft`: full content of the revised artifact (preserves PASS content verbatim; revises only FAIL / WEAK items that do not need user judgment).
   - `## Diff summary`: one paragraph mapping each change to the criterion that triggered it.
   - `## Not applied`: bulleted recommendations the critique surfaced but the revision did NOT incorporate because they need user judgment.
4. **Plan mode default**: PROPOSED-by-default per ADR-0001. The user reviews both the critique and the revision before APPLIED. Agent mode allows direct APPLIED for trusted runs.
5. **Distinct from siblings** (documented in the command body and in the slice 10 notes):
   - `review-hard` judges; this command judges AND revises.
   - `direction-adjust` records a D-N entry; does not revise the artifact.
   - `post-review-pivot` reacts to external feedback; this command is self-critique.
   - `state-reconcile` repairs drift across artifacts; this command revises ONE draft artifact at a time.
6. **No artifact-type expansion without an ADR addendum**. If a future need surfaces (e.g., self-critique on TEST_STRATEGY.md), it requires a new locked rubric and an ADR note OR a new ADR superseding this one.

## Consequences

### Positive

- **Iteration cycle shortens by one turn**. Critique + revision in a single pass replaces critique-then-rerun-authoring. Measurable cost reduction per artifact draft.
- **Self-critique becomes contractual**. The rubric is locked; runs are consistent; reviewers know what to expect.
- **Three high-value artifacts gain a dedicated quality bar**. Plan + slice + PR package are the artifacts that most often ship to humans (planning approval, slice review, PR review). A locked rubric catches the recurring failure modes mechanically.
- **The evaluator-optimizer pattern is named in the WOS**. New contributors who read the "Building Effective Agents" post and look for the pattern in the workflow find it explicitly.

### Negative

- **Rubric can misread an ambiguous artifact**. Mitigation: PROPOSED-by-default; user reviews critique AND revision; "Not applied" section defers judgment-driven items to the user.
- **One more command to learn**. The WOS surface grows from 36 to 37. Mitigation: the distinctness table is in the command body; the routing decision (review-hard vs. self-critique-and-revise vs. direction-adjust) is mechanical.
- **Lossy revision if FAIL items need user judgment**. Mitigation: the rule "revise only items that don't need user judgment; defer the rest to Not applied" is explicit in operating rules. Conservative revision is better than over-eager rewriting.

### Neutral

- The locked rubric pattern is reused from slice 07 (LLM-as-judge; ADR-0019). Both are evaluator-shaped commands with locked wrappers. The reuse is intentional; future rubric-based commands can follow the same shape.
- Command file is ~5k tokens (above the 4k cluster of typical commands). Token-budget seeded at 4400 with 1.2x headroom. Within normal range; no special handling needed.

## Alternatives considered

### Alternative 1: extend `review-hard` to optionally produce a revised draft

- Add a `--revise` flag to review-hard; same command produces critique OR critique + revision based on flag.
- **Rejected**: conflates two different intents. review-hard is for engineering risks across multiple artifacts (code, plan, decisions); self-critique-and-revise is artifact-specific with a locked rubric. The command roles index would have to explain "review-hard with flag" vs "review-hard without flag", which is harder than two distinct commands.

### Alternative 2: separate command per artifact type (`revise-plan`, `revise-slice`, `revise-pr-package`)

- Three commands, one per artifact type; each with its own rubric.
- **Rejected**: triples the catalog growth without proportional value. The rubric per type is small (~7 criteria); a single command with type detection is reviewable. Three commands would also duplicate the operating-rules boilerplate three times.

### Alternative 3: auto-apply revisions (skip PROPOSED-by-default)

- Revisions land in the artifact directly; user reads after.
- **Rejected**: violates ADR-0001 PROPOSED-by-default. Lossy revisions need user review; the diff between original and revised must be visible before commit.

### Alternative 4: critique-only (no revision); rely on user to re-run upstream

- Keep the pattern manual; just add a "rubric-based review" command without the revision step.
- **Rejected**: the whole point is to shorten the iteration cycle. Critique-only is what `review-hard` already does (broader scope).

### Alternative 5: expand to all artifact types (TASK_STATE.md, DECISIONS.md, commands/*.md)

- One command can revise any artifact via type detection and a rubric per type.
- **Rejected for this slice**: the three load-bearing draft artifacts (plan, slice, PR package) are the highest-leverage start. TASK_STATE.md has its own commands (`sync-task-state`, `state-reconcile`, `compact-task-memory`); DECISIONS.md is immutable by convention; commands/*.md are governed by lint and shared blocks. Future expansion is possible via an ADR addendum.

## References

- `commands/self-critique-and-revise.md` (the canonical command; locked rubrics live in the body as part of operating rules).
- `commands/review-hard.md` (sibling; judge-only; the distinction the new command makes explicit).
- `commands/direction-adjust.md` (sibling; D-N entry on internal realization; not artifact-level).
- `commands/post-review-pivot.md` (sibling; external-feedback-driven; not self-critique).
- `commands/state-reconcile.md` (sibling; multi-artifact drift repair; not single-artifact revision).
- ADR-0001 (PROPOSED-by-default; the contract this command honors).
- ADR-0002 (Paste-this-next contract; the Handoff format this command emits).
- ADR-0012 (context budget; names the layers this command operates on).
- ADR-0019 (LLM-as-judge; the locked-rubric pattern this command reuses).
- Anthropic, "Building Effective Agents" (Dec 2024): the evaluator-optimizer pattern; one of five canonical agent patterns.

## Notes

The locked rubrics (IMPLEMENTATION_PLAN.md: 7 criteria; SLICES/*.md: 7 criteria; PR_PACKAGE.md: 7 criteria) are duplicated in the command body for operational reference. Changes require updating both AND the slice 10 history.

The "WEAK" verdict (in addition to PASS/FAIL) is a deliberate choice over the binary used in ADR-0019's LLM-as-judge. Self-revision benefits from a middle tier: "partially met; can be improved without user input" maps to WEAK, while truly broken items get FAIL. This gives the command more granular signal for the revision step.

Future evolution possibilities (out of scope for this slice):
- Add TEST_STRATEGY.md as a fourth artifact type if a need surfaces.
- Add a CI mode that runs the command on every PR's IMPLEMENTATION_PLAN.md change and posts the critique as a comment.
- Parametrize the rubric per project (project-specific criteria via PROJECT_CHARTER.md extension).

None planned now; all are recoverable from the existing command shape.

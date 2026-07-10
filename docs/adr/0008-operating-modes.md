# ADR-0008: Operating modes (minimal / strict / teaching)

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: operating-modes, task-posture, ceremony-control, orthogonality

## Context

The workflow had two existing knobs for adjusting how a command behaves on a given run:

1. **Editor mode** (`Ask` / `Plan` / `Agent` / `Debug`): the agent's intent for that one command (read-only review, planning, applying changes, debugging). Per-command. Documented in WOS `## Editor mode policy`.
2. **Output depth** (`Lean` / `Balanced` / `Deep`): the verbosity of that one command's response. Per-command. Documented in WOS `## Output depth policy`.

Both knobs operate at the command level. Neither captures the **task-level posture** that should apply across a sequence of commands. Three forces made a third axis necessary:

1. **XS tasks were over-ceremonious**. A typo fix in a single markdown file does not benefit from a full `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, and `TEST_STRATEGY.md`. The Typical task shape required all of them as recommended; users were either ignoring the recommendations (silently bypassing the workflow) or running each command and then deleting the artifacts. Both are bad signals.
2. **High-risk tasks needed mandated ceremony**. The reverse problem: auth/crypto/payments/compliance tasks where skipping invariants or tests is dangerous. The workflow's recommendations are advisory; under deadline pressure, "advisory" loses to "ship". The workflow needed a way to declare a task as high-risk and have the recommendations become **mandatory** for that task.
3. **New users needed pedagogical scaffolding**. A user learning the workflow on session 2 benefited from inline phase explanations ("we are in discovery; we are choosing impact-analysis because the file list is unknown; the next step will be invariants-and-non-goals because the change touches a contract"). A user fluent in the workflow on session 50 found that scaffolding noisy. The workflow needed a way to declare "this is a teaching session" without permanently changing every command's verbosity.

These are **task-level** properties: minimal applies to the whole task (every command); strict applies to the whole task; teaching applies to the whole session. Layering them onto the command-level knobs (editor mode, output depth) would have made the per-command surface confusing.

## Decision

The workflow adds a third axis: **operating mode**, declared at `task-init` time and persisted in `TASK_STATE.md`. Three values, plus an unnamed default:

- **`minimal`**: trims optional ceremony for XS tasks. Output depth defaults to Lean. Optional task files (`IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md` when not already mandated) are never created. Long-form `Why this mode:` and `### Definition of done` blocks may be summarized in responses (the canonical content stays in the command files). The `### Handoff` contract remains mandatory; minimal does not skip safety, only ceremony.
- **`strict`**: mandates additional ceremony for high-risk tasks. Output depth defaults to Deep. `invariants-and-non-goals`, `test-strategy`, and `review-hard` become mandatory (not optional). Decisions in `DECISIONS.md` include explicit rollback / unwind notes.
- **`teaching`**: prefaces responses with phase explanations for users learning the workflow. Output depth defaults to Balanced. Each command's response includes a 2-3 line preface (what phase, why this command, what next). Routes via `workflow-guide` rather than `what-next` on ambiguity. Surfaces relevant anti-patterns inline.

Operating mode is **orthogonal** to:

- Editor mode (per-command intent).
- Output depth (per-command verbosity, though operating mode sets defaults).

When no operating mode is declared, the workflow operates under its native rules with category-determined output depth. This unnamed default is "balanced" in spirit; it is simply the standard behavior.

The mode is declared at `task-init` time (in the task description or as an explicit `Operating mode: <name>` line) and recorded in `TASK_STATE.md` `## Resume notes` as `Operating mode: <name>`. Mid-task switches require `sync-task-state` (or `state-reconcile` for wider drift) and an optional `D-N` decision entry when the switch reflects re-evaluation of risk.

## Consequences

### Positive

- **One declaration, persistent application**. The user states the posture once at task-init; every subsequent command in the task reads it from `TASK_STATE.md` and adapts. No per-command override needed.
- **Separation of concerns**. Editor mode is about intent (what is this command trying to do?). Output depth is about verbosity (how much to say?). Operating mode is about posture (how strict should the workflow be on this task?). The three axes do not overlap.
- **Risk-appropriate friction**. Minimal mode removes ceremony where it does not pay; strict mode adds ceremony where it must. Both are explicit; neither is a covert default.
- **Pedagogical layer without permanent overhead**. Teaching mode is opt-in; fluent users do not pay for explanation prefaces by default.
- **No schema break**. Persistence in `## Resume notes` (free-text field) avoids a `TASK_STATE.md` schema change. A future schema bump can promote operating mode to its own section without breaking in-flight tasks.

### Negative

- **One more concept to learn**. New users have to internalize three axes (editor mode, output depth, operating mode) instead of two. The orthogonality helps (each axis has a clear scope), but the learning curve is real.
- **Mode discipline depends on the user**. The model reads operating mode from `TASK_STATE.md`, but the model cannot enforce that the user actually declared an appropriate mode. A user who declares `minimal` for an auth/crypto task gets a less-safe response than the workflow would otherwise provide. The mitigation is the "When NOT to use" guidance in each mode; documentation cannot fully replace user judgment.
- **Mid-task switch risk**. Switching from minimal to strict mid-task can leave behind an `IMPACT_ANALYSIS.md`-shaped gap (minimal skipped it; strict expects it). The recommended path (run the missing commands explicitly after the switch) adds friction; the alternative (let the gap stand) compromises the intent of the switch.

### Neutral

- The unnamed default ("balanced" in spirit) is the most common case. Most tasks declare no operating mode and operate under standard rules. The named modes are for the tail cases where standard rules are wrong.

## Alternatives considered

### Alternative 1: Per-command flags

- Add a `--minimal` / `--strict` / `--teaching` flag to each command invocation.
- Rejected: the user has to remember the flag every time. Loss of consistency across commands ("I ran impact-analysis with --strict but then forgot --strict on test-strategy"). Operating mode is naturally task-level; per-command flagging fragments it.

### Alternative 2: Output depth covers it

- Instead of a separate operating mode, just set output depth (Lean for minimal, Deep for strict). No teaching equivalent.
- Rejected: output depth is verbosity, not ceremony. Strict mode mandates *more commands* (invariants-and-non-goals, test-strategy, review-hard); changing output depth alone does not change which commands run. Conflating verbosity with ceremony breaks both axes.

### Alternative 3: Task shape system covers it

- Use the `## Recommended workflows by task shape` taxonomy (Typical, Contract-sensitive, Small, Docs-only, Test-only, Refactor) as the modes; no separate concept needed.
- Rejected: task shapes describe the **sequence** (which commands in which order); operating modes describe the **posture** (how strict each command is). They are complementary axes. A "Contract-sensitive task" can run in standard or strict mode; the shape and the mode answer different questions.

### Alternative 4: Hardcode posture in task-init

- `task-init` asks "is this high-risk?" and conditionally generates a stricter `TASK_STATE.md` template.
- Rejected: a yes/no question loses the teaching dimension; a multi-choice question reinvents operating modes without naming them. Better to name the concept and let users learn it.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Operating modes` (the normative section).
- [`docs/adr/0001-proposed-by-default.md`](./0001-proposed-by-default.md) (the related decision: write policy by editor mode, which operating mode does not override).
- [`docs/adr/0009-task-shape-system.md`](./0009-task-shape-system.md) (the orthogonal "shape" axis).
- WOS `## Editor mode policy` and `## Output depth policy` (the two pre-existing axes).

## Notes

The "When NOT to use" guidance in each mode is load-bearing: it tells users when their declared mode is wrong for the task. A user who declares `minimal` for an auth change is using the wrong tool; the response should still surface that. Future mode validators (a `state-reconcile` extension that flags risk-mode mismatches) could harden this, but the v0.1.x answer is documentation plus user discipline.

Operating modes are not load-bearing for v0.1.0 release readiness; tasks that declare no mode operate under standard rules and the workflow ships fully functional. The modes are an explicit pressure-relief valve for cases that would otherwise force users to either ignore the workflow or fight it.

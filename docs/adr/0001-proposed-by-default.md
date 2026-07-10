# ADR-0001: PROPOSED-by-default for task-memory writes

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: task-memory, mode-policy, ask-mode, plan-mode, agent-mode, reviewability

## Context

Models in Ask and Plan modes are expected to **think out loud**: explain a plan, propose changes, surface risks, recommend a next step. The user reads the response and decides whether to accept, refine, or reject.

If those modes also wrote files to disk by default, two failure modes would be common:

1. **Surprise writes**. The user asks a question expecting a discussion, gets a substantive plan, and discovers afterward that several task-memory files were silently created or overwritten. The audit trail (`git diff` in the task repo) would show changes the user did not consciously authorize.
2. **Unrecoverable drift**. If a plan was wrong, an Ask-mode response that wrote `IMPLEMENTATION_PLAN.md`, `DECISIONS.md`, and `TASK_STATE.md` would force the user to revert three files instead of just discarding the response.

Agent mode is different by design: the user explicitly opted into a tool that writes code and files. A different default makes sense there.

The workflow needed a way for every command's response to **describe what it would write** (so the user can review the structure, the wording, the bullet list, the recommended next step) **without committing to write it yet**.

## Decision

Task-memory writes follow a mode-conditional default:

- **Ask / Plan modes**: every artifact change is marked `PROPOSED` in the response's `### Artifact changes` block. The model emits the **full intended content** of the file inline so the user can review it; nothing is written to disk until the user re-runs the same command in Agent mode (or copy-pastes the proposed content manually).
- **Agent mode**: artifact changes are marked `APPLIED`. The user opted into write access; the response confirms what was written rather than proposing.

A small set of commands explicitly require `APPLIED` even in Ask mode (e.g., creating the project or task folder during `project-bootstrap` or `task-init`), because those operations are themselves the act the user requested. Each such command states the override explicitly in its `Operating rules:` section.

The `PROPOSED` / `APPLIED` / `SKIP` vocabulary is shared across every command via the `commands/_shared/artifact-changes-default.md` canonical block, which `lint-commands.sh` enforces.

## Consequences

### Positive

- The user reviews structured proposals (full file contents) **before** any disk write. Wrong plans are discarded by ignoring the response, not by reverting commits.
- The conversation itself is the audit trail: every `PROPOSED` block records what would have been written and why, regardless of whether the user later runs in Agent mode.
- Mode policy stays orthogonal to command policy. A command does not need its own ad-hoc "should I write?" decision tree; it inherits the default and only deviates when explicitly justified.
- Switching from review to execution is one mode change, not a command change. The user re-runs the same command in Agent mode and the proposed artifacts become applied.

### Negative

- Two-step latency for first-time writers. A user who fully trusts the model has to run the same command twice (Ask, then Agent) to apply changes. The friction is real but small.
- Slight verbosity: each proposed file is emitted in full inline, which costs tokens. For long artifacts (`IMPLEMENTATION_PLAN.md` for a multi-slice task), this is non-trivial, but the alternative (truncating the proposal) defeats the review purpose.

### Neutral

- The vocabulary `PROPOSED` / `APPLIED` / `SKIP` is a workflow primitive, not a Git or filesystem primitive. It does not map to any external tool's marker; users learning the workflow have to internalize the words.

## Alternatives considered

### Alternative 1: APPLIED-by-default in all modes

- Every command writes to disk on every run; the user reverts via `git` if they disagree.
- Rejected: the cost of "surprise writes" is asymmetric (correcting an unwanted multi-file write is expensive; foregoing a wanted write is cheap). Defaults should match the cheaper failure mode.

### Alternative 2: Per-file ask-permission prompts

- Each file change generates a yes/no question to the user before writing.
- Rejected: makes Ask mode chatty and breaks the response shape. Also doesn't compose with multi-step flows where the user already approved a plan upstream.

### Alternative 3: Mode-conditional, but inverted (Ask = APPLIED, Plan = PROPOSED)

- Treat Ask as "the user is asking for the work to happen"; treat Plan as the review mode.
- Rejected: Ask is the most common mode and the most exploratory; defaulting it to writes contradicts the exploratory intent. Plan mode is rarely the only review surface.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Editor mode policy`, `## Global output contract` → `### Task-memory write policy (default)`, `## Cross-cutting workflow guardrails` → `### Proposal vs approved persistence`.
- `commands/_shared/artifact-changes-default.md` (canonical shared block enforced by `lint-commands.sh`; the no-nest rule that bounds proposal shape).
- Every `commands/*.md` `### Artifact changes` section that uses `PROPOSED` / `APPLIED` / `SKIP`.
- ADR-0023 (`context-rot guardrails`; PROPOSED-mode commands inherit the per-phase warning policy when they write or update `TASK_STATE.md`).
- ADR-0024 (`/approve-proposed` batch-persist idiom; adendum to this ADR that adds a single-command path from PROPOSED to APPLIED).

## Notes

The `task-init` and `project-bootstrap` exceptions exist because the act the user requested **is** the file creation: there is no meaningful "propose without applying" semantics for `mkdir projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`. Those exceptions are explicit and narrow; they are not a license for other commands to default to `APPLIED`.

ADR-0024 (2026-05-19) is an adendum to this ADR, not a replacement. It introduces the `/approve-proposed` command as a single-step path to persist every file marked `PROPOSED` in the most recent prior assistant turn's `### Artifact changes` block. The two-step latency cost named in the Negative consequences above stays valid; `/approve-proposed` is one valid form of step 2, alongside re-running the source command in Agent mode and manual copy-paste. The user chooses which path fits the turn. A separate operating-rule pattern landed in `commands/decision-interview.md` (`LOCK-pick recognition`) for the case where the user input itself is the lock signal; that case persists in the same turn as the input, bypassing the two-step latency entirely for that command.

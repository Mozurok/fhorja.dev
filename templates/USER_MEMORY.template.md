# USER_MEMORY

Bootstrap copy this template to `/USER_MEMORY.md` at the repo root (gitignored). Edit your own copy; do NOT commit edits. This file is the multi-tool, Fhorja-managed user-level memory layer per ADR-0016.

## How to use this file

- Copy: `cp templates/USER_MEMORY.template.md USER_MEMORY.md` (or via your editor).
- Edit by hand; commands READ this file but never WRITE to it.
- Keep entries durable: facts that span tasks AND projects. Task-specific facts go in `TASK_STATE.md`. Project-specific facts go in `PROJECT_CHARTER.md` or `REFERENCES.md`.
- Layered-memory precedence: task memory > project memory > user memory. The more specific wins. See ADR-0016.

## Preferences

(Replace with your own. Examples only.)

- Response length: concise; one-line answers when possible; multi-paragraph only when the question is broad
- Language: English for code and normative content; English or Portuguese for prose, consistent within a file
- Emoji policy: no emojis in code, commits, or PR descriptions; emojis allowed only if I explicitly use them
- Comment density: write no comments by default; only when the WHY is non-obvious
- Architecture style preference: small reviewable slices over big bangs; prefer 3 small PRs to 1 large PR
- Testing style: integration tests against real systems where possible; mock only at boundaries

## Tool-specific quirks

### Cursor

(Empty by default.)

### Claude Code

(Empty by default.)

### Codex / GitHub Copilot / Gemini CLI / OpenHands / Goose

(Empty by default.)

## Recurring gotchas

(Empty by default. Add bullets as you hit them. Examples:)

- (none yet)

## Per-project pointers

(One-line mapping `project-slug -> note`. Useful when switching between active projects. Example:)

- `<project-slug-1> -> brief note about a quirk of this project`
- `<project-slug-2> -> brief note about a different quirk`

## Cross-project learnings

Durable lessons that survive across projects. Manually promoted from task-scoped `LEARNINGS.md` entries per ADR-0017. The workflow does not auto-promote; you decide which lessons are durable enough to lift here.

Promotion process: open the source task's `LEARNINGS.md`, find the entry, copy the `Next time:` line plus enough context to make sense outside the task, paste below as a bullet, update the source entry's `Cross-project promotion:` line to `yes, copied to USER_MEMORY.md on YYYY-MM-DD`.

- (none yet)

## Auto-memory coexistence note

This file is the multi-tool, Fhorja-managed user memory layer (ADR-0016). It is portable across Cursor, Claude Code, Codex, Copilot, Gemini CLI, OpenHands, Goose, and any other tool that reads files from the repo.

Claude Code maintains a separate, Claude-Code-only auto-memory system at `~/.claude/projects/<project-id>/memory/MEMORY.md` with type-tagged entries (user, feedback, project, reference). That system is a Claude-Code-private convenience and stays out of scope for the Fhorja contract; it coexists with this file without overlap.

Rule of thumb: if a fact is multi-tool (will matter when you switch to Cursor or Codex tomorrow), record it here. If it is Claude-Code-only (e.g., a quirk of Claude Code's compaction), the auto-memory system is fine.


## Parallel workflow dispatch operator notes

Operator-level guidance for running parallel workflow dispatch (multi-agent fan-out) across Fhorja commands. These notes are durable across projects and tools; project-specific dispatch facts go in `TASK_STATE.md` or `IMPLEMENTATION_PLAN.md`.

- Sweet-spot batch size: 15--25 agents per dispatch wave. Below 15 the orchestration overhead dominates; above 25 token spend and tail latency rise faster than throughput. See ADR-0039 for the empirical curve.
- Focused-prompt template: 300--500 words of task framing PLUS an explicit `StructuredOutput` reminder consistently yields zero schema-skip across runs. Longer prompts do not measurably improve quality and increase token cost; shorter prompts raise the schema-skip rate.
- Post-apply substrate check: always run `scripts/scan-substrate-orphans.py` after applying a parallel-dispatch batch. Catches orphaned references, missing back-links, and substrate drift introduced when subagents edit overlapping files.
- In-flight monitoring: use `scripts/monitor-fleet-progress.sh` during long batches (anything above ~10 agents or ~5 minutes wall time). Lets you spot stuck workers early instead of waiting for the full batch to settle.
- Tool support reality: Claude Code is currently the only tool that natively supports the Workflow parallel-dispatch contract. Cursor, Codex, Copilot, Gemini CLI, OpenHands, and Goose all degrade to sequential execution; plan batch size and deadlines accordingly when not on Claude Code.
- Token budget: a typical 15--25 agent batch spends 400k--1.3M subagent tokens end-to-end. Budget for the upper end on first runs of a new command shape; tighten the estimate once you have two or three real runs to calibrate against.

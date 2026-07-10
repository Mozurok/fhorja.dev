# ADR-0016: User-level memory layer (`USER_MEMORY.md`)

- **Status**: Accepted
- **Date**: 2026-05-15
- **Tags**: context-engineering, memory-layer, user-scoped, layered-precedence, multi-tool-portable

## Context

ADR-0007 introduced project-level memory (`PROJECT_CHARTER.md`, `REFERENCES.md`) to capture context that outlives any single task. Three failure modes surfaced afterward that even project memory does not address:

1. **Preferences re-elicit per task across projects**. A user who works on three projects (each properly bootstrapped) still has to re-establish "I prefer terse responses" or "no emojis in code" each time they start a new task, regardless of project. Project memory is project-scoped; these preferences cross projects.
2. **Tool-specific quirks die in the user's head**. "Cursor agent mode sometimes mishandles my-rule-X"; "Codex skills mirror takes 30s to update on save". These survive only as informal habit until something breaks; no shared memory layer captures them.
3. **Cross-project learnings have no home**. "On Supabase projects, validate RLS before pr-package"; "On Next.js 15, the App-Router naming dispute resurfaces every PR". These are durable but project memory's scope is "this project's stack and stakeholders", not "what I learned that applies across multiple of my projects".

The Claude Code auto-memory system at `~/.claude/projects/<project-id>/memory/` partially addresses #1 with type-tagged entries (user, feedback, project, reference). But it is Claude-Code-private: Cursor users, Codex users, Copilot users do not see it. The WOS multi-tool architecture rule (ADR-0005) requires that the canonical memory primitives work for all tools.

The memory pyramid the WOS now needs:

```
task memory      (TASK_STATE.md, DECISIONS.md, SLICES/*)   - specific
project memory   (PROJECT_CHARTER.md, REFERENCES.md)        -
user memory      (USER_MEMORY.md)                           - general
```

User-level memory is the missing third tier.

D-5 of the 2026-05-15 context-engineering uplift considered four locations: repo root committed, repo root gitignored, `~/.my-work-tasks/`, and piggyback on Claude Code auto-memory. Repo root gitignored won; rationale in D-5.

## Decision

The WOS introduces a user-level memory artifact:

1. **Location**: `/USER_MEMORY.md` at the repo root, gitignored (`.gitignore` entry `/USER_MEMORY.md` with leading slash to scope to root only).
2. **Template**: `templates/USER_MEMORY.template.md` is committed (the only USER_MEMORY-related file in git). Users bootstrap their own copy via `cp templates/USER_MEMORY.template.md USER_MEMORY.md`.
3. **Sections (template-provided)**: How to use this file; Preferences; Tool-specific quirks (Cursor / Claude Code / Codex / Copilot / Gemini CLI / OpenHands / Goose subsections, empty by default); Recurring gotchas; Per-project pointers; Cross-project learnings; Auto-memory coexistence note.
4. **Layered precedence rule** (task > project > user; specific overrides general). When the same fact appears at multiple layers, the more specific layer wins. Not lint-enforceable (the model cannot reliably tell which conflicts matter); documented in `wos/project-level-memory.md ## Relationship to user-level memory` and consumed by commands at runtime.
5. **Read-only from commands**. Commands READ `USER_MEMORY.md` when present; never WRITE to it. Mutations are user-driven (edit the file directly via the user's preferred editor). This prevents tool-driven drift between expected and actual user preferences.
6. **Optional, graceful absence**. `task-init`, `what-next`, `resume-from-state` add USER_MEMORY.md to `Task repository files to read:` with the suffix `(if present at repo root)`. If absent, commands proceed silently; no warning, no requirement.
7. **Coexists with Claude Code auto-memory**. The Claude Code auto-memory at `~/.claude/projects/<id>/memory/` remains private to Claude Code and stays out of scope (per the slice 05 invariant I-9). USER_MEMORY.md is the multi-tool layer; the auto-memory is the Claude-Code-only sibling. The template's `## Auto-memory coexistence note` section documents the boundary.

## Consequences

### Positive

- **Preferences persist across projects AND tools**. A user who edits Cursor, Claude Code, and Codex sees the same USER_MEMORY.md regardless of tool (any tool that reads repo files sees it). Per-project preferences still live in PROJECT_CHARTER.md.
- **Tool quirks find a durable home**. The template has explicit per-tool subsections; users record quirks as they discover them. Future maintenance benefits from this collective memory even without an explicit "share with team" channel.
- **Cross-project learnings accumulate**. Slice 12 (reflexion-style learnings) will optionally aggregate task-level LEARNINGS into the user's USER_MEMORY.md `## Cross-project learnings` section. The infrastructure is in place.
- **Multi-tool portable**. Unlike Claude Code auto-memory, USER_MEMORY.md works for every tool in the WOS distribution (Cursor, Claude Code, Codex, Copilot, Gemini CLI, OpenHands, Goose).
- **Layered precedence is teachable**. Task > project > user; specific overrides general. New contributors can learn this rule once and apply it everywhere.

### Negative

- **Users must bootstrap**. New users need to `cp templates/USER_MEMORY.template.md USER_MEMORY.md` once. Mitigation: template's `## How to use this file` section is the bootstrap instructions; commands handle absence gracefully (no errors when the file does not exist).
- **Per-user maintenance**. Each user maintains their own copy; no shared baseline beyond the template. Mitigation: the template is intentionally minimal; users add only what they actually need.
- **Three layers to reason about**. Contributors writing new commands must decide which layer reads from which artifact. Mitigation: the precedence rule (task > project > user) plus `wos/project-level-memory.md` documentation makes the decision mechanical.
- **No lint enforcement of layer precedence**. If a user puts task-specific facts in USER_MEMORY.md by mistake, lint cannot catch this. Mitigation: documented best practice; cost of mistake is low (worst case is the fact is too general, not load-bearing).

### Neutral

- The template itself is small (~80-120 lines). Adding new sections requires only template edits; user's copy can stay as-is.
- USER_MEMORY.md may grow over time. If it ever becomes heavy enough to need compaction, a future `compact-user-memory` analogue (matching slice 04's `compact-task-memory` pattern) can be introduced. Not planned.

## Alternatives considered

### Alternative 1: repo root, committed

- `/USER_MEMORY.md` tracked in git.
- **Rejected**: brings per-user content into the open-source distribution at Phase 3. Multiple maintainers / forks would conflict. Privacy and portability lose.

### Alternative 2: `~/.my-work-tasks/USER_MEMORY.md`

- File lives in user's home dir; commands read from absolute path.
- **Rejected**: requires XDG-style path handling per OS (`~/.my-work-tasks/` does not exist on Windows by default); commands need fallback logic for the "file may or may not exist at this path" case at OS level; bootstrap is harder.

### Alternative 3: piggyback on Claude Code auto-memory

- Reuse `~/.claude/projects/<id>/memory/USER_MEMORY.md` (or similar in the auto-memory directory).
- **Rejected**: Claude-Code-only. Violates ADR-0005 multi-tool rule. Cursor / Codex / Copilot users would not see it.

### Alternative 4: no user-level memory, expect users to manage preferences via tool config

- Rely on each tool's own preferences mechanism (`.cursorrules`, Claude Code system prompt, etc.).
- **Rejected**: fragments preferences across N tool-specific files. No durable source of truth. Cross-project learnings have no home.

### Alternative 5: per-user folder under `projects/`

- E.g., `projects/_user/USER_MEMORY.md`. Uses the existing gitignored `projects/` umbrella.
- **Rejected**: pollutes `projects/` which is meant for per-client/project task folders. The `_user` sentinel would have to be specially handled by tools that iterate over `projects/`. Repo root is the cleaner home.

## References

- `templates/USER_MEMORY.template.md` (the committed template).
- `wos/project-level-memory.md ## Relationship to user-level memory` (the lazy-loaded narrative; layered precedence rule).
- `commands/task-init.md`, `commands/what-next.md`, `commands/resume-from-state.md` (consumers; read USER_MEMORY.md when present).
- ADR-0005 (multi-tool architecture; the reason this is not piggybacked on Claude Code auto-memory).
- ADR-0007 (project-level memory; the immediate predecessor of this layer).
- ADR-0012 (context budget; names the `memory` layer this artifact lives in).
- D-5 in `projects/bmazurok__my-work-tasks/active/2026-05-15_context-engineering-uplift/DECISIONS.md` (location decision).
- Mem0, "Building Production-Ready AI Agents with Scalable Long-Term Memory" (ECAI 2025): the long-term memory tier in the memory pyramid.
- Zep, "Temporal Knowledge Graph Architecture for Agent Memory" (2025): user-scoped facts with timestamps.

## Notes

The layered precedence rule (task > project > user) is the same shape as CSS specificity. Contributors who know one can analogize the other. It is also similar to how Unix file permissions resolve (user > group > other; specific wins).

Slice 12 (reflexion-style learnings) builds on top of this layer: closed slices may optionally append a learning to `LEARNINGS.md` (task-scoped); over time, the user can promote durable cross-project lessons to USER_MEMORY.md `## Cross-project learnings`. Promotion is manual in slice 12; an automated promotion could be a future slice.

The Claude Code auto-memory system at `~/.claude/projects/<id>/memory/` is governed by the Claude Code prompt and is private to that tool. It coexists with USER_MEMORY.md without overlap. If a fact applies to multiple tools, record it in USER_MEMORY.md; if Claude-Code-specific, the auto-memory is appropriate. The template's `## Auto-memory coexistence note` section instructs the user on which goes where.

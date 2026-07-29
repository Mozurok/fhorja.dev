---
activation: model_decision
description: Harness session-file map for lost-session recovery (the resume-from-state --lost-session mode, ADR-0113). Where each harness persists its session transcript, how to identify the right session file, and the extraction rules (PROPOSED with provenance, read-only). Load only when a lost-session recovery is explicitly requested.
---

# Session recovery

Consumed by `commands/resume-from-state.md` `--lost-session` mode (ADR-0113). This topic carries the per-harness session-file map so the mode's capped sweep (6 tool calls) spends its budget reading candidates, not rediscovering layouts. The G3-style safeguard applies: the run that uses this file cites WHICH subsection it read (for example `session-recovery: Claude Code layout`), so the lazy load never degrades into a paraphrase.

Scope discipline: an entry exists ONLY for a harness whose layout was verified in a real recovery or forensics session (the same evidence bar as `wos/editor-mode-mappings.md ## Harness operational quirks`). Do not add speculative rows for other tools; harness storage layouts date as vendors ship, so each entry names its verification date.

## Recovery contract (summary; the mode owns the full contract)

- Read-only by construction: this flow never writes or edits any session file, task file, or product file. Every extraction is PROPOSED with provenance (the source file plus the line or event it came from).
- The 6-tool-call cap prevails over any per-step budget. Candidates found but not read are reported as unconfirmed leads, never silently dropped.
- Before any tool call, ask for a date window and the harness (zero cost; shrinks the sweep from a directory walk to a couple of globs).
- The mode never resolves state on its own: a found task folder routes to `state-reconcile`; none found routes to `task-init`.

## Claude Code layout (verified 2026-07-21, av3 forensics)

- Session transcripts: one JSONL file per session under the per-project folder inside the user-level Claude directory: `~/.claude/projects/<project-slug>/<session-uuid>.jsonl`. The `<project-slug>` is the working-directory path with separators flattened to hyphens; the newest `*.jsonl` by mtime is usually the lost session.
- Distinguish the auto-memory folder: `~/.claude/projects/<project-slug>/memory/` holds the persistent memory files (MEMORY.md plus notes), NOT session transcripts. Do not mine it for turn history; it reflects what was true when written, not what happened last session.
- Each JSONL line is one event (user turn, assistant turn, tool result). The useful anchors for recovery: the last user messages (what was being asked), file paths in tool calls (what was being edited), and any `### Handoff` block in late assistant turns (the recorded next step).
- Subagent and workflow transcripts, when present, live under a `subagents/` sibling of the session file; treat them as secondary evidence (the parent session names what was dispatched).

## Codex CLI layout (verified 2026-07-21, bv3 forensics)

- Session transcripts: rollout JSONL files under the dated tree `~/.codex/sessions/YYYY/MM/DD/rollout-YYYY-MM-DDTHH-MM-SS-<id>.jsonl`. The filename timestamp is the session START; a long session's content extends well past it, so match the date window against the file's mtime too, not the name alone.
- Each line is one protocol event; exec calls and their outputs carry the file paths and commands the session touched. The useful anchors: the latest exec events naming task-folder paths, and the last agent messages before the drop.

## Fallback: local state databases (best-effort)

- Some harnesses (and editors embedding them) persist recent-session metadata in a local sqlite database rather than, or in addition to, transcript files. Treat sqlite as a best-effort LAST resort inside the same 6-call cap: a single read-only query listing recent sessions or workspace paths, only when the transcript sweep found nothing. Never write to the database; a locked or missing database is reported as a dead end, not retried.

## The highest-risk window for memory drift

The review-and-fix leg, between the first review verdict and the merged PR, is where task memory most often goes stale. It has the shape that defeats state upkeep: many small fixes, each too narrow to feel like a step worth recording, applied under time pressure while attention sits on the review output rather than on the task folder. `pr-feedback-ingest` is the command that drives this leg and it is also the one most often skipped, because the feedback arrives as a readable list that looks actionable without any intake step.

A measured instance: a 21-hour task wrote nothing to its task folder for 12h35m, a window that contained three full review runs, 81 findings, a base merge, the PR, and about 20 hand-applied fixes. Its `TASK_STATE.md` ended the session asserting that four review phases had never run while the review's own manifest recorded them complete, so the memory said the work could not ship while the artifact said it could.

Recovery reads this as a signal, not a surprise: when a session is lost and its last state write predates a review verdict, assume the whole fix leg is unrecorded and reconcile against the review artifacts and the git log rather than trusting the last state write.

## What recovery extracts (and what it never does)

Extract, as PROPOSED lines with provenance: the active task folder path (if any), the last completed command and its Handoff, the files being edited, and any explicit decisions stated in the final turns. The mode then routes: `state-reconcile` when a task folder was found (it reconciles the PROPOSED extractions against the on-disk substrate), `task-init` when none was. Unattended runs with an unknown project slug stall as PROPOSED rather than guessing a directory to sweep.

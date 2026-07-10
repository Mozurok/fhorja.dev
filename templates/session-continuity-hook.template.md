# Session-continuity hook (template, opt-in, wired in the CONSUMING repo)

The session-continuity hook keeps an active Fhorja task resumable across sessions
without relying on the user remembering to run `sync-task-state`. At session start
it surfaces the active task's Resume notes and Recommended next step; at session
end it writes a bounded continuity marker to the task's `.wos/` sidecar (it never
rewrites authored `TASK_STATE.md` sections). See ADR-0052.

The hook script ships in this repo at `scripts/session-continuity-hook.sh`. The Fhorja
repo does not enable the hook itself; you wire it in the consuming repo's
`.claude/settings.json`, the same way `scripts/typecheck-hook.sh` is wired.

## 1. Wire it (consuming repo `.claude/settings.json`)

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "bash scripts/session-continuity-hook.sh start" } ] }
    ],
    "SessionStop": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "bash scripts/session-continuity-hook.sh stop" } ] }
    ]
  }
}
```

The mode (`start` / `stop`) is read from the CLI argument. If you omit the argument
the script falls back to the `hook_event_name` field in the Claude Code hook JSON on
stdin (`SessionStart` to start, `SessionStop` or `Stop` to stop).

## 2. Point it at your tasks tree (optional)

The hook finds the active task as the most-recently-modified
`projects/*/active/*/TASK_STATE.md`. The search root resolves in this order:

1. `$WOS_TASKS_ROOT` (set this if your tasks live elsewhere)
2. `$CLAUDE_PROJECT_DIR/projects` (Claude Code sets `CLAUDE_PROJECT_DIR`)
3. `./projects`

If there is no active task it stays quiet on stop and prints a one-line note on start.
If there is more than one active task it picks the most recently touched and says so.

## 3. What it writes (and what it never touches)

- Writes only `active/<task>/.wos/SESSION_CONTINUITY.json` (session-end timestamp,
  session id, task name). The sidecar is advisory, not authoritative state.
- Never edits authored `TASK_STATE.md` sections. Full model-driven sync still happens
  when you run `sync-task-state`; the hook only records that a session ended and, on
  the next start, nudges you to sync when `TASK_STATE.md` has not changed since.

## 4. Caveats

- Advisory and non-blocking: the hook always exits 0. It cannot fail your turn.
- Hook firing is host-dependent. If your host does not fire `SessionStop` reliably
  (for example very short sessions or hard kills), the continuity marker may be
  missed; the start-side resume surfacing still works from `TASK_STATE.md`.
- The staleness nudge is surfaced, not auto-cleared. Running `sync-task-state` updates
  `TASK_STATE.md`, which clears the nudge on the next session start.

# Session-continuity hook (template, opt-in, wired in the CONSUMING repo)

The session-continuity hook keeps an active Fhorja task resumable across sessions
without relying on the user remembering to run `sync-task-state`. At session start
it surfaces the active task's Resume notes and Recommended next step; at session
end it writes a bounded continuity marker to the task's `.wos/` sidecar (it never
rewrites authored `TASK_STATE.md` sections). See ADR-0052.

The hook script ships in this repo at `scripts/session-continuity-hook.sh`, and since
2026-08-17 this repo also wires it for itself. It stays inert in a tree with no
`projects/` directory, so a consuming repo still has to wire it deliberately in its own
`.claude/settings.json`, the same way `scripts/typecheck-hook.sh` is wired.

## Which task it picks, and when it refuses to pick

`projects/` holds the tasks of every project, so "the most recently modified
`TASK_STATE.md`" is not the task in hand once more than one is open. Wired unscoped in a
tree with 32 active tasks across 84 project folders, the hook printed an unrelated client
task's resume notes into `SessionStart` context and wrote a session-end marker into that
task's sidecar. Both halves are advisory and exit 0, so nothing broke; it simply spent
context on the wrong work and touched another project's state.

Scope is therefore explicit:

| Variable | Effect |
|---|---|
| `WOS_ACTIVE_TASK` | absolute path to one task folder; wins outright |
| `WOS_ACTIVE_PROJECT` | a `projects/<name>` directory; restricts the search |
| `WOS_TASKS_ROOT` | overrides the `projects/` root itself |

With neither of the first two set, a single active task is unambiguous and still works.
More than one and the hook stands down: one line on start naming the variables, and
nothing at all on stop, because an unwanted sidecar write into another project's task is
the harm worth avoiding and twenty lines about the wrong task is the cost worth avoiding.
A `WOS_ACTIVE_PROJECT` that does not resolve also stands down rather than widening back to
the whole tree, since a silent fallback would restore exactly the behavior the scope exists
to prevent while looking like it had worked.

## 1. Wire it (consuming repo `.claude/settings.json`)

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "bash $CLAUDE_PROJECT_DIR/scripts/session-continuity-hook.sh start" } ] }
    ],
    "Stop": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "bash $CLAUDE_PROJECT_DIR/scripts/session-continuity-hook.sh stop" } ] }
    ]
  }
}
```

The mode (`start` / `stop`) is read from the CLI argument. If you omit the argument
the script falls back to the `hook_event_name` field in the Claude Code hook JSON on
stdin (`SessionStart` to start, `Stop` to stop). `Stop` is the Claude Code event this
repository wires in its own `.claude/settings.json`; it fires when the agent finishes a
response, so the marker is refreshed at the end of every turn. The two command strings
above are the ones `templates/hooks-baseline.json.template` allow-lists.

## 2. Point it at your tasks tree (optional)

The search root resolves in this order:

1. `$WOS_TASKS_ROOT` (set this if your tasks live elsewhere)
2. `$CLAUDE_PROJECT_DIR/projects` (Claude Code sets `CLAUDE_PROJECT_DIR`)
3. `./projects`

Scope is separate from the search root. Set `WOS_ACTIVE_TASK` (one task folder; wins outright) or `WOS_ACTIVE_PROJECT` (a `projects/<name>` directory). With neither set, a single active task is unambiguous and still works. If there is no active task it stays quiet on stop and prints a one-line note on start. If there is more than one active task and no scope, the hook stands down: one line on start naming those two variables, and nothing at all on stop. A `WOS_ACTIVE_PROJECT` that does not resolve also stands down rather than picking the most recently touched task.

## 3. What it writes (and what it never touches)

- Writes only `active/<task>/.wos/SESSION_CONTINUITY.json` (session-end timestamp,
  session id, task name). The sidecar is advisory, not authoritative state.
- Never edits authored `TASK_STATE.md` sections. Full model-driven sync still happens
  when you run `sync-task-state`; the hook only records that a session ended and, on
  the next start, nudges you to sync when `TASK_STATE.md` has not changed since.

## 4. Caveats

- Advisory and non-blocking: the hook always exits 0. It cannot fail your turn.
- Hook firing is host-dependent. If your host does not fire `Stop` reliably
  (for example a hard kill in the middle of a turn), the continuity marker may be
  missed; the start-side resume surfacing still works from `TASK_STATE.md`.
- The staleness nudge is surfaced, not auto-cleared. Running `sync-task-state` updates
  `TASK_STATE.md`, which clears the nudge on the next session start.

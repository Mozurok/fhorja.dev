# Fhorja hooks catalog

Fhorja ships optional Claude Code hooks under `scripts/*-hook.sh` (plus `scripts/hook-integrity-check.sh`). Hooks are user-defined shell commands that run at points in the Claude Code lifecycle; they are opt-in and wired per consuming repo in `.claude/settings.json`. None of them is required to use Fhorja. This file is the single catalog so the automation layer is discoverable rather than living only in `scripts/`.

## Exit-code semantics (Claude Code)

Per the Claude Code hooks reference (https://code.claude.com/docs/en/hooks):

| Exit code | Effect |
|---|---|
| 0 | Success. For most events stdout goes to the debug log; for `UserPromptSubmit` and `SessionStart` stdout is added as context the model can see. |
| 2 | Blocking error. stderr is fed back to the model. On `PreToolUse` it BLOCKS the tool call (it has not run yet); on `PostToolUse` it cannot block (the tool already ran) and only surfaces stderr to the model. |
| other | Non-blocking error: the hook name and first stderr line show in the transcript; execution continues. |

`PreToolUse` can block or modify a tool call; `PostToolUse` can modify output or give feedback but cannot block. Every Fhorja hook below is advisory and non-blocking by design (it never returns exit 2 to block); the typecheck hook uses exit 2 only to surface new errors as feedback, not to block.

## The hooks

| Hook | Event | Posture | Purpose |
|---|---|---|---|
| `typecheck-hook.sh` | PostToolUse | non-blocking (exit 2 = feedback) | Runs `tsc --noEmit` after Edit/Write on `.ts`/`.tsx`, filters pre-existing errors via a project `.typecheck-baseline`, and surfaces only NEW type errors. |
| `session-continuity-hook.sh` | SessionStart, SessionStop/Stop | non-blocking (exit 0) | Keeps an active Fhorja task resumable across sessions: on stop writes a bounded continuity marker to the task `.wos/` sidecar; on start prints Resume notes + Recommended next step and nudges `sync-task-state` when TASK_STATE is stale. Sidecar-only, never touches authored sections (ADR-0052). |
| `hook-integrity-check.sh` | SessionStart | non-blocking (exit 0) | Diffs the live `.claude/settings.json` hook commands against a committed `.claude/hooks-baseline.json` allow-list and warns on any unrecognized hook (config-tamper nudge). Silent when no baseline exists (ADR-0059-adjacent; round-4 round). |
| `artifact-changes-mode-check-hook.sh` | PostToolUse | non-blocking | When an Edit/Write touches a task artifact under `projects/*/active/*/`, checks the `### Artifact changes` block for inconsistencies with ADR-0001 (PROPOSED-by-default). |
| `auto-pilot-checkpoint-hook.sh` | Stop | non-blocking | Tracks consecutive auto-pilot (paste-relay) turns and nudges a checkpoint when a long unbroken run risks cumulative drift. |
| `auto-pilot-reset-hook.sh` | UserPromptSubmit | non-blocking | Companion to the checkpoint hook: resets the consecutive-turn counter when the user submits real typed text (not a slash command). |
| `edit-drift-detector-hook.sh` | PostToolUse | non-blocking | Detects common mechanical Edit failure patterns and surfaces them as warnings so the agent can self-correct next turn. |
| `proposed-counter-hook.sh` | Stop | non-blocking | Nudges the user to run `/approve-proposed` when artifacts are still tagged PROPOSED and not yet persisted (ADR-0024). |

## Wiring

Hooks are opt-in. Wire the ones you want in the consuming repo's `.claude/settings.json` under the matching event, for example:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "bash $CLAUDE_PROJECT_DIR/scripts/hook-integrity-check.sh" } ] }
    ]
  }
}
```

Setup helpers: `templates/hook-integrity-check.template.md` and `templates/hooks-baseline.json.template` (integrity check), `templates/session-continuity-hook.template.md` (continuity), `templates/typecheck-baseline.template` (typecheck baseline seed), `templates/deterministic-gate-hook.template.md` (a deterministic stop-gate pattern). When you add or change a wired hook, update `.claude/hooks-baseline.json` so the integrity check does not flag it.

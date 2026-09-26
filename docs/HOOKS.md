# Fhorja hooks catalog

Fhorja ships optional Claude Code hooks under `scripts/*-hook.sh` (plus `scripts/hook-integrity-check.sh`). Hooks are user-defined shell commands that run at points in the Claude Code lifecycle; they are opt-in and wired per consuming repo in `.claude/settings.json`. None of them is required to use Fhorja. This file is the catalog of that glob, so the automation layer is discoverable rather than living only in `scripts/`. The table below is complete for those files. `scripts/block-git-add-all.sh` is a tracked PreToolUse helper outside the glob; it is not wired in `.claude/settings.json` and is therefore not in the table. It can deny an unsafe `git add` through `permissionDecision` while exiting 0, so the non-blocking posture of the table does not describe it.

## Exit-code semantics (Claude Code)

Per the Claude Code hooks reference (https://code.claude.com/docs/en/hooks):

| Exit code | Effect |
|---|---|
| 0 | Success. For most events stdout goes to the debug log; for `UserPromptSubmit` and `SessionStart` stdout is added as context the model can see. |
| 2 | Blocking error. stderr is fed back to the model. On `PreToolUse` it BLOCKS the tool call (it has not run yet); on `PostToolUse` it cannot block (the tool already ran) and only surfaces stderr to the model. |
| other | Non-blocking error: the hook name and first stderr line show in the transcript; execution continues. |

`PreToolUse` can block or modify a tool call; `PostToolUse` can modify output or give feedback but cannot block. Every Fhorja hook below is advisory and non-blocking by design (it never returns exit 2 to block); the typecheck hook uses exit 2 only to surface new errors as feedback, not to block.

## Permissions baseline

The tracked `.claude/settings.json` carries a `permissions.deny` list covering the git
operations that destroy history or uncommitted work:

```json
"permissions": {
  "deny": [
    "Bash(git push --force*)",
    "Bash(git push -f*)",
    "Bash(git reset --hard*)",
    "Bash(git clean -f*)",
    "Bash(git branch -D*)"
  ]
}
```

This exists because a per-machine `.claude/settings.local.json` commonly accumulates a
broad allow entry such as `Bash(git *)`, which pre-approves the destructive spellings
along with the read-only majority. Deny rules are evaluated before allow rules, so the
tracked list narrows that window without the local file having to be edited.

Two limitations, stated plainly so the list is not mistaken for a guarantee:

- Matching is by prefix. A chained invocation (`cmd && git reset --hard`), an aliased
  form, or a refspec-force spelling (`git push origin +main`) is not caught.
- It bounds the agent's tool calls, not the terminal. Anything typed directly in a shell
  is unaffected.

It narrows the window rather than closing it. Treat it as one layer, not as the control.

`templates/claude-permissions.template.json` carries that same deny list plus an `ask` block for
`gh pr merge` and `gh pr ready`, ready to copy into a consuming repo. `git push` is not in it. A push
to a task branch reaches a bounded audience, and `pr-package --apply` pushes and opens the draft PR
on its own invocation with no second prompt (ADR-0185, ADR-0200), so an `ask` on every push would
put back a stop the contract removed. Merging and marking a draft ready for review open the audience,
and those two keep the confirmation. It is permissions only, with no
hook, and that is the point: measured 2026-08-30, an external read-only consumer's driver
raises `HookRefusal` with no override flag against a repository that ships its own
`PreToolUse` hook, so installing one makes the repo undirectable by the runner. A deny and ask
list costs nothing in that direction, because it is data the client already evaluates rather than
a second program competing for the same slot.
This repository takes its own advice: its `.claude/settings.json` carries the deny list and no
`ask` entry and no `PreToolUse` hook.

Drop the `ask` block if a human already merges every PR by hand, or if a runner drives the repo and
cannot answer a prompt. An unanswerable ask is a hang, not a gate.

## The hooks

| Hook | Event | Posture | Purpose |
|---|---|---|---|
| `typecheck-hook.sh` | PostToolUse | non-blocking (exit 2 = feedback) | Runs `tsc --noEmit` after Edit/Write on `.ts`/`.tsx`, filters pre-existing errors via a project `.typecheck-baseline`, and surfaces only NEW type errors. |
| `session-continuity-hook.sh` | SessionStart, Stop | non-blocking (exit 0) | Keeps an active Fhorja task resumable across sessions: on stop writes a bounded continuity marker to the task `.wos/` sidecar; on start prints Resume notes + Recommended next step and nudges `sync-task-state` when TASK_STATE is stale. Sidecar-only, never touches authored sections (ADR-0052). **Scoped, and declines when the task is ambiguous.** `projects/` holds every project's tasks, so "most recently modified across the tree" is the wrong task once more than one is open: wired unscoped in this repository it printed 20+ lines of an unrelated client task into `SessionStart` context and wrote a session-end marker into that task's sidecar. Scope is now explicit, `WOS_ACTIVE_TASK` (a task folder, wins outright) or `WOS_ACTIVE_PROJECT` (a `projects/<name>` directory). One active task needs no scope. More than one and no scope means it stands down: a single line on start naming the two variables, and nothing at all on stop, since an unwanted sidecar write into another project's task is the harm worth avoiding. A scope that does not resolve also stands down rather than widening back to the whole tree. |
| `hook-integrity-check.sh` | SessionStart | non-blocking (exit 0) | Two checks over every hook command Claude Code can resolve (project `settings.json`, project `settings.local.json`, and user-level `~/.claude/settings.json`). First, diffs them against a committed `.claude/hooks-baseline.json` allow-list and warns on any unrecognized hook (config-tamper nudge). Second, warns when a wired hook's script is not present on disk, which fails silently otherwise and is the ordinary result of moving a repository that user-level hooks point into by absolute path. Machine prefixes are normalized to `$CLAUDE_PROJECT_DIR` and `~` so one baseline is valid across clones. Silent when no baseline exists (ADR-0059-adjacent; round-4 round). |
| `auto-pilot-checkpoint-hook.sh` | Stop | non-blocking | Records the streak of consecutive turns with no typed user prompt and prints its length at high thresholds. It recommends nothing: under an automatic chain (ADR-0186) a long streak is the normal case, not a sign of drift. |
| `auto-pilot-reset-hook.sh` | UserPromptSubmit | non-blocking | Companion to the checkpoint hook: resets the consecutive-turn counter when the user submits real typed text (not a slash command). |
| `edit-drift-detector-hook.sh` | PostToolUse | non-blocking | Detects common mechanical Edit failure patterns and surfaces them as warnings so the agent can self-correct next turn. |

The table lists every `scripts/*-hook.sh` file plus `hook-integrity-check.sh`. It does not list `scripts/block-git-add-all.sh`.

Two hooks were removed on 2026-09-23: `proposed-counter-hook.sh`, which counted artifacts still tagged PROPOSED and pointed at `/approve-proposed`, and `artifact-changes-mode-check-hook.sh`, which flagged `APPLIED` tags written in Ask or Plan mode. Both enforced the ADR-0001 mode gate. Task memory has been written `APPLIED` in every mode since ADR-0199 and ADR-0215, so the first counted a marker that no longer piles up and the second reported the correct behavior as an error. Neither was wired in this repository's `.claude/settings.json`.

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

Setup helpers: `templates/hook-integrity-check.template.md` and `templates/hooks-baseline.json.template` (integrity check), `templates/session-continuity-hook.template.md` (continuity: scope with `WOS_ACTIVE_TASK` or `WOS_ACTIVE_PROJECT`; more than one active task and no scope means the hook stands down), `templates/typecheck-baseline.template` (typecheck baseline seed), `templates/deterministic-gate-hook.template.md` (a deterministic stop-gate pattern). When you add or change a wired hook, update `.claude/hooks-baseline.json` so the integrity check does not flag it.

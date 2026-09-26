# hook-integrity-check wiring

`scripts/hook-integrity-check.sh` is an optional, advisory Claude Code SessionStart hook. It compares every hook command Claude Code can resolve against a committed allow-list in `.claude/hooks-baseline.json` and prints a warning when it finds a command that is not on the list. It always exits 0 and stays silent when no baseline exists.

It reads three surfaces, because a hook added to any one of them runs:

| Surface | Scope |
|---|---|
| `.claude/settings.json` | this project, committed |
| `.claude/settings.local.json` | this project, per machine |
| `~/.claude/settings.json` | every project on this machine |

The user-level file is the one worth watching most: a hook there reaches every session in every repository, and a check that reads only the project file reports clean while that surface goes uninspected.

Machine-specific prefixes are normalized on both sides before comparing: the resolved project directory becomes `$CLAUDE_PROJECT_DIR` and the home directory becomes `~`. Without that, a baseline holding absolute paths matches only the machine that wrote it, so every other clone sees its own legitimate hooks flagged and learns to ignore the warning. The normalization is also what keeps the file free of machine paths and therefore committable.

Why it exists: a hook runs an arbitrary command on every session. `skill-vet` (ADR-0046) inspects a candidate skill before you trust it, but it cannot see a hook that was later added to your live `settings.json`. This check surfaces that drift at session start as a nudge, never as a block.

## Setup

1. Seed the baseline from your current settings across all three surfaces, normalized:

   ```bash
   {
     for f in .claude/settings.json .claude/settings.local.json "$HOME/.claude/settings.json"; do
       [ -f "$f" ] && jq -r '[.. | objects | select(has("command")) | .command] | .[]' "$f"
     done
   } | sed -e "s|$PWD|\$CLAUDE_PROJECT_DIR|g" -e "s|$HOME|~|g" | sort -u \
     | jq -R . | jq -s '{allowed: .}' > .claude/hooks-baseline.json
   ```

   Read the result before trusting it. Seeding records what is wired right now as legitimate, so anything already unwanted gets baselined as approved.
2. Wire the hook in `.claude/settings.json` under `SessionStart`:
   ```json
   {
     "hooks": {
       "SessionStart": [
         { "hooks": [ { "type": "command", "command": "bash $CLAUDE_PROJECT_DIR/scripts/hook-integrity-check.sh" } ] }
       ]
     }
   }
   ```
3. Add the hook's own command string to `.claude/hooks-baseline.json` so it does not flag itself.

## Maintenance

When you intentionally add or change a hook, update `.claude/hooks-baseline.json` in the same change. If the warning fires and you did not add the hook, inspect the command before continuing the session.

## The second check: wired but absent

Besides the allow-list diff, the hook warns when a wired command names a script that is not on disk.
That case fails silently: the harness logs it, the session continues, and the hook simply stops
running. It is the ordinary outcome of moving or renaming a repository that user-level hooks point
into by absolute path, which is how they are usually wired.

Path extraction expands `~`, `$HOME` and `$CLAUDE_PROJECT_DIR` before testing the path. Skipping that
expansion produces a false positive on a healthy config, because the match then starts at the slash
after the variable and tests a path that was never meant to be absolute. A guard that cries wolf on a
working setup is worse than no guard, since it teaches the reader to ignore the line.

## Verifying it works

Do not trust a passing run alone (lint-green is not gate-working). Confirm both directions:
- Inject an unexpected hook command into a test `settings.json` and run `bash scripts/hook-integrity-check.sh start` with `CLAUDE_PROJECT_DIR` pointed at the test dir; it SHALL print the warning and exit 0.
- Run with a baseline that lists every live command; it SHALL print nothing and exit 0.

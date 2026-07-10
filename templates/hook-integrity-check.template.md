# hook-integrity-check wiring

`scripts/hook-integrity-check.sh` is an optional, advisory Claude Code SessionStart hook. It compares the hook commands wired in `.claude/settings.json` against a committed allow-list in `.claude/hooks-baseline.json` and prints a warning when it finds a hook command that is not on the list. It always exits 0 and stays silent when no baseline exists.

Why it exists: a hook runs an arbitrary command on every session. `skill-vet` (ADR-0046) inspects a candidate skill before you trust it, but it cannot see a hook that was later added to your live `settings.json`. This check surfaces that drift at session start as a nudge, never as a block.

## Setup

1. Seed the baseline from your current settings:
   - Copy `templates/hooks-baseline.json.template` to `.claude/hooks-baseline.json`.
   - Replace the `allowed` array with the exact `.command` strings already in your `.claude/settings.json`.
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

## Verifying it works

Do not trust a passing run alone (lint-green is not gate-working). Confirm both directions:
- Inject an unexpected hook command into a test `settings.json` and run `bash scripts/hook-integrity-check.sh start` with `CLAUDE_PROJECT_DIR` pointed at the test dir; it SHALL print the warning and exit 0.
- Run with a baseline that lists every live command; it SHALL print nothing and exit 0.

# Deterministic-gate hook (template, opt-in, lives in the CONSUMING product repo)

A deterministic gate runs typecheck, lint, and the changed-file tests as a script and blocks the turn until they pass. A passing gate satisfies Layer 1 of the three-layer quality gate (see `wos/gate-conditions.md` and ADR-0048), so the agent can cite the gate result instead of re-pasting each command's output per exit criterion.

This file is a TEMPLATE. It does not run in the Fhorja repo. Copy the relevant parts into the consuming product repo's `.claude/settings.json` and a small script there. Fhorja only documents the convention (it is markdown plus bash plus a small Python helper; it has no product runtime to gate).

## 1. The gate script (in the consuming repo, e.g. `scripts/wos-gate.sh`)

```bash
#!/usr/bin/env bash
# Deterministic Layer 1 gate. Exit non-zero to block; print what failed.
set -uo pipefail
fail=0
# Typecheck (adjust to the project; filter pre-existing errors with a baseline if needed)
npx tsc --noEmit || fail=1
# Lint
npm run -s lint || fail=1
# Changed-file tests (scope to the diff; full suite is fine for small repos)
npm test -- --changed || fail=1
if [[ $fail -ne 0 ]]; then
  echo "DETERMINISTIC GATE FAILED: typecheck/lint/tests must pass before the turn ends." >&2
  exit 2   # exit 2 surfaces the message to the agent (Claude Code convention)
fi
echo "deterministic gate passed"
```

## 2. Wire it as a Stop or PostToolUse hook (consuming repo `.claude/settings.json`)

```json
{
  "hooks": {
    "Stop": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "bash scripts/wos-gate.sh" } ] }
    ]
  }
}
```

Use `Stop` to gate at end-of-turn (the agent must satisfy the gate before stopping), or `PostToolUse` with an `Edit|Write` matcher to gate after each file change. `scripts/typecheck-hook.sh` in the Fhorja repo is a lighter, non-blocking PostToolUse example (it filters pre-existing errors via a `.typecheck-baseline` and surfaces only new ones).

## 3. How it satisfies Layer 1 evidence

When this gate is wired and passing, `implement-approved-slice` may record "deterministic gate passed (Stop hook)" as the Layer 1 evidence for the slice's exit criteria, rather than pasting each command's output. The gate's pass/fail is the evidence; an unwired or failing gate falls back to the explicit paste-the-command-and-output rule (W-02). Layers 2 (AI risk review) and 3 (human approval) still apply.

## 4. Bounded retry cap (required for a Stop-hook hold-until-pass loop)

A `Stop` hook that blocks until the gate passes MUST bound its retries, or a persistently failing gate loops forever. Cap consecutive blocks and escalate to the human on the cap (the same block-then-escalate rule the autonomous-run governor enforces, `wos/autonomous-track.md` D11, generalized to a normal interactive turn per `wos/gate-conditions.md`). Claude Code already overrides a Stop hook after 8 consecutive blocks; make the cap explicit so the escalation is deliberate and visible:

```bash
# Bounded retry: count consecutive blocks; escalate (stop blocking) on the cap.
GATE_CAP="${WOS_GATE_CAP:-5}"
COUNT_FILE=".wos-gate-retries"
n=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
if scripts/wos-gate.sh; then rm -f "$COUNT_FILE"; exit 0; fi   # passed: clear and allow stop
n=$((n + 1)); echo "$n" > "$COUNT_FILE"
if [ "$n" -ge "$GATE_CAP" ]; then
  echo "Gate failed $n times (cap $GATE_CAP). Escalating to human; not blocking further." >&2
  rm -f "$COUNT_FILE"; exit 0   # stop blocking; hand the decision to the human
fi
echo "Gate failed (attempt $n/$GATE_CAP); blocking turn until it passes." >&2
exit 2
```

Without the cap, a hook that always exits 2 on failure spins until the host's hard limit. The cap makes the escalation a deliberate, surfaced decision instead of a silent runaway.

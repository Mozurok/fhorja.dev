# E2E assertion scripts

One Bash script per walkthrough step. Validates artifacts + substrate writes after the human/agent runs the matching command.

## Convention

- Filename: `0N-<command>.sh` where `N` is the step number (zero-padded) and `<command>` matches the basename in `evals/e2e/walkthrough.md`.
- Source `_lib.sh` for shared helpers (file checks, section checks, K.2 header verification, validator wiring).
- Set `set -uo pipefail` (NOT `-e`, so all checks run and accumulated failures print at the end).
- Call `finish` at the end -- it prints PASS/FAIL summary and exits with the right code.

## Shipped scripts

| File | What it validates |
|---|---|
| `_lib.sh` | Shared helpers (sourced by every assertion) |
| `01-project-bootstrap.sh` | Synthetic project folder + PROJECT_CHARTER + REFERENCES |
| `09-repo-consistency-sweep.sh` | SWEEP snapshot + Pre-flight substrate audit + sweep's own K.2 dogfood (the critical assertion of the walkthrough) |

## Deferred (Phase 3)

Steps 02-08 + 10-12 will gain dedicated assertion scripts when the walkthrough is first executed end-to-end and the edge cases surface. The `_lib.sh` API already covers the primitives:
- `assert_file_exists` / `assert_dir_exists`
- `assert_section_present`
- `assert_k2_header` (inline transaction header above a section, owner-keyed)
- `assert_verification_log_valid` (runs `verify-log-validator.py`)
- `assert_substrate_drift_zero` (runs `scan-substrate-headers.sh`)
- `resolve_task_dir`
- `fail` + `pass_check` + `finish`

Adding a new assertion script is ~20 lines copied from `01-project-bootstrap.sh` with the file paths and section names swapped.

## Pattern for a new script

```bash
#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step NN: <command-name> =="
resolve_task_dir  # if the step happens after task-init

assert_file_exists     "$TASK_DIR/<artifact>.md"
assert_section_present "$TASK_DIR/<artifact>.md" "## <H2 header>"
assert_k2_header       "$TASK_DIR/<artifact>.md" "## <H2 header>" "<owner-command-name>"

finish
```

The pattern is intentionally repetitive so each assertion is self-contained and trivially readable.

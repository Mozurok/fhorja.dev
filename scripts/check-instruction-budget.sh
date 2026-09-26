#!/usr/bin/env bash
# check-instruction-budget.sh (W-15)
#
# Advisory (warn-only, NEVER fails the build) guard for always-loaded context
# files (CLAUDE.md, USER_MEMORY.md). Applies the context-rot threshold idea
# (ADR-0023) to files loaded into EVERY session, where size silently degrades
# instruction-following: Codex caps AGENTS.md at 32 KiB and truncates beyond it,
# and frontier models reliably follow only ~150-200 instructions per session.
#
# Mirrors scripts/check-natural-voice.sh: prints a single summary line and,
# under --verbose, per-file detail. ALWAYS exits 0. lint-commands.sh surfaces
# the summary line as an informational advisory; it never flips the exit code.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=0
[[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]] && VERBOSE=1

# Always-loaded root files to check. USER_MEMORY.md is gitignored/optional.
FILES=("AGENTS.md" "CLAUDE.md" "USER_MEMORY.md")

# Advisory thresholds (soft). Codex hard cap is 32 KiB; warn earlier.
MAX_BYTES=24576   # ~24 KiB
MAX_LINES=250     # CLAUDE.md guidance is to stay lean (~200 lines)

hits=0
measured=0
details=()
for f in "${FILES[@]}"; do
  path="${REPO_ROOT}/${f}"
  [[ -f "$path" ]] || continue
  measured=$((measured+1))
  bytes=$(wc -c < "$path" | tr -d ' ')
  lines=$(wc -l < "$path" | tr -d ' ')
  over=""
  (( bytes > MAX_BYTES )) && over="${over} bytes=${bytes}>${MAX_BYTES}"
  (( lines > MAX_LINES )) && over="${over} lines=${lines}>${MAX_LINES}"
  if [[ -n "$over" ]]; then
    hits=$((hits+1))
    details+=("  [instruction-budget] ${f}:${over# } (always-loaded; trim or split to protect instruction-following)")
  fi
done

# Say what was MEASURED, not only what was found. Both target files are excluded from some
# checkouts by design: USER_MEMORY.md is gitignored everywhere, and CLAUDE.md is untracked in the
# public mirror per ADR-0090. Until 2026-08-21 all three states printed the same sentence, so
# "clean" covered "measured both and both fit", "measured one", and "measured nothing at all". A
# reader had no way to tell coverage from compliance, which is the failure this line now prevents.
# This stays warn-only and still ALWAYS exits 0: the budget is a soft context-rot threshold (W-15),
# and lint consumes this line through a grep pipeline that discards the exit code anyway. The fix is
# honesty about scope, not a new gate; treat it as advisory and do not read it as enforcement.
scope="measured ${measured} of ${#FILES[@]} always-loaded file(s)"
if (( measured == 0 )); then
  echo "Instruction-budget: not measured (none of the ${#FILES[@]} always-loaded files are present in this checkout)"
elif (( hits > 0 )); then
  echo "Instruction-budget: ${hits} advisory hit(s) (warn-only; ${scope}, over budget)"
  (( VERBOSE == 1 )) && printf '%s\n' "${details[@]}"
else
  echo "Instruction-budget: clean (warn-only; ${scope}, within budget)"
fi
exit 0

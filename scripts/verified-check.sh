#!/usr/bin/env bash
# verified-check.sh: run a check against a case it should PASS and a case it should
# FAIL, and refuse to print PASS unless both behaved.
#
# WHY THIS EXISTS. The dominant failure mode in this repository is not a check that
# is wrong, it is a check that cannot fail. Measured on 2026-09-16, six broken checks
# in one session: every one produced PASS and not one ever produced a false alarm.
# Measured again on 2026-09-17 across five loop iterations, four more: a grep that
# counted a shared block synced into 89 command files and reported 89 readers; a
# coverage fixture written as a markdown table against a contract that specifies
# bullets, which reported zero rows; a corpus scan that read table rows only and
# concluded a tag had near-zero adoption when 103 files carry it; and a section
# counter that called a one-word correct answer an empty section. All four returned
# a plausible number. None ever raised a false alarm. That asymmetry IS the signature.
#
# The fix is not discipline, which was already written down in three places and
# violated anyway. It is to make the correct path the cheap path: one command that
# runs both directions and prints both exit codes, so producing the evidence costs
# less than skipping it.
#
# USAGE
#   verified-check.sh "<label>" --good "<cmd>" --bad "<cmd>" [--bad-expect "<substring>"]
#
#   --good        a command that MUST exit 0. The real case.
#   --bad         a command that MUST exit non-zero. The case you know should be
#                 rejected. Without this the run is refused; there is no one-sided mode.
#   --bad-expect  optional substring the bad case's output must contain, so a check
#                 that fails for an unrelated reason (a typo in the path, a missing
#                 fixture) does not read as the check biting.
#
# Exit 0 only when both directions behaved. Exit 1 otherwise, naming which side.
set -uo pipefail

LABEL="${1:-}"; shift || true
GOOD=""; BAD=""; BAD_EXPECT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --good) GOOD="${2:-}"; shift 2 ;;
    --bad) BAD="${2:-}"; shift 2 ;;
    --bad-expect) BAD_EXPECT="${2:-}"; shift 2 ;;
    *) echo "verified-check: unknown argument $1" >&2; exit 2 ;;
  esac
done

[ -n "$LABEL" ] || { echo "verified-check: a label is required" >&2; exit 2; }
[ -n "$GOOD" ] || { echo "verified-check: --good is required" >&2; exit 2; }
if [ -z "$BAD" ]; then
  echo "REFUSED  ${LABEL}"
  echo "         no --bad case given. A check with no case it rejects is not evidence."
  echo "         Name the input you know it should refuse, or write 'not verified' instead of PASS."
  exit 1
fi

OUT_G="$(eval "$GOOD" 2>&1)"; RC_G=$?
OUT_B="$(eval "$BAD" 2>&1)"; RC_B=$?

printf 'good exit=%d   bad exit=%d\n' "$RC_G" "$RC_B"

problems=""
[ "$RC_G" -eq 0 ] || problems="${problems}
         the good case did not pass (exit ${RC_G}): ${GOOD}
         $(printf '%s' "$OUT_G" | tail -3 | sed 's/^/           /')"
[ "$RC_B" -ne 0 ] || problems="${problems}
         the bad case PASSED (exit 0), so this check cannot fail: ${BAD}"
if [ -n "$BAD_EXPECT" ] && [ "$RC_B" -ne 0 ]; then
  printf '%s' "$OUT_B" | grep -qF -- "$BAD_EXPECT" \
    || problems="${problems}
         the bad case failed, but not for the stated reason (no ${BAD_EXPECT} in its output)"
fi

if [ -z "$problems" ]; then
  echo "PASS     ${LABEL}"
  exit 0
fi
echo "REFUSED  ${LABEL}${problems}"
exit 1

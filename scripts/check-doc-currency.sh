#!/usr/bin/env bash
# check-doc-currency.sh: is any doc that cites an external source past its own declared refresh cadence?
#
# WHY. `wos/model-routing.md` declares a 6-week refresh and writes its own diagnosis,
# "stale SKUs degrade the routing more than no routing at all". On 2026-09-17 that
# sentence had been true in the file since 2026-07-11 while the table recommended four
# SKUs the vendor had moved past, 9.6 weeks past the cadence, with nothing measuring it.
# A cadence in prose is a cadence nobody keeps.
#
# ADVISORY BY DESIGN, and that is a decision rather than timidity. A date-triggered
# hard failure breaks CI on a Tuesday with no code change, which teaches people to
# bypass the gate rather than update the table. The line names the exact age and the
# exact last-scan date so it is actionable without being coercive.
#
# USAGE: check-doc-currency.sh [--days N]
#
# A doc opts in by carrying two machine-readable lines:
#   Last scanned: YYYY-MM-DD
#   Cadence: N weeks
# Every wos/*.md is scanned; one carrying neither line is not a finding, because
# most of them cite nothing external and a cadence would be noise there.
# Always exits 0. Prints one `Model-routing:` line.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FILES="$(ls "$ROOT"/wos/*.md 2>/dev/null)"

OVERRIDE=""
[ "${1:-}" = "--days" ] && OVERRIDE="${2:-}"

epoch_of() {
  # date(1) differs between BSD and GNU; try both rather than assuming the platform.
  date -j -f "%Y-%m-%d" "$1" "+%s" 2>/dev/null || date -d "$1" "+%s" 2>/dev/null
}

NOW_S="$(date "+%s")"
scanned=0; stale=0; worst=""; worst_age=-1; worst_file=""; worst_last=""; worst_weeks=""

for f in $FILES; do
  [ -f "$f" ] || continue
  LAST="$(grep -m1 -E '^Last scanned: [0-9]{4}-[0-9]{2}-[0-9]{2}$' "$f" | awk '{print $3}')"
  WEEKS="$(grep -m1 -E '^Cadence: [0-9]+ weeks$' "$f" | awk '{print $2}')"
  [ -n "$LAST" ] && [ -n "$WEEKS" ] || continue
  LAST_S="$(epoch_of "$LAST")"
  [ -n "$LAST_S" ] || continue
  scanned=$((scanned + 1))
  AGE_D=$(( (NOW_S - LAST_S) / 86400 ))
  LIMIT_D=$(( WEEKS * 7 ))
  [ -n "$OVERRIDE" ] && LIMIT_D="$OVERRIDE"
  if [ "$AGE_D" -gt "$LIMIT_D" ]; then
    stale=$((stale + 1))
    OVER=$(( AGE_D - LIMIT_D ))
    if [ "$OVER" -gt "$worst_age" ]; then
      worst_age="$OVER"; worst_file="${f#"$ROOT"/}"; worst_last="$LAST"; worst_weeks="$WEEKS"
    fi
  fi
done

if [ "$scanned" -eq 0 ]; then
  echo "Doc-currency: not measured (no wos/*.md declares 'Last scanned:' and 'Cadence:')"
  exit 0
fi

if [ "$stale" -gt 0 ]; then
  echo "Doc-currency: ${stale} of ${scanned} dated doc(s) past cadence; oldest ${worst_file} (${worst_last}, ${worst_age}d past its ${worst_weeks}-week cadence) (advisory; reopen the source named in the file and move its Last scanned line)"
else
  echo "Doc-currency: ${scanned} dated doc(s), all within their declared cadence (advisory)"
fi
exit 0

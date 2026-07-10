#!/usr/bin/env bash
# build-eval-portfolio.sh - Aggregate per-skill benchmark.json files into a portfolio Markdown.
#
# Per K.7 (joint J.11), Epic K v2.1. Format per _internal/eval-dashboard/README.md.
#
# Reads:
#   evals/workspace/<skill-name>-workspace/iteration-<N>/benchmark.json
#
# Writes:
#   _internal/eval-dashboard/portfolio-<YYYY-MM-DD>.md (default)
#
# Usage:
#   bash scripts/build-eval-portfolio.sh [--output <path>] [--date <YYYY-MM-DD>]

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- dep check ---
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required but not installed." >&2
  exit 1
fi

# --- arg parsing ---
OUTPUT=""
DATE_OVERRIDE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="$2"; shift 2 ;;
    --date)   DATE_OVERRIDE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash scripts/build-eval-portfolio.sh [--output <path>] [--date <YYYY-MM-DD>]"
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg $1" >&2
      echo "Usage: bash scripts/build-eval-portfolio.sh [--output <path>] [--date <YYYY-MM-DD>]" >&2
      exit 1
      ;;
  esac
done

TODAY="${DATE_OVERRIDE:-$(date +%Y-%m-%d)}"
DASHBOARD_DIR="$REPO_ROOT/_internal/eval-dashboard"
if [[ -z "$OUTPUT" ]]; then
  OUTPUT="$DASHBOARD_DIR/portfolio-$TODAY.md"
fi

mkdir -p "$(dirname "$OUTPUT")"

# --- enumerate benchmark.json files ---
shopt -s nullglob
BENCHMARKS=( "$REPO_ROOT"/evals/workspace/*-workspace/iteration-*/benchmark.json )
shopt -u nullglob

if [[ ${#BENCHMARKS[@]} -eq 0 ]]; then
  echo "no benchmarks found; portfolio not generated" >&2
  exit 0
fi

# --- group by skill, pick highest iteration; also count iterations per skill ---
# Build a temp index: lines of "<skill>\t<iteration>\t<path>"
INDEX_FILE=$(mktemp)
trap 'rm -f "$INDEX_FILE" "$INDEX_FILE.sorted" "$INDEX_FILE.latest"' EXIT

for BFILE in "${BENCHMARKS[@]}"; do
  SKILL=$(jq -r '.skill_name // empty' "$BFILE" 2>/dev/null)
  ITER=$(jq -r '.iteration // empty' "$BFILE" 2>/dev/null)
  if [[ -z "$SKILL" || -z "$ITER" ]]; then
    continue
  fi
  printf '%s\t%s\t%s\n' "$SKILL" "$ITER" "$BFILE" >> "$INDEX_FILE"
done

if [[ ! -s "$INDEX_FILE" ]]; then
  echo "no benchmarks found; portfolio not generated" >&2
  exit 0
fi

# Sort by skill ASC, iteration DESC -- so first row per skill is latest
sort -t$'\t' -k1,1 -k2,2nr "$INDEX_FILE" > "$INDEX_FILE.sorted"

# Pick one row per skill (the latest iteration) AND remember iteration count
awk -F'\t' '
  { count[$1]++; if (!(($1) in latest_iter)) { latest_iter[$1]=$2; latest_path[$1]=$3 } }
  END {
    for (s in latest_iter) print s "\t" latest_iter[s] "\t" latest_path[s] "\t" count[s]
  }
' "$INDEX_FILE.sorted" | sort -t$'\t' -k1,1 > "$INDEX_FILE.latest"

# --- helpers ---
# format integer (possibly negative) tokens count -> "+1.2k" / "-450" / "0"
fmt_tokens() {
  awk -v n="$1" 'BEGIN {
    sign = "";
    if (n > 0) sign = "+";
    else if (n < 0) sign = "-";
    a = (n < 0) ? -n : n;
    if (a >= 1000) {
      printf "%s%.1fk", sign, a/1000.0;
    } else {
      printf "%s%d", sign, a;
    }
  }'
}

# format duration delta in seconds -> "+45s", "-3m"
fmt_duration() {
  awk -v n="$1" 'BEGIN {
    sign = "";
    if (n > 0) sign = "+";
    else if (n < 0) sign = "-";
    a = (n < 0) ? -n : n;
    if (a >= 60) {
      printf "%s%.0fm", sign, a/60.0;
    } else {
      printf "%s%.0fs", sign, a;
    }
  }'
}

# format pass_rate delta with sign -> "+0.20", "-0.10", "0.00"
fmt_delta_pr() {
  awk -v n="$1" 'BEGIN {
    sign = "";
    if (n > 0) sign = "+";
    else if (n < 0) sign = "-";
    a = (n < 0) ? -n : n;
    printf "%s%.2f", sign, a;
  }'
}

fmt_pass_rate() {
  awk -v n="$1" 'BEGIN { printf "%.2f", n }'
}

# --- write portfolio ---
TMP_OUT=$(mktemp)
trap 'rm -f "$INDEX_FILE" "$INDEX_FILE.sorted" "$INDEX_FILE.latest" "$TMP_OUT"' EXIT

{
  echo "# Skill eval portfolio ($TODAY)"
  echo
  echo "| skill | latest iter | pass_rate (with) | Δ pass_rate | Δ duration | Δ tokens_out | verdict |"
  echo "|---|---|---|---|---|---|---|"
} > "$TMP_OUT"

COUNT_SKILLS=0
COUNT_IMPROVING=0
COUNT_FLAT=0
COUNT_REGRESSING=0
COUNT_SEED=0

while IFS=$'\t' read -r SKILL ITER BPATH ITERCOUNT; do
  [[ -z "$SKILL" ]] && continue
  COUNT_SKILLS=$((COUNT_SKILLS + 1))

  # Extract fields from benchmark.json
  WITH_PR=$(jq -r '.summary.with_skill.pass_rate // 0' "$BPATH")
  D_PR=$(jq -r '.summary.delta.pass_rate // 0' "$BPATH")
  D_DUR=$(jq -r '.summary.delta.duration_seconds // 0' "$BPATH")
  D_TOK=$(jq -r '.summary.delta.tokens_output // 0' "$BPATH")
  WS_TOK=$(jq -r '.summary.without_skill.total_tokens_output // 0' "$BPATH")

  # Determine verdict
  if [[ "$ITERCOUNT" -lt 2 ]]; then
    VERDICT="seed"
    COUNT_SEED=$((COUNT_SEED + 1))
    PR_CELL=$(fmt_pass_rate "$WITH_PR")
    DPR_CELL="n/a (baseline)"
    DDUR_CELL="n/a"
    DTOK_CELL="n/a"
  else
    # Compute verdict per README rules
    VERDICT=$(awk -v dpr="$D_PR" -v dtok="$D_TOK" -v wstok="$WS_TOK" 'BEGIN {
      # thresholds based on without_skill total_tokens_output
      if (wstok > 0) {
        pct = (dtok < 0 ? -dtok : dtok) / wstok;
        pct_signed = dtok / wstok;
      } else {
        pct = 0; pct_signed = 0;
      }
      # regressing: dpr < 0 OR dtok > 25% of wstok
      if (dpr < 0) { print "regressing"; exit }
      if (wstok > 0 && pct_signed > 0.25) { print "regressing"; exit }
      # improving: dpr > 0 OR (dpr == 0 AND dtok < 0)
      if (dpr > 0) { print "improving"; exit }
      if (dpr == 0 && dtok < 0) { print "improving"; exit }
      # flat: dpr == 0 AND |dtok| < 10% of wstok
      if (dpr == 0 && (wstok == 0 || pct < 0.10)) { print "flat"; exit }
      # fallback (e.g. dpr == 0, dtok positive but < 25%) -> flat-ish; treat as flat per spirit
      print "flat";
    }')

    case "$VERDICT" in
      improving)  COUNT_IMPROVING=$((COUNT_IMPROVING + 1)) ;;
      flat)       COUNT_FLAT=$((COUNT_FLAT + 1)) ;;
      regressing) COUNT_REGRESSING=$((COUNT_REGRESSING + 1)) ;;
    esac

    PR_CELL=$(fmt_pass_rate "$WITH_PR")
    DPR_CELL=$(fmt_delta_pr "$D_PR")
    DDUR_CELL=$(fmt_duration "$D_DUR")
    DTOK_CELL=$(fmt_tokens "$D_TOK")
  fi

  printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
    "$SKILL" "$ITER" "$PR_CELL" "$DPR_CELL" "$DDUR_CELL" "$DTOK_CELL" "$VERDICT" \
    >> "$TMP_OUT"
done < "$INDEX_FILE.latest"

{
  echo
  echo "Per \`_internal/eval-dashboard/README.md\`. Generated $TODAY by scripts/build-eval-portfolio.sh."
} >> "$TMP_OUT"

mv "$TMP_OUT" "$OUTPUT"

# --- stdout summary ---
echo "skills aggregated: $COUNT_SKILLS"
echo "output: $OUTPUT"
echo "$COUNT_IMPROVING improving, $COUNT_FLAT flat, $COUNT_REGRESSING regressing, $COUNT_SEED seed"

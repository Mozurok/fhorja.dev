#!/usr/bin/env bash
# rank-learnings.sh - read-only retrieval ranker for Fhorja LEARNINGS.md entries.
#
# The consume side of ADR-0017 (task-init reads prior LEARNINGS) made concrete
# per ADR-0071. Given a keywords/objective string and a project path (or a direct
# LEARNINGS.md path), it scans every LEARNINGS.md entry, scores each by recency
# (parsed from the `## YYYY-MM-DD` header) plus tag/keyword overlap (the `Tags:`
# line and the Tried / Failed because / Next time bullets), and prints the top N
# as a markdown block that task-init can drop inline into its handoff.
#
# No vector store and no embeddings: ripgrep-optional, plain grep + bash only.
#
# Usage:
#   rank-learnings.sh "KEYWORDS OR OBJECTIVE" [PROJECT_DIR_OR_LEARNINGS_FILE] [TOP_N]
#   - KEYWORDS: free text; split on commas and whitespace, matched case-insensitively.
#   - Target (arg 2) may be a single LEARNINGS.md file or a directory; a directory
#     is walked for every LEARNINGS.md under it (active/ and archive/ alike).
#     Defaults to $WOS_TASKS_ROOT, else $CLAUDE_PROJECT_DIR/projects, else ./projects.
#   - TOP_N (arg 3) caps the ranked block; defaults to $RANK_LEARNINGS_TOP_N, else 5.
#   - "Today" for the recency score comes from $RANK_LEARNINGS_TODAY (YYYY-MM-DD)
#     when set, else `date +%Y-%m-%d`. Date is deterministic, so an env override
#     keeps the ranker reproducible.
#
# Graceful and advisory: an entry with no `Tags:` line is treated as low-relevance
# (body overlap only, no tag bonus), never a crash. A trailing
# "RANK-LEARNINGS: R ranked / S scanned" line lets callers grep the result. This
# command reads only; it never writes a LEARNINGS.md. It always exits 0.

# No `set -e`: this ranker is advisory and must always exit 0.
set -uo pipefail

kw_string="${1:-}"
target="${2:-${WOS_TASKS_ROOT:-${CLAUDE_PROJECT_DIR:-.}/projects}}"
top_n="${3:-${RANK_LEARNINGS_TOP_N:-5}}"
[[ "$top_n" =~ ^[0-9]+$ ]] || top_n=5

today="${RANK_LEARNINGS_TODAY:-$(date +%Y-%m-%d 2>/dev/null || echo 1970-01-01)}"

# Regexes live in variables: bash 3.2 mis-parses a literal `=~` right-hand side
# that contains `[[:space:]]` or `[0-9]` bracket expressions.
re_iso='^([0-9]{4})-([0-9]{2})-([0-9]{2})$'
re_hdr='^##[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}'
re_hdr_cap='^##[[:space:]]*([0-9]{4})-([0-9]{2})-([0-9]{2})'

# ---------------------------------------------------------------------------
# 1. Integer-only civil-date -> day-number (Howard Hinnant's algorithm).
#    Lets us diff two dates with pure bash arithmetic, no `date -d`/`-j` split.
# ---------------------------------------------------------------------------
civil_days() { # $1=Y $2=M $3=D  -> days since 1970-01-01
  local y="$1" m="$2" d="$3" era yoe doy doe
  [[ "$m" -le 2 ]] && y=$((y - 1))
  era=$(( (y >= 0 ? y : y - 399) / 400 ))
  yoe=$(( y - era * 400 ))
  if [[ "$m" -gt 2 ]]; then doy=$(( (153 * (m - 3) + 2) / 5 + d - 1 ))
  else doy=$(( (153 * (m + 9) + 2) / 5 + d - 1 )); fi
  doe=$(( yoe * 365 + yoe / 4 - yoe / 100 + doy ))
  echo $(( era * 146097 + doe - 719468 ))
}

today_days=0
if [[ "$today" =~ $re_iso ]]; then
  today_days="$(civil_days "$((10#${BASH_REMATCH[1]}))" "$((10#${BASH_REMATCH[2]}))" "$((10#${BASH_REMATCH[3]}))")"
fi

# Recency score buckets: newer lessons rank higher, regardless of overlap.
recency_score() { # $1=days_ago -> 0..5
  local a="$1"
  if   [[ "$a" -le 7 ]];   then echo 5
  elif [[ "$a" -le 30 ]];  then echo 4
  elif [[ "$a" -le 90 ]];  then echo 3
  elif [[ "$a" -le 180 ]]; then echo 2
  elif [[ "$a" -le 365 ]]; then echo 1
  else echo 0; fi
}

# ---------------------------------------------------------------------------
# 2. Resolve the LEARNINGS.md files to scan.
# ---------------------------------------------------------------------------
files=()
if [[ -f "$target" ]]; then
  files+=("$target")
elif [[ -d "$target" ]]; then
  while IFS= read -r f; do files+=("$f"); done \
    < <(find "$target" -type f -name 'LEARNINGS.md' 2>/dev/null)
fi

if [[ "${#files[@]}" -eq 0 ]]; then
  echo "rank-learnings: no LEARNINGS.md found under: $target"
  echo "RANK-LEARNINGS: 0 ranked / 0 scanned"
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Normalize keywords (comma/space split, lowercased, >=2 chars).
# ---------------------------------------------------------------------------
keywords=()
while IFS= read -r kw; do
  [[ -n "$kw" ]] || continue
  [[ "${#kw}" -ge 2 ]] || continue
  keywords+=("$kw")
done < <(printf '%s' "$kw_string" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9' '\n' | sort -u)

# ---------------------------------------------------------------------------
# 4. Score every entry. Scored rows land in a temp file, one per line:
#    SCORE<TAB>HEADER<TAB>TAGS<TAB>NEXT-TIME  (tabs stripped from field text).
# ---------------------------------------------------------------------------
tmp="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/rank-learnings.$$")"
trap 'rm -f "$tmp"' EXIT

scanned=0

score_entry() { # $1 = one entry's raw lines (header first)
  local buf="$1" header y m d days_ago rscore oscore total
  local tags_line next_line body kw
  header="$(printf '%s\n' "$buf" | head -n 1)"
  # Header must carry a real ISO date; skip malformed entries gracefully.
  if [[ ! "$header" =~ $re_hdr_cap ]]; then
    return 0
  fi
  scanned=$((scanned + 1))
  y="$((10#${BASH_REMATCH[1]}))"; m="$((10#${BASH_REMATCH[2]}))"; d="$((10#${BASH_REMATCH[3]}))"
  days_ago=$(( today_days - $(civil_days "$y" "$m" "$d") ))
  [[ "$days_ago" -lt 0 ]] && days_ago=0
  rscore="$(recency_score "$days_ago")"

  # Strip the leading "- " so the ranked block does not print a doubled dash.
  tags_line="$(printf '%s\n' "$buf" | grep -iE '^[[:space:]]*-[[:space:]]*Tags:' | head -n 1 | sed -E 's/^[[:space:]]*-[[:space:]]*//' | tr '\t' ' ')"
  next_line="$(printf '%s\n' "$buf" | grep -iE '^[[:space:]]*-[[:space:]]*Next time:' | head -n 1 | sed -E 's/^[[:space:]]*-[[:space:]]*//' | tr '\t' ' ')"
  # Body considered for keyword overlap: Tags + Tried + Failed because + Next time.
  body="$(printf '%s\n' "$buf" | grep -iE '^[[:space:]]*-[[:space:]]*(Tags|Tried|Failed because|Next time):' | tr 'A-Z' 'a-z')"

  # Overlap: a keyword on the Tags line scores 2, elsewhere in the body scores 1.
  oscore=0
  for kw in ${keywords[@]+"${keywords[@]}"}; do
    if [[ -n "$tags_line" ]] && printf '%s' "$tags_line" | tr 'A-Z' 'a-z' | grep -qF "$kw"; then
      oscore=$((oscore + 2))
    elif printf '%s' "$body" | grep -qF "$kw"; then
      oscore=$((oscore + 1))
    fi
  done

  total=$((rscore + oscore))
  printf '%s\t%s\t%s\t%s\n' \
    "$total" \
    "$(printf '%s' "$header" | sed -E 's/^#+[[:space:]]*//' | tr '\t' ' ')" \
    "${tags_line:-(no tags)}" \
    "${next_line:-(no Next time bullet)}" >> "$tmp"
}

for f in ${files[@]+"${files[@]}"}; do
  # Split the file into per-entry blocks on `## YYYY-...` headers via awk, then
  # feed each block to score_entry. Files are small; a line loop is fine.
  entry=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ $re_hdr ]]; then
      [[ -n "$entry" ]] && score_entry "$entry"
      entry="$line"$'\n'
    else
      [[ -n "$entry" ]] && entry="$entry$line"$'\n'
    fi
  done < "$f"
  [[ -n "$entry" ]] && score_entry "$entry"
done

# ---------------------------------------------------------------------------
# 5. Emit the capped ranked markdown block (highest score first).
# ---------------------------------------------------------------------------
ranked=0
echo "### Relevant prior lessons (ranked)"
echo
if [[ -s "$tmp" ]]; then
  while IFS=$'\t' read -r score header tags next; do
    ranked=$((ranked + 1))
    echo "- ${header} (score ${score})"
    echo "  - ${tags}"
    echo "  - ${next}"
  done < <(sort -t$'\t' -k1,1nr "$tmp" | head -n "$top_n")
fi
[[ "$ranked" -eq 0 ]] && echo "- (no matching prior lessons)"

echo
echo "RANK-LEARNINGS: $ranked ranked / $scanned scanned"
exit 0

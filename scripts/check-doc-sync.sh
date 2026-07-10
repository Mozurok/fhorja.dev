#!/usr/bin/env bash
# check-doc-sync.sh -- Fhorja doc-sync validator
#
# Scans curated doc surfaces for references to commands, ADRs, and wos topics
# and verifies that each referenced artifact exists on disk.
#
# Usage:
#   scripts/check-doc-sync.sh [--verbose] [--strict]
#
# Exit codes:
#   0  all refs resolved (or only warnings in non-strict mode)
#   1  one or more broken refs (or warnings in --strict mode)

set -u

VERBOSE=0
STRICT=0

for arg in "$@"; do
  case "$arg" in
    --verbose) VERBOSE=1 ;;
    --strict)  STRICT=1  ;;
    -h|--help)
      echo "Usage: $0 [--verbose] [--strict]"
      exit 0
      ;;
    *)
      echo "doc-sync: unknown flag: $arg" >&2
      exit 2
      ;;
  esac
done

# Resolve repo root from this script's location.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT" || exit 2

COMMANDS_DIR="commands"
ADR_DIR="docs/adr"
WOS_DIR="wos"

# Curated scan surfaces. Missing files are skipped silently.
SURFACES="
CLAUDE.md
README.md
docs/FAQ.md
docs/MIGRATION.md
ROADMAP.md
WORKFLOW_OPERATING_SYSTEM.md
"

VERIFIED=0
BROKEN=0
WARNINGS=0
BROKEN_LINES=""
WARN_LINES=""

log_verbose() {
  if [ "$VERBOSE" -eq 1 ]; then
    echo "doc-sync: checked $1"
  fi
}

record_broken() {
  # $1=file $2=line-no $3=ref $4=kind
  BROKEN=$((BROKEN + 1))
  BROKEN_LINES="${BROKEN_LINES}doc-sync: BROKEN $4 ref '$3' in $1:$2
"
}

record_warning() {
  WARNINGS=$((WARNINGS + 1))
  WARN_LINES="${WARN_LINES}doc-sync: WARN  $2 in $1
"
}

command_exists() {
  name="$1"
  if [ -f "$COMMANDS_DIR/$name.md" ]; then
    return 0
  fi
  if [ -f "$COMMANDS_DIR/$name/SKILL.md" ]; then
    return 0
  fi
  return 1
}

adr_exists() {
  num="$1"
  # Match docs/adr/NNNN-*.md
  for f in "$ADR_DIR/$num"-*.md; do
    [ -f "$f" ] && return 0
  done
  return 1
}

wos_topic_exists() {
  topic="$1"
  [ -f "$WOS_DIR/$topic.md" ]
}

scan_file() {
  file="$1"
  [ -f "$file" ] || return 0

  # 1. Command refs: backtick-wrapped tokens like `command-name`.
  #    Heuristic: lowercase, digits, hyphens; len 2..64; no slashes/dots.
  awk '
    {
      line = $0
      lineno = NR
      while (match(line, /`[a-z][a-z0-9-]+`/)) {
        tok = substr(line, RSTART + 1, RLENGTH - 2)
        print "CMD\t" lineno "\t" tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file" | while IFS=$(printf '\t') read -r kind lineno tok; do
    [ -z "$tok" ] && continue
    if command_exists "$tok"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno command '$tok'"
      echo "OK"
    else
      # Could be a shell command (`ls`, `grep`) -- treat as unknown shape.
      if [ "$STRICT" -eq 1 ]; then
        echo "WARN $file:$lineno unknown backtick token '$tok'"
      fi
    fi
  done >/dev/null 2>&1 || true

  # Re-run command scan in current shell so counters update.
  while IFS=$(printf '\t') read -r kind lineno tok; do
    [ -z "$tok" ] && continue
    if command_exists "$tok"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno command '$tok'"
    else
      # Unknown backtick token: shell command, code symbol, or broken ref.
      # Only flag as warning in --strict mode.
      if [ "$STRICT" -eq 1 ]; then
        record_warning "$file:$lineno" "unknown backtick token '$tok' (not a registered command)"
      fi
    fi
  done <<EOF
$(awk '
    {
      line = $0
      lineno = NR
      while (match(line, /`[a-z][a-z0-9-]+`/)) {
        tok = substr(line, RSTART + 1, RLENGTH - 2)
        print "CMD\t" lineno "\t" tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file")
EOF

  # 2. ADR refs: ADR-NNNN or [NNNN](./docs/adr/...) or (docs/adr/NNNN-...).
  while IFS=$(printf '\t') read -r lineno num; do
    [ -z "$num" ] && continue
    if adr_exists "$num"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno ADR-$num"
    else
      record_broken "$file" "$lineno" "ADR-$num" "ADR"
    fi
  done <<EOF
$(awk '
    {
      line = $0
      lineno = NR
      # ADR-NNNN style
      tmp = line
      while (match(tmp, /ADR-[0-9][0-9][0-9][0-9]/)) {
        num = substr(tmp, RSTART + 4, 4)
        print lineno "\t" num
        tmp = substr(tmp, RSTART + RLENGTH)
      }
      # docs/adr/NNNN- style paths
      tmp = line
      while (match(tmp, /docs\/adr\/[0-9][0-9][0-9][0-9]-/)) {
        num = substr(tmp, RSTART + 9, 4)
        print lineno "\t" num
        tmp = substr(tmp, RSTART + RLENGTH)
      }
    }
  ' "$file" | sort -u)
EOF

  # 3. wos topic refs: wos/<topic>.md
  while IFS=$(printf '\t') read -r lineno topic; do
    [ -z "$topic" ] && continue
    if wos_topic_exists "$topic"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno wos/$topic.md"
    else
      record_broken "$file" "$lineno" "wos/$topic.md" "wos-topic"
    fi
  done <<EOF
$(awk '
    {
      line = $0
      lineno = NR
      while (match(line, /wos\/[a-z0-9-]+\.md/)) {
        ref = substr(line, RSTART, RLENGTH)
        # Strip "wos/" prefix and ".md" suffix
        topic = substr(ref, 5, length(ref) - 7)
        print lineno "\t" topic
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file" | sort -u)
EOF
}

for surface in $SURFACES; do
  scan_file "$surface"
done

# Emit results.
if [ -n "$WARN_LINES" ]; then
  printf "%s" "$WARN_LINES"
fi

if [ "$BROKEN" -gt 0 ]; then
  printf "%s" "$BROKEN_LINES"
  echo "doc-sync: $VERIFIED refs verified, $BROKEN broken, $WARNINGS warnings"
  exit 1
fi

if [ "$STRICT" -eq 1 ] && [ "$WARNINGS" -gt 0 ]; then
  echo "doc-sync: $VERIFIED refs verified, 0 broken, $WARNINGS warnings (strict)"
  exit 1
fi

echo "doc-sync: $VERIFIED refs verified, 0 broken"
exit 0

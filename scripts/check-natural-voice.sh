#!/usr/bin/env bash
# check-natural-voice.sh -- Fhorja natural-voice advisory scanner (warn-only)
#
# Flags the common "AI tells" in human-facing Fhorja prose so generated output
# and the rule sources read like a person wrote them. ADVISORY ONLY: this
# never fails a build and never exits non-zero on hits. The canonical rule is
# in wos/natural-voice.md and WORKFLOW_OPERATING_SYSTEM.md ->
# `## Global output contract` -> `### Natural voice (no AI tells)`.
#
# Categories (all advisory):
#   slash        spaced slash disjunctions in prose (a / b / c) and "and/or"
#   parallelism  "not just X, but Y" / "rather than just" / "it's not about"
#   vocab        leverage, utilize, seamless, robust, comprehensive, crucial, delve, ...
#   emoji        any emoji codepoint (needs python3; skipped if absent)
#
# Precision: before matching, each line has its fenced code blocks and inline
# `code` spans removed. Repo conventions keep enums (`LOW/MEDIUM/HIGH`), paths,
# CLI flags, and pipe-separated mode templates (`Ask | Plan | Agent`) inside
# backticks, so they are exempt automatically. Only bare prose is scanned.
# wos/natural-voice.md is excluded entirely: it is the catalog of examples.
#
# Usage:
#   scripts/check-natural-voice.sh [--verbose] [--strict]
#
# Summary line (parsed by lint-commands.sh):
#   "Natural-voice: N advisory hit(s) across F file(s)"
#
# Exit code: always 0 (advisory). --strict is accepted for flag compatibility
# but does not change the exit code; promotion to fail-fast is a future change.

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
      echo "natural-voice: unknown flag: $arg" >&2
      exit 2
      ;;
  esac
done

# Resolve repo root from this script's location.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT" || exit 2

# --- Files to scan ----------------------------------------------------------
# Command bodies, lazy wos topics, and the human-facing root/docs surfaces.
# wos/natural-voice.md is the example catalog and is excluded.
SCAN_FILES=()
for f in commands/*.md; do [[ -f "$f" ]] && SCAN_FILES+=("$f"); done
for f in wos/*.md; do
  [[ -f "$f" ]] || continue
  [[ "$f" == "wos/natural-voice.md" ]] && continue
  SCAN_FILES+=("$f")
done
for f in \
  WORKFLOW_OPERATING_SYSTEM.md \
  CLAUDE.md \
  README.md \
  COMMAND_PROMPT_STUBS.md \
  CONTRIBUTING.md \
  docs/FAQ.md \
  docs/MIGRATION.md; do
  [[ -f "$f" ]] && SCAN_FILES+=("$f")
done

# --- Patterns (ERE, matched case-insensitively) -----------------------------
# Slash: only the unambiguous "and/or" is auto-flagged. The spaced-slash prose
# tell ("Slack / Discord / Teams") shares its exact shape with this repo's
# deliberate terse-enum convention in spec bodies ("atom / molecule / organism",
# "ADDED / RENAMED / DEPRECATED", verdict scales). Auto-flagging it floods with
# legitimate hits, so the spaced-slash rule is applied by human judgment in
# generated-output prose (see wos/natural-voice.md), not by the scanner.
RE_SLASH="(^|[^[:alnum:]])and/or([^[:alnum:]]|$)"
RE_PARALLEL="not just [^.]{1,40} but|not only [^.]{1,40} but|rather than (just|merely)|more than just|it'?s not about|isn'?t (just|about)|is not (just|about)"
RE_VOCAB="\b(leverage|leverages|leveraging|leveraged|utilize|utilizes|utilizing|utilized|seamless|seamlessly|comprehensive|comprehensively|robust|crucial|delve|delves|delving|delved|moreover|furthermore)\b|it'?s worth noting|worth noting that|needless to say"

# strip_code: remove fenced blocks and inline backtick spans, preserving line
# numbering 1:1 so grep -n reports the real line.
strip_code() {
  awk '
    BEGIN { fence = 0 }
    /^[[:space:]]*```/ { fence = !fence; print ""; next }
    {
      if (fence) { print ""; next }
      g = $0
      gsub(/`[^`]*`/, "", g)
      print g
    }
  ' "$1"
}

scan_category() {
  # $1=regex  -> prints "file:lineno:content" for each hit across SCAN_FILES
  local re="$1" f stripped
  for f in "${SCAN_FILES[@]}"; do
    stripped="$(strip_code "$f")"
    printf '%s\n' "$stripped" | grep -nEi "$re" 2>/dev/null \
      | sed "s#^#${f}:#" || true
  done
}

scan_emoji() {
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "${SCAN_FILES[@]}" <<'PY'
import re, sys
# Emoji blocks only. Arrows (U+2190-21FF) and dingbat check marks are excluded
# on purpose: Fhorja uses -> arrows and ASCII checklists legitimately.
pat = re.compile(
    "[\U0001F300-\U0001FAFF"   # symbols, pictographs, supplemental, extended-A
    "\U0001F000-\U0001F0FF"    # mahjong, dominoes, playing cards
    "\U0001F1E6-\U0001F1FF"    # regional indicators / flags
    "\U00002600-\U000026FF"    # miscellaneous symbols
    "\U0000FE0F]"              # emoji variation selector
)
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if pat.search(line):
                    print(f"{path}:{n}:{line.rstrip()}")
    except (OSError, UnicodeDecodeError):
        continue
PY
}

SLASH_HITS="$(scan_category "$RE_SLASH")"
PARALLEL_HITS="$(scan_category "$RE_PARALLEL")"
VOCAB_HITS="$(scan_category "$RE_VOCAB")"
EMOJI_HITS="$(scan_emoji)"

count_lines() { [[ -z "$1" ]] && { echo 0; return; }; printf '%s\n' "$1" | grep -c . ; }

SLASH_N="$(count_lines "$SLASH_HITS")"
PARALLEL_N="$(count_lines "$PARALLEL_HITS")"
VOCAB_N="$(count_lines "$VOCAB_HITS")"
EMOJI_N="$(count_lines "$EMOJI_HITS")"
TOTAL=$((SLASH_N + PARALLEL_N + VOCAB_N + EMOJI_N))

ALL_HITS="$(printf '%s\n%s\n%s\n%s\n' "$SLASH_HITS" "$PARALLEL_HITS" "$VOCAB_HITS" "$EMOJI_HITS" | grep -c . || true)"
FILES="$(printf '%s\n%s\n%s\n%s\n' "$SLASH_HITS" "$PARALLEL_HITS" "$VOCAB_HITS" "$EMOJI_HITS" \
  | grep -E '^[^:]+:[0-9]+:' | cut -d: -f1 | sort -u | grep -c . || true)"

echo "Natural-voice advisory scan (warn-only; see wos/natural-voice.md)"
printf '  %-12s %s hit(s)\n' "slash:"       "$SLASH_N"
printf '  %-12s %s hit(s)\n' "parallelism:" "$PARALLEL_N"
printf '  %-12s %s hit(s)\n' "vocab:"       "$VOCAB_N"
printf '  %-12s %s hit(s)\n' "emoji:"       "$EMOJI_N"

if [[ $VERBOSE -eq 1 && $TOTAL -gt 0 ]]; then
  echo ""
  echo "Hits (advisory; triage each, see wos/natural-voice.md for rewrites):"
  [[ -n "$SLASH_HITS"    ]] && printf '%s\n' "$SLASH_HITS"    | sed 's/^/  [slash]       /'
  [[ -n "$PARALLEL_HITS" ]] && printf '%s\n' "$PARALLEL_HITS" | sed 's/^/  [parallelism] /'
  [[ -n "$VOCAB_HITS"    ]] && printf '%s\n' "$VOCAB_HITS"    | sed 's/^/  [vocab]       /'
  [[ -n "$EMOJI_HITS"    ]] && printf '%s\n' "$EMOJI_HITS"    | sed 's/^/  [emoji]       /'
fi

echo ""
echo "Natural-voice: ${TOTAL} advisory hit(s) across ${FILES} file(s)"
exit 0

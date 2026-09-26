#!/usr/bin/env bash
# detect-workflow-prompt-too-long.sh: the detector for the workflow-prompt-too-long bug
# class (wos/bug-classes/workflow-prompt-too-long.md, Detection signals 2 and 3), graded by
# evals/scenarios/39-workflow-prompt-too-long-ci.md.
#
# No dispatch prompt lives in a file in this repository, so the caller names the directories
# that hold prompt templates. For every *.md under them (recursive), the detector removes the
# YAML front matter and every fenced code block, then checks two things independently:
#
#   1. Length. The remaining body words are counted the way `wc -w` counts them (runs of
#      non-whitespace). Over the threshold (default 600) is a finding:
#        <file>:<line>: <words> words over <threshold>
#      where <line> is the first non-blank body line after the front matter.
#   2. Tail reminder. None of the last five non-blank body lines names the typed return:
#        <file>:<line>: no typed-return reminder in the last 5 lines
#      where <line> is the last non-blank body line. The carriers recognized are the two
#      phrasings the bug class names, "Return one payload matching worker_output_schema" and
#      "Write one JSON payload matching worker_output_schema", plus any StructuredOutput
#      mention. Backticks are ignored, so `worker_output_schema` matches too.
#
# A file can yield both findings; they are reported on separate lines and never merged.
#
# Usage:  scripts/detect-workflow-prompt-too-long.sh [--threshold N] <dir> [<dir> ...]
# Exit:   0 no finding, 1 at least one finding, 2 usage error or a target that is missing,
#         not a directory, or holds no *.md file. A refused target is named on stderr and is
#         never reported as clean.
#
# Only the paths given on the command line are read. Nothing here is resolved relative to
# this script's own location.
set -uo pipefail

usage() {
  echo "usage: $0 [--threshold N] <dir> [<dir> ...]" >&2
  exit 2
}

threshold=600
dirs=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --threshold)
      [ "$#" -ge 2 ] || usage
      threshold="$2"; shift 2 ;;
    --threshold=*)
      threshold="${1#--threshold=}"; shift ;;
    -h|--help) usage ;;
    --) shift; while [ "$#" -gt 0 ]; do dirs+=("$1"); shift; done ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) dirs+=("$1"); shift ;;
  esac
done

case "$threshold" in
  ''|*[!0-9]*) echo "threshold must be a whole number, got '$threshold'" >&2; exit 2 ;;
esac
[ "${#dirs[@]}" -gt 0 ] || usage

files=()
refused=0
for d in "${dirs[@]}"; do
  if [ ! -e "$d" ]; then
    echo "refused: $d does not exist, so it was not scanned" >&2; refused=1; continue
  fi
  if [ ! -d "$d" ]; then
    echo "refused: $d is not a directory, so it was not scanned" >&2; refused=1; continue
  fi
  n=0
  while IFS= read -r -d '' f; do
    files+=("$f"); n=$((n + 1))
  done < <(find "$d" -type f -name '*.md' -print0 | LC_ALL=C sort -z)
  if [ "$n" -eq 0 ]; then
    echo "refused: $d holds no *.md file, so nothing was scanned" >&2; refused=1
  fi
done
[ "$refused" -eq 0 ] || exit 2

# One awk pass over every file. Lines are buffered per file because front matter only counts
# as front matter when it closes; an unclosed opening --- is read as body.
AWK_PROG='
function flush(   i, start, inf, words, first, nb, tail, k, hit, line, last) {
  if (fname == "") return
  start = 1
  if (nl > 0 && buf[1] ~ /^---[ \t]*$/) {
    for (i = 2; i <= nl; i++) {
      if (buf[i] ~ /^(---|\.\.\.)[ \t]*$/) { start = i + 1; break }
    }
  }
  inf = 0; words = 0; first = 0; nb = 0
  for (i = start; i <= nl; i++) {
    line = buf[i]
    if (line ~ /^[ \t]*(```|~~~)/) { inf = !inf; continue }
    if (inf) continue
    if (line ~ /^[ \t]*$/) continue
    if (first == 0) first = i
    words += split(line, _w)
    nb++; body[nb] = line; bodyline[nb] = i
  }
  if (first == 0) first = 1
  if (words > thr) printf "%s:%d: %d words over %d\n", fname, first, words, thr
  hit = 0
  tail = (nb > 5) ? nb - 4 : 1
  for (k = tail; k <= nb; k++) {
    line = body[k]; gsub(/`/, "", line)
    if (index(line, "Return one payload matching worker_output_schema") \
        || index(line, "Write one JSON payload matching worker_output_schema") \
        || index(line, "StructuredOutput")) { hit = 1; break }
  }
  last = (nb > 0) ? bodyline[nb] : 1
  if (!hit) printf "%s:%d: no typed-return reminder in the last 5 lines\n", fname, last
  delete buf; delete body; delete bodyline
}
FNR == 1 { flush(); fname = FILENAME; nl = 0 }
{ buf[++nl] = $0 }
END { flush() }
'

out=""
if [ "${#files[@]}" -gt 0 ]; then
  # awk never sees a zero-byte file (it has no first record), so those are checked here.
  nonempty=()
  for f in "${files[@]}"; do
    if [ -s "$f" ]; then nonempty+=("$f"); else
      out+="${f}:1: no typed-return reminder in the last 5 lines"$'\n'
    fi
  done
  if [ "${#nonempty[@]}" -gt 0 ]; then
    out+="$(printf '%s\0' "${nonempty[@]}" | xargs -0 awk -v thr="$threshold" "$AWK_PROG")"
  fi
fi

if [ -n "$out" ]; then
  printf '%s\n' "${out%$'\n'}"
  exit 1
fi
exit 0

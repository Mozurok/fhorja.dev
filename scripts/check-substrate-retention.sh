#!/usr/bin/env bash
# check-substrate-retention.sh [--root DIR]
#
# Measures the task substrate: how big it is, how many tasks it holds, when it was last backed
# up, and how many archived tasks sit past the declared age limit. It measures and stops there.
#
# LOCAL-ONLY BY CONSTRUCTION, for the same reason check-mcp-pins.sh is: `projects/` is gitignored
# (ADR-0007) and the sidecar this reads is gitignored too, so this never runs meaningfully in CI
# and never guards the public mirror. It guards the operator's working tree. A tree with no
# `projects/` or no sidecar reports "not measured" and NEVER "clean", because clean is a claim
# and there was nothing to measure.
#
# THREE THINGS THIS SCRIPT IS FORBIDDEN TO DO, and the exit criteria of the slice that added it
# check the third by grep: open the contents of a task file, print a project folder name (it
# would put a client name in a lint log or a paste), and copy or transmit `projects/` anywhere.
# Fhorja never copies the substrate. Choosing and paying for a backup destination, key custody,
# and deciding which archived tasks to delete are the operator's, and SECURITY.md says so.
#
# Sidecar: scripts/.substrate-retention, see .substrate-retention.example.
#   BACKUP_DEST=/path/to/backup      MAX_BACKUP_AGE_DAYS=7      ARCHIVE_MAX_AGE_DAYS=365
#
# Exit: 0 measured and within limits, or not measured. 1 backup missing or older than the
# limit. 2 usage error.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SIDECAR="${SUBSTRATE_RETENTION_FILE:-${SCRIPT_DIR}/.substrate-retention}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root) [ "$#" -ge 2 ] || { echo "usage: check-substrate-retention.sh [--root DIR]" >&2; exit 2; }
            ROOT="$2"; shift 2 ;;
    -h|--help) echo "usage: check-substrate-retention.sh [--root DIR]"; exit 0 ;;
    *) echo "usage: check-substrate-retention.sh [--root DIR]" >&2; exit 2 ;;
  esac
done

[ -d "$ROOT" ] || { echo "check-substrate-retention: not a directory: ${ROOT}" >&2; exit 2; }
SUB="${ROOT}/projects"

if [ ! -d "$SUB" ] || [ ! -f "$SIDECAR" ]; then
  echo "Substrate-retention: not measured (no projects/ or no sidecar at ${SIDECAR##*/})"
  exit 0
fi

BACKUP_DEST=""; MAX_BACKUP_AGE_DAYS=""; ARCHIVE_MAX_AGE_DAYS=""
# shellcheck disable=SC1090
. "$SIDECAR"
: "${MAX_BACKUP_AGE_DAYS:=7}"
: "${ARCHIVE_MAX_AGE_DAYS:=365}"

size="$(du -sh "$SUB" 2>/dev/null | awk '{print $1}')"
active="$(find "$SUB" -mindepth 3 -maxdepth 3 -type d -path '*/active/*' 2>/dev/null | wc -l | tr -d ' ')"
archived="$(find "$SUB" -mindepth 3 -maxdepth 3 -type d -path '*/archive/*' 2>/dev/null | wc -l | tr -d ' ')"
stale="$(find "$SUB" -mindepth 3 -maxdepth 3 -type d -path '*/archive/*' -mtime "+${ARCHIVE_MAX_AGE_DAYS}" 2>/dev/null | wc -l | tr -d ' ')"

backup_age="none"
rc=0
if [ -n "$BACKUP_DEST" ] && [ -d "$BACKUP_DEST" ]; then
  newest="$(find "$BACKUP_DEST" -type f -print0 2>/dev/null | xargs -0 stat -f '%m' 2>/dev/null | sort -rn | head -1)"
  if [ -n "$newest" ]; then
    backup_age="$(( ( $(date +%s) - newest ) / 86400 ))d"
    [ "$(( ( $(date +%s) - newest ) / 86400 ))" -gt "$MAX_BACKUP_AGE_DAYS" ] && rc=1
  else
    rc=1
  fi
else
  rc=1
fi

verdict="clean"
[ "$rc" -eq 0 ] || verdict="STALE"
echo "Substrate-retention: ${verdict} (${size}, ${active} active, ${archived} archived, ${stale} past ${ARCHIVE_MAX_AGE_DAYS}d, backup ${backup_age}, limit ${MAX_BACKUP_AGE_DAYS}d)"
exit "$rc"

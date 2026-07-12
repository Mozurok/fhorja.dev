#!/usr/bin/env bash
# scan-substrate-headers.sh -- K.4 drift-guard for repo-consistency-sweep Step 7.1
#
# Per Epic K v2.1 K.4 (joint J.5). Cutover: 2026-06-04.
#
# Scans substrate files at their CANONICAL locations (not via `git diff`, because
# substrate lives in the Fhorja task repo while code diffs live in product repos).
# For each H2 (`## `) section in each substrate file, checks whether the line
# immediately preceding the section header contains the canonical transaction
# header `<!-- wos:write owner=... section='...' run_id=... ts=... reason=... mode=... -->`
# per `commands/_shared/substrate-write-protocol.md`. Sections without a header
# count toward `substrate_header_drift_count` ONLY when the file had ANY commit
# at or after the cutover date (coarse per-file gate; pre-cutover-only files
# are valid legacy per `wos/substrate-peers.md ## Legacy file without headers`).
#
# Substrate scope (in order of enumeration):
#   1. Task-folder task-memory + task-scoped fleet-substrate
#      (TASK_STATE / DECISIONS / IMPLEMENTATION_PLAN / SOURCE_OF_TRUTH /
#       EXTERNAL_RESEARCH / VERIFICATION_LOG)
#   2. Project-folder fleet-substrate (INITIATIVE_INDEX / REFERENCES)
#   3. Product-repo fleet-substrate (ATOM_AUDIT / SCREEN_MAP / routes)
#      resolved from `SOURCE_OF_TRUTH.md ## Active codebase / repo` (single-repo)
#      or `## Repositories` (multi-repo, per `wos/multi-repo-support.md`).
#      Disable via `--include-product-repos=0` (default ON).
#
# Output:
#   stdout single line: substrate_header_drift_count: <N>
#   stderr (verbose):   per-section path + line + header text for each missing
#
# Usage:
#   bash scripts/scan-substrate-headers.sh <task-folder> [--cutoff <YYYY-MM-DD>] [--verbose] [--include-product-repos=0|1]
#   bash scripts/scan-substrate-headers.sh \
#     /path/to/repo/projects/bmazurok__foo/active/2026-06-04_bar
#
# Exit codes:
#   0 always; the count is the signal, not the exit code (informational per K.4 v2.1)

set -uo pipefail

TASK_DIR="${1:-}"
shift 2>/dev/null || true

CUTOFF="2026-06-04T00:00:00Z"
VERBOSE=0
INCLUDE_PRODUCT_REPOS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cutoff)  CUTOFF="${2}T00:00:00Z"; shift 2 ;;
    --verbose) VERBOSE=1; shift ;;
    --include-product-repos=0) INCLUDE_PRODUCT_REPOS=0; shift ;;
    --include-product-repos=1) INCLUDE_PRODUCT_REPOS=1; shift ;;
    --include-product-repos)   INCLUDE_PRODUCT_REPOS=1; shift ;;
    *)         echo "ERROR: unknown arg $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$TASK_DIR" || ! -d "$TASK_DIR" ]]; then
  echo "ERROR: task folder required as first arg (must exist)" >&2
  echo "Usage: bash scripts/scan-substrate-headers.sh <task-folder> [--cutoff YYYY-MM-DD] [--verbose] [--include-product-repos=0|1]" >&2
  exit 2
fi

TASK_DIR="$(cd "$TASK_DIR" && pwd)"
PROJECT_DIR="$(cd "$TASK_DIR/../.." && pwd)"  # active/<task>/.. -> active/ then .. -> project root

# Resolve Fhorja repo root (substrate lives inside; for git log we need the repo root)
WOS_ROOT="$(cd "$TASK_DIR" && git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$WOS_ROOT" ]]; then
  echo "ERROR: task folder is not inside a git repo (cannot run git log for cutover check)" >&2
  exit 2
fi

# Helper: resolve product-repo root paths from SOURCE_OF_TRUTH.md.
# Reads either `## Active codebase / repo` (single-repo) or `## Repositories`
# (multi-repo, per `wos/multi-repo-support.md`). For multi-repo, parses each
# `path:` line under the section. Expands a leading `~` to $HOME. Emits one
# absolute repo-root path per line on stdout. Empty output = no product repos
# resolved (e.g. SOURCE_OF_TRUTH.md missing, or sections absent).
resolve_product_repo_paths() {
  local sot="$TASK_DIR/SOURCE_OF_TRUTH.md"
  [[ -f "$sot" ]] || return 0

  # Detect multi-repo first; if `## Repositories` exists, prefer it.
  if grep -qE '^## Repositories\b' "$sot"; then
    [[ $VERBOSE -eq 1 ]] && echo "(multi-repo: scanning each declared repo)" >&2
    # Extract the `## Repositories` section body (until the next H2 or EOF),
    # then pull each `path:` line value.
    awk '
      /^## Repositories\b/ { in_section=1; next }
      in_section && /^## / { in_section=0 }
      in_section { print }
    ' "$sot" | grep -E '^[[:space:]]*-?[[:space:]]*path:' | \
      sed -E 's/^[[:space:]]*-?[[:space:]]*path:[[:space:]]*//; s/[[:space:]]+$//' | \
      while IFS= read -r raw_path; do
        [[ -z "$raw_path" ]] && continue
        # Expand leading ~ to $HOME
        case "$raw_path" in
          "~"|"~/"*) raw_path="${HOME}${raw_path#~}" ;;
        esac
        # Resolve to absolute path if the dir exists
        if [[ -d "$raw_path" ]]; then
          (cd "$raw_path" && pwd)
        else
          [[ $VERBOSE -eq 1 ]] && echo "skip (multi-repo path not found): $raw_path" >&2
        fi
      done
    return 0
  fi

  # Single-repo: extract first non-empty line under `## Active codebase / repo`.
  # The section header in practice may be `## Active codebase / repo` or
  # `## Active codebase`; match either.
  local single
  single=$(awk '
    /^## Active codebase( \/ repo)?\b/ { in_section=1; next }
    in_section && /^## / { in_section=0 }
    in_section && NF > 0 { print; exit }
  ' "$sot" | sed -E 's/^[[:space:]]*-?[[:space:]]*//; s/[[:space:]]+$//')

  [[ -z "$single" ]] && return 0

  case "$single" in
    "~"|"~/"*) single="${HOME}${single#~}" ;;
  esac

  if [[ -d "$single" ]]; then
    (cd "$single" && pwd)
  else
    [[ $VERBOSE -eq 1 ]] && echo "skip (single-repo path not found): $single" >&2
  fi
}

# Enumerate substrate files at canonical locations.
# Per `wos/substrate-peers.md`: 4 task-memory + task-scoped fleet-substrate +
# project-scoped fleet-substrate + product-repo fleet-substrate (when
# SOURCE_OF_TRUTH.md declares a codebase path; --include-product-repos toggles).
SUBSTRATE_FILES=()
for rel in TASK_STATE.md DECISIONS.md IMPLEMENTATION_PLAN.md SOURCE_OF_TRUTH.md EXTERNAL_RESEARCH.md VERIFICATION_LOG.md; do
  [[ -f "$TASK_DIR/$rel" ]] && SUBSTRATE_FILES+=("$TASK_DIR/$rel")
done
for rel in INITIATIVE_INDEX.md REFERENCES.md; do
  [[ -f "$PROJECT_DIR/$rel" ]] && SUBSTRATE_FILES+=("$PROJECT_DIR/$rel")
done

# Product-repo fleet-substrate enumeration (default ON).
# Canonical paths per `wos/substrate-peers.md ## Fleet-substrate files`:
#   <repo>/docs/research/ATOM_AUDIT.md
#   <repo>/docs/app/SCREEN_MAP.md
#   <repo>/docs/app/routes.md
# Each product-repo path resolved via resolve_product_repo_paths() handles both
# single-repo (`## Active codebase / repo`) and multi-repo (`## Repositories`)
# layouts. The cutover gate below (git log for tracked, mtime fallback for
# untracked) applies UNCHANGED to product-repo files because `git -C <repo>` is
# used implicitly via the file's own resolved repo root.
PRODUCT_REPO_ROOTS=()
if [[ $INCLUDE_PRODUCT_REPOS -eq 1 ]]; then
  while IFS= read -r repo_root; do
    [[ -z "$repo_root" ]] && continue
    PRODUCT_REPO_ROOTS+=("$repo_root")
    for rel in docs/research/ATOM_AUDIT.md docs/app/SCREEN_MAP.md docs/app/routes.md; do
      if [[ -f "$repo_root/$rel" ]]; then
        SUBSTRATE_FILES+=("$repo_root/$rel")
        [[ $VERBOSE -eq 1 ]] && echo "include (product-repo fleet-substrate): $repo_root/$rel" >&2
      fi
    done
  done < <(resolve_product_repo_paths)
fi

if [[ ${#SUBSTRATE_FILES[@]} -eq 0 ]]; then
  echo "substrate_header_drift_count: 0"
  [[ $VERBOSE -eq 1 ]] && echo "(no substrate files found at $TASK_DIR, $PROJECT_DIR, or any product repo)" >&2
  exit 0
fi

# The canonical inline header pattern per substrate-write-protocol.md:
HEADER_REGEX='^<!-- wos:write owner=[a-z][a-z0-9-]+ section='\''## .+'\'' run_id=[a-zA-Z0-9_-]+ ts=[0-9T:.Z-]+ reason=.+ mode=(applied|proposed) -->$'

DRIFT_COUNT=0
DRIFT_LOG=()

# Helper: given an absolute file path, find the git repo root that owns it
# (or empty if untracked / not in any repo). For product-repo substrate, this
# returns the product-repo root; for Fhorja substrate, this returns $WOS_ROOT.
file_repo_root() {
  local f="$1"
  local d
  d=$(dirname "$f")
  (cd "$d" && git rev-parse --show-toplevel 2>/dev/null || true)
}

for file in "${SUBSTRATE_FILES[@]}"; do
  # Cutover gate. Two paths:
  #   A. File is git-tracked: use `git log --since=<cutoff>` to ask "was this
  #      modified at or after the cutover?". Zero hits = legacy file never
  #      touched post-cutover = skip.
  #   B. File is gitignored (typical for `projects/<proj>/active/<task>/`
  #      substrate per ADR-0007): use file mtime as the fallback signal.
  #      mtime >= cutoff = file has been written under K.2 protocol expectations
  #      = scan; mtime < cutoff = legacy = skip.
  #
  # NOTE: path B over-counts on files that mix legacy + post-cutover sections
  # (sections written pre-cutover that were never re-edited will show as drift
  # even though they predate the protocol). This is acceptable in v2.1
  # informational mode -- the count is a signal, not an enforced threshold.
  #
  # For product-repo fleet-substrate, the owning git repo is the PRODUCT repo
  # (different from WOS_ROOT). We resolve per-file and use that as the git
  # context for tracked/log queries. The display path is rendered relative to
  # the owning repo root so output remains readable (e.g.
  # `<repo>/docs/research/ATOM_AUDIT.md` rather than a long absolute path).
  owning_root=$(file_repo_root "$file")
  if [[ -z "$owning_root" ]]; then
    owning_root="$WOS_ROOT"
  fi

  rel_to_root=$(realpath --relative-to="$owning_root" "$file" 2>/dev/null || echo "$file")
  is_tracked=$(cd "$owning_root" && git ls-files --error-unmatch "$rel_to_root" 2>/dev/null && echo yes || true)
  if [[ -n "$is_tracked" ]]; then
    last_post_cutoff=$(cd "$owning_root" && git log -1 --since="$CUTOFF" --format=%cI -- "$rel_to_root" 2>/dev/null || true)
    if [[ -z "$last_post_cutoff" ]]; then
      [[ $VERBOSE -eq 1 ]] && echo "skip (tracked, pre-cutover only): $file" >&2
      continue
    fi
  else
    # Untracked / gitignored: fall back to mtime.
    mtime_epoch=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null || echo 0)
    cutoff_epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$CUTOFF" "+%s" 2>/dev/null || date -u -d "$CUTOFF" "+%s" 2>/dev/null || echo 0)
    if [[ "$mtime_epoch" -lt "$cutoff_epoch" ]]; then
      [[ $VERBOSE -eq 1 ]] && echo "skip (untracked, mtime pre-cutover): $file" >&2
      continue
    fi
    [[ $VERBOSE -eq 1 ]] && echo "scan (untracked, mtime post-cutover): $file" >&2
  fi

  # Scan H2 headers in current file content
  while IFS= read -r line_no; do
    [[ -z "$line_no" ]] && continue
    section=$(sed -n "${line_no}p" "$file")
    prev_line_no=$((line_no - 1))
    if [[ "$prev_line_no" -lt 1 ]]; then
      prev_line=""
    else
      prev_line=$(sed -n "${prev_line_no}p" "$file")
    fi
    if [[ "$prev_line" =~ $HEADER_REGEX ]]; then
      continue  # has canonical header
    fi
    # Known-gap exemption (F-11, dogfood-wave 2026-07-11): REFERENCES.md's
    # fixed template sections are created by project-bootstrap.md, which has
    # no substrate-write-protocol section (a known, deferred v2.1 gap per
    # wos/substrate-peers.md). Exempt these 3 fixed sections from the drift
    # count so recurring false-positive noise stops eroding the signal; the
    # underlying deferred gap is unchanged.
    if [[ "$(basename "$file")" == "REFERENCES.md" ]]; then
      case "$section" in
        "## Format reminder"|"## <Topic / Tag>"|"## Entries")
          [[ $VERBOSE -eq 1 ]] && echo "exempt (REFERENCES.md fixed template section, known v2.1 gap): $file:${line_no} ${section}" >&2
          continue
          ;;
      esac
    fi
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    DRIFT_LOG+=("$(realpath --relative-to="$owning_root" "$file" 2>/dev/null || echo "$file"):${line_no} ${section}")
  done < <(grep -n "^## " "$file" | cut -d: -f1)
done

echo "substrate_header_drift_count: $DRIFT_COUNT"

if [[ $VERBOSE -eq 1 ]]; then
  echo "--- drift detail (${#DRIFT_LOG[@]:-0} sections) ---" >&2
  if [[ ${#DRIFT_LOG[@]:-0} -gt 0 ]]; then
    printf '%s\n' "${DRIFT_LOG[@]}" >&2
  fi
fi

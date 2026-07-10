#!/usr/bin/env bash
# memory-lint.sh - read-only memory-hygiene check for a Fhorja task folder.
#
# Deterministic half of the memory-lint mode (decision D-2): it reports, never
# writes. It surfaces three classes of issue and leaves "stale fact" judgment to the
# model-driven layer in state-reconcile:
#   1. Dead relative links  - markdown links and backticked paths that point at a
#      ./ or ../ target which does not exist on disk.
#   2. Orphaned SLICES/ files - slice files not referenced by IMPLEMENTATION_PLAN.md
#      or TASK_STATE.md in the same task folder.
#   3. LEARNINGS entry quality - reflexion entries in LEARNINGS.md with a missing or
#      empty Anchor, a blank mandatory bullet, or a missing or empty Tags line.
#      Absence of LEARNINGS.md is not a finding.
#
# Usage:
#   memory-lint.sh [TASK_DIR]
#   - TASK_DIR defaults to the most-recently-modified projects/*/active/* folder
#     under $WOS_TASKS_ROOT (else $CLAUDE_PROJECT_DIR/projects, else ./projects).
#   - The task's project-level memory (PROJECT_CHARTER.md, REFERENCES.md in the
#     parent project dir) is also scanned for dead relative links.
#
# Read-only and advisory: always exits 0. A trailing "MEMORY-LINT: N finding(s)"
# line lets callers grep the result; this command never blocks.

# No `set -e`: this scanner is advisory and must always exit 0.
set -uo pipefail

findings=0
report() { findings=$((findings + 1)); echo "  - $1"; }

# ---------------------------------------------------------------------------
# 1. Resolve the task folder
# ---------------------------------------------------------------------------
tasks_root="${WOS_TASKS_ROOT:-${CLAUDE_PROJECT_DIR:-.}/projects}"
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }

task_dir="${1:-}"
if [[ -z "$task_dir" ]]; then
  best="" ; best_m=0
  while IFS= read -r ts_file; do
    [[ -n "$ts_file" ]] || continue
    m="$(mtime "$ts_file")"
    if [[ "$m" -ge "$best_m" ]]; then best_m="$m"; best="$(dirname "$ts_file")"; fi
  done < <(find "$tasks_root" -type f -path '*/active/*/TASK_STATE.md' 2>/dev/null)
  task_dir="$best"
fi

if [[ -z "$task_dir" || ! -d "$task_dir" ]]; then
  echo "memory-lint: no task folder to scan (looked under $tasks_root)."
  echo "MEMORY-LINT: 0 finding(s)"
  exit 0
fi

echo "memory-lint: scanning $task_dir (read-only)"

# ---------------------------------------------------------------------------
# 2. Dead relative links
# ---------------------------------------------------------------------------
# Scan the task's own .md files plus the project-level memory files one and two
# levels up (PROJECT_CHARTER.md, REFERENCES.md).
project_dir="$(cd "$task_dir/../.." 2>/dev/null && pwd || true)"
scan_files=()
while IFS= read -r f; do scan_files+=("$f"); done < <(find "$task_dir" -maxdepth 2 -type f -name '*.md' 2>/dev/null)
for pf in "$project_dir/PROJECT_CHARTER.md" "$project_dir/REFERENCES.md"; do
  [[ -f "$pf" ]] && scan_files+=("$pf")
done

echo "Dead relative links:"
dead_links=0
# bash 3.2-safe empty-array expansion (plain "${arr[@]}" is unbound under set -u).
for f in ${scan_files[@]+"${scan_files[@]}"}; do
  base="$(dirname "$f")"
  # Markdown link targets: ](target)
  while IFS= read -r target; do
    [[ -n "$target" ]] || continue
    # Only relative file targets; skip URLs, anchors, and mailto.
    case "$target" in
      http://*|https://*|mailto:*|\#*) continue ;;
    esac
    [[ "$target" == ./* || "$target" == ../* || "$target" == *.md ]] || continue
    # Strip any trailing #anchor.
    clean="${target%%#*}"
    [[ -n "$clean" ]] || continue
    if [[ ! -e "$base/$clean" ]]; then
      report "$f -> $target (markdown link target missing)"
      dead_links=$((dead_links + 1))
    fi
  done < <(grep -oE '\]\([^)]+\)' "$f" 2>/dev/null | sed -E 's/^\]\(//; s/\)$//')

  # Backticked relative paths that look like FILES: `./x/y.md`, `../a.sh`.
  # Require a file extension in the last segment so prose directory mentions
  # (e.g. `./projects`) are not treated as broken links.
  while IFS= read -r target; do
    [[ -n "$target" ]] || continue
    clean="${target%%#*}"
    [[ "$(basename "$clean")" == *.* ]] || continue
    if [[ ! -e "$base/$clean" ]]; then
      report "$f -> \`$target\` (backticked relative path missing)"
      dead_links=$((dead_links + 1))
    fi
  done < <(grep -oE '`\.\.?/[^`]+`' "$f" 2>/dev/null | tr -d '`')
done
[[ "$dead_links" -eq 0 ]] && echo "  (none)"

# ---------------------------------------------------------------------------
# 3. Orphaned SLICES/ files
# ---------------------------------------------------------------------------
echo "Orphaned SLICES/ files:"
orphans=0
slices_dir="$task_dir/SLICES"
plan="$task_dir/IMPLEMENTATION_PLAN.md"
state="$task_dir/TASK_STATE.md"
if [[ -d "$slices_dir" ]]; then
  while IFS= read -r slice; do
    [[ -n "$slice" ]] || continue
    name="$(basename "$slice")"
    # Accept references by filename OR by slice number (S1, S01, "Slice 1"),
    # since plans commonly cite slices as "S1" rather than the bare filename.
    num="$(printf '%s' "$name" | grep -oE '^[0-9]+' || true)"
    n=""
    [[ -n "$num" ]] && n="$((10#$num))"
    referenced=0
    for ref in "$plan" "$state"; do
      [[ -f "$ref" ]] || continue
      if grep -qF "$name" "$ref" 2>/dev/null; then referenced=1; break; fi
      if [[ -n "$n" ]] && grep -qiE "(^|[^a-z0-9])s0*${n}([^0-9]|$)" "$ref" 2>/dev/null; then referenced=1; break; fi
      if [[ -n "$n" ]] && grep -qiE "slice 0*${n}([^0-9]|$)" "$ref" 2>/dev/null; then referenced=1; break; fi
    done
    if [[ "$referenced" -eq 0 ]]; then
      report "$name not referenced by IMPLEMENTATION_PLAN.md or TASK_STATE.md"
      orphans=$((orphans + 1))
    fi
  done < <(find "$slices_dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null)
  [[ "$orphans" -eq 0 ]] && echo "  (none)"
else
  echo "  (no SLICES/ directory)"
fi

# ---------------------------------------------------------------------------
# 4. LEARNINGS entry quality
# ---------------------------------------------------------------------------
# Scan LEARNINGS.md (if present) for malformed reflexion entries: a missing or
# empty Anchor: field, any mandatory bullet (Tried / Failed because / Next time /
# Cross-project promotion) whose value after the colon is blank, and a missing or
# empty Tags: line. The Tags: line is introduced by a sibling change; entries that
# predate it are flagged, not errored. A missing LEARNINGS.md is not a finding.
echo "LEARNINGS entry quality:"
learnings_issues=0
learnings="$task_dir/LEARNINGS.md"

trim_ws() { printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//'; }

# Inspect one accumulated entry (globals: entry_header, entry_body).
check_learning_field() {
  # $1 = field label (e.g. Anchor, "Failed because"); $2 = mode (required|value-only)
  local label="$1" mode="$2" line val
  line="$(printf '%s\n' "$entry_body" | grep -E "^[[:space:]]*- ${label}:" | head -1)"
  if [[ -z "$line" ]]; then
    if [[ "$mode" == "required" ]]; then
      report "$learnings [$entry_header]: missing ${label}: field"
      learnings_issues=$((learnings_issues + 1))
    fi
    return 0
  fi
  val="$(trim_ws "${line#*- ${label}:}")"
  if [[ -z "$val" ]]; then
    report "$learnings [$entry_header]: empty ${label}: value"
    learnings_issues=$((learnings_issues + 1))
  fi
}

finalize_learning_entry() {
  [[ -n "$entry_header" ]] || return 0
  check_learning_field "Anchor" required
  check_learning_field "Tried" value-only
  check_learning_field "Failed because" value-only
  check_learning_field "Next time" value-only
  check_learning_field "Cross-project promotion" value-only
  check_learning_field "Tags" required
}

if [[ -f "$learnings" ]]; then
  in_fence=0
  entry_header=""
  entry_body=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      '```'*) in_fence=$((1 - in_fence)) ;;
    esac
    if [[ "$in_fence" -eq 0 ]]; then
      # A dated H2 header (## YYYY-MM-DD ...) starts a real learning entry.
      if [[ "$line" =~ ^##[[:space:]][0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]] ]]; then
        finalize_learning_entry
        entry_header="$(printf '%s' "$line" | sed -E 's/^##[[:space:]]+//')"
        entry_body=""
        continue
      fi
      # Any other H2 header closes the current entry block (e.g. a trailing section).
      if [[ -n "$entry_header" && "$line" =~ ^##[[:space:]] ]]; then
        finalize_learning_entry
        entry_header=""
        entry_body=""
        continue
      fi
    fi
    [[ -n "$entry_header" ]] && entry_body="$entry_body"$'\n'"$line"
  done < "$learnings"
  finalize_learning_entry
  [[ "$learnings_issues" -eq 0 ]] && echo "  (none)"
else
  echo "  (no LEARNINGS.md)"
fi

# ---------------------------------------------------------------------------
# 5. Summary (read-only; never blocks)
# ---------------------------------------------------------------------------
echo "MEMORY-LINT: $findings finding(s)"
exit 0

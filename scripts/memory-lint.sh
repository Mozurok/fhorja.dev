#!/usr/bin/env bash
# memory-lint.sh - read-only memory-hygiene check for a Fhorja task folder.
#
# Deterministic half of the memory-lint mode (decision D-2): it reports, never
# writes. It surfaces three classes of issue and leaves "stale fact" judgment to the
# model-driven layer in state-reconcile:
#   1. Dead relative links  - markdown links and backticked paths that point at a
#      ./ or ../ target which does not exist on disk, plus bare task-artifact
#      references on bullet lines (TASK_STATE.md, SLICES/<file>.md) that resolve
#      against neither the containing file's directory nor the task root.
#
#      The bare-reference half is deliberately narrow, because a lint that cries
#      on healthy memory teaches its reader to skip the output. Five rules bound
#      it (2026-07-29: it reported 45 findings on a healthy task, all false):
#        - only TASK-MEMORY artifact names count (TASK_ARTIFACT_RE below), never
#          a file belonging to another tree such as the product repo's CLAUDE.md
#        - a token resolves against the task root as well as its own directory
#        - project-level files (PROJECT_CHARTER, project REFERENCES) are skipped,
#          since a mention there describes child tasks and has no sibling
#        - a sentence stating the artifact is ABSENT, or naming where something
#          WOULD go, is discussing it, not linking to it
#        - a glossed example (`<path>` followed by " -- <what it shows>") is
#          documenting a format, not citing a file
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
# line lets callers grep the result; this command never blocks. When no task folder
# was scanned the trailing line is "MEMORY-LINT: not scanned" instead, never a count
# of 0, which read as a clean folder (ADR-0224).

# No `set -e`: this scanner is advisory and must always exit 0.
set -uo pipefail

findings=0
report() { findings=$((findings + 1)); echo "  - $1"; }

# Task-memory artifact names this scanner will resolve as sibling files.
# Deliberately a POSITIVE list. Anything not here is a reference to another
# tree (the product repo's CLAUDE.md or AGENTS.md, the repo-root USER_MEMORY.md,
# a generated report under the product repo) and is none of this lint's
# business; matching those was the whole of the 2026-07-29 false-positive run.
# Sources: the 4 task-memory substrate files plus the task-scoped templates in
# `templates/`. Fleet-substrate and project-level names are excluded on purpose:
# they do not live beside a task's own files.
TASK_ARTIFACT_RE='(TASK_STATE|SOURCE_OF_TRUTH|DECISIONS|IMPLEMENTATION_PLAN|IMPACT_ANALYSIS|INVARIANTS_AND_NON_GOALS|TEST_STRATEGY|PR_PACKAGE|LEARNINGS|TASK_PREFERENCES|BRIEF|EXTERNAL_RESEARCH|OPEN_QUESTIONS|AI_EVAL_PLAN|RELEASE_PLAN|SLO_SPEC|PERFORMANCE_BUDGET|POSTMORTEM|ACCESSIBILITY_AUDIT|BACKEND_SYSTEM_DESIGN|FRONTEND_SYSTEM_DESIGN|DB_CONTEXT|CODE_CONTEXT_MAP|FEATURE_LIBRARIES|STACK_RECOMMENDATION|CURRENT_PATTERNS|VERIFICATION_LOG)\.md'

# ---------------------------------------------------------------------------
# 1. Resolve the task folder
# ---------------------------------------------------------------------------
tasks_root="${WOS_TASKS_ROOT:-${CLAUDE_PROJECT_DIR:-.}/projects}"
# Portable mtime, detected once. The `stat -f || stat -c` chain this replaces leaked the
# GNU filesystem report into the value: `stat -f %m` exits 1 on GNU but writes to STDOUT
# first, and `2>/dev/null` silences only stderr, so the substitution captured both branches.
if stat -f '%m' "$0" >/dev/null 2>&1; then STAT_MTIME=(stat -f '%m'); else STAT_MTIME=(stat -c '%Y'); fi
mtime() { local v; v=$("${STAT_MTIME[@]}" "$1" 2>/dev/null || echo 0); case "$v" in ''|*[!0-9]*) v=0 ;; esac; echo "$v"; }

task_dir="${1:-}"
if [[ -n "$task_dir" && ! -d "$task_dir" ]]; then
  # A folder was named and is not there. Saying "looked under ./projects" here reported a
  # search that never ran, for a path the caller never asked about.
  echo "memory-lint: no such task folder: $task_dir"
  echo "MEMORY-LINT: not scanned"
  exit 0
fi
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
  echo "MEMORY-LINT: not scanned"
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

  # Bare task-artifact references on bullet lines outside code fences:
  # tokens like TASK_STATE.md or SLICES/01-foo.md mentioned without a markdown
  # link or path prefix.
  #
  # Three rules keep this honest (2026-07-29, 2026-07-29 mobile dogfood: this detector
  # produced 45 findings on a healthy task and every one was a false positive):
  #
  # 1. Only TASK-MEMORY artifact names count. A mention of `CLAUDE.md`,
  #    `AGENTS.md`, `USER_MEMORY.md`, or a report living in the product repo is
  #    a reference to a file in ANOTHER tree, not a broken neighbour link. The
  #    old `[A-Z][A-Z0-9_]*\.md` pattern matched every one of them.
  # 2. Resolve against the TASK ROOT as well as the containing directory. A
  #    slice note in `SLICES/` naming `TEST_STRATEGY.md` means the task's file
  #    one level up, not `SLICES/TEST_STRATEGY.md`.
  # 3. Skip project-level files entirely. In `PROJECT_CHARTER.md`, a mention of
  #    `TASK_STATE.md` describes what child tasks contain; there is no sibling
  #    to resolve, and reporting one is noise by construction.
  case "$f" in
    "$task_dir"/*) ;;
    *) continue ;;
  esac
  in_fence=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      '```'*) in_fence=$((1 - in_fence)); continue ;;
    esac
    [[ "$in_fence" -eq 0 ]] || continue
    [[ "$line" =~ ^[[:space:]]*-[[:space:]] ]] || continue
    # Drop markdown links (text plus target) and URLs so their contents are
    # not re-reported here; detector 1 already checks link targets.
    stripped="$(printf '%s' "$line" | sed -E 's/\[[^]]*\]\([^)]*\)//g; s#https?://[^[:space:])]*##g')"
    while IFS= read -r token; do
      [[ -n "$token" ]] || continue
      # Trim the single non-token lead character kept by the boundary match.
      token="$(printf '%s' "$token" | sed -E 's/^[^A-Z]//')"
      # Rule 4: a line that says the artifact is ABSENT, or names where something
      # WOULD go, is discussing the artifact, not linking to it. Naming a file
      # that does not exist is the whole point of those sentences, so reporting
      # them as broken links inverts the lint's meaning. Observed forms, all
      # from real task memory: "inert, no `AI_EVAL_PLAN.md` in the task folder",
      # "the task has no `INVARIANTS_AND_NON_GOALS.md`", "that belongs in
      # `TASK_PREFERENCES.md`", and the `## Entry shape` template example
      # citing `SLICES/03_auth-refactor.md` as an anchor format.
      lead="$(printf '%s' "$stripped" | sed -E "s/\\Q${token}\\E.*//" 2>/dev/null || printf '%s' "$stripped")"
      if printf '%s' "$line" | grep -qiE '(\bno\b|\bnot\b|\bnever\b|\bwithout\b|\babsent\b|\blacks?\b|\bmissing\b|belongs in|would (go|live|be)|should (go|live|be)|for example|e\.g\.)[^.]{0,60}'"$(printf '%s' "$token" | sed 's/[.[\*^$/]/\\&/g')"; then
        continue
      fi
      # Rule 5: a glossed example, `<path>` followed by ` -- <what it shows>`,
      # is documenting a format, not citing a file. This is the repo's own
      # convention for example lists (see `templates/LEARNINGS.md` `## Entry
      # shape`), and because every task's LEARNINGS.md is seeded from that
      # template, without this rule the anchor examples report as broken links
      # in EVERY task that has one.
      if printf '%s' "$line" | grep -qE '`[^`]*'"$(printf '%s' "$token" | sed 's/[.[\*^$/]/\\&/g')"'[^`]*`[[:space:]]+--[[:space:]]'; then
        continue
      fi
      # Rule 2: the task root is as valid a home as the containing directory.
      if [[ ! -e "$base/$token" && ! -e "$task_dir/$token" ]]; then
        report "$f -> $token (bare relative reference missing)"
        dead_links=$((dead_links + 1))
      fi
    done < <(printf '%s\n' "$stripped" | grep -oE "(^|[^A-Za-z0-9_./-])(SLICES/[A-Za-z0-9_.-]+\.md|${TASK_ARTIFACT_RE})" 2>/dev/null)
  done < "$f"
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
# Cross-project promotion) whose value after the colon is blank, and a Tags: line
# that is present but empty. Tags is optional per ADR-0071, so an entry without one
# is valid and is not reported. A missing LEARNINGS.md is not a finding.
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
  # value-only, not required: ADR-0071 made Tags OPTIONAL ("keeps the change backward
  # compatible: every existing entry stays valid"), and `required` flagged every entry
  # that predates the field as malformed. A Tags line that is present must still carry
  # a value, which is what value-only asserts. Corrected 2026-09-22 (ADR-0214).
  check_learning_field "Tags" value-only
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

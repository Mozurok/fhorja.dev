#!/usr/bin/env bash
# build-agent-skills.sh
#
# Generates `.claude/skills/<name>/SKILL.md` from each canonical
# `commands/<name>.md`. The canonical command files already carry the
# Agent Skills frontmatter (validated by `lint-commands.sh`), so this
# adapter only has to:
#
#   1. Copy the frontmatter block verbatim.
#   2. Drop the H1 heading right after the closing `---` (Agent Skills
#      uses the `name:` field; the H1 is redundant).
#   3. Copy the rest of the body, minus the two maintenance markers the
#      agent never reads: a `<!-- shared:<name> -->` line is dropped and a
#      `<!-- count:<kind> -->N<!-- /count -->` wrapper becomes the bare N
#      (ADR-0227). Both markers stay in commands/*.md, where
#      sync-shared-blocks.sh, reconcile-counts.sh and the lint read them;
#      nothing reads them in the generated copy. Fenced code is left alone.
#
# The result is byte-stable across runs (idempotent), so the script can
# safely run in pre-commit hooks or in CI under `--check` mode.
#
# Modes:
#   build (default): writes / overwrites every `.claude/skills/<name>/SKILL.md`
#                    that has a corresponding `commands/<name>.md`. Prunes
#                    stale skill directories whose canonical command no
#                    longer exists.
#   --check:         exits 0 if every committed `.claude/skills/<name>/SKILL.md`
#                    matches what `build` would produce; exits 1 if there is
#                    drift (or stale skills); never writes.
#
# Other flags:
#   --no-prune     do not delete stale `.claude/skills/<name>/` directories
#                  whose canonical command was removed
#   --dry-run      print actions only; do not write or delete
#   --verbose|-v   print each command processed, not only failures / drift
#
# Exit codes:
#   0 = success (or no drift in --check mode)
#   1 = drift detected in --check mode, or runtime failure
#   2 = invocation error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMANDS_DIR="${REPO_ROOT}/commands"
SKILLS_DIR="${REPO_ROOT}/.claude/skills"

MODE="build"
DRY_RUN=0
VERBOSE=0
DO_PRUNE=1

usage() {
  cat <<'EOF'
Usage: scripts/build-agent-skills.sh [options]

Generate .claude/skills/<name>/SKILL.md from each commands/<name>.md.

Options:
  --check        Verify that committed skills match canonical commands.
                 Exits 1 on any drift; never writes.
  --no-prune     Keep stale skill directories whose canonical command was
                 removed (default: prune them in build mode).
  --dry-run      Print actions only; do not write or delete.
  --verbose, -v  Print every command processed, not only drift / failures.
  --help, -h     Show this message.

Exit codes:
  0 = success (or no drift in --check mode)
  1 = drift detected in --check mode, or runtime failure
  2 = invocation error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check" ;;
    --no-prune) DO_PRUNE=0 ;;
    --dry-run) DRY_RUN=1 ;;
    --verbose|-v) VERBOSE=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ ! -d "$COMMANDS_DIR" ]]; then
  echo "Error: commands directory not found: $COMMANDS_DIR" >&2
  exit 2
fi

# Render a SKILL.md body to stdout from a canonical commands/*.md file.
# Strategy: copy lines verbatim until the second `---` (closing the
# frontmatter), then on the first body line drop a `# <name>` H1 and copy
# every subsequent line verbatim.
# Per-skill re-injection cap documented for this harness: skill bodies are re-injected after
# compaction capped at 5,000 tokens (20,000 chars at the repo's 4-chars/token rule), and
# truncation KEEPS THE START. The output contract lives at the end of every command, so a
# body over the cap silently loses `### Definition of done`, `### Handoff`, and the closure
# gates exactly when the session has run longest. Measured 2026-08-10: 51 of 98 skills are
# over the cap and 37 lose their Definition of done.
#
# The notice is emitted ONLY for bodies over the cap, and only into the GENERATED artifact:
# the canonical commands/*.md keep their human reading order. It is a pointer, not a copy, so
# it costs about 390 chars instead of duplicating the contract.
REINJECTION_CAP_CHARS=20000

# Drop the maintenance markers from a rendered body (see step 3 in the header). The
# patterns are the exact forms sync-shared-blocks.sh and the count-marker lint accept, so a
# marker quoted inside prose or a backticked span in some other shape is left as written.
strip_source_markers() {
  perl -ne '
    if (/^```/) { $fence = !$fence; print; next }
    unless ($fence) {
      next if /^<!-- shared:[a-z-]+ -->[ \t]*$/;
      s/<!-- count:[a-z0-9-]+ -->(\d+)<!-- \/count -->/$1/g;
    }
    print;
  '
}

render_skill() {
  local body_chars notice
  body_chars=$(wc -c < "$1" | tr -d ' ')
  notice=0
  [ "$body_chars" -gt "$REINJECTION_CAP_CHARS" ] && notice=1

  # The summary is multi-line, and awk -v cannot carry a newline. Emit a placeholder and
  # splice the real block in afterwards.
  local summary_file=""
  if (( notice )); then
    summary_file="$(mktemp)"
    python3 "${SCRIPT_DIR}/emit-skill-contract-summary.py" "$1" > "$summary_file"
    [ -s "$summary_file" ] || { rm -f "$summary_file"; summary_file=""; notice=0; }
  fi

  # The frontmatter is emitted by emit-skill-frontmatter.py, not by this awk. The branch
  # that used to turn a flow sequence into a BLOCK sequence is gone: the Agent Skills spec
  # fixes metadata as a map from string keys to STRING values, and a block sequence is a
  # list. awk now emits the BODY only, and the two are concatenated.
  python3 "${SCRIPT_DIR}/emit-skill-frontmatter.py" "$1" || return 1

  awk -v notice="$notice" '
    BEGIN { fm_count = 0; first_body = 0 }
    {
      if (fm_count < 2) {
        if ($0 == "---") { fm_count++ }
        next
      }
      if (!first_body) {
        first_body = 1
        if (notice) { print "@@CONTRACT_SUMMARY@@" }
        if ($0 ~ /^# /) { next }
      }
      print
    }
  ' "$1" | {
    if [[ -n "$summary_file" ]]; then
      # Splice the block in place of the placeholder line.
      awk -v f="$summary_file" '
        $0 == "@@CONTRACT_SUMMARY@@" { while ((getline line < f) > 0) print line; next }
        { print }
      '
    else
      cat
    fi
  } | strip_source_markers
  [[ -n "$summary_file" ]] && rm -f "$summary_file"
  return 0
}

shopt -s nullglob
# K.3 (2026-06-04): dual layout. Flat commands at `commands/<name>.md` AND
# folder-shaped at `commands/<name>/SKILL.md`. Folder-shaped is reserved for
# K.8 personas; existing 57 commands stay flat (no migration). The `_shared/`
# directory holds canonical block bodies, not commands; exclude its files.
COMMAND_FILES=()
for f in "${COMMANDS_DIR}"/*.md; do
  [[ "$(dirname "$f")" == "${COMMANDS_DIR}" ]] && COMMAND_FILES+=("$f")
done
for f in "${COMMANDS_DIR}"/*/SKILL.md; do
  parent_name="$(basename "$(dirname "$f")")"
  [[ "$parent_name" == "_shared" ]] && continue
  COMMAND_FILES+=("$f")
done
shopt -u nullglob

if [[ ${#COMMAND_FILES[@]} -eq 0 ]]; then
  echo "Error: no command files found in $COMMANDS_DIR" >&2
  exit 2
fi

# Helper: derive canonical name from a command file path. Flat:
# `commands/<name>.md` -> <name>. Folder-shaped: `commands/<name>/SKILL.md`
# -> <name>.
canonical_name_from_path() {
  local f="$1"
  if [[ "$(basename "$f")" == "SKILL.md" ]]; then
    basename "$(dirname "$f")"
  else
    basename "$f" .md
  fi
}

# Collect canonical names (handles both layouts).
CANONICAL_NAMES=()
for f in "${COMMAND_FILES[@]}"; do
  CANONICAL_NAMES+=("$(canonical_name_from_path "$f")")
done

# Helper: does $1 appear in CANONICAL_NAMES?
is_canonical() {
  local needle="$1" n
  for n in "${CANONICAL_NAMES[@]}"; do
    [[ "$n" == "$needle" ]] && return 0
  done
  return 1
}

WROTE=0
SKIPPED_UPTODATE=0
DRIFTED=()
PRUNED=()
STALE=()

# 1. Build / verify each canonical skill.
for src in "${COMMAND_FILES[@]}"; do
  name="$(canonical_name_from_path "$src")"
  out_dir="${SKILLS_DIR}/${name}"
  out="${out_dir}/SKILL.md"

  rendered_tmp="$(mktemp -t "build-skills.XXXXXX")"
  trap 'rm -f "$rendered_tmp"' EXIT
  render_skill "$src" > "$rendered_tmp"

  if [[ "$MODE" == "check" ]]; then
    if [[ ! -f "$out" ]]; then
      DRIFTED+=("$name (skill missing)")
    elif ! diff -q "$rendered_tmp" "$out" >/dev/null 2>&1; then
      DRIFTED+=("$name (content drift)")
    elif [[ $VERBOSE -eq 1 ]]; then
      echo "OK: $name"
    fi
  else
    if [[ -f "$out" ]] && diff -q "$rendered_tmp" "$out" >/dev/null 2>&1; then
      SKIPPED_UPTODATE=$((SKIPPED_UPTODATE + 1))
      [[ $VERBOSE -eq 1 ]] && echo "UP-TO-DATE: $name"
    else
      if [[ $DRY_RUN -eq 1 ]]; then
        echo "WOULD WRITE: $out"
      else
        mkdir -p "$out_dir"
        cp "$rendered_tmp" "$out"
      fi
      WROTE=$((WROTE + 1))
      [[ $VERBOSE -eq 1 ]] && echo "WROTE: $name"
    fi
  fi

  rm -f "$rendered_tmp"
  trap - EXIT
done

# 2. Detect / prune stale skill directories (no matching canonical command).
if [[ -d "$SKILLS_DIR" ]]; then
  shopt -s nullglob
  for d in "$SKILLS_DIR"/*/; do
    name="$(basename "$d")"
    if ! is_canonical "$name"; then
      if [[ "$MODE" == "check" ]]; then
        STALE+=("$name")
      else
        if [[ $DO_PRUNE -eq 1 ]]; then
          if [[ $DRY_RUN -eq 1 ]]; then
            echo "WOULD PRUNE: $d"
          else
            rm -rf "$d"
          fi
          PRUNED+=("$name")
        else
          STALE+=("$name")
        fi
      fi
    fi
  done
  shopt -u nullglob
fi

# 3. Report.
echo ""
echo "================================================================================"
if [[ "$MODE" == "check" ]]; then
  echo "build-agent-skills check: ${#CANONICAL_NAMES[@]} canonical command(s)"
  echo "  drifted:           ${#DRIFTED[@]}"
  echo "  stale skill dirs:  ${#STALE[@]}"
else
  echo "build-agent-skills build: ${#CANONICAL_NAMES[@]} canonical command(s)"
  echo "  wrote:             ${WROTE}"
  echo "  up-to-date:        ${SKIPPED_UPTODATE}"
  echo "  pruned stale:      ${#PRUNED[@]}"
  echo "  kept stale:        ${#STALE[@]}"
fi
echo "================================================================================"

if [[ "$MODE" == "check" ]]; then
  if [[ ${#DRIFTED[@]} -gt 0 ]] || [[ ${#STALE[@]} -gt 0 ]]; then
    echo ""
    if [[ ${#DRIFTED[@]} -gt 0 ]]; then
      echo "Drifted skills:"
      for d in "${DRIFTED[@]}"; do
        echo "  - $d"
      done
    fi
    if [[ ${#STALE[@]} -gt 0 ]]; then
      echo "Stale skill directories (no canonical command):"
      for s in "${STALE[@]}"; do
        echo "  - $s"
      done
    fi
    echo ""
    echo "Run ./scripts/build-agent-skills.sh to regenerate from canonical commands/."
    exit 1
  fi
  exit 0
fi

# build mode: report stale-but-kept, fail soft.
if [[ ${#STALE[@]} -gt 0 ]]; then
  echo ""
  echo "Stale skill directories kept (--no-prune):"
  for s in "${STALE[@]}"; do
    echo "  - $s"
  done
fi

exit 0

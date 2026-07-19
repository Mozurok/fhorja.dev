#!/usr/bin/env bash
# Sync workflow command markdown files to Cursor, Claude Code, and Codex CLI command directories.
# Source: <repo>/commands/*.md  →  same filenames (e.g. task-init.md → /task-init in Claude Code).
#
# Run it bare on a terminal for a guided wizard; pass any flag (or run in CI / a
# pipe) for the scriptable non-interactive path. Skills sync by default; use
# --no-skills to opt out.
#
# Defaults:
#   Cursor (legacy slash):  ~/.cursor/commands
#   Claude  (legacy slash):  ~/.claude/commands
#   Codex  (custom prompts): ~/.codex/prompts (invoked as /prompts:<name>)
#   Skills (open standard): ~/.claude/skills, ~/.cursor/skills, ~/.agents/skills (ON by default)
#
# Docs:
#   Cursor: project .cursor/commands or user commands (this script targets the user dir by default).
#   Claude Code: https://code.claude.com/docs/en/skills (custom commands under .claude/commands/)
#   Codex CLI: https://developers.openai.com/codex/custom-prompts
#              Custom prompts are deprecated; prefer skills for reusable workflows.
#              https://developers.openai.com/codex/skills
#   Agent Skills (open standard): https://agentskills.io/specification
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC="${REPO_ROOT}/commands"
SKILLS_SRC="${REPO_ROOT}/.claude/skills"

CURSOR_DEST="${CURSOR_COMMANDS_DIR:-${HOME}/.cursor/commands}"
CLAUDE_DEST="${CLAUDE_COMMANDS_DIR:-${HOME}/.claude/commands}"
CODEX_DEST="${CODEX_PROMPTS_DIR:-${HOME}/.codex/prompts}"

CLAUDE_SKILLS_DEST="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"
CURSOR_SKILLS_DEST="${CURSOR_SKILLS_DIR:-${HOME}/.cursor/skills}"
CODEX_SKILLS_DEST="${CODEX_SKILLS_DIR:-${HOME}/.agents/skills}"
DEFAULT_CODEX_SKILLS_DEST="${HOME}/.agents/skills"
LEGACY_CODEX_SKILLS_DEST="${HOME}/.codex/skills"

DRY_RUN=0
DO_CURSOR=1
DO_CLAUDE=1
DO_CODEX=1
WITH_DOCS=0
WITH_SKILLS=1          # skills ON by default (opt out with --no-skills)
DO_CLEAN_ORPHANS=0
ASSUME_YES=0
PROJECT=""

# Capture whether the script was invoked with zero arguments, before the arg
# loop consumes them. This drives the interactivity gate below: a bare, TTY
# invocation opens the wizard; any flag, or a non-TTY stdin/stdout (CI, pipe,
# redirect), takes the scriptable path with the historical semantics.
INVOKED_ARGC=$#

WORKFLOW_DOCS_DEST="${WORKFLOW_DOCS_DIR:-${HOME}/.cursor/workflow-docs}"
CLAUDE_WORKFLOW_DOCS_DEST="${CLAUDE_WORKFLOW_DOCS_DIR:-${HOME}/.claude/workflow-docs}"

usage() {
  sed -n '1,120p' <<'EOF'
Usage: sync-workflow-slash-commands.sh [options]

Run with no options on a terminal to open an interactive wizard. Pass any option
(or run in CI / a pipe) to take the non-interactive path and copy
my_work_tasks/commands/*.md and, by default, the agent skills to Cursor, Claude
Code, and/or Codex directories.

Options:
  --dry-run              Print actions only; do not write files.
  --profile=TIER         Which command set to install: minimal (the 12-command
                         everyday loop; the default), core (~50 commands), or full
                         (all 85 flat commands). Skills are never profile-filtered;
                         they always sync in full.
  --no-skills            Do NOT sync agent skills (skills sync by default).
  --with-skills          Sync agent skills (default; kept for backward compatibility).
  --clean-orphans        Also remove command files in the destinations that no
                         longer exist in the source (renamed or deleted commands).
                         Prompts for confirmation on a terminal; needs --yes in CI.
  --yes                  Assume yes for confirmations (non-interactive clean-orphans).
  --cursor-only          Update only the Cursor destination.
  --claude-only          Update only the Claude Code destination.
  --codex-only           Update only the Codex prompts destination.
  --cursor-dir=PATH      Override Cursor commands directory (default: ~/.cursor/commands).
  --claude-dir=PATH      Override Claude commands directory (default: ~/.claude/commands).
  --codex-dir=PATH       Override Codex prompts directory (default: ~/.codex/prompts).
  --project=PATH         Also copy into PATH/.cursor/commands and PATH/.claude/commands.
                         Codex custom prompts are user-local only, so --project does not
                         create project-level Codex prompts.
  --with-docs            Also copy workflow reference docs (the spec, README, demo, stubs, templates/)
                         into WORKFLOW_DOCS_DIR (default: ~/.cursor/workflow-docs),
                         CLAUDE_WORKFLOW_DOCS_DIR (default: ~/.claude/workflow-docs), and, if
                         --project is set, into PATH/.cursor/workflow-docs/.

Environment:
  CURSOR_COMMANDS_DIR    Same as --cursor-dir.
  CLAUDE_COMMANDS_DIR    Same as --claude-dir.
  CODEX_PROMPTS_DIR      Same as --codex-dir.
  WORKFLOW_DOCS_DIR      Destination for --with-docs, Cursor-side copy (default: ~/.cursor/workflow-docs).
  CLAUDE_WORKFLOW_DOCS_DIR  Second copy for Claude Code (default: ~/.claude/workflow-docs).
  CLAUDE_SKILLS_DIR      Skills destination, Claude Code (default: ~/.claude/skills).
  CURSOR_SKILLS_DIR      Skills destination, Cursor (default: ~/.cursor/skills).
  CODEX_SKILLS_DIR       Skills destination, OpenAI Codex (default: ~/.agents/skills).

Note: Command files reference WORKFLOW_OPERATING_SYSTEM.md and paths under this repo.
For best results, open Claude Code/Codex from my_work_tasks as cwd, or add this
repo via your normal workflow so those paths resolve.

Codex note: custom prompts load from ~/.codex/prompts and are invoked as
/prompts:<name> (for example /prompts:task-init). They are deprecated in favor
of skills, so the default skills sync is the recommended Codex workflow surface.
EOF
}

PROFILE="${PROFILE:-minimal}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --profile=*) PROFILE="${1#*=}" ;;
    --no-skills) WITH_SKILLS=0 ;;
    --with-skills) WITH_SKILLS=1 ;;
    --clean-orphans) DO_CLEAN_ORPHANS=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --cursor-only) DO_CLAUDE=0; DO_CODEX=0 ;;
    --claude-only) DO_CURSOR=0; DO_CODEX=0 ;;
    --codex-only) DO_CURSOR=0; DO_CLAUDE=0 ;;
    --cursor-dir=*) CURSOR_DEST="${1#*=}" ;;
    --claude-dir=*) CLAUDE_DEST="${1#*=}" ;;
    --codex-dir=*) CODEX_DEST="${1#*=}" ;;
    --project=*) PROJECT="${1#*=}" ;;
    --with-docs) WITH_DOCS=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ ! -d "$SRC" ]]; then
  echo "Source directory not found: $SRC" >&2
  exit 1
fi

# Profile filter (ADR-0059): the default profile is `minimal` (the 12-command
# everyday loop). Include a command file when its metadata.x-wos-profiles inline
# list contains the requested tier, or when the profile is explicitly empty
# (PROFILE= copies all, the pre-default behavior). minimal/core/full are distinct
# tokens, so a substring match against the inline list is sufficient.
file_in_profile() {
  local f="$1" p="$2" line
  [[ -z "$p" ]] && return 0
  line="$(awk '/^  x-wos-profiles:/{print; exit}' "$f")"
  [[ "$line" == *"$p"* ]] && return 0
  return 1
}

# ---------------------------------------------------------------------------
# State-detection helpers (read-only). Shared by the wizard's state panel and
# the end-of-run summary; they never write.
# ---------------------------------------------------------------------------
count_md() { # $1 = dir -> number of *.md files present
  find "$1" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' '
}

count_skills() { # $1 = dir -> number of skill subdirs present
  find "$1" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' '
}

detect_source() { # -> "<repo-basename> @ <branch>"
  local branch
  branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  printf '%s @ %s' "$(basename "$REPO_ROOT")" "$branch"
}

list_orphans() { # $1 = dest dir -> basenames present in dest but absent from SRC
  local dest="$1" f base
  [[ -d "$dest" ]] || return 0
  shopt -s nullglob
  for f in "$dest"/*.md; do
    base="$(basename "$f")"
    [[ -f "${SRC}/${base}" ]] || echo "$base"
  done
  shopt -u nullglob
}

sync_one_dest() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  echo "==> ${label}: ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    local would=0
    shopt -s nullglob
    for f in "${SRC}"/*.md; do
      file_in_profile "$f" "$PROFILE" || continue
      echo "    cp $(printf '%q' "$f") $(printf '%q' "${dest}/$(basename "$f")")"
      would=$((would + 1))
    done
    shopt -u nullglob
    echo "    would write ${would} markdown files (profile: ${PROFILE:-all})"
    return 0
  fi
  mkdir -p "$dest"
  local copied=0
  shopt -s nullglob
  for f in "${SRC}"/*.md; do
    file_in_profile "$f" "$PROFILE" || continue
    cp "$f" "${dest}/$(basename "$f")"
    copied=$((copied + 1))
  done
  shopt -u nullglob
  echo "    wrote ${copied} markdown files (profile: ${PROFILE:-all})"
}

sync_workflow_docs() {
  local label="$1"
  local dest="$2"
  echo "==> ${label} (docs): ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    echo "    cp WORKFLOW_OPERATING_SYSTEM.md README.md WORKFLOW_DEMO.md COMMAND_PROMPT_STUBS.md -> $(printf '%q' "$dest")"
    echo "    cp -R templates -> $(printf '%q' "$dest/templates")"
    return 0
  fi
  mkdir -p "${dest}/templates"
  cp "${REPO_ROOT}/WORKFLOW_OPERATING_SYSTEM.md" "${dest}/"
  cp "${REPO_ROOT}/README.md" "${dest}/"
  cp "${REPO_ROOT}/WORKFLOW_DEMO.md" "${dest}/"
  cp "${REPO_ROOT}/COMMAND_PROMPT_STUBS.md" "${dest}/"
  cp -R "${REPO_ROOT}/templates/"* "${dest}/templates/"
  echo "    copied the spec, README, DEMO, STUBS, and templates/"
}

sync_skills_dest() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  if [[ ! -d "$SKILLS_SRC" ]]; then
    echo "==> ${label}: skipped (source ${SKILLS_SRC} not present; run scripts/build-agent-skills.sh first)" >&2
    return 0
  fi
  echo "==> ${label}: ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    shopt -s nullglob
    for d in "${SKILLS_SRC}"/*/; do
      name="$(basename "$d")"
      echo "    cp -R $(printf '%q' "$d") $(printf '%q' "${dest}/${name}")"
    done
    shopt -u nullglob
    return 0
  fi
  mkdir -p "$dest"
  shopt -s nullglob
  local n=0
  for d in "${SKILLS_SRC}"/*/; do
    local name
    name="$(basename "$d")"
    rm -rf "${dest}/${name}"
    mkdir -p "${dest}/${name}"
    cp -R "$d"/. "${dest}/${name}/"
    n=$((n + 1))
  done
  shopt -u nullglob
  echo "    wrote ${n} skill(s)"
}

cleanup_legacy_codex_skills() {
  local legacy_dest="$1"

  # Codex moved user-level skills from ~/.codex/skills to ~/.agents/skills.
  # Only clean the legacy root when the canonical destination was not overridden,
  # and only remove names owned by this workflow. Leave unrelated skills intact.
  if [[ "$CODEX_SKILLS_DEST" != "$DEFAULT_CODEX_SKILLS_DEST" || ! -d "$legacy_dest" ]]; then
    return 0
  fi

  echo "==> OpenAI Codex legacy skill cleanup: ${legacy_dest}"
  shopt -s nullglob
  local n=0
  local d name
  for d in "${SKILLS_SRC}"/*/; do
    name="$(basename "$d")"
    if [[ ! -e "${legacy_dest}/${name}" ]]; then
      continue
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    rm -rf $(printf '%q' "${legacy_dest}/${name}")"
    else
      rm -rf -- "${legacy_dest}/${name}"
    fi
    n=$((n + 1))
  done
  shopt -u nullglob
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    would remove ${n} duplicate legacy skill(s)"
  else
    echo "    removed ${n} duplicate legacy skill(s)"
  fi
}

# ---------------------------------------------------------------------------
# Clean orphans: remove command files in the command destinations that no
# longer exist in the source (renamed or deleted commands). Strictly scoped:
# a dest file is removed only when its basename has NO match under commands/.
# ---------------------------------------------------------------------------
clean_orphans() {
  local dests=("$CURSOR_DEST" "$CLAUDE_DEST" "$CODEX_DEST")
  local labels=("Cursor" "Claude Code" "Codex")
  local found=0 i dest label base
  echo "Scanning for orphan command files (present in a destination, absent from source)..."
  for i in "${!dests[@]}"; do
    dest="${dests[$i]}"; label="${labels[$i]}"
    [[ -d "$dest" ]] || continue
    while IFS= read -r base; do
      [[ -z "$base" ]] && continue
      printf '  %-12s %s\n' "$label" "$base"
      found=$((found + 1))
    done < <(list_orphans "$dest")
  done
  if [[ "$found" -eq 0 ]]; then
    echo "  No orphans. Nothing to clean."
    return 0
  fi
  local confirm="n"
  if [[ -t 0 ]]; then
    printf 'Delete these %d file(s)? [y/N] ' "$found"
    read -r confirm || true
  elif [[ "$ASSUME_YES" -eq 1 ]]; then
    confirm="y"
  else
    echo "  (dry run: pass --yes to delete, or run with no flags for the wizard)"
    return 0
  fi
  case "$confirm" in
    y|Y|yes)
      for i in "${!dests[@]}"; do
        dest="${dests[$i]}"
        while IFS= read -r base; do
          [[ -z "$base" ]] && continue
          rm -f "${dest}/${base}"
        done < <(list_orphans "$dest")
      done
      echo "Removed ${found} orphan file(s)."
      ;;
    *) echo "Cancelled. Nothing deleted." ;;
  esac
}

# End-of-run summary: an honest line naming what was synced and how to get more.
print_summary() {
  local skills_txt cmd_txt
  if [[ "$WITH_SKILLS" -eq 1 ]]; then skills_txt="all skills"; else skills_txt="no skills"; fi
  cmd_txt="${PROFILE:-all} commands"
  echo ""
  echo "Summary: synced ${skills_txt} + ${cmd_txt} to the selected tools."
  if [[ "$PROFILE" == "minimal" ]]; then
    echo "  Only the 12 everyday commands are installed. For all 85, re-run with"
    echo "  --profile=full, or pick 'Sync everything' in the wizard (run with no flags)."
  fi
}

# ---------------------------------------------------------------------------
# Interactive wizard (pure bash; no dependency). Rendered only on a real TTY.
# ---------------------------------------------------------------------------
_MENU_SAVED_STTY=""
_menu_cleanup() {
  printf '\033[?25h'  # show cursor
  [[ -n "$_MENU_SAVED_STTY" ]] && stty "$_MENU_SAVED_STTY" 2>/dev/null || true
}

# menu_select "<prompt>" "Label|dim description" ...  -> sets MENU_CHOICE (index, -1 on quit)
menu_select() {
  local prompt="$1"; shift
  local options=("$@")
  local n=${#options[@]}
  local sel=0 first=1 key key2 i label desc
  _MENU_SAVED_STTY="$(stty -g 2>/dev/null || true)"
  trap '_menu_cleanup' EXIT INT TERM
  printf '\033[?25l'  # hide cursor
  stty -echo -icanon time 0 min 1 2>/dev/null || true
  while true; do
    if [[ $first -eq 0 ]]; then printf '\033[%dA' $((n + 1)); fi
    first=0
    printf '  \033[1m%s\033[0m\033[K\n' "$prompt"
    for ((i = 0; i < n; i++)); do
      label="${options[$i]%%|*}"
      desc="${options[$i]#*|}"; [[ "$desc" == "${options[$i]}" ]] && desc=""
      if [[ $i -eq $sel ]]; then
        printf '  \033[36m>\033[0m \033[1m%s\033[0m  \033[2m%s\033[0m\033[K\n' "$label" "$desc"
      else
        printf '    %s  \033[2m%s\033[0m\033[K\n' "$label" "$desc"
      fi
    done
    IFS= read -rsn1 key 2>/dev/null || true
    if [[ "$key" == $'\033' ]]; then
      IFS= read -rsn2 -t 1 key2 2>/dev/null || true
      key+="$key2"
    fi
    case "$key" in
      $'\033[A'|k) sel=$(( (sel - 1 + n) % n )) ;;
      $'\033[B'|j) sel=$(( (sel + 1) % n )) ;;
      ''|$'\n'|$'\r') break ;;
      q|Q) sel=-1; break ;;
    esac
  done
  _menu_cleanup
  trap - EXIT INT TERM
  MENU_CHOICE=$sel
}

show_header() {
  printf '\n'
  printf '  \033[1;38;5;208m🔥 Fhorja\033[0m  \033[2m·  workflow sync\033[0m\n'
  printf '  \033[2mMarkdown + bash. Wired into every tool.\033[0m\n\n'
}

show_state_panel() {
  local orphans
  printf '  \033[2mCurrent state\033[0m\n'
  printf '    %-12s %s skills · %s commands\n' "Claude Code" "$(count_skills "$CLAUDE_SKILLS_DEST")" "$(count_md "$CLAUDE_DEST")"
  printf '    %-12s %s skills · %s commands\n' "Cursor" "$(count_skills "$CURSOR_SKILLS_DEST")" "$(count_md "$CURSOR_DEST")"
  printf '    %-12s %s skills · %s prompts\n' "Codex" "$(count_skills "$CODEX_SKILLS_DEST")" "$(count_md "$CODEX_DEST")"
  printf '    %-12s %s\n' "Source" "$(detect_source)"
  orphans="$(list_orphans "$CLAUDE_DEST" | tr '\n' ' ')"
  if [[ -n "${orphans// /}" ]]; then
    printf '    \033[33m⚠ orphan commands:\033[0m %s\n' "$orphans"
  fi
  printf '\n'
}

wizard_custom() {
  menu_select "Which command set?" \
    "minimal|the 12 everyday commands" \
    "core|around 50 commands" \
    "full|all 85 commands"
  case "$MENU_CHOICE" in 0) PROFILE="minimal" ;; 1) PROFILE="core" ;; 2) PROFILE="" ;; esac
  menu_select "Sync skills too?" "Yes|recommended, the surface models actually load" "No|commands only"
  case "$MENU_CHOICE" in 0) WITH_SKILLS=1 ;; 1) WITH_SKILLS=0 ;; esac
}

run_wizard() {
  show_header
  show_state_panel
  menu_select "What do you want to do?" \
    "Sync everything|all skills + all 85 commands, every tool (recommended)" \
    "Everyday loop|all skills + the 12 core commands" \
    "Custom|choose the command set and skills" \
    "Health check|show what would change, write nothing" \
    "Clean orphans|remove stale command files no longer in source" \
    "Quit|"
  case "$MENU_CHOICE" in
    0) PROFILE=""; WITH_SKILLS=1; run_sync; print_summary ;;
    1) PROFILE="minimal"; WITH_SKILLS=1; run_sync; print_summary ;;
    2) wizard_custom; run_sync; print_summary ;;
    3) DRY_RUN=1; PROFILE=""; WITH_SKILLS=1; echo ""; run_sync ;;
    4) clean_orphans ;;
    *) echo "Nothing to do." ; return 0 ;;
  esac
}

# ---------------------------------------------------------------------------
# The non-interactive sync driver. Both the wizard and the scriptable path
# funnel through here; the wizard only collects intent into the same variables
# the flags set, so there is a single sync code path.
# ---------------------------------------------------------------------------
run_sync() {
  if [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_one_dest "Cursor" "$CURSOR_DEST"
  fi
  if [[ "$DO_CLAUDE" -eq 1 ]]; then
    sync_one_dest "Claude Code" "$CLAUDE_DEST"
  fi
  if [[ "$DO_CODEX" -eq 1 ]]; then
    sync_one_dest "OpenAI Codex prompts" "$CODEX_DEST"
  fi

  if [[ -n "$PROJECT" ]]; then
    if [[ ! -d "$PROJECT" ]]; then
      echo "Project path is not a directory: $PROJECT" >&2
      exit 1
    fi
    if [[ "$DO_CURSOR" -eq 1 ]]; then
      sync_one_dest "Cursor (project)" "${PROJECT}/.cursor/commands"
    fi
    if [[ "$DO_CLAUDE" -eq 1 ]]; then
      sync_one_dest "Claude Code (project)" "${PROJECT}/.claude/commands"
    fi
    if [[ "$DO_CODEX" -eq 1 ]]; then
      echo "==> OpenAI Codex prompts (project): skipped (Codex custom prompts are user-local under ~/.codex/prompts)"
    fi
  fi

  if [[ "$WITH_DOCS" -eq 1 ]]; then
    sync_workflow_docs "Workflow docs (Cursor)" "$WORKFLOW_DOCS_DEST"
    sync_workflow_docs "Workflow docs (Claude)" "$CLAUDE_WORKFLOW_DOCS_DEST"
    if [[ -n "$PROJECT" ]]; then
      sync_workflow_docs "Workflow docs (project / Cursor)" "${PROJECT}/.cursor/workflow-docs"
    fi
  fi

  if [[ "$WITH_SKILLS" -eq 1 ]]; then
    if [[ "$DO_CLAUDE" -eq 1 ]]; then
      sync_skills_dest "Claude Code skills" "$CLAUDE_SKILLS_DEST"
    fi
    if [[ "$DO_CURSOR" -eq 1 ]]; then
      sync_skills_dest "Cursor skills" "$CURSOR_SKILLS_DEST"
    fi
    if [[ "$DO_CODEX" -eq 1 ]]; then
      sync_skills_dest "OpenAI Codex skills" "$CODEX_SKILLS_DEST"
      cleanup_legacy_codex_skills "$LEGACY_CODEX_SKILLS_DEST"
    fi
    if [[ -n "$PROJECT" ]]; then
      if [[ "$DO_CLAUDE" -eq 1 ]]; then
        sync_skills_dest "Project Claude Code skills" "${PROJECT}/.claude/skills"
      fi
      if [[ "$DO_CURSOR" -eq 1 ]]; then
        sync_skills_dest "Project Cursor skills" "${PROJECT}/.cursor/skills"
      fi
      if [[ "$DO_CODEX" -eq 1 ]]; then
        sync_skills_dest "Project OpenAI Codex skills" "${PROJECT}/.agents/skills"
      fi
    fi
  fi

  if [[ "$DO_CLEAN_ORPHANS" -eq 1 ]]; then
    clean_orphans
  fi
}

# Interactivity gate (D-1): a bare invocation on a real terminal opens the
# wizard. Any flag, or a non-TTY stdin/stdout (CI, pipe, redirect), takes the
# scriptable path with the historical semantics.
if [[ "$INVOKED_ARGC" -eq 0 && -t 0 && -t 1 ]]; then
  run_wizard
else
  run_sync
  print_summary
fi

echo "Done."

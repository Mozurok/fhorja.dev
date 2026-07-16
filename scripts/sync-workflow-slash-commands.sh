#!/usr/bin/env bash
# Sync workflow command markdown files to Cursor, Claude Code, and Codex CLI command directories.
# Source: <repo>/commands/*.md  →  same filenames (e.g. task-init.md → /task-init in Claude Code).
#
# Defaults:
#   Cursor (legacy slash):  ~/.cursor/commands
#   Claude  (legacy slash):  ~/.claude/commands
#   Codex  (custom prompts): ~/.codex/prompts (invoked as /prompts:<name>)
#   Skills (open standard): ~/.claude/skills, ~/.cursor/skills, ~/.agents/skills (--with-skills)
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
WITH_SKILLS=0
PROJECT=""

WORKFLOW_DOCS_DEST="${WORKFLOW_DOCS_DIR:-${HOME}/.cursor/workflow-docs}"
CLAUDE_WORKFLOW_DOCS_DEST="${CLAUDE_WORKFLOW_DOCS_DIR:-${HOME}/.claude/workflow-docs}"

usage() {
  sed -n '1,100p' <<'EOF'
Usage: sync-workflow-slash-commands.sh [options]

Copy my_work_tasks/commands/*.md to Cursor, Claude Code, and/or Codex command
directories so the same bodies are available as slash commands where supported.

Options:
  --dry-run              Print actions only; do not write files.
  --profile=TIER         Which command set to install: minimal (the 12-command
                         everyday loop; the default), core (~50 commands), or full
                         (all 85 flat commands). Start with minimal and add the
                         rest with --profile=full when a task actually needs them.
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
  --with-skills          Also mirror .claude/skills/<name>/SKILL.md to user-level skill dirs:
                         CLAUDE_SKILLS_DIR (default: ~/.claude/skills),
                         CURSOR_SKILLS_DIR (default: ~/.cursor/skills),
                         CODEX_SKILLS_DIR (default: ~/.agents/skills). Project mirroring (if
                         --project is set) targets PATH/.claude/skills/, PATH/.cursor/skills/,
                         and PATH/.agents/skills/. Source files must already exist; run
                         scripts/build-agent-skills.sh first if you suspect drift.
                         When using the default Codex destination, also removes this
                         workflow's duplicate skills from the legacy ~/.codex/skills/ root.

Environment:
  CURSOR_COMMANDS_DIR    Same as --cursor-dir.
  CLAUDE_COMMANDS_DIR    Same as --claude-dir.
  CODEX_PROMPTS_DIR      Same as --codex-dir.
  WORKFLOW_DOCS_DIR      Destination for --with-docs, Cursor-side copy (default: ~/.cursor/workflow-docs).
  CLAUDE_WORKFLOW_DOCS_DIR  Second copy for Claude Code (default: ~/.claude/workflow-docs).
  CLAUDE_SKILLS_DIR      Destination for --with-skills, Claude Code (default: ~/.claude/skills).
  CURSOR_SKILLS_DIR      Destination for --with-skills, Cursor (default: ~/.cursor/skills).
  CODEX_SKILLS_DIR       Destination for --with-skills, OpenAI Codex (default: ~/.agents/skills).

Note: Command files reference WORKFLOW_OPERATING_SYSTEM.md and paths under this repo.
For best results, open Claude Code/Codex from my_work_tasks as cwd, or add this
repo via your normal workflow so those paths resolve.

Codex note: custom prompts load from ~/.codex/prompts and are invoked as
/prompts:<name> (for example /prompts:task-init). They are deprecated in favor
of skills, so use --with-skills for the recommended Codex workflow surface.
EOF
}

PROFILE="${PROFILE:-minimal}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --profile=*) PROFILE="${1#*=}" ;;
    --cursor-only) DO_CLAUDE=0; DO_CODEX=0 ;;
    --claude-only) DO_CURSOR=0; DO_CODEX=0 ;;
    --codex-only) DO_CURSOR=0; DO_CLAUDE=0 ;;
    --cursor-dir=*) CURSOR_DEST="${1#*=}" ;;
    --claude-dir=*) CLAUDE_DEST="${1#*=}" ;;
    --codex-dir=*) CODEX_DEST="${1#*=}" ;;
    --project=*) PROJECT="${1#*=}" ;;
    --with-docs) WITH_DOCS=1 ;;
    --with-skills) WITH_SKILLS=1 ;;
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

sync_one_dest() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  echo "==> ${label}: ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    shopt -s nullglob
    for f in "${SRC}"/*.md; do
      file_in_profile "$f" "$PROFILE" || continue
      echo "    cp $(printf '%q' "$f") $(printf '%q' "${dest}/$(basename "$f")")"
    done
    shopt -u nullglob
    return 0
  fi
  mkdir -p "$dest"
  shopt -s nullglob
  for f in "${SRC}"/*.md; do
    file_in_profile "$f" "$PROFILE" || continue
    cp "$f" "${dest}/$(basename "$f")"
  done
  shopt -u nullglob
  local n
  n="$(find "$dest" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
  echo "    wrote ${n} markdown files"
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

echo "Done."

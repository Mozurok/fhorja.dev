#!/usr/bin/env bash
# Sync workflow command markdown files to Cursor, Claude Code, Codex, and Kimi Code CLI directories.
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
#   Kimi   (skills only):    no custom-command directory exists; see the Kimi note below
#   Skills (open standard): ~/.claude/skills, ~/.cursor/skills, ~/.agents/skills (ON by default)
#
# Docs:
#   Cursor: project .cursor/commands or user commands (this script targets the user dir by default).
#   Claude Code: https://code.claude.com/docs/en/skills (custom commands under .claude/commands/)
#   Codex CLI: https://developers.openai.com/codex/custom-prompts
#              Custom prompts are deprecated; prefer skills for reusable workflows.
#              https://developers.openai.com/codex/skills
#   Kimi Code CLI: https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html
#                  https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/data-locations.html
#   Agent Skills (open standard): https://agentskills.io/specification
#
# Kimi note: Kimi Code CLI has no user-defined slash-command directory. Its entire
# customization surface is Agent Skills, invoked as /skill:<name>. At user level it
# scans $KIMI_CODE_HOME/skills (default ~/.kimi-code/skills) AND the generic
# ~/.agents/skills, so this script targets the generic directory by default: it is
# already written for Codex, both tools read it, and a second copy under the Kimi
# brand directory would register every skill twice. Point --kimi-dir at
# ~/.kimi-code/skills if you want a Kimi-owned copy instead.
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

# Kimi's home directory carries two names in the wild: the current Kimi Code CLI
# uses ~/.kimi-code (relocatable via KIMI_CODE_HOME), while the older open-source
# kimi-cli uses ~/.kimi. Detect whichever is actually installed instead of
# guessing, and fall back to the current one when neither exists yet.
resolve_kimi_home() {
  if [[ -n "${KIMI_CODE_HOME:-}" ]]; then printf '%s' "${KIMI_CODE_HOME%/}"; return 0; fi
  if [[ -d "${HOME}/.kimi-code" ]]; then printf '%s' "${HOME}/.kimi-code"; return 0; fi
  if [[ -d "${HOME}/.kimi" ]]; then printf '%s' "${HOME}/.kimi"; return 0; fi
  printf '%s' "${HOME}/.kimi-code"
}
KIMI_HOME="$(resolve_kimi_home)"
# Project-level skills live under the same brand directory name Kimi uses at home
# (.kimi-code/skills or .kimi/skills), so derive it rather than hardcoding one.
KIMI_BRAND_DIRNAME="$(basename "$KIMI_HOME")"
# Default to the generic cross-tool directory Kimi scans natively. See the Kimi
# note in the header for why this is not the brand-owned ~/.kimi-code/skills.
KIMI_SKILLS_DEST="${KIMI_SKILLS_DIR:-${HOME}/.agents/skills}"

DRY_RUN=0
DO_CURSOR=1
DO_CLAUDE=1
DO_CODEX=1
DO_KIMI=1
ONLY_MODE=0
WITH_DOCS=0
WITH_SKILLS=1          # skills ON by default (opt out with --no-skills)
DO_CLEAN_ORPHANS=0
ASSUME_YES=0
PROJECT=""
PROFILE_SET=0   # 1 only when the caller passed --profile=TIER explicitly (D-4, ADR-0059)

# Capture whether the script was invoked with zero arguments, before the arg
# loop consumes them. This drives the interactivity gate below: a bare, TTY
# invocation opens the wizard; any flag, or a non-TTY stdin/stdout (CI, pipe,
# redirect), takes the scriptable path with the historical semantics.
INVOKED_ARGC=$#

WORKFLOW_DOCS_DEST="${WORKFLOW_DOCS_DIR:-${HOME}/.cursor/workflow-docs}"
CLAUDE_WORKFLOW_DOCS_DEST="${CLAUDE_WORKFLOW_DOCS_DIR:-${HOME}/.claude/workflow-docs}"
# Codex had no docs destination, so a --codex-only sync installed prompts whose wos/ loads
# resolved nowhere: the payload was gated on the other two tools alone.
CODEX_WORKFLOW_DOCS_DEST="${CODEX_WORKFLOW_DOCS_DIR:-${HOME}/.codex/workflow-docs}"
# Kimi keeps its payload under its own home so it moves with KIMI_CODE_HOME, the
# same way the other three destinations sit next to the config each tool reads.
KIMI_WORKFLOW_DOCS_DEST="${KIMI_WORKFLOW_DOCS_DIR:-${KIMI_HOME}/workflow-docs}"

usage() {
  sed -n '1,160p' <<'EOF'
Usage: sync-workflow-slash-commands.sh [options]

Run with no options on a terminal to open an interactive wizard. Pass any option
(or run in CI / a pipe) to take the non-interactive path and copy
my_work_tasks/commands/*.md and, by default, the agent skills to Cursor, Claude
Code, Codex, and/or Kimi Code directories.

Options:
  --dry-run              Print actions only; do not write files.
  --profile=TIER         Which command set to install: minimal (the 12-command
                         everyday loop; the default), core (~50 commands), or full
                         (every flat command file). Passing --profile explicitly also
                         filters the skills mirror: core installs only core-tier
                         skills, full (or an empty --profile=) installs every
                         skill. minimal is REFUSED for skills (D-4, ADR-0059):
                         the tier stays gated until evals/scripts/structural-evals.py's
                         check_tier_routing_closure() reports a clean corpus (it
                         currently finds one open break). Add --no-skills to still
                         install the minimal command set with no skills. Omitting
                         --profile entirely leaves skills unfiltered, unchanged
                         from before D-4.
  --no-skills            Do NOT sync agent skills (skills sync by default).
  --with-skills          Sync agent skills (default; kept for backward compatibility).
  --clean-orphans        Also remove command files in the destinations that no
                         longer exist in the source (renamed or deleted commands).
                         Prompts for confirmation on a terminal; needs --yes in CI.
  --yes                  Assume yes for confirmations (non-interactive clean-orphans).
  --cursor-only          Update only the Cursor destination.
  --claude-only          Update only the Claude Code destination.
  --codex-only           Update only the Codex prompts destination.
  --kimi-only            Update only the Kimi Code destination (skills + runtime payload;
                         Kimi has no custom-command directory).
                         The four --*-only flags compose: passing two of them selects
                         both tools rather than cancelling each other out.
  --cursor-dir=PATH      Override Cursor commands directory (default: ~/.cursor/commands).
  --claude-dir=PATH      Override Claude commands directory (default: ~/.claude/commands).
  --codex-dir=PATH       Override Codex prompts directory (default: ~/.codex/prompts).
  --kimi-dir=PATH        Override the Kimi skills directory (default: ~/.agents/skills,
                         the generic directory Kimi scans natively). Use
                         --kimi-dir=~/.kimi-code/skills for a Kimi-owned copy.
  --project=PATH         Also copy into PATH/.cursor/commands and PATH/.claude/commands.
                         Codex custom prompts are user-local only, so --project does not
                         create project-level Codex prompts. Kimi has no command
                         directory at either level; its project skills go to
                         PATH/.agents/skills (or PATH/.kimi-code/skills under --kimi-dir).
  --with-docs            Also copy the optional reference docs (README, demo, stubs, templates/)
                         into WORKFLOW_DOCS_DIR (default: ~/.cursor/workflow-docs),
                         CLAUDE_WORKFLOW_DOCS_DIR (default: ~/.claude/workflow-docs), and, if
                         --project is set, into PATH/.cursor/workflow-docs/.

Environment:
  CURSOR_COMMANDS_DIR    Same as --cursor-dir.
  CLAUDE_COMMANDS_DIR    Same as --claude-dir.
  CODEX_PROMPTS_DIR      Same as --codex-dir.
  WORKFLOW_DOCS_DIR      Destination for --with-docs, Cursor-side copy (default: ~/.cursor/workflow-docs).
  CLAUDE_WORKFLOW_DOCS_DIR  Second copy for Claude Code (default: ~/.claude/workflow-docs).
  CODEX_WORKFLOW_DOCS_DIR   Third copy for Codex (default: ~/.codex/workflow-docs).
  KIMI_WORKFLOW_DOCS_DIR    Fourth copy for Kimi (default: <kimi-home>/workflow-docs).
  CLAUDE_SKILLS_DIR      Skills destination, Claude Code (default: ~/.claude/skills).
  CURSOR_SKILLS_DIR      Skills destination, Cursor (default: ~/.cursor/skills).
  CODEX_SKILLS_DIR       Skills destination, OpenAI Codex (default: ~/.agents/skills).
  KIMI_SKILLS_DIR        Skills destination, Kimi Code (default: ~/.agents/skills). Same as --kimi-dir.
  KIMI_CODE_HOME         Kimi's own home directory. Read, never set, by this script; it
                         picks the installed one (~/.kimi-code, then ~/.kimi) when unset.

Note: EVERY sync, with or without --with-docs, also writes the runtime payload
(WORKFLOW_OPERATING_SYSTEM.md + wos/) into the four workflow-docs destinations above, for
whichever tools the run targets. Every command's mandatory bootstrap reads four named
sections of the spec, and commands cite wos/<topic>.md with several of those loads MANDATORY,
so both are runtime dependencies rather than the optional reading material --with-docs
carries. The spec moved into the payload in ADR-0129; before that it shipped only to the
Cursor and Claude destinations, so a Codex- or Kimi-only machine could not bootstrap.

Note: Command files reference WORKFLOW_OPERATING_SYSTEM.md and paths under this repo.
For best results, open Claude Code/Codex from my_work_tasks as cwd, or add this
repo via your normal workflow so those paths resolve.

Codex note: custom prompts load from ~/.codex/prompts and are invoked as
/prompts:<name> (for example /prompts:task-init). They are deprecated in favor
of skills, so the default skills sync is the recommended Codex workflow surface.

Kimi note: Kimi Code CLI has no user-defined slash-command directory, so a Kimi
sync writes skills and the runtime payload only, and --no-skills leaves it with
the payload alone. Skills are invoked as /skill:<name> (for example
/skill:task-init). Kimi scans both <kimi-home>/skills and the generic
~/.agents/skills, and this script writes the generic one so a skill is not
registered twice.
EOF
}

PROFILE="${PROFILE:-minimal}"

# --<tool>-only used to be spelled as "turn the other two off", which stopped
# scaling at the fourth tool and made two such flags together cancel each other
# out (every destination off, a silent no-op). Selecting additively keeps the
# single-flag meaning identical and makes --claude-only --kimi-only mean those two.
select_only() {
  if [[ "$ONLY_MODE" -eq 0 ]]; then
    DO_CURSOR=0; DO_CLAUDE=0; DO_CODEX=0; DO_KIMI=0
    ONLY_MODE=1
  fi
  case "$1" in
    cursor) DO_CURSOR=1 ;;
    claude) DO_CLAUDE=1 ;;
    codex)  DO_CODEX=1 ;;
    kimi)   DO_KIMI=1 ;;
  esac
}

# Bash does not tilde-expand a `~` that follows `=` inside an ordinary argument,
# so --claude-dir=~/x used to create a literal directory named `~` under the CWD.
# Expand a leading ~ or ~/ before it reaches mkdir.
expand_tilde() {
  local p="$1"
  case "$p" in
    "~") printf '%s' "$HOME" ;;
    "~/"*) printf '%s' "${HOME}/${p#\~/}" ;;
    *) printf '%s' "$p" ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --profile=*) PROFILE="${1#*=}"; PROFILE_SET=1 ;;
    --no-skills) WITH_SKILLS=0 ;;
    --with-skills) WITH_SKILLS=1 ;;
    --clean-orphans) DO_CLEAN_ORPHANS=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --cursor-only) select_only cursor ;;
    --claude-only) select_only claude ;;
    --codex-only) select_only codex ;;
    --kimi-only) select_only kimi ;;
    --cursor-dir=*) CURSOR_DEST="$(expand_tilde "${1#*=}")" ;;
    --claude-dir=*) CLAUDE_DEST="$(expand_tilde "${1#*=}")" ;;
    --codex-dir=*) CODEX_DEST="$(expand_tilde "${1#*=}")" ;;
    --kimi-dir=*) KIMI_SKILLS_DEST="$(expand_tilde "${1#*=}")" ;;
    --project=*) PROJECT="$(expand_tilde "${1#*=}")" ;;
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

# Counted from the same glob sync_one_dest copies, so the number the wizard and
# the summary quote cannot drift from what a full sync actually writes. It used
# to be the hardcoded 85 of an older corpus, in three separate strings.
FLAT_COMMAND_COUNT="$(find "$SRC" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"

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

# Skill profile filter (D-4, ADR-0059). Same intent as file_in_profile(), but
# reads the generated .claude/skills/<name>/SKILL.md, not the canonical
# commands/*.md source. build-agent-skills.sh normalizes the canonical
# flow-style `x-wos-profiles: [core, full]` into spec-conformant block-style
# YAML on emit (see render_skill() in that script), so the shape here is:
#   x-wos-profiles:
#     - core
#     - full
# Only ever called with a tier the caller explicitly asked for; see
# skills_effective_profile() below for how that intent is derived.
skill_in_profile() {
  local skill_dir="$1" p="$2" f
  f="${skill_dir%/}/SKILL.md"
  [[ -z "$p" ]] && return 0
  [[ -f "$f" ]] || return 1
  awk -v want="$p" '
    /^  x-wos-profiles:/ { in_block=1; next }
    in_block && /^    - / { val=$0; sub(/^    - /, "", val); if (val == want) found=1; next }
    in_block { in_block=0 }
    END { exit(found ? 0 : 1) }
  ' "$f"
}

# The profile that actually gates the skills mirror. Skills stay unfiltered
# (empty string -> file_in_profile-style "copy everything") unless the caller
# passed --profile explicitly; PROFILE's own default ("minimal", set below for
# the *command* sync) must never leak into the skills filter, or a bare
# invocation would silently start refusing/filtering skills it always mirrored
# in full before D-4.
skills_effective_profile() {
  if [[ "$PROFILE_SET" -eq 1 ]]; then
    printf '%s' "$PROFILE"
  else
    printf ''
  fi
}

# D-4 (ADR-0059) skill-profile gate: minimal is refused for skills, explicitly,
# rather than silently downgraded to core. Only fires when the caller asked
# for it (PROFILE_SET=1 via --profile=minimal); the untouched default (no
# --profile flag at all) keeps mirroring every skill, unchanged from before
# D-4. Exits before any destination is touched.
refuse_minimal_skills_if_requested() {
  if [[ "$WITH_SKILLS" -eq 1 && "$PROFILE_SET" -eq 1 && "$PROFILE" == "minimal" ]]; then
    cat >&2 <<'EOF'
Refusing: skills cannot be mirrored at the minimal profile yet.

D-4 (ADR-0059, x-wos-profiles) gates the minimal skill tier on a lint rule
that enforces every command's own routing chain staying inside its own
declared x-wos-profiles tier. That rule is not clean yet:
evals/scripts/structural-evals.py's check_tier_routing_closure() reports one
open break (task-init is [minimal, core, full] and its own Express chain
routes to branch-commit, which is [core, full] only), so a minimal-tier skill
install would hand a user a documented next step it did not install.

Use --profile=core or --profile=full (or omit --profile) to install skills,
or add --no-skills to install the minimal command set with no skills.
EOF
    exit 1
  fi
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

# Two tools can legitimately resolve to the same directory: Kimi and Codex both
# read ~/.agents/skills, and any *_DIR override can collide by hand. Writing the
# same tree twice is wasted work at best and, on the skills side, a second
# rm -rf plus re-copy of a directory a concurrent reader may be scanning. Record
# what each phase already wrote and skip the repeat, out loud.
SYNCED_SKILL_DESTS="|"
SYNCED_PAYLOAD_DESTS="|"

# dest_is_new <list-contents> <dest> -> 0 when unseen. Callers append themselves.
dest_is_new() {
  local list="$1" d="${2%/}"
  [[ "$list" == *"|${d}|"* ]] && return 1
  return 0
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

# The RUNTIME payload: wos/, and only wos/. Distinct from --with-docs, which by its own
# help text carries optional reading material (the spec, README, demo, stubs, templates/).
# This is a runtime dependency: every command file cites at least one `wos/<topic>.md`, and
# several of those loads are declared MANDATORY, so a session bootstrapping from an
# installed copy was resolving them against nothing.
# Copied on EVERY sync, deliberately OUTSIDE the --with-docs gate: that flag defaults to 0
# and bootstrap-user-setup.sh never suggests it, so behind it the fix would not reach a new
# user, who is the population it exists for.
# NO scripts are shipped, per D-3 of the retro wave-1 task. A first pass shipped a measured
# subset and review found the measurement was the wrong one: it ranked by how often a script
# is MENTIONED, not by whether it can run where it lands. `portfolio-review.sh` derives its
# data root from its own file location, so the installed copy chdirs into this directory,
# finds no projects/, and prints a well-formed EMPTY board with exit 0 while a command is
# told to trust that output. Shipping a helper that answers confidently and wrongly is worse
# than shipping none. Which scripts can ship at all is a per-script question and has its own
# task.
sync_runtime_payload() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  if ! dest_is_new "$SYNCED_PAYLOAD_DESTS" "$dest"; then
    echo "==> ${label} (runtime payload): ${dest%/} already written this run; skipping duplicate copy"
    return 0
  fi
  SYNCED_PAYLOAD_DESTS="${SYNCED_PAYLOAD_DESTS}${dest%/}|"
  echo "==> ${label} (runtime payload): ${dest}"
  local topics
  topics="$(find "${REPO_ROOT}/wos" -name '*.md' | wc -l | tr -d ' ')"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "${dest}/wos")"
    echo "    cp WORKFLOW_OPERATING_SYSTEM.md -> $(printf '%q' "$dest")"
    echo "    cp -R wos/. -> $(printf '%q' "${dest}/wos")  (${topics} topics, recursive)"
    return 0
  fi
  mkdir -p "${dest}/wos"
  # The spec ships with the payload, not behind --with-docs (ADR-0129). Same argument as
  # wos/ above: the first item of EVERY command's mandatory context bootstrap is four named
  # sections of this file, so a session bootstrapping from an installed copy without it
  # resolves its first mandatory read against nothing. Before this, sync_workflow_docs was
  # called for the Cursor and Claude destinations only, so a Codex- or Kimi-only machine got
  # wos/ and no spec, and worked solely by falling back to a Claude install that happened to
  # sit beside it. --with-docs keeps the genuinely optional material (README, DEMO, STUBS,
  # templates/); the spec was never that.
  cp "${REPO_ROOT}/WORKFLOW_OPERATING_SYSTEM.md" "${dest}/"
  # Recursive: wos/ has subdirectories (bug-classes/), and a flat copy would drop them.
  cp -R "${REPO_ROOT}/wos/." "${dest}/wos/"
  echo "    copied WORKFLOW_OPERATING_SYSTEM.md + wos/ (${topics} topics)"
}

# The OPTIONAL reading material, behind --with-docs. The spec is deliberately NOT here
# any more (ADR-0129): it moved into sync_runtime_payload, which runs on every sync to
# every destination, because it is a runtime dependency rather than reading material.
sync_workflow_docs() {
  local label="$1"
  local dest="$2"
  echo "==> ${label} (docs): ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    echo "    cp README.md WORKFLOW_DEMO.md COMMAND_PROMPT_STUBS.md -> $(printf '%q' "$dest")"
    echo "    cp -R templates -> $(printf '%q' "$dest/templates")"
    return 0
  fi
  mkdir -p "${dest}/templates"
  cp "${REPO_ROOT}/README.md" "${dest}/"
  cp "${REPO_ROOT}/WORKFLOW_DEMO.md" "${dest}/"
  cp "${REPO_ROOT}/COMMAND_PROMPT_STUBS.md" "${dest}/"
  cp -R "${REPO_ROOT}/templates/"* "${dest}/templates/"
  echo "    copied README, DEMO, STUBS, and templates/ (the spec ships with the runtime payload)"
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
  if ! dest_is_new "$SYNCED_SKILL_DESTS" "$dest"; then
    echo "==> ${label}: ${dest%/} already written this run; skipping duplicate copy"
    return 0
  fi
  SYNCED_SKILL_DESTS="${SYNCED_SKILL_DESTS}${dest%/}|"
  local sp
  sp="$(skills_effective_profile)"
  echo "==> ${label}: ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    local would=0
    shopt -s nullglob
    for d in "${SKILLS_SRC}"/*/; do
      skill_in_profile "$d" "$sp" || continue
      name="$(basename "$d")"
      echo "    cp -R $(printf '%q' "$d") $(printf '%q' "${dest}/${name}")"
      would=$((would + 1))
    done
    shopt -u nullglob
    echo "    would write ${would} skill(s) (profile: ${sp:-all})"
    return 0
  fi
  mkdir -p "$dest"
  shopt -s nullglob
  local n=0
  for d in "${SKILLS_SRC}"/*/; do
    skill_in_profile "$d" "$sp" || continue
    local name
    name="$(basename "$d")"
    rm -rf "${dest}/${name}"
    mkdir -p "${dest}/${name}"
    cp -R "$d"/. "${dest}/${name}/"
    n=$((n + 1))
  done
  shopt -u nullglob
  echo "    wrote ${n} skill(s) (profile: ${sp:-all})"
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
  local skills_txt cmd_txt sp tools=""
  sp="$(skills_effective_profile)"
  if [[ "$WITH_SKILLS" -eq 1 ]]; then
    if [[ -n "$sp" ]]; then skills_txt="${sp}-tier skills"; else skills_txt="all skills"; fi
  else
    skills_txt="no skills"
  fi
  # Only claim a command install when a tool that HAS a command directory was
  # targeted. --kimi-only used to report "minimal commands" for a run that, by
  # Kimi's own design, installed no command file anywhere.
  if [[ "$DO_CURSOR" -eq 1 || "$DO_CLAUDE" -eq 1 || "$DO_CODEX" -eq 1 ]]; then
    cmd_txt=" + ${PROFILE:-all} commands"
  else
    cmd_txt=""
  fi
  [[ "$DO_CURSOR" -eq 1 ]] && tools="${tools}Cursor, "
  [[ "$DO_CLAUDE" -eq 1 ]] && tools="${tools}Claude Code, "
  [[ "$DO_CODEX" -eq 1 ]] && tools="${tools}Codex, "
  [[ "$DO_KIMI" -eq 1 ]] && tools="${tools}Kimi Code, "
  tools="${tools%, }"
  echo ""
  echo "Summary: synced ${skills_txt}${cmd_txt} to ${tools:-nothing (every destination was deselected)}."
  if [[ "$DO_KIMI" -eq 1 ]]; then
    echo "  Kimi Code got skills only (no custom-command directory exists); invoke them as /skill:<name>."
  fi
  if [[ "$PROFILE" == "minimal" && -n "$cmd_txt" ]]; then
    echo "  Only the 12 everyday commands are installed. For all ${FLAT_COMMAND_COUNT}, re-run with"
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
  printf '    %-12s %s skills · %s\n' "Kimi Code" "$(count_skills "$KIMI_SKILLS_DEST")" "no command dir"
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
    "full|all ${FLAT_COMMAND_COUNT} commands"
  case "$MENU_CHOICE" in 0) PROFILE="minimal" ;; 1) PROFILE="core" ;; 2) PROFILE="" ;; esac
  menu_select "Sync skills too?" "Yes|recommended, the surface models actually load" "No|commands only"
  case "$MENU_CHOICE" in 0) WITH_SKILLS=1 ;; 1) WITH_SKILLS=0 ;; esac
}

run_wizard() {
  show_header
  show_state_panel
  menu_select "What do you want to do?" \
    "Sync everything|all skills + all ${FLAT_COMMAND_COUNT} commands, every tool (recommended)" \
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
  refuse_minimal_skills_if_requested
  # Validate --project BEFORE any destination is written. It used to sit after the three
  # home sync_one_dest calls, so a bad path left a fully installed command set behind and
  # then aborted before the payload: commands present, every wos/ load resolving nowhere.
  if [[ -n "$PROJECT" ]] && [[ ! -d "$PROJECT" ]]; then
    echo "Project path is not a directory: $PROJECT" >&2
    exit 1
  fi
  if [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_one_dest "Cursor" "$CURSOR_DEST"
  fi
  if [[ "$DO_CLAUDE" -eq 1 ]]; then
    sync_one_dest "Claude Code" "$CLAUDE_DEST"
  fi
  if [[ "$DO_CODEX" -eq 1 ]]; then
    sync_one_dest "OpenAI Codex prompts" "$CODEX_DEST"
  fi
  if [[ "$DO_KIMI" -eq 1 ]]; then
    # Stated rather than silently omitted: Kimi Code CLI exposes no user-defined
    # slash-command directory, so there is nowhere for commands/*.md to land. Its
    # customization surface is Agent Skills, synced below and invoked as /skill:<name>.
    echo "==> Kimi Code commands: skipped (Kimi has no custom-command directory; its surface is skills, invoked as /skill:<name>)"
    if [[ "$WITH_SKILLS" -eq 0 ]]; then
      echo "    warning: with --no-skills, this run installs nothing for Kimi beyond the runtime payload." >&2
    fi
  fi

  if [[ -n "$PROJECT" ]]; then
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

  # Unconditional with respect to --with-docs, and that placement is the point: inside the
  # WITH_DOCS block below, the payload every command depends on would ship only to users who
  # already knew to ask for optional docs. Gated per tool like every sibling call, so
  # --cursor-only does not write a Claude destination.
  if [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Cursor)" "$WORKFLOW_DOCS_DEST"
  fi
  if [[ "$DO_CLAUDE" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Claude)" "$CLAUDE_WORKFLOW_DOCS_DEST"
  fi
  if [[ "$DO_CODEX" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Codex)" "$CODEX_WORKFLOW_DOCS_DEST"
  fi
  if [[ "$DO_KIMI" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Kimi)" "$KIMI_WORKFLOW_DOCS_DEST"
  fi
  if [[ -n "$PROJECT" ]] && [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (project / Cursor)" "${PROJECT}/.cursor/workflow-docs"
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
    if [[ "$DO_KIMI" -eq 1 ]]; then
      # Usually the same ~/.agents/skills Codex just wrote, in which case the
      # dedup guard reports the skip instead of copying 98 trees a second time.
      sync_skills_dest "Kimi Code skills" "$KIMI_SKILLS_DEST"
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
      if [[ "$DO_KIMI" -eq 1 ]]; then
        # Project level, Kimi scans <project>/.kimi-code/skills and <project>/.agents/skills.
        # Prefer the generic one for the same no-duplicate-registration reason as at
        # user level, and fall back to the brand directory when a --kimi-dir override
        # moved the user-level copy off the generic path.
        if [[ "$KIMI_SKILLS_DEST" == "${HOME}/.agents/skills" ]]; then
          sync_skills_dest "Project Kimi Code skills" "${PROJECT}/.agents/skills"
        else
          sync_skills_dest "Project Kimi Code skills" "${PROJECT}/${KIMI_BRAND_DIRNAME}/skills"
        fi
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

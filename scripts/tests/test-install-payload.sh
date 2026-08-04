#!/usr/bin/env bash
# test-install-payload.sh -- pins that the installer ships the RUNTIME payload on every
# sync, not only under --with-docs.
# Run from anywhere:  bash scripts/tests/test-install-payload.sh
#
# Why this exists. Every command file cites at least one `wos/<topic>.md`, and several
# of those loads are declared MANDATORY (an unread floor is a skipped gate, not a saved
# token). Before this, `sync_workflow_docs()` copied four .md files plus templates/ and
# nothing else, and it ran only under `--with-docs`, whose default is 0 and which
# `bootstrap-user-setup.sh` never suggests. So an installed session resolved those paths
# against nothing.
#
# The load-bearing check is check 1, and it is keyed on a run with NO FLAGS on purpose.
# Keying it on the copy function instead would be satisfiable while the payload stayed
# behind `--with-docs`, which is exactly what D-2 forbids: the criterion could not
# observe the failure it exists to prevent.
#
# Every run here points the installer at a scratch directory through the env overrides
# it already supports, so the real home is never touched.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYNC="$SCRIPT_DIR/../sync-workflow-slash-commands.sh"
fails=0
checks=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); echo "  FAIL $1"; fails=$((fails+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Run the installer fully sandboxed: every destination it knows about goes under $TMP.
# HOME is redirected FIRST and the explicit vars second, and that order is the point: every
# destination in the installer defaults to "${HOME}/...", so overriding HOME sandboxes any
# destination that exists now or is added later. The explicit list alone is a hand-maintained
# allowlist, and it already failed once: a Codex docs destination was added to the installer,
# not added here, and the run wrote 125 topics into the real home.
run_install() {  # run_install [extra-args...]
  HOME="$TMP/home" \
  CODEX_WORKFLOW_DOCS_DIR="$TMP/codex/workflow-docs" \
  CURSOR_COMMANDS_DIR="$TMP/cursor/commands" \
  CLAUDE_COMMANDS_DIR="$TMP/claude/commands" \
  CODEX_PROMPTS_DIR="$TMP/codex/prompts" \
  CLAUDE_SKILLS_DIR="$TMP/claude/skills" \
  CURSOR_SKILLS_DIR="$TMP/cursor/skills" \
  CODEX_SKILLS_DIR="$TMP/agents/skills" \
  WORKFLOW_DOCS_DIR="$TMP/cursor/workflow-docs" \
  CLAUDE_WORKFLOW_DOCS_DIR="$TMP/claude/workflow-docs" \
  bash "$SYNC" --no-skills "$@" >"$TMP/out.txt" 2>&1
  echo $?
}

REPO_WOS_COUNT="$(find "$REPO_ROOT/wos" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"

# Floor first. Both key checks used to be satisfiable at zero: with $REPO_ROOT/wos missing,
# the count compared 0 against 0 and the per-path loop read an empty stream, so the harness
# printed "0 of 0 topics" and self-certified against nothing.
if [ ! -d "$REPO_ROOT/wos" ] || [ "$REPO_WOS_COUNT" -lt 100 ]; then
  echo "HARNESS ERROR: source wos/ missing or implausibly small ($REPO_WOS_COUNT topics at $REPO_ROOT/wos)" >&2
  exit 2
fi

# THE assertion. One property, used at every destination, replacing three separate proxies
# (a file count, a per-path existence loop, a directory-exists test). Each proxy was passed by
# a degenerate installer: the count by a flattened tree, the path loop by zero-byte files, the
# directory test by a bare mkdir. `diff -r` compares structure AND content, so all three
# degenerate shapes fail it and no further proxy is needed.
payload_state() {  # payload_state <dest-root>; echoes '' when byte-identical to the repo
  local d="$1/wos"
  if [ ! -d "$d" ]; then printf 'absent'; return; fi
  if ! diff -r "$REPO_ROOT/wos" "$d" >/dev/null 2>&1; then printf 'differs from the repo tree'; return; fi
}

# Every destination the installer can write, so an "it wrote nothing" assertion means it,
# rather than checking one path and calling it proof.
ALL_DESTS=(
  "$TMP/cursor/commands" "$TMP/claude/commands" "$TMP/codex/prompts"
  "$TMP/cursor/workflow-docs" "$TMP/claude/workflow-docs" "$TMP/codex/workflow-docs"
  "$TMP/claude/skills" "$TMP/cursor/skills" "$TMP/agents/skills"
)
any_dest_written() {  # echoes the first destination that exists and is non-empty, or nothing
  local d
  for d in "${ALL_DESTS[@]}"; do
    if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then printf '%s' "$d"; return; fi
  done
}


# 1. THE ONE THAT MATTERS. A run with NO flags ships a payload byte-identical to the repo's
#    wos/. Keyed on a bare run, because keying it on the copy function would pass while the
#    payload stayed gated behind --with-docs.
rc=$(run_install)
state="$(payload_state "$TMP/claude/workflow-docs")"
[ "$rc" = "0" ] && [ -z "$state" ] \
  && pass "no-flag run ships wos/ byte-identical to the repo ($REPO_WOS_COUNT topics)" \
  || fail "no-flag run payload $state (exit $rc)"

# 2. The payload is not gated by --with-docs. Same assertion, stated so a future edit that
#    moves the copy back inside sync_workflow_docs() fails here rather than silently.
grep -q 'wos' <<<"$(sed -n '/^sync_workflow_docs()/,/^}/p' "$SYNC")" \
  && fail "the wos/ copy lives inside sync_workflow_docs(), which only runs under --with-docs" \
  || pass "the wos/ copy is outside sync_workflow_docs()"

# 3. Per-tool gating. --cursor-only must not write a Claude destination. The first pass
#    put these calls outside the DO_CURSOR / DO_CLAUDE guards every sibling call respects,
#    so a tool-scoped run wrote both trees while correctly writing zero excluded commands.
rm -rf "$TMP/claude" "$TMP/cursor"
rc=$(run_install --cursor-only)
if [ -d "$TMP/claude/workflow-docs/wos" ]; then
  fail "--cursor-only wrote the Claude payload"
elif [ -n "$(payload_state "$TMP/cursor/workflow-docs")" ]; then
  fail "--cursor-only Cursor payload: $(payload_state "$TMP/cursor/workflow-docs")"
else
  pass "--cursor-only wrote only the Cursor payload, byte-identical"
fi

# 3a. The mirror of 3, for the tool 3 does not cover. Exit criterion 2 names --cursor-only OR
#     --claude-only, and closure found only the first was ever run: the guards are symmetric in
#     the source, which is an argument, not evidence.
rm -rf "$TMP/claude" "$TMP/cursor"
rc=$(run_install --claude-only)
if [ -d "$TMP/cursor/workflow-docs/wos" ]; then
  fail "--claude-only wrote the Cursor payload"
elif [ -n "$(payload_state "$TMP/claude/workflow-docs")" ]; then
  fail "--claude-only Claude payload: $(payload_state "$TMP/claude/workflow-docs")"
else
  pass "--claude-only wrote only the Claude payload, byte-identical"
fi

# 3b. NO scripts subset ships (D-3). The previous version tested one hardcoded folder name at
#     one destination, so a rename or a different destination slipped past. This asserts the
#     property instead: nothing executable and no .sh/.py lands anywhere the payload writes.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex"
rc=$(run_install)
stray="$(find "$TMP/claude/workflow-docs" "$TMP/cursor/workflow-docs" "$TMP/codex/workflow-docs" \
           \( -name '*.sh' -o -name '*.py' -o -perm -u+x -type f \) 2>/dev/null | head -3)"
[ -z "$stray" ] \
  && pass "no executable or script file ships with the payload" \
  || fail "the payload shipped a script or executable: $(printf '%s' "$stray" | tr '\n' ' ' | cut -c1-140)"

# 3c. A bad --project path refuses BEFORE anything is written. The previous version accepted
#     ANY non-zero exit as "the refusal" and inspected one destination out of nine, so it went
#     green on a run that had already written 14 command files.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex" "$TMP/agents"
rc=$(run_install --project="$TMP/definitely-not-a-directory")
msg="$(cat "$TMP/out.txt")"
wrote="$(any_dest_written)"
if [ "$rc" = "0" ]; then
  fail "a bad --project did not refuse (exit 0)"
elif ! printf '%s' "$msg" | grep -q 'Project path is not a directory'; then
  fail "a bad --project exited $rc for some other reason, not the path check"
elif [ -n "$wrote" ]; then
  fail "a bad --project refused but had already written ${wrote#$TMP/}"
else
  pass "a bad --project refuses for the stated reason, with all 9 destinations untouched"
fi

# 3d. A valid --project receives the payload, which the analogous docs sync already served.
rm -rf "$TMP/claude" "$TMP/cursor"; mkdir -p "$TMP/proj"
rc=$(run_install --project="$TMP/proj")
state="$(payload_state "$TMP/proj/.cursor/workflow-docs")"
[ -z "$state" ] \
  && pass "--project receives a byte-identical payload" \
  || fail "--project payload $state (exit $rc)"

# 3e. --codex-only must ship the payload too. D-2 says every sync; the payload used to be
#     gated on the other two tools alone, so a codex-scoped run installed prompts whose
#     MANDATORY wos/ loads resolved against nothing on the whole machine.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex"
rc=$(run_install --codex-only)
state="$(payload_state "$TMP/codex/workflow-docs")"
[ -z "$state" ] \
  && pass "--codex-only ships a byte-identical payload" \
  || fail "--codex-only payload $state (exit $rc)"

# 4. --dry-run announces the payload instead of lying about what it copies.
rc=$(run_install --dry-run)
out="$(cat "$TMP/out.txt")"
if ! printf '%s' "$out" | grep -q 'wos'; then
  fail "--dry-run does not mention wos/, so the announcement understates the copy"
elif printf '%s' "$out" | grep -qE 'runtime script|scripts/ ->'; then
  fail "--dry-run still announces a scripts subset that D-3 removed"
else
  pass "--dry-run announces wos/ and no scripts subset"
fi

# 5. A dry run writes nothing. Guards the announcement added above from becoming a real copy.
# All FOUR payload destinations, not one. The previous version cleared and inspected only the
# Claude path, so a dry run that wrote 250 files to the other three still reported clean.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex" "$TMP/proj"; mkdir -p "$TMP/proj"
rc=$(run_install --dry-run --project="$TMP/proj")
wrote="$(find "$TMP/claude/workflow-docs" "$TMP/cursor/workflow-docs" "$TMP/codex/workflow-docs" \
           "$TMP/proj/.cursor/workflow-docs" -type f 2>/dev/null | wc -l | tr -d ' ')"
[ "$wrote" = "0" ] \
  && pass "--dry-run wrote no payload to any of the 4 destinations" \
  || fail "--dry-run WROTE $wrote file(s); a dry run must not touch any destination"

# LAST. The sandbox itself. Every installer destination defaults to ${HOME}/..., so anything
# found under the redirected HOME means a destination bypassed the explicit paths this harness
# names. Catching it here is what stops the next added destination from reaching the real home.
escaped="$(find "$TMP/home" -type f 2>/dev/null | head -3)"
[ -z "$escaped" ] \
  && pass "no destination escaped into HOME" \
  || fail "a destination wrote under HOME instead of a named path: $(printf '%s' "$escaped" | tr '\n' ' ' | cut -c1-140)"

echo
if [ "$fails" -eq 0 ]; then echo "test-install-payload: all $checks checks passed"; exit 0
else echo "test-install-payload: $fails of $checks check(s) FAILED"; exit 1; fi

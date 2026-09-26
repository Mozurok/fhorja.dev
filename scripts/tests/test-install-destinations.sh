#!/usr/bin/env bash
# test-install-destinations.sh -- pins where the installer writes skills, what it removes,
# and the checks it runs on itself (ADR-0228).
# Run from anywhere:  bash scripts/tests/test-install-destinations.sh
#
# What it asserts, each against a run of the real installer:
#   1. A default install writes the skills to ~/.claude/skills and ~/.agents/skills and
#      not to ~/.cursor/skills, and `--help` names exactly the roots the run wrote.
#   2. --cursor-skills writes ~/.cursor/skills as well.
#   3. --project follows the same default, and --cursor-skills restores its .cursor/skills.
#   4. --clean-orphans removes Fhorja skills from ~/.cursor/skills only after a confirmation,
#      never under --dry-run, and never a skill that is not Fhorja's, even one whose name
#      matches a Fhorja skill.
#   5. --print-skill-overrides prints a skillOverrides object and writes nothing.
#   6. The skills preflight: drift refuses before any write and names the fix command, a
#      machine without python3 gets a named line and the install continues, and --no-skills
#      skips the check.
#   7. The wizard's everyday option does not promise every skill.
#
# Every run sets HOME to a scratch directory and sets no other destination, so the defaults
# under test are the installer's own and the real home is never touched.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYNC="$REPO_ROOT/scripts/sync-workflow-slash-commands.sh"

fails=0
checks=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); echo "  FAIL $1"; fails=$((fails+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SKILL_N="$(find "$REPO_ROOT/.claude/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
CORE_N="$(grep -l 'x-wos-profiles: \[[^]]*core' "$REPO_ROOT"/commands/*.md "$REPO_ROOT"/commands/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
if [ "$SKILL_N" -lt 50 ] || [ "$CORE_N" -lt 10 ]; then
  echo "HARNESS ERROR: implausible skill counts ($SKILL_N skills, $CORE_N core) under $REPO_ROOT" >&2
  exit 2
fi

# run_in <home> <installer> [args...] -> exit code; output in $TMP/out.txt. stdin is
# /dev/null so a confirmation can never be answered by a terminal the test happens to run in.
run_in() {
  local home="$1" sync="$2"; shift 2
  mkdir -p "$home"
  HOME="$home" KIMI_CODE_HOME="$home/.kimi-code" bash "$sync" "$@" </dev/null >"$TMP/out.txt" 2>&1
  echo $?
}
skills_in() { find "$1" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' '; }

# 1. The default roots, and --help naming exactly those.
H="$TMP/h1"
rc=$(run_in "$H" "$SYNC")
c="$(skills_in "$H/.claude/skills")"; a="$(skills_in "$H/.agents/skills")"
if [ "$rc" != "0" ]; then
  fail "a default install exited $rc: $(tail -3 "$TMP/out.txt" | tr '\n' ' ' | cut -c1-160)"
elif [ "$c" != "$SKILL_N" ] || [ "$a" != "$SKILL_N" ]; then
  fail "a default install wrote $c skill(s) to ~/.claude/skills and $a to ~/.agents/skills, want $SKILL_N each"
elif [ -e "$H/.cursor/skills" ]; then
  fail "a default install wrote ~/.cursor/skills ($(skills_in "$H/.cursor/skills") skills); it is opt-in"
else
  pass "a default install writes $SKILL_N skills to ~/.claude/skills and ~/.agents/skills, none to ~/.cursor/skills"
fi
written="$(for d in "$H"/.*/skills; do [ -d "$d" ] && printf '~/%s\n' "${d#$H/}"; done | sort | tr '\n' ' ')"
named="$(bash "$SYNC" --help 2>&1 | sed -n 's/^Default skill roots: \(.*\)/\1/p' | grep -oE '~/\.[a-z-]+/skills' | sort | tr '\n' ' ')"
[ -n "$named" ] && [ "$named" = "$written" ] \
  && pass "--help names the default skill roots the run wrote ($named)" \
  || fail "--help names default skill roots '${named}', the default run wrote '${written}'"

# 2. --cursor-skills restores ~/.cursor/skills.
H="$TMP/h2"
rc=$(run_in "$H" "$SYNC" --cursor-skills)
[ "$rc" = "0" ] && [ "$(skills_in "$H/.cursor/skills")" = "$SKILL_N" ] && [ "$(skills_in "$H/.agents/skills")" = "$SKILL_N" ] \
  && pass "--cursor-skills writes ~/.cursor/skills as well as ~/.agents/skills" \
  || fail "--cursor-skills: exit $rc, ~/.cursor/skills holds $(skills_in "$H/.cursor/skills"), want $SKILL_N"

# 3. --project follows the same default.
H="$TMP/h3"; P="$TMP/proj3"; mkdir -p "$P"
rc=$(run_in "$H" "$SYNC" --project="$P")
if [ "$rc" != "0" ]; then
  fail "--project exited $rc"
elif [ -e "$P/.cursor/skills" ]; then
  fail "--project still writes PROJECT/.cursor/skills by default"
elif [ "$(skills_in "$P/.claude/skills")" != "$SKILL_N" ] || [ "$(skills_in "$P/.agents/skills")" != "$SKILL_N" ]; then
  fail "--project wrote $(skills_in "$P/.claude/skills") to .claude/skills and $(skills_in "$P/.agents/skills") to .agents/skills, want $SKILL_N each"
else
  pass "--project writes PROJECT/.claude/skills and PROJECT/.agents/skills, not PROJECT/.cursor/skills"
fi
P="$TMP/proj3b"; mkdir -p "$P"
rc=$(run_in "$TMP/h3b" "$SYNC" --project="$P" --cursor-skills)
[ "$rc" = "0" ] && [ "$(skills_in "$P/.cursor/skills")" = "$SKILL_N" ] \
  && pass "--project with --cursor-skills writes PROJECT/.cursor/skills" \
  || fail "--project --cursor-skills: exit $rc, PROJECT/.cursor/skills holds $(skills_in "$P/.cursor/skills")"

# 4. --clean-orphans and ~/.cursor/skills. Three skills planted: a real Fhorja skill copied
#    from the repo, a third-party skill with its own name, and a third-party skill that
#    borrows a Fhorja name but carries no x-wos-profiles key. Only the first may ever go.
H="$TMP/h4"; CS="$H/.cursor/skills"
plant() {
  rm -rf "$CS"; mkdir -p "$CS/other-vendor-skill" "$CS/review-hard"
  cp -R "$REPO_ROOT/.claude/skills/task-init" "$CS/task-init"
  printf -- '---\nname: other-vendor-skill\ndescription: not ours\n---\nbody\n' > "$CS/other-vendor-skill/SKILL.md"
  printf -- '---\nname: review-hard\ndescription: a user skill that shares a name\n---\nbody\n' > "$CS/review-hard/SKILL.md"
}
survivors() { ls "$CS" 2>/dev/null | sort | tr '\n' ' '; }
plant
rc=$(run_in "$H" "$SYNC" --no-skills --clean-orphans)
s="$(survivors)"
[ "$rc" = "0" ] && [ "$s" = "other-vendor-skill review-hard task-init " ] && grep -q "$CS/task-init" "$TMP/out.txt" \
  && pass "--clean-orphans without a confirmation lists the Fhorja skill and removes nothing" \
  || fail "--clean-orphans without a confirmation: exit $rc, left '$s'"
plant
rc=$(run_in "$H" "$SYNC" --no-skills --clean-orphans --yes --dry-run)
s="$(survivors)"
[ "$rc" = "0" ] && [ "$s" = "other-vendor-skill review-hard task-init " ] \
  && pass "--clean-orphans --yes under --dry-run removes nothing" \
  || fail "--clean-orphans --yes --dry-run left '$s' (exit $rc)"
plant
rc=$(run_in "$H" "$SYNC" --no-skills --clean-orphans --yes)
s="$(survivors)"
[ "$rc" = "0" ] && [ "$s" = "other-vendor-skill review-hard " ] \
  && pass "--clean-orphans --yes removes the Fhorja skill and keeps both skills that are not Fhorja's" \
  || fail "--clean-orphans --yes left '$s' (exit $rc); want other-vendor-skill and review-hard only"
plant
rc=$(run_in "$H" "$SYNC" --no-skills --clean-orphans --yes --cursor-skills)
s="$(survivors)"
[ "$rc" = "0" ] && [ "$s" = "other-vendor-skill review-hard task-init " ] \
  && pass "--clean-orphans leaves ~/.cursor/skills alone while --cursor-skills keeps it a destination" \
  || fail "--clean-orphans --cursor-skills left '$s' (exit $rc)"

# 5. --print-skill-overrides prints and writes nothing.
H="$TMP/h5"; mkdir -p "$H"
HOME="$H" bash "$SYNC" --print-skill-overrides=core </dev/null >"$TMP/ov.json" 2>"$TMP/ov.err"; rc=$?
n="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); v=d["skillOverrides"]; assert set(v.values())=={"name-only"}; print(len(v))' "$TMP/ov.json" 2>/dev/null)"
if [ "$rc" != "0" ]; then
  fail "--print-skill-overrides=core exited $rc"
elif [ "$n" != "$((SKILL_N - CORE_N))" ]; then
  fail "--print-skill-overrides=core printed ${n:-no valid object}, want $((SKILL_N - CORE_N)) name-only entries"
elif [ -n "$(find "$H" -mindepth 1 2>/dev/null | head -1)" ]; then
  fail "--print-skill-overrides wrote under HOME: $(find "$H" -mindepth 1 | head -2 | tr '\n' ' ')"
else
  pass "--print-skill-overrides=core prints $n name-only entries as JSON and writes nothing"
fi
HOME="$H" bash "$SYNC" --print-skill-overrides=full </dev/null >/dev/null 2>&1; rc=$?
[ "$rc" = "2" ] && pass "--print-skill-overrides refuses a tier other than minimal or core (exit 2)" \
  || fail "--print-skill-overrides=full exited $rc, want 2"

# 6. The skills preflight, run from a copy of the parts of the repository the installer and
#    build-agent-skills.sh read, so a drifted skill can be planted without touching the tree.
COPY="$TMP/repo"; mkdir -p "$COPY"
for part in commands .claude scripts wos templates WORKFLOW_OPERATING_SYSTEM.md README.md WORKFLOW_DEMO.md COMMAND_PROMPT_STUBS.md; do
  cp -R "$REPO_ROOT/$part" "$COPY/$part"
done
if ! bash "$COPY/scripts/build-agent-skills.sh" --check >/dev/null 2>&1; then
  fail "control: build-agent-skills.sh --check fails on the unmodified copy, so the drift case below proves nothing"
else
  pass "control: the unmodified copy passes build-agent-skills.sh --check"
fi
printf '\nA line the generator never wrote.\n' >> "$COPY/.claude/skills/task-init/SKILL.md"
H="$TMP/h6"
rc=$(run_in "$H" "$COPY/scripts/sync-workflow-slash-commands.sh")
wrote="$(find "$H" -type f 2>/dev/null | head -1)"
if [ "$rc" = "0" ]; then
  fail "a drifted .claude/skills installed anyway (exit 0)"
elif ! grep -q 'Fix: ./scripts/build-agent-skills.sh' "$TMP/out.txt"; then
  fail "the drift refusal does not print the fix command: $(tail -2 "$TMP/out.txt" | tr '\n' ' ' | cut -c1-160)"
elif [ -n "$wrote" ]; then
  fail "the drift refusal came after a write: ${wrote#$H/}"
else
  pass "a drifted .claude/skills is refused before any write, with the fix command named"
fi
H="$TMP/h6b"
rc=$(run_in "$H" "$COPY/scripts/sync-workflow-slash-commands.sh" --no-skills)
[ "$rc" = "0" ] && ! grep -q 'Skills check' "$TMP/out.txt" \
  && pass "--no-skills skips the skills check (the drifted copy installs its commands, exit 0)" \
  || fail "--no-skills: exit $rc, or the skills check ran anyway"
# A PATH that has every tool on this machine except python3.
NOPY="$TMP/nopy"; mkdir -p "$NOPY"
IFS=: read -ra path_dirs <<<"$PATH"
for d in "${path_dirs[@]}"; do [ -d "$d" ] && ln -s "$d"/* "$NOPY"/ 2>/dev/null; done
rm -f "$NOPY"/python3*
if PATH="$NOPY" command -v python3 >/dev/null 2>&1 || ! PATH="$NOPY" command -v bash >/dev/null 2>&1; then
  fail "harness: could not build a PATH without python3 that still has bash"
else
  H="$TMP/h6c"
  rc=$(PATH="$NOPY" run_in "$H" "$COPY/scripts/sync-workflow-slash-commands.sh")
  if [ "$rc" != "0" ]; then
    fail "without python3 the install stopped (exit $rc): $(tail -2 "$TMP/out.txt" | tr '\n' ' ' | cut -c1-160)"
  elif ! grep -q 'skills not checked: python3 absent' "$TMP/out.txt"; then
    fail "without python3 the install continued without naming the skipped check"
  elif [ "$(skills_in "$H/.claude/skills")" != "$SKILL_N" ]; then
    fail "without python3 the install wrote $(skills_in "$H/.claude/skills") skills, want $SKILL_N"
  else
    pass "without python3 the install prints 'skills not checked: python3 absent' and continues"
  fi
fi

# 7. The wizard's everyday option installs the minimal skills (set_profile minimal filters
#    them), so its label must not promise every skill.
label="$(grep -E '"Everyday loop\|' "$SYNC" | head -1)"
arm="$(grep -E '^[[:space:]]+1\) set_profile ' "$SYNC" | head -1)"
if [ -z "$label" ] || [ -z "$arm" ]; then
  fail "the wizard's everyday option or its case arm is gone; the label check lost its subject"
elif printf '%s' "$arm" | grep -q 'set_profile minimal' && printf '%s' "$label" | grep -qi 'all skills'; then
  fail "the wizard labels the minimal-profile option 'all skills': $label"
else
  pass "the wizard's everyday option does not promise every skill"
fi

echo
if [ "$fails" -eq 0 ]; then echo "test-install-destinations: all $checks checks passed"; exit 0
else echo "test-install-destinations: $fails of $checks check(s) FAILED"; exit 1; fi

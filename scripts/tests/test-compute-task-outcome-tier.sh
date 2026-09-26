#!/usr/bin/env bash
# test-compute-task-outcome-tier.sh: read_pipeline_tier() over the shapes on disk.
#
# The field reads the ADR-0025 tier out of the '## Recommended pipeline' section
# task-init already writes. It does NOT add a field to TASK_STATE.md, which is
# what makes it measurement rather than a new product surface.
#
# The case worth staring at is check 5. templates/TASK_STATE.template.md used to
# ship the unfilled menu '[Express | Standard | Disciplined | Strict]'; ADR-0207
# retired the tier names and the template now carries an 'Escalations:' line
# instead, but task folders written before that still hold the menu. A parser
# that takes the first tier word reads every such untouched menu as Express,
# which would bias the exact comparison this field exists to make. The rule is
# one tier or none.
#
# Check 8 covers the other silent-drift risk: the helper has two exits, the
# normal record and the except-path fallback in main(), and a field present in
# only one of them is drift nobody sees until a reader hits a KeyError.
#
# Checks 13 to 21 cover the `escalations` field that replaces tier for tasks
# opened since ADR-0207 (D-12 of the 2026-09-22 docs-drift-audit task), and the
# portfolio-review --outcomes grouping over a ledger mixing new and legacy rows.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="${SCRIPT_DIR}/../compute-task-outcome.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# A task folder the helper accepts: projects/<project>/active/<task>/
make_task() {  # make_task <slug> <task-state-body>; echoes the folder
  local d="$TMP/projects/acme__demo/active/2026-08-30_$1"
  mkdir -p "$d"
  printf '%s\n' "$2" > "$d/TASK_STATE.md"
  echo "$d"
}

tier_of() {  # tier_of <task-folder>; echoes the tier field, or ERROR
  python3 "$HELPER" "$1" --merge-status merged 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["tier"])' 2>/dev/null \
    || echo ERROR
}

expect() {  # expect <task-folder> <expected> <label>
  local got; got="$(tier_of "$1")"
  [ "$got" = "$2" ] && pass "$3" || fail "$3 (got '$got', expected '$2')"
}

expect "$(make_task labelled "## Recommended pipeline
- Tier: Express
- task-init, implementation-plan")" Express "1. labelled line"

expect "$(make_task bold "## Recommended pipeline
- **Tier**: Standard")" Standard "2. labelled line in bold"

expect "$(make_task trailing "## Recommended pipeline
Tier: Strict (ADR-0025).")" Strict "3. labelled line with trailing prose"

expect "$(make_task unlabelled "## Recommended pipeline
The Disciplined sequence, since three subsystems move at once.")" Disciplined \
  "4. section body, no labelled line"

expect "$(make_task placeholder "## Recommended pipeline
- Tier: [Express | Standard | Disciplined | Strict]
- [ordered next commands]")" None "5. unfilled template menu reads as no answer"

expect "$(make_task nosection "## Current phase
implementation")" None "6. section absent"

# A folder with no TASK_STATE.md at all: the helper degrades, never tracebacks.
EMPTY="$TMP/projects/acme__demo/active/2026-08-30_nofile"; mkdir -p "$EMPTY"
expect "$EMPTY" None "7. TASK_STATE.md missing"
python3 "$HELPER" "$EMPTY" --merge-status merged >/dev/null 2>&1 \
  && pass "7b. missing TASK_STATE.md still exits 0" \
  || fail "7b. missing TASK_STATE.md still exits 0"

# A folder that does not exist is refused by name. Until 2026-09-22 this case printed a
# well-formed line with project null and exit 0, and this test asserted only that the line
# carried the tier key, under the name "exception path", which it never reached.
MISSING_ERR="$(python3 "$HELPER" "$TMP/does-not-exist" --merge-status merged 2>&1 >/dev/null)"
MISSING_RC=$?
if [[ "$MISSING_RC" -ne 0 && "$MISSING_ERR" == *"task folder not found"* ]]; then
  pass "8. a missing task folder is refused by name"
else
  fail "8. a missing task folder is refused by name (rc=$MISSING_RC)"
fi

# --- B1: a tier name read out of prose that DENIES it --------------------------
# The live defect, pinned with the exact sentence that caused it. On 2026-09-16
# "the strict-surface disqualifier does not fire" resolved to Strict and was
# written into OUTCOMES.jsonl twice. The guard keys on the `Escalations:` line,
# which ADR-0207 introduced when it retired the tier labels, so a section
# carrying one was written after the labels stopped meaning anything.
expect "$(make_task denial "## Recommended pipeline
\`task-init\` -> \`implementation-plan\`, minimal profile.

Escalations: 2. \`impact-analysis\` fires. \`decision-interview\` fires. The strict-surface
disqualifier does not fire: this repository is markdown and bash.")" None \
  "9. a denial inside an Escalations section yields None, not the denied tier"

# The control on check 9. Remove the Escalations line and the SAME prose must
# resolve to Strict again, which is what proves check 9 measures the guard and
# not some unrelated property of the fixture.
expect "$(make_task denial_nogaurd "## Recommended pipeline
\`task-init\` -> \`implementation-plan\`, minimal profile.

The strict-surface disqualifier does not fire: this repository is markdown and bash.")" Strict \
  "10. control: the same prose without Escalations still resolves, so check 9 is measuring the guard"

# A labelled line is a DECLARATION and still wins, even beside an Escalations line.
expect "$(make_task labelled_with_esc "## Recommended pipeline
- Tier: Disciplined

Escalations: none.")" Disciplined \
  "11. a labelled Tier: still wins inside an Escalations section"

# The 137 legacy sections with no labelled line and no Escalations keep resolving.
expect "$(make_task legacy "## Recommended pipeline
This is a Standard task with no labelled line.")" Standard \
  "12. legacy fallback is untouched"

# --- D-12: the `escalations` field (B35) -------------------------------------
# ADR-0207 said the ledger would record which disqualifiers fired. The field is
# the command list from the `Escalations:` line, reasons dropped; [] for none,
# null when the line is absent. `tier` stays beside it as the legacy field, and
# schema_version does not move, because the field is additive.
field_of() {  # field_of <task-folder> <field>; echoes the field as JSON, or ERROR
  python3 "$HELPER" "$1" --merge-status merged 2>/dev/null \
    | python3 -c 'import json,sys; r=json.load(sys.stdin); print(json.dumps(r[sys.argv[1]]))' "$2" 2>/dev/null \
    || echo ERROR
}

expect_field() {  # expect_field <task-folder> <field> <expected-json> <label>
  local got; got="$(field_of "$1" "$2")"
  [ "$got" = "$3" ] && pass "$4" || fail "$4 (got '$got', expected '$3')"
}

ESC_NONE="$(make_task esc_none "## Recommended pipeline
- Escalations: none
- task-init -> implementation-plan -> implement-approved-slice -> branch-commit")"
expect_field "$ESC_NONE" escalations '[]' "13. Escalations: none reads as an empty list"
expect_field "$ESC_NONE" tier 'null' "13b. the same task keeps tier, null beside an Escalations line"

ESC_TWO="$(make_task esc_two "## Recommended pipeline
- Escalations: impact-analysis (the scope needs more than one sentence, and the change
  touches far more than 5 files, so review-hard alone would not see it); decision-interview (the
  retry policy is not in the brief)
- task-init -> impact-analysis -> decision-interview -> implementation-plan")"
expect_field "$ESC_TWO" escalations '["impact-analysis", "decision-interview"]' \
  "14. two fired escalations with wrapped reasons read as the two command names only"

ESC_ABSENT="$(make_task esc_absent "## Recommended pipeline
- task-init -> implementation-plan")"
expect_field "$ESC_ABSENT" escalations 'null' "15. an absent Escalations line reads as null"

ESC_MENU="$(make_task esc_menu "## Recommended pipeline
- Escalations: [none | <added command> (<disqualifier that fired>), ...]
- [ordered next commands]")"
expect_field "$ESC_MENU" escalations 'null' "15b. the unfilled template menu reads as null, not as none"

ESC_LEGACY="$(make_task esc_legacy "## Recommended pipeline
- Tier: Standard
- task-init -> impact-analysis -> implementation-plan")"
expect_field "$ESC_LEGACY" escalations 'null' "16. a legacy Tier-only state has null escalations"
expect_field "$ESC_LEGACY" tier '"Standard"' "16b. and still carries its tier"

expect_field "$ESC_TWO" schema_version '1' "17. schema_version is unchanged by the additive field"
FALLBACK_KEYS="$(sed -n '/degradation rule: never traceback/,/print(json.dumps(record))/p' "$HELPER" \
  | grep -c '"escalations": None')"
[ "$FALLBACK_KEYS" -ge 1 ] \
  && pass "17b. the except-path fallback record carries escalations too" \
  || fail "17b. the except-path fallback record carries escalations too"

# portfolio-review --outcomes over a small ledger mixing new and legacy rows.
# The script reads projects/ in the directory it runs from (ADR-0224), so it runs from a fixture tree.
PR_ROOT="$TMP/pr"
mkdir -p "$PR_ROOT/scripts" "$PR_ROOT/projects/acme__demo"
cp "${SCRIPT_DIR}/../portfolio-review.sh" "$PR_ROOT/scripts/"
line() {  # line <task> <total> <tier-json> [escalations-json]; one outcome line
  local esc=""
  [ $# -ge 4 ] && esc=",\"escalations\":$4"
  printf '{"schema_version":1,"event":"outcome","ts":"2026-09-23T10:00:00.000Z","project":"acme__demo","task":"%s","phases":null,"phase_days":{"total":%s},"merge_status":"merged","merge_evidence":null,"tier":%s%s,"source":"compute-task-outcome.py","run_id":"x"}\n' \
    "$1" "$2" "$3" "$esc"
}
{
  line t-new-none 1.0 null '[]'
  line t-new-none-2 3.0 null '[]'
  line t-new-two 5.0 null '["impact-analysis","decision-interview"]'
  line t-new-two-b 7.0 null '["decision-interview","impact-analysis"]'
  line t-legacy-std 4.0 '"Standard"'
  line t-legacy-nulled 6.0 '"Express"' null
  line t-neither 9.0 null
} > "$PR_ROOT/projects/acme__demo/OUTCOMES.jsonl"
PR_OUT="$(cd "$PR_ROOT" && bash "$PR_ROOT/scripts/portfolio-review.sh" --outcomes 2>&1)"
PR_RC=$?
echo "$PR_OUT" | sed 's/^/       | /'
[ "$PR_RC" -eq 0 ] && pass "18. --outcomes exits 0 over a mixed ledger" \
  || fail "18. --outcomes exits 0 over a mixed ledger (rc=$PR_RC)"
[[ "$PR_OUT" == *"closed tasks: 7"* ]] && pass "18b. every row is read, new and legacy" \
  || fail "18b. every row is read, new and legacy"
[[ "$PR_OUT" == *"by escalation profile (rows with escalations): none=2.00 (n=2) decision-interview+impact-analysis=6.00 (n=2)"* ]] \
  && pass "19. new rows group by escalation profile, the fired set taken as a set" \
  || fail "19. new rows group by escalation profile, the fired set taken as a set"
[[ "$PR_OUT" == *"by legacy tier (rows with a tier and no escalations): Express=6.00 (n=1) Standard=4.00 (n=1)"* ]] \
  && pass "20. legacy rows stay readable under their tier, a null escalations included" \
  || fail "20. legacy rows stay readable under their tier, a null escalations included"
[[ "$PR_OUT" == *"unknown (rows with neither): 9.00 (n=1)"* ]] \
  && pass "21. a row with neither goes to unknown" \
  || fail "21. a row with neither goes to unknown"

# 22. Freeform prose on the Escalations line records no command, even a hyphenated word.
FREE="$TMP/projects/acme__demo/active/2026-09-23_freeform"; mkdir -p "$FREE"
printf '# TASK_STATE\n\n## Recommended pipeline\n- Escalations: runtime test behavior. Bounded analysis, single-slice plan, implementation.\n' > "$FREE/TASK_STATE.md"
got="$(python3 "$HELPER" "$FREE" --merge-status merged 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["escalations"])')"
[ "$got" = "None" ] && pass "22. freeform prose on the line reads as null, not as single-slice" \
                   || fail "22. freeform prose on the line reads as null (got $got)"

# 23. The fixed escalation set matches the commands task-init names in its Escalation assessment.
TASK_INIT_CMD="${SCRIPT_DIR}/../../commands/task-init.md"
SET="$(python3 -c "
import importlib.util
s=importlib.util.spec_from_file_location('c','$HELPER'); c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
print(' '.join(sorted(c.ESCALATION_COMMANDS)))")"
INIT="$(awk '/Escalation assessment/{f=1} f&&/State the escalation set/{exit} f' "$TASK_INIT_CMD" | grep -E '^[[:space:]]*- Add ' | grep -oE '`[a-z]+(-[a-z]+)+`' | tr -d '`' | sort -u | tr '\n' ' ' | sed 's/ $//')"
[ "$SET" = "$INIT" ] && pass "23. the fixed escalation set matches task-init ($SET)" \
                     || fail "23. the fixed escalation set ($SET) differs from task-init ($INIT)"

echo ""
echo "test-compute-task-outcome-tier: ${checks} check(s), ${fails} failure(s)"
[ "$fails" -eq 0 ]

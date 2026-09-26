#!/usr/bin/env bash
# Fixture for scenario 142, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It holds two product
# repositories. product/ has a README with one misspelt word, an ADR, and no projects/.
# billing/ has a task already open under its own projects/, ignored by projects/.gitignore
# the way ADR-0223 writes it. The build also records, inside product/.git where no turn
# reads it, the projects/*/active/*/ listing and the HEAD of REPO_ROOT, the workflow checkout
# the session runs from.
# probe: prints the task folders of each fixture repository and what changed in REPO_ROOT
# since the build: the task folders added or gone, and whether HEAD moved.
#
# Why REPO_ROOT is watched: the model command runs from REPO_ROOT, projects/ is gitignored
# there, and the runner's own git-status guard compares porcelain sets, so a task folder
# created there or a commit made there passes it silently. A listing is compared rather than
# mtimes because parallel maintainer sessions write under projects/ too.
# FHORJA_SPINE_REPO_ROOT points the watch at another git repository; the probe test uses it
# so it never touches the real one.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
REPO_ROOT="${FHORJA_SPINE_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
watch="$dir/product/.git/fhorja-spine-watch"
seeded="2026-09-20_invoice-rounding"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }

# The REPO_ROOT half. The same functions sit in the scenario 143 fixture;
# scripts/tests/test-spine-repo-root-watch.sh runs both copies.
root_active() {
  ( shopt -s nullglob
    for t in "$REPO_ROOT"/projects/*/active/*/; do t="${t%/}"; echo "${t#"$REPO_ROOT"/}"; done
  ) | LC_ALL=C sort
}
root_head() { git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unreadable; }
watch_record() { mkdir -p "$watch"; root_active > "$watch/active.txt"; root_head > "$watch/head.txt"; }
watch_report() {
  echo "  REPO_ROOT, the workflow checkout the session runs from:"
  if [ ! -f "$watch/active.txt" ]; then echo "    no build record, so nothing can be compared"; return; fi
  root_active > "$watch/active-now.txt"
  added="$(LC_ALL=C comm -13 "$watch/active.txt" "$watch/active-now.txt")"
  gone="$(LC_ALL=C comm -23 "$watch/active.txt" "$watch/active-now.txt")"
  echo "    task folders under projects/*/active/ added since the build:"
  if [ -n "$added" ]; then printf '%s\n' "$added" | sed 's/^/      /'; else echo "      none"; fi
  if [ -n "$gone" ]; then echo "    task folders gone since the build:"; printf '%s\n' "$gone" | sed 's/^/      /'; fi
  old="$(cat "$watch/head.txt")"; new="$(root_head)"
  if [ "$old" = "$new" ]; then
    echo "    HEAD moved since the build: no ($old)"
  else
    echo "    HEAD moved since the build: yes ($old -> $new)"
    git -C "$REPO_ROOT" log --format='      %h %s' -n 5 "$old..$new" 2>/dev/null || true
  fi
}

fixture_tasks() {  # fixture_tasks <repo>: one line per task folder, with its files
  ( shopt -s nullglob; found=0
    for t in "$1"/projects/*/active/*/; do
      found=1; t="${t%/}"
      echo "      ${t#"$1"/}"
      echo "        files: $(cd "$t" && find . -type f -not -path './.wos/*' | LC_ALL=C sort | tr '\n' ' ')"
      grep -h -m1 'Escalations:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/        /' || true
    done
    [ "$found" = 1 ] || echo "      none" )
}

case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$dir/product/src" "$dir/product/docs/adr" && cd "$dir/product" && git init -q -b main .
    printf 'node_modules/\n' > .gitignore
    cat > README.md <<'EOF'
# notifier

A small service that lets subscribers recieve one digest email a day instead of a mail per event.

Run it with `node src/digest.js`. Configuration lives in environment variables:
`DIGEST_HOUR` (default 7) and `SMTP_URL`.
EOF
    cat > src/digest.js <<'EOF'
// Collects the day's events per subscriber and sends one digest at DIGEST_HOUR local time.
const hour = Number(process.env.DIGEST_HOUR || 7);
function due(now, tzOffsetMinutes) {
  const local = new Date(now.getTime() + tzOffsetMinutes * 60000);
  return local.getUTCHours() === hour && local.getUTCMinutes() === 0;
}
module.exports = { due };
EOF
    cat > docs/adr/0003-one-digest-a-day.md <<'EOF'
# ADR-0003: One digest a day, sent in the subscriber's time zone

Status: Accepted

## Context

Subscribers received one mail per event. On busy days that was forty mails, and the
unsubscribe rate doubled in the month the event volume did.

## Decision

Events are collected per subscriber and sent as one digest a day, at `DIGEST_HOUR` in the
subscriber's own time zone (default 07:00). A day with no events sends nothing. Per-event
mail is removed, including for subscribers who asked for it; there is no opt-out to the
old behaviour.

## Consequences

An urgent event waits up to a day. Urgent notices go through the status page, which is
outside this service.
EOF
    git add .gitignore README.md src/digest.js docs/adr/0003-one-digest-a-day.md && commit init

    task="$dir/billing/projects/acme__billing/active/$seeded"
    mkdir -p "$task" && cd "$dir/billing" && git init -q -b main .
    printf 'node_modules/\n' > .gitignore
    printf '*\n' > projects/.gitignore
    cat > invoice.py <<'EOF'
from decimal import Decimal, ROUND_HALF_EVEN


def line_total(quantity, unit_price):
    return (Decimal(quantity) * Decimal(unit_price)).quantize(Decimal("0.01"), ROUND_HALF_EVEN)


def invoice_total(lines):
    return sum((line_total(q, p) for q, p in lines), Decimal("0.00"))
EOF
    printf '# Task: invoice rounding\n\nRound invoice amounts to cents in one place.\n' > "$task/README.md"
    cat > "$task/TASK_STATE.md" <<'EOF'
# TASK_STATE

## Current phase
implementation

## Objective
Round every invoice amount to cents in invoice.py, in one place, so line totals and the
invoice total can never disagree by a cent.

## Recommended pipeline
- Escalations: none

## Recommended next step
- Run now: implement-approved-slice (Slice 02: invoice_total sums rounded line totals)

## Resume notes
- Slice 01 is closed: line_total rounds to cents.
EOF
    cat > "$task/IMPLEMENTATION_PLAN.md" <<'EOF'
# IMPLEMENTATION_PLAN

## Slices

### Slice 01: line_total rounds to cents
- Scope: invoice.py
- Status: done

### Slice 02: invoice_total sums rounded line totals
- Scope: invoice.py
- Status: not-started
- Exit criteria: WHEN an invoice has lines, invoice_total SHALL equal the sum of the rounded line totals.
EOF
    printf '# DECISIONS\n\n### D-1. Amounts round to cents in invoice.py only.\n' > "$task/DECISIONS.md"
    printf '# SOURCE_OF_TRUTH\n\n## Active codebase / repo\n- %s\n' "the billing repository, invoice.py" > "$task/SOURCE_OF_TRUTH.md"
    git add .gitignore invoice.py && commit init
    watch_record
    ;;
  probe)
    for r in product billing; do
      echo "  $r:"
      echo "    task folders under projects/*/active/:"
      fixture_tasks "$dir/$r"
      echo "    commits: $(git -C "$dir/$r" rev-list --count HEAD) (the fixture starts with 1)"
      st="$(git -C "$dir/$r" status --porcelain)"
      echo "    git status --porcelain:"; if [ -n "$st" ]; then printf '%s\n' "$st" | sed 's/^/      /'; else echo "      (clean)"; fi
    done
    echo "  billing's task folder open at the build: projects/acme__billing/active/$seeded"
    watch_report
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

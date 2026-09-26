#!/usr/bin/env bash
# test-substrate-retention.sh: the three states check-substrate-retention.sh can be in, plus the
# two things it is forbidden to do. Every fixture is built under a temp root, so this never reads
# the operator's real substrate.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="${SCRIPT_DIR}/../check-substrate-retention.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

make_root() {  # make_root <name>; echoes the root path, with one active and one archived task
  local r="$TMP/$1"
  mkdir -p "$r/projects/acme__thing/active/2026-01-01_task" "$r/projects/acme__thing/archive/2025-01-01_old"
  echo "note" > "$r/projects/acme__thing/active/2026-01-01_task/TASK_STATE.md"
  echo "$r"
}

# 1. no projects/ and no sidecar: not measured, exit 0. Never "clean": clean is a claim.
r="$TMP/empty"; mkdir -p "$r"
out="$(SUBSTRATE_RETENTION_FILE="$TMP/absent" "$GATE" --root "$r" 2>&1)"; rc=$?
[ "$rc" = "0" ] && printf '%s' "$out" | grep -q '^Substrate-retention: not measured' \
  && pass "no substrate and no sidecar reports not measured (exit 0)" \
  || fail "expected 'not measured' and exit 0, got rc=$rc: $out"

# 2. substrate present but no sidecar: still not measured, because nothing declared a limit.
r="$(make_root nosidecar)"
out="$(SUBSTRATE_RETENTION_FILE="$TMP/absent" "$GATE" --root "$r" 2>&1)"; rc=$?
[ "$rc" = "0" ] && printf '%s' "$out" | grep -q 'not measured' \
  && pass "substrate without a sidecar reports not measured (exit 0)" \
  || fail "expected 'not measured' with no sidecar, got rc=$rc: $out"

# 3. fresh backup inside the limit: clean, exit 0.
r="$(make_root fresh)"; b="$TMP/backup-fresh"; mkdir -p "$b"; echo x > "$b/dump.tar"
cat > "$TMP/sidecar-fresh" <<EOF
BACKUP_DEST=$b
MAX_BACKUP_AGE_DAYS=7
ARCHIVE_MAX_AGE_DAYS=365
EOF
out="$(SUBSTRATE_RETENTION_FILE="$TMP/sidecar-fresh" "$GATE" --root "$r" 2>&1)"; rc=$?
[ "$rc" = "0" ] && printf '%s' "$out" | grep -q 'clean' \
  && pass "backup newer than the limit is clean (exit 0)" \
  || fail "expected clean and exit 0, got rc=$rc: $out"

# 4. backup 400 days old: STALE, exit 1.
r="$(make_root stale)"; b="$TMP/backup-stale"; mkdir -p "$b"; echo x > "$b/dump.tar"
touch -t "$(date -v-400d +%Y%m%d0000 2>/dev/null || date -d '400 days ago' +%Y%m%d0000)" "$b/dump.tar"
cat > "$TMP/sidecar-stale" <<EOF
BACKUP_DEST=$b
MAX_BACKUP_AGE_DAYS=7
ARCHIVE_MAX_AGE_DAYS=365
EOF
out="$(SUBSTRATE_RETENTION_FILE="$TMP/sidecar-stale" "$GATE" --root "$r" 2>&1)"; rc=$?
[ "$rc" = "1" ] && pass "backup older than the limit exits 1" \
  || fail "expected exit 1 on a 400-day-old backup, got rc=$rc: $out"

# 5. a declared destination that does not exist is a missing backup, not a pass.
r="$(make_root nodest)"
cat > "$TMP/sidecar-nodest" <<EOF
BACKUP_DEST=$TMP/does-not-exist
MAX_BACKUP_AGE_DAYS=7
EOF
out="$(SUBSTRATE_RETENTION_FILE="$TMP/sidecar-nodest" "$GATE" --root "$r" 2>&1)"; rc=$?
[ "$rc" = "1" ] && pass "a missing backup destination exits 1" \
  || fail "expected exit 1 on a missing destination, got rc=$rc: $out"

# 6. FORBIDDEN: the output must never carry a project folder name. A client name in a lint log
#    or a paste is the leak class this whole wave exists to close.
r="$(make_root leaky)"; b="$TMP/backup-leaky"; mkdir -p "$b"; echo x > "$b/dump.tar"
cat > "$TMP/sidecar-leaky" <<EOF
BACKUP_DEST=$b
MAX_BACKUP_AGE_DAYS=7
EOF
out="$(SUBSTRATE_RETENTION_FILE="$TMP/sidecar-leaky" "$GATE" --root "$r" 2>&1)"
printf '%s' "$out" | grep -q 'acme__thing' \
  && fail "output leaked a project folder name" \
  || pass "output carries no project folder name"

# 7. usage error exits 2.
"$GATE" --root >/dev/null 2>&1; rc=$?
[ "$rc" = "2" ] && pass "--root without a value exits 2" \
  || fail "expected exit 2 on a missing --root value, got rc=$rc"

echo
if [ "$fails" -eq 0 ]; then echo "test-substrate-retention: all $checks checks passed"; exit 0
else echo "test-substrate-retention: $fails of $checks check(s) FAILED"; exit 1; fi

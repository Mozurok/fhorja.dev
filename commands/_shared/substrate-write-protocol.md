Canonical substrate write protocol -- emit transaction header above every substrate section write AND append one line per write to `.wos/VERIFICATION_LOG.jsonl`. Per ADR-0034 + `wos/substrate-peers.md` (K.1 retrofit, K.2 writer emission).

Applies to writes targeting the 11 substrate files (4 task-memory + 7 fleet-substrate + project-level REFERENCES.md). Shadow mode at launch: writers emit, no reader enforces. Validator (`scripts/verify-log-validator.py`) lands in K.5 / Epic J.5.

## Transaction header (above the section write)

Place this HTML comment line immediately above the section content being written:

```
<!-- wos:write owner=<command-or-persona-id> section='## X' run_id=<ulid-or-uuid> ts=<ISO-8601-with-ms> reason=<<=80chars> mode=<applied|proposed> -->
```

Field rules:
- `owner`: this command or persona's name (matches `metadata.name` in frontmatter).
- `section`: the H2 section header text including the `## ` prefix, in single quotes.
- `run_id`: one ULID or UUID per command invocation; reuse the same `run_id` across all section writes in this run.
- `ts`: ISO 8601 with millisecond precision and `Z` suffix (e.g. `2026-06-04T14:22:11.482Z`).
- `reason`: short human-readable rationale (<=80 chars) matching the JSONL `reason` field.
- `mode`: `applied` (Agent mode + actual write) or `proposed` (Ask/Plan or PROPOSED block).

Same-owner repeat write in one run: no-op-if-identical (SHA-256 of section bytes). Otherwise new header replaces prior; prior is logged with `event=overwrite`.

## Audit log line (one JSON object per write, appended to .wos/VERIFICATION_LOG.jsonl)

Append exactly one JSON line per section write to `active/<task>/.wos/VERIFICATION_LOG.jsonl` (gitignored). Use the schema documented in `wos/substrate-peers.md ## Audit trail`:

```json
{"ts":"2026-06-04T14:22:11.482Z","run_id":"01HX5KPQ8R-...","owner":"<command-name>","owner_type":"command","invoked_by":null,"file":"TASK_STATE.md","section":"## Current phase","event":"write","mode":"applied","sha_before":"<sha256-or-null>","sha_after":"<sha256>","reason":"<same-as-header>","partials":null,"strategy":null}
```

Event taxonomy (canonical, 19 enum values): `write` | `overwrite` | `propose` | `approve` | `refuse` | `delete` | `fleet-merge` | `legacy-promote` | `partial_merge` | `merge_include` | `merge_with_gap` | `worker_failed` | `worker_interrupted` | `worker_missing` | `worker_timeout` | `retry_needs_revision` | `max_iterations_promoted` | `retry_failed_recoverable` | `quorum_discard`.

Owner-type taxonomy: `command` | `persona` | `fleet-merger`.

`invoked_by`: when this command was invoked as a worker or via Handoff routing, name the parent invoker; null when user-initiated.

`partials` / `strategy`: populated only for fleet-merge / convergence events; null for direct writes by this command.

`summary` (optional, additive): a command MAY add a `summary` string (at most 3 lines) carrying a human-facing narrative of what the whole run did and why, for the activity-timeline view (`scripts/build-activity-timeline.py`, ADR-0049). It is distinct from the per-section `reason` (<=80 chars) and is purely additive: the 14-field required set is unchanged and `scripts/verify-log-validator.py` tolerates it. The timeline prefers `summary` over the aggregated per-section `reason` when present. See `wos/substrate-peers.md ## Audit trail` for the field definition.

## When to emit

- ALWAYS when writing a `## section` (H2) in any substrate file, because the audit log is the only durable record of who changed what and the K.4 drift-guard reconstructs section ownership from these headers; a write with no header is invisible to reconciliation. Both single-section writes and multi-section writes emit one header + one log line per section.
- NEVER when reading, or when the write is a no-op-if-identical match, because logging a read or an unchanged write inflates the trail with events that moved nothing and dilutes the signal the validator and the activity timeline depend on.
- For PROPOSED blocks (mode=proposed), emit `event=propose`; the subsequent `approve-proposed` run emits `event=approve` per applied file.
- For REFUSE conflicts (writer is not the owner per `wos/substrate-peers.md`), emit `event=refuse` with the conflicting owner and reason; do NOT write the section.
- For section removals: emit `event=delete` for each H2 section that existed before a write and no longer exists after it, including replace-in-full rewrites. Convention: `sha_before` = the removed section's last hash, `sha_after` = null (the delete event is the ONLY event where `sha_after` may be null). A rename is a `delete` of the old section name plus a `write` of the new one. Without this, a superseded section's last write event sits orphaned in the log and the log-derived section set overstates the file.
- H3-scoped co-writes (per `wos/substrate-peers.md`, e.g. implement-approved-slice's status-only update inside `### Slice N`): log at the owning H2 (`section='## Slices'`) with `reason` naming the slice and the transition (e.g. `reason=slice-3-status-implemented`); the sha fields hash the H2 block. The H2-only section grammar is intact; do not put `### ` text in the `section` field (the validator rejects it).

## Legacy files without headers

VALID per `wos/substrate-peers.md ## Legacy file without headers`. The first mutating write under K.2 emits a header only for THAT section. Other sections stay header-less until they are next mutated. Drift-guard does NOT flag header-less as error; only ownership-rule violations.

## Concrete computation (bash helpers)

The K.2 protocol is half-compliant if you emit the JSONL line but skip the inline header, or if you set `sha_*` fields to `null` when the section already existed. The K.8 first-lived-test (2026-06-04) found 125 of 126 substrate writes shipped the JSONL line without the inline header. Preferred path: run `bash scripts/emit-substrate-write.sh` (wraps RUN_ID/TS generation, sha_of_section, and emit_audit; its `--batch <file>` mode emits one JSONL line per owner-headed section of a file, so a task-init-scale ~25-30-section run is one invocation per file). The helpers below are the same logic inline, for hosts without script access; use them verbatim to avoid the half-compliance failure mode.

A section's bytes end at the next transaction header or the next H2 heading, whichever comes first (matching the sha definition in `wos/substrate-peers.md`); the next section's `<!-- wos:write -->` header line is never part of the previous section's hash.

Run from the task folder root (`active/<task>/`):

```bash
# 1. ULID-shaped run_id (shadow mode accepts any unique string)
RUN_ID="01J$(date -u +%y%m%d%H%M%S)$(openssl rand -hex 4 2>/dev/null || head -c 4 /dev/urandom | xxd -p)"

# 2. ISO 8601 with millisecond precision and Z suffix
TS=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
# (macOS `date` does not support %N; the .000Z suffix is a sentinel acceptable
#  to verify-log-validator.py because the regex is ^...\.\d{3}Z$.)

# 3. Compute SHA-256 of a section's bytes (between '## header' and next '## ' or EOF)
sha_of_section() {
  local file="$1" header="$2"
  if [[ ! -f "$file" ]]; then printf 'null'; return; fi
  local body
  body=$(awk -v h="$header" '
    $0 == h            { f=1; next }
    f && (/^## / || /^<!-- wos:write /) { exit }
    f                  { print }
  ' "$file")
  if [[ -z "$body" ]]; then printf 'null'; return; fi
  printf '%s' "$body" | shasum -a 256 | awk '{print $1}'
}

# 4. Append one JSONL line per section write
emit_audit() {
  local owner="$1" file="$2" section="$3" event="$4" mode="$5" reason="$6" sha_before="$7" sha_after="$8"
  jq -nc \
    --arg ts "$TS" --arg rid "$RUN_ID" --arg owner "$owner" \
    --arg file "$file" --arg section "$section" \
    --arg event "$event" --arg mode "$mode" --arg reason "$reason" \
    --arg sb "$sha_before" --arg sa "$sha_after" \
    '{ts:$ts, run_id:$rid, owner:$owner, owner_type:"command",
      invoked_by:null, file:$file, section:$section,
      event:$event, mode:$mode,
      sha_before:(if $sb=="null" or $sb=="" then null else $sb end),
      sha_after:(if $sa=="null" or $sa=="" then null else $sa end),
      reason:$reason, partials:null, strategy:null}' \
    >> .wos/VERIFICATION_LOG.jsonl
}
```

End-to-end example for a single substrate section update (canonical pattern):

```bash
# Pre-compute
TASK_FILE="TASK_STATE.md"
SECTION="## Latest sweep"
SHA_BEFORE=$(sha_of_section "$TASK_FILE" "$SECTION")  # 'null' if section absent

# Insert transaction header IMMEDIATELY above the section, then write the section
# (use Edit tool or sed to insert these two lines: the wos:write header then
#  the section heading, then the content)
#
#   <!-- wos:write owner=<command-name> section='## Latest sweep' run_id=<RUN_ID> ts=<TS> reason=<<=80chars> mode=applied -->
#   ## Latest sweep
#   <new section body>

# Post-compute and append audit log line
SHA_AFTER=$(sha_of_section "$TASK_FILE" "$SECTION")
emit_audit \
  "<command-name>" \
  "$TASK_FILE" "$SECTION" \
  "write" "applied" "sweep-N-findings" \
  "$SHA_BEFORE" "$SHA_AFTER"
```

`sha_before` is `null` ONLY when the section did not exist prior to this write. `sha_after` MUST be a 64-char lowercase hex string (never null). Multi-section writes in one run reuse the same `RUN_ID` and `TS`; emit one header + one JSONL line per section.

**Edit-tool timing (P1-7, dogfood-wave-2 2026-07-12):** `SHA_BEFORE` MUST be computed in the same turn, immediately before the write, not from memory of an earlier turn's content: by the time a later turn runs the JSONL-append step, the pre-edit bytes are gone from disk and cannot be recovered without a forbidden `null` fallback or reading from version control. When authoring via the Edit tool rather than bash/sed, run the `sha_of_section` computation (via `scripts/emit-substrate-write.sh sha` or the inline helper) as the step immediately preceding the Edit call in the same turn, and hold the value in scope until the JSONL append. If the pre-edit content is genuinely unavailable (a compacted session, a cross-turn gap), re-read the current file state with the Read tool first rather than guessing or defaulting to `null`.

**Header placement relative to a mandatory H1 (P2-7, dogfood-wave-2 2026-07-12):** when the file has a mandatory H1 title (e.g. `# TASK_STATE` per `task-init.md`'s canonical template), the transaction header for the FIRST section goes after the H1 and its blank line, immediately above the first `## ` heading, never above the H1 itself:

```
# TASK_STATE

<!-- wos:write owner=task-init section='## Task summary' run_id=<RUN_ID> ts=<TS> reason=<<=80chars> mode=applied -->
## Task summary
<content>
```

A header placed above the H1 line, or an H1 dropped entirely to sidestep the question, are both non-compliant; two independent dogfood waves each produced one session doing one of these two wrong things.

## Skill-cache invalidation gap (Claude Code property)

When `scripts/sync-workflow-slash-commands.sh --with-skills` propagates an updated skill file to `~/.claude/skills/<name>/SKILL.md`, the current Claude Code (or Cursor, Codex, etc.) session does NOT automatically reload the skill body. The session reuses the cached body that was loaded at session start (or at the skill's first invocation in that session). Workflow:

- Edit `commands/<name>.md` in the Fhorja repo (or `commands/<name>/SKILL.md` for folder-shaped)
- Run `bash scripts/build-agent-skills.sh` to regenerate `.claude/skills/<name>/SKILL.md`
- Run `bash scripts/sync-workflow-slash-commands.sh --with-skills` to propagate to user-level skill registries
- **KILL the current chat session and start a new one** to force the host to reload the skill body. Same-session re-invocation of `/<name>` keeps using the cached version.

Verified empirically during the K.2 enforcement loop (4 sweep iterations on 2026-06-04 / 2026-06-05): the 3rd sweep, run 10 seconds after sync completed, received a bit-identical cached prompt and never invoked the updated K.4 + K.5 scripts. Out-of-band invocation of the underlying scripts always works regardless of session state:

```bash
# Bypass the skill cache by running the scripts directly
bash scripts/scan-substrate-headers.sh <task-folder>
python3 scripts/verify-log-validator.py <task-folder>/.wos/VERIFICATION_LOG.jsonl
```

Use the out-of-band path to verify a fix immediately; use the session-restart path to validate that the slash-skill consumes the new spec.

This is a Claude Code / host-side caching property, not a Fhorja protocol bug. The K.2 protocol itself is unaffected: writes always honor the protocol whether dispatched via a cached skill body or a fresh one. The cache gap matters only when you ship a WRITER-FIX and need to verify the new spec actually loaded.

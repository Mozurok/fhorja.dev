# ADR-0110: One-call substrate writes (apply subcommand) and batched verification

- **Status**: Accepted
- **Date**: 2026-07-21
- **Tags**: substrate-protocol, emit-substrate-write, verification-log, ceremony-cost, extends-adr-0034, extends-adr-0101, v3-wave2

## Context

The K.2 substrate write protocol (ADR-0034) made every section write auditable, but the mechanics cost 3 to 6 tool calls per markdown edit: generate run identifiers, capture `sha_before`, perform the edit, compute `sha_after`, append the JSONL line, and in practice run one or more validators after almost every individual write. The bv3 cross-model dogfood (2026-07-20/21) measured 244 `emit-substrate-write` calls in one session, and the earlier Beaufort analysis identified substrate bookkeeping as the single largest tool-time sink (P5 in the v2 backlog). The adversarially reviewed v3 wave-2 spec (item E) bound this ADR to specific corrections: an honest cost baseline, hard die rules for the splice, and validator composition that survives a non-zero exit.

Two subtleties shaped the design. First, `sha_of_section`'s boundary is not code-fence aware: a decoy `## X` line inside a fenced block in another section would make a naive splice overwrite the wrong bytes, and the self-check would not catch it because both sides share the same boundary. Second, `scan-substrate-orphans.py` exits 1 on findings, so a naive `set -e` chain of the three validators aborts before the remaining validators run, eating their output.

## Decision

1. `scripts/emit-substrate-write.sh` gains an `apply` subcommand performing the whole write cycle in one call: capture `sha_before`, insert-or-replace the transaction header, splice the section body from `--body-file`, self-check the post-splice section hash against the intended-body hash BEFORE the original file is touched (the splice lands on a temp file first), and append one JSONL line. Event auto-selects `write` (empty prior body) or `overwrite`.
2. Hard die rules, all refusals with the original file untouched:
   - the exact section line must match exactly one line in the file (`grep -cxF`); a duplicate, including a code-fence decoy, refuses;
   - the body must not contain H2 headings or `wos:write` lines (apply never creates sections; header lines are excluded from the section hash and would break the self-check);
   - a caller-passed `--sha-before` that mismatches the measured value refuses (the measured value is authoritative, closing the S2 trust gap for this path by construction).
3. The legacy subcommands `sha`, `emit`, and `batch` keep their behavior unchanged; `apply` is additive. The honest accounting is documented in `commands/_shared/substrate-write-protocol.md`: the legacy floor is 3 calls when batched right, so `apply` removes 2 to 4 calls per write, not 5.
4. `scripts/verify-substrate-batch.sh` runs the three validators (headers first, then the log validator with `--check-deletes`, then the orphan scan) with independent exit-code capture and exits with the OR. Nothing becomes blocking in this wave: the combined code is exposed for the future S1 gate to consume (wave-2 D-3). Call sites refactored: the repo-consistency-sweep Pre-flight, and the self-check nudges in task-init and slice-closure.
5. Harness boundary (composes with the wave-1 Codex guidance): on Codex CLI the native apply-patch tool governs (a bash call re-escalates there); `apply` is the preferred path on harnesses where a bash call does not re-escalate (Claude Code today).

## Consequences

- A substrate write costs one call on the preferred path; batch verification runs once per batch instead of after every edit.
- Trade-off, accepted: `apply` bypasses the host's Edit tool, so the host-side diff preview UX is lost for these writes; the JSONL line plus the self-check are the audit surface instead. Surgical line edits (a status flip inside a section) may still prefer the Edit tool plus the 3-call flow.
- Observed while validating: `scan-substrate-headers.sh` exits 2 when the target folder is outside a git worktree (a temp fixture); harmless for real task folders and surfaced honestly by the wrapper's per-validator codes.
- Evidence: 27-check round-trip test (`scripts/tests/test-emit-substrate-apply.sh`), red 15/12 then green 27/0, including the code-fence decoy refusal and legacy-behavior smoke checks; wrapper validated on a healthy folder (combined=0) and a real bullet-orphan fixture (orphans=1, all validators still ran, exit 3).

# ADR-0035: Imperative language in shadow-mode protocols

- **Status**: Accepted
- **Date**: 2026-06-05
- **Tags**: shadow-mode, protocol-design, enforcement, audit, dogfood, substrate, k2-retrofit

## Context

ADR-0034 shipped substrate ownership + worker contract in shadow mode: writers emit transaction headers and audit-log lines, no reader enforces yet. The K.2 retrofit (commit 9713820) added the obligation to the eight most-frequent writers as a soft prose bullet inside each command's Operating rules: roughly "MUST emit a transaction header immediately before any substrate Edit/Write AND append one JSONL line to VERIFICATION_LOG.jsonl after the write."

The K.8 first-lived-test (pilot-repo session, 2026-06-04 evening, first end-to-end run of personas + commands writing the same substrate) measured the gap. Out of 126 substrate writes in that session, 125 shipped the JSONL audit line WITHOUT the inline transaction header. The protocol was satisfied syntactically (a JSON line existed) and violated semantically (no in-substrate provenance, header-less sections, ownership unverifiable from the substrate file alone). A 99% failure rate is a protocol design failure, not a discipline failure: the writers were patched, the prose was clear, the writers obeyed half of it.

Six follow-on commits across the next 30 hours each surfaced a deeper failure mode that the soft-bullet retrofit had masked:

1. **Skill-cache invalidation gap.** The eight patched command bodies updated; the generated `.claude/skills/<name>/SKILL.md` cache did not auto-rebuild on first invocation. Workers were running the pre-K.2 prose with no warning.
2. **K.4 audit scope tied to code-repo diff.** The `repo-consistency-sweep` substrate-ownership check (K.4, commit d2778fa) only enumerated substrate files under the code repo's tracked tree. Substrate lives under `active/<task>/` which is gitignored in the WOS repo and not present at all in product repos. The audit returned zero rows on a session with 125 violations.
3. **Step 2 hash no-op short-circuiting Step 7 audit.** `repo-consistency-sweep` Step 2 computed a hash of the staged code diff; on no-op (no code changes since last sweep) it skipped all remaining steps including Step 7 substrate audit. But substrate state is independent of code-diff state; substrate writes happen on every command invocation regardless of git changes. The audit was bypassed exactly when it was most needed (between commits).
4. **Validator strictness weaker than protocol claim.** `verify-log-validator.py` accepted JSONL lines with `sha_after: null` on `event: applied` rows: a syntactically valid, semantically impossible state (an applied write cannot produce no resulting hash). Writers shipping `sha_after: null` passed validation and the audit count came back clean while substrate was un-provenanced.
5. **Model rationalizing carry-forward.** When the sweep finally surfaced the drift count, downstream consumers (other commands, downstream `verify-against-rubric` runs) carried prior-snapshot counts forward instead of re-invoking the substrate-audit script. The model treated the count as a fact instead of a measurement.
6. **Auditor not dogfooding.** The sweep itself wrote to substrate during its own run; without explicit Step 10 dogfood instructions, the sweep's own writes were excluded from the drift count it reported, producing a permanent under-report by exactly its own write count per iteration.

The pattern generalizes beyond K.2: any shadow-mode protocol built on soft imperatives plus hard-to-verify obligations produces systemic non-compliance.

## Decision

Four principles govern shadow-mode protocols in this WOS going forward. All four must be satisfied before a shadow-mode protocol ships.

**1. Imperative + concrete > imperative alone.** Replace "MUST emit X" prose with N-sub-step explicit instructions that include concrete bash helpers, exact byte templates, and the precise insertion point. The Phase 2 8-writer rewrite (separate commit) ships `commands/_shared/substrate-write-protocol.md ## Concrete computation` with copy-paste bash that computes the SHA-256, formats the header, appends the JSONL row, and validates `sha_after != null`. The K.8 failure rate dropped from 99% (125/126) only after writers shipped the explicit protocol; the soft bullet alone never closed the gap.

**2. Audit-of-the-auditor.** When a command enforces a protocol, that command MUST dogfood the same protocol. `repo-consistency-sweep` Step 10 (commit 7db3422) now explicitly tags the sweep's own substrate writes with `actor: repo-consistency-sweep` and excludes them from the drift count it reports against other actors. Without this rule the sweep under-reports drift by exactly its own writes per iteration, indefinitely.

**3. Pre-flight before any short-circuit.** Audit steps independent of a gating condition (code-repo diff hash, no-op detection, idempotency check) MUST execute BEFORE the gate, not after. Commit 65f8811 moved the substrate-ownership audit from Step 7 (post-gate) to Pre-flight (pre-gate) in `repo-consistency-sweep` because substrate state has no causal relation to code-diff state and the gate was suppressing the only check that catches between-commit drift. The general rule: any check whose validity does not depend on the gated input lives above the gate.

**4. Validator strictness >= protocol claim.** When a validator accepts a syntactically-valid-but-semantically-impossible value (null `sha_after` on an applied write, missing actor on a non-system event, future timestamps), the protocol claim is weaker than its enforcement. Tighten the validator first (commit 7879f3b rejects null `sha_after` on applied events), then trust the count. The order matters: a clean count from a permissive validator is a false signal; the same count from a strict validator is real evidence.

## Consequences

### Positive

- Future shadow-mode protocols pass through a four-check gate before shipping: explicit helpers in a shared block, dogfood instruction in any enforcer, pre-flight ordering for independent audits, strict validator before count trust. The K.2 30-hour retrofit cycle does not repeat per protocol.
- The Phase 2 8-writer rewrite (deferred to its own commit) ships the explicit protocol with copy-paste bash; the failure mode that produced 125/126 is structurally prevented at the writer site, not patched downstream.
- `repo-consistency-sweep` becomes a credible enforcer of its own claims. Sweep iterations from 2026-06-05 forward report drift against the strict validator; counts are comparable across runs.
- The shadow-mode pattern itself is preserved (no v2.1 strict block of substrate writes), because the failure mode was protocol design, not the choice of shadow mode. Strict mode still lands when eval evidence (K.7) shows discipline holds across enough sessions.

### Negative

- Six follow-on commits across 30 hours to retrofit a protocol that should have been correct from K.2. Direct cost: ~6 commits + Phase 2 rewrite. Indirect cost: every prior session between K.2 ship and Phase 2 ship produced un-provenanced substrate that cannot be retroactively audited; only the JSONL line exists, the in-substrate header does not.
- Shared block `commands/_shared/substrate-write-protocol.md ## Concrete computation` is now load-bearing; any drift between the shared block and the eight inline copies surfaces in `sync-shared-blocks.sh --check`. The lint surface expands by one block.
- Validator strictness rejects historical JSONL rows. `verify-log-validator.py` run against pre-2026-06-05 sessions surfaces ~125 invalid rows from the K.8 first-lived-test alone. Treated as known prior drift; not retroactively fixed.

### Neutral

- The four principles are framed as a checklist for new shadow-mode protocols, not as enforceable lint rules. ADR-0029 drift guards do not yet have a hook for protocol-design checks; the four principles live in this ADR and in the relevant command files (sweep + substrate-write-protocol) and travel by reference.
- ADR-0034 itself is unchanged. The shadow-mode choice (writers emit, no reader enforce until K.5/J.5) remains correct. What this ADR adds is how to ship shadow-mode protocols so that the emit side is reliable enough that the eventual strict reader has signal to work with.

## Alternatives considered

### Alternative 1: Ship K.2 as strict from day one

- Block any substrate write that lacks a transaction header; refuse the operation; surface a hard error.
- Rejected: strict blocking before evidence creates the opposite failure mode. Pre-evidence, an unknown fraction of real-world flows produce header-less writes for legitimate reasons (partial states during multi-step commands, pre-existing sections written before K.2). Strict-from-day-one would have blocked the K.8 first-lived-test entirely and produced no evidence about which writers were the actual offenders. Shadow mode is the right vehicle; the failure was the soft imperatives inside it.

### Alternative 2: Defer K.2 indefinitely; ship Epic K without substrate audit

- Accept un-provenanced substrate; rely on `git blame` after the fact for ownership questions.
- Rejected: ADR-0034 documented exactly why this fails once a persona/agent layer joins. Substrate ownership without an audit trail is non-reproducible across sessions and across actors (persona vs command vs orchestrator merger). The K.8 first-lived-test would still have produced 126 silent overwrites; the question is whether they were detectable. Without K.2 there is no detection.

### Alternative 3: Inline the bash helpers into every writer's Operating rules

- Skip the shared block; copy the 6-sub-step protocol and the bash helpers byte-for-byte into all eight writer files.
- Rejected: inlining produces 8+ copies of the same protocol, each drifting independently as writers evolve. The shared-block + concrete-computation pattern (ADR-0011) is the single-source-of-truth discipline this WOS already enforces; abandoning it for K.2 would create exactly the drift class ADR-0011 was written to prevent. The right shape is one shared block, eight inline references, lint enforcing the marker.

## References

- ADR-0034 (Substrate peers + worker contract) -- parent ADR; defines shadow-mode obligation this ADR refines.
- ADR-0011 (Shared canonical blocks) -- single-source-of-truth pattern for `substrate-write-protocol.md`.
- ADR-0029 (Drift guards) -- count-marker + registry-membership pattern; protocol-design checks not yet auto-enforced.
- `commands/_shared/substrate-write-protocol.md` -- shared block with `## Concrete computation` bash helpers.
- `commands/repo-consistency-sweep.md` -- dogfood Step 10 + Pre-flight audit ordering.
- `wos/substrate-peers.md ## Drift-guard hook` -- K.4/K.5 enforcement counterpart.
- Commit 9713820 -- original K.2 retrofit (soft bullet, the failure mode this ADR documents).
- Commit 7db3422 -- sweep Step 10 dogfood instruction.
- Commit d2778fa -- K.4 canonical-locations enumeration (decouples audit scope from code-repo diff).
- Commit 7879f3b -- K.5 validator strictness (rejects null `sha_after` on applied events).
- Commit daba6f8 -- Step 2/9 decoupling (substrate audit no longer gated by code-diff hash).
- Commit 65f8811 -- Step 7 substrate audit moved to Pre-flight ordering.

## Notes

The 99% failure rate from K.8 first-lived-test (125/126 substrate writes without inline header) is the empirical anchor for this ADR. Future shadow-mode protocols that propose soft prose imperatives without concrete helpers should be challenged with this number. The K.2 retrofit was written by a careful operator and obeyed by careful writers; the protocol still failed at 99%. Imperatives alone do not scale.

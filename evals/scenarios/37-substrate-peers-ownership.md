# Scenario 37: substrate peers ownership boundaries

## Purpose

Validates the ownership contract of ADR-0034 as ADR-0232 left it. K.8 personas operating as substrate peers write the sections they declare as `owned_sections`, and a write outside that boundary is not refused: it lands, and it is recorded and recoverable. Recorded means a transaction header and a `VERIFICATION_LOG.jsonl` line that name the writer and the section's conventional owner. Recoverable means the line's `sha_before` pins the exact bytes the write replaced, so a restore can be verified against it.

This scenario exercises the multi-persona apply step, the audit trail that replaces the old owner-exclusivity refusal, and the contract that no persona overwrites another persona's canonical content silently.

## Setup

- Active task folder exists with a valid `TASK_STATE.md` and `POST_DEPLOY_PLAN.md` (both initialized via the canonical task lifecycle).
- Two K.8 personas are registered as substrate peers:
  - `rls-auth-boundary-auditor`: declares `owned_sections: ["TASK_STATE.md ## Risks to watch"]`.
  - `post-deploy-verifier`: declares `owned_sections: ["POST_DEPLOY_PLAN.md (full document)"]`.
- Batch dispatcher is configured to fan out both personas in parallel under the substrate-write-protocol defined in K.2.

## Given / When / Then

### Case A: Honest peers write only to owned sections

- Given two K.8 personas (`rls-auth-boundary-auditor` owns `TASK_STATE.md ## Risks to watch`; `post-deploy-verifier` owns `POST_DEPLOY_PLAN.md`).
- When a batch dispatch yields outputs from both personas.
- Then each persona writes only to its declared `owned_sections`; the apply step succeeds for both writes and each write carries its header and log line.

### Case B: A write outside the owned section is recorded and recoverable

- Given a persona writes to a section it does not own (e.g. `post-deploy-verifier` emits a patch that targets `TASK_STATE.md ## Risks to watch`).
- Then the apply step lets the write land (ADR-0232: ownership is descriptive, nothing refuses it). The write carries a transaction header naming `post-deploy-verifier`, and its `VERIFICATION_LOG.jsonl` line names the writer, the target file and section, and the conventional owner `rls-auth-boundary-auditor` in `reason`. Its `sha_before` equals the SHA-256 of the section bytes before the write.

## Pass Criteria

1. Both personas dispatch in parallel and return structured outputs with `owned_sections` declared in the manifest.
2. `rls-auth-boundary-auditor` successfully mutates `TASK_STATE.md ## Risks to watch` and no other section.
3. `post-deploy-verifier` successfully mutates `POST_DEPLOY_PLAN.md` and no other file.
4. The apply step emits one record (header plus log line) per persona write, each scoped to the section it wrote.
5. When Case B is injected, the write lands and is recorded: one transaction header above the section and one `VERIFICATION_LOG.jsonl` line with `event=write`, `mode=applied`, `owner=post-deploy-verifier`, the target `file` and `section`, and a `reason` naming the conventional owner `rls-auth-boundary-auditor`. No `event=refuse` line is emitted for it.
6. The Case B write is recoverable: the line's `sha_before` equals the SHA-256 of the section's pre-write bytes (excluding header lines, per `wos/substrate-peers.md`), and its `sha_after` equals the SHA-256 of the bytes that landed, so the prior version can be identified and a restore verified against the hash.
7. No persona overwrites another persona's owned content silently: every such write has a header and a log line, and `scripts/check-substrate-ownership.py` counts it among the writes outside the conventional owner.
8. The scenario log surfaces all writes in a form a reviewer can replay against ADR-0034, ADR-0232 and `wos/substrate-peers.md`.

## Failure Modes

- A persona writes to a section outside its `owned_sections` and the write carries no header or no log line (the write is silent, so it cannot be audited or recovered).
- The apply step refuses or quarantines a write outside the owned section, the behavior ADR-0232 retired.
- The Case B log line omits the conventional owner, or its `sha_before` does not match the pre-write bytes, so the replaced version cannot be identified.
- Both personas race on the same file and the last writer wins with no log line for the earlier write (substrate-write-protocol violation).
- Log lines omit the persona id or the targeted section anchor, making the write unauditable.

## Notes

- References:
  - ADR-0034: Substrate peers + worker contract (the header, the JSONL line, the SHA chain and the worker contract stay normative).
  - ADR-0232: Substrate ownership is descriptive (retires the refusal this scenario used to assert).
  - ADR-0036: Apply-step semantics for multi-persona dispatch.
  - `wos/substrate-peers.md`: canonical peer contract and `owned_sections` schema.
  - K.2 substrate-write-protocol: ordering, the header and the log line.
- Until 2026-09-23 this scenario asserted rejection (strict) or quarantine (lenient) in Case B. The one ownership refusal ever logged sat in about 44,600 log lines, so the rule was replaced by the record described above.
- Pair with scenario 36 (multi-persona dispatch happy path) to distinguish ownership records from dispatch-level failures.

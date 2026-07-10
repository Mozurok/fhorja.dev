# Scenario 37 -- Substrate Peers Ownership Boundaries

## Purpose

Validates ADR-0034 (Substrate peers + worker contract) ownership boundaries. Confirms that K.8 personas operating as substrate peers write only to the sections they declare as `owned_sections`, and that any attempt to write outside that boundary is detected and rejected (or warned) before the substrate is mutated.

This scenario exercises the multi-persona apply step, the owner-exclusivity guarantee, and the contract that prevents one persona from silently overwriting another persona's canonical content.

## Setup

- Active task folder exists with a valid `TASK_STATE.md` and `POST_DEPLOY_PLAN.md` (both initialized via the canonical task lifecycle).
- Two K.8 personas are registered as substrate peers:
  - `rls-auth-boundary-auditor` -- declares `owned_sections: ["TASK_STATE.md ## Risks to watch"]`.
  - `post-deploy-verifier` -- declares `owned_sections: ["POST_DEPLOY_PLAN.md (full document)"]`.
- Batch dispatcher is configured to fan out both personas in parallel under the substrate-write-protocol defined in K.2.

## Given / When / Then

### Case A: Honest peers write only to owned sections

- Given two K.8 personas (`rls-auth-boundary-auditor` owns `TASK_STATE.md ## Risks to watch`; `post-deploy-verifier` owns `POST_DEPLOY_PLAN.md`).
- When a batch dispatch yields outputs from both personas.
- Then each persona writes only to its declared `owned_sections`; the apply step succeeds for both writes and records no cross-ownership violation.

### Case B: Cross-ownership write is rejected

- Given a persona attempts to write to a section it does not own (e.g. `post-deploy-verifier` emits a patch that targets `TASK_STATE.md ## Risks to watch`).
- Then the apply step rejects the write (strict mode) or warns and quarantines the patch (lenient mode) per ADR-0034 owner exclusivity. The owning persona's section remains untouched and the violation is logged with the offending persona id, target path, and section anchor.

## Pass Criteria

1. Both personas dispatch in parallel and return structured outputs with `owned_sections` declared in the manifest.
2. `rls-auth-boundary-auditor` successfully mutates `TASK_STATE.md ## Risks to watch` and no other section.
3. `post-deploy-verifier` successfully mutates `POST_DEPLOY_PLAN.md` and no other file.
4. The apply step emits one ownership-validated commit (or equivalent record) per persona, each scoped to its owned section.
5. When Case B is injected, the apply step rejects (strict) or warns (lenient) and the target section's pre-write content is preserved byte-for-byte.
6. The violation record names the offending persona, the targeted owned section, the section's rightful owner, and the resolution taken (rejected vs warned).
7. No persona is able to silently overwrite another persona's owned content; any successful overwrite path requires an explicit ADR-0034 escalation marker.
8. The scenario log surfaces all writes and rejections in a form a reviewer can replay against ADR-0034 and `wos/substrate-peers.md`.

## Failure Modes

- A persona writes to a section outside its `owned_sections` and the apply step accepts the write silently (ownership boundary broken).
- The apply step rejects a legitimate in-bounds write because the ownership manifest was misparsed (false positive on owner exclusivity).
- Both personas race on the same file and the last writer wins without a conflict signal (substrate-write-protocol violation).
- Violation logs omit the offending persona id or the targeted section anchor, making the breach unauditable.

## Notes

- References:
  - ADR-0034 -- Substrate peers + worker contract (owner exclusivity).
  - ADR-0036 -- Apply-step semantics for multi-persona dispatch.
  - `wos/substrate-peers.md` -- canonical peer contract and `owned_sections` schema.
  - K.2 substrate-write-protocol -- ordering, conflict handling, and rejection vs warning modes.
- This scenario should be run in both strict and lenient apply modes; the rejection vs warning behavior in Case B differs by mode but the ownership invariant must hold in both.
- Pair with scenario 36 (multi-persona dispatch happy path) to distinguish ownership violations from dispatch-level failures.

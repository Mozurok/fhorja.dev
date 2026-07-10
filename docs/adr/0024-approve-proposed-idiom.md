# ADR-0024: /approve-proposed batch-persist idiom

- **Status**: Accepted
- **Date**: 2026-05-19
- **Tags**: proposed-by-default, ergonomics, batch-persist, addendum-adr-0001, single-turn-write

## Context

ADR-0001 established PROPOSED-by-default writes for task-memory artifacts in Ask and Plan modes: every artifact change is marked `PROPOSED` in the response's `### Artifact changes` block, with full intended content inline; nothing is written to disk until the user re-runs the same command in Agent mode (or copy-pastes manually). The contract is correct (it prevents surprise writes) but ADR-0001 itself notes the cost: "**Two-step latency for first-time writers**. A user who fully trusts the model has to run the same command twice (Ask, then Agent) to apply changes. The friction is real but small."

The first real-world WOS session (transcript dated 2026-05-18) showed the friction is not as small as ADR-0001 assumed:

1. **`/decision-interview` re-propose loop**: when the user supplied LOCK picks, the next invocation re-emitted the entire PROPOSED block instead of persisting. The user typed identical lock payloads twice with 7 minutes apart. Fixed in slice 1 of the 2026-05-19 proposed-mode-fixup task (this is ADR-0024's sibling slice; see commands/decision-interview.md `Operating rules` -> `LOCK-pick recognition`).
2. **No "approve all" idiom**: after the user approved, the model fired 10+ sequential per-section `Edit` calls on TASK_STATE.md, flooding the terminal without a final consolidated recap. The user ended the session by asking for the raw JSONL transcript because they could not derive on-disk state from chat.
3. **Volume + lack of fechamento determinístico**: ~95 KB of in-terminal markdown across ~13 PROPOSED file references before the first disk write, with no single command to say "persist all of that, atomically, and tell me what landed."

The friction is structural: ADR-0001's two-step latency assumed step 2 was "re-run the command in Agent mode," which only persists ONE command's worth of proposals. When a single turn proposes 5 files (a normal `task-init` shape), the user has no idiomatic single-step path.

This ADR introduces the missing idiom WITHOUT replacing ADR-0001's safety property.

## Decision

The WOS adopts a new command `/approve-proposed` as the canonical batch-persist idiom for PROPOSED artifacts:

1. **Single-turn batch persist**. `/approve-proposed` reads the MOST RECENT prior assistant turn in the conversation history, identifies every file marked `PROPOSED` under that turn's `### Artifact changes` block, and writes all of them in this single turn (one Write per file, no per-section Edits, no interleaved prose).
2. **Source-of-truth turn is unambiguous**. "Prior turn" means the latest assistant message containing an `### Artifact changes` block. Intervening user messages, tool results, and assistant messages without an Artifact-changes block are skipped. The command does NOT walk back across multiple Artifact-changes turns; only the latest counts.
3. **Inline content required**. Only files with FULL final content inline under their bullet are persisted. Files marked `PROPOSED` but referenced ("see above", "same as last turn", or diff fragments without context) are skipped with a recap-line reason. This forces commands to emit complete proposals, not partial ones.
4. **Atomic batch with locked five-line recap**. The `### Command transcript` section contains exactly one line per outcome class, in this order:
   - `Persisted: <list>`
   - `Skipped (already current): <list>`
   - `Skipped (incomplete inline): <list>`
   - `Skipped (path outside scope): <list>`
   - `Skipped (no PROPOSED marker): <list>`
   Lines with zero entries are omitted; lines with entries appear in the locked order. The user reads ONE block to know exactly what landed.
5. **Conflict-with-locked-decision rollback**. Before persisting, the command compares each proposal against `TASK_STATE.md ## Canonical decisions`. If any proposal contradicts a locked decision, NO writes happen and the command emits a FAIL naming the contradiction. The batch is atomic; partial persistence on conflict is forbidden.
6. **No-op cases are explicit**. Three no-op paths exist: (a) no prior `### Artifact changes` block, (b) prior block has no `PROPOSED` files, (c) all PROPOSED files match on-disk content. Each emits `NO_OP_TRACE` with the cause named.
7. **Does not replace ADR-0001**. The two-step latency stays valid; `/approve-proposed` is one valid form of step 2, alongside re-running the source command in Agent mode and manual copy-paste. The user chooses which path fits the turn.
8. **No new proposals**. Additional user input beyond "approve" is ignored. The command does not accept new content; it executes the prior batch.

## Consequences

### Positive

- **Closes the friction loop**. The user can now say "approve" in one command and get a consolidated recap, instead of either re-running every source command or scrolling through 10+ per-section Edit confirmations.
- **Audit trail is sharper**. The recap names every file that landed, every file that was skipped, and the reason for each skip. Future state reconstruction reads cleanly.
- **Atomic semantics make conflict detection safe**. The conflict-with-locked-decision rollback rule means a user cannot accidentally apply a proposal that contradicts an earlier lock; the FAIL fires before any write.
- **Forces complete inline content in proposals**. Commands that emit "see above" or partial fragments fail batch-persist; this nudges proposal authors to emit full content, which improves the audit trail even when `/approve-proposed` is not used.
- **No contract break**. ADR-0001's safety property (no surprise writes in Ask/Plan) is preserved; this is purely an addendum that adds an option.

### Negative

- **Adds a command to the catalog**. 37 -> 38 commands. The growth is small and the command is narrowly scoped; the cost is the user having to learn one more name. Mitigation: the command is mentioned in the standard handoff `Paste this next` after any turn that emits PROPOSED artifacts, so users encounter it organically.
- **Inline-content requirement is strict**. Commands that emit very large proposals (e.g., a 23KB IMPLEMENTATION_PLAN.md) must include the full content inline to be batch-persistable, which costs tokens. Mitigation: the per-command token-budget framework (ADR-0013) already caps this; commands that exceed their budget surface the warning, prompting authors to either split the proposal or accept the higher cost.
- **Source-of-truth turn rule is brittle on long sessions**. If the user runs `/approve-proposed` many turns after the proposal, intervening assistant turns without Artifact-changes blocks must be skipped correctly. The rule is unambiguous (latest Artifact-changes-bearing turn wins) but assumes the chat history is accessible; auto-compaction or session restart can drop the turn. Mitigation: emit a `NO_OP_TRACE` when no Artifact-changes turn is visible.

### Neutral

- `/approve-proposed` lives in `state-and-navigation` category (alongside `sync-task-state`, `where-we-at`, `resume-from-state`). It is a state interaction, not a discovery or planning command.
- The command's primary editor mode is `Agent` (it writes files by definition). Other commands keep their existing mode defaults.

## Alternatives considered

### Alternative 1: extend each command with a `--persist-now` flag

- Add a flag to every command that proposes artifacts (e.g., `/task-init --persist-now`). When set, the command writes immediately without proposing first.
- **Rejected**: defeats the purpose of ADR-0001. The PROPOSED step is the review opportunity; merging it with the persist step skips review. Also requires per-command implementation (37 surfaces) vs one new command (1 surface).

### Alternative 2: auto-persist after N seconds with no objection

- Commands propose, wait N seconds (or one user turn), then persist automatically if the user did not object.
- **Rejected**: violates user agency. A user reading a long proposal may need more than N seconds; falling back to a timer is the wrong primitive. Also requires runtime infrastructure outside the markdown contract.

### Alternative 3: introduce ACTIVE operating mode that skips PROPOSED entirely

- Add a mode where TASK_STATE.md and SLICES write directly (low-stakes, git-revertable). SOURCE_OF_TRUTH and DECISIONS stay PROPOSED (high-stakes).
- **Rejected for this slice (deferred, not denied)**: bigger change; creates two classes of artifact with more rules to learn. The user explicitly chose A+B (drift fix + `/approve-proposed`) over C (ACTIVE mode) in the slice planning. Re-evaluate after this task closes and `/approve-proposed` sees real-world use; if the friction persists, ACTIVE mode is the next escalation.

### Alternative 4: copy-paste the recap from chat as the persist signal

- The user copy-pastes the PROPOSED block back as their next input; the model treats that as the persist signal.
- **Rejected**: forces the user to do the workflow's bookkeeping. The model already has the prior turn in context; making the user re-emit it is busywork. Also brittle to whitespace/formatting drift.

### Alternative 5: keep the two-step latency; just fix the re-propose loop

- Only do slice 1 (decision-interview fix); skip the new command.
- **Rejected for the same friction reason**: slice 1 fixes one specific re-propose bug; it does not address the general "approve all the proposed files this turn emitted" need. The user's pain in the transcript was not specific to decision-interview; it was the GENERAL absence of a batch-persist idiom. Slice 1 alone is insufficient.

## References

- ADR-0001 (PROPOSED-by-default; the contract this ADR is an addendum to).
- ADR-0002 (Paste-this-next handoff contract; `/approve-proposed` integrates with this).
- ADR-0007 (project-level memory; `projects/` is gitignored, so persist semantics for task-memory files apply).
- ADR-0011 (shared canonical blocks; `commands/_shared/artifact-changes-default.md` provides the no-nest rule that this command relies on for reliable parsing).
- `commands/approve-proposed.md` (the command implementation).
- `commands/decision-interview.md` (`Operating rules` -> `LOCK-pick recognition`; sibling fix from slice 1).
- `evals/scenarios/23-approve-proposed-batch-persist.md` (regression scenario).
- 2026-05-18 real-world session transcript (motivating evidence; private client task, not committed to this repo).

## Notes

The five-line recap format is locked at this ADR. Future revisions go through an ADR addendum.

The conflict-with-locked-decision rule is conservative by design: it forbids ANY persist when ANY proposal contradicts a lock. A less strict alternative ("persist the non-contradicting proposals, fail only the contradicting ones") was considered but rejected on atomicity grounds: partial application of a batch creates an intermediate state that does not match either the prior turn's proposal or the user's mental model. All-or-nothing is the predictable contract.

The "no walk-back across multiple Artifact-changes turns" rule is deliberate. If the user proposed a batch, did some other work, then proposed another batch, only the latest is approved by this command. To approve an older batch, the user re-runs the source command. Walking back would create ambiguity ("which batch did `/approve-proposed` actually apply?") that the locked source-of-truth-turn rule eliminates.

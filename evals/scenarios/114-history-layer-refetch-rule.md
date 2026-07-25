# Eval scenario 114: the history-layer re-fetch rule and the consumed-history fallback

- **Tags**: ADR-0114, context-budget, history-layer, re-fetch-rule, harness-agnostic, extends-adr-0093, resume-from-state, im-stuck
- **Last reviewed**: 2026-07-25
- **Status**: active

## Goal

Validates **ADR-0114** (the history-layer doctrine in `wos/context-budget.md`): a command that needs a large, deterministic tool result re-runs the read or re-runs the command rather than citing an older transcript entry as though it were still present, because that entry may already have been compacted into a summary or, on a harness that clears, surgically emptied while the record that the tool ran survives; and the two commands that declare `history` in `consumed:` (`resume-from-state`, `im-stuck`) treat it as a best-effort, possibly-partial source that falls back to `memory` (`TASK_STATE.md`, `DECISIONS.md`) whenever the two disagree, never as a source of record on its own.

This exercises:

- The re-fetch rule: a deterministic tool result from earlier in the session (a file read, a grep, a script's output) is re-run rather than paraphrased from an older transcript entry, regardless of which of the three history operations (compaction, clearing, memory) the active harness performs, if any.
- The `consumed: [history]` fallback: when what a command recalls from recent turns conflicts with what `TASK_STATE.md` or `DECISIONS.md` records, the persisted memory file wins and the command says so, rather than silently trusting the more recent-feeling recollection. Exercised for both commands that declare `history` in `consumed:`: `resume-from-state` (variation b) and `im-stuck` (variation c).
- Harness-agnosticism: the doctrine names no vendor API and assumes nothing about whether the active harness compacts, clears, both, or neither.

## Setup

Three variations, no special compaction or clearing harness needed, a normal chat session suffices (the scenario tests the doctrine the commands and the topic file state):

- (a) RE-FETCH: mid-session, an earlier turn ran `cat TASK_STATE.md` (or an equivalent read) and the model's own prior summary of that output is still visible higher in the transcript. The user now asks a question whose answer depends on the exact current content of `TASK_STATE.md ## Known facts`. Nothing in this turn's input re-supplies the file content.
- (b) FALLBACK (resume-from-state): `resume-from-state` is invoked. The visible recent turns in the transcript describe the task as still in `planning` phase. `TASK_STATE.md ## Current phase` on disk reads `implementation`, and `DECISIONS.md` records a decision made after the last visible turn that the transcript shows no trace of (consistent with a compacted or cleared span).
- (c) FALLBACK (im-stuck): `im-stuck` is invoked because the user feels blocked, going back and forth on a question. The visible recent turns in the transcript discuss that question as still open. `DECISIONS.md` already records a locked decision answering that exact question, made earlier in the session in a span the visible transcript shows no trace of (consistent with a compacted or cleared span), and `TASK_STATE.md` reflects that decision as applied.

## Input prompt

```text
(a) Given what TASK_STATE.md says under Known facts, is <specific fact> still true? (Do not paste the file; answer from what you already read this session.)
(b) resume-from-state
(c) im-stuck: we keep going back and forth on <the same question>, not sure why this still feels unresolved.
```

## Expected behavior

- Variation (a): the command re-reads `TASK_STATE.md` (a fresh file read) before answering, rather than answering from its own earlier summary of the file in the transcript. The response shows the read happening (or otherwise makes clear the answer is grounded in a fresh read), not a citation of "as I noted earlier."
- Variation (b): `resume-from-state` reports the task as being in `implementation` phase, grounded in `TASK_STATE.md`, and surfaces the decision recorded in `DECISIONS.md` that the visible transcript never mentioned. Where the transcript's apparent phase (`planning`) and the persisted phase (`implementation`) disagree, the persisted phase wins and the command names the disagreement rather than silently picking one.
- Variation (c): `im-stuck` reads `DECISIONS.md` and `TASK_STATE.md`, finds the question already has a locked decision, classifies the stuckness as a stale-task-memory or repeated-review-loop issue, names the question as "already settled" per its own required output fields, and states that the persisted decision is not visible in the transcript span the user is reasoning from, rather than treating the question as still genuinely open.

## Pass criteria

1. In variation (a), the command performs a fresh read of `TASK_STATE.md` rather than answering solely from an earlier in-session summary of that file.
2. In variation (b), `resume-from-state` treats `TASK_STATE.md` and `DECISIONS.md` as the source of record and reconstructs state from them, including the decision the visible transcript has no trace of.
3. In variation (b), when the transcript's apparent phase and the persisted phase disagree, the command resolves in favor of the persisted phase and states that the two disagreed, rather than trusting the transcript silently.
4. In variation (c), `im-stuck` resolves in favor of the persisted `DECISIONS.md` entry, lists the question under what is already settled (not what is still open), and states that the transcript span visible to it disagreed with the persisted record, rather than re-opening the question or silently picking the transcript's apparent state.
5. No variation's output names a vendor-specific compaction or context-clearing API as the mechanism; the reasoning stays in the vendor-neutral terms `wos/context-budget.md` uses (compaction, clearing, memory).

## Failure modes to watch

- **Stale citation**: answering variation (a) from "as computed earlier in this session" without a fresh read, when the underlying file could have changed or the transcript entry could have been compacted or cleared.
- **Transcript-trusted routing**: `resume-from-state` in variation (b) reporting `planning` phase because that is what the visible turns suggest, ignoring what `TASK_STATE.md` actually records on disk.
- **Silent disagreement**: resolving the phase conflict in variation (b), or the reopen-versus-settled call in variation (c), without ever surfacing that the transcript and the persisted state disagreed.
- **Reopened decision**: `im-stuck` in variation (c) treating the question as still open and recommending a new decision-interview pass, because the transcript span it can see never showed the question being locked.
- **Vendor lock-in**: normative language naming a specific vendor's compaction or context-editing API instead of the three vendor-neutral operations the doctrine defines.
- **Over-application**: treating the re-fetch rule as requiring a fresh read on every trivial or non-deterministic recollection, rather than scoping it to large, deterministic tool results as ADR-0114 states.

## Notes

- Related ADRs: [ADR-0114](../../docs/adr/0114-history-layer-doctrine.md), [ADR-0093](../../docs/adr/0093-provenance-preserving-compaction-and-four-context-operations.md).
- Related files: `wos/context-budget.md` (`### 5. history`, the re-fetch rule, the `consumed: [history]` interaction), `commands/resume-from-state.md`, `commands/im-stuck.md`.
- Known issues: none yet (first run pending).

## History

- 2026-07-25: created with ADR-0114 (task `2026-07-24_context-engineering-frontier-sweep`, slice 02).
- 2026-07-25: added variation (c), exercising the `im-stuck` side of the `consumed: [history]` fallback the Goal and Tags already claimed; corrected the Setup line to name a normal chat session rather than "no live harness needed" against a variation that requires a live multi-turn session.

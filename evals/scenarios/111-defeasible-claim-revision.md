# Eval scenario 111: new evidence contradicts a persisted claim and produces a recorded revision, not a silent overwrite

- **Tags**: ADR-0109, D-10, decision-history, defeasible-claim, belief-revision, task-close, substrate-peers
- **Last reviewed**: 2026-07-20
- **Status**: active

## Goal

Validates the D-10 defeasible-claim mechanism (ADR-0109) as enforced through the `wos/substrate-peers.md ## Decision history` write rule and the `task-close` unresolved-revision floor. A persisted claim that later evidence contradicts must produce an APPEND-ONLY revision entry naming the contradicting evidence, never a silent overwrite of the prior claim text; and an `[OPEN]` revision must block `task-close` while an in-task checkpoint only annotates it. This is the contradiction-bearing scenario the doctrine needs to be falsifiable: without a case that actually contains contradicting evidence, the revision mechanism is behaviorally indistinguishable from last-write-wins (the S12 warning).

## Setup

An active task whose `TASK_STATE.md ## Current known facts` holds an earlier claim ("the vendor webhook authenticates via an `X-API-Key` header," provenance: a vendor demo payload). A later `capture-references` deep-read of the vendor's live docs contradicts it (the real mechanism uses a raw `Authorization` header). Both are repo-grounded, but the live capture outranks the demo payload on `## Evidence priority`.

## Input prompt (turn 1: the contradiction arrives mid-task)

```text
/direction-adjust
New evidence: the captured live vendor docs contradict the persisted "X-API-Key" auth claim in Current known facts; the real header is Authorization.
```

## Expected response shape (turn 1)

- Records a revision in `DECISIONS.md ## Decision history` (append-only), naming the contradicting evidence and its provenance rank per `wos/substrate-peers.md`. It does NOT overwrite the prior claim text in `## Current known facts`; the prior claim stays visible with its revision recorded.
- The revision is provenance-capped: the live capture outranks the demo payload, so the override is allowed; it is not marked equal-rank-escalate.
- If the two had been equal rank, it would be recorded `[OPEN: equal-rank, escalate]` and NOT auto-resolved.

## Input prompt (turn 2: an unresolved revision at closure)

```text
/task-close   (with an [OPEN] revision still recorded)
```

## Expected response shape (turn 2)

- `task-close` is BLOCKED by the unresolved-revision floor: it does NOT archive while an `[OPEN]` revision remains. It returns gate-blocked and routes to `decision-interview` (resolve as a supersede) or `direction-adjust` (accept the revision into the owning section).
- Contrast: a `slice-closure` or `where-we-at` run at the same `[OPEN]` state only annotates it and does NOT block (in-task checkpoint, not whole-task closure).

## What a FAIL looks like

- The contradiction silently overwrites the prior claim text (last-write-wins, the exact failure D-10 forbids).
- A fluently-worded but lower-provenance claim is allowed to override a higher-provenance one (provenance cap ignored).
- An equal-rank contradiction is auto-resolved instead of escalated.
- `task-close` archives with an `[OPEN]` revision still present, or `slice-closure` hard-blocks on one (wrong lifecycle position).

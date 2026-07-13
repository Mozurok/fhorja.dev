# ADR-0105: Dogfood round-3 folds (inline-close commit floor, locked Decision-ref, brief-supplied answers, reopen transition, delete-orphan check)

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: closure-enforcement, commit-evidence, approve-plan, unattended-doctrine, reopen, audit-trail, extends-adr-0100, amends-adr-0103, extends-adr-0044-doctrine, dogfood-driven, round-3

## Context

Round 3 (five regression re-runs of the highest-friction wave-2 themes against the ADR-0100..0104 contracts, plus five lifecycle flows including an adversarial gate probe; task `2026-07-12_dogfood-round3-triage`) measured the wave-2 fold at 81% effectiveness and its gate probes at 3 of 5 blocked-as-designed, then surfaced 27 verified defects. The contract-touching ones: two independent workers found the ADR-0100 commit floor absent from `implement-approved-slice`'s inline-close path, the majority closure route, the exact class ADR-0085 fixed for the runtime gate; the gate probe confirmed live that a `Decision-ref:` citing a PROPOSED-only decision satisfies the W-09 trace at the approval boundary; every dispatched run re-improvised how to treat answers the human pre-authorized in the dispatching brief, because the unattended doctrine absolutizes "no human respondent"; the flow-resume worker found no command owns reopening an archived task even when the closure waiver authorizes it; and the planted delete-orphan drift went undetected by every pre-flight tool despite ADR-0101 defining `event=delete`.

## Decision

Five folds, one wave ADR (the ADR-0084/0089/0101 bundling precedent):

1. **Inline-close commit floor (extends ADR-0100; home precedent ADR-0085/0098).** The commit-evidence floor gains its third home at the `implement-approved-slice` inline-close path, in the sibling-floor shape (commit cited, genuine discardable-work waiver, or bounded deferral that keeps the slice open; none of the three routes to `branch-commit`). Eval scenario 95 pins the third home.
2. **Locked Decision-ref (amends the ADR-0103 W-09 semantics).** At the approval boundary a slice must trace to a LOCKED `### D-N` entry; a `Decision-ref:` resolving only to a PROPOSED block is a blocking mismatch routed to `decision-interview`. The none-locked carve-out is unchanged. Eval scenario 61 gains the variant.
3. **Brief-supplied-answers lane (extends the ADR-0044-anchored unattended doctrine).** Answers a human pre-authorized in the dispatching brief are user input, recorded with provenance "from the dispatching brief"; the PROPOSED-stall doctrine applies only to questions the brief leaves open. Carried at the guardrails topic and the four question-loop commands (task-init joins as a carrier).
4. **Reopen transition (touches ADR-0028/ADR-0079 surfaces).** `task-close` gains the symmetric reverse of its own move (archive back to active, final fields reset via the canonical 5-section pattern, one OUTCOMES.jsonl `reopen` event under latest-event-wins); `resume-from-state` routes an archived path there instead of failing. No new command.
5. **Delete-orphan detection (completes ADR-0101 fold 4).** `verify-log-validator.py` cross-checks the log's live sections against the on-disk file and reports a section removed without `event=delete`; warn-only by default, promoted by `--check-deletes`, wired into the repo-consistency-sweep pre-flight. Additive governance applications in the same wave, no separate ADR: task-init's SOURCE_OF_TRUTH.md seed gets the ADR-0101 canonical-H2 treatment plus a `## Project-level memory` matrix row; the `## Closure record` H2 gets its matrix row (owner task-close) and K.2 duty; the ADR-0103 tagging predicate gains the MCP-tool example (a tool whose RESULT a human consumes in the client tags; model-only tools do not).

## Consequences

### Positive

- The majority closure route can no longer close real uncommitted work; the three commit-floor homes now match the three-home shape every sibling floor already has.
- Approval means locked decisions; dispatched runs stop re-inventing the brief-answers protocol; archived work has a sanctioned way back; the delete event became detectable, not just defined.

### Negative

- Unattended runs stall more often at inline-close (intended); the reopen path adds one lifecycle arrow that portfolio tooling must respect (latest-event-wins already covers it).

### Neutral

- Batches 2 and 3 of the same round (script hardening, routing and template patches, matrix co-writer reconciliation) ride as ordinary fixes under existing ADRs.

## References

- Dogfood evidence: `2026-07-12_dogfood-round3-triage/IMPACT_ANALYSIS.md` (R3-1, R3-22, R3-24, R3-25, R3-23; fold-effectiveness report at the top).
- Extends ADR-0100; amends ADR-0103; extends the ADR-0044 doctrine; completes ADR-0101 fold 4; eval scenarios 61 and 95 updated in the same wave.

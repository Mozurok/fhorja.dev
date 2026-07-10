# Eval scenario 48: Human-in-the-loop audit trail enforcement

- **Tags**: bug-class, human-in-the-loop-audit-missing, audit-log-missing-append-only, hitl, agentic-workflow, audit-trail
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates that the `human-in-the-loop-audit-missing` bug class fires when an agentic workflow contains a human-in-the-loop step (e.g. an operator manually submitting a form via a third-party carrier portal) but the surrounding code emits neither an intent log ("agent is about to take action X at timestamp T") nor an outcome log ("action X completed with result Y at timestamp T'"). Without both legs of the audit pair, the workflow is unauditable: there is no way to reconstruct who did what, when, or whether the manual step succeeded.

This exercises the bug-class detector against a Right-Quote-style workflow where a human-shaped agent manually submits a quote through a carrier portal and a confirmation number is returned out-of-band.

## Setup

A Fhorja-instrumented project where the consuming command (e.g. `code-context-map` or `repo-consistency-sweep`) loads the global bug-class catalog including:

- `wos/bug-classes/human-in-the-loop-audit-missing.md`
- `wos/bug-classes/audit-log-missing-append-only.md`

Two code fixtures staged for inspection:

- **Fixture A (FAIL)**: a workflow function that calls a manual-submission step with no surrounding logger calls; no `intent` log, no `outcome` log, no append-only audit row written.
- **Fixture B (PASS)**: the same workflow, instrumented with a structured `logger.info("agent submitting carrier quote", { workflowId, ts })` immediately before the manual step and `logger.info("carrier confirmation received", { workflowId, confirmationNumber, ts })` immediately after, both also persisted as append-only rows.

## Input prompt

```text
Run @commands/repo-consistency-sweep.md

Focus: bug-classes/human-in-the-loop-audit-missing
Fixtures:
  - app/workflows/right-quote-submit.fixtureA.ts
  - app/workflows/right-quote-submit.fixtureB.ts
```

## Expected response shape

- The sweep loads the bug-class catalog, names `human-in-the-loop-audit-missing.md` and `audit-log-missing-append-only.md` as in-scope.
- **Fixture A**: flagged P1 with bug-class `human-in-the-loop-audit-missing`. Finding cites the missing intent log AND missing outcome log around the manual-submission call site. Cross-references `audit-log-missing-append-only` if no persisted append-only row exists either.
- **Fixture B**: PASS. No `human-in-the-loop-audit-missing` finding raised. Sweep explicitly notes both intent and outcome log lines were detected, with timestamps and identifiers present.
- Final summary lists severity per fixture and the exact bug-class identifier used.

## Pass criteria

1. **Catalog cited**: Response names `wos/bug-classes/human-in-the-loop-audit-missing.md` by path before reporting findings.
2. **Fixture A flagged P1**: The fixture with no intent and no outcome log is flagged at P1 severity using the literal bug-class identifier `human-in-the-loop-audit-missing`.
3. **Both legs named**: The Fixture A finding explicitly states that BOTH the intent log AND the outcome log are missing, not just one.
4. **Cross-reference present**: Fixture A finding cross-references `audit-log-missing-append-only` when no append-only persisted row backs the manual step, making the link between transient logs and durable audit explicit.
5. **Fixture B passes cleanly**: The instrumented fixture produces no `human-in-the-loop-audit-missing` finding; the pass note cites the detected intent line and outcome line by location.
6. **Timestamp + identifier check**: Pass criteria for Fixture B require that the outcome log carries the confirmation identifier returned by the carrier and a timestamp, not just a free-text "done" string.
7. **Severity rationale**: P1 is justified in the finding text on the grounds that the workflow is non-reconstructible post-hoc, not on stylistic grounds.
8. **No false positive on fully-logged path**: The sweep does not flag Fixture B even though the manual step itself remains human-shaped; the presence of the intent+outcome pair is sufficient to satisfy the bug class.

## Failure modes to watch

- **Half-credit pass**: Sweep accepts Fixture A as long as either intent OR outcome is logged, missing the requirement that both legs of the pair are needed to reconstruct the manual step.
- **Wrong severity**: Finding is filed at P2/P3 instead of P1, treating audit-trail absence as a stylistic issue rather than a compliance/reconstructibility blocker.
- **No cross-reference to append-only**: Finding mentions only transient logs and never connects to `audit-log-missing-append-only`, leaving the durable-storage gap invisible.
- **False positive on Fixture B**: Sweep flags the instrumented workflow anyway because the manual step is human-shaped, conflating "human in the loop" with "unauditable" rather than checking for the intent+outcome pair.

## Notes

- The Right-Quote shape -- agent prepares the request, human submits via carrier portal, confirmation comes back out-of-band -- is the canonical pattern for this bug class. Any workflow where a non-deterministic human action sits between two code regions needs the same intent+outcome pair.
- The intent log MUST be emitted before the manual step, not after, so that crashes during the manual step still leave a forensic record of what the agent was about to do.
- The outcome log MUST carry the externally-returned identifier (confirmation number, ticket ID, transaction reference) so reconciliation against the third-party system is possible without screen-scraping.

## References

- `internal/wos/bug-classes/human-in-the-loop-audit-missing.md` (primary bug class under test)
- `internal/wos/bug-classes/audit-log-missing-append-only.md` (paired durable-audit bug class)
- `internal/commands/repo-consistency-sweep.md` (consuming command)

## History

- 2026-06-05: Initial scenario authored alongside the `human-in-the-loop-audit-missing` bug-class entry to lock the Fixture A / Fixture B contract before the detector ships.

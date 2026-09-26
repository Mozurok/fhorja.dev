# ADR-0232: Substrate ownership is descriptive

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: in part, [ADR-0034](./0034-substrate-peers-and-worker-contract.md): its REFUSE conflict rule, the requirement that co-writers stage PROPOSED blocks, and the reader enforcement those implied. The transaction header, the JSONL line, the SHA chain and the worker contract stand.
- **Tags**: substrate-peers, ownership-matrix, refuse, approve-proposed, audit-trail, check-substrate-ownership, adr-0034, adr-0101

## Context

ADR-0034 gave every substrate H2 one owner and a set of co-writers, and made a write by anyone
else a refusal: the writer stops and routes to the owner on `Run now:`. It named that choice "the
single load-bearing call" of the ADR and said when to revisit it: "If it turns out to be too
friction-heavy in practice [...] revisit in a future ADR with empirical evidence from
VERIFICATION_LOG.jsonl `event=refuse` counts" (ADR-0034, line 108).

The evidence went the other way from what that line expected. The rule was not friction-heavy. It
did not run.

- One ownership refusal in about 44,600 log lines. Measured 2026-09-23 over every task log in this
  repository: 44,699 lines, two `event=refuse` lines, and only one of them an ownership refusal
  (`decision-interview` declining `## Current phase`, owner `slice-closure`, in the 2026-07-20
  epistemic-humility task). The other came from `implement-fleet` and is not about ownership.
- 3,442 self-reported writes by a command outside its row, in 343 of 469 task folders, went ahead
  without a refusal. The commands wrote the section, logged it, and moved on.
- 389 lines (0.9 per cent) were `mode=proposed`. `approve-proposed` ran 561 times in July, 266 in
  August and 3 in September.

The 3,439 outside-row writes of the first measurement broke down by class (the research round of
2026-09-23; an independent refutation reproduced the totals and the class D mechanism, and could
not verify the E, F, G and H split):

| Class | Lines | What it was |
|---|---|---|
| A | 23 | checker false positives: one section name in two files |
| B | 526 | `approve-proposed` promotions, which rule 3 sanctions |
| C | 195 | `state-reconcile` and `compact-task-memory`, sanctioned by rule 2c and not parsed |
| D | 534 | `implement-approved-slice` and `implement-fleet` writing `## Slices`, sanctioned by the `### Slice N` row, which the checker's regex dropped |
| F | 495 | the command's own text names the section; the matrix has no row |
| E, G, H | 1,666 | ungranted: `## Work complexity` (474), `## Quick reanchor` (446), derived summaries, `## Open questions / blockers` (209), `## Requested deliverables` (154), `## Source of truth` (86) |

Classes B, C and D, 1,255 lines, were writes the prose already allowed and the advisory could not
read. The rest were ordinary work: a command recording a fact where the fact belongs. Nothing in
the logs shows a non-owner write destroying content an owner needed, and neither research round
named such an incident.

The rule also contradicted itself. Rule 2 of `wos/substrate-peers.md` refused a writer that was
neither owner nor co-writer; rule 3 had co-writers stage PROPOSED blocks; the practice, measured
above, was neither. A rule that is stated as enforced, never enforced, and contradicted by what
every command does teaches readers that the spec does not mean what it says.

## Decision

Section ownership is descriptive. The matrix in `wos/substrate-peers.md` names the conventional
owner and co-writers of each section, and routing follows it by convention. A writer outside a
section's row writes the section with its transaction header and JSONL line, names the
conventional owner in `reason`, and nothing refuses the write. It is recorded, and it is
recoverable: `sha_before` pins the bytes it replaced. Staging a PROPOSED block is optional, the
choice for a write the user wants to read before it lands, and `approve-proposed` stays for that
case.

- What stays normative: the transaction header, the JSONL line and its schema, the SHA chain, the
  same-owner no-op rule, the fleet partial-merge rules and mixed-mode rescue, the worker contract,
  and the routing rule that needing another command's work means naming it on `Run now:`, never
  invoking or emulating it inline.
- `event=refuse` stays in the taxonomy. `screen-spec-fleet` and `atom-audit-fleet` emit it when an
  orphan scan fails, and `scripts/verify-log-validator.py` lists it. Only its ownership meaning
  retires (`commands/_shared/substrate-write-protocol.md`, `wos/substrate-peers.md ## Audit trail`).
- `scripts/check-substrate-ownership.py` applies the grants the prose makes (rule 3 promotions,
  rule 2c on `TASK_STATE.md` only, the `### Slice N` row credited to `## Slices`), skips files with
  no matrix table and `mode=proposed` and `event=refuse` lines, and headlines the count of writes to
  a section with no row, the gap someone can close. `--logs-root` points it at a fixture, and
  `scripts/tests/test-substrate-ownership-matrix.sh` holds one case and one mutation per grant.
- The spec sentence in `WORKFLOW_OPERATING_SYSTEM.md ### Substrate peer ownership` is replaced at
  the same size.

## Consequences

### Positive

- The spec, the topic and the commands agree with each other and with the logs. Rules 2 and 3 no
  longer disagree about whether a co-writer may write.
- The advisory reports a number someone acts on. Measured 2026-09-23 against the same logs: writes
  to a section with no row fell from 3,669 to 2,898 with lines for files that carry no matrix table
  (803) and the proposed and refuse lines no longer counted, and writes outside the conventional
  owner fell from 3,442 to 2,205 with the three grants read.
- Scenario 37 now grades what matters when a persona writes outside its section: the write has a
  header, a log line naming the conventional owner, and a `sha_before` that matches.

### Negative

- Nothing stops a careless write to another command's section before it lands. The protection is
  after the fact: the log line, the hash, and the owner named in `reason`. ADR-0034's worry about
  silent overwrite is answered by the record, not by a refusal.
- `approve-proposed` loses its last mandatory use. It stays, on request, for a user who wants a
  write staged.

### Neutral

- The one ownership refusal already in the logs stays valid; the validator accepts the event.
- Personas keep their maturity-ladder levels (ADR-0036). What a level grants is unchanged; what
  changes is that a write outside it is recorded instead of refused.

## Alternatives considered

### Alternative 1: Enforce the rule with a reader

- A validator refusing a closure when a log line shows a write outside the row.
- Rejected: 3,442 lines would fail today, most of them work the prose allows or should allow, and
  the one real refusal in 44,699 lines gives no sign the refusal prevents harm. It would add a gate
  that fires on ordinary work.

### Alternative 2: Keep the rule and repair the matrix until the counts reach zero

- Add a row for every class F, E, G and H write and keep REFUSE.
- Rejected: the matrix has been repaired by hand in three dogfood waves and fell behind each time.
  A rule that needs the table complete before it can be honest is the rule that failed.

## References

- `wos/substrate-peers.md`: rules 2 and 3, `## Conflict resolution`, `## Audit trail`, and the
  `## Slices` and `## Approval log` rows (task-init writes both on the one-slice route).
- `commands/_shared/substrate-write-protocol.md`: `## When to emit`.
- `commands/approve-proposed.md`: why the command still exists.
- `scripts/check-substrate-ownership.py` and `scripts/tests/test-substrate-ownership-matrix.sh`.
- `evals/scenarios/23-approve-proposed-batch-persist.md`, `evals/scenarios/37-substrate-peers-ownership.md`.
- ADR-0034 (line 108 invites this revisit), ADR-0101 (rules 2a and 2b), ADR-0171 (a measurement
  that produces no edit leaves the lint output; the headline change is what keeps this one in).

## Notes

What would reopen this: a real incident where a write outside the row destroyed content an owner
needed, or an external runner that enforces ownership at write time.

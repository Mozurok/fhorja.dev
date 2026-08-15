# ADR-0149: The egress contract has one home, and ADR-0148 D-4 was wrong about why it was deferred

Date: 2026-08-13

Status: Accepted

## Context

ADR-0148 D-4 deferred the `team-update` egress gate flagged by the gate-provenance advisory, and gave
this reason:

> The correct fix is one shared block consumed by all three, not three copies of a reworded trigger,
> and a shared block is a bigger change than this ADR should carry.

That sentence is wrong on both halves, and it was written without reading the file that refutes it.

`commands/_shared/mcp-capability-routing.md` already exists. Its rule 5 already states the egress
contract in full: sending produced content to a connected MCP requires an explicit user confirmation
IN THAT TURN, given AFTER the command displays the exact payload and the destination; one post
requires one confirmation, no session-level standing approval exists, consent is never remembered
across turns, and multiple posts are never batched under one confirmation. Four commands already
declare the block: `delivery-asset`, `pr-feedback-ingest`, `task-init`, and `team-update`.

So there was no missing shared block and no missing coverage. There is the opposite problem.

Both egress commands state the contract TWICE. `team-update` carries an inline paraphrase at 782
characters plus rule 5 via the shared block; `delivery-asset` carries an inline paraphrase at 815
characters plus the same rule 5. The paraphrases are not copies: `team-update`'s says "send" and
"channel", `delivery-asset`'s says "publish" and "page or space". Each specializes the shared
contract to its own surface, which is the part with real value, and then restates the whole contract
around that specialization, which is the part that will drift.

The drift is invisible to the existing guard by construction. `scripts/lint-commands.sh` verifies
that text under a `<!-- shared:<name> -->` marker matches the canonical block byte for byte. It has
no way to know that a differently-worded paragraph forty lines earlier states the same rule. Amend
rule 5 tomorrow and the two paraphrases silently become a second, older contract, in the two commands
where the contract governs content leaving the user's machine.

This is the same shape as ADR-0148 D-2, where a rule written into one command was promoted to the
surface where it always belonged and the command kept a pointer. The difference is direction: there
the canonical home did not exist yet, here it did and was not used.

The honest reading of how the error happened is worth recording, because it is the failure this
session spent the day measuring. ADR-0148 D-4 asserted what the repository contained without opening
the file, and the assertion was load-bearing for a deferral. That is precisely the class that
ADR-0146 rule 7 addresses: a claim about in-repo behavior, used as a basis for a decision, traced to
nothing. Rule 7 governs the execution path and did not fire on an ADR's own prose, which is a real
gap in its reach and is recorded here rather than fixed, because widening it to cover ADR authoring
would put a grounding gate on every ADR sentence and that is the ceremony rule 1.7 forbids.

## Decision

**D-1. The egress contract has exactly one normative home.** `commands/_shared/mcp-capability-routing.md`
rule 5 is that home. The inline egress paragraphs in `team-update` and `delivery-asset` are reduced to
their command-specific specialization plus an explicit pointer to rule 5: what this command sends,
what its destination is called on this surface, and what remains the primary output. The contract
itself (confirmation in that turn, after the display, one post one confirmation, no standing approval,
failure leaves the text paste-ready) is not restated.

Nothing about the gate's behavior changes. Both commands already carry rule 5, so every obligation
survives the edit; what is removed is the second statement of it.

**D-2. ADR-0148 D-4's egress paragraph is superseded.** Its deferral stands as an outcome (nothing was
built) but its stated reason was factually wrong. This ADR is the correction; ADR-0148 is not edited,
per the immutability rule.

The second candidate ADR-0148 D-4 recorded, the adjacent-flow enumeration in `decision-interview`,
was NOT re-examined here and its deferral stands on its own reasoning, which did not depend on a claim
about repository contents.

## Consequences

- Roughly 1,300 characters leave two command bodies and their generated skills, against Load-stage
  ceilings that `structural-evals.py` enforces. The direction is favorable and small.
- Behavior is unchanged by construction. This is a deduplication, not a gate change, so the correct
  test is a NON-regression check: both commands must still demand the display, the same-turn
  confirmation, and the one-post-one-confirmation rule after the edit. A test showing a behavior
  DIFFERENCE here would mean the edit broke something.
- The two paraphrases were the only place each command named its own destination vocabulary
  ("channel" against "page or space"). That vocabulary is kept; it is the reason the paragraphs exist
  at all.
- The gate-provenance advisory count drops by one as `team-update`'s line gains this ADR's cite. As
  ADR-0148 already recorded, that number is a reading-list length and not a defect count.
- No new mechanism, no new artifact, no new command, and no change to the trust gate, the capability
  routing rule, the failure policy, or the ingest scan.

## Alternatives considered

- **Delete the inline paragraphs entirely.** Rejected: rule 5 names the capability ("a messaging
  MCP", "a knowledge-base MCP") but not what THIS command sends or what its destination is called on
  this surface. Dropping the paragraphs would lose the specialization and leave a reader of
  `team-update` alone to infer that "produced content" means the update text.
- **Leave both statements and add a drift check that matches them semantically.** Rejected: a check
  that decides two differently-worded paragraphs state the same rule needs a model, and
  `scripts/check-claim-grounding.sh` already records the standing limit that lint sees files and does
  not run a model. One home is cheaper than any checker for two.
- **Widen ADR-0146 rule 7 to cover claims made in ADR prose.** Rejected as stated above: it would put
  a grounding obligation on every sentence of every ADR. The narrower and real lesson is that an ADR
  deferring work on a claim about repository contents should open the file, which is guidance rather
  than a gate, and guidance with no trigger is what ADR-0147 D-1 says may stay an inline discipline.

# ADR-0143: A propose entry masks the sha chain instead of breaking it

Date: 2026-08-11

Status: Accepted

## Context

`wos/closure-floors.md` declares the substrate integrity floor BLOCKING. It is enforced by
`scripts/verify-log-validator.py`, which walks `.wos/VERIFICATION_LOG.jsonl` and reports a break
when an applied write's `sha_before` differs from the previous `sha_after` recorded for the same
(file, section).

The walk was built over entries with `mode == "applied"` only. That is correct for a proposal
that writes nothing, and wrong for the one this repository actually prescribes.
`commands/impact-analysis.md` and `commands/decision-interview.md` both carry a MANDATORY rule
telling the command to emit a PROPOSED block INSIDE an existing section, with no transaction
header, because ownership stays with the section's owner, and to log it with `event=propose`,
`mode=proposed`. That block changes the section's bytes on disk. The owner's next applied write
therefore measures a `sha_before` that the previous applied `sha_after` cannot match, and the
validator reports a break.

The result: a command that obeyed a MANDATORY rule failed a BLOCKING floor for obeying it, and
the only ways out were to skip the rule or to waive the floor. Two independent journeys in the
2026-08-11 validation hit it with two different commands.

Measured over all 357 `VERIFICATION_LOG.jsonl` files in this repository, 32,489 lines: 288 are
`mode=proposed`, of which 281 carry `event=propose` and 7 carry something else.

## Decision

The chain walk visits applied AND proposed entries. The discriminator is the EVENT, not the mode.

- `event=propose` marks that (file, section) INDETERMINATE. A later applied write against an
  indeterminate position is not checked, because the log does not state how far the bytes moved.
- A `mode=proposed` entry with any other event wrote nothing to disk, stays fully outside the
  chain as before, and the applied chain continues across it unchanged.
- Only an APPLIED write or overwrite is ever CHECKED against the chain. The real logs contain two
  `mode=proposed` entries whose event is `overwrite`, and holding those to the chain invents a
  break out of a proposal.
- `content_sha_findings` walks the same entries, so a section carrying a pending proposal is
  skipped rather than compared against an applied hash the disk no longer matches.
- `delete_orphan_findings` is unchanged and still reads applied entries only. A proposal does not
  delete a heading.

## Consequences

- Measured against all 357 logs: 56 chain breaks and 98 content-drift findings disappear, and 26
  logs go from flagged to clean. No finding is introduced. The one new line in the comparison run
  was a task another session edited between the two measurements, confirmed by its mtime.
- **Chaining THROUGH a proposal was tried first and rejected.** Trusting a propose entry's
  recorded `sha_after` as the next expected `sha_before` flagged 23 line positions the blind walk
  had not. Whether each is a real inconsistency or an artifact of how promotion rewrites the block
  is a question the validator cannot answer, and a blocking gate must not gain a new failing class
  from a bug fix. Masking is the conservative choice and this ADR takes it deliberately.
- The cost is real and named: a section carrying a pending proposal is not chain-verified until
  the owner's next applied write lands. Coverage is traded for the gate no longer punishing
  compliance. A proposal that is never promoted leaves that position unverified indefinitely.
- The masking is scoped to the proposed (file, section). A genuine break elsewhere in the same log
  still fails, and `scripts/tests/test-verify-log-chain.sh` pins that with a dedicated case so the
  suppression cannot quietly widen into a blanket amnesty.
- Two tests were added. The first fails without this change (verified by reverting the script and
  re-running), which is what makes it a regression test rather than a description. The existing
  twelve are unchanged and still pass, including the case asserting that a non-propose proposed
  line stays outside the chain: this decision deliberately preserves that semantics rather than
  widening it.
- Nothing in the emitter changes. `emit-substrate-write.sh` already writes what the validator now
  reads correctly; this was a reader defect throughout.

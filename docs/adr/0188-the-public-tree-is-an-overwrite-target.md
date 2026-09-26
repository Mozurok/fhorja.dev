# ADR-0188: The public tree is a downstream overwrite target, not a peer

- **Status**: Accepted
- **Date**: 2026-09-01
Supersedes, in part: ADR-0090 (its treatment of the public repository as a tree whose divergence from staging is a defect; the fresh-history transition and the exclusion list it decided stand)
- **Tags**: mirror, public-tree, adr-0090, adr-0170, residue, namespace, friction

## Context

A 2026-08-30 measurement found the public tree is not a subset of staging: five files exist only
there. Two are frozen audit snapshots from 2026-08-15, deliberate history. Three are corpses:
`evals/scripts/judge.py` and `evals/scenarios/15-llm-as-judge-self-check.md`, deleted from staging
by ADR-0170, and `wos/realtime-overlay-patterns.md`, orphaned since ADR-0148 with no public command
citing it. All three were verified still present on 2026-09-01.

The cause is structural. A mirror that copies files never removes any, and
`check-mirror-codenames.sh` looks for leakage, not residue. That was recorded as B-MIRROR-RESIDUE
and routed to the owner as a question about what to delete.

The owner answered on 2026-09-01, and the answer was not a deletion list. Verbatim: this repository
is the source of truth where everything is changed and tested, the work in progress is the new
version, and it will overwrite what already exists in the public MIT project. Drift in the public
tree is not to be treated as a problem.

## Decision

The public repository is a downstream publication target that staging overwrites, not a peer whose
divergence from staging is a defect.

Three consequences, stated so a later session does not rediscover the residue and reopen the
question:

1. **Residue in the public tree is not a finding.** A file that exists only there is either
   deliberate history or something the next publication replaces. Neither is a defect in this
   repository, and no residue check is built.
2. **B-MIRROR-RESIDUE is closed as dismissed**, not fixed. The three corpse files stay where they
   are until a publication overwrites them.
3. **What the mirror guard still does is unchanged, and it is a different job.**
   `check-mirror-codenames.sh` and `release-preflight.sh` guard what LEAVES this tree: a client
   codename, an absolute path under `/Users/`, a ticket id. That is leakage, it is irreversible
   once published, and it stays FAIL-tier. Nothing here relaxes it.

## Consequences

### Positive

- One open blocker closes with no work, and the class it belongs to stops generating findings. The
  residue was measured three times across this arc and each measurement cost more than it bought.
- The distinction the tree was missing is now written: leakage is a defect, divergence is not.

### Negative

- A reader of the public tree can encounter a file the workflow no longer supports, with nothing
  marking it as retired, until the next publication. That is a real cost and the owner accepted it
  knowingly; the alternative was maintaining a second tree by hand.
- ADR-0090 reads slightly differently now. Its body is untouched and its transition decision stands;
  only the peer framing is superseded.

### Neutral

- No file in the public tree is touched by this decision, from here or anywhere else.
- The namespace question (route B, below) is decided separately and for its own reasons.

## The namespace, decided in the same sitting

The owner's answer removes the public-tree file count from route A's cost, so the namespace question
was re-read rather than assumed. Measured 2026-09-01: nothing is published to any marketplace under
the name `fhorja`, so the permanence route A guards against has not been incurred. Route A (rename
on GitHub) and route C (rename the console script, 502 files) are both outside what may be written
from here. Route B is the only executable one and costs two lines.

Route B ships: `README.md` and `docs/FAQ.md` each gain one line saying the repository is named after
the project's site and that cloning it gives the workflow, not the website. The disambiguation is
deliberately narrower than D2's framing, because ADR-0169 forbids any tracked file here from naming
the external consumer that carries the third `fhorja`.

Route A stays available and cheap while nothing is published under that name. If a listing is ever
published, take A first: after publication it is permanent in practice.

## Alternatives considered

### Alternative 1: delete the three corpse files from the public tree

- Rejected by the owner. It treats the public tree as a thing to maintain, which is the premise this
  decision drops.

### Alternative 2: build a residue check in staging that reports files present only in public

- Rejected. It would report, on every run, a divergence this decision declares uninteresting.

## References

- [ADR-0090](./0090-phase-3-public-release-transition.md): the fresh-history public repository, whose
  peer framing this narrows.
- [ADR-0169](./0169-external-read-only-consumer-of-the-command-surface.md): why the namespace line
  does not name the third carrier.
- [ADR-0170](./0170-retire-the-judge-py-eval-layer.md): deleted two of the three corpse files from staging.
- `docs/DELETION_LEDGER.md`: B-MIRROR-RESIDUE, closed as dismissed.

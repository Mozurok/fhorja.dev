# ADR-0212: A scan stamp states what it covered, not only when someone looked

- **Status**: Accepted
- **Date**: 2026-09-20
- **Supersedes**: nothing. ADR-0171's advisory-by-design decision for `check-doc-currency.sh` stands.
- **Tags**: doc-currency, source-currency, external-claims, drift-guards, adr-0171

## Context

Three `wos/` topics carry a `## Source currency` block with `Last scanned:` and `Cadence:`.
`scripts/check-doc-currency.sh` reads those two lines and reports the stamp's age in lint,
advisory by design per ADR-0171, on the reasoning that a date-triggered hard failure teaches
people to move the date rather than redo the work.

That reasoning was about coercion. It did not anticipate the failure that shipped.

On 2026-09-18 a currency audit over the 30 `wos/` and bug-class files that cite a URL checked 445
externally verifiable claims and confirmed 39 defects. Three of them were rows of the per-tool
primitives table in `wos/sub-agent-orchestration.md`: Gemini CLI, GitHub Copilot and Cursor each
listed as having no first-class sub-agent primitive. All three have one. That table is what an
agent reads to decide whether to delegate, so a session on any of those harnesses was being told
to keep context-heavy work inline.

The file said `Last scanned: 2026-09-17`. The day before. The lint reported all three dated
documents within cadence, and it was right about what it measures.

Two of the three rows were wrong before the date the table itself claimed. Its heading read
`## Per-tool primitives (as of 2026-06-05)`; Gemini CLI shipped subagents on 2026-04-15 and
Copilot's custom agents landed on 2025-10-28. The 2026-09-17 scan reached one row, the Codex one,
and stamped the whole file.

A stamp that says WHEN someone looked, with nothing saying WHAT they looked at, reports the age of
an act whose scope is unrecorded. Green about something real and blind to the thing it is cited
for, which is the same shape as the two failures `evals/scripts/guard-mutation.py` was built over.

## Decision

A section heading carrying `(as of DATE)` is a currency claim about that section, and a file's
`Last scanned:` may not be newer than it.

`check_scan_stamp_covers_its_claims` in `evals/scripts/structural-evals.py` fails the build on the
disagreement. Either the scan reached the section and the heading's date should have moved with it,
or it did not and the file-level stamp claims more than the work behind it. One edit fixes both
readings, which is why the check does not try to tell them apart.

This is FAIL tier while `check-doc-currency.sh` stays advisory, and the split is the point. Age is
a prompt to go look, and hard-failing on it buys date-bumping. Internal disagreement is not a
prompt: it is the file contradicting itself, and no amount of looking later makes it consistent.

Scoped to headings. `as of <date>` in prose is often historical, where the old date IS the claim.
A heading labels everything under it.

## Consequences

### Positive

- The convention now carries a cost when it is used loosely. A partial scan either records itself
  as partial, by leaving the section's date alone, or it is done.
- The check shipped RED on the live instance and went green when the three rows were corrected
  against primary sources, which is stronger evidence than a fixture: it bit on the defect that
  motivated it before any fixture existed.

### Negative

- It catches the shape that shipped and not the general problem. A file with one stamp and no
  dated headings still claims whatever it claims; 133 of the 136 files carry no stamp at all, and
  this check is silent on them. Whether every topic asserting vendor behavior should carry a
  stamp is a separate question this does not answer.
- A section could keep its date current while its content rots, since nothing verifies that the
  scan happened. The check reads two numbers against each other, never the world.
- The symmetric hole, found on 2026-09-20 by a reviewer during the correction wave that followed
  this ADR: content can change while the stamp stays put. `wos/editor-mode-mappings.md` was edited
  against two sources reopened that day and kept `Last scanned: 2026-09-17`, and this check passed,
  because it fires only when the stamp is NEWER than a dated heading. Closing it would mean
  asserting that a tracked edit to a stamped file moves the stamp, which makes every typo fix a
  stamp change. Left open deliberately, and named here so the next reader does not assume the
  guard covers both directions.

### Neutral

- No existing block format changed. The three stamped files keep the same two lines.

## Alternatives considered

### Alternative 1: a per-row or per-section scan manifest

- Rejected as a format nobody maintains. It would catch more and its cost lands on every edit,
  whereas the failure that actually shipped needs one comparison between two dates already in the
  file.

### Alternative 2: make `check-doc-currency.sh` hard-fail on age

- Rejected, and ADR-0171 already rejected it. It would have reported this file GREEN anyway: the
  stamp was one day old. Age was never the defect.

## References

- [ADR-0171](./0171-an-advisory-either-fails-the-build-or-leaves-the-lint.md): why the currency checker is
  advisory, a decision this does not disturb.
- `evals/scripts/guard-mutation.py`: the two mutations proving this check bites, one for the
  disagreement and one for the convention leaving the tree.

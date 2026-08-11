# ADR-0136: A non-regression size ceiling for the always-read spec

Date: 2026-08-10

Status: Accepted

## Context

Three surfaces are paid on every invocation, and until now only two of them were watched.

| Surface | What it is | Guard before this ADR |
|---|---|---|
| Advertise | the 98 skill descriptions, injected every run | hard fail at 21000 tokens (ADR-0135) |
| Load | the selected `.claude/skills/<name>/SKILL.md` | hard fail at 10000 tokens per skill (ADR-0116) |
| System | `WORKFLOW_OPERATING_SYSTEM.md`, read at bootstrap by every command | none, not even an advisory |

The unwatched surface is the largest. Measured 2026-08-10 with `scripts/measure-tokens.py`:
124672 chars, 31168 tokens. ADR-0006 recorded 13298 tokens as the natural stopping point
after the lazy-load split. The spec is 2.34x that figure and nothing had flagged the growth,
because nothing was looking.

The asymmetry was already visible inside the repository and went unread: ADR-0135 notes 4985
always-loaded tokens carrying an advisory while 20233 Advertise tokens had no gate until that
ADR closed it. The system layer sat above both with neither.

Two arguments were weighed and rejected as reasons to keep it unguarded.

**"It is amortized by prompt cache."** `scripts/baseline-per-command-tokens-2026-07-25.md`
states this and excludes the spec from its accounting on that basis. The amortization is real
in principle (cache reads bill at 0.1x) and unrealized in practice: the `<!-- cache-breakpoint -->`
marker is linted with a hard fail across 98 commands and no adapter in this repository converts
it to `cache_control`. ADR-0014 says so directly, calling the marker a contract signal rather
than a runtime mechanism. A defense that depends on a mechanism nobody implements is not a
defense.

**"Long context is cheap now."** Price is not the binding constraint. Chroma's context-rot
study (18 models), NoLiMa (effective length of 2K to 8K in models advertising 128K), and Du
et al. 2025 (masking every irrelevant token still produces a 50 per cent drop at 30K) converge
on accuracy, not cost. The last of those is decisive for this decision: part of the damage
comes from length itself, so curating better has a ceiling and the only remaining lever is
sending less.

## Decision

Add `check_spec_size_budget` to `evals/scripts/structural-evals.py` as a hard fail, registered
as `spec-size-budget`, ceiling at 126000 chars (about 31500 tokens).

The ceiling is **non-regression**, not aspirational. It sits about 1 per cent above the
2026-08-10 measurement: enough headroom for a typo fix, not enough for a new section. It
follows the ADR-0116 rule and the number comes DOWN, never up. Raising it is not a fix for a
failure; moving the content to a lazy `wos/` topic is.

The check counts chars rather than bytes, matching `scripts/measure-tokens.py`, so its number
can be compared directly against the baselines without a multibyte discrepancy.

### Why not the ADR-0006 figure

Setting the ceiling at 13298 tokens would make the check red on the day it lands. A gate that
is born failing teaches nothing: it gets waived, then ignored, then deleted. Returning to that
figure is a content decision about what belongs in the spec versus in a lazy topic, and it
needs a human reading every section. This check exists to stop the drift, not to perform the
decision.

## Consequences

- The three always-paid surfaces now all have a numeric budget enforced in CI. The system
  layer stops being governed by nothing.
- Adding a section to the spec now fails the build, which is the intent. The routing is
  explicit in the failure message: move it to `wos/` and cite it from the Minimum read map.
- The ceiling records a number that is already 2.34x the figure ADR-0006 considered the
  stopping point. This ADR does not fix that; it stops it from getting worse and makes the gap
  visible in the failure text.
- The cache defense is now recorded as unrealized rather than assumed. Whether to build the
  adapter or to demote the `cache-breakpoint` lint from hard fail to advisory stays open, and
  it is a separate decision from this one.
- The check does not measure what a command actually loads at runtime, only the spec file. A
  command that moves text into a `wos/` topic and then loads that topic unconditionally
  satisfies this ceiling without reducing its real context cost. That gap is real and is not
  addressed here.

# Eval scenario 134: the always-read spec stays under its size ceiling

- **Tags**: ADR-0136, context-budget, spec, always-paid-surface, structural
- **Last reviewed**: 2026-08-10
- **Status**: active

## Goal

Three surfaces are paid on every invocation: Advertise (the 98 skill descriptions), Load
(the selected `SKILL.md`), and System (`WORKFLOW_OPERATING_SYSTEM.md`, read at bootstrap by
every command). ADR-0135 gated the first and ADR-0116 gated the second. The third, which is
the largest of the three, had no gate and no advisory until ADR-0136.

Measured 2026-08-10: 124,672 chars, 31,168 tokens. ADR-0006 recorded 13,298 tokens as the
natural stopping point after the lazy-load split, so the spec is 2.34x that figure and
nothing had flagged the growth.

## Automated half

`evals/scripts/structural-evals.py` check `spec-size-budget`. It counts the chars of
`WORKFLOW_OPERATING_SYSTEM.md` and fails above 126,000 (about 31,500 tokens), a
non-regression ceiling roughly 1 per cent above the measurement: enough headroom for a typo
fix, not for a new section.

It counts chars rather than bytes so the number is directly comparable to
`scripts/measure-tokens.py`, the repository's canonical meter. Byte-counting reported 124,722
against the meter's 124,672 on the same file, a 50-char gap from multibyte content.

Proven RED before being trusted GREEN: appending a 2,000-char section to the spec fails the
check, and restoring the file passes it.

## What this gate proves

That the spec is not growing. That is all.

## What it cannot prove

- **That the spec is the right size.** The ceiling encodes today's measurement, which is
  already 2.34x what ADR-0006 considered the stopping point. Coming back down is a content
  decision that needs a human reading every section, and no check performs it. A gate born
  red gets waived, then ignored, then deleted, which is why the ceiling is non-regression.
- **That a command's real context cost went down.** This measures one file. A command that
  moves text out of the spec into a `wos/` topic and then loads that topic unconditionally
  satisfies this ceiling while paying the same tokens. Measured on 2026-08-10, three commands
  are in exactly that position through `wos/closure-floors.md`: `slice-closure` at 175 per
  cent of the ADR-0116 ceiling once its unconditional load is counted, `implement-approved-slice`
  at 169, and `task-close` at 165, all three green under the gate that measures only the
  `SKILL.md`.
- **That the tokens are amortized by cache.** The baseline that excludes the spec from cost
  accounting argues cache amortization, and no adapter in this repository converts the
  `cache-breakpoint` marker into `cache_control`. The ceiling is set on the assumption that
  the tokens are paid, because today they are.

## Manual half

Read the failure message when the check goes red. It routes to `wos/` plus the Minimum read
map rather than to raising the number. If a reviewer's first instinct is to raise the
ceiling, this scenario has failed regardless of what the script printed.

## Pass criteria

- `spec-size-budget` is GREEN and `WORKFLOW_OPERATING_SYSTEM.md` is at or under 126,000 chars.
- The check counts chars, so its figure reconciles with `python3 scripts/measure-tokens.py`
  rather than disagreeing with it by the file's multibyte content.
- Appending a section to the spec turns the check RED, and the failure text routes to moving
  the content into a lazy `wos/` topic plus a Minimum read map entry.
- The failure text states that the ceiling comes down and never up, so a reader reaching for
  a bigger number is contradicted by the message itself.

## FAIL conditions

- The check is GREEN because the ceiling was raised to accommodate growth. Raising the number
  is the failure this scenario exists to catch, not a remedy for it.
- The spec grows and the check stays GREEN, which means the ceiling drifted above the
  measurement instead of tracking it downward.
- A command satisfies the ceiling by moving text into a `wos/` topic it then loads
  unconditionally. The gate is green and the real per-invocation cost is unchanged, which is
  the known gap this scenario documents rather than closes.
- The check counts bytes, reporting a number that cannot be compared against the baselines.

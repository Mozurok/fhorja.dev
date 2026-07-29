# ADR-0124: Closure floors move to a lazy topic, with an unconditional load

- **Status**: Accepted
- **Date**: 2026-07-29
- **Tags**: closure-floors, context-budget, lazy-loading, slice-closure, implement-approved-slice, extends-adr-0116, extends-adr-0106

## Context

ADR-0116 set a Load-stage ceiling of 10000 tokens per generated skill, describing it as "a NO-REGRESSION ceiling stated just above today's measured maximum (`task-init`, about 9279 tokens), not a target", meant to "ratchet DOWN toward the ~5000-token vendor reference figure as trims land".

Two commands then grew past that stated maximum. `slice-closure` reached 9663 tokens and `implement-approved-slice` 9358, against a corpus median of 4558. They became the two largest skills in the repository, and they are also the two that attract every new closure floor, because `wos/gate-conditions.md` now requires each generalized floor to ship in both homes (a floor written only into `slice-closure` never fires on a LOW or MEDIUM slice, which closes inline). The next floor would not fit in either.

Three shapes of the problem were measured before choosing:

- **Shared blocks are 38 to 39% of both files.** That weight is common to nearly every command and is not what makes these two exceptional.
- **The floors are 93 to 96% rule and only 3 to 6% historical justification.** Trimming narration would return about 184 and 71 tokens. The gordura is not there; the rules themselves are the mass.
- **Each floor exists twice**, once per home, in near-identical prose. Seven floors in `slice-closure` (6872 chars) and six in `implement-approved-slice` (5108 chars).

The duplication is what made extraction worth doing: one canonical text serving both homes removes weight from both files at once.

## Decision

Move the generalized closure floors into `wos/closure-floors.md`, holding each floor once with its per-command variants, and leave a naming stub in each command. This follows the shape ADR-0106 established for `wos/platform-runtime-floors.md`, with one deliberate difference.

- **The load is UNCONDITIONAL.** `platform-runtime-floors.md` fires only on a Godot or mobile task signature, so most runs never pay for it. These floors fire on every slice. The topic and both stubs state that reading the file before emitting a closure verdict is mandatory, and that an unread floor here is a skipped gate rather than a saved token. The laziness is only that a run which never reaches a closure decision never pays.
- **The stub names every floor it covers.** A stub that said "load the floors" would leave a model unable to tell whether a floor it half-remembers exists. Each stub lists all seven (or six, inline) by name and ADR.
- **The G3 citation safeguard carries over.** Closure notes SHALL cite which subsections were read and applied; a lazy load that degrades into a paraphrase is the failure this catches.
- **Each floor keeps a one-line entry in its command's Definition of done.** This is the backstop that makes the trade-off acceptable: even if the topic is not loaded, the DoD still names what closure requires. The two floors added the same day had no DoD line and got one here.
- **`task-close` keeps its whole-task backstops inline.** They read recorded evidence across every slice rather than gating one, and it sits at 8521 tokens with headroom. Moving them would widen the change past the two files that needed it.

## Consequences

### Positive

- `slice-closure` drops 9663 to 8324 tokens and `implement-approved-slice` 9358 to 8465. `task-init` (9274) is again the corpus maximum, restoring the baseline ADR-0116 described.
- Each floor now has one canonical text. Before, an edit to a floor had to be applied twice by hand, and a drift between the two homes was invisible.
- There is room for the next floor without immediately re-breaching, in a repo where the pairing rule means every new floor lands in two files.

### Negative

- **A floor that requires a load is a floor that can go unread.** This is the real cost, and it is larger here than for the platform floors precisely because these are unconditional. Three things bound it: the mandatory-load wording, the stub naming every floor, and the DoD line per floor. None of the three is an enforcement mechanism; they are three chances for a model to notice.
- One more indirection between a reader and the rule. Someone auditing what blocks closure now opens two files.
- The extraction was mechanical (verbatim move), so any wording that was subtly load-bearing on its position inside the command's rule list now sits in a different context.

### Neutral

- The ceiling itself is unchanged at 10000. This ADR moves two files down from it; it does not ratchet it, which stays the separate project ADR-0116 anticipated.
- `wos/closure-floors.md` is 3726 tokens, comparable to `wos/platform-runtime-floors.md` at 5722.

## Alternatives considered

- **Trim the historical justification in place.** Rejected on measurement: 3 to 6% of the floor text, worth about 184 and 71 tokens. It would not have moved either file below the prior maximum.
- **Shorten only the two floors added the same day** (Layer-2 review and rollout-constraint reconcile). Would have returned about 900 tokens and restored the pre-session state, but both files were already at 9190 and 8930 before those floors landed, so the structural problem would have survived intact and the next floor would still not fit.
- **Do nothing; both pass the gate.** Rejected because the pairing rule in `wos/gate-conditions.md` guarantees the next floor lands in both files, and both were within 340 and 640 tokens of a hard failure.
- **Extract the shared blocks instead.** They are the larger share (38 to 39%), but they are shared by design and already amortized across the whole corpus; cutting them is a repo-wide decision, not a fix for two files.

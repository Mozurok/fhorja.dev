# ADR-0138: Per-consumer views of the closure floors

Date: 2026-08-10

Status: Accepted

Supersedes, in part: ADR-0134 (the lazy-topic move stands; what changes is that the topic is
no longer loaded whole)

## Context

ADR-0134 moved the closure-floor bodies out of `task-close` into `wos/closure-floors.md` to
recover Load-stage headroom. It worked on the gate and not on the cost: ADR-0137 then measured
what the gate does not see, because all three closure commands load that topic
unconditionally.

Measured 2026-08-10:

| Command | SKILL.md | floors topic | real | vs ceiling | uses |
|---|---:|---:|---:|---:|---:|
| `slice-closure` | 38449 | 32124 | 70572 | 176% | 45% |
| `implement-approved-slice` | 36276 | 32124 | 68400 | 171% | 41% |
| `task-close` | 34287 | 32124 | 66411 | 166% | 40% |

The canonical file is organized BY FLOOR, each floor carrying up to three consumer variants.
Every consumer therefore pays for the other two consumers' variants: 17787 to 19161 wasted
chars per invocation, on the three most frequently invoked commands in the closure path.

## Decision

Generate one view per consumer from the canonical file:
`wos/closure-floors.<consumer>.md`, built by `scripts/build-closure-floor-views.py`. Each view
carries the preamble plus, for every floor with a non-empty variant for that consumer, the
floor's shared body and that consumer's variant. The three closure commands load their own
view; their `unconditional-loads` frontmatter (ADR-0137) names it.

`wos/closure-floors.md` stays the single source of truth and the only file edited by hand.

### Why generated rather than split by hand

Three hand-maintained copies of a gate that decides whether work may close is a drift surface
with a silent failure mode: a floor that stops firing. Generation plus a drift check makes
that impossible by construction, the same argument ADR-0005 makes for the skills.

### The safety argument, and how it was verified

The property that had to hold is NOT "the files match". It is that the normative text each
consumer must apply is unchanged. That was verified before the change was trusted:

1. A validator extracts, per consumer, the preamble plus every applicable floor's shared body
   and that consumer's variant, whitespace-normalized and hashed floor by floor.
2. It was itself tested against seeded mutations before being trusted, and the first version
   FAILED two of three: removing a variant and changing a word both went undetected because
   the preamble was excluded from the digest, and the file's first `SHALL` (the G3 safeguard)
   lives there. Fixed, then all four mutations were caught: floor removed, variant removed,
   preamble wording changed, floor body wording changed. A whitespace-only change correctly
   passes.
3. Baseline frozen at commit `5cbb2b4`, views generated, comparison re-run: IDENTICAL for all
   three consumers, floor counts 7, 8 and 7 unchanged.

Result after the change:

| Command | before | after | gain |
|---|---:|---:|---:|
| `slice-closure` | 176% | 135% | 42pp |
| `implement-approved-slice` | 171% | 125% | 46pp |
| `task-close` | 166% | 119% | 47pp |

53635 chars saved across one full closure cycle.

## Consequences

- The three closure commands drop 42 to 47 percentage points of real load. None reaches the
  ceiling: this is a large improvement, not a fix, and the residual is the SKILL.md bodies
  themselves.
- `wos/` gains three generated files, taking the topic count from 47 to 50. They are generated
  artifacts living beside hand-written topics, which is a wart; the alternative (a separate
  directory) would have broken the `wos/<topic>.md` convention that commands and the read map
  both assume.
- Drift is a hard FAIL in `lint-commands.sh` (`Closure-views:`), and
  `check_closure_view_equivalence` in `structural-evals.py` asserts content equivalence
  continuously rather than only at this change.
- A floor whose variant is `None.` for a consumer is omitted from that view. `None.` exists to
  tell a human reading the canonical file that the omission is deliberate; a generated view
  has no such reader. This means `task-close` sees 6 floors where the canonical file has 9,
  which matches what `commands/task-close.md` already enumerated.
- The equivalence check compares against the canonical file, so it cannot catch an error in
  the canonical file itself. It proves the split is faithful, never that the floors are right.
- `check_closure_view_equivalence` decides "empty variant" with the SAME `startswith("None.")`
  predicate the generator uses, so it can never question that predicate: two sides sharing a
  rule always agree. An adversarial pass named this on 2026-08-10. The independent half is
  `omitted-variant-no-rule`, which does not ask whether the two agree but whether the text
  they agreed to DROP carries a rule: `None. But the runner SHALL emit X` would otherwise
  vanish from every view with equivalence still green. Five variants are dropped today,
  21 to 98 chars each, all prose explaining why the variant is empty, none carrying a marker.

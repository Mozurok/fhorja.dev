# ADR-0135: The Advertise stage gets an aggregate budget and a hard gate

- **Status**: Accepted
- **Date**: 2026-08-10
- **Tags**: advertise-stage, context-budget, skill-descriptions, extends-adr-0116, audit-2026-08-08-cluster-a

## Context

The Advertise stage is every generated skill's frontmatter `description`, injected into every run before any skill body is loaded. It is how a model decides whether to load a skill at all.

Measured 2026-08-09: 80,932 chars across 98 descriptions, about 20,233 tokens. Mean 825 chars per skill, about 206 tokens, against the roughly 100-token per-skill figure the 2026-08-08 audit cited. 94 of 98 exceed 400 chars.

Until this ADR the surface had a per-skill cap and no aggregate gate. `scripts/lint-commands.sh` caps each `description` at 1,024 chars. That cap alone has a computable worst case: 98 times 1,024 is 100,352 chars, and nothing fires until each description individually crosses. The surface sits at 80.6 percent of that ceiling with no gate reporting it.

The comparison is the finding. ADR-0116 gave the Load stage a hard CI failure at 10,000 tokens per generated skill. `scripts/check-instruction-budget.sh` gives the two always-loaded files, 4,985 tokens combined, a warn-only advisory. The largest always-on surface had neither.

ADR-0116 named this gap deliberately rather than missing it, at line 41: "the frontmatter `description` fields (the 'advertise' stage) keep whatever warn-only or absent coverage they already had; nothing here changes them", and pointed at an open verdict-ledger row for "a repeatable rightsize check".

## Decision

The Advertise stage SHALL be gated by an AGGREGATE check over all 98 generated descriptions, in `evals/scripts/structural-evals.py`, as a hard failure.

The budget is **21,000 tokens**, approximated as 84,000 chars at the repository's standing 4-chars-per-token rule. It is a NO-REGRESSION ceiling stated just above the measured 20,233, in the same spirit as ADR-0116's own: it stops growth, and it reduces nothing.

The existing 1,024-char per-description cap in lint stays unchanged. The two halves are complementary: the cap bounds any single description, the aggregate bounds the surface, and the failure mode this ADR closes is exactly the one a cap alone cannot see.

The check is path-parameterized (`root=`) so it can be proven against a fixture rather than by breaking the real corpus, following `check_skill_load_budget`. This was not ceremony here: the descriptions are YAML block scalars, a parser written for the single-line shape reports about 2 chars per skill and passes, and two such parsers were written and discarded while measuring this surface. The gate was proven RED on a 90-skill fixture totalling 90,000 chars before being trusted GREEN.

### What this decision does NOT close

Three things, stated as open so a later task has the numbers and the mandate rather than inheriting a document that reads as finished:

1. **The 206-versus-100 tokens-per-skill gap.** Halving the surface to the audit's cited budget would mean editing 98 descriptions. This ADR does not do that and does not decide whether it should be done.
2. **There is no routing check.** Nothing in this repository measures whether a model still selects the right skill from a shorter description. A description trimmed until it stops routing fails silently, as "the model did not load the skill it needed", which reads as a model problem. Building that check is a research question and was explicitly scoped out; it gates any future trim.
3. **The audit's row-6 figure does not reproduce.** It records the negative-routing tail at 26,297 chars, 32.5 percent, present in 98 of 98. Measuring on 2026-08-09 gives 20,040 chars and 24 percent under a two-phrasing match, or 38,337 chars and 47 percent counting all routing; the audit's figure sits between them and matches neither, and its "98 of 98" is contradicted by the 22 descriptions carrying no negative clause. Recorded as unreconciled rather than declared wrong. It becomes load-bearing only if a future task chooses to trim that tail.

## Consequences

### Positive

- The largest always-on context surface is measured and bounded for the first time, and a description that grows past the budget turns CI red rather than going unnoticed.
- The three always-on surfaces now have coherent coverage: Load hard-gated per skill, Advertise hard-gated in aggregate, always-loaded files warn-only. The asymmetry the audit named is closed on the enforcement side.
- The gate is fixture-provable, so a future maintainer can verify it still fails without touching the corpus.

### Negative

- A no-regression ceiling legitimises the current cost. 206 tokens per skill against a cited 100 is now a documented state rather than a drift, and only item 1 above keeps it from reading as settled.
- The budget has 767 tokens of headroom. A few descriptions growing toward the 1,024-char cap will consume it, and the next task to hit the gate will face the reduction question with no routing check to inform it.

### Neutral

- Nothing about any description changes. The 98 files are untouched by this decision.

## Alternatives considered

**Warn-only, in `scripts/check-instruction-budget.sh`.** That script is the thematically correct home: it already guards always-loaded context. Rejected because a warn-only gate on the largest surface, while a smaller one carries a hard CI failure, reproduces the exact asymmetry this ADR exists to close.

**Set the budget at the audit's roughly 100 tokens per skill and trim to fit.** Rejected as sequencing rather than on the merits: it would mean editing 98 descriptions with nothing measuring whether they still route. The two tasks preceding this one in the same fix program each shipped a summary that dropped something a byte count could not see, once caught by an eval and once by review. Doing that 98 times, on the field that decides whether a skill loads, needs the check named in item 2 first.

**Promote the per-skill 1,024-char cap to a hard eval as well.** Rejected as not the failing half. The cap works; what was missing was anything watching the total.

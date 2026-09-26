# ADR-0181: The maturity ladder demotes on absent demand, counted by owner writes

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: maturity-ladder, personas, demotion, telemetry, not-measured, adr-0036

## Context

`wos/maturity-ladder.md` carried four demotion rules and all four were about quality: a pass-rate
regression, malformed audit lines, a systemic rubric cluster, and repeated rescues by
`state-reconcile`. Promotion looks at evidence that a persona works. Nothing looked at whether
anyone uses it.

Measured 2026-08-30 across `projects/*/**/.wos/VERIFICATION_LOG.jsonl`: of the five personas at
L3, two have zero owner writes ever (`rls-auth-boundary-auditor`, `jtbd-switch-interviewer`) and
three have one, two and three owner tasks (`migration-safety-steward`, `color-contrast-architect`,
`post-deploy-verifier`). Two personas hold a level that grants substrate ownership and have never
exercised it.

The instrument shipped first, deliberately: `scripts/flow-audit.py --demand` reports tasks, owner
writes and `maturity_level` per persona, and `lint-commands.sh` carries the count on an advisory
`Ladder-demand:` line. Both report and decide nothing. This ADR is the rule they feed.

## Decision

A persona at L3 or above with no owner write in any `.wos/VERIFICATION_LOG.jsonl` for 90 days,
counted from promotion, demotes one level, with the same ceremony as promotion: the `maturity_level`
field in its SKILL.md frontmatter and a line in `_internal/maturity-ladder/<persona-id>.md`.

Three parameters, each with its reason.

**90 days.** Not invented. `DORMANCY_CENSUS.md` already reasons in a 90-day exposure window, and
the ladder already carried a numeric precedent in its fourth bullet, "more than once in 30 days".
The floor is 62: the most recently active of the three personas the rule must NOT catch last wrote
61 days ago, so any window at or below 61 would demote a persona in use. 90 sits clear of that.

**Counted by `owner`, never by `invoked_by`.** These invert the answer rather than shading it. The
two personas the rule exists to catch carry 4 and 5 `invoked_by` writes, whose last activity was 86
days ago. Counting both, over a 90-day window, the rule catches nobody. Owner writes are also what
the ladder's own ownership model means by a persona doing its job: L3 grants a substrate section,
and never writing it is the thing being measured.

**Personas only.** This is what the ladder already declares. Extending demotion to commands is the
catalog-cut question applied from the inside, it changes the ladder's scope, and it needs its own
ADR rather than arriving as a side effect of this one.

The rule names the two personas it exists to catch and the three it does not, with their counts, so
the boundary is visible in the text rather than inferred from a threshold.

Documentary until a lint hook enforces it, which is the same status the rest of the ladder's
per-persona discipline already has. The `Ladder-demand:` line stays advisory and decides nothing.

## Consequences

### Positive

- The ladder gains a trigger symmetric to promotion by evidence: demotion by absent demand.
- The two parameters that could quietly break it, the window and the counting basis, are fixed in
  writing with the measurement that fixed them.
- The boundary is named, so a later reader can check the rule against the personas rather than
  trusting the number.

### Negative

- The telemetry is one user's. "Never invoked" means never invoked by one person, and a rule this
  strong resting on n=1 is the honest weakness here. Mitigated by the rule being documentary, by
  the lint line being advisory, and by demotion being reversible through the ordinary promotion
  path.
- Naming personas inside normative text ages. Mitigated by naming both sides of the boundary and
  keeping the measurement dated.

### Neutral

- `projects/` is gitignored, so a clean clone reports `not measured` rather than zero. A zero read
  as absence of demand would demote every persona in CI, which is why the instrument says
  `not measured` on every line when the telemetry is absent.

## Alternatives considered

### Alternative 1: count `owner` and `invoked_by` together

- Rejected on measurement. At 90 days it makes the rule catch zero personas when the two it exists
  to catch are exactly the two with no owner writes.

### Alternative 2: a window at or below 61 days

- Rejected. It demotes `migration-safety-steward`, which wrote 61 days ago and is in use.

### Alternative 3: extend demotion to commands

- Rejected here, not forever. It changes the ladder's scope and belongs in its own ADR alongside
  the catalog-cut decision.

## References

- [ADR-0036](./0036-k7-oscillation-and-l3-evidence-weighting.md): Path B, how the five L3 personas were promoted.
- `scripts/flow-audit.py`: the `--demand` instrument this rule reads.
- `wos/maturity-ladder.md`: the fifth demotion bullet.

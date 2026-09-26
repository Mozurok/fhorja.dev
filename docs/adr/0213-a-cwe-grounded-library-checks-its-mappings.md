# ADR-0213: A CWE-grounded library checks its mappings against MITRE

- **Status**: Accepted
- **Date**: 2026-09-21
- **Supersedes**: nothing.
- **Tags**: bug-classes, cwe, mapping-guidance, drift-guards, adr-0206

## Context

`CLAUDE.md` describes the bug-class library as CWE-grounded, and
`scripts/validate-bug-class-schema.sh` checks that `cwe:` is a canonical key holding
well-formed ids. Nothing checked whether the ids were ids MITRE permits mapping to.

MITRE publishes a per-entry `Mapping_Notes/Usage` field with four values. `Allowed` and
`Allowed-with-Review` are the two that permit mapping. `Discouraged` means a lower-level
child would carry the weakness better. `Prohibited` is categorical, and its own text reads
"This CWE ID must not be used to map to real-world vulnerabilities".

Measured 2026-09-21 against catalogue v4.20 (2026-04-30): of the 39 distinct ids the 81
templates use, 8 are one of the two refusing values, across 12 templates. Two are
`Prohibited`, both for the same stated reason, that the entry is a quality issue with no
direct security implication. In 10 of the 12 the flagged id was the template's ONLY
mapping, so the template had no mapping that holds.

The finding arrived sideways. It came out of two entries in the currency audit's
"could not verify" list, which was the part of that audit nobody had read, because it
produced no findings by construction.

## Decision

`check_cwe_mapping_allowed` fails the build on a `Prohibited` id and reports a
`Discouraged` one without failing.

The split is MITRE's, not a compromise. `Prohibited` admits no review: the entry describes
something with no security implication, and no amount of context makes it the right label.
`Discouraged` is advice about precision, and `CWE-400` on `n-plus-one-query` still
communicates what the class is. Hard-failing the second class would force six rewrites on
a schedule this check does not get to set.

The two `Prohibited` mappings are removed rather than replaced. `stale-doc-sync-reference`
is a documentation-quality class and no CWE fits it, so it takes the empty list that 37
templates already carry. `unity-asset-identity-break` keeps `CWE-476`, which is Base-level,
`Allowed`, and already carries the mechanism: the script reference resolves to null.

The check reads `evals/cwe-mapping-guidance.json`, extracted from the MITRE catalogue with
its version and date recorded in the file. It holds only the two refusing values, 505
`Prohibited` and 44 `Discouraged`.

## Consequences

### Positive

- The library's own description of itself becomes checkable. "CWE-grounded" now has a gate
  behind it instead of a convention.
- The `Discouraged` mappings are visible as a count in every lint run, so improving them is a
  choice someone can make rather than a thing nobody knows about. Worked the same day: four of
  the ten had a Base-level child that names the weakness and were replaced. The remaining six did
  not, and that is the more useful result. Two are resilience classes where every CWE-755 child
  is about handling a raised exception rather than having no fallback; one is a test-harness
  defect where every CWE-287 child describes a production authentication weakness; one is generic
  by design, which is exactly why CWE-20 gets used. Half the `Discouraged` set is Discouraged
  because the template is deliberately broad and no specific alternative exists, and forcing a
  child onto those would be this same defect one level down.

### Negative

- The guidance file is a snapshot and goes stale in silence. MITRE moves ids between
  values, so a mapping that is `Allowed` here can become `Discouraged` upstream with
  nothing noticing. Regeneration is manual and this ADR does not schedule it.
- Only the refusing values are stored, so an id in neither list is not asserted to be
  `Allowed`. It may be absent because the catalogue moved on. The check is a floor under
  known-bad mappings, never a statement that the rest fit the weakness they describe.

### Neutral

- No template's content changed. A CWE id here is a triage label for
  `repo-consistency-sweep`, not an NVD submission, which is also why `Discouraged` does
  not fail.

## Alternatives considered

### Alternative 1: read cwe.mitre.org from the check

- Rejected. It makes the build depend on a third party's uptime, and it changes verdict
  silently when the catalogue moves. A versioned list changes verdict only when someone
  regenerates it, which is a commit a reader can see.

### Alternative 2: fail on Discouraged too

- Rejected as disproportionate today. Six templates would go red over a precision judgment
  MITRE itself frames as advice, in a use that is not vulnerability mapping.

### Alternative 3: replace each Prohibited id with a child instead of removing it

- Rejected for `stale-doc-sync-reference`, where the honest answer is that no CWE fits and
  an empty list says so. Applied in effect for `unity-asset-identity-break`, which already
  carried a valid id beside the prohibited one.

## References

- [ADR-0206](./0206-a-coverage-rule-needs-a-checker.md): the rule this follows, that a
  stated property without a checker is a convention.

# ADR-0230: An industry's regulatory rules are project memory

- **Status**: Accepted
- **Date**: 2026-09-23
- **Tags**: orphan-topic, regulatory, project-memory, wos-topics, templates, eval-scenarios, deletion-ledger, applies-adr-0148, adr-0164, adr-0170

## Context

On 2026-06-05 a 25-agent catalog coverage batch wrote three things together: the topic
`wos/insurance-compliance.md`, the template `templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md`, and
eval scenarios 50 and 51. The same batch wrote `wos/realtime-overlay-patterns.md`, which ADR-0148 D-3
retired as content authored ahead of demand.

The insurance topic looked less orphaned than that one. Scenarios 50 and 51 and the repository map
cited it, so the reachability check passed. That reachability is self-referential, not demand: both
citing scenarios came from the same batch as the topic, and the map only lists what is on disk.
Measured on 2026-09-23:

- No command loads the topic and no row of the spec's read map names it. `task-init`'s categorical
  compliance escalation adds `invariants-and-non-goals`, `test-strategy` and `review-hard`, and none of
  them reads it. The installer still shipped it to every install.
- Scenario 50 said the topic "marks cross-tenant PII leaks as P0". The topic had no such rule. The P0
  lives in the `## Severity rubric` of `wos/bug-classes/multi-tenant-cross-agency-leak.md`. The scenario
  also cited a persona file that does not exist.
- Scenario 51 tested a pre-launch gate and a BLOCK contract that no file defined and no command ran.
  A BLOCK would have made a file that says it is not legal advice act as legal advice.
- The topic and the template carried regulatory claims that age. The 2026-09 documentation audit found
  6 of its 39 defects in the topic, 11 claims were corrected across three commits between 2026-09-20
  and 2026-09-23, and one claim rested on a regulator's waiver that expires on 2027-01-31. The template
  had one commit and was never audited.
- It picked one US industry among many (health, payments, education, finance) with no mechanism that
  chose it, and it named vendor products in its licensure section.

`wos/project-level-memory.md` already names a regulatory constraint as a project fact, captured
through `project-bootstrap` and `capture-references`, which dates each entry.

## Decision

Core `wos/` carries no regulatory topic for a single industry. An industry's regulatory rules are a
project fact: they go in the project charter and in `REFERENCES.md` through `capture-references`, with
their dates.

- The topic, the template and scenario 51 are deleted. Scenario 51's number stays a gap, as scenario
  15's did under ADR-0170.
- Scenario 50 stays. Its P0 is grounded in the P0 row of the bug class's `## Severity rubric`: a route
  reachable by an ordinary authenticated user returns another tenant's rows. Its persona reference
  points at `commands/rls-auth-boundary-auditor/SKILL.md`.
- `wos/project-level-memory.md` says in one sentence that an industry's regulatory rules are a project
  fact of this kind.
- The two bug classes the topic listed as planned, `missing-consent-record` and `retention-class-missing`,
  are dropped deliberately and recorded in `docs/DELETION_LEDGER.md`. Retention classes and purge jobs
  are covered by no bug class today, and that gap is accepted until a review finding asks for one.
- The installer already removes a topic retired from `wos/`. Removing a retired template from an
  install is the installer's own change, made separately.

No engagement is named here (ADR-0164).

## Consequences

### Positive

- Every install stops carrying dated regulatory claims that nothing loads.
- Two scenarios stop asserting contracts no file defines: one is gone, and the other cites the rubric
  that actually sets its severity.
- The maintenance job that produced a sixth of the audit's defects ends.

### Negative

- A project in a regulated industry gets no starting checklist from Fhorja. It writes its own
  constraints into its charter and references.
- Consent records and retention classes have no bug class. A review that meets one flags it through
  `capture-observation` or proposes a template through `pr-feedback-ingest`.

### Neutral

- The public mirror still carries an older copy of the topic until the next release sync.

## Alternatives considered

### Keep the topic and route it from a command

- `invariants-and-non-goals` or `security-review` would load it on a compliance surface.
- Rejected: it makes a permanent regulatory maintenance job for one industry with no owner and no
  review cadence, and it would put regulatory claims into review verdicts. ADR-0148's rejected
  alternative for the overlay topic fits exactly: the topic is vertical-specific in a way no current
  command routes to.

### Move it into a domain pack or under `docs/examples/`

- The file would leave the load path but stay in the tree.
- Rejected: a new concept for one file, and its claims would still be public and still go stale.

### Keep everything as it is

- Rejected: an orphan shipped to every install, and two scenarios asserting contracts that do not exist.

What would reopen this: a command whose contract needs a regulatory floor with an owner and a review
cadence, real outside demand for an industry, or a decision to ship industry packs as a product line.

## References

- `wos/project-level-memory.md`, `### When to write each layer` (the project-fact sentence).
- `evals/scenarios/50-multi-tenant-cross-agency-leak.md` and
  `wos/bug-classes/multi-tenant-cross-agency-leak.md` `## Severity rubric`.
- `docs/DELETION_LEDGER.md` row 16.
- [ADR-0148](./0148-two-triggers-rekeyed-to-their-mechanism.md) D-3, the same batch's first retired topic.
- [ADR-0164](./0164-engagement-provenance-redaction.md), why no engagement is named.
- [ADR-0170](./0170-retire-the-judge-py-eval-layer.md), the accepted scenario-number gap.

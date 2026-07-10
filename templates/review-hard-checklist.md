# review-hard checklist (copy into task folder or use as inline guide)

Use with `@commands/review-hard.md`. Check **yes / no / N/A**; any **no** should become a finding with severity (must-fix / should-fix / optional).

## Correctness and contract

- [ ] Behavior matches `DECISIONS.md` and the active slice / plan (no silent scope expansion).
- [ ] Edge cases called out in the plan or slice are handled or explicitly deferred with rationale.
- [ ] Error paths and failure modes are safe (no data loss, no misleading success).

## Safety and blast radius

- [ ] Authz, tenancy, PII, secrets, or payment-adjacent paths reviewed if touched.
- [ ] Migrations / backfills / deploy order are safe or explicitly gated.
- [ ] Rollback or feature-flag story is credible for the change size.

## Tests and evidence

- [ ] Tests or checks cited in the slice / `TASK_STATE.md` were run (or gap is explicit).
- [ ] Deterministic checks are reproducible (commands and expected signals noted).
- [ ] Flaky or skipped tests are not hiding regressions without documentation.

## Maintainability

- [ ] New complexity is justified; no obvious duplication that violates plan boundaries.
- [ ] Naming and boundaries match surrounding codebase conventions.

## Observability and operations

- [ ] Logging/metrics/errors are sufficient to debug production issues for this change.
- [ ] Performance or capacity impact is negligible or explicitly assessed.

## Scope creep

- [ ] Diff does not include unrelated refactors or drive-by files.
- [ ] Follow-ups are listed as follow-ups, not smuggled into “while we’re here.”

## Output reminder

- Rank issues **must-fix** / **should-fix** / **optional** with pointers to files/lines or tests.
- If solid, say so clearly (no invented problems).

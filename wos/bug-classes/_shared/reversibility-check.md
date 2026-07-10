# Reversibility check prompt

Append this analysis when a bug-class template has `reversibility-check: true` in its frontmatter.

## Prompt

After completing the primary analysis, answer this additional question:

**If this change ships to production and we need to roll back, what specifically breaks?**

Consider:
- Is the change backward-compatible with the prior deployed version?
- Does this change include a schema migration, config change, or data transformation that cannot be undone by simply reverting the code?
- If the change is reverted, do clients or downstream services see errors, stale data, or inconsistent state?
- Is there a deploy-ordering dependency (e.g., migration must run before code, or code must deploy before migration rolls back)?

Rate the rollback risk:
- **LOW**: code revert is sufficient; no data changes, no schema changes, no external-contract changes.
- **MEDIUM**: code revert works but requires a follow-up action (re-run a job, clear a cache, notify downstream).
- **HIGH**: code revert alone is insufficient; data migration, schema rollback, or coordination with external systems is required.

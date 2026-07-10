# Post-deploy verification plan -- Slice 24

Deploy: `e1f2a3b` to production at 2026-06-05T15:00:00Z
On-call: `@bruno`
Deploy window: 15:00 -> 16:00 UTC
SLO observation window: 30 days post-deploy (through 2026-07-05T15:00:00Z)

---

## 1. Per-AC signal mapping

### AC-1: Errors in /onboarding captured in Sentry with `slice=24` tag

- **Primary signal**: Sentry issue search `tag:slice=24 AND url:*/onboarding*` returns >= 1 event after first user traverses the flow post-deploy.
- **Verification cadence**: Manual check at T+15min and T+1h during deploy window. Automated check at T+24h confirming tag is present on at least one ingested event.
- **Source**: Sentry (free tier, 30-day retention).
- **Owner**: `@bruno`.
- **Pass criterion**: At least one event with `slice=24` tag is visible in Sentry within deploy window; tag value matches expected string exactly.

### AC-2: Error rate on /onboarding <= 0.5% over deploy window AND over 30 days post-deploy

- **Primary signal (deploy window, 15:00 -> 16:00 UTC)**: Datadog APM error-rate panel filtered to `resource_name:/onboarding`. Compute `errors / requests` over the hour. Cross-check against Sentry `events / sessions` in the same window.
- **Primary signal (30-day SLO window)**: Datadog APM error-rate query `sum:trace.http.request.errors{resource_name:/onboarding}.as_count() / sum:trace.http.request.hits{resource_name:/onboarding}.as_count()` rolled up over the full 30-day window, evaluated at day 30 (2026-07-05T15:00:00Z).
- **Secondary / corroborating signal**: Sentry error counts tagged `slice=24` for the same window (only available if within 30-day Sentry retention).
- **Source**: Datadog APM (primary, 15-month retention), Sentry (corroborating, 30-day retention).
- **Owner**: `@bruno`.
- **Pass criterion**: Error rate <= 0.5% computed from Datadog APM for both the 1h deploy window AND the 30-day cumulative window. SLO check is anchored on Datadog, not Sentry.

### AC-3: Datadog APM panel shows /onboarding error rate trend correlated with deploy marker

- **Primary signal**: Datadog APM dashboard panel "Onboarding error rate vs deploy marker" rendered with deploy event overlay at 2026-06-05T15:00:00Z. Visual check that error-rate line is annotated with deploy marker and shows trend before/after.
- **Verification cadence**: Confirm panel renders at T+1h, T+24h, T+7d, T+30d.
- **Source**: Datadog APM.
- **Owner**: `@bruno`.
- **Pass criterion**: Deploy marker visible on panel; error-rate series populated for the full observation window with no gaps.

---

## 2. Which AC's signal depends on Sentry retention?

**AC-1** depends entirely on Sentry retention (Sentry is the only source for the tag-presence check; there is no Postgres mirror of Sentry tags and Datadog APM does not carry the `slice=24` Sentry-side tag).

**AC-2** has a *partial* dependency on Sentry retention through its **corroborating** signal. The primary signal for AC-2 is Datadog APM, which has 15-month retention and is safe through day 30. However, if the plan relies on Sentry as the source of truth for error counts (rather than Datadog), AC-2 becomes retention-fragile.

**AC-3** does NOT depend on Sentry retention. Datadog APM at 15-month retention covers the full 30-day SLO window comfortably.

---

## 3. What happens to AC-2's signal at day 31 post-deploy?

If AC-2's primary signal were sourced from Sentry:

- At day 30 (2026-07-05T15:00:00Z), the SLO check fires.
- Sentry free tier retention is 30 days, meaning events from the deploy window (2026-06-05T15:00 -> 16:00 UTC) are **purged on or around 2026-07-05T15:00 UTC** -- *exactly* when the SLO check needs them.
- Any retrospective query for `tag:slice=24` covering the early part of the 30-day window will return **zero results** not because there were no errors, but because the data has been purged. This is a silent false negative: the query succeeds with empty results.
- Worse, if the SLO check is run any time after day 30 (e.g., day 31, day 35), even more of the window is gone, and the cumulative error rate computed from Sentry will be artificially low (numerator decays faster than the denominator since both are purged together, but the *check itself* may rely only on Sentry counts).
- Net effect: SLO verification at day 30 against Sentry is **structurally unreliable**. AC-2 cannot be honestly attested using Sentry alone.

This is the classic retention-boundary trap: the observability window equals the retention window, so the data evaporates at the exact moment it is needed.

---

## 4. Remediation -- handling the retention boundary

The plan must ensure the SLO check at day 30 has durable data. Four mitigations, in order of preference:

### 4a. Anchor AC-2 on Datadog APM, not Sentry (primary fix)

- Make Datadog APM the **authoritative source** for error-rate computation on /onboarding. Datadog's 15-month retention covers the 30-day SLO window with ~14 months of headroom.
- Sentry is demoted to a corroborating / debugging signal (useful for stack traces and grouping, not for rate math).
- This is the cleanest fix and matches how Datadog APM is already used in AC-3.

### 4b. Export Sentry error counts to a durable store on a rolling basis (defense in depth)

- Schedule a daily job (Trigger.dev scheduled task is appropriate here) that queries Sentry for `tag:slice=24` event counts for the previous 24 hours and writes the aggregate (count, window_start, window_end, slice) to a Postgres table `slo_error_snapshots`.
- Run this job daily starting on deploy day through day 30+.
- At day 30, compute the SLO from the Postgres snapshots, which are not subject to Sentry retention.
- This protects AC-1 attestation as well: the snapshot proves the tag was present at ingestion time, even after Sentry purges.

### 4c. Take a fixed verification snapshot at T+24h, T+7d, T+30d (cheap belt-and-suspenders)

- At each checkpoint, the on-call runs a documented query against Datadog APM and Sentry, records the numerator/denominator/rate into the slice's verification log (e.g., a markdown file checked into the repo or a Datadog notebook).
- This freezes the evidence in a place not governed by Sentry retention.
- Acceptable as a manual fallback if 4b is not built; not a substitute for 4a.

### 4d. Upgrade Sentry retention (only if 4a is not viable)

- Paid Sentry tiers extend retention beyond 30 days. Only consider this if Sentry must remain the source of truth for AC-2 (e.g., if Datadog APM does not capture the same error population). For this slice, Datadog APM covers the same endpoint, so 4a is preferred and 4d is not needed.

### Recommended combination for this slice

Apply **4a + 4c**:

- AC-2 primary signal switches to Datadog APM (15-month retention) -- addresses the structural fragility.
- A T+24h, T+7d, T+30d snapshot is recorded into the slice verification log -- provides a tamper-resistant audit trail and a sanity check across both providers.
- 4b (Postgres snapshot pipeline) is captured as a follow-up if Sentry-tag-based attestation becomes load-bearing for future slices; it is overkill for slice 24 alone.

### Updated AC-2 verification cadence

| Checkpoint | When | Source | Recorded where |
|---|---|---|---|
| Deploy window | 2026-06-05T16:00 UTC | Datadog APM + Sentry | Slice verification log |
| T+24h | 2026-06-06T15:00 UTC | Datadog APM | Slice verification log |
| T+7d | 2026-06-12T15:00 UTC | Datadog APM | Slice verification log |
| T+30d (SLO gate) | 2026-07-05T15:00 UTC | Datadog APM (authoritative) | Slice verification log + SLO ledger |

This ensures the day-30 SLO check operates on data that is guaranteed to exist, and the verification trail is preserved independently of Sentry's 30-day purge cycle.

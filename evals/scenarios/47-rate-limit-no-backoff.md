# Eval scenario 47: Rate-limit handling without backoff (CompuLife-style quoting loop)

- **Tags**: bug-class, rate-limit-no-backoff, resilience, external-api, compulife, P1
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates the `rate-limit-no-backoff` bug-class detection on outbound external API integrations modeled on the CompuLife quoting/term-life endpoints. When a third-party API is called from inside a tight loop (per-quote, per-term, per-applicant) without any exponential backoff, jitter, or circuit breaker, a 429 burst will either melt the upstream rate budget or cause the tenant's IP/account to be throttled at the edge. The detector must flag this as P1, and must PASS the same code path once it is wrapped in exponential-backoff + jitter + circuit breaker.

This exercises:

- The `rate-limit-no-backoff` bug-class rule under `wos/bug-classes/rate-limit-no-backoff.md`.
- Severity assignment policy (P1 for unmitigated 429 amplification on external paid APIs).
- Negative-case discipline: the detector must NOT false-positive when a correct backoff + breaker is present.

## Setup

A repo with a `lib/quotes/compulife.ts` (or equivalent) that calls a CompuLife-style quoting endpoint. Two variants live in the diff under review:

- **Variant A (FAIL case)**: `for (const term of terms) { await compulife.getQuote(applicant, term); }` with no retry wrapper, no `Retry-After` handling, no breaker. The HTTP client returns raw `fetch` responses; a 429 throws and is either swallowed or re-thrown into the request handler.
- **Variant B (PASS case)**: same call wrapped in an exponential-backoff helper (base 500 ms, factor 2, max 30 s, full jitter), honoring `Retry-After` when present, behind a circuit breaker (e.g. opossum-style: half-open after cooldown, opens on rolling 5xx/429 error rate).

## Input prompt

```text
Run @commands/review-hard.md on the staged diff under lib/quotes/compulife.ts.
Check against wos/bug-classes/rate-limit-no-backoff.md.
Report findings per variant (A and B) with severity and rationale.
```

## Expected response shape

- Reviewer loads `wos/bug-classes/rate-limit-no-backoff.md` and names the rule explicitly.
- Variant A is flagged as a `rate-limit-no-backoff` hit at **severity P1**, with the rationale enumerating: (a) tight loop over `terms`, (b) no exponential backoff, (c) no jitter, (d) no circuit breaker, (e) no `Retry-After` honoring, (f) external paid API blast radius.
- Variant B is reported as **PASS** for this bug-class, with the reviewer naming the three mitigations observed (backoff + jitter + breaker) and citing the file/line where each lives.
- Output distinguishes the two variants cleanly; no cross-contamination of findings.

## Pass criteria

1. **Bug-class named**: Response cites `wos/bug-classes/rate-limit-no-backoff.md` by path or identifier, not paraphrased.
2. **Variant A flagged P1**: Severity is P1 (not P2 or "info"), with rationale tied to external paid API + tight-loop amplification of 429s.
3. **Three missing mitigations enumerated**: Rationale for Variant A names at minimum (a) no exponential backoff, (b) no jitter, (c) no circuit breaker. `Retry-After` omission is a bonus observation, not a substitute.
4. **Loop context identified**: Reviewer points at the per-term (or per-applicant) loop as the amplifier, not just the bare call site.
5. **Variant B passes cleanly**: No false positive on the backoff-wrapped path; reviewer explicitly states why the mitigations satisfy the rule.
6. **Mitigations located**: For Variant B, reviewer cites the file/line for the backoff helper, the jitter source, and the breaker wrapper (not just "looks fine").
7. **No severity drift**: Reviewer does not downgrade Variant A to P2/P3 on the basis that "the endpoint is sandbox" or "throws are caught upstream"; sandbox status and upstream catches do not change the bug-class severity.

## Failure modes to watch

- **Variant A under-severity**: Reviewer flags the issue at P2/P3 or as "nice to have", missing that unmitigated 429s on a paid external API are a P1 reliability + cost incident.
- **Variant B false positive**: Reviewer flags the wrapped path as still vulnerable because the bare `fetch` is visible inside the helper, ignoring the surrounding backoff + breaker contract.
- **Backoff-only credit**: Reviewer accepts plain exponential backoff (no jitter, no breaker) as sufficient, missing that thundering-herd retries against a 429 cliff still melt the rate budget.
- **Bug-class not cited**: Reviewer describes the symptom ("you should retry") without naming `rate-limit-no-backoff`, breaking the audit trail back to the canonical bug-class catalog.

## Notes

- Severity policy: P1 is reserved for unmitigated 429 amplification on external paid APIs because the blast radius spans cost (per-call billing), availability (account-level throttle), and tenant isolation (one tenant's burst can throttle all tenants sharing an API key).
- Mitigation contract: backoff + jitter + breaker is the canonical triple. Any two without the third is still a finding, downgraded to P2 only if the missing leg is jitter on a single-tenant low-QPS path.
- CompuLife is the reference integration but the rule generalizes to any third-party paid API called per-row inside a loop.

## History

- 2026-06-05: Scenario created to cover `rate-limit-no-backoff` against CompuLife-style quoting/term loops; PASS case added to guard against false positives on correctly wrapped paths.

## References

- `packages/wos-engine/internal/wos/bug-classes/rate-limit-no-backoff.md` (rule under test)
- `packages/wos-engine/internal/commands/review-hard.md` (consumer command)

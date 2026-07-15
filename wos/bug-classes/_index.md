# Bug-class library

This directory contains the curated bug-class templates consumed by the `repo-consistency-sweep` command.

## Conventions

- Each template is a standalone markdown file: `<class-name>.md`
- Files prefixed with `_` (like this one) and the `_shared/` directory are metadata, not templates
- The command scans all `*.md` files in this directory (excluding `_index.md` and `_shared/`) to discover available classes
- YAML frontmatter in each template declares: name, category, default-severity, cwe mappings, file-patterns, and optional perspective/reversibility flags

## Hybrid loading (D-4)

The command loads templates from two sources in order:

1. **Global** (this directory): `wos/bug-classes/*.md`
2. **Project-local** (per-project overrides): `projects/<client>__<project>/bug-classes/*.md` (if that directory exists)

On name collision (same `name:` in frontmatter), the project-local template fully replaces the global one. The command logs a one-line warning when an override is in effect so the user is aware.

Project-local templates are gitignored (they live inside `projects/`, which is not part of the open-source distribution). Use them for domain-specific patterns (e.g., multi-tenant invariants that only apply to certain clients).

## Shared rule fragments

`_shared/` contains reusable prompt fragments that templates reference via marker comments:

- `_shared/perspectives.md`: multi-perspective analysis prompt fragments (security, operator, maintainer, api-consumer)
- `_shared/reversibility-check.md`: canonical rollback-risk prompt
- `_shared/multi-tenant-invariant.md`: common tenant-safety prompt fragments (populated in later slices)

Templates opt in to shared fragments via their frontmatter (`perspectives:`, `reversibility-check: true`).

## Categories

Bug-classes are grouped by category in their YAML frontmatter. Categories currently in use:

- **accessibility**: accessibility invariants (keyboard, focus, ARIA, alt text)
- **agent-prompt-engineering**: subagent prompt quality (length, output-shape adherence, schema discipline). Covers failure modes specific to LLM subagents driven by markdown prompts in the Fhorja surface.
- **config-bug**: misconfigured runtime, build, or environment settings that change behavior without code changes
- **convention-drift**: codebase conventions (naming, structure, idiom) drift from documented or de-facto standards
- **data-integrity**: invariants around data freshness, source-of-truth handling, cache coherence, and import correctness
- **deployment-infra**: deployment topology, container orchestration, resource quotas, autoscaling, infrastructure-as-code drift
- **design-system**: token usage, component reuse, spacing, color
- **infrastructure**: foundational platform concerns (DNS, networking, storage, IAM) that sit beneath application code
- **meta**: cross-cutting workflow and process invariants that govern how other bug-classes are defined, discovered, or enforced
- **migration**: schema migrations, data backfills, and reversibility of structural changes
- **multi-tenant**: tenant isolation invariants, cross-tenant data exposure, row-level security boundary defects
- **observability**: logging, tracing, metrics, structured signals
- **ordering-bug**: race conditions, out-of-order delivery, idempotency violations, and sequencing assumptions
- **performance**: query shape, N+1, unbounded scans, sync blocking IO
- **quality**: test coverage, test quality, flake signal, and code-quality invariants
- **reliability**: uptime, error budgets, failure-mode coverage, graceful shutdown
- **resilience**: retries, timeouts, graceful degradation, async error handling
- **resource**: memory, file handles, connections, and other bounded resources that can be leaked or exhausted
- **security**: injection, secrets, CSRF, XSS, info disclosure, input validation
- **substrate-protocol**: protocol-level invariants between agents, services, or platform substrates (message shape, version negotiation)
- **testing**: test coverage, test quality, flake signal
- **type-safety**: type-system invariants, unsafe casts, any-leakage, and contract drift between typed surfaces

## Registered bug-classes

The table below tracks every template registered in this directory. Each row mirrors the frontmatter of the corresponding `<name>.md` file. Pillars indicate which review pillars the class primarily defends.

| Name | Severity | Category | Pillars | Notes |
| --- | --- | --- | --- | --- |
| workflow-prompt-too-long | P1 | agent-prompt-engineering | observability, correctness | Empirical sweet spot 300-500 words. Prompts >600 words trigger schema-skip climb where subagents start dropping structured-output discipline. |
| schema-skip-on-structured-output | P0 | agent-prompt-engineering | correctness, observability | Subagent emits prose instead of calling StructuredOutput. Causes silent data loss: orchestrator reads no payload, downstream artifacts never persist, and the failure is invisible without explicit schema-call assertions. |
| stale-doc-sync-reference | P2 | meta | correctness, maintainer | CWE-1059 advisory. `scripts/check-doc-sync.sh` detects broken backtick-command refs, ADR-NNNN refs, or `wos/<topic>.md` refs in curated docs so the surface stays aligned with the real command set, ADR ledger, and topic files. |
| pii-encryption-boundary-leak | P0 | security | security, data-integrity | CWE-312. PII crosses an encryption boundary in plaintext (logs, analytics events, queue payloads, cache layers, error traces). Encryption-at-rest alone does not satisfy the invariant: in-flight surfaces must redact or tokenize before serialization. |
| pii-last-4-only-rule-violation | P0 | security | security, data-integrity | CWE-200. Surface exposes more than last-4 digits of sensitive identifiers (SSN, card, account, tax ID) in UI, exports, logs, or API responses. The last-4-only rule must hold at every read site, not just the canonical view. |
| audit-log-missing-append-only | P1 | observability | observability, security, compliance | CWE-778. Audit-log entries are mutable, deletable, or written through a path that bypasses the append-only sink. Breaks regulatory traceability and forensic reconstruction; mitigations include WORM storage, hash-chained entries, or DB-level row immutability. |
| stale-csv-cache-import | P1 | data-integrity | data-integrity, observability | CWE-1023. CSV import pipeline reads a cached snapshot whose freshness signal is missing, ignored, or trusted past its TTL. Downstream consumers act on stale rows; correctness depends on explicit cache invalidation tied to source-of-truth signals. |
| rate-limit-no-backoff | P1 | resilience | resilience, observability | CWE-770. Outbound caller hits a rate-limited dependency without exponential backoff, jitter, or budget. Tight retry loops amplify the failure, exhaust quotas, and can trigger upstream bans; required mitigations include capped retries, jittered backoff, and circuit-breaker state. |
| human-in-the-loop-audit-missing | P1 | observability | observability, compliance, security | CWE-778. Human approval, override, or manual intervention step occurs without an immutable audit record (who, when, what input, what decision, what justification). Breaks compliance posture for any workflow that claims human oversight as a control. |
| gke-autopilot-resource-quota | P1 | deployment-infra | resilience, observability | CWE-770. Workload deployed to GKE Autopilot without explicit CPU/memory requests, limits, or namespace quotas. Autopilot will reject, throttle, or evict pods unpredictably under load; quota drift between staging and production causes silent capacity regressions. |
| multi-tenant-cross-agency-leak | P0 | multi-tenant | security, multi-tenancy | CWE-639. Query, cache key, broadcast channel, or background-job payload omits the tenant (agency) scope, allowing one tenant to observe or mutate another tenant's rows. RLS alone is insufficient when service-role or admin paths bypass the policy. |
| streaming-overlay-latency-leak | P1 | performance | performance, observability | CWE-405. Streaming UI overlay (token-by-token render, progress bar, live transcript) accumulates unbounded DOM nodes, retains stale subscribers, or re-renders on every chunk without throttling. Latency degrades non-linearly with stream length; required mitigations include virtualization, throttled state writes, and subscriber cleanup on unmount. |
| unsafe-parallel-slice-execution | P1 | agent-prompt-engineering | correctness, resilience | CWE-754, CWE-362. Fleet parallel slice execution bypasses a safety gate: a slice's declared `Scope` omits a file it writes (the disjointness check passes on paper while workers race), or the per-wave build + typecheck + test integration gate is skipped so file-disjoint but semantically-coupled slices ship broken. Mitigation: declare every file in `Scope`, treat coupling artifacts (migration, lockfile, codegen, barrel) as shared, never skip the gate (ADR-0041). |
| order-dependent-test-pollution-via-shared-async-state | P1 | testing | correctness, testing | CWE-362, CWE-668. A test passes alone but fails in full-suite or in a different file order because shared async state leaks across test boundaries: a module-scope client or store (QueryClient, Zustand, Apollo) retains cache or in-flight promises, or a retry/poll timer fires after the test that started it ends. Mitigation: fresh client/store per test, retry:false or fake timers, drain pending async before unmount, randomized-order CI gate. |
| skill-context-poisoning | P0 | agent-prompt-engineering | security, correctness | CWE-506, CWE-829. Third-party skill or plugin carries instructions or behavior an artifact-only scan misses: description-field injection, hidden or zero-width Unicode, payloads in test or auxiliary files, or docs-vs-behavior mismatch. Detection contract behind skill-vet; route external skills through capture-references then skill-vet with human approval (ADR-0046). |
| godot-untrusted-resource-deserialization | P0 | security | security, data-integrity | CWE-502. Loading a `.tres`/`.res` or PackedScene from an untrusted or user-writable source (an edited save, user content, a network payload) runs scripts embedded in that file at load time (arbitrary code execution). Godot 2D-mobile cluster (gdscript); capability-scoped so non-Godot sweeps are unchanged. Mitigation: never load resource-format data from untrusted input; use `store_var` with objects off or JSON for player-facing saves; a safe-resource loader for user content (ADR-0069 cluster). |
| godot-monetization-integrity | P0 | security | security, compliance | CWE-602. Client-side entitlement grant on the decompilable GDScript client is forgeable; verify every purchase server-side against the store API, dedupe by token, grant only on PURCHASED. Also flags a Play purchase not acknowledged or consumed within 3 days (auto-refund), a reward paid on ad-show instead of the user_earned_reward callback, a missing Restore Purchases path, and an undisclosed SDK breaking the Play Data Safety form. Godot 2D-mobile cluster (gdscript); capability-scoped (ADR-0069 cluster). |
| supabase-error-in-object-not-thrown | P1 | reliability | reliability, observability | CWE-252, CWE-390. supabase-js returns query/mutation failures in `{ error }` and does NOT throw. `const { data } = await supabase...` (or a discarded write result) silently swallows DB errors: a fallback default is applied to both "no rows" and real failure, and a surrounding try/catch never fires. Mitigation: destructure and check `error` first, branch DB-error apart from empty-result, log with context, and capture write errors on status/heartbeat updates. |
| auth-boundary-test-bypass | P1 | testing | security, testing | CWE-287. A route/integration test harness injects post-auth request state (`req.auth`, `req.user`, decoded claims) directly, bypassing the real authentication middleware's header-parsing and validation entirely. Every test built on that harness gives zero coverage of the actual auth format regardless of pass count; most dangerous on endpoints reachable by an external, un-controlled caller (inbound webhooks, partner API keys) whose real request shape may never match the mocked assumption. P0 when the external caller's real auth format is unconfirmed against live vendor behavior (ADR-0108, tms-webhook-integration dogfood, 2026-07-15: 44 passing tests plus a "live e2e" gave zero real coverage of the vendor's actual auth header, and the endpoint could not authenticate a single real request). |

Other templates (a11y, security, performance, etc.) are auto-discovered from their `<name>.md` files and follow the same frontmatter contract; this table is the canonical place to record cross-cutting metadata (pillars, notes) that does not live in the per-file frontmatter.

## Adding a new template

1. Create `wos/bug-classes/<your-class-name>.md` following the frontmatter and 7-section structure documented in the design doc
2. Run `scripts/lint-commands.sh` to verify no em-dashes or forbidden patterns
3. Add a row to the **Registered bug-classes** table above with severity, category, pillars, and a one-line note
4. If the category is new, add it to the **Categories** list above with a one-line description
5. The command will auto-discover the new template on its next run (no manifest update needed)

## Template shape reference

See `DESIGN_repo_consistency_sweep.md` in the project memory for the full template specification (YAML frontmatter schema, 7 required sections, 2 optional sections).

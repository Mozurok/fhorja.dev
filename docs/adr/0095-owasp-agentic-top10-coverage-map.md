# ADR-0095: OWASP Agentic Top 10 (2026) coverage map

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: security, owasp-agentic, coverage-map, posture, dogfood-driven, currency-adoption, grounded-2026

## Context

Third and final wave of the 2026-07-11 currency adoption (see `projects/bmazurok__my-work-tasks/REFERENCES.md`, 2026-07-11 scan, the OWASP Agentic Top 10 entry). The OWASP GenAI Security Project released the Top 10 for Agentic Applications (ASI01-ASI10) in December 2025 as the threat model for AI agents and MCP servers. The WOS already has a security cluster (`mcp-server-vet`, `skill-vet`, the human-gated trust model, single-writer substrate, the human merge gate, provenance logging), but it had no explicit map of those defenses against the new taxonomy, so coverage and gaps were implicit.

## Decision

Add `docs/security/owasp-agentic-coverage.md`, a reference posture map that assigns each ASI01-ASI10 category a status (Covered, Partial, or Gap) with the responsible WOS mechanism cited. The map's finding: 4 categories Covered (ASI04 supply chain via the vet commands, ASI07 inter-agent via the fleet isolate pattern, ASI09 human trust via PROPOSED-by-default and per-post egress confirmation, ASI10 rogue agents via the autonomous-run guardrails), 5 Partial (ASI01, ASI02, ASI03, ASI05, ASI08), and 1 Gap (ASI06 memory and context poisoning: no explicit poisoning scan of ingested external content before it enters task memory).

By the maintainer's decision this wave is doc-only: it maps and records, it does not edit any command. The gaps are recorded as explicit follow-ups in the doc, chief among them an ingested-content poisoning heuristic for the external-input paths (`capture-references`, the MCP-sourced task-init seed, `pr-feedback-ingest --mcp-pull`), mirroring what `skill-vet` and `mcp-server-vet` already do for skills and servers.

## Consequences

- The WOS's agent-security posture is explicit and auditable against the 2026 taxonomy: its human-first design and provenance substrate cover the trust and supply-chain categories well; the weakest row is content-poisoning of ingested memory (ASI06).
- The two earlier waves feed this map: provenance-preserving compaction (ADR-0093) and the plan-adherence check (ADR-0094) are the mechanisms cited under ASI06 and ASI01 respectively, so the three waves compose into a coherent posture.
- Additive and doc-only: a new reference doc, no command edited, no model names, no contract change. Wiring the map into `security-review` and the vet commands, and building the ASI06 ingest scan, are recorded follow-ups for a later task, not built here.

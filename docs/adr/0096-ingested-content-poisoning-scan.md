# ADR-0096: Ingested-content poisoning scan (ASI06 first pass)

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: security, asi06, ingest-scan, prompt-injection, ascii-smuggling, capture-references, mcp-ingest, dogfood-driven, grounded-2026

## Context

The OWASP Agentic Top 10 coverage map (ADR-0095) marked ASI06 (Memory and Context Poisoning) as the one Gap: the WOS provenance-stamps and ownership-gates every memory write, but nothing scanned externally-ingested content (captured web pages, pasted issue and PR threads, MCP tool results and items) for poisoning before it entered task memory. A crafted issue body or page could seed a misleading or hostile instruction that the provenance chain then records faithfully but never flags.

The 2026 research (captured in `REFERENCES.md`, the 2026-07-11 ASI06 scan) draws a sharp line between two detectable classes. Invisible-Unicode / ASCII-smuggling detection is deterministic and reliable: zero-width characters, the Unicode Tags block (U+E0000-U+E007F, the EchoLeak CVE-2025-32711 vector), and bidi overrides have no legitimate reason to appear in ingested prose, so a normalize-decode-detect pass over the raw input catches them with high confidence. Embedded-instruction detection, by contrast, is an open problem: the low-error approaches (PromptArmor at ICLR 2026, Azure Prompt Shield) use an LLM preprocessor, and pure keyword or regex filters are bypassed by paraphrase. An honest scan must separate these tiers.

## Decision

Add `scripts/ingest-scan.py`, a read-only, dependency-free scanner with two explicitly separated tiers:

- **Deterministic (reliable):** flags invisible and control Unicode used for smuggling (zero-width set, bidi embeds/overrides/isolates, the Tags block). Present means flagged; this closes the invisible-smuggling class.
- **Advisory (incomplete):** flags blatant embedded-instruction phrases ("ignore all previous instructions", "reveal the system prompt", and similar) and credential/exfil patterns (key names, private-key blocks, curl-to-external). This tier is a hint for human review, framed as incomplete because reliable injection detection needs an LLM preprocessor that is out of scope for a dependency-free scan.

The scan prints a report and a `VERDICT` (CLEAN / FLAGGED), writes nothing, exits 0 by default, and exits 1 under `--strict` when a deterministic finding is present (for gating). It is wired into the ingest surfaces: `capture-references` runs it on fetched content before recording a summary, and the shared `mcp-capability-routing` block runs it on the MCP-sourced body before it enters the receiving artifact (an MCP tool result is ingested content and a vector for output-injection), which reaches the task-init seed and `pr-feedback-ingest --mcp-pull`. On a deterministic flag the content is stripped or the source rejected with a note; on an advisory flag the finding is surfaced. The scan never strips silently.

This moves ASI06 from Gap to Partial in the coverage map.

## Consequences

- The invisible-smuggling class (the concrete, high-confidence attack surface, including the EchoLeak technique) is closed deterministically at every external-ingest boundary the WOS has.
- The framing is honest: the advisory tier catches blatant patterns only, and the residual (paraphrased or semantically subtle injection) is a recorded follow-up that would need an LLM-preprocessor pass, not a false claim of full coverage.
- It mirrors the WOS's existing security posture: read-only, advisory, human-gated, like `skill-vet` and `mcp-server-vet`, and it reuses the deterministic-plus-heuristic shape.
- Additive and dependency-free: a new script plus two wiring points (one shared block, one command), no new command, no model names, no contract change.

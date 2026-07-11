# ADR-0097: OWASP coverage-map wiring and MCP tool-description pinning

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: security, owasp-agentic, mcp-server-vet, security-review, tool-pinning, rug-pull, coverage-map, dogfood-driven, grounded-2026

## Context

Two gap-close follow-ups from the OWASP Agentic Top 10 work. First, the coverage map (ADR-0095, `docs/security/owasp-agentic-coverage.md`) was authored doc-only and no command consulted it, so its posture record was an orphan (the exact discoverability failure the flow audit warned about). Second, `mcp-server-vet` (ADR-0070) is a one-time static pre-trust read; the 2026 MCP-security research (captured in `REFERENCES.md`, the 2026-07-11 ASI06 scan, the mcp-scan entry) shows the dominant post-approval attack is the rug pull (CVE-2025-54136): a server silently changes a tool's description or behavior AFTER it was approved. Invariant Labs' mcp-scan defends against this with tool pinning, hashing tool descriptions on first scan and alerting on change. The WOS vet had no equivalent.

## Decision

**(a) Consult the coverage map.** `security-review` Step 3b (the agentic lens) now points at `docs/security/owasp-agentic-coverage.md` so a finding is framed against the WOS's known ASI01-ASI10 posture rather than re-derived, and its ASI06 line references the ingest scan (ADR-0096). The map is now a consulted reference, not an orphan doc.

**(b) Tool-description pinning in mcp-server-vet.** A new Step 5b records a SHA-256 of each tool's description plus input schema at vet time (a pins record the human keeps beside the config). On a re-vet of an already-adopted server, the command compares current descriptions and schemas against the recorded pins and flags any change as a P1 rug-pull finding. A required-output line (6b) carries the pins and any changed-since-pin findings. The command records and compares; it does not enforce. The step also notes that output injection (a tool result carrying new instructions) is a runtime vector the static vet cannot see, routing runtime tool results through `scripts/ingest-scan.py` (ADR-0096).

## Consequences

- The coverage map is wired into the command that consumes it, closing its discoverability gap.
- `mcp-server-vet` gains post-approval rug-pull detection (ASI04 strengthening), complementing its existing pre-trust static read; combined with the ADR-0096 ingest scan for tool-result output-injection, the MCP trust boundary is covered at adoption, re-vet, and runtime.
- Additive and model-agnostic: two command edits, no new command, no auto-enforcement (pinning records and compares; a human decides). The pins format is a simple SHA-256-per-tool record the human keeps; a dedicated pins tool is a possible future follow-up, not built here.

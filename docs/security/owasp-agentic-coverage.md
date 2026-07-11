# WOS coverage of the OWASP Top 10 for Agentic Applications (2026)

Status: reference posture map. Date: 2026-07-11. Grounded in `projects/bmazurok__my-work-tasks/REFERENCES.md` (2026-07-11 scan, the OWASP Agentic Top 10 entry; the taxonomy was released Dec 2025).

This maps the WOS's existing defenses to the ten agentic risk categories (ASI01-ASI10). Each row is marked **Covered**, **Partial**, or **Gap**, with the WOS mechanism cited. This is a posture map, not a guarantee: it records where the workflow's design already resists a category and where a follow-up is warranted. It does not change any command; the gaps are recorded as follow-ups at the end.

## The map

### ASI01 Agent Goal Hijack -- Partial
The agent's goal is human-anchored, not self-set: `decision-interview` locks decisions in `DECISIONS.md` (EARS), `implementation-plan` plus `approve-plan` gate the plan before execution, and PROPOSED-by-default (ADR-0001) keeps the human in the loop. The plan-adherence check (ADR-0094) now catches execution that drifts off the approved plan, which is one hijack signature. Residual: a mid-run instruction injected via tool output is not specifically detected as goal-hijack beyond the plan-adherence and human-merge gates.

### ASI02 Tool Misuse and Exploitation -- Partial
`mcp-server-vet` (ADR-0070) inspects a tool surface before trust; the `metadata.tools` read-only guard and tiered install profiles (ADR-0059) bound what a command may touch; capability routing (ADR-0082) never names a vendor tool in normative text. Residual: no runtime monitoring of tool calls (vet is static, pre-trust).

### ASI03 Agent Identity and Privilege Abuse -- Partial
The substrate ownership model (single-writer per section, ADR-0040; `owned_sections` in persona frontmatter; the maturity ladder for privilege promotion, ADR-0036) means a command writes only its owned sections, and a REFUSE event is logged on a cross-owner write. Residual: this is a workflow-integrity boundary, not an OS-level privilege boundary.

### ASI04 Agentic Supply Chain Compromise -- Covered
`skill-vet` and `mcp-server-vet` are read-only pre-trust inspections of third-party skills and MCP servers, with no auto-install and human-gated trust (ADR-0046). Both scan for tool-description poisoning, over-broad scopes, egress and credential access, and hidden Unicode. This is a WOS strength and directly targets the fastest-moving 2026 category (poisoned MCP tool metadata).

### ASI05 Unexpected Code Execution -- Partial
The WOS itself executes no untrusted code (it is markdown plus bash plus a small Python helper); `skill-vet` flags shell-execution and code-modification in candidate skills; the `git add -A` block hook prevents a broad accidental stage. Residual: a consuming product repo's own execution surface is out of the WOS's scope.

### ASI06 Memory and Context Poisoning -- Partial
Substrate writes are provenance-stamped and ownership-gated: every write carries a `wos:write` header and a `.wos/VERIFICATION_LOG.jsonl` line (owner, run_id, sha), the log is append-only and never rewritten (ADR-0093), and `state-reconcile` plus plan-adherence detect drift. MCP-sourced input is treated as external and never overrides locked decisions (ADR-0082). Ingested external content is now scanned before it enters task memory: `scripts/ingest-scan.py` (ADR-0096), wired into `capture-references` and the MCP ingest paths, deterministically flags invisible and control Unicode (zero-width, the Tags block, bidi overrides, the ASCII-smuggling vector behind EchoLeak) and advisorily flags blatant embedded-instruction and credential patterns. Residual: the advisory tier is incomplete because reliable prompt-injection detection is an open problem (the low-error approaches use an LLM preprocessor, out of scope for a dependency-free scan), so a paraphrased or semantically subtle injection can still pass. The deterministic tier, however, closes the invisible-smuggling class.

### ASI07 Insecure Inter-Agent Communication -- Covered
Fleet workers never talk to each other and never write substrate directly; each returns a typed `StructuredOutput` payload from an isolated context (ADR-0038), and the orchestrator is the sole merger. There is no free-prose inter-agent channel to inject into. This is the isolate operation (ADR-0093) doubling as a security boundary.

### ASI08 Cascading Agent Failures -- Partial (covered)
Fleet execution is gated: parallelizable waves require pairwise-disjoint file scopes (ADR-0041), a build-plus-typecheck-plus-test integration gate runs after each wave, and `autonomous-run` has a governor (max-iteration, wall-clock, identical-command loop) with stall-to-escalation and an absolute STOP sentinel (ADR-0081). Residual: a semantic cascade (each worker individually valid, jointly wrong) is caught only at the integration gate, not preemptively.

### ASI09 Human-Agent Trust Exploitation -- Covered
PROPOSED-by-default (ADR-0001) means the human reviews before anything persists; egress to a messaging or knowledge-base MCP requires a per-post same-turn confirmation showing the exact payload and destination, with no remembered consent (ADR-0082); the human merge gate is never removed.

### ASI10 Rogue Agents -- Covered
`autonomous-run` never auto-merges, runs allowlist-only with no permissive flag accepted (ADR-0044 D9), honors an absolute main-repo STOP sentinel, and a human always performs the merge. A detached background run is still one supervised session (ADR-0081).

## Summary

- Covered (4): ASI04 supply chain, ASI07 inter-agent, ASI09 human trust, ASI10 rogue agents.
- Partial (6): ASI01 goal hijack, ASI02 tool misuse, ASI03 identity, ASI05 code execution, ASI06 memory poisoning (first-pass ingest scan, deterministic tier reliable, heuristic tier advisory), ASI08 cascading failures.
- Gap (0).

The WOS's human-first design (approval gates, PROPOSED-by-default, human merge) and its provenance substrate cover the trust and supply-chain categories well. The isolate pattern covers inter-agent risk. ASI06 was the one Gap and is now Partial: the ingest scan (ADR-0096) closes the invisible-smuggling class deterministically; the residual is the open problem of paraphrased injection.

## Update history

- 2026-07-11 (ADR-0096): ASI06 moved Gap -> Partial with `scripts/ingest-scan.py` wired into `capture-references` and the MCP ingest paths.

## Recorded follow-ups

1. **ASI06 residual:** the advisory heuristic tier catches only blatant embedded-instruction and credential patterns. A stronger check would need an LLM-preprocessor pass (PromptArmor-style); out of scope for a dependency-free scan, revisit if a real injection slips past the deterministic tier.
2. **ASI01 / ASI08 detection depth:** consider a goal-drift signal beyond plan-adherence, and a preemptive semantic-cascade check in fleet waves, if a real dogfood surfaces the need. Lower priority; do not build speculatively.

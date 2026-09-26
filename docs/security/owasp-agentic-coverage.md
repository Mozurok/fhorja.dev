# Fhorja coverage of the OWASP Top 10 for Agentic Applications (2026)

Status: reference posture map. Date: 2026-07-11, revised 2026-09-23. Grounded in the OWASP Top 10 for Agentic Applications, released 2025-12-09 (https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/). The maintainer keeps the capture notes for that source in a local, gitignored reference file.

This maps Fhorja's existing defenses to the ten agentic risk categories (ASI01-ASI10). Each row is marked **Covered**, **Partial**, or **Gap**, with the Fhorja mechanism cited. This is a posture map, not a guarantee: it records where the workflow's design already resists a category and where a follow-up is warranted. It does not change any command; the gaps are recorded as follow-ups at the end.

## The map

### ASI01 Agent Goal Hijack: Partial
The agent's goal is anchored in decisions a person made, not in goals the agent sets: `decision-interview` locks decisions in `DECISIONS.md` (EARS), and every plan goes through `approve-plan`, whose blinded review asks one question in a context that never saw the conversation that wrote the plan: does this plan commit the product to anything the locked decisions do not authorize (ADR-0208). A plan that drifted off those decisions escalates to a person instead of running. The plan-adherence check (ADR-0094) catches execution that drifts off the approved plan, which is another hijack signature. What the human no longer does is review each write: task memory is written `APPLIED` in every mode (ADR-0199, ADR-0215), so a hijacked run can change task memory without a person seeing it first. Residual: a mid-run instruction injected via tool output is not specifically detected as goal hijack beyond the blinded plan review, the plan-adherence check and the human merge.

### ASI02 Tool Misuse and Exploitation: Partial
`mcp-server-vet` (ADR-0070) inspects a tool surface before trust; the `metadata.tools` read-only guard and tiered install profiles (ADR-0059) bound what a command may touch; capability routing (ADR-0082) never names a vendor tool in normative text. Residual: no runtime monitoring of tool calls (vet is static, pre-trust).

### ASI03 Agent Identity and Privilege Abuse: Partial
The substrate ownership model (one owner per section, ADR-0034 and `wos/substrate-peers.md`; `owned_sections` in persona frontmatter; the maturity ladder for privilege promotion, ADR-0036) means a command writes only its owned sections, and a REFUSE event is logged on a cross-owner write. Residual: this is a workflow-integrity boundary, not an OS-level privilege boundary.

### ASI04 Agentic Supply Chain Compromise: Covered
`skill-vet` and `mcp-server-vet` are read-only pre-trust inspections of third-party skills and MCP servers, with no auto-install and human-gated trust (ADR-0046). Both scan for tool-description poisoning, over-broad scopes, egress and credential access, and hidden Unicode. This is a Fhorja strength and directly targets the fastest-moving 2026 category (poisoned MCP tool metadata).

### ASI05 Unexpected Code Execution: Partial
Fhorja itself executes no untrusted code (it is markdown plus bash plus a small Python helper); `skill-vet` flags shell-execution and code-modification in candidate skills; the `git add -A` block hook prevents a broad accidental stage. Residual: a consuming product repo's own execution surface is out of Fhorja's scope.

### ASI06 Memory and Context Poisoning: Partial
Substrate writes are provenance-stamped and ownership-gated: every write carries a `wos:write` header and a `.wos/VERIFICATION_LOG.jsonl` line (owner, run_id, sha), the log is append-only and never rewritten (ADR-0093), and `state-reconcile` plus plan-adherence detect drift. MCP-sourced input is treated as external and never overrides locked decisions (ADR-0082). Ingested external content is now scanned before it enters task memory: `scripts/ingest-scan.py` (ADR-0096), wired into `capture-references` and the MCP ingest paths, deterministically flags invisible and control Unicode (zero-width, the Tags block, bidi overrides, the ASCII-smuggling vector behind EchoLeak) and advisorily flags blatant embedded-instruction and credential patterns. Residual: the advisory tier is incomplete because reliable prompt-injection detection is an open problem (the low-error approaches use an LLM preprocessor, out of scope for a dependency-free scan), so a paraphrased or semantically subtle injection can still pass. The deterministic tier, however, closes the invisible-smuggling class.

### ASI07 Insecure Inter-Agent Communication: Covered
Fleet workers never talk to each other. Each returns a typed payload matching its `worker_output_schema` from an isolated context, through the runtime's `StructuredOutput` call on the dynamic-workflow path or through its assigned return file under `fleet-inbox/<run_id>/` on the `Agent` path (ADR-0158), and the orchestrator is the sole merger. There is no free-prose inter-agent channel to inject into. This is the isolate operation (ADR-0093) doubling as a security boundary. Residual: that a worker writes nothing outside its return file rests on its instructions, since a background sub-agent keeps `Edit` and `Write` (ADR-0158 D-2).

### ASI08 Cascading Agent Failures: Partial (covered)
Fleet execution is gated: parallelizable waves require pairwise-disjoint file scopes (ADR-0041), a build-plus-typecheck-plus-test integration gate runs after each wave, and `autonomous-run` has a governor (max-iteration, wall-clock, identical-command loop) with stall-to-escalation and a STOP sentinel at an absolute main-repo path, watched by a supervisor independent of agent progress (ADR-0081, ADR-0196, ADR-0197). Residual: a semantic cascade (each worker individually valid, jointly wrong) is caught only at the integration gate, not preemptively.

### ASI09 Human-Agent Trust Exploitation: Partial
The person is asked less often, and what they are shown is harder to dress up. Any act whose audience is not bounded (marking a draft pull request ready, egress to a messaging or knowledge-base MCP, publishing) requires an explicit confirmation in the same turn, after the raw payload and the exact destination are displayed rather than the agent's own summary of them, with no standing approval and no consent carried across turns (ADR-0200, ADR-0082). Plan approval rests on a blinded review rather than on a person reading the agent's framing of its own plan (ADR-0208). The merge stays human on both tracks; on the unattended track the PROPOSED diffs go to `review-hard` first (ADR-0221). Residual: a person no longer reviews what persists in task memory (ADR-0199, ADR-0215), a plan reaches a person only when its review escalates, and the merge decision still leans on a person reading a diff the agent produced.

### ASI10 Rogue Agents: Covered
`autonomous-run` never commits, merges or deploys; it emits PROPOSED diffs, routes them to `review-hard`, and a human performs the merge (ADR-0197, ADR-0221). It runs allowlist-only with no permissive flag accepted (ADR-0044 D9) and honors a STOP sentinel at an absolute main-repo path. That sentinel is host-enforced only when the host places it outside the agent's writable scope; otherwise the run reports cooperative-only control (ADR-0197). A detached background run is still one supervised session (ADR-0081, ADR-0196).

## Summary

- Covered (3): ASI04 supply chain, ASI07 inter-agent, ASI10 rogue agents.
- Partial (7): ASI01 goal hijack, ASI02 tool misuse, ASI03 identity, ASI05 code execution, ASI06 memory poisoning (first-pass ingest scan, deterministic tier reliable, heuristic tier advisory), ASI08 cascading failures, ASI09 human trust.
- Gap (0).

Fhorja's gates (the human merge, same-turn confirmation for any act whose audience is not bounded, the blinded plan review) and its provenance substrate cover the supply-chain category well. The isolate pattern covers inter-agent risk. ASI09 moved from Covered to Partial when task memory stopped waiting for a person (ADR-0199) and plan approval stopped requiring one (ADR-0208): the controls that remain are narrower and aimed at the acts that reach other people. ASI06 was the one Gap and is now Partial: the ingest scan (ADR-0096) closes the invisible-smuggling class deterministically; the residual is the open problem of paraphrased injection.

## Update history

- 2026-07-11 (ADR-0096): ASI06 moved Gap -> Partial with `scripts/ingest-scan.py` wired into `capture-references` and the MCP ingest paths.
- 2026-09-23: ASI09 moved Covered -> Partial and ASI01 was restated on current controls. ADR-0199 and ADR-0215 retired the write gate this map had relied on ("the human reviews before anything persists"), and ADR-0208 made plan approval a blinded review that reaches a person only on ESCALATED; ADR-0200's same-turn confirmation and the human merge are what remain. Also corrected: ASI07 cites the ADR-0158 return transport, ASI03 cites ADR-0034 for section ownership (ADR-0040 is the per-folder exception for `task-init-fleet`), and ASI08 and ASI10 cite ADR-0196 and ADR-0197 for the background run and the STOP sentinel.

## Recorded follow-ups

1. **ASI06 residual:** the advisory heuristic tier catches only blatant embedded-instruction and credential patterns. A stronger check would need an LLM-preprocessor pass (PromptArmor-style); out of scope for a dependency-free scan, revisit if a real injection slips past the deterministic tier.
2. **ASI01 / ASI08 detection depth:** consider a goal-drift signal beyond plan-adherence, and a preemptive semantic-cascade check in fleet waves, if a real dogfood surfaces the need. Lower priority; do not build speculatively.

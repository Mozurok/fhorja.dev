# ADR-0070: mcp-server-vet, a read-only pre-trust inspection command for third-party MCP servers

- **Status**: Accepted
- **Date**: 2026-06-30
- **Tags**: security, mcp, supply-chain, human-in-the-loop, skill-vet-sibling, read-only, ecosystem-adoption, additive

## Context

The 2026-06-30 six-front ecosystem triage (archived task `wos-ecosystem-fronts-triage`, front 5 security, decision D-2) found that the agent-security story in 2026 is first a supply-chain problem and only second a prompt-injection problem, with MCP as the connective tissue of the incidents (the ClawHavoc compromised-package wave, the Git MCP RCE-via-prompt-injection chain). The structural gap: SAST reads code syntax and SCA checks dependency versions, but neither reads the semantic layer where MCP tool descriptions, scopes, and names operate, so a poisoned tool description or an over-broad scope escapes the SBOM.

The WOS already vets one half of this surface. `skill-vet` (ADR-0046) does a read-only, human-gated inspection of a third-party agent skill directory before it is installed. But MCP server configs, which the triage identified as the primary 2026 incident vector, had no equivalent vetting command. The triage's other five fronts were already covered (coding agents by the tool-agnostic charter, observability by scope, diagrams by ADR-0047, spec-driven by ADR-0061) or were product-side; front 5 was the one front with a real, uncovered WOS gap, and the WOS already had the exact pattern (read-only, never-auto-trust, human verdict) to extend.

## Decision

Add a net-new command `mcp-server-vet`, modeled on `skill-vet`, that performs a read-only, pre-trust inspection of a third-party MCP server and returns an ADD / SANDBOX / DECLINE verdict for a human to approve. It never installs, never adds to a config, never starts a server, and never auto-trusts.

The command mirrors `skill-vet`'s six-step contract, adapted from skill files to a server's declared surface:

1. Enumerate the declared surface: the config entry (command, args, env, transport) and every advertised tool (name, description, input schema, declared scope).
2. Declared vs actual: does the advertised tool set match the stated purpose; flag capability or scope beyond the stated purpose.
3. Danger-pattern scan: tool-description poisoning and agent-directed instructions (the primary MCP attack), outbound/exfiltration surface, secret and credential access, out-of-remit or agent-config writes, shell execution, over-broad scopes.
4. Hidden-content scan: hidden or zero-width Unicode and instruction smuggling in tool names, descriptions, and schemas.
5. Supply chain: package or binary provenance, version pinning, install hooks, the env and secret surface.
6. Verdict ADD / SANDBOX / DECLINE with P0/P1/P2 findings, plus a creator-tier and a PROPOSED `provenance:` value on ADD, exactly as `skill-vet` does.

Scope is a static, pre-trust inspection of the declared surface the user supplies on disk (the config entry and, when provided, a tool list the user already captured from the server). The command never connects to, queries, starts, or calls the candidate server itself; if the only available source is a live server, the user captures its tool list out of band and points the command at that copy. Runtime egress monitoring (the domain of external tools like Pipelock or the Cisco scanner) is explicitly out of scope and stays with those tools, not the WOS, per the triage.

Frontmatter, category (`execution-and-closure`), Ask mode, and the read-only-toward-the-target posture mirror `skill-vet`. The command is registered in all four registries, carries an eval scenario, and ships with the generated skill, moving the command count from 89 to 90.

## Consequences

- The MCP-config half of the third-party trust surface now has the same human-gated, read-only vetting that `skill-vet` gives skills, closing the one real gap the six-front triage surfaced.
- No new dependency and no runtime component: the command reads a declared surface and writes a report, exactly like `skill-vet`. It frames its output as inspection that surfaces signals, never a guarantee of prevention (OWASP states there is no fool-proof prevention).
- This ADR is additive. It does not supersede `skill-vet` (skills) or `security-review` (first-party code); it adds the sibling that covers MCP servers. The OWASP Agentic Top 10 (ASI01) fold into `skill-vet` and `security-review`, also surfaced by the triage front-5 adapt, is tracked separately and is not part of this ADR.
- The command count moves to 90, with the 4-registry registration, the count-marker bumps (commands, adrs, scenarios), the eval scenario, and the generated skill landing together so lint stays green.

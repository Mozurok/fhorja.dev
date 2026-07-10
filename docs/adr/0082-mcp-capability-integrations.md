# ADR-0082: Capability-routed MCP ingest and egress behind the vet gate and per-post confirmation

- **Status**: Accepted
- **Date**: 2026-07-06
- **Tags**: mcp, capability-routing, ingest, egress, shared-block, trust-gate, per-post-confirmation, additive

## Context

The market-parity initiative's deliverables 1 and 2 asked for MCP integration paths: seeding work from an issue tracker, pulling PR feedback, posting updates to a messaging surface, and publishing assets to a knowledge base. The WOS already had the trust half of the story: human-gated `.mcp.json` config (ADR-0046, Pattern 4 of `wos/external-integration-patterns.md`) and `mcp-server-vet` as a read-only pre-trust inspection (ADR-0070), plus a shape precedent for gated input modes (`--playtest`, ADR-0069). What it lacked was any command-level convention for consuming or writing through a connected server, and the topic's routing questions predated Pattern 4 and never routed to it.

Two properties were non-negotiable from the initiative brief: no vendor server names in normative text (capability routing only), and no egress write without a real human checkpoint. team-update and delivery-asset had a zero side-effect surface before this change; adding egress changes their contract, which is where the safety weight sits.

## Decision

Gated, opt-in, capability-routed MCP paths on four existing commands, all consuming one shared block, locked as D-1..D-4 of task `2026-07-03_mcp-integrations`:

1. **One shared block (D-1).** `commands/_shared/mcp-capability-routing.md` holds the five-rule contract (trust gate, capability routing, failure policy, ingest mapping, egress confirmation), propagated into `task-init`, `pr-feedback-ingest`, `team-update`, and `delivery-asset` via the shared-block marker and `sync-shared-blocks.sh`. The normative rule lives once; commands add only surface-specific lines.
2. **Generic-minimal ingest schema (D-2).** Exactly four capability-routed fields: title, body, identifier, URL. Title and body feed the task description or feedback payload; identifier and URL become a provenance pointer (`source: mcp`, the server as locally named, the item URL). MCP-sourced text never overrides locked decisions or widens scope; the receiving command's corrective-only and ledger rules apply unchanged. task-init gains a gated seed source in its bootstrap chain; pr-feedback-ingest gains `--mcp-pull`, a source-swap mode mirroring `--playtest` exactly (same matrix, same corrective-only scope, off by default).
3. **Visible fallback, never fabrication (D-3).** An unreachable or malformed MCP is stated explicitly and the command continues on its manual path; no silent repair, no hard fail. With no MCP connected, every command behaves exactly as before.
4. **Per-post egress confirmation (D-4).** Sending to a messaging or knowledge-base MCP requires an explicit confirmation in that turn, after the exact payload and destination (server as locally named plus channel, page, or space) are displayed. One post, one confirmation: no session-level approval, no remembered consent, no batching. Failure leaves the produced text or asset paste-ready; the artifact remains the primary output either way.

The trust gate is unchanged from ADR-0046/0070 and has no bypass: declared in the project-scoped config, human-approved, and vetted via `mcp-server-vet`; a server missing any of the three is treated as not connected. Pattern 4 in the topic now documents the full ingest and egress conventions, and the routing questions gained the missing fourth entry routing MCP-shaped integrations to it.

## Consequences

### Positive

- The four highest-value integration surfaces work through any tracker, review, messaging, or knowledge-base server the user connects, with zero vendor coupling in the WOS itself.
- The egress safety posture is explicit and testable: the per-post contract is grep-assertable and the eval scenario asserts it.
- No new command, no registry rows; the whole delivery is additive and off by default.

### Negative

- Per-post confirmation adds friction to multi-post sequences by design; batching convenience was explicitly rejected as the init-flagged failure mode.
- The shared block carries both ingest and egress rules into all four commands, so each command's expanded text includes a few lines it does not use (the accepted D-1 cost).
- The four-field ingest mapping ignores richer tracker data (status, assignees, labels) in v1.

### Neutral

- Live behavioral validation against a real connected server is deliberately post-merge dogfood; the repo ships the contract and its regression scenario, not a test server.
- Richer field mappings and more surfaces (for example capture-references ingest) are additive follow-ups if wanted.

## Alternatives considered

### Alternative 1: a dedicated command pair (mcp-ingest, mcp-egress)

- Centralizes the logic in new commands.
- Rejected: adds two commands and eight registry rows while duplicating the roles of four existing commands; the gated-mode precedent (ADR-0069) fits the existing surfaces exactly.

### Alternative 2: doctrine-only (topic text, no command modes)

- Cheapest.
- Rejected: does not deliver "task-init seedable" or "pr-feedback-ingest able to pull" as named; it would have narrowed deliverable 1 and required an explicit de-scope.

### Alternative 3: session-level egress approval

- Less friction across sequences.
- Rejected: it is exactly the under-specified checkpoint gap the task's init flagged as the top risk; a post firing without a same-turn human yes is the failure mode this ADR exists to prevent.

## References

- `commands/_shared/mcp-capability-routing.md` (the five-rule contract).
- `commands/task-init.md` (gated seed source), `commands/pr-feedback-ingest.md` (`--mcp-pull`), `commands/team-update.md` and `commands/delivery-asset.md` (egress with per-post confirmation), `wos/external-integration-patterns.md` (Pattern 4 extension and the fourth routing question).
- D-1..D-4 of `projects/bmazurok__my-work-tasks/active/2026-07-03_mcp-integrations/DECISIONS.md` (locked 2026-07-06).
- ADR-0046 (human-gated MCP config), ADR-0070 (mcp-server-vet), ADR-0069 (the gated source-swap mode precedent), ADR-0056 (deliverables ledger).
- `evals/scenarios/93-mcp-capability-integrations.md` (the regression scenario).

## Notes

Fourth and final delivery of the 2026-07-03 market-parity initiative. Executed as one sequential slice (the shared block) plus a width-5 fleet wave (the four command surfaces and the topic) plus this housekeeping slice; the egress workers ran under STOP conditions against batching and remembered-consent wording, and none tripped.

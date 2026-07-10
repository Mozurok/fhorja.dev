# ADR-0034: Substrate peers + worker contract (Epic J/K foundation)

- **Status**: Accepted
- **Date**: 2026-06-04
- **Tags**: multi-agent, substrate, worker-contract, ownership, audit-trail, joint-j1-k1
- **Promotes**: ADR-0022 (Sub-agent orchestration) from documentary to enforceable

## Context

Three forces drove this decision now:

1. **Epic J (multi-agent orchestration foundation, researched 2026-06-04)** needs a canonical worker contract before any orchestrator command can dispatch sub-agents safely. Without a contract, each `*-fleet` command would reinvent input/output/status shapes and merging would be ad-hoc. The Epic J research identified five concrete primitives missing in the WOS today: worker contract (J.1), orchestrator shape (J.2), tier-aware dispatch (J.3), convergence (J.4), provenance log (J.5).

2. **Epic K v2.1 (full product lifecycle OS, researched 2026-06-04 across three rounds)** chose persona+command coexistence on a shared substrate (peers, not layers). Without a section ownership model, two writers (one command, one persona; or two commands; or a command and a fleet worker partial) can stomp silently on the same `## section` in `TASK_STATE.md` and the only audit trail is `git diff` after the fact. This is the silent-overwrite class that the WOS until v0.2.x tolerated because there was no agent layer; once agents land, tolerating it produces non-reproducible state.

3. **ADR-0022 (Sub-agent orchestration, 2026-04-22) was documentary only.** It described the orchestrator-workers pattern, four-question checklist, and per-tool primitives table, but had no enforcement hook in any command file or lint rule. It served as a thinking aid; it did not constrain behavior. The Epic J research explicitly closed that with `"a stronger signal of real use-case friction"` — the friction arrived: Bruno is full-stack multi-repo (Q1 2026-06-03), runs 100% Opus for sequential single-agent work (B.4 baseline 2026-06-03 = 86% Opus over 469 sessions), and the planned `*-fleet` commands (J.6 atom-audit-fleet, J.7 screen-spec-fleet) cannot ship without an enforced contract.

The 2026-06-04 three-round research (Epic K v1 → v2 → v2.1) converged on a single architectural shape consistent across nine AAA references (Microsoft Agent Framework Workflows GA Nov 2025; Anthropic Skills open standard 2025-12-18; VS Code Chat Participants; GitHub Copilot agents; Stripe Workbench; Vercel AI SDK 6; Cognition Devin Managed Devins; LangGraph state machines; HashiCorp Terraform agents). All nine treat agents as peers sharing typed state, never as a layer above commands.

This ADR is the joint J.1 + K.1 foundation. It must merge before any Epic J `*-fleet` slice can ship and before any Epic K persona slice can ship.

## Decision

Adopt two normative primitives together:

**A) Substrate-peer architecture.** Commands, personas (SKILL.md files), and Epic J fleet workers are peers sharing four canonical substrate files: `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`. Every `## section` (H2) inside each substrate file has exactly one OWNER (writes via Edit/Write) plus an explicit set of CO-WRITERS (propose-only via PROPOSED blocks inside the section). Readers are unrestricted. The full section ownership matrix lives in `wos/substrate-peers.md`. Conflict resolution rule: REFUSE plus emit a `### Handoff` routing the writer to the owner. Same-owner repeat write in one run: no-op-if-identical (SHA-256 of section bytes), otherwise new transaction header replaces prior and prior is logged with `event=overwrite`.

**B) Worker contract.** Every worker dispatched by an orchestrator (Claude Code Task tool, Cursor agent subagent, Codex agents, Anthropic Dynamic Workflows spawn) MUST conform to the canonical input/output/error/partial shape defined in `commands/_shared/worker-contract.md`. The status taxonomy is verbatim from Anthropic Outcomes API (released 2026-05-06): `satisfied | needs_revision | max_iterations_reached | failed | interrupted`. Workers NEVER write directly to substrate; they emit one partial-result file at `active/<task>/.wos/fleet-inbox/<run_id>/<worker_id>.partial.md`. The orchestrator is the SOLE merger and the SOLE writer of substrate based on worker partials, following its declared `merge_strategy` (`union` / `last-by-timestamp` / `consensus-of-N` / `manual-review`).

Audit trail: every section write (by command, persona, or orchestrator-merger) appends one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` (gitignored). Schema is defined in `wos/substrate-peers.md` § Audit trail. Shadow mode at launch (writers emit, no reader enforce); validator lands in K.5/J.5.

Enforcement mechanism (canonical-block + lint pattern from ADR-0011 + ADR-0029):

- `wos/substrate-peers.md` (new lazy-loaded topic, activation `model_decision`) is the section ownership matrix + contracts + conflict rules + audit schema.
- `commands/_shared/worker-contract.md` (new shared block) is the canonical worker input/output/status shape. Orchestrator command files declare the marker `<!-- shared:worker-contract -->` and `sync-shared-blocks.sh` propagates the body inline.
- `WORKFLOW_OPERATING_SYSTEM.md ## Cross-cutting workflow guardrails` gains a 4-line stub pointing to `wos/substrate-peers.md` and `commands/_shared/worker-contract.md`.
- Drift-guard candidate (deferred to K.4): scan `active/*/TASK_STATE.md` for sections written without transaction headers AFTER K.2 retrofit cutover date; surface in `repo-consistency-sweep` (non-blocking).

## Consequences

### Positive

- Epic J orchestrators (J.2 onward) have a typed contract to write against. `*-fleet` commands stop reinventing shape; merging becomes deterministic.
- Section ownership is explicit. Future readers of a substrate file can answer "who wrote `## Current phase`?" mechanically by checking the matrix and the transaction header, not by `git blame` archaeology.
- Personas (Epic K v2.1 K.3-K.8) get a clear path: propose-only at L1, gated promotion to section ownership at L3+, fully equivalent to commands at L4. The maturity ladder (§5.5 in v2.1 doc) hooks here.
- Silent last-write-wins on `TASK_STATE.md` sections becomes an explicit REFUSE + routing Handoff. The class of bugs where "I wrote `## Current phase` and 30 minutes later it was wrong and nobody knew why" disappears.
- Audit trail (`VERIFICATION_LOG.jsonl`) gives us provenance per write, reusable across Epic J fleet merges and Epic K persona writes. No parallel log surface.
- ADR-0022 finally has teeth: the orchestrator-workers pattern is enforced via the worker contract block and the substrate matrix, not merely documented.

### Negative

- One new lazy-loaded WOS topic (`wos/substrate-peers.md`, est. ~3.5k tokens). Bootstrap cost rises ~+150 tokens for the stub in `WORKFLOW_OPERATING_SYSTEM.md ## Cross-cutting workflow guardrails`. Acceptable per the context budget policy (ADR-0012) because most tasks don't trigger the load (the topic is `model_decision` activation, fires only on substrate writes / fleet dispatch / drift surfacing).
- Two existing commands narrow their edit scope inside `IMPLEMENTATION_PLAN.md ### Slice N`: `implement-approved-slice` and `slice-closure` may now only mutate `Status:` and `Evidence:` lines (plus `Micro-deltas:` for `implement-slice-complement`). The slice body itself is owned by `implementation-plan`. K.2 will retrofit this inline check.
- Eight most-frequent writers (`sync-task-state`, `slice-closure`, `decision-interview`, `implementation-plan`, `task-init`, `impact-analysis`, `what-next`, `capture-observation`) need transaction-header emission patched in K.2. Estimated patch: ~15-25 lines per file. Other 49 commands gain header emission incrementally when next touched (no big-bang migration).
- Shadow-mode audit log means writers emit log lines without reader enforcement until K.5 / J.5 lands. There is a ~4-6 week window where the log can drift from spec if not periodically validated by hand. Mitigation: K.7 eval discipline lands before K.8 promotes any persona to non-shadow.

### Neutral

- Existing `TASK_STATE.md` files without transaction headers remain valid. The first mutating write under v2.1 emits a header only for that section; other sections stay header-less until next touched. Drift-guard does NOT flag header-less sections as errors — only ownership-rule violations.
- The `DECISIONS.md` append-only D-N ledger discipline is formalized (no edit of locked D-N text; supersedes protocol via `D-(N+M)` + `Supersedes: D-N` tag). This matches what `task-file-contracts.md` already documents; this ADR makes it normative for substrate.
- Fleet-inbox directory `active/<task>/.wos/fleet-inbox/` is gitignored and cleaned by `slice-closure` or `task-close`. No impact on archived tasks.

## Alternatives considered

### Alternative 1: Keep ADR-0022 documentary; let each fleet command invent its own worker shape

- Skip canonical worker contract; each `*-fleet` command declares its own input/output ad-hoc.
- Rejected: this is what the Epic J research called out as the failure mode. With three planned fleet commands at minimum (J.6 atom-audit-fleet, J.7 screen-spec-fleet, J.8 task-init complexity fan-out, plus K.7 eval harness consuming all of them), divergent shapes mean each downstream consumer needs N adapters. The cost of one canonical contract is far lower than the cost of N divergent ones.

### Alternative 2: Last-write-wins on substrate (current behavior, just formalize it)

- Document the section ownership matrix but allow any writer to overwrite any section. Conflict resolution = whoever wrote last.
- Rejected: this is what we have today, and the Epic K v2.1 research surfaced it as the silent-overwrite class that becomes lethal once a persona/agent layer joins. Five of the nine AAA references (Microsoft, Anthropic, VS Code, Stripe, HashiCorp) explicitly reject last-write-wins for typed shared state. The remaining four don't address it at all (their state model is different). Production evidence cited in the Epic K v2.1 doc (Block/Square Goose 1.0 session.jsonl provenance pattern) confirms explicit ownership pays back the surface cost.

### Alternative 3: Hierarchical "personas as a layer above commands" (Epic K v1 proposal)

- Personas invoke commands; commands execute. Personas own the orchestration; commands own the unit of work. Asymmetric responsibility.
- Rejected: zero of nine AAA references use this shape in production. Epic K v2 documented the contradiction: Anthropic Skills, Microsoft Agent Framework, GitHub Copilot Workspace, VS Code Chat Participants, Stripe Workbench, Vercel AI SDK 6, Cognition Devin all treat agents and commands (or their equivalents) as peers sharing state, never as layered with one above the other. Inventing the hierarchy puts Bruno's WOS off the convergent path for no gain.

### Alternative 4: Defer ADR-0034 until after first `*-fleet` ship to learn from real use

- Ship J.6 atom-audit-fleet first, observe what shape its workers need, then write ADR-0034.
- Rejected: J.6 cannot ship without a worker contract. The chicken-and-egg resolves the other way: contract first, fleet second, iterate based on production signal. The contract is small (one shared block file + one ADR + one WOS topic); the cost of writing it before J.6 is far lower than the cost of refactoring J.6 after.

## References

- `commands/_shared/worker-contract.md` — canonical worker input/output/status shape introduced by this ADR.
- `wos/substrate-peers.md` — full section ownership matrix + read/write contracts + conflict resolution + audit schema.
- `WORKFLOW_OPERATING_SYSTEM.md ## Cross-cutting workflow guardrails` — 4-line stub linking to the two files above.
- `_internal/epic-j-multi-agent-research-2026-06-04.md` — Epic J research (J.1 worker contract scope).
- `_internal/epic-k-v2.1-implementation-ready-2026-06-04.md` — Epic K v2.1 §5 substrate architecture; §6 Epic J revision verdict.
- ADR-0001 (PROPOSED-by-default) — substrate-peer PROPOSED blocks extend the inline pattern to section scope.
- ADR-0011 (Shared canonical blocks) — `commands/_shared/worker-contract.md` follows this discipline.
- ADR-0022 (Sub-agent orchestration topic) — this ADR promotes 0022 from documentary to enforceable.
- ADR-0029 (Drift guards) — drift-guard candidate hook documented in §5.6 of v2.1; deferred to K.4 implementation.
- ADR-0031 (EARS) — DECISIONS.md ledger discipline references EARS form.
- ADR-0033 (verify-against-rubric stateless subagent) — the worker contract status taxonomy aligns with the verdict shape from ADR-0033 (extended to fleet-scale).
- Anthropic Outcomes API (released 2026-05-06) — source of the canonical status taxonomy `satisfied | needs_revision | max_iterations_reached | failed | interrupted`.
- Microsoft Agent Framework Workflows GA Nov 2025 — typed shared state + executor ownership pattern.
- Anthropic Skills open standard 2025-12-18 — peer state model + read-only-by-default.

## Notes

This ADR is the JOINT J.1 + K.1 foundation. It is the FIRST item shipped under Epic J implementation (Week 1 Foundation per the v2.1 roadmap) and is the FIRST item of K.1 by the time K.1 starts. Both J.1 and K.1 reference this ADR as their normative source.

Pre-K gate items 2 + 3 (J.6 OR J.7 shipped; J.11/K.7 operational; J.5 schema stable) remain operational gates for K.2 onwards. K.1 docs (the rest of K.1: ADR-0035 SKILL.md adoption, maturity ladder docs) can ship after ADR-0034 lands but before the operational gates clear — they are docs-only and have no runtime dependency on fleet evidence.

Conflict resolution choice (REFUSE over last-write-wins) is the single load-bearing call in this ADR. If it turns out to be too friction-heavy in practice (e.g., users get blocked by REFUSE more than 1x/day during normal flow), revisit in a future ADR with empirical evidence from VERIFICATION_LOG.jsonl `event=refuse` counts.

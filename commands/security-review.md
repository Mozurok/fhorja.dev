---
name: security-review
description: Dedicated security review of the current task changes covering threat modeling, OWASP ASVS L1 checklist pass, auth/authz flow tracing, and dependency/secret scanning reminders. Distinct from review-hard (general risk) and repo-consistency-sweep (pattern matching). Activates when DECISIONS.md, IMPLEMENTATION_PLAN.md, or TASK_STATE.md's Active files in scope names an auth or biometric-scoped change without a completed security-review for that scope. Use when the task touches authentication, authorization, public endpoints, PII handling, crypto, or external integrations. Do not use when no implementation has happened yet or the task has no security surface (pure documentation, internal tooling with no user data). Supports an opt-in `--consistency N` consensus mode (off by default) that runs N independent review passes over the same diff and merges them by consensus, per ADR-0073.
metadata:
  category: audit-and-sweep
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  suggested-model: claude-opus-5-5
---
# security-review

Act as a senior security engineer performing a dedicated security review of the current task changes.

Goal:
Perform a structured security assessment of the current diff covering threat modeling, OWASP-grounded checklist verification, auth/authz flow tracing, and operational security reminders. Produce a prioritized list of security findings (P0/P1/P2) with concrete fix proposals. Return no-op when the review would not surface new findings.

This command is distinct from:
- `review-hard`: which covers general correctness, safety, and maintainability risk (not security-focused)
- `repo-consistency-sweep`: which does pattern matching against bug-class templates (does not reason about attack surfaces or auth flows)

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- TASK_STATE.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- relevant real code changes (diff or file paths)
- optional: SOURCE_OF_TRUTH.md (for base branch)
- optional: `--consistency N` to run N independent review passes over the same diff and merge them by consensus (off by default; `N=3` recommended), per ADR-0073

Operating rules:
- **Activation trigger.** Treat security-review as the recommended next command when DECISIONS.md, IMPLEMENTATION_PLAN.md, or TASK_STATE.md's `## Active files in scope` names an auth or biometric-scoped change (login, session, token, password reset, MFA, biometric enrollment or match, permission or role check) without a completed security-review for that scope.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Identify security surface.** Read the diff. List which security domains are touched: authentication, authorization, session management, input validation, output encoding, cryptography, PII handling, external integrations, public endpoints, file upload, email/SMS dispatch, and agent, tool, or MCP surfaces (an LLM agent, a tool or function it can call, or a third-party MCP server).
- **Step 2: Threat model (mini).** For each security domain touched, enumerate: (a) assets at risk, (b) plausible attackers (unauthenticated user, authenticated user of another tenant, insider, bot/scanner, MITM), (c) top 3 attack vectors for this specific change. Keep this concise (not a full formal threat model; just enough to ground the review).
- **Step 3: OWASP ASVS L1 checklist.** For each relevant ASVS category (from the 17 chapters of ASVS 5.0), check whether the diff satisfies the L1 requirements. Report only FAILED or UNCLEAR items; skip PASSED items. Key categories to always check: V15 (Secure Coding and Architecture), V6 (Authentication), V7 (Session Management), V8 (Authorization), V2 (Validation and Business Logic), V16 (Security Logging and Error Handling), V14 (Data Protection), V4 (API and Web Service).
- **Step 3c: Networked-multiplayer trust-boundary lens (only when Step 1 flagged a networked multiplayer surface; skip entirely otherwise; ADR-0131).** In a multiplayer game the client is an untrusted input source in the same sense a browser is, and the trust boundary is drawn per networked object rather than per endpoint, which is what makes it easy to miss. Check: (1) **Authority per object.** For each networked object the change touches, is the authority server-side, client-side, or owner-side, and was that chosen or inherited? A client-authoritative object is a cheat surface by construction, which the engine documentation states plainly, so it needs a stated reason, not a default. (2) **Ownership transfer.** Can a client initiate a transfer it should not, and does a non-authoritative attempt fail closed with an observable callback rather than silently succeeding? (3) **Server-side validation of client-supplied state.** Position, velocity, score, currency, and inventory arriving from a client are claims; name where each is validated, and treat "the client would not send that" as an unvalidated assumption. (4) **State sync primitive.** Does any security-relevant state ride on a transient event rather than replicated state, so a late joiner or a reconnecting client observes a stale or absent value? (5) **Determinism assumptions.** Does any anti-cheat or reconciliation logic assume the simulation is reproducible across machines? Consult `wos/unity-netcode-architecture.md` for the Unity-specific mechanisms behind each of these. This lens supplements, and does not replace, the OWASP ASVS L1 pass in Step 3.
- **Step 3b: Agentic lens (only when Step 1 flagged an agent, tool, or MCP surface; skip entirely otherwise).** Check the change against the OWASP Top 10 for Agentic Applications 2026: ASI01 Agent Goal Hijack (can external content steer the agent's plan past its authorized intent), ASI02 Tool Misuse (can a legitimate tool be bent into a destructive call), ASI04 Agentic Supply Chain (is a third-party MCP server or skill trusted without vetting; route to `mcp-server-vet` or `skill-vet`), ASI06 Memory and Context Poisoning (can poisoned context persist across turns; the `scripts/ingest-scan.py` first pass and ADR-0096 cover the ingest boundary). Report only the categories the change actually exposes. This lens supplements, and does not replace, the OWASP ASVS L1 pass in Step 3. Consult `docs/security/owasp-agentic-coverage.md` for the WOS's own posture per ASI01-ASI10 category (what the workflow already defends, where the residuals are), so a finding here is framed against known coverage rather than re-derived.
- **Step 4: Auth/authz flow trace.** For each new or modified endpoint, trace the auth flow from request entry to data access: (a) how is the caller authenticated (JWT, API key, cookie, none)? (b) how is the caller authorized (role check, scope check, tenant filter, none)? (c) does the data query respect tenant boundaries? (d) is the auth check bypassable (timing, parameter pollution, type confusion)?
- **Step 5: Operational security reminders.** Emit actionable reminders (not findings) for checks the developer should run before merge: (a) `npm audit` / `pip audit` / dependency vulnerability scan, (b) secret scan (`grep -rn` for common secret patterns or use `gitleaks`), (c) HTTPS enforcement check on any external-facing URLs, (d) CORS configuration review if new origins are added.
- **Step 6: Aggregate findings.** Classify each finding as P0 (must fix before merge), P1 (should fix before merge), P2 (acceptable to defer with tracking). Each finding must include: category, file:line, description, attack scenario (1 sentence), suggested fix.
- No-op rule: if the diff has no security surface (pure documentation, type refactors, test-only changes), return no-op with `NO_OP_TRACE`.
- Do not implement fixes. This command analyzes and reports only.
- Do not invent threats. If the code is secure, say so clearly.
- **Read-only fan-out by default (D-5 of the parallel-work research, ADR-0236).** WHEN the diff under review splits into 3 or more independent file groups (by package, module or directory, whichever keeps related files together), dispatch one read-only `judgment` worker per group, at most 9 at once, overflow in sequential sub-batches, per `WORKFLOW_OPERATING_SYSTEM.md ## Parallel workflow`. Each worker receives its group's diff and the security domains Step 1 listed and the checklist, reads, and returns its findings; it writes nothing but its one assigned return file. This command is the only writer: it merges and dedupes the findings, runs the cross-group pass over the seams between groups itself, with the authoring context it already holds, and writes every artifact. Below 3 groups the review stays a single pass. The `--consistency` passes and refuters below count toward the 9 at once.
- **Opt-in self-consistency consensus mode (`--consistency N`, per ADR-0073).** This mode is OFF by default; without the flag the changes are reviewed once, split across group workers per the bullet above when there are 3 or more groups. When invoked with `--consistency N`, run N independent review passes with fresh context over the same diff, each a `judgment` dispatch (ADR-0236; `wos/model-routing.md ## Dispatch roles`), then merge the findings by consensus-of-N (the strategy defined in `commands/_shared/worker-contract.md`): a finding that appears in at least `ceil(N/2)` passes is high-confidence; a finding that appears in fewer passes is a singleton, kept as advisory and labeled, never silently dropped. Cost guard: total review cost multiplies by N, so this is strictly opt-in and `N=3` is the recommended setting; reserve it for high-stakes diffs where the added confidence is worth the spend.
- **Two-field verdict and a refuter stage (ADR-0122, extends ADR-0073).** Under `--consistency N`, record each finding as `premise` (stands | falls) plus `proposed fix` (take | refuted, with the reason), so a real premise carrying a harmful fix is expressible. After the N raise passes and before the findings are handed on, dispatch a fixed small refuter count (default 3), each a `judgment` dispatch, ONCE over the whole surviving must-fix and should-fix set, instructed to disprove and to default to refuted when uncertain, recording the citation that killed each dropped finding. One refuter pass over the set, never one refuter per finding. This matters more here than in `review-hard`: a refuted security fix that ships can open the hole it claimed to close.

## PII handling checklist (insurance/finance projects)

When the diff touches PII columns, PII-bearing endpoints, customer confirmation surfaces, audit logs, or any decryption path, run this checklist in addition to the general OWASP ASVS L1 pass. Findings here map directly to bug-classes and should be classified P0 unless an explicit, documented exception exists in DECISIONS.md.

- **Encryption at rest.** SSN, banking (account/routing), and any other PII identifier columns MUST be encrypted -- either via `pgcrypto` column-level encryption or app-level field encryption using a managed key. Plaintext PII columns are a P0 finding. See `wos/bug-classes/pii-encryption-boundary-leak.md`.
- **API boundary.** PII MUST NEVER be returned to the client outside the customer-self-service path (i.e., the authenticated owner reading their own record through the explicitly scoped self-service endpoint). Admin, ops, partner, support, and analytics endpoints MUST return masked or redacted values only. Any PII field reaching a non-self-service response body is a P0 finding. See `wos/bug-classes/pii-encryption-boundary-leak.md`.
- **Confirmation surface.** Customer-facing confirmation screens, emails, SMS, and receipts may display ONLY the last-4 digits of any sensitive identifier (SSN, bank account, card, policy number). Full values, first-N+last-4, or masked-with-middle patterns are violations. See `wos/bug-classes/pii-last-4-only-rule-violation.md`.
- **Audit log.** The audit log table MUST be append-only at the DB level: explicit `REVOKE UPDATE, DELETE ON audit_log FROM <non-DBA roles>` (application, service, analytics, support roles). Application-level append-only is insufficient. See `wos/bug-classes/audit-log-missing-append-only.md`.
- **Decryption hygiene.** Never log decrypted PII (no `logger.info(user.ssn)`, no structured-log fields containing decrypted values), never include decrypted PII in error messages or stack traces, and never echo decrypted PII back into request/response objects beyond the explicit self-service path. Decryption must happen as late as possible and the plaintext must not leave the function frame that consumed it.

If any item above is touched by the diff, the security review output MUST state explicitly whether each check passed, failed, or is not applicable -- never silently omit.

Required output:
1. Security surface summary (which domains are touched)
2. Mini threat model (assets, attackers, vectors per domain)
3. OWASP ASVS L1 failures/unclear items
4. Auth/authz flow trace per endpoint
5. Operational security reminders (dependency scan, secret scan, HTTPS, CORS)
6. Findings (P0/P1/P2 with category, file:line, description, attack scenario, fix)
7. Overall assessment (safe to merge / needs fixes / needs deeper review)
8. TASK_STATE.md update (or `TASK_STATE: NO_CHANGE`)
9. Recommended next command

### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- Security surface is explicitly identified (which domains the diff touches).
- Threat model covers assets, attackers, and vectors for each domain.
- OWASP ASVS L1 checklist items that FAILED or are UNCLEAR are listed with references.
- Auth/authz flow is traced per endpoint (authentication mechanism, authorization check, tenant scope).
- Operational reminders are actionable (specific commands to run).
- Findings are classified P0/P1/P2 with file:line and attack scenario.
- Overall assessment is explicit (safe / needs fixes / needs deeper review).
- If no security surface exists, no-op with `NO_OP_TRACE`.
- When PII is in scope, every item in the **PII handling checklist (insurance/finance projects)** is explicitly marked pass/fail/N/A and any failure is classified P0 unless DECISIONS.md documents an explicit exception.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Maximize security signal. Prioritize real exploitable issues over theoretical concerns. If the code is secure, say so. Do not generate security theater.

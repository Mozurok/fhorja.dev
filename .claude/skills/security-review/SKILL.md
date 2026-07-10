---
name: security-review
description: |-
  Dedicated security review of the current task changes covering threat modeling, OWASP ASVS L1 checklist pass, auth/authz flow tracing, and dependency/secret scanning reminders. Distinct from review-hard (general risk) and repo-consistency-sweep (pattern matching). Use when the task touches authentication, authorization, public endpoints, PII handling, crypto, or external integrations. Do not use when no implementation has happened yet or the task has no security surface (pure documentation, internal tooling with no user data). Supports an opt-in `--consistency N` consensus mode (off by default) that runs N independent review passes over the same diff and merges them by consensus, per ADR-0073.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 3000
  suggested-model: claude-opus-4-7
---

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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- relevant real code changes (diff or file paths)
- optional: SOURCE_OF_TRUTH.md (for base branch)
- optional: `--consistency N` to run N independent review passes over the same diff and merge them by consensus (off by default; `N=3` recommended), per ADR-0073

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Identify security surface.** Read the diff. List which security domains are touched: authentication, authorization, session management, input validation, output encoding, cryptography, PII handling, external integrations, public endpoints, file upload, email/SMS dispatch, and agent, tool, or MCP surfaces (an LLM agent, a tool or function it can call, or a third-party MCP server).
- **Step 2: Threat model (mini).** For each security domain touched, enumerate: (a) assets at risk, (b) plausible attackers (unauthenticated user, authenticated user of another tenant, insider, bot/scanner, MITM), (c) top 3 attack vectors for this specific change. Keep this concise (not a full formal threat model; just enough to ground the review).
- **Step 3: OWASP ASVS L1 checklist.** For each relevant ASVS category (from the 17 chapters of ASVS 5.0), check whether the diff satisfies the L1 requirements. Report only FAILED or UNCLEAR items; skip PASSED items. Key categories to always check: V1 (Architecture), V2 (Authentication), V3 (Session), V4 (Access Control), V5 (Validation), V7 (Error Handling and Logging), V8 (Data Protection), V13 (API and Web Service).
- **Step 3b: Agentic lens (only when Step 1 flagged an agent, tool, or MCP surface; skip entirely otherwise).** Check the change against the OWASP Top 10 for Agentic Applications 2026: ASI01 Agent Goal Hijack (can external content steer the agent's plan past its authorized intent), ASI02 Tool Misuse (can a legitimate tool be bent into a destructive call), ASI04 Agentic Supply Chain (is a third-party MCP server or skill trusted without vetting; route to `mcp-server-vet` or `skill-vet`), ASI06 Memory and Context Poisoning (can poisoned context persist across turns). Report only the categories the change actually exposes. This lens supplements, and does not replace, the OWASP ASVS L1 pass in Step 3.
- **Step 4: Auth/authz flow trace.** For each new or modified endpoint, trace the auth flow from request entry to data access: (a) how is the caller authenticated (JWT, API key, cookie, none)? (b) how is the caller authorized (role check, scope check, tenant filter, none)? (c) does the data query respect tenant boundaries? (d) is the auth check bypassable (timing, parameter pollution, type confusion)?
- **Step 5: Operational security reminders.** Emit actionable reminders (not findings) for checks the developer should run before merge: (a) `npm audit` / `pip audit` / dependency vulnerability scan, (b) secret scan (`grep -rn` for common secret patterns or use `gitleaks`), (c) HTTPS enforcement check on any external-facing URLs, (d) CORS configuration review if new origins are added.
- **Step 6: Aggregate findings.** Classify each finding as P0 (must fix before merge), P1 (should fix before merge), P2 (acceptable to defer with tracking). Each finding must include: category, file:line, description, attack scenario (1 sentence), suggested fix.
- No-op rule: if the diff has no security surface (pure documentation, type refactors, test-only changes), return no-op with `NO_OP_TRACE`.
- Do not implement fixes. This command analyzes and reports only.
- Do not invent threats. If the code is secure, say so clearly.
- **Opt-in self-consistency consensus mode (`--consistency N`, per ADR-0073).** This mode is OFF by default; without the flag the review is a single pass and behaves exactly as today. When invoked with `--consistency N`, run N independent review passes with fresh context over the same diff, then merge the findings by consensus-of-N (the strategy defined in `commands/_shared/worker-contract.md`): a finding that appears in at least `ceil(N/2)` passes is high-confidence; a finding that appears in fewer passes is a singleton, kept as advisory and labeled, never silently dropped. Cost guard: total review cost multiplies by N, so this is strictly opt-in and `N=3` is the recommended setting; reserve it for high-stakes diffs where the added confidence is worth the spend.

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

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

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

<!-- cache-breakpoint -->

---
name: human-in-the-loop-audit-missing
category: observability
default-severity: P1
priority: P1
pillars: [observability, compliance, security]
cwe: [CWE-778]
languages: [typescript, sql, markdown]
file-patterns: ["apps/web/src/server/**", "apps/web/src/app/**", "packages/**/audit/**", "supabase/migrations/**"]
perspectives: [operator, maintainer, auditor]
reversibility-check: false
---

# human-in-the-loop-audit-missing

A workflow requires a human operator to perform an action in an external system (carrier portal, regulator filing site, bank dashboard, third-party CRM) and the app records nothing about it. The action happens in the real world but the app's audit trail has a hole: no WHO, no WHEN, no WHAT. When a customer, regulator, or internal compliance reviewer later asks "did the agent actually submit on day X?", the system has no answer.

## What it looks like

- A workflow step says, in prose or in a runbook, "the agent then logs into the carrier portal and submits the application" -- and the next persisted state is just `status = 'submitted'` with no operator id, no timestamp, no payload reference, no confirmation number.
- A task transitions from `pending_external_action` to `external_action_complete` via a single button click, with no audit row written at click-time and no follow-up row capturing the external system's response.
- The DB has a `status` column that tracks workflow position but no append-only audit table capturing operator-initiated transitions.
- The UI exposes a "mark as submitted" affordance with no required attestation fields (confirmation number, screenshot, external reference id).
- Reports can answer "how many submissions today?" but cannot answer "who submitted application 12345 and when did the carrier confirm?".

## Why it matters

- Insurance, finance, and healthcare workflows are subject to regulatory audit. Chain-of-custody for every state change is mandatory, and human-initiated external actions are the single most commonly missed link.
- When a customer disputes timing ("the agent told me they submitted on Tuesday but the carrier shows Thursday"), the operator has no defensible record. Liability lands on the platform.
- Internal investigations of error, fraud, or process failure cannot reconstruct what happened. Root-cause analysis falls back to interviewing humans, which is slow and unreliable.
- Compliance reviewers treat missing audit as evidence of control failure even when the underlying action was correct. The gap itself is the finding.

## How to detect

Workflow-level review:

- Walk each workflow step. For every step that involves a human acting in an external system, look for two audit-log rows: one BEFORE the action (intent: "operator X is about to submit application Y at time T") and one AFTER (outcome: "operator X confirmed submission of Y, carrier reference Z, at time T2").
- If only the post-state exists (or worse, only a `status` column update), flag the step.
- Any step whose only persisted artifact is a status transition triggered by an operator click is a candidate.

Code-level grep:

```
rg -n "status\s*=\s*['\"](submitted|filed|sent|delivered)" apps/web/src \
  | rg -v "audit_log|audit_entry|insertAudit"
```

Schema-level: any table tracking external-action state without a sibling append-only audit table referencing it.

## How to fix

Emit two immutable audit-log rows per human-in-the-loop external action:

1. Intent row, written when the operator commits to the action (e.g., clicks "I am about to submit"). Captures: operator id, task id, action type, target external system, intended payload hash, client timestamp, server timestamp.
2. Outcome row, written when the operator back-fills the result (confirmation number, screenshot upload reference, external system response). Captures: operator id, task id, action type, outcome status, external reference id, evidence artifact ids, server timestamp.

Both rows MUST be immutable and append-only per `audit-log-missing-append-only` (no UPDATE, no DELETE, enforced by RLS and by table design). The intent row MUST be written BEFORE the operator leaves the app to perform the action, not reconstructed after the fact.

UI requirements:

- The "I am about to submit" affordance writes the intent row synchronously and only then surfaces the external link.
- The return path requires the operator to enter the confirmation number or upload evidence before the task can advance; this write becomes the outcome row.
- Neither row is editable from the app surface. Corrections happen via a new compensating audit row, never by mutation.

## CWE / standard refs

- CWE-778: Insufficient Logging. The application does not record security-relevant or compliance-relevant events at sufficient granularity to support audit, dispute resolution, or incident reconstruction.

## See also

- `wos/bug-classes/audit-log-missing-append-only.md` (the immutability contract both rows rely on)
- `wos/bug-classes/missing-business-metric.md` (sibling observability gap for non-audit signals)

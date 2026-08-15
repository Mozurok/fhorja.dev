---
name: human-in-the-loop-audit-missing
category: observability
default-severity: P1
cwe: [CWE-778]
languages: [typescript, sql, markdown]
file-patterns: ["apps/web/src/server/**", "apps/web/src/app/**", "packages/**/audit/**", "supabase/migrations/**"]
perspectives: [operator, maintainer, auditor]
reversibility-check: false
---

# human-in-the-loop-audit-missing

## Trigger

A workflow requires a human operator to act in an external system, a carrier portal, a regulator filing site, a bank dashboard, a third-party CRM, and the application records nothing about it. The action happens in the real world and the audit trail has a hole where it should be: no who, no when, no what.

The hole is discovered by a question nobody can answer. A customer disputes timing and the operator has no defensible record. An internal investigation of an error or a suspected fraud cannot reconstruct the sequence and falls back on interviewing people months later. A compliance reviewer in a regulated workflow treats the missing record as evidence of a control failure, and that judgment does not depend on whether the underlying action was correct: the gap itself is the finding. Human-initiated external actions are the most commonly missed link in chain-of-custody precisely because they happen outside the system that keeps the records.

CWE-778 (Insufficient Logging): the application does not record compliance-relevant events at a granularity that supports audit, dispute resolution, or incident reconstruction.

## Detection

- A workflow step described in prose or a runbook as "the operator logs into the portal and submits", where the next persisted state is a status value with no operator identity, no timestamp, no payload reference, and no external confirmation.
- A transition from an awaiting-external-action state to a completed one driven by a single click, with no row written at click time and no row capturing the external system's response.
- A schema with a status column tracking workflow position and no append-only audit table beside it.
- A mark-as-done affordance in the UI with no required attestation: no confirmation number, no evidence upload, no external reference.
- Reporting that can answer how many actions happened today and cannot answer who performed a specific one or when the external system confirmed it.

```
rg -n "status\s*=\s*['\"](submitted|filed|sent|delivered)" apps/web/src \
  | rg -v "audit_log|audit_entry|insertAudit"
```

Schema-level: any table tracking external-action state with no sibling append-only table referencing it.

## Retrieval

- The workflow definition end to end, in whatever form it exists: a state machine, a runbook, a sequence of handlers. The gap is a step, so the steps have to be enumerable before it can be located.
- Every write that advances state for the step under analysis, including the UI handler that triggers it. The absence being looked for is an absence at a specific moment, and the moment is the handler.
- The audit table's schema and its constraints, or the fact that none exists. Whether appends are enforced as append-only by table design and access policy is the difference between a record and a mutable claim.
- The UI affordance and its required fields, because the attestation either exists at the point of action or is reconstructed afterward, and reconstructed attestation is what this class produces.
- Any retention, export, or reporting path over the audit data. A record that cannot be produced on request does not answer the question that motivates it.
- The regulatory or contractual requirement that applies to this workflow, cited from a captured source rather than assumed from the industry. Do not assert what a regime requires from memory.

## Analysis prompt

Given the retrieved workflow, its state-advancing writes, and the audit schema:

1. Enumerate every step where a human acts in an external system. Report the list. A step that only reads externally is not in scope; name the ones you excluded and why.
2. For each such step, report whether a record is written BEFORE the operator leaves the application, and whether one is written AFTER, capturing the external system's response. Report the two independently. Only-after is the common shape and it cannot establish intent or timing.
3. For each record that exists, report its fields against what a reconstruction actually needs: operator identity, task identity, action type, target system, a reference to the intended payload, and both client and server timestamps for the intent; operator identity, outcome, external reference, evidence artifacts, and server timestamp for the outcome.
4. Report whether the audit records are immutable in practice, not in intent. Name the mechanism: table design, access policy, absence of an update path in the application. A table that the application can update is a log that can be edited, and an editable log answers a dispute weakly.
5. Report whether the application exposes any edit or delete path to these records, including administrative ones. Corrections should arrive as new compensating rows; find out whether they do.
6. For each mark-as-done affordance, report which attestation fields are required before the state can advance. An optional confirmation number is an absent one at the moment it matters.
7. Report whether the stored records can answer the two questions this class exists for: who performed a specific action and when, and when the external system confirmed it. Answer them against the schema, concretely, for one real record if possible.
8. WHERE the analysis asserts a regulatory requirement, cite the captured source for it. If no source was captured, report the requirement as ungrounded and recommend capturing it rather than reasoning from the domain.
9. Recommend, in order: write an intent record synchronously when the operator commits to acting, before the application surfaces the external link, capturing identity, target, intended payload reference, and both timestamps; require the confirmation number or evidence on the return path and make that write the outcome record; enforce append-only at the table and the access policy rather than by convention; make corrections compensating rows rather than mutations; and verify by answering, from stored data alone, who did a specific action and when the external system confirmed it.

## Severity rubric

- **P1**: a human-in-the-loop external action in a regulated or contractual workflow with no intent record and no outcome record. Justification: the chain of custody is broken at the step most likely to be questioned, and it cannot be repaired retroactively, because the evidence that would fill it never existed. It is not P0 because no data is exposed or corrupted and the workflow itself functions; the loss is the ability to demonstrate what happened.
- **P1 also**: audit rows that exist and are mutable from the application surface. A log that can be edited by the party being audited carries little weight in the dispute it was written for, and its existence invites the assumption that it does.
- **P2**: an outcome record without an intent record, where the outcome carries operator identity and a server timestamp. Timing and intent are unestablished; attribution is not.
- **P2**: complete records with no export or reporting path, so the answer exists and cannot be produced on request.

## Confidence factors

- **HIGH**: a state-advancing write for an external action with no insert into any audit table in the same handler. The handler is the whole evidence.
- **MEDIUM**: an audit table that exists and receives outcome rows only, where intent may be captured by an unrelated mechanism such as an access log not retrieved here.
- **LOW**: a workflow step described in a runbook as external where the application may be performing it through an integration rather than a human, so the class may not apply until the handler is read.

## Examples

### Positive (status flips, nothing records the act)

```ts
// POST /tasks/:id/mark-submitted
await db.from("tasks").update({ status: "submitted" }).eq("id", taskId);
return ok();
```

The operator clicked a button, went to the portal, came back, and clicked again. The row now says submitted. It does not say who, or when they went, or what the portal answered, and there is nothing to produce when the customer says the date was different.

### Negative (intent before, outcome after, both immutable)

```ts
// 1. before the external link is surfaced
await audit.insert({
  kind: "external_action_intent", operatorId, taskId,
  action: "carrier_submit", target: "carrier_portal",
  payloadHash: hash(payload), clientTs, serverTs: now(),
});
return { externalUrl };                       // only now does the operator leave

// 2. on the return path, gated by the form
await audit.insert({
  kind: "external_action_outcome", operatorId, taskId,
  action: "carrier_submit", outcome: "confirmed",
  externalRef: body.confirmationNumber,       // required, not optional
  evidenceIds: body.uploadIds, serverTs: now(),
});
await db.from("tasks").update({ status: "submitted" }).eq("id", taskId);
```

The audit table rejects updates and deletes at the access-policy level, the intent row exists before the operator can act, the state change happens only after the outcome row lands, and a correction later would arrive as a third compensating row rather than as an edit to either of these.

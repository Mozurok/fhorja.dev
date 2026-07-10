# Eval scenario 21: slice-closure with optional `### Learnings` section emission

- **Tags**: slice-closure, reflexion-style-learnings, optional-section, LEARNINGS-md, locked-entry-shape
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates `slice-closure` (slice 12 of the 2026-05-15 context-engineering uplift; ADR-0017) when the slice involved a failed attempt or surprising blocker worth recording. The command must emit an optional `### Learnings` section with the LOCKED 4-bullet shape (`Tried:`, `Failed because:`, `Next time:`, `Cross-project promotion:`) appended to `LEARNINGS.md` (bootstrapped from `templates/LEARNINGS.md` if absent). The routine no-Learnings case is also exercised in variant B to confirm the section is correctly SKIPPED when nothing meaningful happened.

## Setup

Two variants of the scenario; the model is given ONE per run.

**Variant A: slice had a failed attempt that taught a lesson.**

Active task at `projects/acme__widget-pricing/active/2026-05-13_payment-method-tokenization/`. Slice 4 (Stripe Setup Intent integration) just finished. The user reports:

> "We initially tried calling stripe.setupIntents.create() inside our request handler synchronously. It worked locally but caused timeouts in staging because the Stripe API call was on the request critical path (~800ms). We switched to an async job pattern via the existing job queue. Slice 4 is done; both approaches are in the diff because the first attempt's code is preserved in a feature flag for fallback."

**Variant B: slice was routine; no learning.**

Same task path. Slice 5 (display the masked PAN after tokenization) just finished. The user reports:

> "Slice 5 done. Read the tokenized PAN from the customer record; rendered with the standard masked-format helper. No surprises."

## Input prompt

Use ONE:

```text
[VARIANT A]
Run @commands/slice-closure.md

Active task: projects/acme__widget-pricing/active/2026-05-13_payment-method-tokenization/
Slice: 4 (Stripe Setup Intent integration)
Mode: Plan

Status: implemented. We initially tried calling stripe.setupIntents.create() inside the request handler synchronously. It worked locally but caused timeouts in staging because the Stripe API call was on the request critical path (~800ms). We switched to an async job pattern via the existing job queue. Both approaches are in the diff because the first attempt's code is preserved in a feature flag for fallback. Tests pass.
```

```text
[VARIANT B]
Run @commands/slice-closure.md

Active task: projects/acme__widget-pricing/active/2026-05-13_payment-method-tokenization/
Slice: 5 (display masked PAN)
Mode: Plan

Status: implemented. Read the tokenized PAN from the customer record; rendered with the standard masked-format helper. No surprises. Tests pass.
```

## Expected response shape

- Response begins with slice-closure's persona line.
- Response proposes slice closure (PROPOSED status; Plan mode default).
- **Variant A**: response emits an optional `### Learnings` section with a 4-bullet entry to be appended to `LEARNINGS.md`. The entry shape matches the locked format from ADR-0017.
- **Variant B**: response OMITS the `### Learnings` section (the slice was routine; nothing to record).
- Both variants produce the standard slice-closure output (status, completed, deferred, blockers, next action, TASK_STATE update block, Handoff).

## Pass criteria

1. **Variant A emits Learnings section**: a `### Learnings` section appears in the output with the 4-bullet shape (Tried / Failed because / Next time / Cross-project promotion).
2. **Variant A entry shape matches locked format**:
   - `Tried:` mentions the synchronous stripe.setupIntents.create() call in the request handler.
   - `Failed because:` mentions the 800ms latency on the critical path causing staging timeouts.
   - `Next time:` mentions the async job pattern OR equivalent ("treat external API calls > N ms as async by default", etc.); specific and verifiable.
   - `Cross-project promotion: no` (default; user lifts to USER_MEMORY.md later if durable). Acceptable: `yes` is allowed if the model judges this is clearly cross-project (Stripe API latency rules of thumb), but `no` is the safer default.
3. **Variant A targets LEARNINGS.md**: response names `LEARNINGS.md` as the target file (creates from `templates/LEARNINGS.md` if absent). Source field is `slice-4` (matching the slice number).
4. **Variant A no empty bullets**: each bullet has concrete content; vague phrases like "Tried: stuff" or "Next time: be careful" disqualify the entry per ADR-0017.
5. **Variant B omits Learnings section**: no `### Learnings` section appears. The output contract explicitly allows skipping when the slice was routine. A NO_OP_TRACE or "(no learning to record for this slice)" annotation in the transcript is acceptable but not required.
6. **Both variants: standard slice-closure output**: the Required output 1-13 from `commands/slice-closure.md` are produced regardless of Learnings emission (Variant A item 14 is the Learnings section; Variant B item 14 is absent).
7. **Both variants: PROPOSED status**: artifact changes are `PROPOSED`, not `APPLIED` (Plan mode default per ADR-0001).
8. **Variant A: LEARNINGS.md change marked**: `### Artifact changes` lists `LEARNINGS.md` as PROPOSED (created if absent; appended-to if exists).

## Failure modes to watch

- **Variant A omits Learnings**: the slice clearly involved a failed attempt; missing the section means the lesson is lost. ADR-0017's whole point is the optional-but-emitted-when-relevant rule.
- **Variant A emits with empty/vague bullets**: "Tried: the Stripe thing / Failed because: it didn't work / Next time: be careful" violates the explicit shape contract; better no learning than vague learning per ADR-0017.
- **Variant B emits Learnings unnecessarily**: "Tried: read the PAN / Failed because: nothing failed / Next time: nothing to change" pollutes LEARNINGS.md with noise. Optional means skip when nothing to record.
- **Wrong source field**: response uses `slice-N` for Variant A but the wrong N (e.g., slice-5 instead of slice-4) or a non-locked value (e.g., `slice-4-closure`). Per ADR-0017, source values are locked: `slice-NN`, `post-review-pivot`, `incident-triage HOTFIX`, `incident-triage ESCALATE`.
- **Both variants the same response**: signals the model is not reading the slice's outcome.

## Notes

- Related ADRs: [ADR-0017](../../docs/adr/0017-reflexion-style-learnings.md), [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md).
- Related commands: `commands/slice-closure.md`, `commands/post-review-pivot.md` (sibling; pivot is a learning by definition), `commands/incident-triage.md` (sibling; HOTFIX/ESCALATE postmortems).
- Related templates: `templates/LEARNINGS.md`, `templates/USER_MEMORY.template.md` (promotion target).

## History

- 2026-05-18: scenario authored as new-command coverage for slice 12's Learnings section. First eval of the optional section.

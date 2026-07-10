# Eval scenario 51: Insurance compliance checklist pre-launch gate

- **Tags**: insurance, compliance, pre-launch-gate, checklist, NAIC, state-licensure, PII, audit-retention, sign-off
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates that an insurance project initialized with `INSURANCE_COMPLIANCE_CHECKLIST.template.md` carries a fully populated compliance checklist at pre-launch review, covering state licensure, NAIC applicability, PII handling, audit retention, and final sign-off. The scenario also validates the negative path: when the audit retention section is empty, the checklist review must BLOCK pre-launch with an explicit, named reason rather than waving the project through.

This exercises:

- The shape and required sections of `templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md`.
- The pre-launch gate behavior described in `wos/insurance-compliance.md`.
- The escalation contract: missing audit retention is a hard BLOCK, not a soft warning.

## Setup

A bootstrapped insurance project `projects/acme__auto-insurance/` initialized from the insurance project bootstrap path. The project folder contains a populated `INSURANCE_COMPLIANCE_CHECKLIST.md` derived from `templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md`. Two checklist variants are staged for the two turns below.

## Input prompt (turn 1: fully populated checklist)

```text
Review @projects/acme__auto-insurance/INSURANCE_COMPLIANCE_CHECKLIST.md
for pre-launch readiness per @wos/insurance-compliance.md.
```

## Input prompt (turn 2: missing audit retention)

```text
Review @projects/acme__auto-insurance/INSURANCE_COMPLIANCE_CHECKLIST.md
for pre-launch readiness per @wos/insurance-compliance.md.

(checklist has the audit retention section present but empty)
```

## Expected response shape (turn 1: fully populated)

- Reviewer confirms all five canonical sections are present and populated: state licensure, NAIC applicability, PII handling, audit retention by state, and final sign-off.
- Each section is acknowledged by name with a one-line evidence pointer (e.g., licensed states list, NAIC model citation, PII data-flow reference, retention schedule, signer + date).
- Final verdict: pre-launch readiness PASS, with a concise summary listing the five sections and their state.
- No section is skipped, glossed, or merged into another.

## Expected response shape (turn 2: missing audit retention)

- Reviewer detects the audit retention section is empty.
- Pre-launch is **BLOCKED** with the explicit literal phrase "audit retention by state not completed" (or a near-identical wording) in the block reason.
- Block message names the offending section and points at `templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md` and `wos/insurance-compliance.md` as the contract sources.
- A concrete remediation is proposed: fill the retention schedule per state of licensure before re-running the gate.
- No PASS verdict is emitted; the other four populated sections do not override the missing one.

## Pass criteria

1. **Turn 1 -- five sections enumerated**: Response names all five canonical sections (state licensure, NAIC applicability, PII handling, audit retention, sign-off) explicitly, not collapsed into a single bullet.
2. **Turn 1 -- evidence per section**: Each of the five sections is acknowledged with a short evidence pointer rather than a bare "OK" tick.
3. **Turn 1 -- PASS verdict**: Final verdict is an explicit pre-launch PASS, with a one-line summary the user can paste into a release log.
4. **Turn 2 -- BLOCK before sign-off**: Response BLOCKS pre-launch instead of issuing PASS or a soft warning.
5. **Turn 2 -- explicit block phrase**: Block reason contains the literal phrase "audit retention by state not completed" (or close equivalent) so the failure is grep-able in review logs.
6. **Turn 2 -- contract citations**: Block message references both `templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md` and `wos/insurance-compliance.md` by path.
7. **Turn 2 -- remediation proposed**: Block message states a concrete next step (populate retention schedule per licensed state, then re-run the gate).
8. **No partial pass leakage**: Across both turns, the reviewer never approves pre-launch on the strength of four-of-five sections; all five are required.

## Failure modes to watch

- **Silent pass with empty retention**: Reviewer issues PASS in turn 2 because the other four sections look complete, ignoring the empty audit retention section. Direct violation of the pre-launch gate contract.
- **Soft warning instead of block**: Reviewer flags the empty retention as a "TODO" or "follow-up" but still emits a conditional PASS, allowing launch on a promise.
- **Section conflation**: Reviewer treats NAIC applicability as a sub-bullet of state licensure (or folds PII handling into sign-off), reducing the five-section contract to fewer named items.
- **Block without contract citation**: Reviewer blocks turn 2 but does not name the template or the `wos/insurance-compliance.md` policy, leaving the block reason unauditable.

## Notes

- The five-section contract is intentionally rigid: insurance launches are auditable by state regulators, and a missing retention schedule is a regulator-facing defect, not an internal hygiene issue.
- Audit retention is per state of licensure because retention windows vary (typically 3 to 10 years) and a single global number is not sufficient evidence of compliance.

## References

- `internal/templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md` (the checklist shape under test)
- `internal/wos/insurance-compliance.md` (the pre-launch gate policy and BLOCK contract)

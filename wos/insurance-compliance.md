---
activation: model_decision
description: US insurance compliance domain (NAIC, state licensure, HIPAA-adjacent health screening, TCPA, PII rules). Load when the project is insurance/finance and regulatory baseline must be considered.
---

# wos/insurance-compliance.md

Lazy reference for US insurance and insurance-adjacent financial compliance baseline. Load when the task touches quoting, binding, agent licensing, consumer health questionnaires, outbound telephony, or storage of regulated PII. Single concern: provide the minimum regulatory floor any insurance product feature must clear before review. This file is NOT legal advice; it is an engineering checklist with citations.

## When this applies

Load this topic when the task scope includes any of:

- Selling, quoting, or comparing insurance products (life, health, P&C, annuities, Medicare, ACA)
- Capturing licensure or appointment state for agents/producers
- Collecting personal health information for underwriting, screening, or risk classification (even when not a HIPAA covered entity)
- Outbound or inbound calling, SMS, or voicemail to consumers
- Persisting regulated PII (SSN, DOB, drivers license, financial account numbers, MIB-style health attestations)
- Suitability determinations for annuities or life insurance recommendations
- Any flow producing a binding quote, application, or commission event

Skip this topic for non-insurance verticals unless an adjacent regulation applies (e.g., TCPA covers any outbound dialing, not just insurance).

## NAIC Model Acts (most common floor)

The NAIC publishes Model Acts that states adopt with variation. The four most commonly invoked for a digital insurance product:

| Model Act | Scope | Engineering impact |
|---|---|---|
| **Producer Licensing Model Act (#218)** | Licensing, appointment, continuing education for producers | Block bind/quote when producer not licensed + appointed in the consumer's resident state for that line of business |
| **Suitability in Annuity Transactions Model Regulation (#275)** | Best-interest standard for annuity recommendations | Persist suitability questionnaire + recommendation rationale; immutable audit trail |
| **Privacy of Consumer Financial and Health Information Regulation (#672)** | Notice + opt-out for sharing nonpublic personal info | Privacy notice surface at first data collection; opt-out flag honored across downstream services |
| **Unfair Trade Practices Act (#880)** | Misrepresentation, rebating, defamation of insurers | No marketing copy promising features the policy does not include; no automated "discount" UI tied to non-disclosed referral flows |

State adoption varies. Treat the Model Act as the floor; the state-of-residence statute is the ceiling for that consumer.

## State licensure source of truth

Industry pattern: licensure and appointment state lives in a per-agency vendor system (commonly **SureLC** by SuranceBay, or AgencyBloc, or Vertafore Sircon). Each agency maintains its own SureLC tenant; there is no cross-agency visibility of producer licensure.

Implications for engineering:

- Licensure checks are per-agency. A producer licensed at Agency A is NOT automatically visible to Agency B's system even if both use SureLC.
- The agency's SureLC tenant is the source of truth for: NPN, resident state, non-resident state appointments, lines of authority (Life, Health, P&C, Variable), expiration dates, CE compliance status.
- Cache licensure read with a TTL no longer than 24h; the underlying state DOI feed can revoke a license overnight.
- Never compute "licensed" from a local mirror older than the TTL. On binding events, force a fresh check.
- Carrier appointment is a separate dimension from state license. Both must be active for the line of business and the consumer's state at the moment of bind.

## HIPAA-adjacent for health screening

Most insurance-quote products are NOT HIPAA covered entities (covered entities are health plans, healthcare providers, and clearinghouses). Selling life or health insurance and collecting health questionnaires typically falls under state insurance privacy law plus NAIC #672, not HIPAA itself.

That said, the engineering posture should be HIPAA-adjacent:

- **Encryption**: TLS 1.2+ in transit, AES-256 at rest for any field containing height/weight/conditions/medications/MIB-style attestations.
- **Access controls**: role-scoped read; producer can only read applications they originated; underwriter scope is line-of-business scoped.
- **Retention**: explicit retention class on every health-bearing record (see Audit retention below). Default to "delete after policy lifecycle + state retention period" rather than "retain forever".
- **Audit log**: every read of a health-bearing field logged with actor, timestamp, and reason code.
- **Vendor BAAs**: if a downstream vendor processes health data (e.g., a knockout-rules engine), a BAA-equivalent contract is required even when HIPAA does not strictly mandate it, because some carriers contractually require it.

When the product later integrates with a covered entity (e.g., a telehealth provider for paramed exams), the boundary becomes a full HIPAA boundary and a real BAA is mandatory.

## TCPA / DNC for inbound and outbound calls

The Telephone Consumer Protection Act (TCPA, 47 U.S.C. 227) and the FCC's implementing rules govern any automated dialing, prerecorded message, or SMS to a consumer. The 2023-2024 FCC one-to-one consent rule materially raised the bar.

Engineering invariants:

- **Prior express written consent** is required before any autodialed or prerecorded call/SMS for marketing. Consent must be one-to-one (single named seller), not a buried multi-partner checkbox.
- **National DNC scrub** on every outbound campaign list; per-state DNC where applicable.
- **Internal DNC list** honored within 30 days of consumer request; persisted across systems.
- **Time-of-day restrictions**: no calls before 8am or after 9pm local time of the called party.
- **Caller ID transmission**: name + callback number required; spoofing prohibited.
- **Revocation**: a consumer's "stop" by any reasonable means revokes consent across all channels; engineering must propagate the revocation across SMS, voice, and email queues within a documented SLA.

Inbound calls have a lower bar but recording requires disclosure under two-party-consent states.

## PII rules summary

Standard PII handling rules apply with insurance-specific intensifiers. See related bug-classes for enforcement at code level:

- SSN: never log, never echo back to UI in plaintext, mask all but last 4 in any rendered surface.
- DOB: treat as PII; use in risk scoring is permitted, display in audit views is not.
- Drivers license number: collect only when statutorily required for the line of business.
- Financial account numbers: PCI-scope if used to collect premium; tokenize via the payment processor; never persist a PAN in the application database.
- Email + phone: not PII alone in most state regimes, but become PII when joined to a policy or quote record.

Related Fhorja bug-classes live in `wos/bug-classes/` and should be consulted when implementing forms or storage layers that touch the above fields.

## Audit retention by state

Retention varies by state and line of business; there is no national floor. Typical ranges observed:

- **Producer transaction records**: 3 to 7 years post-transaction (e.g., NY 6 years, CA 5 years, FL 5 years, TX 4 years).
- **Suitability documentation for annuities**: minimum 5 years from sale per NAIC #275; many states require 7.
- **Health questionnaire data**: tied to policy lifecycle plus the state insurance retention period; conservative default is 7 years post-policy-termination.
- **Recorded calls (when used as transaction record)**: minimum the same as producer transaction records for that state.

Engineering implication: every regulated record needs an explicit retention class and an automated purge job. "Retain forever" is a compliance liability, not a feature. The retention class lives on the record itself, not in tribal knowledge.

## Templates and checklists

The starter checklist for any new insurance product slice is `templates/INSURANCE_COMPLIANCE_CHECKLIST.template.md`. Copy at task-init when the project charter indicates an insurance vertical. The checklist covers: licensure check placement, suitability persistence, privacy notice surfaces, TCPA consent capture, retention class assignment, and audit log coverage.

## Related bug-classes

Consult these bug-classes during implementation and review:

- `pii-encryption-boundary-leak` :: PII crossing an encryption boundary in plaintext (logs, stack traces, analytics, queue payloads)
- `pii-last-4-only-rule-violation` :: more than last-4 of SSN or account number rendered in a user-facing surface, export, or log
- `audit-log-missing-append-only` :: consent or intervention record written through a mutable path (closest existing class for consent-artifact gaps)
- `stale-csv-cache-import` :: a regulated read (e.g. licensure) served from a cache past its TTL
- `form-error-not-associated` :: accessibility-adjacent; regulators have begun citing under UDAP/UTPA

Planned (not yet in the library): `missing-consent-record` (persisted consent artifact for outbound dial or SMS), `retention-class-missing` (explicit retention class on regulated records). Until they land, flag instances via `capture-observation`.

## References

External authoritative sources. Always check for amendments before locking a decision.

- NAIC Model Laws index :: https://content.naic.org/cipr-topics/model-laws
- NAIC #218 Producer Licensing Model Act :: https://content.naic.org/sites/default/files/MO218.pdf
- NAIC #275 Suitability in Annuity Transactions :: https://content.naic.org/sites/default/files/MO275.pdf
- NAIC #672 Privacy of Consumer Financial and Health Information :: https://content.naic.org/sites/default/files/MO672.pdf
- HHS HIPAA for Professionals :: https://www.hhs.gov/hipaa/for-professionals/index.html
- FCC TCPA rules and 2023 one-to-one consent order :: https://www.fcc.gov/document/fcc-closes-tcpa-lead-generator-loophole-protects-consumers
- FTC National Do Not Call Registry :: https://www.donotcall.gov/
- NAIC State Insurance Regulators directory :: https://content.naic.org/state-insurance-departments

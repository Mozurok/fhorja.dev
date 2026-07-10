---
project: {{project_name}}
states_of_operation: {{state_codes_comma_separated}}
last_reviewed: {{YYYY-MM-DD}}
compliance_owner: {{owner_name_or_role}}
review_cadence: {{quarterly_or_annual}}
---

# Insurance Compliance Checklist :: {{project_name}}

Scope: US-focused. Covers NAIC model acts, per-state licensure, HIPAA-adjacent
health screening, TCPA/DNC for inbound calls, audit log retention, PII handling,
and carrier-specific obligations.

## State licensure (per-state agent appointment via SureLC-style source)

- [ ] Active producer license verified for every state in {{state_codes_comma_separated}}
- [ ] Carrier appointments synced from {{licensure_source_system}} (e.g. SureLC, NIPR)
- [ ] Appointment expiration alerts configured at T-{{days_before_expiry}} days
- [ ] Non-resident license renewals tracked separately from resident license
- [ ] License lookup audit trail retained for {{license_audit_retention_years}} years
- [ ] Block sales flow when no active appointment exists for state X carrier pair

## NAIC Model Acts applicable

- [ ] Suitability in Annuity Transactions Model Regulation (#275) -- best interest standard
- [ ] Producer Licensing Model Act (#218) -- continuing education tracked
- [ ] Unfair Trade Practices Act (#880) -- marketing copy reviewed
- [ ] Privacy of Consumer Financial and Health Information (#672) -- opt-in / opt-out flows
- [ ] Insurance Information and Privacy Protection (#670) -- adverse underwriting notices
- [ ] Market Conduct Surveillance Model Law (#693) -- complaint log maintained
- [ ] Model act applicability matrix per state at {{naic_matrix_path}}

## HIPAA-adjacent (health screening data)

- [ ] At-rest encryption: {{at_rest_encryption_algorithm}} (AES-256 minimum)
- [ ] In-transit encryption: TLS 1.2+ enforced on all health data endpoints
- [ ] Retention policy: health screening data purged after {{health_data_retention_days}} days
- [ ] Access controls: role-based with quarterly access review
- [ ] Minimum necessary rule enforced in queries returning health attributes
- [ ] BAA executed with {{baa_counterparties}} (carriers, screening vendors)
- [ ] Breach notification runbook at {{breach_runbook_path}}
- [ ] PHI never logged in app logs (verified via {{log_redaction_tool}})

## State-specific health questionnaire requirements

- [ ] CA: pre-app questionnaire matches CDI bulletin {{cdi_bulletin_ref}}
- [ ] NY: Reg 187 best interest disclosure shown before health questions
- [ ] FL: senior product disclosure for applicants 65+
- [ ] TX: required suicide-question phrasing per TDI rule {{tdi_rule_ref}}
- [ ] Per-state question variant map at {{questionnaire_matrix_path}}
- [ ] Auto-block submission when state-required question is unanswered

## TCPA / DNC (telemarketing rules for inbound calls)

- [ ] Inbound-only call flag enforced; no outbound dialer without express written consent
- [ ] Internal DNC list synced from {{dnc_source}} every {{dnc_sync_hours}} hours
- [ ] National DNC scrub before any callback within {{callback_window_days}} days
- [ ] Recorded-call consent disclosure played in two-party states
- [ ] Call recording retention: {{call_recording_retention_days}} days
- [ ] Quiet hours respected per called party local time (8am to 9pm)
- [ ] Lead vendor TCPA consent artifacts archived at {{lead_consent_archive_path}}

## Audit log retention (per state minimums)

- [ ] Application records: {{application_record_retention_years}} years (max of state minimums)
- [ ] Marketing materials: 3 years (NAIC default) or longer per state
- [ ] Producer activity logs: {{producer_log_retention_years}} years
- [ ] Complaint records: 5 years from final resolution
- [ ] Logs are append-only with cryptographic chaining ({{chain_method}})
- [ ] Retention enforced by lifecycle policy in {{storage_backend}}
- [ ] Legal hold override path documented at {{legal_hold_runbook_path}}

## PII handling

- [ ] At-rest encryption for all PII columns ({{pii_encryption_provider}})
- [ ] Last-4 rule: SSN, DOB, account numbers displayed as last-4 only in UI
- [ ] Append-only audit on every PII read ({{audit_table_name}})
- [ ] Per-record access reason captured at read time
- [ ] Data subject access request (DSAR) flow documented at {{dsar_runbook_path}}
- [ ] State-level CCPA/CPRA, VCDPA, CPA coverage matrix at {{state_privacy_matrix_path}}
- [ ] Tokenization for downstream analytics (no raw PII outside {{prod_vpc_name}})

## Carrier-specific compliance

- [ ] {{carrier_1}} -- producer guide acknowledged: {{carrier_1_guide_version}}
- [ ] {{carrier_2}} -- replacement form workflow validated
- [ ] {{carrier_3}} -- senior suitability sign-off captured
- [ ] Illustration disclosure rules per carrier documented at {{illustration_matrix_path}}
- [ ] Carrier-mandated training completion tracked in {{training_lms}}
- [ ] Anti-money-laundering (AML) training current per carrier requirements
- [ ] Carrier-specific marketing pre-approval workflow at {{marketing_approval_path}}

## Sign-off

Compliance officer name: {{compliance_officer_name}}
Title: {{compliance_officer_title}}
Date reviewed: {{YYYY-MM-DD}}
Signature method: {{signature_method}} (wet, e-sign, in-system attestation)
Next mandatory review date: {{next_review_YYYY-MM-DD}}
Exceptions logged at: {{exceptions_log_path}}
Notes: {{signoff_notes}}

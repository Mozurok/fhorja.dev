-- The carrier-facing trail. Unlike audit_log this one is inspected by an
-- external auditor, so it is append-only at the privilege layer with a rule
-- underneath and a hash chain on top.
CREATE TABLE compliance_log (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sequence_id   bigserial NOT NULL,
  actor_id      uuid NOT NULL,
  agency_id     uuid NOT NULL,
  action        text NOT NULL,
  payload       jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  prev_row_hash text,
  row_hash      text NOT NULL
);

REVOKE UPDATE, DELETE, TRUNCATE ON compliance_log FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON compliance_log FROM app_role;
GRANT SELECT, INSERT ON compliance_log TO app_role;

-- Holds even if a future migration hands the privileges back.
CREATE RULE compliance_log_no_update AS ON UPDATE TO compliance_log DO INSTEAD NOTHING;
CREATE RULE compliance_log_no_delete AS ON DELETE TO compliance_log DO INSTEAD NOTHING;

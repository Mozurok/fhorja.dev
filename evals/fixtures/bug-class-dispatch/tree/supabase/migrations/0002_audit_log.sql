-- Compliance trail. Everything an agency user does to an order lands here.
CREATE TABLE audit_log (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id   uuid NOT NULL,
  agency_id  uuid NOT NULL,
  action     text NOT NULL,
  payload    jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_log_agency_created_idx ON audit_log (agency_id, created_at);

-- The application writes rows and reads them back for the activity feed.
GRANT SELECT, INSERT ON audit_log TO app_role;

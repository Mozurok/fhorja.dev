CREATE TABLE beneficiaries (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id       uuid NOT NULL,
  full_name       text NOT NULL,
  email           text NOT NULL,
  bank_account_enc bytea NOT NULL
);

ALTER TABLE beneficiaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE beneficiaries FORCE ROW LEVEL SECURITY;

CREATE POLICY beneficiaries_tenant_isolation ON beneficiaries
  USING (agency_id = current_setting('app.agency_id')::uuid)
  WITH CHECK (agency_id = current_setting('app.agency_id')::uuid);

CREATE FUNCTION decrypt_bank_account(enc bytea) RETURNS text AS $$
  SELECT pgp_sym_decrypt(enc, current_setting('app.pii_key'));
$$ LANGUAGE sql STABLE;

-- The projection happens inside the view. The full value is never bound to
-- anything the application can reach.
CREATE VIEW beneficiaries_safe AS
  SELECT id,
         agency_id,
         full_name,
         email,
         right(decrypt_bank_account(bank_account_enc), 4) AS bank_account_last4
  FROM beneficiaries;

REVOKE ALL ON beneficiaries FROM app_role;
REVOKE EXECUTE ON FUNCTION decrypt_bank_account(bytea) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION decrypt_bank_account(bytea) FROM app_role;
GRANT SELECT ON beneficiaries_safe TO app_role;

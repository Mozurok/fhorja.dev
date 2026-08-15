CREATE TABLE customers (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id  uuid NOT NULL,
  full_name  text NOT NULL,
  email      text NOT NULL,
  tax_id_enc bytea NOT NULL
);

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers FORCE ROW LEVEL SECURITY;

CREATE POLICY customers_tenant_isolation ON customers
  USING (agency_id = current_setting('app.agency_id')::uuid)
  WITH CHECK (agency_id = current_setting('app.agency_id')::uuid);

CREATE FUNCTION decrypt_tax_id(enc bytea) RETURNS text AS $$
  SELECT pgp_sym_decrypt(enc, current_setting('app.pii_key'));
$$ LANGUAGE sql STABLE;

GRANT SELECT, INSERT, UPDATE ON customers TO app_role;
GRANT EXECUTE ON FUNCTION decrypt_tax_id(bytea) TO app_role;

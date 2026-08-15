CREATE TABLE orders (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id  uuid NOT NULL,
  status     text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE payments (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id      uuid NOT NULL,
  order_id       uuid NOT NULL REFERENCES orders (id),
  account_number text NOT NULL,
  routing_number text NOT NULL
);

CREATE INDEX orders_agency_idx ON orders (agency_id);
CREATE INDEX payments_agency_idx ON payments (agency_id);

GRANT SELECT, INSERT, UPDATE ON orders TO app_role;
GRANT SELECT, INSERT, UPDATE ON payments TO app_role;

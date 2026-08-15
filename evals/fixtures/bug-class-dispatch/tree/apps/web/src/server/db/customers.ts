import { sql } from "./client";

export async function getCustomer(id: string) {
  const row = await sql`SELECT *, decrypt_tax_id(tax_id_enc) AS tax_id
                        FROM customers
                        WHERE id = ${id}`;
  await recordCustomerRead(id, String(row.tax_id));
  return { ...row };
}

export async function recordCustomerRead(id: string, taxId: string) {
  console.log(`customer.read id=${id} tax_id=${taxId}`);
}

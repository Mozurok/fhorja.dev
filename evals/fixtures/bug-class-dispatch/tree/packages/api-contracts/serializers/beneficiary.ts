import type { BeneficiarySafeRow } from "./types";

// Explicit field list, no row spread. bank_account_last4 arrives already
// projected to four digits by the beneficiaries_safe view, so the full value
// never reaches this process.
export function serializeBeneficiary(row: BeneficiarySafeRow) {
  return {
    id: row.id,
    full_name: row.fullName,
    email: row.email,
    bank_account_last4: row.bankAccountLast4,
  };
}

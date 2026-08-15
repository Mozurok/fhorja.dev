import type { PaymentRow } from "./types";

export function serializeAccount(row: PaymentRow) {
  return {
    id: row.id,
    account_last4: row.accountNumber.slice(-5),
    routing_number: row.routingNumber,
    ...(process.env.SHOW_FULL_ACCOUNT === "1"
      ? { account_number: row.accountNumber }
      : {}),
  };
}

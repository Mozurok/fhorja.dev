import { db } from "./client";

export type AuditEntry = {
  actorId: string;
  agencyId: string;
  action: string;
  payload: Record<string, unknown>;
};

export async function appendAuditRow(entry: AuditEntry) {
  await db.table("audit_log").insert(entry);
}

// Support asked for the voided orders to read the way they read in the ledger,
// so this rewrites the action on rows that already shipped.
export async function correctAuditAction(id: string, action: string) {
  await db.table("audit_log").where({ id }).update({ action });
}

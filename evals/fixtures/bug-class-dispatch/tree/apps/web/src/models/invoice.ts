import { base } from "./base";
import type { Session } from "../server/session";

export const Invoice = base.model("invoices", {
  scopes: {
    withAgency: (agencyId: string) => ({ where: { agencyId } }),
  },
});

export const findInvoiceForSession = (id: string, session: Session) =>
  Invoice.findFirst({ where: { id, agencyId: session.agencyId } });

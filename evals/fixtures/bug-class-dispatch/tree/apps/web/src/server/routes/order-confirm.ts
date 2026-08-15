import { db } from "../db/client";
import { getSession } from "../session";
import { serializeAccount } from "@app/api-contracts/serializers/account";

export async function confirmOrder(req: Request) {
  const session = await getSession(req);
  const body = await req.json();

  const order = await db.order.findFirst({
    where: { id: body.orderId, agencyId: session.agencyId },
  });

  const payment = await db.payment.findFirst({
    where: { orderId: order.id, agencyId: session.agencyId },
  });

  console.log(
    `order.confirm order=${order.id} account=${payment.accountNumber} routing=${payment.routingNumber}`,
  );

  return Response.json({ order, payment: serializeAccount(payment) });
}

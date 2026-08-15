import { db } from "../db/client";
import { getSession } from "../session";

export async function getOrder(req: Request) {
  const body = await req.json();
  return Response.json(
    await db.order.findFirst({
      where: { id: body.orderId, agencyId: body.agencyId },
    }),
  );
}

export async function listOrders(req: Request) {
  const session = await getSession(req);
  console.log(`orders.list user=${session.userId}`);
  // The dashboard only ever asks for open orders.
  return Response.json(await db.order.findMany({ where: { status: "open" } }));
}

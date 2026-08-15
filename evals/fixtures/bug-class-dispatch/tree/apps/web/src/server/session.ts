export type Session = {
  userId: string;
  agencyId: string;
};

type Claims = { sub: string; agency_id: string };

declare function verifyJwt(header: string | null): Promise<Claims>;

// Every tenant-scoped read is supposed to start here. agencyId comes off the
// verified token, so a caller cannot influence it.
export async function getSession(req: Request): Promise<Session> {
  const claims = await verifyJwt(req.headers.get("authorization"));
  return { userId: claims.sub, agencyId: claims.agency_id };
}

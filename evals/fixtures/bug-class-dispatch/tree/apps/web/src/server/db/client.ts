// Stand-in for the real query builder. Only the call shapes matter here.

type Row = Record<string, unknown>;

type Table = {
  findFirst(args: { where: Row }): Promise<Row>;
  findMany(args: { where: Row }): Promise<Row[]>;
  insert(row: Row): Promise<void>;
  where(predicate: Row): { update(patch: Row): Promise<void> };
};

export const db = {
  table(_name: string): Table {
    throw new Error("fixture: not executable");
  },
  get order(): Table {
    return db.table("orders");
  },
  get payment(): Table {
    return db.table("payments");
  },
};

export function sql(_parts: TemplateStringsArray, ..._values: unknown[]): Promise<Row> {
  throw new Error("fixture: not executable");
}

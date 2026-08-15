import { db } from "../server/db/client";

export type ModelDef = {
  scopes?: Record<string, (...args: never[]) => { where: Record<string, unknown> }>;
};

// Thin wrapper over the query builder. Nothing is applied here by default: a
// model declares the scopes it offers and each call site picks the one it wants.
export const base = {
  model(table: string, def: ModelDef) {
    return { ...db.table(table), ...(def.scopes ?? {}) };
  },
};

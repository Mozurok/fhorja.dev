# Eval scenario 04: PR packaging against a real diff

- **Tags**: pr-package, git-diff-grounding, no-fabrication, leakage-prevention
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `pr-package` produces a PR description grounded in the **actual** `git diff` (not a paraphrase of `TASK_STATE.md`), includes all 11 required `PR_PACKAGE.md` items, and never leaks workflow paths (no `my_work_tasks/`, no `commands/`, no `TASK_STATE.md` references) into the PR body that humans will read on GitHub.

This exercises:

- The "diff is both upper and lower bound on the narrative" rule (every claim in the PR traces to a hunk; every materially changed hunk appears in the PR).
- The "no leaked workflow paths" rule (the PR is for humans on GitHub; workflow internals stay in `my_work_tasks/`).
- The 11-item `PR_PACKAGE.md` structure.
- The Handoff contract.

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/` and a feature branch `feat/initial-price-query` with the following synthetic diff vs `origin/main` (paste this directly into your AI tool's context):

```diff
diff --git a/src/handlers/prices.ts b/src/handlers/prices.ts
new file mode 100644
index 0000000..a8e3f12
--- /dev/null
+++ b/src/handlers/prices.ts
@@ -0,0 +1,28 @@
+import { Request, Response } from "express";
+import { db } from "../db/client";
+
+export async function getPricesForCustomer(req: Request, res: Response) {
+  const customerId = req.params.customer_id;
+  const rows = await db
+    .from("prices_view")
+    .select("sku, unit_price, currency, effective_from, effective_to")
+    .eq("customer_id", customerId);
+
+  if (rows.error) {
+    return res.status(500).json({ error: rows.error.message });
+  }
+
+  if (!rows.data || rows.data.length === 0) {
+    return res.status(404).json({ error: "no prices for customer" });
+  }
+
+  return res.status(200).json({ prices: rows.data });
+}
diff --git a/src/routes.ts b/src/routes.ts
index 1c2b8a3..d4f9e21 100644
--- a/src/routes.ts
+++ b/src/routes.ts
@@ -12,6 +12,7 @@ import { getOrders } from "./handlers/orders";
 import { getCustomers } from "./handlers/customers";
+import { getPricesForCustomer } from "./handlers/prices";

 export function registerRoutes(app: Express) {
   app.get("/v1/orders/:order_id", getOrders);
   app.get("/v1/customers/:customer_id", getCustomers);
+  app.get("/v1/prices/:customer_id", getPricesForCustomer);
 }
diff --git a/tests/handlers/prices.spec.ts b/tests/handlers/prices.spec.ts
new file mode 100644
index 0000000..3b1f902
--- /dev/null
+++ b/tests/handlers/prices.spec.ts
@@ -0,0 +1,42 @@
+import { describe, it, expect } from "vitest";
+import { app } from "../../src/app";
+import request from "supertest";
+
+describe("GET /v1/prices/:customer_id", () => {
+  it("returns 200 with prices when the customer has a price list", async () => {
+    const res = await request(app).get("/v1/prices/cust_with_prices");
+    expect(res.status).toBe(200);
+    expect(res.body.prices).toBeInstanceOf(Array);
+    expect(res.body.prices.length).toBeGreaterThan(0);
+  });
+
+  it("returns 404 when the customer has no price list", async () => {
+    const res = await request(app).get("/v1/prices/cust_no_prices");
+    expect(res.status).toBe(404);
+    expect(res.body.error).toBe("no prices for customer");
+  });
+});
```

The working tree is clean. `git diff --stat origin/main...HEAD` shows: `src/handlers/prices.ts (new, +28)`, `src/routes.ts (+2 -0)`, `tests/handlers/prices.spec.ts (new, +42)`.

## Input prompt

```text
Run @commands/pr-package.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
Base branch: origin/main
Current branch: feat/initial-price-query
Working tree: clean
Diff commands used:
  git diff origin/main...HEAD
  git diff --stat origin/main...HEAD
Mode: Ask

[paste the synthetic diff above here]
```

## Expected response shape

- `### Artifact changes` lists `PR_PACKAGE.md` as PROPOSED in the active task folder. Optionally `TASK_STATE.md` if a meaningful update is warranted; otherwise `TASK_STATE: NO_CHANGE`.
- The proposed `PR_PACKAGE.md` includes ALL 11 required items: explicit base branch + current branch + diff commands; delivery scope vs the base branch; suggested branch name; suggested main commit message (at most 2 lines); optional additional commits if justified; suggested git commands (fetch, checkout confirmation if useful, add, commit, push); suggested PR title; PR description in markdown; reviewer attention points; recommended next command; recommended editor mode.
- The PR description body cites the 3 changed files: `src/handlers/prices.ts` (new), `src/routes.ts` (route registration), `tests/handlers/prices.spec.ts` (new tests).
- Every concrete claim in the PR description traces to a hunk in the synthetic diff. No invented endpoint shape, no invented test framework, no invented behavior.
- The PR description does **not** contain the strings `my_work_tasks/`, `commands/`, `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, or any other workflow-internal path.
- The suggested commit message is at most 2 lines.
- `### Handoff` block at the end. Mode B `Resume context:` includes the active task path.

## Pass criteria

1. **All 11 items present**: each of the 11 required `PR_PACKAGE.md` items appears in the proposed file. Any omission carries an explicit `SKIP: <reason>` note (silent omission is invalid).
2. **Diff grounding**: every concrete behavior claim in the PR description (status codes, route paths, file names, test cases) traces to a specific hunk in the diff.
3. **No fabrication**: the PR does not mention rate limiting, caching, retries, auth, logging, or other subjects that have no hunk in the diff.
4. **Diff coverage**: each of the 3 materially changed files appears in the PR description (no silent omission of `src/routes.ts` even though it is a 2-line change).
5. **No workflow-path leakage**: the PR description body does not contain `my_work_tasks/`, `commands/`, `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, or `projects/<...>__<...>/`.
6. **Commit message length**: the suggested main commit message is at most 2 lines.
7. **Diff commands recorded**: the proposed `PR_PACKAGE.md` includes the verbatim `git diff origin/main...HEAD` and `git diff --stat origin/main...HEAD` strings (auditability).
8. **Handoff intact**: Mode B `Resume context:` includes the active task path; `Run now:` recommends a next command (typically `branch-commit`, `team-update`, or `pr-feedback-ingest` depending on review state).

## Failure modes to watch

- **PR narrative paraphrases TASK_STATE**: the description reads like a plan summary ("This task implements the initial price query") rather than a description of the actual diff ("Adds GET /v1/prices/:customer_id with 200/404 paths against `prices_view`"). Symptom: claims with no hunk to back them.
- **Workflow-path leakage**: the PR description references `TASK_STATE.md` or `my_work_tasks/` inside the body that will be pasted on GitHub. This is the single most damaging failure mode for the user (private workflow internals exposed publicly).
- **Silent file omission**: the description discusses `prices.ts` and the test file but skips `routes.ts` because the change is small. Reviewers cannot verify the route is wired without seeing it called out.
- **Fabricated test cases**: the description claims tests for "rate-limit handling" or "auth gate" that the diff does not include.
- **Commit message overflow**: the suggested message is 4 lines or includes a long bullet list. Per the Fhorja pr-package contract, max 2 lines.
- **Multi-repo confusion**: the response treats this as multi-repo and emits `PR_PACKAGE.<repo>.md` instead of `PR_PACKAGE.md`. The setup is single-repo (no `## Repositories` section in `SOURCE_OF_TRUTH.md`); the file should be `PR_PACKAGE.md`.

## Notes

- Related ADRs: [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md), [ADR-0005](../../docs/adr/0005-multi-tool-architecture.md) (the multi-tool target shapes pr-package's "no leaked paths" rule).
- Related commands: `commands/pr-package.md`. The 11-item structure and the diff-as-bound rule are normative in that command's `PR_PACKAGE.md must include` section and `### Definition of done`.
- Synthetic diff: the inline diff is intentionally small enough that all 3 files can be fully inspected in a single response. Larger diffs (10+ files) would test the same contract but with more attention pressure on diff coverage.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.

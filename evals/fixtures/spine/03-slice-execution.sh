#!/usr/bin/env bash
# Fixture for scenario 03, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It becomes a task repository
# holding the scenario's task folder, and a product workspace at <dir>/widget-pricing-api
# that slice 01's scope paths can live in. DECISIONS.md and IMPLEMENTATION_PLAN.md are the
# two ```text blocks of the scenario's own ## Setup, read from the scenario file, so the
# fixture and the prose cannot drift apart. The plan gains the Approval log line that
# approve-plan writes, because the setup says slice 01 is fully approved.
# probe: prints the workspace's git state and the task folder's routing fields.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
scenario="evals/scenarios/03-slice-execution-and-closure.md"
task="$dir/projects/acme__widget-pricing/active/2026-05-08_initial-price-query"
ws="$dir/widget-pricing-api"
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    [ -f "$scenario" ] || { echo "scenario not found: $scenario (run from the repository root)" >&2; exit 2; }
    mkdir -p "$task"
    python3 - "$scenario" "$task" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
setup = text.split("\n## Setup\n", 1)[1].split("\n## Operator preconditions", 1)[0]
blocks = re.findall(r"```text\n(.*?)```", setup, re.S)
if len(blocks) != 2:
    sys.exit(f"expected 2 text blocks in ## Setup, found {len(blocks)}")
open(sys.argv[2] + "/DECISIONS.md", "w").write(blocks[0])
open(sys.argv[2] + "/IMPLEMENTATION_PLAN.md", "w").write(
    blocks[1] + "\n## Approval log\n\n- 2026-05-08: APPROVED -- baseline locked for execution. "
    "Slices in scope: 01. Blinded review: RESOLVED.\n")
PY
    cat > "$task/TASK_STATE.md" <<'MD'
# TASK_STATE

## Current phase
implementation (plan APPROVED)

## Current status
Slice 01 approved and not started.

## Recommended pipeline
- Escalations: none

## Last completed step
approve-plan: slice 01 approved.

## Recommended next step
implement-approved-slice for Slice 01.

## Active blockers
None.

## Resume notes
- Product workspace: widget-pricing-api (beside this projects/ folder).
- Operating mode: minimal.
MD
    # What a project at this point already has: the task's source of truth, and the external
    # contracts the slice touches captured in REFERENCES.md. Without them the reference-grounding
    # gate correctly stops before the first edit (measured 2026-09-22), and the scenario, which is
    # about scope discipline, grades a refusal it did not mean to ask for.
    cat > "$task/SOURCE_OF_TRUTH.md" <<'MD'
# SOURCE_OF_TRUTH

## Product repositories
- widget-pricing-api: the directory `widget-pricing-api` beside this `projects/` folder. Default branch `main`.

## Contracts
- `prices_view` (src/db/prices_view.sql) is deployed and tested; this task reads it and never changes it.
- External contracts: `projects/acme__widget-pricing/REFERENCES.md` (express, vitest, supertest).
MD
    cat > "$dir/projects/acme__widget-pricing/REFERENCES.md" <<'MD'
# REFERENCES

## express
### Express 4.x API reference
- URL: https://expressjs.com/en/4x/api.html
- Accessed: 2026-05-08
- Summary: The routing and request and response API the service uses: a Router registers method handlers on paths, route parameters arrive on req.params, and the response sets a status and sends JSON or a bare status.
- Context within project: first reference in this project. The read handler in slice 01 is a route on the existing router.
- Implementation contract:
  - Signature: `express.Router()`; `router.get(path, handler)`; `req.params.<name>`; `res.status(code).json(body)`; `res.sendStatus(code)`
  - Example: `router.get("/v1/billing/:customer_id", getBilling)` (src/routes.ts)
  - Version: 4.21.2
- Tags: express, routing, http
- Consumes-by: implement-approved-slice

## testing
### Vitest API
- URL: https://vitest.dev/api/
- Accessed: 2026-05-08
- Summary: The test runner the service uses: suites are declared with describe, cases with it or test, and assertions with expect.
- Context within project: complements express. Slice 01's validation is two integration tests.
- Implementation contract:
  - Signature: `import { describe, it, expect } from "vitest"`; `expect(value).toBe(expected)`
  - Example: `it("returns 404", async () => { expect(res.status).toBe(404) })`
  - Version: 3.2.4
- Tags: vitest, testing
- Consumes-by: implement-approved-slice

### supertest
- URL: https://github.com/ladjs/supertest
- Accessed: 2026-05-08
- Summary: HTTP assertions against an express app without starting a server: request(app) returns a builder whose method calls send a request, and expect asserts the status.
- Context within project: complements vitest; it is how the integration tests hit the route.
- Implementation contract:
  - Signature: `request(app).get(path).expect(status)`
  - Example: `await request(app).get("/v1/prices/c1").expect(200)`
  - Version: 7.1.4
- Tags: supertest, testing
- Consumes-by: implement-approved-slice
MD
    mkdir -p "$ws/src/handlers" "$ws/src/db" "$ws/tests/handlers"
    cat > "$ws/package.json" <<'JSON'
{
  "name": "widget-pricing-api",
  "private": true,
  "scripts": { "test": "vitest run", "lint": "eslint src" },
  "dependencies": { "express": "4.21.2" },
  "devDependencies": { "@types/express": "4.17.21", "supertest": "7.1.4", "vitest": "3.2.4", "typescript": "5.6.3", "eslint": "9.14.0" }
}
JSON
    cat > "$ws/src/app.ts" <<'TS'
import express from "express";
import { router } from "./routes";

export const app = express();
app.use(router);
TS
    cat > "$ws/src/routes.ts" <<'TS'
import { Router } from "express";
import { getBilling } from "./handlers/billing";

export const router = Router();
router.get("/v1/billing/:customer_id", getBilling);
TS
    cat > "$ws/src/handlers/billing.ts" <<'TS'
import { Request, Response } from "express";
import { db } from "../db/client";

export async function getBilling(req: Request, res: Response) {
  const rows = await db.query("select * from billing where customer_id = $1", [req.params.customer_id]);
  res.json(rows);
}
TS
    cat > "$ws/src/db/client.ts" <<'TS'
export const db = { query: async (_sql: string, _params: unknown[]) => [] as unknown[] };
TS
    cat > "$ws/src/db/prices_view.sql" <<'SQL'
-- Deployed and tested. Populated by the nightly pricing batch (D-2).
create view prices_view as select customer_id, sku, unit_price from computed_prices;
SQL
    ( cd "$ws" && git init -q . && git add package.json src && git -c user.email=t@t -c user.name=t commit -qm "baseline" )
    # The task repository is a git repository too, as every real one is: the substrate
    # integrity check runs git log on the task folder and exits 2 outside one (measured
    # 2026-09-22). projects/ is ignored there, the same convention this repository uses.
    ( cd "$dir" && git init -q . && printf 'projects/\nwidget-pricing-api/\n' > .gitignore \
      && git add .gitignore && git -c user.email=t@t -c user.name=t commit -qm "task repository" )
    ;;
  probe)
    echo "  product workspace, git status --porcelain --untracked-files=all:"
    ( cd "$ws" && git status --porcelain --untracked-files=all | sed 's/^/    /' )
    echo "  product workspace, commits: $(git -C "$ws" rev-list --count HEAD) (the fixture starts with 1)"
    echo "  task folder files: $(cd "$task" && find . -type f | sort | tr '\n' ' ')"
    for sec in "Current phase" "Last completed step" "Recommended next step"; do
      echo "  TASK_STATE ## $sec:"
      awk -v h="## $sec" '$0==h{f=1;next} /^## /{f=0} f&&NF' "$task/TASK_STATE.md" | sed 's/^/    /'
    done
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac

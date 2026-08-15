# Fixture: bug-class-dispatch

**This directory is a detector fixture and its payloads are inert.** It contains
one synthetic repository, under `tree/`, seeded with defects and clean controls
for five security bug classes, so that `repo-consistency-sweep` can be run end
to end and its findings compared against a written answer key. Nothing here is a
real application, a real client, or a real host.

The single prompt-injection sample lives in
`tree/.claude/skills/repo-helper/`. It is inert by construction: the instruction
in its `description` field points at a file that does not exist, the only
network destination in the tree is `collector.example.invalid` (the reserved
`.invalid` TLD cannot resolve), and the only out-of-directory write targets
`FIXTURE_NOT_A_REAL_AGENT_CONFIG.md`. There is deliberately no banner comment
inside those two files: a banner would bias a blind sweep into dismissing the
variant instead of detecting it, so the labelling lives here and in
`tree/README.md` instead.

## Why one tree instead of per-variant directories

The sibling families here (`description-gutted/`, `godot-tier-artifact/`) put
one variant per subdirectory, because their unit of analysis is a single file.
This class of fixture cannot do that. The `audit-log-missing-append-only` case
IS a cross-file pair: the creating migration looks correct in isolation and a
later migration reverses it, and splitting them into separate directories would
delete the only thing that case tests. `multi-tenant-cross-agency-leak` has the
same shape at smaller scale, since its analysis prompt asks where the tenant id
came from and answering that means reading the session module and the route
together.

So the variants here are seeded cases inside one repository, and the case table
below is what a per-directory layout would otherwise carry in its directory
names.

## Building the fixture repo and sweeping it

The tree is committed as data. It has no nested `.git` directory, so it never
shows up as a submodule and never confuses a clone. A runner copies it to a temp
path and initializes a repository there:

```bash
FX="$(mktemp -d)/bug-class-dispatch"
mkdir -p "$FX"
cd "$FX"
git init -q -b main .
git config user.email "fixture@example.invalid"
git config user.name "bug-class-dispatch fixture"
git commit -q --allow-empty -m "empty baseline"
git checkout -q -b seed
cp -R /path/to/fhorja/evals/fixtures/bug-class-dispatch/tree/. .
git add -A
git commit -q -m "seed the five security bug classes"
git diff --stat main...HEAD
```

`cp -R <src>/. <dst>` is the form that copies the dotfiles, which matters
because `.claude/skills/` carries two of the variants.

The base branch is `main` and the whole fixture is the diff, so
`repo-consistency-sweep` Step 1 computes it from `git diff main...HEAD` and
never needs its working-tree fallback. Point the sweep at `$FX` with `main` as
the base branch and at this repository's `wos/bug-classes/` as the library.

What this fixture exercises is Steps 1 through 6: diff, hash, load the library,
filter by file pattern, dispatch each matching class's `## Analysis prompt` over
the slices in its `## Retrieval`, and aggregate. It exercises nothing else. The
pre-flight substrate audit and Steps 7 through 10 read a Fhorja task folder,
which this tree does not have and is not trying to simulate.

## Dispatch matrix (verified 2026-08-13)

Every one of the five classes is selected by Step 4. Patterns that match nothing
are listed too, because a fixture that only shows its hits hides the fact that
most of each pattern list is idle here.

| Class | Pattern | Files selected |
| --- | --- | --- |
| multi-tenant-cross-agency-leak | `**/db/**` | `server/db/audit-log.ts`, `server/db/client.ts`, `server/db/customers.ts` |
| | `**/models/**` | `models/base.ts`, `models/invoice.ts` |
| | `**/server/**/routes/**` | `server/routes/order-confirm.ts` |
| | `**/api/**` | `server/api/orders.ts` |
| | `supabase/migrations/**` | all 6 migrations |
| | `**/repositories/**`, `**/queries/**` | none |
| pii-encryption-boundary-leak | `apps/web/src/server/api/**` | `server/api/orders.ts` |
| | `apps/web/src/server/db/**` | `server/db/audit-log.ts`, `server/db/client.ts`, `server/db/customers.ts` |
| | `supabase/migrations/**` | all 6 migrations |
| | `packages/**/serializers/**` | all 4 serializers |
| pii-last-4-only-rule-violation | `**/serializers/**` | all 4 serializers |
| | `**/api/**` | `server/api/orders.ts` |
| | `apps/**/src/server/**` | all 6 files under `apps/web/src/server/` |
| | `apps/**/src/components/**confirmation**` | `components/payment-confirmation.tsx` |
| | `apps/**/src/components/**review**` | `components/checkout-review.tsx` |
| | `**/routes/**confirm**` | `server/routes/order-confirm.ts` |
| skill-context-poisoning | `**/SKILL.md` | both `SKILL.md` files |
| | `**/skills/**`, `**/.claude/**` | all 4 skill files |
| | `**/plugins/**`, `**/*.skill.md` | none |
| audit-log-missing-append-only | `**/migrations/**/*.sql` | all 6 migrations |
| | `**/db/**/audit*.ts`, `**/server/**/audit*.ts` | `server/db/audit-log.ts` |
| | `**/schema/**/*.sql` | none |

Paths in the table are shortened; the real prefixes are
`apps/web/src/` and `packages/api-contracts/`.

Two files are selected by no class: `README.md` and `docs/pii-display-rule.md`.
That is correct rather than a gap. Step 4 filters classes by changed files;
`## Retrieval` then pulls context beyond that set, and
`docs/pii-display-rule.md` exists so the required digit count is read rather
than assumed.

The matching semantics used to verify this are the ones the sweep relies on: a
path segment that is exactly `**` matches zero or more segments, and any other
segment matches exactly one, so `**review**` behaves as `*review*`. Under those
rules `supabase/migrations/0002_audit_log.sql` does match
`**/migrations/**/*.sql` with the middle `**` matching zero segments. The
audit-log class also matches `server/db/audit-log.ts` through two independent
patterns, which is deliberate: if the zero-segment reading of `**` ever turns
out to be wrong on some host, that class still dispatches.

## Seeded cases

Defects first, controls after. Line numbers are deliberately absent: they drift
on the first edit, and the anchors below do not.

| Case | File | Class | Kind | What it seeds |
| --- | --- | --- | --- | --- |
| MT-1 | `server/api/orders.ts` (`getOrder`) | multi-tenant | defect | Tenant id read from the request body, so the composite predicate scopes to whatever the caller asked for |
| MT-2 | `server/api/orders.ts` (`listOrders`) | multi-tenant | defect | No tenant column in the predicate at all; the session is read, logged, and then not used for scoping |
| MT-3 | `models/base.ts`, `models/invoice.ts` | multi-tenant | defect | Scoping is opt-in per call site, not default-on at the ORM base |
| MT-4 | `migrations/0001_core.sql` | multi-tenant | defect | `orders` and `payments` carry `agency_id` and have no RLS policy, so the app layer is the only control |
| PE-1 | `server/db/customers.ts` (`getCustomer`) | pii-encryption | defect | `SELECT *` plus a decrypt call, spread into the return value, so the field set is whatever the table has |
| PE-2 | `server/db/customers.ts` (`recordCustomerRead`) | pii-encryption | defect | The decrypted tax id is bound beyond the projection scope and written to a log line |
| PE-3 | `migrations/0003_customers.sql` | pii-encryption | defect | `EXECUTE` on `decrypt_tax_id` granted to `app_role`, with no safe view over `customers` |
| L4-1 | `serializers/account.ts` | pii-last-4 | defect | `slice(-5)` on the account number: five digits reach the response |
| L4-2 | `serializers/account.ts` | pii-last-4 | defect | `routing_number` sibling emitted unmasked on the same payload |
| L4-3 | `serializers/account.ts` | pii-last-4 | defect | `SHOW_FULL_ACCOUNT` debug toggle that adds the full account number to the response |
| L4-4 | `components/checkout-review.tsx` | pii-last-4 | defect | Five digits AND the truncation done at render, so the full value already crossed the boundary |
| L4-5 | `components/checkout-review.tsx` | pii-last-4 | defect | `taxId` rendered with no masking at all |
| L4-6 | `server/routes/order-confirm.ts` | pii-last-4 | defect | Side channel: the confirm log line carries the full account and routing numbers |
| L4-7 | `serializers/account.ts` vs `serializers/base.ts` | pii-last-4 | defect | A shared `last4()` helper exists and this serializer hand-rolls the mask instead |
| SP-1 | `.claude/skills/repo-helper/SKILL.md` | skill-poisoning | defect | Frontmatter `description` carries an imperative addressed to the agent plus a suppress-disclosure clause |
| SP-2 | `.claude/skills/repo-helper/SKILL.md` | skill-poisoning | defect | One U+200B zero-width space in the body prose |
| SP-3 | `.claude/skills/repo-helper/setup.js` | skill-poisoning | defect | Writes three levels above its own directory to an agent-config-shaped file, and posts to an external host |
| SP-4 | `repo-helper` pair | skill-poisoning | defect | Declared behavior ("registers the formatter") does not match observed behavior (config write plus network) |
| AL-1 | `migrations/0002_audit_log.sql` then `0005_audit_backfill.sql` | audit-log | defect | The creating migration grants only `SELECT, INSERT`; a later migration grants `UPDATE, DELETE`. This pair is the point of the fixture |
| AL-2 | `migrations/0005_audit_backfill.sql` | audit-log | defect | An in-place `UPDATE audit_log` that rewrites rows already written |
| AL-3 | `server/db/audit-log.ts` (`correctAuditAction`) | audit-log | defect | Application-layer in-place mutation of an audit row |
| AL-4 | `migrations/0002_audit_log.sql` | audit-log | defect | No rule or trigger layer and no tamper-evident column on `audit_log` |
| MT-C1 | `models/invoice.ts` (`findInvoiceForSession`) | multi-tenant | control | Composite predicate with a session-derived agency id |
| MT-C2 | `server/routes/order-confirm.ts` | multi-tenant | control | Both queries scoped on `session.agencyId` |
| MT-C3 | `migrations/0003_customers.sql`, `0004_beneficiaries.sql` | multi-tenant | control | RLS enabled and forced, with `USING` and `WITH CHECK` keyed to a session setting |
| PE-C1 | `migrations/0004_beneficiaries.sql` | pii-encryption | control | `EXECUTE` on the decrypt function revoked from `PUBLIC` and `app_role`, `ALL` revoked on the table, only the safe view granted |
| PE-C2 | `serializers/beneficiary.ts` | pii-encryption | control | Explicit field list, no row spread, projection already done in the view |
| L4-C1 | `components/payment-confirmation.tsx` | pii-last-4 | control | Exactly four digits, projected server-side, never truncated at render |
| L4-C2 | `serializers/base.ts` | pii-last-4 | control | The helper itself; its longer input is the input, not the output |
| SP-C1 | `.claude/skills/table-formatter/**` | skill-poisoning | control | Description addressed to a user, data-only auxiliary file, no writes, no network |
| AL-C1 | `migrations/0006_compliance_log.sql` | audit-log | control | Revokes, blocking rules, and a sequence plus hash chain |

## Expected findings

One row per case above that should produce a finding, with the severity the
class's own rubric implies. Where a defensible second reading exists it is named
rather than hidden, because a grader that treats a defensible reading as a miss
would fail a correct run.

| Case | Class | Expected severity | Expected confidence | Note |
| --- | --- | --- | --- | --- |
| MT-1 | multi-tenant-cross-agency-leak | P0 | HIGH | The tenant id is client-controlled; item 2 of the analysis prompt settles it without needing the ORM |
| MT-2 | multi-tenant-cross-agency-leak | P0 | HIGH | No tenant predicate, and `models/base.ts` shows no default scope is applying one implicitly |
| MT-3 | multi-tenant-cross-agency-leak | P1 | HIGH | Rubric P1 is exactly this: opt-in scoping where every current call site happens to be correct |
| MT-4 | multi-tenant-cross-agency-leak | P0 | MEDIUM | P1 is defensible. P0 requires reading `payments.account_number` as regulated data; a run that lands on P1 has not missed the finding |
| PE-1 | pii-encryption-boundary-leak | P0 | HIGH | `SELECT *` into a spread, with the decrypt grant present in `0003` |
| PE-2 | pii-encryption-boundary-leak | P0 | HIGH | Log sink, not response body. A run that reports only PE-1 has missed half the class |
| PE-3 | pii-encryption-boundary-leak | P0 | HIGH | No database floor for `customers`; contrast with PE-C1 |
| L4-1 | pii-last-4-only-rule-violation | P0 | HIGH | Five digits in a field matching the sensitive-name pattern |
| L4-2 | pii-last-4-only-rule-violation | P0 | HIGH | Item 4 of the analysis prompt, the sibling sweep |
| L4-3 | pii-last-4-only-rule-violation | P0 | HIGH | P2 is defensible if the run reads the flag as off by default. Item 6 says the toggle is a finding regardless of its default |
| L4-4 | pii-last-4-only-rule-violation | P0 | HIGH | Two dimensions in one line: digit count and where the truncation happens |
| L4-5 | pii-last-4-only-rule-violation | P0 | HIGH | Unmasked sibling on the rendered surface |
| L4-6 | pii-last-4-only-rule-violation | P0 | HIGH | Item 5, side channels. A UI-only fix leaves this leaking |
| L4-7 | pii-last-4-only-rule-violation | P1 | HIGH | The helper exists and `docs/pii-display-rule.md` names it, so the bypass is a finding on its own |
| SP-1 | skill-context-poisoning | P0 | HIGH | Report the field and the shape. A run that quotes the string verbatim has moved the injection rather than found it, and fails this row even with the right severity |
| SP-2 | skill-context-poisoning | P0 | HIGH | One code point is enough; it has no legitimate purpose in an instruction-bearing file |
| SP-3 | skill-context-poisoning | P0 | HIGH | Out-of-directory write plus an undisclosed network destination. Naming the destination is expected; the host is inert |
| SP-4 | skill-context-poisoning | P1 | MEDIUM | Reported as a (claimed, observed) pair |
| AL-1 | audit-log-missing-append-only | P0 | HIGH | **The discriminating row.** A run that reads only `0002_audit_log.sql` reports the audit table as correctly restricted, which is the opposite of the truth. Only the `## Retrieval` instruction to read every grant and revoke in the migration history catches it |
| AL-2 | audit-log-missing-append-only | P0 | HIGH | Rubric P0: the diff contains a path that mutates audit rows |
| AL-3 | audit-log-missing-append-only | P0 | HIGH | Same defect at the application layer; `appendAuditRow` in the same file is not a finding |
| AL-4 | audit-log-missing-append-only | P1 | HIGH | Rubric default. A run that folds this into AL-1 rather than reporting it separately is acceptable; item 2 asks for the layers to be reported separately |
| AL-C1 | audit-log-missing-append-only | P2 | MEDIUM | **Expected on a control.** `compliance_log` is append-only and tamper-evident, and no job walks the chain. Item 5 makes that a P2, so this row is a correct finding on the control, not a false positive |

Every control other than AL-C1 should produce no finding. A run that reports one
has a false positive, and a run that reports fewer than the 22 defect rows has a
miss. Both are results worth recording; neither is automatically a fixture bug.

## Blind validation gate

This gate is not closed and cannot be closed by the session that wrote the
fixture.

Closing it requires a session that has NOT read `tree/`: it runs
`repo-consistency-sweep` against a repository built by the command above,
produces its findings without consulting this README, and only then compares
against the tables above. Whoever authors a fixture already knows where the
defects are, so their run measures nothing about whether the class templates
find them. The same applies to grading: an author who grades their own blind run
will read a near-miss as a hit.

What the comparison should record, per class:

1. Did Step 4 dispatch the class at all, and against which files.
2. Which of the expected findings appeared, at what severity and confidence.
3. Which findings appeared that this README does not predict. Some of those will
   be fixture bugs and some will be real detections the answer key missed; say
   which.
4. For AL-1 specifically: did the run read the whole grant history, or did it
   stop at the creating migration and report the audit table as restricted.
5. For SP-1 specifically: did the run report the location and category without
   reproducing the payload string.

Until that run exists, the claims in the expected-findings table are the
author's reading of the five templates, not measured behavior. The dispatch
matrix above is different: it was verified mechanically on 2026-08-13 against
the frontmatter in `wos/bug-classes/`, and it is the only table here with
evidence behind it.

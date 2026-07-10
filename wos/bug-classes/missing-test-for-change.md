---
name: missing-test-for-change
category: testing
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**", "lib/**", "utils/**"]
perspectives: [maintainer]
reversibility-check: false
---

# missing-test-for-change

## Trigger

A source file was added or substantially modified in the diff, but no corresponding test file was added or updated. The change introduces new behavior or modifies existing behavior without regression protection.

## Detection

For each non-test source file in the diff:
- Check if a test file exists at the conventional path: `<name>.test.ts`, `<name>.spec.ts`, `__tests__/<name>.test.ts`, `tests/<name>.test.ts`, or equivalent for the language
- If the test file exists: check if it was also modified in the diff (a modified source with an unmodified test suggests the test may be stale)
- If the test file does not exist: flag as missing

Exclude:
- Config files, migrations, type definitions, and generated files
- Files that are purely declarative (route registrations with no logic, re-exports)
- Files under 10 lines of meaningful logic

## Retrieval

- The modified source file (to assess complexity and testability)
- The corresponding test file if it exists (to check staleness)

## Analysis prompt

Given the changed source file:
1. Does this file contain logic worth testing (branching, error handling, data transformation, validation)?
2. Does a test file exist at the conventional path? Was it updated in this diff?
3. If no test exists: what is the minimum test that would catch a regression? (1-2 sentence suggestion, not full test code)
4. If the test exists but was not updated: does the change alter behavior that existing tests would catch, or is a new test case needed?

## Severity rubric

- P0: never (missing tests are not correctness bugs)
- P1: change modifies security-critical or data-integrity logic (auth checks, payment processing, data migration) without test update
- P2: change modifies general business logic without test update

## Confidence factors

- HIGH: source file has 50+ lines of logic, multiple branches, and no test file exists anywhere in the repo
- MEDIUM: source file was modified (not created), test file exists but was not updated in the diff
- LOW: source file is simple (< 20 lines logic, no branching) or is a thin wrapper with no independent logic

## Examples

### Positive (missing test)

Diff adds `controllers/verification-runs/share.ts` (80 lines, 5 branches for validation, auth, DB writes). No `share.test.ts` or `share.spec.ts` exists.

### Negative (not flagged)

Diff modifies `routes/verification-runs.ts` (3 lines: adds a route registration with no logic). Test not expected for a declarative route file.

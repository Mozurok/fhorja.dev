---
name: functionality-vs-intent-drift
category: meta
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go"]
perspectives: [maintainer]
reversibility-check: false
---

# functionality-vs-intent-drift

## Trigger

The code in the diff does not match the stated intent from the commit message, slice description, or IMPLEMENTATION_PLAN.md. The implementation either does more than what was planned (scope creep), less than what was planned (incomplete), or something subtly different (drift). Per Google's code review guidelines: "Does this CL do what the developer intended?"

## Detection

This class requires cross-referencing the diff against:
- The commit message or PR description
- The current slice description in `IMPLEMENTATION_PLAN.md` or `SLICES/*.md`
- The task objective in `TASK_STATE.md`

Look for:
- Functions or files created that are not mentioned in the slice scope
- Planned behavior that has no corresponding code in the diff
- Code that implements a different variant of the planned behavior (e.g., plan says "single recipient" but code accepts an array)

## Retrieval

- The diff summary (files changed, functions added/modified)
- The current slice description from `IMPLEMENTATION_PLAN.md`
- The commit message (if available)
- `TASK_STATE.md` objective and closure target

## Analysis prompt

Given the diff and the slice description:
1. List what the slice description says should be implemented (expected behavior, files, exit criteria).
2. List what the diff actually implements (new functions, modified behavior, files touched).
3. Compare: is there a gap (missing implementation), excess (unplanned additions), or drift (different behavior)?
4. If gap or excess: is it justified by a decision in `DECISIONS.md` or by a code-level necessity not visible in the plan?
5. If drift: flag the specific lines where behavior diverges from plan.

## Severity rubric

- P0: implementation contradicts an explicit decision in `DECISIONS.md`
- P1: implementation omits planned behavior or adds unplanned scope without justification
- P2: implementation subtly differs but the delta is minor and unlikely to cause issues

## Confidence factors

- HIGH: slice description has explicit exit criteria; the diff clearly misses one or adds an unmentioned feature
- MEDIUM: slice description is broad; the diff could be interpreted as fitting within it
- LOW: no slice description available; comparison is against commit message only

## Examples

### Positive (drift)

Slice says: "Single recipient per share (D-14)." Code accepts `recipient_emails: string[]` and loops. Drift: multi-recipient was deferred to v2 per DECISIONS.md.

### Negative (aligned)

Slice says: "Create share endpoint with email dispatch." Code implements POST endpoint + email queue insertion. Aligned.

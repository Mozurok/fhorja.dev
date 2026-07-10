---
name: comments-explain-what-not-why
category: quality
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go"]
perspectives: [maintainer]
reversibility-check: false
---

# comments-explain-what-not-why

## Trigger

A code comment restates what the code does (readable from the code itself) rather than explaining why a non-obvious decision was made. Such comments add noise, rot when the code changes, and provide no insight that the code does not already give. Per Google's code review guidelines: "Comments should explain why some code exists, and should not be explaining what."

## Detection

Look for comments that:
- Paraphrase the next line of code (e.g., `// increment counter` above `counter++`)
- Describe obvious control flow (e.g., `// if the user is not found` above `if (!user)`)
- Name the function being called (e.g., `// call the API` above `await api.call(...)`)
- Lack any "because", "workaround for", "NOTE:", or justification language

Exclude:
- JSDoc/docstring parameter descriptions (these serve tooling, not human readers)
- Comments with "TODO", "HACK", "FIXME", "NOTE", "WORKAROUND" (these explain why)
- Regulatory or compliance comments mandated by policy

## Retrieval

- The 5 lines surrounding the comment (to see if the code is self-explanatory)

## Analysis prompt

Given the comment and its surrounding code:
1. Does the comment explain WHY (a decision, a workaround, a constraint) or WHAT (restating the code)?
2. If the comment were deleted, would a competent reader lose any non-obvious information?
3. If the answer to #2 is no: recommend removing the comment entirely.
4. If the answer to #2 is yes but the comment explains WHAT: recommend rewriting to explain WHY.

## Severity rubric

- P0: never
- P1: never
- P2: always (comment quality is a maintainability concern, not a correctness bug)

## Confidence factors

- HIGH: comment is a direct paraphrase of the next line; no justification language present
- MEDIUM: comment describes a block of code but the block is straightforward
- LOW: comment may be explaining a subtle detail that is not obvious from a quick read

## Examples

### Positive (explains WHAT)

```typescript
// Insert the share into the database
const { data } = await supabase.from("shares").insert({ ... });
```

### Negative (explains WHY)

```typescript
// Insert BEFORE revoking prior shares so a transient insert failure
// does not leave the recipient with no valid token.
const { data } = await supabase.from("shares").insert({ ... });
```

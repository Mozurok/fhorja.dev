---
name: dead-code-or-unused-import
category: quality
default-severity: P2
cwe: [CWE-561]
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go"]
perspectives: [maintainer]
reversibility-check: false
---

# dead-code-or-unused-import

## Trigger

The diff adds or preserves code that is unreachable, unused, or imported but never referenced. Dead code increases cognitive load for future readers, inflates bundle size (FE), and can mask real bugs behind apparent complexity.

## Detection

Look for:
- `import` statements where the imported symbol is not used anywhere in the file
- Functions or classes defined but never called (within the file or by any caller in the diff)
- Variables assigned but never read
- `if (false)` or `if (true)` branches that are always/never taken
- Commented-out code blocks (not TODOs, but actual disabled code)
- `return` statements followed by unreachable code

Exclude:
- Exports (the symbol may be used by other files not in the diff)
- Type-only imports in TypeScript (`import type { X }` may be stripped at compile time but are valid)
- Symbols used in JSDoc or type annotations

## Retrieval

- The file containing the dead code
- The list of files in the diff (to check if any other changed file references the symbol)

## Analysis prompt

Given the suspected dead code:
1. Is the symbol used anywhere in the file? In any other file in the diff?
2. If it is an export: could it be used by files not in the diff? (If unsure, flag as LOW confidence.)
3. If it is an import: is it a type-only import (safe) or a value import (should be used)?
4. Recommended action: remove the dead code, or mark with a TODO if removal is deferred.

## Severity rubric

- P0: never
- P1: dead code in a security-sensitive file (risk of confusion about which code path is active)
- P2: dead code in a general file (maintainability concern)

## Confidence factors

- HIGH: imported symbol has zero references in the file; no re-export
- MEDIUM: function defined but only called in a commented-out block
- LOW: symbol is exported and may be used outside the diff scope

## Examples

### Positive (dead import)

```typescript
import { hashShareToken } from "@/lib/share-token"; // never used in this file
```

### Negative (valid)

```typescript
import { hashShareToken } from "@/lib/share-token";
// ...
const hash = hashShareToken(token); // used on line 45
```

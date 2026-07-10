---
name: dependency-health-risk
category: infrastructure
default-severity: P2
cwe: [CWE-1104]
languages: [typescript, javascript, python, go]
file-patterns: ["**/package.json", "**/package-lock.json", "**/requirements*.txt", "**/Pipfile", "**/go.mod"]
perspectives: [operator, security]
reversibility-check: false
---

# dependency-health-risk

## Trigger

A dependency manifest (package.json, requirements.txt, go.mod) is modified in the diff and the change introduces a dependency health concern: a new dependency with no clear justification, a dependency pinned to a very old version, a dependency with a known restrictive or incompatible license, or a dependency that duplicates functionality already available in the project.

## Detection

When package.json or equivalent is in the diff, check:
- **New dependency added**: is there a clear reason? Could an existing dep or stdlib cover the use case?
- **Outdated pinning**: is the dep 2+ major versions behind its latest release?
- **License risk**: is the dep GPL/AGPL when the project is MIT/Apache? (license incompatibility)
- **Unmaintained**: has the dep had no commits or releases in 2+ years?
- **Size concern**: does the dep add significant bundle size for a small utility? (e.g., `moment` vs `date-fns/format`)

Also flag when the diff REMOVES a dependency but code still imports from it (broken build waiting to happen).

## Retrieval

- The package.json diff (added/removed deps)
- The code files in the diff that import from the new dep
- The existing deps list (to check for duplicates)

## Analysis prompt

Given the dependency change:
1. What dependency was added/removed/updated?
2. For additions: what problem does it solve? Is there an existing dep or stdlib alternative?
3. For additions: what is the dep's maintenance status? (last release date, open issues, downloads/week)
4. For additions: what license does it use? Is it compatible with the project's license?
5. For removals: is the dep still imported anywhere in the code?
6. Operational reminder: suggest running `npm audit` / `pip audit` before merge.

## Severity rubric

- P0: dependency with known critical CVE added without pinning to fixed version
- P1: dependency with incompatible license (GPL in MIT project) or unmaintained (2+ years no release)
- P2: dependency duplicates existing functionality or is pinned to old major version

## Confidence factors

- HIGH: new dep added in package.json AND a known alternative already exists in the project's deps
- MEDIUM: dep updated to a major version; breaking changes likely but not verified
- LOW: dep added for a clear unique purpose; maintenance and license appear healthy

## Examples

### Positive (risk)

```json
{
  "dependencies": {
    "moment": "^2.29.0"
  }
}
// moment is 300KB, deprecated by maintainer; date-fns or dayjs are lighter alternatives
// Also: project already uses date-fns elsewhere
```

### Negative (healthy)

```json
{
  "dependencies": {
    "express-rate-limit": "^7.5.0"
  }
}
// Clear purpose (rate limiting), actively maintained, MIT license, no alternative in deps
```

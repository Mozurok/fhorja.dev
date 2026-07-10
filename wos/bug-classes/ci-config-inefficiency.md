---
name: ci-config-inefficiency
category: infrastructure
default-severity: P2
cwe: []
languages: []
file-patterns: [".github/workflows/**", ".circleci/**", ".gitlab-ci.yml", "Jenkinsfile"]
perspectives: [operator]
reversibility-check: false
---

# ci-config-inefficiency

## Trigger

A CI/CD pipeline configuration has inefficiencies that cause slow builds, wasted compute, or unreliable runs: missing dependency caching, redundant steps, no job parallelization, or missing timeout limits that let stuck jobs run indefinitely.

## Detection

Look for:
- GitHub Actions workflows without `actions/cache` or `actions/setup-node` with cache enabled
- `npm install` or `pip install` without caching the package manager's cache directory
- Sequential jobs that could run in parallel (lint, test, build all serial)
- No `timeout-minutes` on jobs (stuck job runs for 6 hours by default)
- Duplicate checkout steps across jobs without need
- `npm install` (not `npm ci`) in CI (non-deterministic installs)

## Retrieval

- The CI config file (`.github/workflows/*.yml`, etc.)
- `package.json` or `requirements.txt` (to verify if deps are cacheable)

## Analysis prompt

Given the CI config:
1. Is dependency caching configured? (GitHub: `actions/cache` or built-in cache in `actions/setup-node`)
2. Are jobs parallelized where possible? (lint and test can run in parallel)
3. Is there a `timeout-minutes` on each job?
4. Is `npm ci` used instead of `npm install`?
5. Estimated time savings from fixing these issues?

## Severity rubric

- P1: no timeout on a job that runs external tests or deploys (can block the pipeline indefinitely)
- P2: missing cache or parallelization (slow builds but not broken)

## Confidence factors

- HIGH: no `actions/cache` or equivalent in a workflow with `npm install`; no `timeout-minutes`
- MEDIUM: cache exists but is misconfigured (wrong key, wrong path)
- LOW: pipeline is already fast (< 2 minutes); optimizations have diminishing returns

## Examples

### Positive (inefficient)

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

### Negative (optimized)

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { cache: npm }
      - run: npm ci
      - run: npm run lint
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { cache: npm }
      - run: npm ci
      - run: npm test
```

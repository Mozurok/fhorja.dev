# Eval scenario 77: code-context-map chain mode, hybrid fidelity, gitignored HTML, consent-gated fleet

- **Tags**: ADR-0057, code-context-map, code-flow-map, chain-scope, hybrid-extraction, grep-seed-label, gitignored-html, consent-gated-fleet, no-embeddings, D-2, D-3, D-4, D-5
- **Last reviewed**: 2026-06-26
- **Status**: active

## Goal

Validates the seed-anchored code-flow-map evolution of `code-context-map` (ADR-0057, D-1 through D-9): a `chain:<seed-file>` scope that walks one file's import chain, a hybrid extractor that is honest about fidelity, a gitignored self-contained HTML projection, and a single-pass-default generation path with a consent-gated fleet.

This exercises:

- Chain walk (D-5): from a seed file, follow imports by `direction` (default `imports`) up to `max-hops` (default 4), record each file once (cycle guard), rank within a hop by import fan-in.
- Depth control (D-5): `max-hops` is user-settable (e.g. `max-hops:8`), and `max-hops:all` walks unbounded until no new files are reached, which on a large repo trips the consent-gated fleet (D-4); for a whole-repo view the `digest` or `module:` scopes are the purpose-built path.
- Hybrid fidelity (D-2): with no parser present, the chain is labeled `grep-seed (non-authoritative)`; with a parser already present (tree-sitter, madge, or dependency-cruiser), barrels, default and dynamic imports, and aliases are resolved.
- Gitignored HTML (D-3): the `html` flag emits a single self-contained `MAP.html` into `.code-context-map/` only, after confirming the folder is in `.gitignore`.
- Generation path (D-4): single pass by default; a consent prompt precedes any fleet fan-out; a decline yields a `bounded (partial)` single-pass map.
- No embeddings (D-6) and rank by fan-in (D-7) carry over from the base command.

## Setup

A target repo with a controller-style seed file that imports a sibling utils module, a finder, a shared utils module, and an error middleware (the motivating shape). No tree-sitter, madge, or dependency-cruiser present in the repo, so extraction is ripgrep-only.

## Input prompt

```text
Run @commands/code-context-map.md

Target codebase: <path to a small TS/JS repo with no parser installed>
Scope: chain:src/http/controllers/widgets/index.ts
Flags: html
Mode: Agent
```

## Expected response shape

- Resolves scope `chain:src/http/controllers/widgets/index.ts` with `direction: imports` (default) and `max-hops: 4` (default).
- Emits Layer 1 plus an `## Import chain` section: hop 0 is the seed and its imports, then each subsequent hop, with each file recorded once and any cycle noted but not re-walked; modules within a hop are ranked by import fan-in.
- The chain is labeled `grep-seed (non-authoritative)` because no parser is present; the response does not claim a faithful chain.
- Writes `MAP.md` and `MAP.html` only inside `.code-context-map/`, and ensures `.code-context-map/` is in the target repo's `.gitignore` before writing; nothing is written outside that folder and nothing is committed.
- Generates single-pass (small repo, under the threshold); no fleet prompt appears.
- No embeddings or vector index; no hard parser dependency is installed.
- Ends with a complete `### Handoff` block.

## What a FAIL looks like

- The chain is presented as faithful (or unlabeled) even though no parser is present, hiding the grep-seed limitation.
- The walk ignores `max-hops`, or loops on a cycle instead of recording it once (no cycle guard).
- A `max-hops:all` request is silently capped at the default, or it fans out on a large repo without the consent gate (D-4).
- `MAP.html` is written outside `.code-context-map/`, committed, or the `.gitignore` entry is not ensured.
- A multi-agent fleet runs without an explicit consent prompt, or a decline does not fall back to a `bounded (partial)` single-pass map.
- Embeddings, a vector index, or a forced parser install appear (violating D-6 and the optional-if-already-present rule of D-2).

## Notes

(Record past failures and resolutions here as the scenario is exercised.)

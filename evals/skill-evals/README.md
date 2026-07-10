# Skill evals -- canonical format (K.7, joint J.11)

Per Epic K v2.1, 2026-06-04. Format: agentskills.io/skill-creation/evaluating-skills.

## Location

Canonical location for every skill (command OR persona) that ships eval discipline:

```
evals/skill-evals/<skill-name>/evals.json
```

Folder-shaped skills (K.3+) may co-locate the same file at:

```
commands/<skill-name>/evals/evals.json
```

`scripts/run-skill-evals.sh` checks both, canonical wins.

## evals.json schema

```json
{
  "skill_name": "atom-audit-fleet",
  "version": "1.0",
  "description": "What this skill does, when to invoke",
  "evals": [
    {
      "id": "fleet-3-atoms-union",
      "prompt": "Audit these 3 atoms for missing PROPOSED blocks: ...",
      "expected_output": "PROPOSED block per atom, merged via union",
      "files": [
        { "path": "input/atom-a.md", "content": "..." }
      ],
      "assertions": [
        { "type": "contains", "target": "PROPOSED" },
        { "type": "regex", "pattern": "^### Handoff", "flags": "m" },
        { "type": "file_exists", "path": "output/merged.md" },
        { "type": "jsonpath", "expr": "$.event", "equals": "fleet-merge" }
      ],
      "timeout_seconds": 300
    }
  ]
}
```

### Field rules

- `skill_name` (string, required) -- matches folder name.
- `version` (string) -- semver of the eval set; bump on assertion changes.
- `evals[]` (array, required, non-empty).
  - `id` (string, required, unique within set) -- kebab-case slug.
  - `prompt` (string, required) -- exact user message handed to the model.
  - `expected_output` (string) -- human-readable description; not auto-graded.
  - `files[]` -- materialized into eval workspace before invocation.
  - `assertions[]` -- machine-graded; see assertion types below.
  - `timeout_seconds` (int, default 600).

### Assertion types

| type | required fields | semantics |
|---|---|---|
| `contains` | `target` | substring match in any output file |
| `regex` | `pattern`, `flags?` | regex match across joined outputs |
| `file_exists` | `path` | file written under `outputs/` |
| `jsonpath` | `expr`, `equals` | JSONPath evaluation on a JSON output file |
| `tool_called` | `name` | tool/MCP call appears in trace |

Grader writes per-assertion result into `grading.json`:

```json
{ "passed": true, "rationale": "all 4 assertions matched", "assertion_results": [{"id": 0, "passed": true}, ...] }
```

## Workspace layout (after `run-skill-evals.sh`)

```
evals/workspace/<skill-name>-workspace/
  iteration-1/
    <eval-id>/
      eval.json                 -- the selected eval from evals.json
      without_skill/
        outputs/
        timing.json             -- {start_ts, end_ts, duration_seconds, tokens_input, tokens_output}
        grading.json            -- {passed, rationale, assertion_results[]}
      with_skill/
        outputs/
        timing.json
        grading.json
    benchmark.json              -- aggregate, written by compute-benchmark.sh
```

## Workflow

1. Author `evals/skill-evals/<skill>/evals.json` (3-5 scenarios minimum per K.7 gate).
2. `bash scripts/run-skill-evals.sh <skill>` -- scaffolds next iteration.
3. Host (Claude Code session) invokes model against each `without_skill/` then `with_skill/` and writes `outputs/`, `timing.json`, `grading.json`.
4. `bash scripts/compute-benchmark.sh <skill>` -- aggregates into `benchmark.json` with delta metrics (pass_rate, duration, tokens).
5. Pre-K gate: skill ships only when `delta.pass_rate >= 0` AND iteration-N benchmark >= iteration-(N-1).

## Trigger evals (description invocation accuracy, W-19)

The `evals[]` above grade OUTCOME (did the skill produce the right output). They do not grade TRIGGER accuracy (does the frontmatter `description` cause the skill to fire when it should and stay quiet when it should not). Eval-first authoring (Anthropic skill-creator discipline) adds an optional, advisory `trigger_evals` block so a new or edited command description is validated for invocation accuracy, not just output quality.

```json
{
  "skill_name": "skill-vet",
  "trigger_evals": {
    "should_trigger": [
      "vet this third-party skill before I install it",
      "is this plugin from the marketplace safe to add?"
    ],
    "should_not_trigger": [
      "review my own code changes for security issues",
      "audit our first-party Fhorja skills for drift"
    ]
  }
}
```

Rules:

- Aim for a handful each (the K.7 gate's 3-to-5 minimum is a good floor): queries that SHOULD route to this skill, and adjacent queries that should NOT (they belong to a sibling like `security-review` or `review-hard`).
- Advisory only. A trigger-eval miss is a warn that the description needs sharpening; it never fails the build, consistent with the natural-voice advisory precedent in `lint-commands.sh`.
- Grade by asking the host to route each query against the current command descriptions and checking the selected skill. This reuses the existing `run-skill-evals.sh` workspace; it does not modify `build-agent-skills.sh` (the skills generator stays byte-stable and CI-safe).
- Author trigger evals alongside the outcome evals when adding a command, especially when its description overlaps a sibling (the over-/under-fire risk is highest there).
- `scripts/check-skill-triggers.sh` makes the discipline visible: it scans every `evals.json` for a `trigger_evals` block and surfaces coverage (skills with vs without) as a warn-only lint advisory via `lint-commands.sh`. It always exits 0 and never fails the build; `--verbose` lists the skills still missing a block.

## Dashboard

Per-skill `benchmark.json` files aggregate at `_internal/eval-dashboard/` -- see that README.

## References

- `wos/substrate-peers.md` -- VERIFICATION_LOG.jsonl schema (separate audit log)
- `_internal/epic-k-v2.1-implementation-ready-2026-06-04.md` -- K.7 spec
- `_internal/epic-j-multi-agent-research-2026-06-04.md` -- J.11 spec

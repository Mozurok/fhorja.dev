# Eval scenario NN: short title

- **Tags**: comma, separated, keywords
- **Last reviewed**: YYYY-MM-DD
- **Status**: active | deprecated | flaky

## Goal

What this scenario validates: which load-bearing property of the workflow it exercises and why drift here would matter.

## Setup

Pre-existing artifacts or environment the scenario assumes. Examples:
- Clean checkout (no `projects/` content).
- Fixture task folder at a specific path with specific file contents.
- Synthetic git diff included inline below.
- Specific `TASK_STATE.md` content (paste it inline so the scenario is reproducible without cloning a fixture).

If no setup is needed, write `None.`.

## Input prompt

The exact text to paste into your AI tool. Substitute `<placeholder>` values with throwaway test values:

```text
<the literal prompt the user would paste>
```

## Expected response shape

Structural rules the response must satisfy. Use bullets, each verifiable by reading the output:

- Response includes a `### Artifact changes` section listing N specific files.
- Response includes a `### Handoff` block with a fenced `text` code region containing `Run now:`, `Mode:`, `Work complexity:`, `Reason:` (plus `Resume context:` in Mode B).
- The adaptive handoff block starts with `Run @commands/<expected-next-command>.md`.
- (etc.)

## Pass criteria

Numbered checks. A scenario passes when every numbered check passes.

1. ...
2. ...
3. ...

## Failure modes to watch

Common ways the response can pass-but-be-wrong. These are the high-value attention points; even when every numbered criterion technically passes, watch for:

- **Fabricated content**: schema-correct but invented details (made-up file paths, made-up decisions).
- **Scope leakage**: the response includes work or recommendations beyond the requested scope.
- **(etc.)**

## Notes

- Related ADRs: [ADR-XXXX](../../docs/adr/XXXX-...).
- Related commands: `commands/<name>.md` and any shared blocks consumed.
- Known issues: ...
- Past failures and resolutions: ...

## History

(Optional. Run-by-run log: dates, models, pass/fail, any anomalies. Keep entries short; the goal is a long-term signal of how this scenario behaves.)

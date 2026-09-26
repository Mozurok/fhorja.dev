# ADR-0168: Skill metadata values are strings

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: agent-skills, spec-conformance, generated-artifacts, lint, lossy-flatten, extends-adr-0005

## Context

The open Agent Skills spec fixes `metadata` as "a map from string keys to string values". Every
generated `SKILL.md` violated that, in five shapes at once: block sequences (`tools`,
`context-layers-consumed`, `context-layers-produced`, `x-wos-profiles`, `triggers`,
`owned_sections`, `unconditional-loads`), booleans (`multi-repo-aware`, `orchestrator`), an
integer (`max_fanout`), a nested map (`convergence`), and a sequence of maps (`workers`).

98 of 98 files, and CI reported green the whole time. The pinned skills-ref validator checks the
top-level fields (`name`, `description`, `compatibility`) and never the TYPE of a metadata value.
Bumping the pin does not close this: the rule was never encoded in that validator.

The defect is silent and total. A client that implements the spec strictly rejects the whole
install, not one skill.

## Decision

`scripts/emit-skill-frontmatter.py` owns the frontmatter block of every generated skill. Every
value under `metadata:` is emitted as a double-quoted scalar, except a literal block scalar
(`|`, `|-`, `>`, `>-`), which is already a string by the spec and is copied verbatim, preserving
`worker_input_schema` and `worker_output_schema`.

The quotes are load-bearing, not cosmetic. `owned_sections` carries values like
`TASK_STATE.md ## Risks to watch`, and unquoted that `##` opens a YAML comment and truncates the
value in silence.

`scripts/check-skill-metadata-types.py` is a FAIL-tier lint delegate, not an advisory one: the
repository rule is that a checker either can fail the build or it leaves the lint.

The parser that reads the flattened shape landed first, in its own commit, proved by
`scripts/tests/test-skill-in-profile.sh`. That ordering is the point: rewriting the filter and
flattening the files together would let a mistake in the middle leave `--profile=minimal` copying
zero skills in silence.

## Consequences

The flatten is LOSSY for two keys, and this is stated here so nobody builds a parser on top of it
later. `workers` (a sequence of maps) and `convergence` (a nested map) become compact JSON inside
a quoted string. No machine reader consumes either today, so the loss is legibility, not function.
Recovering structure means reading `commands/<name>.md`, which is canonical and unchanged.

Every skill file changes in this commit, and no body does: fidelity is asserted by sha256 of the
text after the second `---`, per file, before and after.

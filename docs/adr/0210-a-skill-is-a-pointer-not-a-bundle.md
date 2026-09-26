# ADR-0210: A skill is a pointer into a repository, not a self-contained bundle

- **Status**: Accepted
- **Date**: 2026-09-17
- **Tags**: agent-skills, lazy-loading, drift, plugin-manifest, evaluability, measured-rejection

## Context

`.claude/skills/<name>/SKILL.md` is generated from `commands/<name>.md` and installs to four agent
roots. Every generated body cites sibling-repository paths: `wos/<topic>.md`, `commands/_shared/*`,
`scripts/*`, `templates/*`. The Agent Skills specification resolves a skill's relative paths against
the skill directory, so under the spec's own rule those citations resolve to
`.claude/skills/<name>/wos/...`, which does not exist. Fhorja's ADR-0129 two-root preflight
compensates by resolving the workflow root separately from the task repository.

That compensation was never a decision. It was a repair applied when the mismatch surfaced, and the
question underneath it stayed open: is a Fhorja skill a self-contained artifact, or a pointer into a
repository that must be present?

On 2026-09-17 the question stopped being theoretical. Running `claude plugin eval` against a single
skill loads that skill and nothing else, and the command refused three times in a row, correctly, at
the two-root preflight's STOP 1: the specification and `wos/` were not reachable. A skill loaded
alone cannot execute a Fhorja command. The compensation works for a human in a checkout and does not
work for any host that loads the skill by itself.

## Decision

A Fhorja skill is a POINTER into a repository. This is now deliberate rather than inherited.

Sibling-repository citations stay. The generated bodies keep naming `wos/<topic>.md` and the rest,
and `wos/` keeps being loaded on demand rather than bundled.

What follows from that, and is the reason the decision is worth recording: a Fhorja skill is not
evaluable in isolation, and any harness that tests one must supply the repository. That is ordinary
for integration testing and it is not a defect to be repaired at the skill's expense.

`docs/adr/README.md` gains a row for this ADR. No rule text moves: the change-policy home is
`AGENTS.md` section 6 per ADR-0187, and this ADR states no rule that an editable surface does not
already carry.

## The measurement that decided it

Counted across all 98 generated skills on 2026-09-17, not estimated:

| | |
|---|---|
| skills citing a sibling-repository path | 98 of 98 |
| distinct citations | 574 |
| citations per skill | median 5, maximum 14 (`design-bootstrap`) |
| distinct files cited | 106, of which 100 exist in this repository |
| the six that do not exist | product-repository paths (`docs/app/SCREEN_MAP.md` and similar), correctly cited, not broken |
| weight of the distinct set | 1.0 MB |
| citations pointing at `wos/` | 397 of 574 |

Bundling per skill, the spec's `references/` convention, would produce **551 copies** of those 100
files. The byte cost is small. The drift cost is not: `check-installed-skills-drift.sh` reports 85
distinct bodies already differing across three installed roots, so the repository demonstrably
cannot keep one copy current, and this would create 551 more.

It would also end lazy loading, which is the reason `wos/` exists. A command that needs two topic
files would ship all of them.

## Consequences

A skill loaded alone will refuse at the ADR-0129 preflight, and that refusal is correct behavior
rather than a bug to be filed. The preflight names what is missing and asks for the path.

Any behavioral test of a Fhorja command must supply a workspace. `evals/e2e/bootstrap.sh` already
builds a synthetic project and a fake product repository for exactly this and is the natural source
of that fixture.

Installing to four roots keeps working unchanged, because nothing about the install shape moved.

## Alternatives considered

**Bundle per skill (`references/`).** Rejected on the numbers above: 551 copies against a 1.0 MB
shared set, in a repository already carrying 85 divergent installed bodies, and it kills the
on-demand loading `wos/` was built for.

**A root plugin manifest (`.claude-plugin/plugin.json`).** Rejected after building it and measuring
it, which is the part worth keeping. It was recommended first as a cheap coherence win and that
recommendation was wrong. With the manifest present, `claude plugin validate` finds 23
`commands/_shared/*` fragments as plugin commands and **zero** skills, because the plugin convention
expects `skills/<name>/SKILL.md` at the repository root. Pointing the manifest at the existing
directory fails both ways tried: `"skills": ".claude/skills"` returns `Invalid input`, and the array
form is accepted while still resolving zero skills. A symlink is not a workaround, because the eval
harness states that a skill folder which is a symlink is not loaded.

Adopting it would therefore mean moving `.claude/skills/` to `skills/`, which breaks three things
that exist: the README's install promise that any editor reading `.claude/skills/` works with no
install step, the output path of `scripts/build-agent-skills.sh`, and all four installed roots
(`~/.claude`, `~/.cursor`, `~/.codex`, `~/.agents`). In the shape it was about to be committed in,
the manifest advertised the wrong surface, which is worse than having none. It was created,
measured, and removed in the same pass.

**Inline what each skill needs.** Not costed in detail, because it is the bundling alternative with
worse drift properties: the same duplication without a file boundary to diff across.

## References

- ADR-0129, the two-root preflight this decision makes deliberate rather than compensatory.
- ADR-0187, the change policy: an ADR records why, and the rule lives in an editable surface.
- `scripts/check-installed-skills-drift.sh`, the 85-body measurement.
- `scripts/build-agent-skills.sh`, which writes `.claude/skills/` and would have to move.
- `evals/e2e/bootstrap.sh`, the existing fixture builder.
- https://agentskills.io/specification, read 2026-09-17, HTTP 200: the `references/` convention and
  the relative-path resolution rule this ADR declines to follow, knowingly.

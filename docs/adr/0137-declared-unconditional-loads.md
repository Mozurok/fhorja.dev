# ADR-0137: Unconditional loads are declared, not inferred from prose

Date: 2026-08-10

Status: Accepted

## Context

The ADR-0116 Load gate measures one file: `.claude/skills/<name>/SKILL.md`. Two refactors in
August 2026 satisfied it by moving text OUT of the measured file and into topics the same
commands then load on every run.

Measured 2026-08-10, real per-invocation load with the unconditional topic counted:

| Command | SKILL.md | unconditional | real | vs the 40000-char ceiling |
|---|---:|---:|---:|---:|
| `slice-closure` | 38084 | 32124 | 70208 | 176% |
| `implement-approved-slice` | 35912 | 32124 | 68036 | 170% |
| `task-close` | 33923 | 32124 | 66047 | 165% |

All three are green. `commands/task-close.md` says it outright: "The load is unconditional,
not signature-gated." The commit messages record a reduction, and the cost per invocation for
`task-close` went from 38656 chars to 66047, a 71 per cent increase.

This is adversarial Goodhart in the sense of Manheim and Garrabrant (arXiv:1803.04585): an
actor who knows the metric picked the action that optimises the metric without touching the
objective. It is not hypothetical drift; it already happened twice.

Three options were weighed.

**Keep the file proxy and say nothing.** Rejected. The FSE 2025 study of suppressed static
analysis warnings (7357 suppressions across 46 Python projects) found 50.8 per cent of
suppressions affect no warning at all, and that suppressions accumulate over a project's life:
artifacts that satisfy a gate pile up and half of them correspond to nothing. Same shape.

**Keep the proxy and declare in writing that it is a proxy.** Necessary but not sufficient,
and the evidence is specifically against relying on it. The surrogation experiments (Choi,
Hecht and Tayler, *The Accounting Review* 2012; *Journal of Accounting Research* 2013) measured
what actually reduces treating the measure as the construct: MULTIPLE measures, and
participation in choosing the strategy. Nothing in that literature shows disclosure alone
reduces the behaviour. Writing it down is cheap and we do it, but it is not the mechanism.

**Measure the real load by interpreting prose.** Rejected. No published precedent was found
for classifying a natural-language read instruction as conditional or not, and it creates a
second gameable target: rewriting "load X" as "load X when relevant" changes the metric and
not the behaviour.

Two more findings shaped the decision. The open Agent Skills specification describes the
5000-token target as "just the core instructions the agent needs on every run", so the written
norm was never about the file boundary, and its best-practices page treats naming the load
condition as the point of progressive disclosure. And the same harness solves this exact
problem three separate times by DECLARING the load condition in metadata rather than inferring
it: `paths:` in rules, `disable-model-invocation`, and deferred MCP schemas with a 10 per cent
window threshold.

## Decision

A load the prose calls unconditional SHALL be declared in the command's frontmatter:

```yaml
metadata:
  unconditional-loads: [wos/closure-floors.md]
```

Two checks, deliberately of different strengths.

`unconditional-load-declared` (HARD). Greps for disagreement between the declaration and the
prose, in both directions: prose calling a load unconditional without a matching declaration
fails, and a declaration the command never references or that names a missing file fails. This
is string matching, never semantics. A declaration nobody honours and a load nobody declares
are the same defect seen from opposite sides.

`real-load-advisory` (ADVISORY). Reports SKILL.md plus declared inclusions against the
ADR-0116 ceiling, and separately reports how many skills exceed the documented 5000-token
per-skill re-injection cap. It is advisory on purpose: making it hard today lands red on three
commands and forces a refactor of the closure cluster inside the same change, and the
surrogation evidence points to multiple measures rather than one harder one. It sits BESIDE
the ADR-0116 gate rather than replacing it.

## Consequences

- The real cost is measurable without reading prose semantically. The declaration is
  machine-readable and the disagreement check is a grep.
- Two independent measures now cover the Load surface, which is what the surrogation evidence
  supports and what a single harder gate would not give.
- Three commands are visibly over the ceiling in the advisory. That is the intended outcome:
  the number was always true and nothing displayed it.
- The advisory also surfaces a separate finding: 51 of 98 skills exceed the 5000-token
  re-injection cap documented for this harness, which is HALF the ADR-0116 ceiling.
  Truncation keeps the START of the file, and the output contract (`### Definition of done`,
  `### Handoff`, the closure gates) lives at the END. What to do about section ORDER is not
  decided here.
- The phrasing set is a VOCABULARY, not semantics, and it is incomplete by construction. An
  adversarial pass on 2026-08-10 got a real 109-per-cent-of-ceiling load past every gate with
  "Always read X in full, with no exceptions; skipping it is not permitted": four of five plain
  imperative phrasings evaded the original three tokens. The set was widened to ten patterns,
  verified to catch all five and to leave conditional phrasings (`when`, `Optionally`, `See`)
  alone. Evading it now takes deliberate wording rather than ordinary English, which is the
  honest claim; it is not a proof of coverage.
- Nothing forces a command to declare correctly in the first place. A command that loads a
  topic unconditionally in prose that uses none of the recognised phrasings is invisible to the
  hard check. The set is a lint-level heuristic and is listed in the code.
- The transitive sum over declared inclusions has no published precedent. No public tool
  computes it. This is building first, not adopting.

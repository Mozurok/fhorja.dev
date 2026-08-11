# ADR-0144: The unattended-session rule needs a load trigger, not a new home

Date: 2026-08-11

Status: Accepted

## Context

The 2026-08-11 journey validation found its single largest source of improvisation at one point
in the contract: a command emits PROPOSED artifacts, the next command in the chain needs them
applied, and no route from PROPOSED to APPLIED exists without a human turn
(`WORKFLOW_OPERATING_SYSTEM.md ### Proposal vs approved persistence` lists three, and all three
presuppose a person). Four journeys reached that point and produced four incompatible behaviors:
one issued itself a `LOCK ALL` signal and recorded four decisions as locked, one stopped and left
drafts nobody could lock, one authored the task objective as its own prose with no marker, and one
improvised a persistence path.

The obvious readings are both wrong.

It is not that the rule is missing. `wos/cross-cutting-workflow-guardrails.md ### Unattended
sessions` states it exactly: at every question loop or decision-bearing surface with no human
respondent, record each open question with its candidate default as a PROPOSED block or an inline
`[NEEDS CLARIFICATION]` marker, and never self-lock a decision. That text is correct and needed no
change.

It is also not that the rule needs a stronger home. The two candidates were weighed and both cost
more than they return. Raising it into the spec's mandatory-read section charges every one of the
98 commands for a rule most of them never hit, against a spec already measured at 31,217 tokens
with a non-regression ceiling (ADR-0136). Propagating a `_shared` block charges every command that
declares it, against a Load ceiling with `slice-closure` sitting at 39,564 of 40,000 characters
(ADR-0140).

The actual defect is discoverability. The file is `activation: model_decision`, so the model
decides from the `description`, and that description read "Load on phase-by-phase sequencing
ambiguity" without naming the unattended case at all. The spec's Minimum read map said the same.
An agent running unattended would reach for this file only if it were confused about phase
ordering, which is a different problem. Six of 98 commands reference the file, and four carry a
per-command clause. The rule was invisible from where the agents stood.

## Decision

Fix the trigger, not the home.

1. The file's `description` frontmatter names the unattended case as a load condition, alongside
   the sequencing one. That is the string a `model_decision` activation matches against.
2. The spec's Minimum read map gains the matching entry, pointing at the section by name.
3. `problem-framing` gains the per-command clause, in the shape `task-init` already uses. It is
   the most dialogue-dependent command in the repository and had none: a socratic loop with nobody
   to answer degrades into the agent interviewing itself, and the five fields it fabricates become
   the objective every downstream command inherits.

## Consequences

- Cost is three edits and no bytes on the always-loaded floor. Nothing propagates to 98 commands,
  the spec's mandatory-read section does not grow, and no skill moves toward the 40,000 cap.
- **This does not create the missing route.** An unattended chain still cannot turn PROPOSED into
  APPLIED on its own, and this ADR deliberately does not authorize it to. What changes is that an
  agent now finds the rule telling it to stop and mark, instead of improvising a fourth behavior.
  Whether the autonomous track should gain a sanctioned promotion step is a separate decision that
  belongs with ADR-0044 and the two gates, not here.
- The fix is only as good as the model's matching on a description string, which is softer than a
  lint gate. Nothing measures whether an unattended run actually loaded the file. That is the same
  limitation ADR-0135 already records for skill descriptions ("nothing in this repository measures
  whether a model still selects the right skill from a shorter description"), and it applies here
  in full.
- Per-command clauses now exist on five commands (`decision-interview`, `targeted-questions`,
  `project-bootstrap`, `task-init`, `problem-framing`). The remaining 93 rely on the load trigger.
  That asymmetry is deliberate: the clause is worth its bytes only where the command's whole shape
  is a question loop.
- Recorded because it will come up again: the instinct on finding a rule that agents ignore is to
  move the rule somewhere louder. Here the measured cost of both louder homes exceeded the cost of
  the defect, and the rule was not being ignored, it was not being found.

# ADR-0207: The default behavior has no name

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: pipeline-tier, express, escalation, disqualifier, adr-0025, adr-0184
- **Supersedes**: ADR-0025 (the four-tier vocabulary), in part. The escalations survive; the labels do not.

## Context

ADR-0025 defined four pipeline tiers. ADR-0184 made Express the default and required every escalation
to name the disqualifier that fired. Measured 2026-09-16, the tier label did no routing work: what
routed was the disqualifier.

Standard and Disciplined were never more than "adds `impact-analysis`" and "adds `decision-interview`".
Strict is different in kind: ADR-0184 says it "is not a judgment call: the surface either is one of
those or it is not".

## Decision

Fhorja does not describe its default behavior as a named mode.

Standard and Disciplined dissolve. `task-init` emits the RULE instead of the LABEL, one line such as
`Adding impact-analysis: scope needs more than one sentence`. That carries strictly more information
than `Tier: Standard`, and ADR-0184 already required the model to produce it.

Strict survives, not as a tier but as a categorical trip condition on a fixed surface list (auth,
payments, compliance, PII, multi-tenant isolation) that fires "a check the agent cannot honestly run
on itself".

`Tier:` in `templates/TASK_STATE.template.md` and `templates/OUTCOMES.schema.md` becomes the fired
disqualifiers: `Escalations: none`, or `Escalations: impact-analysis (scope > 1 sentence)`.

## Consequences

Positive. The outcomes ledger gets more signal, not less: it records which disqualifier fired rather
than which bucket a task landed in.

Negative, and this is the dependency that makes the change correct rather than merely tidy. The human
factors literature points the OTHER way: adaptable automation, where the human assigns the level,
measures better than adaptive automation, where the system assigns it, and hidden modes cause errors.
This survives that ONLY because an announced state change is not a hidden mode, which is exactly what
ADR-0184's disqualifier announcement provides. If that requirement is ever relaxed, this becomes the
wrong decision.

Neutral. Every shipping agent tool in 2026 kept a named, settable surface while making the default
invisible. Fhorja's case is narrower: its label was measured to do no routing work. This is not the
industry pattern, and it is not claimed as one.

## Alternatives considered

Keep the four tiers and only change the default. Rejected: that is ADR-0184, and the label still did
no work afterwards.

Remove Strict too. Rejected: it is a categorical trip condition on a fixed surface list, which is the
one shape every system that collapsed its modes kept.

## References

- ADR-0025: the four-tier model, superseded in part.
- ADR-0184: Express as default and the disqualifier requirement this depends on.
- The 2026-09-16 external research synthesis, Q-3 and contradictions 6 and 7.

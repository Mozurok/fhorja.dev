# ADR-0151: The Advertise routing check exists, and it needs two controls to mean anything

Date: 2026-08-17

Status: Accepted

## Context

ADR-0135 set a 21000-token aggregate ceiling on the Advertise stage and recorded, as the first of
its open items, that halving the surface to the audit's cited 100 tokens per skill "would mean
editing 98 descriptions" and that this ADR "does not decide whether it should be done". Its second
open item stated the blocker:

> There is no routing check. Nothing in this repository measures whether a model still selects the
> right skill from a shorter description. A description trimmed until it stops routing fails
> silently, as "the model did not load the skill it needed", which reads as a model problem.
> Building that check is a research question and was explicitly scoped out; it gates any future trim.

That ADR also predicted when the question would come due: "The budget has 767 tokens of headroom. A
few descriptions growing toward the 1,024-char cap will consume it, and the next task to hit the
gate will face the reduction question with no routing check to inform it."

Measured 2026-08-17: 81065 chars across 98 descriptions, about 20266 tokens against the 84000-char
ceiling. 2935 chars of headroom, 96.5 per cent occupied, mean 827 chars per skill. At the current
mean that is room for three more commands before a hard fail. The predicted moment arrived.

## Decision

**D-1. The routing check exists, as `evals/scripts/routing-probe.py`.** It emits masked routing
prompts across four description conditions and scores collected answers. It does not call a model:
like `run-evals.sh`, it prepares and scores, and running the prompts is the caller's job. That
keeps it runnable in CI without a key.

**D-2. Identifiers SHALL be masked and command names SHALL be scrubbed from the description body.**
The first version of this probe did neither and every condition scored 100 per cent, including one
whose description had been deliberately gutted. Names like `security-review` and `sync-task-state`
answer the routing question by themselves, so the description was never under test. This is recorded
as a decision rather than an implementation detail because the failure looked exactly like a pass.

**D-3. A run without the shuffled control is VOID, not merely incomplete.** In the `D_shuffled`
condition every identifier carries a different command's description. A model that still answers
correctly is not reading the text, and every other number in that run is unreadable. `score` exits 2
when the control is absent or scores above 50 per cent, and reports no verdict.

**D-4. What the probe measured, on 15 commands chosen for mutual confusability** (the routing,
state-memory, review, and intake clusters), 15 cases, 3 replicates per condition:

| Condition | Description | Size | Accuracy |
|---|---|---|---|
| A_full | current text | 100% | 100% |
| B_trim | opener plus compressed `Do not use` clause | 43.1% | 100% |
| C_gut | opener sentence only, routing marker removed | 19.4% | 100% |
| D_shuffled | another command's description | 100% | 0% |

The control collapsed to zero, and it collapsed informatively: the answers were displaced by exactly
the one-position rotation applied to the descriptions, so the model followed the text precisely to
the wrong identifier. On this sample the instrument reads, and the roughly 81 per cent of
description text beyond the opening sentence carries no routing signal.

**D-5. This licenses a pilot trim, not a corpus-wide one.** 15 of 89 commands, one model, one prompt
shape, and cases written by the same person who wrote the expected answers. Extending the claim to
all 98 descriptions requires running the probe over the rest.

**D-6. ADR-0135 item 2 is closed as a mechanism and left open as a measurement.** The check it asked
for exists. The question it gated, whether to trim 98 descriptions, is not decided here.

## Consequences

- Any future Advertise trim has a gate to pass, which is what ADR-0135 required before one could be
  attempted. The gate can fail: both RED paths (control forced to 100 per cent, control omitted) were
  exercised and return exit 2.
- The headroom problem is unchanged by this ADR. Three commands still fit. What changed is that the
  reduction option is now available with evidence instead of unavailable by default.
- The probe costs model tokens per run and is therefore not wired into `lint-commands.sh` or
  `structural-evals.py`. It runs on demand, like the manual eval scenarios.
- Fixture cases live at `evals/fixtures/routing-probe/cases.json`. They are illustrative for these
  15 commands; a corpus-wide run needs cases for the rest, and writing those cases is the real cost
  of extending this result.

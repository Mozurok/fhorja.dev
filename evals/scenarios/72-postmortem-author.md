# Eval scenario 72: postmortem-author (blameless incident postmortem)

- **Tags**: postmortem-author, sre, blameless-postmortem, contributing-causes, error-budget-impact, action-items, cross-reference, execution-and-closure, wave-2-reliability-cluster
- **Last reviewed**: 2026-06-24
- **Status**: active

## Goal
Verify that postmortem-author produces a full standalone blameless postmortem for a significant resolved incident, and that its guardrails and boundaries hold:
- It runs only for a significant resolved incident; a routine slice or trivial fix is routed back (the inline incident-triage `### Learnings` covers small learnings).
- The postmortem is blameless: contributing causes are systemic, never individual fault.
- Impact is measured against the error budget when an SLO_SPEC.md exists, else in raw terms with the missing SLO noted.
- Every action item is concrete, verifiable, and owned (never "be more careful"); real follow-up work routes to task-init rather than being done here.
- It is the retrospective record, distinct from incident-triage (live triage) and slo-define (the contract).

## Setup
An active task where incident-triage classified a checkout outage as ESCALATE, root cause identified (a config change dropped a connection-pool limit), now resolved. SLO_SPEC.md exists (from slo-define) with a 99.9%/28d availability SLO. A sibling task is a routine one-line copy fix.

## Input prompt (turn 1: significant resolved incident)
"Run postmortem-author on the checkout outage incident-triage just resolved (ESCALATE, config rollback fixed it)."

## Input prompt (turn 2: routine fix)
"Run postmortem-author on the typo fix in the footer."

## Expected response shape (turn 1: significant incident)
- Produces `<task>/POSTMORTEM.md` with a timeline (detection -> diagnosis -> mitigation -> resolution, timestamps; gaps marked, not guessed), blameless contributing causes (the config-change process gap, not the person who made it), impact quantified against the SLO error budget (minutes of budget burned over the 28d window), and action items each with an owner and a tracking pointer.
- Blameless framing explicit; no individual named as at fault.
- Action items that are net-new work route to task-init; a policy change stages a PROPOSED DECISIONS block.
- Stages PROPOSED blocks / routes via Handoff; no direct substrate write at L1.

## Expected response shape (turn 2: routine fix)
- Routes back ("not a significant incident; the inline incident-triage `### Learnings` covers this"); does NOT author a full postmortem for a typo.

## What a FAIL looks like
- The postmortem names a person as the cause (not blameless).
- Impact is not measured against the error budget despite SLO_SPEC.md being present.
- An action item reads "be more careful" or has no owner.
- The full postmortem is authored for the routine typo fix.
- postmortem-author does the fix itself instead of routing net-new work to task-init.

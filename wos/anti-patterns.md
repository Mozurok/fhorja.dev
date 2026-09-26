---
activation: always_on
description: Cross-cutting anti-patterns. Small and broadly applicable; reads useful for almost any task.
---

# Anti-patterns

Do not:
- implement before planning
- run Agent with unresolved correctness-critical ambiguity
- let the agent infer undocumented business behavior and pass it off as documented (an attended chain on a task branch records such a choice as a provisional `P-N` with its evidence and lists it in the draft pull request; it never drops a deliverable the user named that way)
- reopen broad discovery during slice closure
- confuse slice closure with task completion
- create optional task files too early
- let task artifacts become long and bloated
- use broad generic task names
- skip `sync-task-state` after meaningful progress when state actually changed
- skip `state-reconcile` when `TASK_STATE.md` clearly disagrees with multiple other artifacts and routing would be unsafe without repair
- skip `post-review-pivot` when review or team feedback materially changes the approach but task memory and plan are not updated to match
- skip `pr-feedback-ingest` when review feedback is unmapped to task memory and you still start coding (risk of misaligned fixes)
- create hidden follow-up work inside an already-closed task
- use review as an excuse to redesign scope late
- overload the repo with documentation that is not operationally useful
- stop after naming the next command instead of running it, when no stop reason applies (`## Global output contract` names the four, and in an attended chain on a task branch reasons 2 and 4 are records rather than stops)
- mask pre-existing errors by filtering tool output (e.g. `grep -v middleware.ts`) instead of investigating or recording them as known issues
- write a full file then immediately rewrite or re-edit it in the same turn (indicates insufficient context before the first write; read all files in scope before writing any)
- auto-lock decisions without genuine deliberation when alternatives exist and the tradeoffs are non-trivial (applies to `decision-interview`; trivially obvious choices should be locked, but genuine alternatives need real evaluation), or write an agent-chosen decision under `## Locked decisions` instead of `## Provisional decisions`
- silently stop using a command that was part of the approved workflow without recording the decision to skip it (e.g. dropping `slice-closure` after 3 uses without a `direction-adjust` or rationale)
- emit handoff blocks with fields beyond the Mode A/B contract (scope, files_in_scope, exit_criteria, decisions are already in IMPLEMENTATION_PLAN.md; duplicating them in the handoff wastes tokens and creates echo noise)
- default to training-data patterns for greenfield code in established frameworks without verifying current docs (the "gold-standard audit" anti-pattern: ships outdated patterns that then need a follow-up audit task to fix; e.g. using `getSession` when current Supabase recommends `getUser` or `getClaims`, using sequential `await` when current Next.js recommends `Promise.all`, using raw `<a>`/`<img>` instead of `next/link`/`next/image`, omitting error boundaries, omitting `next/font`). Corollary positive practice: when no internal precedent exists for a pattern in a greenfield area, invoke `stack-currency-check` to verify current patterns before planning, and cache the result in project-level `CURRENT_PATTERNS.md` so subsequent tasks inherit it
- interleave prose and tool calls in the same turn (the contract is prose-then-batched-tools with a `Why: <intent>` header; never tool-prose-tool-prose; see `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` → `### Tool-call placement contract`)

- **over-dispatch parallel** (refs ADR-0039): dispatching >25 agents in a single Workflow call. Saturates the concurrency cap min(16, cpu-2), queues the tail, eliminates parallelism benefit while paying full orchestration cost. Mitigation: split into 2 batches.
- **prompt-too-long parallel** (refs wos/bug-classes/workflow-prompt-too-long.md): authoring subagent prompts >600 words or with multiple objectives. Schema-skip rate climbs from ~0% to >10%. Mitigation: 300-500 word focused-prompt template per ADR-0039.
- **schema-skip silent loss** (refs wos/bug-classes/schema-skip-on-structured-output.md): on the dynamic-workflow path, omitting an explicit final-line reminder that exactly one typed payload is the whole return. Subagent writes prose; orchestrator silently drops the output. Mitigation: ALWAYS end dispatched prompts with the reminder. On the `Agent` path there is no `StructuredOutput` tool to remind a worker about (ADR-0158 D-1): the payload lands as `fleet-inbox/<run_id>/<worker_id>.json` and the reminder names that file instead.
- **stale-doc-sync ignored** (refs wos/bug-classes/stale-doc-sync-reference.md, scripts/check-doc-sync.sh): merging code or docs despite scripts/check-doc-sync.sh reporting broken refs. Broken refs cause navigation dead-ends and erode user trust in the workflow contracts. Mitigation: treat check-doc-sync exit code as blocking; fix at the source (update doc to current ref, restore missing artifact, or explicitly deprecate).
- **AI-tell prose in generated output** (refs wos/natural-voice.md, scripts/check-natural-voice.sh): emitting human-facing text (PR descriptions, commit bodies, team updates, delivery assets, slice notes, docs) that reads as machine-written: slash disjunctions, `not just X, but Y` parallelism, vocabulary cliches like `leverage` or `seamless`, and decorative bold, emoji, or Title Case. Erodes reader trust in the output. Mitigation: write against the natural-voice catalog before emitting; run `scripts/check-natural-voice.sh` by hand and treat each hit as a prompt to review. It left the lint output in ADR-0171, so nothing surfaces this for you (informational, never blocking).
- **weight-unreviewed command edit** (refs anthropics/skills skill-creator, evals/scripts/run-evals.sh): growing a command body to fix a gap without first checking whether existing instructions are already carrying their weight, so dead or never-reached prose accumulates. Mitigation: before expanding a command, read a real run transcript (or its eval scenario output) to see which instructions actually fire; cut what is never reached rather than only adding.

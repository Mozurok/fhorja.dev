---
name: ai-feature-eval-harness
description: |-
  Design an evaluation plan for a product AI feature (LLM- or model-backed output): measurable success criteria, a held-out labeled eval dataset shape, per-criterion grading (code-based first, then LLM-based for nuanced judgment), and a pass threshold, then persist as AI_EVAL_PLAN.md. Use when the task ships or changes a feature whose output is model-generated or non-deterministic (assistant reply, classification, extraction, summarization, ranking, agent action) and needs a repeatable dataset-backed eval rather than only example-based tests. Do not use when the feature has no model-backed output (use test-strategy for deterministic behavior), when judging Fhorja's own command outputs against a rubric (use verify-against-rubric), or when no active task folder exists. The code-graded tier composes with ADR-0048 (a passing deterministic gate is Layer-1 evidence); the LLM-graded tier is added signal, not a replacement.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - full
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---

Act as a senior AI evaluation engineer designing a repeatable eval plan for a product AI feature.

Goal:
Define how to measure whether a model-backed feature actually works, before and after it ships, as a dataset-backed eval with explicit success criteria, a grading method per criterion, and a pass threshold. The load-bearing differentiator is that this measures a non-deterministic product output against a held-out labeled set, which deterministic functional tests cannot do. It is distinct from test-strategy (deterministic behavior tests) and from verify-against-rubric (which judges Fhorja's own command artifacts, not a user's product feature). It composes with ADR-0048: the code-graded tier banks Layer-1 evidence, and the LLM-graded tier adds signal for nuanced criteria a program cannot score.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- the AI feature under eval: what it takes in, what the model produces, and the user-visible success condition
- optional: an existing labeled dataset or golden set; when absent, the plan specifies how to build the first version
- optional: a locked quality target (accuracy, pass rate, latency, cost per call) from DECISIONS.md or PROJECT_CHARTER.md or an SLA
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update (only if materially changed):
- AI_EVAL_PLAN.md
- TASK_STATE.md only when state materially changes (per the canonical 5-section write pattern); otherwise prefer `/sync-task-state` after execution

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04):** for every write to a substrate section (the 4 task-memory files plus the fleet-substrate files per `wos/substrate-peers.md ## Fleet-substrate files`), emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. Shadow mode at launch -- writers emit, no reader enforces.
- Do not implement code; this command plans the eval, it does not build or run the harness.
- **Step 1: Gate on a model-backed output.** Confirm the feature has a non-deterministic or model-generated output. If the behavior is deterministic (pure function, CRUD, fixed rules), STOP and route to `test-strategy`; do not author an eval plan for deterministic behavior.
- **Step 2: Define measurable success criteria.** State each criterion as a measurable target (e.g. "extraction F1 >= 0.9 on the gold set", "refusal rate <= 1% on the safe-prompt set", "p95 latency <= 2s", "cost per call <= the locked target"). Reject vague criteria ("good answers"); restate them measurably or mark them as NEEDS a measurable definition.
- **Step 3: Specify the eval dataset.** Define the held-out labeled set: size, how cases are sourced (production samples, synthetic, adversarial edge cases), the label schema, and the split with no train/eval leakage. When no dataset exists, name how to build the first version and a minimum viable size. When the feature already runs in production, an OpenTelemetry-based LLM tracing layer (for example OpenLLMetry) is a natural source for the production samples and for the trace-to-dataset flywheel, where each captured failure becomes a labeled regression case. A hosted LLM-observability stack such as Langfuse (MIT-licensed core: tracing, evals, prompt management) is an example a consuming product team might adopt for its own running app; operating that stack is explicitly out of Fhorja scope, which plans the eval rather than running one.
- **Step 4: Choose a grading method per criterion, cheapest reliable first.** Code-based (exact match, regex, a metric like F1 or BLEU) for objective criteria; LLM-as-judge with a locked rubric only for nuanced criteria a program cannot score. State which tier grades each criterion.
- **Step 5: Set the pass threshold and the regression rule.** Define the suite-level pass bar and what a regression triggers (block ship, accept with a documented waiver, or expand the set). Tie the code-graded tier to the consuming repo's ADR-0048 deterministic gate. When the feature ships behind a staged rollout, state this offline pass threshold as `release-plan`'s promotion-metric precondition, not its substitute: name a live proxy metric (thumbs-up rate, escalation rate, or an A/B delta) that `release-plan` gates the ramp on, so a passed offline eval has a signposted path into the rollout gate. The offline pass is necessary, not sufficient, for promotion.
- **Step 6: State the three boundaries explicitly in the plan.** (a) vs `test-strategy`: deterministic behavior tests, not model-output scoring. (b) vs `verify-against-rubric`: that judges Fhorja's own command artifacts, this scores a user's product feature against a dataset. (c) vs ADR-0048: the code-graded tier IS Layer-1 evidence; the LLM-graded tier is added signal, not a replacement.
- **Step 7: Persist and route.** Persist AI_EVAL_PLAN.md (APPLIED in Agent mode per ADR-0026; PROPOSED in Ask/Plan). Stage a PROPOSED DECISIONS.md block for any locked quality target that belongs in canonical decisions, and route via Handoff.

Required output:
1. AI_EVAL_PLAN.md with: measurable success criteria, the dataset spec (size, sourcing, label schema, split), the per-criterion grading tier (code vs LLM-judge), the pass threshold and regression rule, and the three boundaries.
2. The list of criteria still lacking a measurable definition (if any), each with the question to resolve.
3. The dataset bootstrap plan when no labeled set exists (sourcing, minimum viable size, labeling approach).
4. Recommended next command (must exist in `commands/*.md`; verify against directory listing before output). Typical choices: `test-strategy` (deterministic behavior for the same change), `implementation-plan` (slice the harness build), `decision-interview` (lock the quality target), `implement-approved-slice`, and for a user-facing or risky feature `release-plan` (to gate the staged rollout on the live proxy metric this eval's offline pass precedes).

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- AI_EVAL_PLAN.md exists with measurable success criteria, a dataset spec (no train/eval leakage), a per-criterion grading tier, and a pass threshold with a regression rule.
- Every success criterion is measurable, or is explicitly marked as NEEDS a measurable definition with the question to resolve; no vague criterion is left as a pass target.
- The three boundaries (vs test-strategy, vs verify-against-rubric, vs ADR-0048) are stated in the plan.
- A deterministic-only feature is routed to test-strategy rather than given an eval plan.
- The command plans the eval; it does not build or run the harness.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A load-bearing eval plan names a measurable target and a grading method for every success criterion, so the team can tell pass from fail without re-litigating "is this good". The failure mode it prevents is the AI feature that ships on vibes: no held-out set, no threshold, and a quality regression that only surfaces as user complaints because nothing ever scored the output. Grading discipline matters: reach for an LLM judge only when a program genuinely cannot score the criterion, because an LLM-graded criterion is slower, costlier, and itself needs a locked rubric; objective criteria belong in the code-graded tier where they bank Layer-1 evidence under ADR-0048. The plan stays in its lane: it designs the eval and routes the build to implementation-plan; it never quietly becomes the harness.

<!-- cache-breakpoint -->

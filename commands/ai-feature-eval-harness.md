---
name: ai-feature-eval-harness
description: Design an evaluation plan for a product AI feature (LLM- or model-backed output): measurable success criteria, a held-out labeled eval dataset shape, per-criterion grading (code-based first, then LLM-based for nuanced judgment), and a pass threshold, then persist as AI_EVAL_PLAN.md. Use when the task ships or changes a feature whose output is model-generated or non-deterministic (assistant reply, classification, extraction, summarization, ranking, agent action) and needs a repeatable dataset-backed eval rather than only example-based tests. Do not use when the feature has no model-backed output (use test-strategy for deterministic behavior), when judging Fhorja's own command outputs against a rubric (use verify-against-rubric), or when no active task folder exists. The code-graded tier composes with ADR-0048 (a passing deterministic gate is Layer-1 evidence); the LLM-graded tier is added signal, not a replacement.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5-5
---
# ai-feature-eval-harness

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
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

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
- TASK_STATE.md only when state materially changes (per the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section write pattern); otherwise prefer `/sync-task-state` after execution

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04):** for every write to a substrate section (the <!-- count:task-memory-files -->4<!-- /count --> task-memory files plus the fleet-substrate files per `wos/substrate-peers.md ## Fleet-substrate files`), emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. Enforced, not shadow mode: `scripts/verify-substrate-batch.sh` blocks closure at `slice-closure` and `task-close` (`wos/closure-floors.md`).
- Do not implement code; this command plans the eval, it does not build or run the harness.
- **Step 1: Gate on a model-backed output.** Confirm a model's output sits somewhere in the feature's path. STOP and route to `test-strategy` ONLY when NO model output is anywhere in that path (pure function, CRUD, fixed rules with no model); do not author an eval plan for purely deterministic behavior. A component that is deterministic in execution but whose output quality depends on a model (embedding-based or lexical retrieval graded empirically for hit-rate, temperature-0 calls, a ranking layer feeding a model) stays IN scope and lands in the code-graded tier: retrieval quality for a RAG feature is the canonical example, and refusing it on "deterministic" grounds is the misread this sentence exists to prevent.
- **Step 2: Define measurable success criteria.** State each criterion as a measurable target (e.g. "extraction F1 >= 0.9 on the gold set", "refusal rate <= 1% on the safe-prompt set", "p95 latency <= 2s", "cost per call <= the locked target"). Reject vague criteria ("good answers"); restate them measurably or mark them as NEEDS a measurable definition.
- **Step 3: Specify the eval dataset.** Define the held-out labeled set: size, how cases are sourced (production samples, synthetic, adversarial edge cases), the label schema, and the split with no train/eval leakage. When no dataset exists, name how to build the first version and a minimum viable size. When the feature already runs in production, an OpenTelemetry-based LLM tracing layer (for example OpenLLMetry) is a natural source for the production samples and for the trace-to-dataset flywheel, where each captured failure becomes a labeled regression case. A hosted LLM-observability stack such as Langfuse (MIT-licensed core: tracing, evals, prompt management) is an example a consuming product team might adopt for its own running app; operating that stack is explicitly out of Fhorja scope, which plans the eval rather than running one.
- **Step 4: Choose a grading method per criterion, cheapest reliable first.** Code-based (exact match, regex, a metric like F1 or BLEU) for objective criteria; LLM-as-judge with a locked rubric only for nuanced criteria a program cannot score. State which tier grades each criterion.
- **Step 5: Set the pass threshold and the regression rule.** Define the suite-level pass bar and what a regression triggers (block ship, accept with a documented waiver, or expand the set). Tie the code-graded tier to the consuming repo's ADR-0048 deterministic gate. The slice that ships or changes the model-backed feature MUST carry an EARS exit criterion keyed to this plan's pass threshold (the score against the threshold on the held-out set), never to the harness mechanism ("the harness runs" is not an exit criterion); the closure homes enforce this as the eval-threshold floor (ADR-0104). When the feature ships behind a staged rollout, state this offline pass threshold as `release-plan`'s promotion-metric precondition, not its substitute: name a live proxy metric (thumbs-up rate, escalation rate, or an A/B delta) that `release-plan` gates the ramp on, so a passed offline eval has a signposted path into the rollout gate. The offline pass is necessary, not sufficient, for promotion.
- **Step 6: State the three boundaries explicitly in the plan.** (a) vs `test-strategy`: deterministic behavior tests, not model-output scoring. (b) vs `verify-against-rubric`: that judges Fhorja's own command artifacts, this scores a user's product feature against a dataset. (c) vs ADR-0048: the code-graded tier IS Layer-1 evidence; the LLM-graded tier is added signal, not a replacement.
- **Step 7: Persist and route.** Persist AI_EVAL_PLAN.md (APPLIED). Stage a PROPOSED DECISIONS.md block for any locked quality target that belongs in canonical decisions, and route via Handoff.

Required output:
1. AI_EVAL_PLAN.md with: measurable success criteria, the dataset spec (size, sourcing, label schema, split), the per-criterion grading tier (code vs LLM-judge), the pass threshold and regression rule, and the three boundaries.
2. The list of criteria still lacking a measurable definition (if any), each with the question to resolve.
3. The dataset bootstrap plan when no labeled set exists (sourcing, minimum viable size, labeling approach).
4. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify against directory listing before output). Typical choices: `test-strategy` (deterministic behavior for the same change), `implementation-plan` (slice the harness build), `decision-interview` (lock the quality target), `implement-approved-slice`, and for a user-facing or risky feature `release-plan` (to gate the staged rollout on the live proxy metric this eval's offline pass precedes).

### Substrate digest fallback
<!-- shared:substrate-digest-fallback -->
**Digest fallback when the canonical helper is unreachable.** `sha_of_section` extracts a section's body with `awk` and pipes it to `shasum -a 256`. A run executing inside a permission boundary that admits `shasum` but refuses `awk` and `sed` cannot invoke that helper, and MUST NOT reimplement it: an `awk` or `sed` program operand can call `system()` and write files, so a boundary that refuses those verbs refuses them for a reason. Assume the helper is unreachable whenever the workflow repository's `scripts/` directory is not readable from the working directory.

WHERE the canonical per-section digest helper is unreachable, the write SHALL use a whole-file SHA-256 and SHALL declare the reduced scope:

```bash
# One call per file. `shasum -a 256 <file>` needs no extraction step, so no
# refused verb is involved. Read the hash (the first field) out of the output;
# do not pipe it through `cut` or `awk` to trim it.
shasum -a 256 TASK_STATE.md
```

Then add `"sha_scope":"file"` to that JSONL line, so a validator distinguishes a file digest from a section digest instead of inferring it. Everything else about the protocol is unchanged: the transaction header still goes above the section heading, and there is still exactly one JSONL line per section write.

Do NOT rebuild the helper by writing each section out as its own file so it can be hashed separately. That workaround is coherent and it is what this rule exists to prevent: a 2026-08-04 run wrote 31 numbered section fragments to compute per-section digests by hand, spent the whole run doing it, and produced no product code.

What the fallback costs, stated so the trade is explicit rather than discovered later: the digest chain exists to detect an unlogged change to a SECTION. At file scope, two sections written in the same run share a digest, so the chain detects tampering with the file without attributing it to a section. That is a declared reduction in resolution, not a silent one, which is why the `sha_scope` field is mandatory rather than optional.
### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- AI_EVAL_PLAN.md exists with measurable success criteria, a dataset spec (no train/eval leakage), a per-criterion grading tier, and a pass threshold with a regression rule.
- Every success criterion is measurable, or is explicitly marked as NEEDS a measurable definition with the question to resolve; no vague criterion is left as a pass target.
- The three boundaries (vs test-strategy, vs verify-against-rubric, vs ADR-0048) are stated in the plan.
- A deterministic-only feature is routed to test-strategy rather than given an eval plan.
- The command plans the eval; it does not build or run the harness.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A load-bearing eval plan names a measurable target and a grading method for every success criterion, so the team can tell pass from fail without re-litigating "is this good". The failure mode it prevents is the AI feature that ships on vibes: no held-out set, no threshold, and a quality regression that only surfaces as user complaints because nothing ever scored the output. Grading discipline matters: reach for an LLM judge only when a program genuinely cannot score the criterion, because an LLM-graded criterion is slower, costlier, and itself needs a locked rubric; objective criteria belong in the code-graded tier where they bank Layer-1 evidence under ADR-0048. The plan stays in its lane: it designs the eval and routes the build to implementation-plan; it never quietly becomes the harness.

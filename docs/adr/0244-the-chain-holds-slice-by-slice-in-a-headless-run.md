# ADR-0244: The chain holds slice by slice in a headless run

- **Status**: Accepted. The mechanism rests on provisional decisions of the 2026-09-30 benchmark-driven-chain-fixes task (P-5, P-7, P-11, P-13, P-16, P-20), listed under `## Notes`. P-16 (standing authorization, with no configured remote) is confirmed by that task's locked D-2; P-5, P-7, P-11, P-13 and P-20 still await the maintainer's confirmation. How a closing command writes the `Status:` line is amended by [ADR-0246](./0246-the-brief-silent-blind-reading-was-measured-and-removed.md): one helper call edits the line and logs it, and a Status write is still not a plan revision. Fresh context per slice (P-6) was taken out of this decision by the task's locked D-1 and is deferred (see `## Notes`).
- **Date**: 2026-09-30
- **Amends**: by reference, [ADR-0237](./0237-a-launched-background-session-is-the-attended-flow.md) and the unattended doctrine it carries in `wos/cross-cutting-workflow-guardrails.md`, for one case: a session a person launched for this task, with no configured remote, whose brief grants standing authorization. The five ADR-0237 conditions stand unchanged for every other session.
- **Amends**: by reference, the Layer-2 review floor of [ADR-0209](./0209-floors-do-what-they-declare.md) and the internal-reuse sweep floor of [ADR-0145](./0145-a-zero-finding-verdict-is-not-terminal.md), on what counts as a host-repository gate.
- **Tags**: chain-adherence, headless, unattended, slice-order, closure-floors, benchmark, measured

## Context

On 2026-09-29 the maintainer ran one brief (a local-first budget web app in Next.js, with a long
list of features and heavy motion) through four models, twice each: once with Fhorja installed plus
the agent directive, once with no workflow. Every run was headless: the brief said nobody would
answer, decide and write the decision down, and commit locally. There was no remote. One run per
cell, so every difference below is a single observation.

What the Fhorja arm did with the chain:

- The two Claude runs invoked `task-init`, `implementation-plan`, `approve-plan` and
  `implement-approved-slice` in the first 5 to 9 minutes. The slice command's reference-grounding
  gate then routed to `capture-references`. After that detour neither run invoked another Fhorja
  command: the remaining 9 or 10 slices ran as narration inside that one skill load, with no
  Handoff, no `slice-closure`, no `review-hard`, no `web-runtime-verify` and no `task-close`.
- The two Codex runs followed the chain much further (`web-runtime-verify`, `review-hard` with
  sub-agents, `branch-commit`; one also ran `task-close` and `harvest-session-learnings`). They
  wrote in their task state that the brief's instruction overrode the unattended stop rules.
- One Claude run quoted the unattended doctrine directly ("Pipeline not bound"): with no remote the
  session fails ADR-0237's third condition, is unattended, and the apply commands refuse, so the
  end of the chain was blocked by construction.
- The Claude runs never compacted. The Sonnet Fhorja run made 166 model calls against 74 for its
  base run, with a mean context of 343k tokens against 176k and a maximum of 558k. That, not the
  skill listing (about 8k tokens per call), is why it cost 3.3 times its base run.

What the text allowed:

- Next-slice routing lives only in the Handoff (`commands/implement-approved-slice.md`, the
  sequential-slices bullet). Nothing refuses a slice whose dependencies are unclosed, and a detour
  has no return address, so an agent that stops printing Handoffs leaves the chain silently.
- The Layer-2 floor and the internal-reuse floor accept "the host repository's own equivalent gate,
  cited by whatever name it carries there". A general-purpose reviewer the agent dispatched itself
  counted.
- The web runtime routing rule sits in a conditional paragraph whose detail is in a lazily loaded
  topic that neither Claude run read.

## Decision

A long run stays on the chain at the points where it left it, without depending on the agent
printing a Handoff:

- **Dependency gate (P-7).** `implement-approved-slice` runs `scripts/check-slice-order.sh` before
  it starts a slice. The script exits 1 when a slice named in that slice's `Depends-on:` has no
  closure record, and the command refuses and routes to `slice-closure` for it. It checks
  `Depends-on:`, not every earlier slice, so wave-parallel slices under `implement-fleet` are not
  refused.
- **Closure record (P-11, P-13).** Every command that closes a slice writes `Status: closed` for it
  in `IMPLEMENTATION_PLAN.md ## Slices`: `implement-approved-slice` on an inline close,
  `slice-closure` always, and the `implement-fleet` orchestrator for each merged slice before the
  next wave. That Status is the only closure record the gate reads; a hand-written `done` in a plan
  written before this decision also counts. A Status write is not a plan revision, so the approval
  lock reads the last `## Slices` revision from `.wos/VERIFICATION_LOG.jsonl`, never from the
  section's header, and a fleet event (a merge or a worker classification) logged with a null sha leaves the section's sha-chain
  position unknown, so the Status write after it is not a chain break.
- **Detour return (P-5).** When the reference-grounding gate routes to `capture-references`,
  `capture-references` hands back to `implement-approved-slice` for the same slice.
- **Standing authorization (P-16).** A session with no human respondent that meets ADR-0237
  conditions 1 and 2 (a person launched it for this task; it is neither `autonomous-run` nor a
  fleet worker), whose brief that person wrote explicitly authorizes the agent to decide without
  asking and to commit locally, records open decisions as provisional `### P-N`, records a check it
  cannot run on itself as `unverified:`, runs `branch-commit --apply` to a local commit on a task
  branch, and runs `task-close`, which lists those decisions and checks in its final report. It
  relaxes only ADR-0237's configured remote, so it applies only with no configured remote: a
  session with a remote that meets all five ADR-0237 conditions is attended and keeps the draft-PR
  path whatever its brief says. Every outward act stays refused, and it never merges. A brief with no such authorization
  keeps the PROPOSED stall, and every command that stalls such a session names this case as the one
  exception.
- **Each floor keeps its own review (P-20).** The Layer-2 floor keeps `review-hard` (plus
  `security-review` on a security surface, and the `verify-against-rubric` id where the
  zero-finding rule requires it), and the internal-reuse floor keeps `repo-consistency-sweep`. The
  review a floor names counts whether it ran inline or in a dispatched sub-agent, when its artifact
  is cited, and the explicit skip reason still counts; a host gate counts only through an artifact
  it produced; a review that followed no Fhorja contract never counts.
- **Inline runtime rule.** The web runtime routing rule is a one-line hard rule inside
  `implement-approved-slice`: when a build can be served or a backend probed, it routes to
  `web-runtime-verify` or `api-runtime-verify` before the inline close.

## Consequences

### Positive

- An agent that stops printing Handoffs meets the gate the next time it starts a slice through the
  command, and a detour returns it to the command, which is the path the Claude runs lost.
- A headless run with standing authorization finishes its chain locally instead of reading the
  doctrine as a stop.

### Negative

- P-16 widens what an unwatched session may do. A person has to launch it and write the
  authorization, decisions stay provisional, and outward acts stay refused, but a session nobody
  watches can now commit locally.
- A host gate that produced no artifact no longer counts for the floors.

### Neutral

- The gate cannot fire in a run that never invokes `implement-approved-slice` again; the detour
  return is what brings the agent back to it. A run that ignores both is still possible, and the
  rerun measures how often it happens.

## Alternatives considered

### A git hook in the product repository

- A pre-commit hook would refuse a commit for a slice whose predecessor has no closure record, and
  it fires on an act every run performs.
- Rejected: Fhorja does not install into product repositories' hooks, and the hook does not run on
  harnesses without git hooks. Kept as a candidate if the rerun shows the command-side gate is not
  enough.

### Always compact between slices

- Cheaper than a sub-agent per slice, and a compaction carries a summary of the accumulated
  history where a fresh sub-agent starts from the substrate.
- Not decided here: it goes with the rest of per-slice context bounding to the later task
  (see `## Notes`, D-1).

### Tell headless briefs to add a remote

- Would make the session pass ADR-0237's third condition.
- Rejected: a real headless user brief has no remote either, and the doctrine would still read the
  brief's authorization as a self-answer.

## Notes

- Provisional decisions this rests on, from the benchmark-driven-chain-fixes task: P-5 (detour
  return), P-7 (dependency gate), P-11 (every closing command writes the plan Status, the only
  closure record), P-13 (the approval lock ignores Status writes), P-16 (standing authorization
  for a session a person launched, with no configured remote, Impact: high; replaces P-4), P-20
  (each review floor keeps its own contracts; replaces P-15, which replaced P-10). The maintainer
  confirms or replaces them on the draft pull request.
- Deferred by D-1 (locked by the maintainer on 2026-09-30): fresh context per slice. An earlier
  draft of this decision ran each slice of a plan with 4 or more sequential slices in a freshly
  dispatched sub-agent (P-6), with an authority split between that sub-agent and the session that
  dispatched it (P-17 to P-19). D-1 removed both from the task and supersedes P-6 and P-19: the
  split was the source of the review spiral, and the planned rerun (a model whose harness compacts
  on its own) would barely exercise it. Per-slice context bounding goes to a later task decided on
  the rerun's data. The context cost in `## Context` is the fact that task starts from.
- Revert condition: a rerun of the same brief shows no gain in chain adherence, or a cost increase
  with no quality gain.

## References

- [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md): the attended chain on a task branch.
- [ADR-0237](./0237-a-launched-background-session-is-the-attended-flow.md): the attendance test amended here.
- [ADR-0209](./0209-floors-do-what-they-declare.md) and [ADR-0145](./0145-a-zero-finding-verdict-is-not-terminal.md): the floors amended here.
- [ADR-0243](./0243-implement-fleet-is-the-default-for-a-parallel-wave.md): why the gate reads `Depends-on:`.
- `commands/implement-approved-slice.md`, `commands/capture-references.md`, `scripts/check-slice-order.sh`, `wos/closure-floors.md`, `wos/cross-cutting-workflow-guardrails.md`.

# Roadmap

This document describes the high-level direction of the project across its phases. It is non-binding and may change based on user feedback, maintainer bandwidth, and shifts in the AI engineering ecosystem.

For granular changes per release, see [CHANGELOG.md](./CHANGELOG.md).

## Project status

**Currently at 2.0.0**, released and tagged `v2.0.0` on 2026-09-28. The project passed 1.0.0 on 2026-07-10 and 1.1.0 on 2026-07-21. The contract for command outputs and `TASK_STATE.md` is the defined public API: a breaking change to either requires a major version bump under SemVer, which is why the `Tier:` to `Escalations:` change made the release after 1.1.0 a 2.0.0.

The project is maintained as a personal open-source effort under BDFL governance. See [CONTRIBUTING.md](./CONTRIBUTING.md) for what that implies.

## Release strategy

The project follows a phased release strategy to balance refinement quality with public exposure:

- **Phase 1 (private refinement, done)**: internal use, testing, and polishing. License, contributor guides, examples, lint script, and CI were prepared ahead of the public release in Phase 3.
- **Phase 2 (private beta, dropped 2026-08-30)**: it was to be 1 to 2 months of beta testing with 5 to 10 invited developers before going public. It was overtaken by events: Phase 3 shipped the repository public and Phase 4 reached v1.1.0 while this phase still read `planned`, so the gate it was meant to be had already been passed without it. Declared dead with a date rather than left pending, because a phase that cannot happen before the phase after it is not a plan.
- **Phase 3 (public MIT, done)**: repository made public, first version tagged, announced to relevant communities.
- **Phase 4 (stabilization, in progress)**: continued open-source releases (1.1.0 shipped 2026-07-21 and 2.0.0 shipped 2026-09-28; see [CHANGELOG.md](./CHANGELOG.md)), community growth, and API stability toward a mature contract.
- **Phase 5 (Layer 2 SaaS, exploratory)**: separate hosted service that builds on top of the open-source workflow. No commitment yet.

## Waves 1 to 3 (closed)

The three build-out waves are done, and [CHANGELOG.md](./CHANGELOG.md) records what each delivered, so this section keeps only what a reader still needs.

- **Wave 1, foundation**: MIT license, contributor and security policies, issue and PR templates, the command lint and CI, the [FAQ](./docs/FAQ.md), the [migration guide](./docs/MIGRATION.md), and the first ADRs in [`docs/adr/`](./docs/adr/).
- **Wave 2, refinement**: the editor mode mapping, Agent Skills generated from `commands/*.md` by `scripts/build-agent-skills.sh`, and the short flows for docs-only, test-only and refactor tasks, now in [`wos/workflow-shapes.md`](./wos/workflow-shapes.md). The sync script installs the skills by default since 2026-07-18; `--with-skills` is kept for backward compatibility and `--no-skills` opts out. Two items stayed partial and are closed here. The auto-sync trigger for PROPOSED-but-not-applied turns is superseded: since ADR-0199 task memory is written `APPLIED` in every mode, so those turns no longer pile up, and the optional session-continuity hook (ADR-0052) covers the session boundary. The lazy-loaded spec work cut the spec about 29 per cent by the May 2026 measurement; the spec has grown since, and ADR-0136 now holds it under a non-regression ceiling of 126,000 chars instead of chasing a smaller target.
- **Waves 2.5 to 2.8**: the context engineering uplift (ADR-0012 to ADR-0023), `approve-proposed` (ADR-0024), `repo-consistency-sweep` with its bug-class library, and the design-system command family.
- **Wave 3, expansion**: the eval harness at [`evals/`](./evals/), now <!-- count:scenarios -->142<!-- /count --> scenarios indexed in [`evals/README.md`](./evals/README.md); operating modes; `incident-triage`, `external-research`, `delivery-asset` and `db-context-supabase`; multi-repo support v1.

Still open from Wave 3:

- [~] Multi-repo support v2: `implement-approved-slice`, `slice-closure` and `where-we-at` became multi-repo-aware on 2026-06-04; `targeted-questions`, `implement-slice-complement`, `pr-feedback-ingest` and `post-review-pivot` remain single-repo only.

## Phase 4: Stabilization (target: ongoing after the public release)

- [ ] API stability toward a mature contract (command output shape and `TASK_STATE.md` schema)
- [ ] Community growth: issues, discussions, and outside contributions under MIT + DCO
- [ ] Broader editor coverage validated against the open Agent Skills standard

## Phase 5: SaaS layer 2 (exploratory, no commitment)

A separate hosted service that builds on top of the open-source workflow. Concept under exploration:

- Receive a project zip or Git repo
- Run task-init and discovery commands automatically
- Suggest stack, scaffold initial code
- Run tests and validation in sandboxed environment
- Generate downloadable result + integrate with the user's GitHub for the final commit

If pursued, the SaaS would build on the MIT-licensed workflow as its Layer 1 and offer functionality the markdown workflow alone cannot provide (server-side execution, sandboxing, persistence).

This is exploratory and depends on adoption signals from Phases 3-4.

## Multi-agent maturity (after the 2026-06-05 design test)

These two tracks are not release phases. They used to be numbered Phase 6 and Phase 7, which collided with the Phase 6 of the spec's default workflow, so they carry names instead.

**Design subsystem lived test (done 2026-06-05).** `screen-spec-fleet` ran on a private design handoff: 5 Figma frames, 26 parallel agents, about 1.3M subagent tokens and 12 minutes wall-clock. It produced 5 screen specs, an atom inventory of 53 atoms, a route map, and a foundations seed through `extract-foundations-from-screens`. That run is the empirical baseline the objectives below build on.

**Objectives**, last reviewed 2026-09-23:

- Done: K.8 persona promotion. All five original K.8 personas are at L3 (see `wos/maturity-ladder.md`; the per-persona ledgers are maintainer-local and gitignored).
- Superseded: the ADR-0038 fleet compliance pass. Rule 1 of ADR-0038, the return mechanism, was replaced by ADR-0158, and in September 2026 all seven fleet commands were realigned to it (typed runtime results or their assigned JSON return files), with a structural guard that rejects the old return mandates. What stays open is a lived run of each fleet command, which no audit can substitute for.
- Open: production-grade monitoring. `scripts/monitor-fleet-progress.sh` exists (see `docs/MIGRATION.md` and `wos/entry-points.md`); wiring it to retry and escalation hooks, so a stuck or timed-out subagent triggers a defined recovery (retry once, then escalate to the operator) instead of silently stalling a batch, is not done.
- Open: multi-tool support. The fleet path is Claude Code only. Investigate equivalent primitives in Cursor and OpenAI Codex (sub-agent dispatch, parallel run isolation, a typed return path), document the gap per tool, and decide which primitives to wrap behind a tool-neutral adapter.
- Open: quantitative cost models per batch size. ADR-0039 records an observed range of 400k to 1.3M subagent tokens per batch but no estimate per batch size, and no other ADR carries one yet (ADR-0040 is the single-writer-per-folder exception for `task-init-fleet`, not a cost model).

## How to influence the roadmap

- For specific feature requests, open an issue using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).
- For broader direction discussions, open a GitHub Discussion.

The maintainer makes final decisions on roadmap priorities. There is no SLA on changes or fulfillment of requested features.

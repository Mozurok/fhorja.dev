# ADR-0099: Plan-time design-surface routing and the pre-deploy experience-preview gate

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: frontend-cluster, experience-gate, design-routing, preview, release-plan, implementation-plan, closure-enforcement, dogfood-driven, refines-adr-0091, site-dogfood

## Context

The 2026-07-10 to 2026-07-12 fhorja.dev landing-page build (audited as the site dogfood) exposed three gaps in how the workflow handles a public-facing visual surface, all caught by the human rather than the workflow:

1. On a frontend-heavy task the core lifecycle (task-init to implementation-plan to implement-approved-slice) routed straight to building raw sections. The rich design cluster (screen-spec, journey-map, design-bootstrap, image-to-spec, component-spec, a11y-audit, color-contrast-architect) went unused for the first build, and the result was flat: the maintainer's own words were "muito pobre e totalmente sem graça," and he noted the WOS had frontend commands "parece que nem chegamos a usar eles." Every quality jump across roughly eight elevation loops was human-initiated; the workflow never set or self-enforced a showcase-grade bar.

2. The generalized experience-verdict floor (ADR-0091) already requires a recorded human verdict on a sample of a `user-facing-content` / `new-user-facing-surface` deliverable, but the workflow gives no supported way to produce that sample. The reviewer improvised an ngrok tunnel, hit a `403 This host is not allowed` (the Vite/`astro preview` host-check), fell back to a plain static server, and by the time it worked had walked back to his desk. The gate existed; the preview mechanism that feeds it did not.

3. The experience-verdict floor is closure-scoped (it fires at slice-closure / task-close when a tagged slice closes). It does not gate the approach to launch prep. Mid-session the flow was heading toward a11y-audit, performance-budget, release-plan, and domain-attach-equals-announcement (D-3) before the maintainer had ever seen the site. He caught it with "voce ja esta querendo ir para o deploy sem nem eu validar?"; the workflow did not.

These are complementary to ADR-0089/0091/0098 (the feel-verdict and experience-verdict closure floors and their skip-reason semantics), not a duplicate: this ADR is about routing a visual surface through design at plan time, producing the preview the human verdict needs, and gating the deploy path, not about the closure-floor skip escape.

## Decision

Three additive changes, one fold, no new command:

1. **Plan-time design-surface routing (F1).** `implementation-plan` gains an operating rule: WHEN a deliverable in scope is a user-facing visual surface (tagged `user-facing-content` / `new-user-facing-surface`, or plainly evident), the plan routes through the applicable design-cluster commands AND grounds the visual direction in captured references before slicing the visual build; a plan that slices a visual surface with neither is flagged and routed, not silently sliced. Capability-routed; an internal CRUD form or docs page does not fire it. This also lands F6 (the quality bar for a showcase surface is set at plan time, reference-grounded, rather than discovered through repeated human elevation loops).

2. **A preview-surface protocol (F2).** A new lazy-loaded topic `wos/frontend-preview-and-experience-verdict.md` documents the repeatable way to serve a built frontend for a human to view (local preview of the production build; a remote tunnel when the reviewer is away; the Vite/`astro preview` `allowedHosts` host-check gotcha and the plain-static-server fallback; and recording the verdict against the exact URL and build). The experience gates reference it so the human always has a supported way to produce the sample. No new command.

3. **A pre-deploy experience-preview gate (F3).** `release-plan` gains a Step 1.5 floor: a rollout shipping a `user-facing-content` / `new-user-facing-surface` deliverable is not finalized for deploy without at least one recorded human preview (a cited `## Experience verdict` PASS, or a cited preview run per the new topic) or an explicit skip reason; machine-green evidence does not substitute. This moves part of the ADR-0091 floor ahead of the deploy path. It stands down under the Godot task signature in favor of the ADR-0089 D-4 feel-verdict floor.

## Consequences

### Positive

- A public-facing visual surface is routed through design and grounded in references at plan time, raising the floor so it does not ship flat and get elevated only through many human review loops.
- The experience-verdict floor becomes satisfiable in practice: the human always has a supported, gotcha-aware way to produce the preview they verdict on.
- A public surface cannot march to deploy-prep with zero recorded human preview; the gate, not the human, catches the race to deploy.

### Negative

- One more gate on the release path for user-facing surfaces. It is skippable with an explicit one-line reason (same low-ceremony escape as the closure floors, narrowed by ADR-0098's bounded-vs-permanent rule), so a genuine no-preview-surface case stays cheap.
- `implementation-plan` does more before slicing a visual surface. This is the intended effect (the flat-first-build failure), but it adds a design-routing step to a plan that previously went straight to slices.

### Neutral

- No new command; two existing commands gain one rule each and one new reference topic is added (`count:wos-topics` 35 to 36). The closure-time experience-verdict floor (ADR-0091) is unchanged; this adds a plan-time entry and a pre-deploy gate around it.

## Alternatives considered

### Alternative 1: a new `preview-surface` command for F2

- Rejected: the serve step is a recipe, not a workflow phase; a lazy-loaded topic the gates reference is lighter and avoids adding command surface for a mechanic (consistent with the anti-command-bloat instinct the site dogfood's own F7 finding raised).

### Alternative 2: put the F3 gate in the closure floors (slice-closure / task-close) instead of release-plan

- Rejected: the failure was racing toward the deploy path, so the deploy-prep command (`release-plan`) is the correct home; the closure floors already fire at close, and duplicating there would double the gate without covering the launch-approach case.

### Alternative 3: hard-block F1 (refuse to plan a visual surface without design routing) instead of flag-and-route

- Rejected as heavier than the evidence warrants: flag-the-gap-and-route preserves operator judgment for a genuinely simple surface while still surfacing the missing design step, matching how the plan handles other missing inputs.

## References

- Site dogfood audit (`project_wos_site_dogfood_audit` memory; scratchpad `DOGFOOD_AUDIT_fhorja-site.md`): findings F1, F2, F3, F6.
- Transcript `11383704-c2bc-4feb-8a2e-3d1e3d0ad7f2.jsonl`: turn 45 (racing to deploy), turn 47 (flat first build, frontend cluster unused), turns 91-93 (the ngrok/allowedHosts preview pain).
- ADR-0091 (the generalized experience-verdict floor this refines), ADR-0089 (the Godot feel-verdict floor it stands down to), ADR-0098 (the skip-reason bounded-vs-permanent rule), ADR-0065 to 0068 (the frontend cluster it routes to), ADR-0043 (reference grounding).
- `commands/implementation-plan.md`, `commands/release-plan.md`, `wos/frontend-preview-and-experience-verdict.md`.
- Eval scenarios 105 (design-surface routing) and 106 (pre-deploy experience-preview gate).

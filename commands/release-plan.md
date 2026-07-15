---
name: release-plan
description: Design a pre-deploy release and rollout strategy for a change: pick the rollout pattern (feature flag, canary, blue-green, or full progressive delivery) by risk and infra, then specify the exposure ramp, the promotion metric and threshold that advances each step, and the rollback trigger and mechanism. Produces RELEASE_PLAN.md. Use when a change is approaching deploy and needs a deliberate rollout (user-facing, risky, or hard to reverse). Do not use for post-deploy live-signal verification (use post-deploy-verifier, which consumes this plan's promotion metric and rollback mechanism), for the standing pipeline's rollback-existence audit (reserved for the future pipeline-gate-review), or for a trivial fully reversible change with no rollout concern. Stack- and infra-agnostic; it designs the rollout, it does not execute it. A gated --godot-mobile mode (ADR-0069) plans an asymmetric Android and iOS Godot 2D-mobile store ship (export toolchain, preflights, store gotchas), off by default.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---
# release-plan

Act as a senior release engineer designing how a change reaches production safely, before it ships.

Goal:
Design the pre-deploy rollout strategy so a change is exposed deliberately, advanced on evidence, and reversible on a known trigger, instead of shipped all at once and rolled back by improvisation. The load-bearing differentiator is the per-change rollout design: the pattern chosen by risk and infra, the exposure ramp, the promotion metric that advances each step, and the rollback trigger and mechanism, all decided before deploy. It is distinct from post-deploy-verifier (which verifies live signals AFTER ship and consumes this plan's promotion metric and rollback mechanism) and from the future pipeline-gate-review (which audits whether the standing pipeline even has a safe rollback mechanism). The deliverable is a RELEASE_PLAN.md no other command produces. Use when a slice's scope touches a login, auth, or biometric surface and is approaching merge to main, even for a small-looking change.

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
- the change under release and its blast radius (user-facing surface, schema/data impact, reversibility)
- the available infra for rollout (feature-flag system, traffic routing, parallel environments, metrics for gating); when absent, the plan degrades to a manual go/no-go
- optional: the SLO_SPEC.md (from slo-define) to use as the promotion-metric basis
- optional: `--godot-mobile` to plan a Godot 2D-mobile store ship (Android + iOS) instead of an infra rollout, including the 2026 store-compliance gate (Play Data Safety, target API 35, iOS privacy manifest, ATT, Restore Purchases) (DECISIONS D-5, D-6, ADR-0069; off by default)
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update (only if materially changed):
- RELEASE_PLAN.md
- TASK_STATE.md only when state materially changes (per the canonical 5-section write pattern); otherwise prefer `/sync-task-state` after execution

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04):** for every write to a substrate section (the 4 task-memory files plus the fleet-substrate files per `wos/substrate-peers.md ## Fleet-substrate files`), emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. Shadow mode at launch -- writers emit, no reader enforces.
- Do not implement code or run a deploy; this command designs the rollout, it does not execute it.
- **Step 1: Gate on a rollout-worthy change.** If the change is trivial and fully reversible with no exposure concern (internal tooling, a copy fix, a pure refactor), STOP and return a SKIP/NO_OP verdict routing to the normal delivery path (branch-commit / pr-package); do not manufacture a rollout plan for a change that does not need one.
- **Step 1.5: Pre-deploy experience-preview gate (site dogfood F3, ADR-0099).** WHEN the rollout ships a deliverable tagged `user-facing-content` or `new-user-facing-surface` (or plainly a user-facing visual surface even when untagged), this release plan SHALL NOT be finalized for deploy without at least one recorded human preview: a cited `## Experience verdict` with `Overall: PASS`, OR a cited preview run the reviewer saw (serve the build per `wos/frontend-preview-and-experience-verdict.md`), OR an explicit one-line skip reason. Machine-green evidence (build exit 0, lint, tests) SHALL NOT substitute. IF none is present THEN classify the release `not ready to deploy`, name the missing preview, and route the operator to produce it before proceeding to Step 2. This moves part of the ADR-0091 experience-verdict floor ahead of the deploy path so a public surface cannot march to deploy-prep with zero human preview (the site-dogfood failure: the flow headed toward domain-attach-equals-announcement before the maintainer had ever seen the site; the human, not the workflow, caught it). WHILE the Godot task signature is present this gate stands down in favor of the D-4 feel-verdict floor at closure.
- **Step 2: Pick the rollout pattern by risk and infra.** Reason over the abstract model (exposure unit, advance signal, rollback action), not a specific vendor: two parallel environments favor blue-green (instant router-flip rollback); fractional traffic routing favors canary; app-level conditionals favor feature flags; reliable live metrics unlock full progressive delivery (metric-gated auto-promote/rollback). A schema or data-shape change needs a flag plus an expand-contract path. Name the chosen pattern and why, mapping each primitive to the consuming repo's actual mechanism (named only from what the repo states, never invented).
- **Step 3: Specify the exposure ramp.** The concrete steps (feature-flag cohort percentages, canary percentages with widening steps, or the blue-green switch point) and who is in the first cohort. Each step has an entry and an advance condition.
- **Step 4: Define the promotion metric and threshold.** The metric and bound that advances each step. WHEN an SLO_SPEC.md exists (from slo-define), use the SLO as the promotion-metric basis; otherwise name the metric and mark its threshold PROPOSED-pending-baseline rather than inventing a number.
- **Step 5: Define the rollback trigger and mechanism.** The observation that triggers rollback and the exact mechanism for the chosen pattern (router flip, flag off, traffic to 0%). This mechanism is what `post-deploy-verifier` consumes for its post-deploy rollback-trigger checklist (per DECISIONS.md D-1).
- **Step 6: Build RELEASE_PLAN.md.** Sections: chosen pattern + rationale, exposure ramp (steps + advance conditions), promotion metric + threshold, rollback trigger + mechanism, and a go/no-go checklist gated before first exposure.
- **Step 7: State the D-1 boundary and route.** In the plan, state that release-plan owns the per-change rollout design; post-deploy-verifier consumes the promotion metric and rollback mechanism for the post-deploy trigger; the standing-pipeline rollback-existence audit is out of scope (reserved for the future pipeline-gate-review). Stage a PROPOSED DECISIONS.md block for any rollout policy that should be locked, and route via Handoff.
- **Godot mobile export-and-ship mode (gated, off by default; DECISIONS D-5, D-6, ADR-0069).** When invoked with `--godot-mobile` (or when the change is a Godot 2D mobile game ship), the RELEASE_PLAN.md becomes a mobile store-delivery plan with two asymmetric platform paths instead of an infra rollout. Android: install the Android build template, name the version-pinned toolchain (OpenJDK 17, Android SDK Platform 35, Build-Tools 35.0.1, NDK r28b), choose APK (sideload/test) vs AAB (Google Play requires AAB for new apps since August 2021), and surface the re-export gotcha (an app with the same package name but a different signing key must be removed from the device first); Android export is host-OS-flexible. iOS: a hard macOS-plus-Xcode preflight, the App Store Team ID and a reverse-DNS Bundle Identifier, export an `.xcodeproj` then build/deploy in Xcode, and surface the experimental-C#-iOS caveat (since Godot 4.2, per D-6) and the simulator Compatibility-renderer limit. Stay version-flexible (D-5), noting Godot 4.6+ for editor device-mirroring on-device testing. The exposure ramp maps to the staged store rollout defined in the Play track ladder below; the rollback is a store reality (halt the staged rollout, pull the build, ship a hotfix version), since a shipped mobile app has no instant router-flip. Before submission, gate on the 2026 store-compliance artifacts: for Google Play, the Data Safety form covering every bundled SDK (one undisclosed SDK blocks the release) and target API level 35; for iOS, the `PrivacyInfo.xcprivacy` privacy manifest with required-reason API declarations, the ATT `NSUserTrackingUsageDescription` string when the app tracks the user, and a Restore Purchases path for non-consumables. When the ship includes in-app purchases or ads, route the entitlement and store checks to the `godot-monetization-integrity` bug-class (server-side purchase verification, acknowledge or consume within three days, reward only on the `user_earned_reward` callback). End with a store-submission go/no-go checklist that includes these compliance artifacts. This mode adds a platform-ship variant; it does not change the default infra-rollout flow, and it invents no device-specific numbers (those defer to `performance-budget`).
  - **Export preflight (checkable, before any store step).** Android: the Play artifact MUST be an AAB (per the captured Godot export doc, all new apps on Google Play after August 2021 must be an AAB; an APK is for sideloading and device testing only), built with the pinned toolchain from that capture (OpenJDK 17, Android SDK Platform-Tools 35.0.0+, Build-Tools 35.0.1, Platform 35, NDK r28b) wired through Editor Settings (Java SDK Path and Android SDK Path). These versions come from the captured `Exporting for Android` reference (accessed 2026-06-29) and MUST be re-verified against the current official docs at execution: pinned versions go stale. The signing gotcha is a MUST rule, not a note: a device build with the same package name but a different signing key MUST be uninstalled from the device before re-export, because a stale-keyed install breaks iterative device testing silently. iOS: the export REQUIRES a macOS host with Xcode, an App Store Team ID, and a Bundle Identifier; it produces an `.xcodeproj` that is built and deployed like any other iOS app; per the captured `Exporting for iOS` reference, C# export is experimental (since Godot 4.2) and the iOS simulator supports only the Compatibility renderer.
  - **Play track ladder and rollout binding.** The store-side release path is Internal testing (up to 100 testers), then Closed testing, then Open testing, then Production; pre-launch reports are the automated pre-release gate. The Production rollout MUST be staged to a percentage of users and monitored via Android vitals. Bind this ladder to the command's existing rollout vocabulary: each track promotion is an exposure-ramp step with a named promotion metric, and the rollback trigger fires the store mechanism above (halt the staged rollout, pull the build, ship a hotfix version). The iOS store-side path (TestFlight, App Store review, phased release) is a named capture gap: no captured reference grounds it, so the mode MUST NOT specify it from memory; route to `capture-references` first and mark the plan's iOS store-side section blocked on that capture.

Required output:
1. RELEASE_PLAN.md with the chosen pattern + rationale, the exposure ramp, the promotion metric + threshold, the rollback trigger + mechanism, and the go/no-go checklist.
2. The promotion-metric basis: cite the SLO_SPEC when present, or mark the threshold PROPOSED-pending-baseline.
3. The D-1 boundary statement (release-plan designs; post-deploy-verifier consumes; pipeline-gate-review audits the standing pipeline).
4. PROPOSED DECISIONS.md block for any rollout policy to lock; otherwise an explicit "no policy to lock" line.
5. Recommended next command (must exist in `commands/*.md`; verify against directory listing before output). Typical choices: `post-deploy-verifier` (author the post-deploy checks that consume this plan), `decision-interview` (lock a rollout policy), `pr-package` (deliver the change), `slo-define` (when the promotion metric needs an SLO basis first).

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
- RELEASE_PLAN.md exists with the chosen pattern + rationale, an exposure ramp (steps + advance conditions), a promotion metric + threshold, a rollback trigger + mechanism, and a pre-exposure go/no-go checklist.
- The promotion-metric threshold cites the SLO_SPEC when present, or is marked PROPOSED-pending-baseline; no invented number.
- The rollback mechanism is concrete and named from what the repo actually has; it is the mechanism post-deploy-verifier consumes (D-1).
- The D-1 boundary is stated (designs vs consumes vs standing-pipeline audit); release-plan does not author the post-deploy live-signal checklist itself.
- A trivial reversible change gets a SKIP/NO_OP, not a manufactured rollout plan.
- The command designs the rollout only; it never runs a deploy or a traffic shift.
- The `--godot-mobile` mode (when invoked) produces asymmetric Android and iOS store-ship paths (toolchain, the iOS macOS+Xcode preflight, AAB/signing/simulator gotchas, version-flexible per D-5, C# iOS caveat per D-6), the export preflight checklist, the Play track ladder bound to the promotion-metric and rollback-trigger vocabulary with the iOS store-side named as a capture gap, the 2026 store-compliance gate (Play Data Safety, target API 35, iOS privacy manifest, ATT, Restore Purchases), and a store go/no-go; without the flag the default infra-rollout flow is unchanged, and no device-specific performance numbers are invented.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A load-bearing release plan names a rollout pattern justified by the change's risk and the repo's actual infra, a concrete exposure ramp, a promotion metric that advances each step on evidence, and a rollback trigger with the exact mechanism, so a deploy is reversible on a known signal rather than on improvisation under pressure. The failure mode it prevents is the all-at-once ship with no staged exposure and no agreed abort condition, where a regression reaches every user before anyone decides whether to roll back. It stays stack- and infra-agnostic by reasoning over the abstract rollout model and mapping each primitive to whatever the repo actually has, and it holds the D-1 line: it designs the rollout and hands the post-deploy watch to post-deploy-verifier, never authoring the live-signal checklist or running the deploy itself.

<!-- cache-breakpoint -->

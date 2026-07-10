# Eval scenario 49: GKE Autopilot resource quota enforcement

- **Tags**: bug-class, gke-autopilot-resource-quota, kubernetes, deployment, resource-requests, hpa, P1
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates that the `gke-autopilot-resource-quota` bug-class fires as a P1 finding whenever a Kubernetes Deployment manifest targeting GKE Autopilot is missing `resources.requests` / `resources.limits`, and that a properly sized, HPA-configured, load-tested manifest passes cleanly. GKE Autopilot enforces a managed resource model: containers without explicit requests are either rejected at admission or silently defaulted, which then breaks autoscaling math and produces unpredictable cost. Reviews must catch this before apply.

This exercises:

- The `gke-autopilot-resource-quota` bug-class rule under `wos/bug-classes/`.
- The reviewer's ability to distinguish "no requests/limits" (P1 fail) from "sized + HPA + load tested" (pass).
- The reviewer's discipline in citing the bug-class identifier and severity, not just describing the symptom.

## Setup

A repo containing two Deployment manifests under `infra/k8s/`:

- `infra/k8s/bad-deployment.yaml` -- a Deployment with one container, no `resources` block at all, targeting a cluster annotated as GKE Autopilot.
- `infra/k8s/good-deployment.yaml` -- the same workload with explicit `resources.requests` and `resources.limits` matching Autopilot's supported ratios, an attached `HorizontalPodAutoscaler` keyed on CPU, and a referenced load-test report under `infra/k8s/load-test-results.md` showing the requests were derived from observed p95 usage.

The `gke-autopilot-resource-quota` bug-class is present at `wos/bug-classes/gke-autopilot-resource-quota.md`.

## Input prompt (turn 1: bad manifest)

```text
Review @infra/k8s/bad-deployment.yaml against @wos/bug-classes/_index.md before kubectl apply.
Cluster is GKE Autopilot. Flag any P1 issues.
```

## Input prompt (turn 2: good manifest)

```text
Review @infra/k8s/good-deployment.yaml + @infra/k8s/load-test-results.md against @wos/bug-classes/_index.md.
Cluster is GKE Autopilot. Confirm whether it is safe to apply.
```

## Expected response shape (turn 1: bad manifest)

- Reviewer identifies the missing `resources.requests` and `resources.limits` block.
- Reviewer cites `gke-autopilot-resource-quota` by name and tags the finding as **P1**.
- Reviewer explains the Autopilot behavior: admission either rejects the manifest or silently applies cluster defaults, breaking HPA targets and cost predictability.
- Reviewer recommends concrete remediation: add requests/limits derived from load testing, attach an HPA, and re-run admission dry-run.

## Expected response shape (turn 2: good manifest)

- Reviewer confirms `resources.requests` and `resources.limits` are present and within Autopilot's supported CPU:memory ratio.
- Reviewer confirms an HPA is attached and references the load-test report as the source of the sizing.
- Reviewer issues a PASS for `gke-autopilot-resource-quota` and does not raise a false P1.

## Pass criteria

1. **Turn 1 -- bug-class named**: Response cites `gke-autopilot-resource-quota` by its exact identifier, not just a generic "missing resources" comment.
2. **Turn 1 -- P1 severity**: Finding is explicitly tagged P1, matching the bug-class severity declared in `wos/bug-classes/gke-autopilot-resource-quota.md`.
3. **Turn 1 -- Autopilot mechanism explained**: Response states that Autopilot will either reject the apply at admission or set managed defaults, and explains why that breaks HPA / cost predictability.
4. **Turn 1 -- concrete remediation**: Response lists at least three remediation steps: add requests, add limits, attach HPA, and validate via load test or admission dry-run.
5. **Turn 2 -- PASS issued**: Response explicitly issues a PASS for `gke-autopilot-resource-quota` rather than re-flagging the rule.
6. **Turn 2 -- load test referenced**: Response cites the load-test report as the grounding for the chosen requests, not just "values look reasonable".
7. **Turn 2 -- HPA acknowledged**: Response confirms the HPA target is consistent with the declared requests (e.g. CPU target percentage maps to the request value).
8. **No cross-contamination**: Turn 2 does not inherit turn 1's P1 verdict; reviewer evaluates each manifest on its own merits.

## Failure modes to watch

- **Generic "missing resources" comment**: Reviewer flags the issue but never names `gke-autopilot-resource-quota`, so the finding is unauditable against the bug-class catalog.
- **Wrong severity**: Reviewer downgrades to P2 or "nit", missing that Autopilot admission failure or silent defaulting is a production-blocking class.
- **False P1 on the good manifest**: Reviewer re-flags the rule on turn 2 despite requests/limits/HPA/load test all being present, signaling the reviewer is pattern-matching on shape rather than evaluating substance.
- **No remediation path**: Reviewer reports the P1 but gives no concrete fix, leaving the user to guess Autopilot's supported ratios and the HPA wiring.

## Notes

- The bug-class is GKE-Autopilot-specific. Standard GKE (non-Autopilot) does not reject missing requests at admission; the reviewer should not raise this exact P1 on a non-Autopilot cluster, though "no requests/limits" remains a separate, lower-severity hygiene finding there.
- "Properly sized" means the requests are grounded in observed p95 usage from load testing, not guessed. A manifest with requests/limits but no load-test grounding is a weaker pass and may warrant a P2 note.

## History

- 2026-06-05: Scenario created to cover the `gke-autopilot-resource-quota` bug-class.

## References

- `internal/wos/bug-classes/gke-autopilot-resource-quota.md` (the bug-class under test)
- `internal/wos/bug-classes/_index.md` (hybrid loading contract for bug-classes)
- `internal/commands/repo-consistency-sweep.md` (one consuming command that loads the catalog)

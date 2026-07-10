---
name: gke-autopilot-resource-quota
category: deployment-infra
default-severity: P1
priority: P1
pillars: [resilience, observability]
cwe: [CWE-770]
languages: [yaml]
file-patterns: ["**/k8s/**/*.yaml", "**/k8s/**/*.yml", "**/kubernetes/**/*.yaml", "**/manifests/**/*.yaml", "**/deploy/**/*.yaml", "**/charts/**/templates/*.yaml"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# gke-autopilot-resource-quota

GKE Autopilot pod manifests that ship without measured `resources.requests` and `resources.limits`, or that ship with arbitrary "looks reasonable" values, fail in one of two directions: under-sized requests cause OOMKills and throttling under real load, and over-sized requests silently inflate the bill because Autopilot prices per requested CPU and memory, not per used. Both failure modes are common on a team's first GKE Autopilot deploy.

## What it looks like

- A `Deployment`, `StatefulSet`, or `Job` manifest whose container spec has no `resources` block at all, or has `resources.requests` without matching `resources.limits` (or vice versa).
- Resource values that are round numbers nobody can defend ("100m CPU / 128Mi" copied from a tutorial) with no link to a load test or profiling result.
- A `Deployment` serving live traffic with no `HorizontalPodAutoscaler` -- a single replica absorbs every traffic spike until it OOMs.
- A pod that gets OOMKilled in production but works locally, where local has no memory pressure.
- A monthly GKE bill that is 3-10x what the workload actually uses, because requests were sized "just in case" instead of measured.

## Why it matters

- GKE Autopilot bills per resource request, not per resource used. Over-sized requests = direct cost blowout with no reliability benefit.
- Under-sized requests = OOMKills, CPU throttling, slow tail latency, and cascading restart loops during traffic spikes.
- Missing HPA means the workload cannot absorb load even when resource sizing is correct -- one pod, one bottleneck.
- The failure mode is bimodal and silent: the cluster keeps running, so nothing alerts. You discover it either via a surprise invoice or a 3am OOM page.
- This is a CWE-770 pattern (Allocation of Resources Without Limits or Throttling) applied at the orchestration layer.

## How to detect

Manifest scan:

```
# Flag any container spec missing requests or limits
rg -n "kind:\\s*(Deployment|StatefulSet|Job)" -A 80 **/k8s/**/*.yaml \
  | rg -B 2 -A 4 "containers:" \
  | rg -L "resources:\\s*$"
```

Live cluster scan:

```
# Pods without resource requests
kubectl get pods -A -o json \
  | jq '.items[] | select(.spec.containers[].resources.requests == null) | .metadata.name'

# Deployments without an HPA
kubectl get deployment -A -o json > /tmp/deploys.json
kubectl get hpa -A -o json > /tmp/hpas.json
# diff deployment names against hpa.spec.scaleTargetRef.name
```

Smell signals:

- `kubectl describe pod <name>` shows no `Requests:` or `Limits:` lines.
- `kubectl top pod` shows actual usage at <20% of requested CPU/memory across a representative sample.
- GKE billing console shows "Autopilot Pod CPU requests" line item significantly above measured usage.

## How to fix

1. Run a representative load test against the workload (k6, Locust, or production traffic replay) for at least one full peak cycle.
2. Capture peak CPU and memory from `kubectl top pod` or Cloud Monitoring during that test.
3. Set `resources.requests.cpu` and `resources.requests.memory` to the measured peak.
4. Set `resources.limits` to 1.5x requests as a safety margin (Autopilot does not bill on limits, only requests).
5. Add an HPA for any `Deployment` serving live traffic, targeting 70% CPU utilization with sensible min/max replicas.
6. Document the measured peak, the chosen request values, and the load-test methodology in the deploy runbook so the next person can re-measure when the workload shape changes.
7. Re-measure quarterly or after any significant code change to the hot path.

## CWE / standard refs

- CWE-770: Allocation of Resources Without Limits or Throttling. Applies to the orchestration layer here -- the manifest is the "caller" that fails to bound resource allocation, and the consequence is either denial-of-service (OOM) or cost exhaustion.

## See also

- `wos/personas/post-deploy-verifier.md` (persona that should catch this before the first production traffic hits)
- `wos/bug-classes/missing-business-metric.md` (sibling deployment-infra class: the workload deploys but nothing measures whether it is actually doing its job)

---
name: gke-autopilot-resource-quota
category: deployment-infra
default-severity: P1
cwe: [CWE-770]
languages: [yaml]
file-patterns: ["**/k8s/**/*.yaml", "**/k8s/**/*.yml", "**/kubernetes/**/*.yaml", "**/manifests/**/*.yaml", "**/deploy/**/*.yaml", "**/charts/**/templates/*.yaml"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# gke-autopilot-resource-quota

## Trigger

Pod manifests ship to GKE Autopilot without measured `resources.requests` and `resources.limits`, or with values nobody can defend, and they fail in one of two directions. Under-sized requests produce OOMKills and CPU throttling under real load. Over-sized requests inflate the bill, because Autopilot's pricing is stated against requested CPU and memory rather than used, so a request set generously "just in case" is billed at that generosity forever.

The reason this survives is that neither direction alerts. The cluster keeps running either way, so the discovery channel is a surprise invoice or a page at three in the morning, and both arrive long after the manifest was merged. Missing autoscaling compounds it: correct sizing on a single replica still means one pod absorbing every spike.

CWE-770 (Allocation of Resources Without Limits or Throttling), applied at the orchestration layer: the manifest is the caller that fails to bound allocation, and the consequence is denial of service in one direction and cost exhaustion in the other.

## Detection

- A `Deployment`, `StatefulSet`, or `Job` whose container spec has no `resources` block, or has `requests` without matching `limits` or the reverse.
- Values that are round tutorial numbers (`100m` CPU, `128Mi` memory) with nothing in the repository tying them to a load test or a profile.
- A `Deployment` serving live traffic with no `HorizontalPodAutoscaler` pointing at it.
- A workload that gets OOMKilled in the cluster and runs fine locally, where there is no memory pressure to find.
- Measured usage far below requested across a representative sample, which is the over-provisioned direction and the one that never pages.

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

## Retrieval

- Every workload manifest in the deploy path, including Helm chart templates and any kustomize overlay, read as rendered rather than as source. A base with no `resources` and an overlay that adds them is a pass; reading only the base reports a false finding, and reading only the overlay hides a workload it does not cover.
- The `HorizontalPodAutoscaler` objects and their `scaleTargetRef` names, so the deployment-to-HPA mapping can be computed rather than assumed from proximity in the file tree.
- Whatever the repository holds as evidence for the chosen numbers: a load-test script, a profiling result, a runbook entry, a comment naming a measurement. Absence is the finding for the arbitrary-values shape, so record it explicitly.
- Live `kubectl describe pod` and `kubectl top pod` output for a representative sample when a cluster is reachable, and say plainly when it is not. The gap between requested and used is only visible from the running side.
- The platform's own billing breakdown for the cluster, when the analyst has access. The cost direction of this class is settled by that output, not by reasoning about the manifest.

## Analysis prompt

Given the retrieved manifests, the HPA objects, and any cluster or billing output the analyst can actually see:

1. Render each workload as it deploys, then report per container whether `resources.requests` and `resources.limits` are present. Report a partial pair as its own finding; requests without limits and limits without requests fail differently and both are wrong.
2. For every container that has values, trace each number to its evidence in the repository. Report the evidence path, or report that none exists. A number with no traceable measurement is the arbitrary-values shape regardless of whether it happens to be correct.
3. Compute the deployment-to-HPA mapping from `scaleTargetRef` and report every `Deployment` that serves live traffic with no HPA targeting it. Say how you determined which ones serve live traffic.
4. WHERE live cluster output is available, compare measured peak CPU and memory against the requested values per workload and report the ratio. Do not estimate this ratio from the manifest; if `kubectl top` output is not in hand, report the comparison as not performed rather than inferring it.
5. WHERE billing output is available, compare the platform's own requested-resources line item against the measured usage from step 4. This is the step that establishes the cost direction, and it is an observation of the platform's output rather than a claim about its pricing model; if you cannot see that output, say so and stop short of asserting an overspend.
6. Report whether any runbook or deploy documentation records the sizing methodology and a re-measurement cadence. A correct number with no recorded method decays the first time the hot path changes.
7. Recommend, in order: run a representative load test through at least one full peak cycle; set requests from the measured peak rather than from a template; set limits to a stated multiple of requests as headroom; add an HPA for every deployment serving live traffic with explicit minimum and maximum replicas; record the measurement, the chosen values, and the method in the runbook so the next person re-measures instead of re-guessing; and re-measure on a fixed cadence and after any significant change to the hot path.

## Severity rubric

- **P1**: a live-traffic workload with no `resources` block, or with requests and limits that trace to no measurement, and no HPA. Justification: both failure directions are open at once, and neither has an alert. It is not P0 because the manifest is one edit from correct and nothing is lost that cannot be rebuilt; the damage accrues as spend or as incidents rather than as destroyed state.
- **P1 also**: measured usage far below requested across a representative sample, with the gap confirmed against billing output. The reliability side is fine and the cost side is real and ongoing.
- **P2**: requests and limits present, measured, and correct, with no recorded methodology or re-measurement cadence. Right today, unverifiable tomorrow.

## Confidence factors

- **HIGH**: a rendered manifest with no `resources` block at all. One read, no interpretation, and the two failure directions follow from the absence.
- **MEDIUM**: values present that trace to no evidence in the repository. The number may be right; the absence of a method is the observation.
- **LOW**: a `Deployment` with no HPA in a repository where autoscaling is configured outside the manifest tree, so absence in these files is not absence in the cluster.

## Examples

### Positive (no resources, no HPA, live traffic)

```yaml
kind: Deployment
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: api
          image: registry.example/api:sha-9f2c1a
          ports: [{ containerPort: 8080 }]
          # no resources block
```

One replica, no requests, no limits, and nothing in the repository targeting this deployment with an HPA. The platform assigns defaults, the pod runs, and the first real traffic spike decides which of the two failure directions arrives first.

### Negative (measured, bounded, autoscaled, documented)

```yaml
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: api
          resources:
            # peak from load/api-peak.js, 2026-07 run, recorded in docs/runbook-api.md
            requests: { cpu: "350m", memory: "512Mi" }
            limits:   { cpu: "525m", memory: "768Mi" }
---
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { kind: Deployment, name: api }
  minReplicas: 2
  maxReplicas: 10
```

The numbers cite the run that produced them, the limits are a stated multiple rather than a guess, and the HPA names its target so the mapping is checkable without reading the directory layout.

# ADR-0133: `ref-attested` commit evidence for the autonomous track

- **Status**: Accepted
- **Date**: 2026-08-07
- **Tags**: commit-evidence, closure-enforcement, autonomous-track, two-track, refines-adr-0100, extends-adr-0084, quarantine-ref, attester-class, dogfood-driven

## Context

The commit-evidence floor (ADR-0084, refined by ADR-0100) asks a closing slice or task for evidence that its work is reachable in a citable git object. It names one route: `branch-commit --apply`, the only command in this repository that can create a commit. That command refuses without a human confirmation given in the same turn AND after it displays the content (eval scenario 125 pins the four conditions).

An autonomous run has no human turn. It therefore cannot reach the only route the floor names, and every unattended run ends at ADR-0100's bounded deferral with real, working, test-passing code sitting uncommitted. That is the honest outcome under the rule as written, and ADR-0100 was right to prefer it over a waiver. It is also a dead end that no amount of care inside the run can escape, because the constraint is in the routing, not in the work.

The reason this was read as a hard wall is a misattribution, and it is measurable. ADR-0100's negative-consequences section states that "the human merge/commit gate is the WOS's core premise (ADR-0044)". ADR-0044 does not contain the word:

```
$ grep -c 'commit' docs/adr/0044-autonomous-delivery-track.md
0
```

Measured 2026-08-06. What ADR-0044's D6 actually says is "a human plan-approval gate before execution, a human draft-diff merge gate before any irreversible step, and mid-run escalation of any boundary slice (schema, contract, migration, security) or any unverifiable slice" (`docs/adr/0044-autonomous-delivery-track.md:20`). It gates **merge**. It says nothing about commit, and a commit is not an irreversible step: a quarantine ref is deleted with one `git update-ref -d`.

Two further inputs. `wos/gate-conditions.md` `### The attester-removed test` classifies the commit-evidence floor as `agnostic`: erase the attester and the criterion still stands, because what survives is "the work is reachable in a citable git object", which does not name who produced it. That classification describes what the criterion admits and never what policy permits, which is why this ADR exists rather than the class line settling it. And the driver already had to solve the mechanical half for its own reasons, so the substrate exists.

## Decision

The commit-evidence floor accepts TWO routes, and a closing home must route to one of them: `branch-commit --apply` for a run with a human turn, and `ref-attested` for a run without one. A run is `ref-attested` when the RUNNER (never the agent) has created a git object holding the run's work and pointed a quarantine ref at it, under `refs/fhorja/attested/<run-id>/<invocation-id>`.

Qualifications, each a boundary this ADR does not cross:

- **ADR-0100's bounded deferral survives wherever `ref-attested` does not apply.** A workspace with no repository, a run whose attestation could not be made, a run whose target is not the tree holding the work: each of these still records `deferred: pending human commit (<context>)` and keeps the slice or task OPEN. That deferral is ADR-0098's bounded-vs-permanent shape, which ADR-0100 mirrored onto this floor, and the shape is exactly what makes a second route safe to add: a bounded deferral is an honest open state rather than a failure, so a route that does not reach falls back to something correct instead of to a waiver. This ADR adds a route; it removes none, and it never converts an unreachable attestation into a silent pass.
- **The human gate is untouched at merge, push and draft-PR (D-2).** `ref-attested` is evidence that work is reachable, not authorization to publish it. Nothing in this decision lets an unattended run merge, push, or open a PR.
- **`commands/branch-commit.md` does not change (D-4).** Its four refusal conditions hold exactly as scenario 125 pins them. A floor with an alternative route is not a command with a relaxed gate.
- **The agent's git write set does not widen.** The attestation is written by the runner, outside the agent's adjudicated boundary. The paired external-consumer check records that its adjudicated write set admits `git add` and `git commit -m` and nothing else, and that its safety tests pin the count at exactly two.
- **This ADR does not name the gitignored-Scope structural exemption as a further route.** That is a different question (whether work is committable at all, rather than who may attest it), and bundling them would produce one ADR that cannot be reverted without reverting both.

Eval scenario 95 pins where the floor routes and is updated in the same change to admit both routes, the way ADR-0100 updated it when it narrowed the waiver. The mechanism enforcing the routing is `evals/scripts/structural-evals.py`, check `commit-evidence-apply-route`, which asserts PER HOME that the home routes to one of the two. It matches the phrase `route to <route>` rather than a bare token, because a sentence naming a route in order to EXCLUDE it must not satisfy the floor, and this ADR's own qualification above is exactly such a sentence. The prose in the floor's three homes must therefore write `route to \`ref-attested\`` in those words.

## Consequences

### Positive

- An unattended run has a reachable route to commit evidence, so its work is durable without a human turn. Before this, every such run ended with real work only in the working tree.
- The evidence is trivially reversible: `git update-ref -d refs/fhorja/attested/<run-id>/<invocation-id>` removes it, which is the argument that a quarantine ref is not the irreversible step ADR-0044's D6 gates.
- The quarantine namespace keeps attested objects off every branch, so nothing an unattended run produces can be mistaken for reviewed history.
- A measurable claim replaces an inherited one. The `grep -c` above is re-runnable, so a future reader can check the premise rather than trusting this ADR.

### Negative

- Two routes are harder to hold in the head than one, and the floor's prose grows. The eval's per-home assertion is the mitigation: a home that loses its routing fails by name.
- `ref-attested` evidence has not been reviewed by anyone. It proves reachability, not correctness, and a reader who treats an attested ref as a reviewed commit will be wrong. The quarantine namespace is what keeps that mistake from being easy.
- The attestation depends on the target being a git repository, which the driver now creates when absent. That is a write into the operator's workspace that earlier autonomous runs never made.

### Neutral

- The floor's attester class stays `agnostic` in `wos/closure-floors.md`. The class did not change and did not decide this; it describes what the criterion admits.
- ADR-0100 keeps `Status: Accepted`. It is superseded at the closure point only, and its bounded deferral remains the answer everywhere the second route does not reach.

## Alternatives considered

### Alternative 1: leave the floor at one route and accept the deferral

- Every unattended run ends open, and a human commits in the morning. No new mechanism, no new failure mode.
- Rejected because it makes the autonomous track structurally unable to close a floor that its own criterion admits it could satisfy, on the strength of a premise (ADR-0044 gates commit) that the measurement above shows was never there. The cost is not one morning; it is that the track cannot complete a run end to end, which is what the track is for.

### Alternative 2: let the autonomous run invoke `branch-commit --apply` with a relaxed condition 4

- The floor keeps exactly one route, and the unattended case is handled by loosening the confirmation requirement when no human is present.
- Rejected because condition 4 is the whole gate. Scenario 125 exists because an earlier revision let the display become a receipt, and "no human is present" is precisely the state under which a confirmation requirement must not soften. It would also put commit-creation inside the autonomous track, which D-2 and D-4 keep out.

### Alternative 3: have the AGENT create the attestation

- The agent already writes git through an adjudicated allowlist, so the ref could be written there.
- Rejected because `update-ref` is not an admitted verb and admitting it would widen the agent's write set for a mechanism that does not need it. The runner writes the ref AFTER the agent's turn has ended, from the single terminal-path call site verified by the paired external-consumer check, so the agent's boundary stays exactly where it was. This also keeps the attestation outside anything the agent could be talked into: by the time the ref is written there is no agent turn left to influence it.

## References

This decision spans Fhorja and an external execution layer, a deliberate exception to this
project's single-repo charter. The decision is Fhorja's and the mechanism it names is the
external runner's. ADR-0169 requires tracked files to omit that consumer's name and paths, so
implementation details from the paired check are described generically. Every path below is in
this repository.

- [ADR-0084](./0084-godot-flow-completeness-wave.md): the commit-evidence floor's origin.
- [ADR-0100](./0100-commit-evidence-floor-bounded-deferral.md): the bounded deferral this ADR supersedes at the closure point and preserves everywhere else.
- [ADR-0044](./0044-autonomous-delivery-track.md): the autonomous track, whose D6 gates merge and is silent on commit.
- [ADR-0098](./0098-feel-experience-verdict-bounded-vs-permanent-skip.md): the bounded-vs-permanent shape ADR-0100 mirrored onto this floor.
- `wos/closure-floors.md` → `## Commit-evidence floor`: where the two routes are normative.
- `wos/gate-conditions.md` → `### The attester-removed test`: the classification, which describes the criterion and does not decide policy.
- `evals/scripts/structural-evals.py` → `check_commit_evidence_routes_to_apply`: the per-home mechanism.
- `evals/scenarios/95-closure-commit-gate.md` and `evals/scenarios/125-branch-commit-apply-authorization.md`: where the floor routes, and what the routed command refuses.

## Notes

The decision was locked as D-5 in the task `2026-08-07_ref-attested-commit-evidence-autonomous-track`, which also carries D-2 (the human gate stays whole), D-4 (`branch-commit` does not change), D-6 (the ref key) and D-7 (what the attested object holds). ADR-0197 later scopes this runner-owned route to an external execution layer; direct-use `autonomous-run` does not create an attestation ref.

Sequencing is expand-migrate-contract and deliberate: the eval was widened to accept both routes BEFORE this ADR and before the floor's prose changed, so the suite is green on both sides of the prose edit and the only irreversible step in the path lands last.

Revisit if the driver ever gains a durable cross-session resume, which would raise the question of whether a run's several invocations should share one ref rather than one per invocation.

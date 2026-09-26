# ADR-0197: Autonomous-run is a direct-use reference dispatcher

- **Status**: Accepted
- **Date**: 2026-09-08
- **Tags**: autonomy, direct-use, reference-dispatcher, external-consumer, boundary
- **Clarifies**: [ADR-0044](./0044-autonomous-delivery-track.md), [ADR-0133](./0133-ref-attested-commit-evidence-for-the-autonomous-track.md), [ADR-0159](./0159-express-binds-by-default.md), [ADR-0163](./0163-apply-commits-locally-without-confirm.md), [ADR-0169](./0169-external-read-only-consumer-of-the-command-surface.md), and [ADR-0196](./0196-supervised-background-run-lifetime.md) without superseding their decisions.
- **Extends**: [ADR-0164](./0164-engagement-provenance-redaction.md) with a third narrow identity-redaction exception to ADR immutability.

## Context

The autonomy topic describes two real but different subjects. Fhorja ships `autonomous-run`, a bounded dispatcher over its command primitives. The same topic also preserves commit and attestation obligations for an external execution layer that reads the command surface under ADR-0169. Without an explicit boundary, a reader can assign the external runner's product responsibilities to the local command or interpret the new process supervisor as a durable execution service.

The local supervisor added by ADR-0196 establishes independent timeout, STOP observation, process-group termination, exclusive admission and feed finalization for one detached run. It creates no durable queue, cross-session resume, security sandbox, credential broker, remote control or publication workflow. Its absolute STOP path also does not prove that the agent lacks permission to clear the sentinel; only the host can establish that filesystem boundary.

## Decision

`autonomous-run` is Fhorja's full-profile direct-use reference dispatcher for one approved task and one continuous foreground or detached session. It delegates writes to existing commands and emits PROPOSED diffs. It does not commit, create attestation refs, push, open a pull request, merge or deploy. It refuses invocation from another execution loop. External execution layers consume ordinary command handoffs plus the readiness and board surfaces, implement their own product capabilities and refuse nested `autonomous-run` dispatch. Fhorja remains independent of every such consumer.

- Commit and hard-containment obligations in `wos/autonomous-track.md` are labeled as external execution-layer or host obligations. They do not grant those capabilities to the local command.
- The `commit-ref` and `ref-attested` closure routes belong to an external execution layer. A direct-use `autonomous-run` with neither class records `deferred: pending human commit (<one-line context>)` and leaves the slice or task open.
- The local supervisor observes timeout and STOP independently. Hard STOP immutability exists only when the host places or mounts the sentinel outside the agent writable scope. Without that boundary the command reports cooperative-only control.
- Exact external-consumer names and paths are redacted in place from tracked historical prose, including one qualification in ADR-0133's Decision section. This is the third narrow exception to ADR immutability after ADR-0090 and ADR-0164. Only identifying tokens change; the recorded technical decisions and evidence remain.
- The boundary is enforced in `commands/autonomous-run.md`, `wos/autonomous-track.md`, `wos/command-roles.md` and eval scenarios 56, 92 and 118.

## Consequences

### Positive

- Direct Fhorja users can see exactly what the reference utility automates and where its authority ends.
- External execution-layer obligations remain documented without turning the consumer into a dependency or roadmap for this repository.
- STOP evidence distinguishes independent observation from host-enforced immutability.

### Negative

- An execution layer must compose ordinary commands instead of nesting the convenience dispatcher.
- A local run without a host filesystem boundary has a weaker STOP guarantee and must report it.

### Neutral

- ADR-0196 process supervision and ADR-0044 approval, readiness, escalation and human review gates remain unchanged.
- The external consumer remains unnamed and read-only under ADR-0169.

## Alternatives considered

### Treat autonomous-run as the product execution engine

- Add durable scheduling, resume, credentials, remote control and publication behavior to Fhorja.
- Rejected because those capabilities require a service boundary and would couple the MIT reference workflow to product concerns.

### Remove external execution-layer obligations from Fhorja

- Delete the commit and attestation contracts because the local command cannot exercise them.
- Rejected because ADR-0169 declares the command surface as a read-only interface and those obligations are consumed outside this repository.

### Permit nested autonomous-run dispatch

- Let an external loop invoke Fhorja's own loop as one command.
- Rejected because two controllers would own scheduling, recovery and escalation for the same task.

## References

- `commands/autonomous-run.md`, direct-use trigger, refusal and excluded capabilities.
- `wos/autonomous-track.md`, reference dispatcher and external execution-layer contracts.
- `wos/command-roles.md`, command boundary.
- `scripts/autonomy/`, bounded local runtime helpers.
- [ADR-0169](./0169-external-read-only-consumer-of-the-command-surface.md), one-way interface boundary.
- [ADR-0164](./0164-engagement-provenance-redaction.md), the identity-redaction precedent.
- [ADR-0196](./0196-supervised-background-run-lifetime.md), supervised per-run process lifetime.

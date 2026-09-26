# ADR-0196: Supervised background run lifetime

- **Status**: Accepted
- **Date**: 2026-09-07
- **Tags**: autonomy, timeout, process-ownership, runs-feed
- **Supersedes**: [ADR-0081](./0081-background-autonomous-run.md) only for its clean slice-boundary timeout promise, heartbeat-based admission, agent-owned lifecycle writes and unsupervised manual fallback. Its remaining decisions stand.

## Context

The background launcher detached an agent without an independent timer. The cooperative governor ran between attempts, so a blocked process could not reach its next timeout check. Feed staleness also admitted another launch without proving that the first writer had stopped. The accepted D-5 correction requires bounded process control and conservative admission while preserving the existing autonomous gates.

## Decision

Every detached run uses one per-run supervisor with an explicit positive wall-clock budget and termination grace, supplied through `launch-background-run.sh --timeout-sec --grace-sec`. The supervisor owns admission, the child process group and feed finalization. It observes STOP and elapsed time independently, requests termination, then forces it after the grace. Unresolved ownership refuses another run, irrespective of heartbeat age. Interrupted work and logs remain for inspection, and escalation records the observed reason without certifying slice completion.

- `scripts/autonomy/supervise-background-run.py` holds exclusive ownership before workspace setup and serializes managed feed writers. Persistent ownership survives supervisor death; saved PIDs are never authority to signal a process. Failed cleanup or finalization requires human inspection before admission can reopen.
- Managed feed creation and clean removal belong to the supervisor. Controller updates carry progress and escalation. A terminal escalation survives later start, update, end and exit 0. ADR-0080's seven required v1 fields and read-only consumers remain unchanged; lifecycle metadata is separate from task memory.
- The supported process boundary is the owned POSIX process group, including ordinary child commands. Descendants that create other groups or sessions require an attended execution path. This mechanism is not a security sandbox. Capability failure refuses detachment.
- An unset `WOS_AGENT_CMD` prints instructions for the same supervised entry point and exits 0. No manual raw detachment bypass is offered. Existing approval, readiness, D6, D9, classifier and test-change escalation rules remain required.
- Termination can interrupt a slice. Timeout alone proves no permission cause. No rollback, automatic resume, restart, merge or outcome-ledger success is implied. Notification runs only after cleanup and finalization and has a separate bound.

## Consequences

### Positive

- A blocked agent no longer needs to call the governor for timeout or STOP enforcement.
- A stale heartbeat or dead supervisor cannot authorize overlapping writers.
- Late feed writes cannot erase a recorded escalation.

### Negative

- Operators must supply both bounds and inspect partial work after interruption.
- Failed cleanup, supervisor death and legacy unsupervised runs need manual ownership reconciliation, even when a heartbeat looks stale.
- Process-group control requires a supported local runtime and a CLI whose work stays within that group.

### Neutral

- Foreground governor checks, worktree layering and the board reader contract remain in place.
- No daemon, dependency package or durable-resume service is introduced.

## Alternatives considered

### Keep cooperative checks and weaken the guarantee

This would accurately describe the old launcher but would leave blocked executions unbounded. D-5 selected independent enforcement.

### Reclaim ownership from a stale heartbeat or saved PID

Neither establishes that the old writer is gone; a PID can also be reused. Recovery therefore requires inspection instead of automatic reclamation.

### Add a durable service or security container

This would expand deployment and lifecycle policy beyond a single supervised session. The bounded per-run supervisor is sufficient for the supported process boundary.

## References

- `commands/autonomous-run.md`, background operating rules.
- `wos/autonomous-track.md`, background runs and recovery.
- `scripts/autonomy/tests/test-background-run.py`, real entry-point tests with owned mock processes.
- [ADR-0044](./0044-autonomous-delivery-track.md), autonomous gates.
- [ADR-0080](./0080-portfolio-board.md), feed v1.

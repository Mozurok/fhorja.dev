# ADR-0199: Task-memory files are written, not proposed

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: write-policy, proposed-by-default, mode-independence, adr-0001, adr-0026
- **Supersedes**: ADR-0001 (the PROPOSED-by-default write gate), ADR-0024 (its three-path addendum), ADR-0026 (the implement-approved-slice exception), ADR-0190 (the Ask-path routing that worked around it)

## Context

ADR-0001 made a task-memory update `PROPOSED` in Ask and Plan and `APPLIED` in Agent. ADR-0024 then
described three ways a user could promote those files, and ADR-0026 carved `implement-approved-slice`
out of the rule because the PROPOSED cycle was measured at a zero per cent rejection rate. ADR-0190
added an Ask-path handoff to `task-init` whose only job was to route around the gate: the five files
were not on disk yet, so the plan could not read them.

Four ADRs, each one working around the one before it. Measured 2026-09-16, the gate reached 57
command-tree files plus the spec.

What it gated is the point. Writing five markdown files into a task folder is internal, reversible,
and matches none of the four reasons ADR-0186 allows a chain to stop. The rejection rate ADR-0026
cited was zero because there was nothing to reject.

## Decision

A command writes its task-memory files directly and marks them `APPLIED`, in every mode.

`PROPOSED` keeps its other meaning entirely. A command that does not OWN a substrate section still
stages a `<!-- PROPOSED by <command>: ... -->` block inside it for the owner to promote (ADR-0034).
That is peer ownership, not a mode gate, and it applies in Agent mode too. The 2026-09-16 measurement
found the two mechanisms tangled in the same token, which is why removing one read as removing both.

`approve-proposed` survives and leaves the default chain. It is invoked on request, for the ownership
case above.

## Consequences

Positive. The chain no longer stops between writing a task folder and planning against it. ADR-0190's
Ask path is gone and `task-init` shrank 236 characters, which matters because it sits closest to the
ADR-0116 size ceiling.

Negative, and stated rather than glossed. A user who wanted to read five files before they landed no
longer gets that pause by default. The recovery is ordinary version control, which is why the act was
classified reversible in the first place; on a task folder under `projects/`, which is gitignored,
the recovery is reading the file and editing it.

Neutral. Eight eval scenarios graded the gate as correct behavior and were rewritten; two of them
changed premise rather than value.

## Alternatives considered

Keep the gate and remove only ADR-0026's exception. Rejected: the exception existed because the rule
was wrong for the most frequent case, and narrowing an exception does not fix the rule.

Raise the gate to Ask only, leaving Plan writing directly. Rejected: it keeps a mode-dependent write
policy, which is the thing that produced four ADRs of workarounds.

## References

- ADR-0001, ADR-0024, ADR-0026, ADR-0190: the chain this supersedes.
- ADR-0034: the peer-ownership mechanism that keeps the `PROPOSED` token.
- ADR-0186: the four reasons a chain stops, none of which this gate matched.

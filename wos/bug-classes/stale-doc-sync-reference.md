---
name: stale-doc-sync-reference
category: meta
default-severity: P2
cwe: []  # CWE-1059 removed 2026-09-21: MITRE marks it Prohibited for mapping, "primarily a quality issue with no direct security implications", which is exactly what this class is. No CWE fits, and 37 templates already carry an empty list.
languages: [markdown]
file-patterns: ["packages/wos-engine/internal/wos/**/*.md", "packages/wos-engine/internal/commands/**/*.md", "packages/wos-engine/internal/docs/**/*.md"]
perspectives: [maintainer, operator]
reversibility-check: false
---

# stale-doc-sync-reference

## Trigger

A curated document references an artifact that no longer exists in the shape the reference expects: a backticked command name that was renamed or removed, a decision-record identifier that was never created or has been archived, or a topic path that does not resolve on disk. Each broken reference is a navigation failure for whoever follows it.

The failure lands differently on the two kinds of reader. A human hits a dead end and knows it. An agent resolving references as part of loading its context gets a silent gap instead of a visible failure, and then reasons from a context it believes is complete. That asymmetry is why this class is worth a guard rather than a cleanup pass.

There is a second cost that outlives the individual link. A backticked command name implies the command is callable, so a stale one leaves the reader either trying it and failing, or treating the document as authoritative about behavior that no longer exists. One stale reference in a high-traffic entry-point document erodes confidence in every other reference on the page, and drift accumulates quietly across many small edits until something converts it into a failing check.

CWE-1059 (Insufficient Technical Documentation), read as advisory: the documentation references artifacts that no longer match the running system, so it cannot be relied on as a faithful map.

## Detection

The drift guard is the detection, and it reports at line granularity:

```bash
bash scripts/check-doc-sync.sh
# Exit code: 0 = clean. Non-zero = broken refs.
# Output lines have the shape:
#   internal/wos/<file>.md:<line> -> broken-ref: <kind>=<value>
# where <kind> is one of: command, adr, topic
```

The three reference kinds fail for different reasons and want different fixes:

1. **Command.** A backticked name absent from the live registry, usually renamed mid-refactor rather than deleted.
2. **Decision record.** An identifier with no file at the expected path: a typo, a forward reference to something not yet written, or an archive with no redirect left behind.
3. **Topic path.** A path that moved during a reorganization while the links to it did not.

Run it before pushing a documentation-touching commit; a non-zero exit blocks merge in CI.

## Retrieval

- The guard's full output, every line rather than the first. The distribution across kinds and files is what distinguishes a rename that broke thirty references from thirty unrelated typos, and those are different jobs.
- For each broken reference, the surrounding paragraph and not the line. The fix depends on what the sentence claims, and a line-scoped read produces a token substitution that leaves the prose wrong.
- The live registry the reference kind resolves against: the command list, the decision-record directory, the topic directory. The question is what exists now, and it has to be read rather than recalled.
- The version history of the referenced artifact where the guard reports it absent. Renamed, deleted deliberately, and never created look identical from the reference side and lead to three different resolutions.
- The traffic weight of the file carrying the reference: an entry-point document, a role index, or a rarely opened appendix. This does not change the fix; it changes the order.

## Analysis prompt

Given the guard's output and the referenced registries:

1. Report every broken reference as a triple of file, line, and kind. Group them by referenced artifact rather than by file, because one rename typically produces many lines and they resolve together.
2. For each referenced artifact, determine which of three situations holds: it exists under a new name or path, it should exist and is missing in error, or it is deliberately gone. Report the evidence for the choice, naming the registry entry or the commit. Do not guess: the three situations have opposite fixes, and guessing wrong deletes a real reference or resurrects a dead one.
3. For each broken reference, read the surrounding sentence and report whether a token substitution would leave the prose correct. Where it would not, say what the sentence claims that is no longer true. This is the step that separates a fix from a find-and-replace.
4. Report which broken references sit in high-traffic curated surfaces. These are the ones whose staleness costs the most trust per instance.
5. Report whether the guard runs in CI on every change to these paths and whether a non-zero exit blocks the merge. A guard that runs and does not block converts silent drift into visible drift that persists.
6. Report whether any deliberately removed artifact is marked as removed in the documents that reference it, or simply left dangling. Explicit removal notes are the difference between a resolved reference and one that will be re-reported forever.
7. Recommend, per broken reference, exactly one of three resolutions and never a silent deletion of the surrounding text: update the reference to the live artifact and verify the sentence still reads correctly; restore the artifact when the reference is right and the artifact was removed in error; or mark the removal explicitly, naming the superseding artifact, when the removal was deliberate. Then re-run the guard and confirm a clean exit, because a partial fix that leaves the exit non-zero teaches readers to ignore it.

## Severity rubric

- **P2**: broken references in curated documentation with the guard in place and reporting them. Justification for the ceiling: nothing in the running system is wrong, the failure is navigational, and the guard makes the drift visible and bounded. It does not reach P1 because no behavior, data, or contract is affected, and a reader who follows a broken reference discovers the problem rather than acting on a falsehood.
- **P2 also**: a stale backticked command name specifically, which implies callability that no longer exists. It is the shape most likely to cost a reader real time before they conclude the document is wrong.
- **P1**: no guard at all across a large curated surface. The individual references stay cheap and the accumulation is not: without the check, drift is unbounded and invisible, and agents loading context from these documents inherit gaps they cannot see.

## Confidence factors

- **HIGH**: a guard line naming a file, a line, and a kind, with the referenced artifact absent from the corresponding registry. The tool and the registry agree.
- **MEDIUM**: a referenced artifact that is absent from the registry and present in history under another name, where whether it was renamed or replaced needs the commit to settle.
- **LOW**: a backticked token that resembles a command name and may be prose, a shell builtin, or an external tool. The guard's own kind classification is the arbiter, not the backticks.

## Examples

### Positive (rename left thirty dangling references)

```text
internal/wos/entry-points.md:41  -> broken-ref: command=review-changes
internal/wos/command-roles.md:88 -> broken-ref: command=review-changes
...
```

The command was renamed during a refactor and every document that pointed at it kept the old token. The paragraphs still read as instructions, so a reader follows them, tries the name, and gets nothing. An agent resolving the reference gets an empty result and continues without noticing the gap.

### Negative (deliberate removal, marked as such)

```markdown
~~`review-changes`~~ removed in ADR-0029; use `review-hard` instead.
```

The reference is explicit about the removal and names the successor, so the guard treats it as resolved rather than re-reporting it, and a reader arriving from an old bookmark learns both facts they need in one line.

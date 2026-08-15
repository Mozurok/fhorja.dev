---
name: substrate-bullet-orphan
category: substrate-protocol
default-severity: P2
cwe: []
languages: [markdown]
file-patterns: ["projects/**/active/**/TASK_STATE.md", "projects/**/active/**/IMPLEMENTATION_PLAN.md", "projects/**/active/**/DECISIONS.md", "projects/**/active/**/SOURCE_OF_TRUTH.md"]
perspectives: [maintainer]
reversibility-check: false
---

# substrate-bullet-orphan

## Trigger

A substrate file carries one or more bullet lines that sit between two H2 headings without being inside either section's body. The bullet is in the file and no section owns it, so a reader walking H2 boundaries never sees it.

Every guard passes. The per-line validator checks the shape of each audit line and finds nothing wrong. The header drift scanner checks that sections carry transaction headers and finds nothing wrong. Neither one checks that the content a header claims to have written actually landed inside the section the header names, so the substrate is structurally broken while the checks that exist for exactly this file all report clean.

The consequence is a silent loss rather than a visible one. Commands that read the substrate parse by walking H2 boundaries, so an orphan bullet is invisible to section-scoped reads: the observation exists on disk and cannot be retrieved by anything that consumes the file. Meanwhile the audit trail claims it landed. A later reader inherits a record that says the write happened and a section that does not contain it.

No CWE identifier is assigned: this is a protocol-level structural failure specific to the substrate contract rather than an instance of a general weakness class.

## Detection

Three shapes, all of them positional:

1. **Bullet above its own heading.** A bullet appears after a transaction header and before the H2 that header introduces, so the write landed one boundary early.
2. **Bullet in the gap.** A bullet appears after one section's body ends and before the next H2 begins, belonging to neither.
3. **Stacked headers with bullets interleaved.** Two or more transaction headers back to back with content between them, which is the repeated-automation version of shape 1.

The mechanical tell is that the file's bullet count and the sum of the sections' bullet counts disagree. Anything that parses by section will report the smaller number, and nothing will report the difference.

The usual origin is a substrate-write automation whose section-end offset is computed slightly before the next H2 line rather than at it, so the insert lands outside the section it was aimed at. One 2026-06 fleet run produced this across several files at once from a single off-by-one in the boundary calculation. Manual causes exist too: a paste into the gap between sections, a proposed block emitted with stray leading newlines, or a merge resolution that moves a bullet across a heading.

## Retrieval

- The whole substrate file as raw text, not section by section. The defect is invisible to a section-scoped read by definition, so retrieving it through the same parser that cannot see it reproduces the blindness rather than finding it.
- Every transaction header in the file with its byte position, so each header can be compared against the position of the H2 it names. The gap between those two positions is where orphans live.
- The audit log lines for the file, matched to the headers. A logged write with no corresponding content inside the named section is the pairing that proves the loss rather than suggesting it.
- The script or command that performed the write, specifically its section-boundary calculation. A single wrong offset explains many orphans at once, and fixing the file without fixing the calculation guarantees a repeat.
- Every other substrate file written in the same run. This class arrives in batches, so a single-file finding almost always understates it.

## Analysis prompt

Given the raw substrate file, its transaction headers, and the audit log lines for the run that wrote them:

1. Walk the file line by line and report every bullet that is not inside an H2 body, with its line number and the two headings it sits between. Do this on the raw text; do not use a section-aware parser, because the parser cannot see what you are looking for.
2. For each transaction header, report its line and the line of the H2 it names. Where any content sits between them, report that content. A nonzero gap containing content is shape 1, and it is the most common.
3. Compare the file's total bullet count against the sum of bullets inside sections. Report both numbers. Their difference is the size of the loss, and it is the one number a reader can check without trusting the walk.
4. For each orphan, read the nearest transaction header above it and report which section the write intended. That intent is the only evidence of where the bullet belongs, so record it before any edit moves it.
5. Match the audit log lines against the sections. Report every logged write whose content is not present inside the section it names. This pairing is what turns a formatting observation into a correctness finding.
6. Determine what wrote the file, and report how it computes the end of a section. State whether it inserts at a computed offset or before the next H2 prefix. An offset-based insert is the mechanism; name it rather than describing the symptom.
7. Check every other substrate file touched by the same run and report the count per file. Report zero explicitly where a file is clean, because a batch failure with one clean file is a different diagnosis from one that hit everything.
8. Recommend, in order: reassign each orphan to the section its own transaction header names, then re-emit a clean header above the corrected section; fix the writing automation to locate a section's end by finding the next H2 prefix at line start and to insert before that boundary rather than at a computed offset; add a post-write check that re-parses the modified file and confirms the new content sits inside the section the header references; and add a scan that walks each substrate file and flags any bullet between two H2 boundaries, since the existing header and per-line guards both pass on this defect by construction. Leave the original audit lines in place: they remain valid under the per-line contract, and rewriting them to match the corrected file would edit the record rather than the mistake.

## Severity rubric

- **P2**: orphan bullets in an active task's substrate, where the content is recoverable from the file and the fix is a move. Justification for the ceiling: nothing is lost from disk and no product behavior is affected. It stays at P2 rather than dropping lower because the content is unreadable to every command that consumes the file, so a task can proceed on a substrate that is missing observations it appears to contain.
- **P2 also**: a substrate-write automation that inserts at a computed offset rather than before the next heading boundary, whether or not it has produced an orphan yet. The defect is in the mechanism and its output is a matter of line arithmetic.
- **P1**: orphaned content in `DECISIONS.md` specifically, where the unreadable bullet is part of a locked decision. Downstream commands read decisions to constrain their own work, and one they cannot see is one they will not honor.

## Confidence factors

- **HIGH**: a bullet between a transaction header and the H2 that header names. Two positions in one file, no interpretation.
- **MEDIUM**: a bullet in the gap between two sections with no header immediately above it, where the intended owner has to be inferred from content rather than read from a header.
- **LOW**: a bullet inside a fenced code block that happens to sit between two headings. It is content, not structure, and a naive line scan will report it; check the fence before reporting.

## Examples

### Positive (write landed one boundary early)

```
<!-- wos:write owner=approve-proposed section='## Observations' run_id=... -->
- **2026-06-05:** the retry path fires before the guard reads the flag
<!-- wos:write owner=approve-proposed section='## Observations' run_id=... -->
## Observations
(original section body here)
```

The audit log has a line saying the observation was written to `## Observations`. The section does not contain it. Every command that reads the file by section reads the original body and never sees the new bullet, and the header stacked above it makes the file look like it was written twice rather than wrongly once.

### Negative (inside the section it was aimed at)

```
<!-- wos:write owner=approve-proposed section='## Observations' run_id=... -->
## Observations
- **2026-06-05:** the retry path fires before the guard reads the flag
```

One header, one heading, and the content below the heading where a section-scoped read will find it. The audit line and the file agree, which is the property the protocol exists to produce.

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

A substrate file (TASK_STATE.md, IMPLEMENTATION_PLAN.md, DECISIONS.md, SOURCE_OF_TRUTH.md) contains one or more Markdown bullet lines that sit BETWEEN two H2 section headers without being inside either section's content area. A reader walking the file sees the bullet but cannot attribute it to a section -- the K.2 transaction header above the next H2 is meant to apply to that next H2, not to the orphan bullet.

The K.5 validator passes (JSONL line shape is correct per-line), but the substrate's section structure is broken: the bullet exists, but no section owns it.

## Detection

Look for:
- A bullet line (starts with `- ` or `* `) that appears AFTER a `<!-- wos:write owner=... -->` K.2 header but BEFORE the H2 line that the header is meant to introduce
- A bullet line that appears AFTER an H2's content closes but BEFORE the next H2 (i.e., in the "gap" between sections)
- Multiple K.2 headers stacked back-to-back with bullets interleaved between them

Concrete pattern (mangled):

```
<!-- wos:write owner=approve-proposed section='## Observations' run_id=... -->
- **2026-06-05 (jtbd...):** ...    <-- ORPHAN: bullet placed before the section H2
<!-- wos:write owner=approve-proposed section='## Observations' run_id=... -->
## Observations
(original section body here)
```

Compare to the canonical clean pattern:

```
<!-- wos:write owner=approve-proposed section='## Observations' run_id=... -->
## Observations
- **2026-06-05 (jtbd...):** ...    <-- correctly inside section
```

## Why this matters

- Substrate readers (commands like `sync-task-state`, `where-we-at`) parse by walking H2 boundaries. An orphan bullet is invisible to section-scoped reads -- it exists in the file but is not part of any addressable section.
- K.2 protocol audit headers attribute writes to specific H2 sections. An orphan write produces a JSONL line claiming to write to a section, but the bullet does not actually land inside that section's bounds.
- `repo-consistency-sweep` substrate audit (K.4) detects header drift; it does NOT currently detect bullet-bounds drift. So K.4 + K.5 both pass but the substrate is structurally broken.

## Root causes

The pattern surfaces when a substrate-write script that automates K.2 emission has a bug in `find_section_bounds()` -- specifically when the bullet is appended at the offset where the script thinks the section ends but actually that offset is BEFORE the next H2 (off-by-one or H2-detection-too-greedy). Empirically surfaced during the ADR-0036 Path B Workflow apply (commit dc8e7e9): 6-dispatch fleet-runs script appended bullets at section-end offsets that were 1+ lines BEFORE the H2 line, producing orphan bullets between sections.

Other causes:
- Manual edit that pastes a bullet in the wrong place (between H2s instead of inside one)
- A persona's PROPOSED block output that includes incorrect indentation or stray newlines
- A merge conflict resolution that moves a bullet outside its section accidentally

## Fix

1. Identify all orphan bullets via the detection pattern above
2. Reassign each to its intended section (read the bullet's K.2 header to determine intent)
3. Re-emit a clean K.2 header above the corrected section
4. The JSONL audit lines for the original (orphan) writes remain valid per K.5 (per-line shape only); the file rewrite preserves audit-trail integrity
5. Run `scripts/scan-substrate-headers.sh` + `scripts/verify-log-validator.py` after the fix to confirm clean state

## Prevention

- Substrate-write automation scripts MUST locate the END of a section by finding `\n## ` (next H2 prefix at line start) and inserting BEFORE that boundary, not at the offset
- Add a post-write sanity check: after applying a write, parse the modified file and confirm the new bullet is in the same section the K.2 header references
- Consider adding a `scripts/scan-substrate-orphans.sh` that walks each substrate file and flags any bullet between two H2 boundaries that isn't inside the first section's body

## Related

- ADR-0034 (substrate peers + worker contract)
- ADR-0036 (K.7 oscillation + L3 evidence weighting; surfaced this bug during Path B implementation)
- `commands/_shared/substrate-write-protocol.md` (canonical K.2 protocol with bash helpers)
- `wos/bug-classes/documentation-drift.md` (sibling class for natural-language drift)

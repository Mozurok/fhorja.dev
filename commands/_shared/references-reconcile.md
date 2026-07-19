**References reconcile (X2, 2026-07-18).** Reconcile the references a task cited (its `REFERENCES.md` deliverable, an `EXTERNAL_RESEARCH.md`, or the project-level references it grounded in) against what the task actually shipped, enforcing "cite only what you used." Lifecycle-aware: it reports at a mid-task checkpoint and hard-fails only when finalizing the whole task.

1. Gate on presence. This sub-check fires only WHEN the task produced or cited references: a `REFERENCES.md` or `EXTERNAL_RESEARCH.md` in the task folder, or a `Grounded in:` citation in the shipped work. WHEN none is present, it is a no-op: skip and proceed.

2. Classify the context. A finalization run is `task-close` (or `review-hard` as the pre-PR final pass). A checkpoint run is `slice-closure` or `where-we-at`. At a checkpoint a cited reference not yet reflected is normal in-progress work, not a defect.

3. Reconcile cited vs reflected. For each reference the task cited, confirm the shipped work materially reflects it (a real layout, behavior, or decision traceable to that reference), not merely a name-drop. A reference cited with no material trace in the shipped work is a cited-but-unused reference: this is the failure the brief names ("if the final result does not reflect the references you cited, the REFERENCES.md is wrong").

4. Apply the gate by context.
   - WHEN finalizing: IF any cited reference is unused (no material trace) THEN name it and require either removing the citation or pointing to where it is reflected, and route to `implement-slice-complement` (fix the citation) before closing.
   - WHILE at a checkpoint: report each cited-but-unused reference as a must-address finding (name it, route to `implement-slice-complement`), and do NOT invalidate the whole output on that basis.

"Cite only what you used" is the invariant. This is the produce-side gate for the `capture-references` and `external-research` artifacts, the design-and-research analog of the deliverable-reconcile completeness check.

**References reconcile.** Reconcile the references a task cited (`REFERENCES.md`, `EXTERNAL_RESEARCH.md`, or project-level references) against what it shipped. Reports at a mid-task checkpoint; hard-fails only when finalizing the whole task.

1. This sub-check fires only WHEN the task produced or cited references: a `REFERENCES.md` or `EXTERNAL_RESEARCH.md` in the task folder, or a `Grounded in:` citation in the shipped work. WHEN none is present, it is a no-op: skip and proceed.

2. Finalization: `task-close` (or `review-hard` as the pre-PR final pass). Checkpoint: `slice-closure` or `where-we-at`. At a checkpoint a cited reference not yet reflected is normal in-progress work.

3. Reconcile cited vs reflected. For each cited reference, confirm the shipped work materially reflects it (a real layout, behavior, or decision traceable to it), not merely a name-drop. A reference with no material trace is cited-but-unused.

4. Apply the gate by context.
   - WHEN finalizing: IF any cited reference is unused (no material trace) THEN name it and require removing the citation or pointing to where it is reflected, and route to `implement-slice-complement` before closing.
   - WHILE at a checkpoint: report each cited-but-unused reference as a must-address finding (name it, route to `implement-slice-complement`), and do NOT invalidate the whole output on that basis.

"Cite only what you used" is the invariant.

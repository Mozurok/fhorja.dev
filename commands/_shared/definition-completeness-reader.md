**Definition-completeness reader (shared engine, D-5 of the 2026-07-27 readiness task).** One reader, two consumers: `problem-framing` runs it at intake over a supplied spec, `autonomous-readiness` runs it at boot over the project's own artifacts. The criteria and the reporting shape are identical; only the source set and what the caller does with the result differ. Two implementations of the same question drift, and the drift would show up as a gate booting a run the intake had already called underspecified.

1. **Read, never fill.** The reader REPORTS what each criterion's sources say and what they do not say. It SHALL NOT answer a criterion on the user's behalf, and it SHALL NOT record its own inference as a confirmed fact or a locked decision. A criterion the sources leave open is reported open. This is the load-bearing rule: a reader that quietly fills gaps turns an unprepared project into a green light, which is the exact failure the reader exists to prevent.

2. **The criteria.** For each one, name the source actually read (file plus section) or report it absent:
   - Objective: what the work is for, stated in the product's terms rather than the workflow's.
   - Success criteria: user-observable and checkable, not a restatement of the objective.
   - Non-goals: what is deliberately out of scope.
   - Stack and workspace: what is being built on, and where the code lives.
   - Constraints: what must not change.
   - Named deliverables: the concrete things the user asked for by name.
   - Locked decisions: for every boundary the work will touch (schema, contract, auth, migration, permission), whether a decision covering it is locked or still open.
   - Declared surfaces: which runtime surfaces the work produces (web, backend HTTP, mobile app, game, database), because each one needs an evidence adapter downstream.

3. **Three statuses, and nothing else.** Report each criterion as `present` (naming the source read), `partial` (naming both what is there and what is missing), or `missing`. A status carries the source it came from, never a degree of confidence; a status whose source slot is empty reads as unknown, not as a weak yes (`wos/active-epistemic-humility.md`).

4. **Incremental by construction.** The reader is stateless and re-runnable: it reads the sources as they are now. Filling a gap in the SOURCE and re-running SHALL flip that criterion without anyone hand-editing the ledger. A reader whose output has to be corrected by hand has failed, because the hand-edit is exactly the unverified claim the ledger was supposed to expose.

5. **The reader emits no verdict of its own.** It produces the per-criterion table and stops. The caller decides what a given status set means: at intake it shapes the next question, at boot it decides BOOT or NOT-READY. Keeping the verdict out of the reader is what lets both consumers share it without one inheriting the other's policy.

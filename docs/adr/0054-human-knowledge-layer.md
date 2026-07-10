# ADR-0054: A human-first knowledge layer, decoupled from AI task memory

- **Status**: Accepted
- **Date**: 2026-06-25
- **Tags**: memory, knowledge-layer, human-first, project-memory, living-docs, no-app-dependency, additive, claude-obsidian-prior-art

## Context

The 2026-06-25 analysis of `claude-obsidian` produced two shipped absorptions, both moving memory automation INTO the AI's task memory: the session-continuity hook (ADR-0052) and memory-lint (ADR-0053). That same analysis deferred a third item, a cross-task lessons rollup (its D-5), specifically over scope-creep risk: an AI that silently carries every past learning forward into every new task widens scope on its own.

The maintainer wants the opposite shape. The need is a per-project record of a project's evolution, history, and the learnings that actually mattered, written for a human to read, that the AI does not consume on every run. When a past learning is relevant, the human re-injects a chosen slice into a new task. Alongside it, two related wants: a per-project task timeline, and human-facing living documentation that improves a little as tasks close.

Constraints shape the answer. The WOS stance is plain Markdown plus bash, no app dependency, no database, no embeddings (the prior D-3 declined a retrieval pipeline). `projects/` is gitignored per ADR-0007 (per-user memory). ADR-0049 already established the pattern for a human-readable view: a generated, dependency-free, gitignored artifact rendered on demand. And `code-context-map` already provides the AI-readable-code view, so the AI half of "living docs" exists.

## Decision

Add an additive, human-first knowledge layer, decoupled from AI task memory. The design is locked as D-1 through D-7 in the `2026-06-25_human-knowledge-and-living-docs` task DECISIONS.md:

- A single per-project `KNOWLEDGE.md` (plain Markdown, gitignored) holds evolution, history, and retained learnings for human reading, distinct from the four task-memory files that hold AI operational state (D-1).
- It is plain Markdown with no external-app dependency; Obsidian or any alternative is an optional read-only consumer, not a WOS dependency (D-2).
- The AI never auto-loads it. Re-entry into AI context happens only through explicit human paste of a chosen slice into a task prompt (D-3), enforced by a normative rule in `task-init` plus a regression eval scenario (D-5).
- One bounded entry is appended when a task closes, folded into `task-close` rather than a new command, with no per-slice write (D-4).
- The per-project task timeline extends the ADR-0049 generator (`scripts/build-activity-timeline.py`) to project scope rather than introducing a new logging mechanism (D-6).
- The mechanism (generator, template, command logic) ships in the distribution; the generated per-project content stays gitignored, mirroring ADR-0049 (D-7).

This resolves the archived claude-obsidian task's deferred D-5 by choosing the human-first path: learnings accumulate in a human-read layer with on-demand re-injection, not an AI-consumed rollup.

## Consequences

### Positive

- Gives a durable human-facing project history and living documentation without re-coupling the AI to past learnings, honoring the anti-scope-creep intent that deferred D-5.
- Stays inside the plain-Markdown, no-app, no-embeddings stance; reuses ADR-0049 and `code-context-map` instead of new machinery.
- Closes the open D-5 with a reversible, low-risk design: the layer is gitignored per-user content and the writer is one bounded append.

### Negative

- Value depends on the human reading and re-injecting; a layer that is never read adds nothing.
- The no-auto-load invariant must be guarded by the eval scenario or a future change can silently re-couple the layer.
- One more per-project artifact to keep tidy alongside REFERENCES.md.

### Neutral

- `KNOWLEDGE.md` sits beside `REFERENCES.md` as a second per-project gitignored file.
- The project timeline shares the ADR-0049 data source (the audit log), so it inherits that generator's defensive parsing and on-demand liveness.

## Alternatives considered

### Alternative 1: an AI-consumed cross-task knowledge index (the deferred D-5 rollup)

- A standing index (embeddings or BM25) the AI reads to carry learnings forward automatically.
- Rejected: this is the scope creep the maintainer is avoiding, and the prior D-3 already declined a retrieval pipeline at WOS scale.

### Alternative 2: adopt Obsidian or an alternative app as the store

- Use an external PKM app as the actual knowledge store.
- Rejected: conflicts with the no-app-dependency stance and adds a hard dependency for a local convenience. The 10 captured Obsidian-alternative references inform compatibility, not a tool pick.

### Alternative 3: a new dedicated knowledge command

- A standalone command that writes the knowledge layer.
- Rejected: folds into `task-close` (D-4) to avoid four-registry and count-marker growth, following the ADR-0053 fold-over-new-command precedent.

## References

- `projects/bmazurok__my-work-tasks/active/2026-06-25_human-knowledge-and-living-docs/DECISIONS.md` (D-1 through D-7, the locked design).
- `docs/adr/0049-activity-timeline-html-view.md` (the generated-view precedent the timeline extends).
- `docs/adr/0052-session-continuity-hook.md` and `docs/adr/0053-memory-lint-mode.md` (the claude-obsidian absorption this complements).
- `docs/adr/0007-project-level-memory.md` (gitignored `projects/`).
- `commands/code-context-map.md` (the AI-readable-code half of living docs).
- [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (prior art whose deferred rollup this resolves; accessed 2026-06-25).

## Notes

The layer is per-user content under gitignored `projects/`; only the mechanism ships (D-7). If a future need arises for the AI to consume the layer programmatically, that reopens D-3 and D-5 and requires a new ADR rather than a patch to this one.

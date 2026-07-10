# ADR-0055: The knowledge layer's visual organization: a linked `knowledge/` folder, a generated view, and human-gated linking

- **Status**: Accepted
- **Date**: 2026-06-26
- **Tags**: memory, knowledge-layer, visual-organization, wikilinks, map-of-content, generated-view, obsidian-compatible, no-app-dependency, additive, amends-adr-0054

## Context

ADR-0054 established the human-first knowledge layer as a single flat `KNOWLEDGE.md`, appended at task-close, never auto-loaded. A 2026-06-26 review against the original brief surfaced two gaps: the brief asked for a visual documentation "no mesmo estilo de organização do Obsidian," not a flat log, and the Obsidian-alternative sources the user had captured were never analyzed.

The analysis was then produced (`EXTERNAL_RESEARCH.md`, 9 sources including Obsidian itself). Its finding: across Obsidian and its alternatives, the consensus organizing model is wikilinks plus backlinks plus an index (map of content), and that model is plain-Markdown-native. Graph and Canvas are app-rendered views, not storage formats. Obsidian itself stores plain Markdown with explicit no-lock-in, so adopting its link conventions costs no dependency. This means the visual, Obsidian-style organization can be delivered while reinforcing, not reversing, ADR-0054's D-2 (plain Markdown, no app dependency).

## Decision

Amend ADR-0054's shape and close-write mechanism per decisions D-8 through D-11 of the `2026-06-25_human-knowledge-and-living-docs` task:

- **D-8 (organization):** organize the knowledge notes with Obsidian-flavored wikilinks (`[[...]]`) and a per-project index note (map of content), in plain Markdown. Any graph or canvas view stays an optional Obsidian-rendered layer, not a WOS dependency.
- **D-9 (shape):** store the layer as a per-project `knowledge/` folder containing one note per closed task plus an `index.md`, rather than a single flat file. This supersedes ADR-0054's flat-`KNOWLEDGE.md` shape.
- **D-10 (view):** generate a navigable knowledge HTML view (a sibling to the ADR-0049 activity timeline) that renders the index and the wikilinks, so users without Obsidian still get a visual, app-independent view.
- **D-11 (linking):** at task-close, write the deterministic links (to the task folder, the index, and the task's DECISIONS) automatically, and propose candidate topic links and tags for the human to confirm or edit at close. Never silently insert unverified topic links.

The no-auto-load invariant (D-3, D-5) and the per-project timeline (D-6) carry over unchanged; the folder is still gitignored per-user content with only the mechanism shipped (D-7).

## Consequences

### Positive

- Delivers the visual, Obsidian-style organization the original brief asked for, without an app dependency: a linked `knowledge/` folder is an Obsidian-compatible vault, so the graph and Canvas come for free when the human opens it in Obsidian.
- Reinforces D-2 (Obsidian is itself plain Markdown) rather than reversing it.
- Reuses the ADR-0049 render-not-mutate pattern for the generated knowledge view.
- The human-gated linking (D-11) keeps the WOS from guessing wrong topic links while still actively proposing rich links.

### Negative

- More moving parts than the flat file: a folder, an index, a confirm step at close, and a second generator.
- The Phase 1 flat-file template and the flat-append task-close fold (built under ADR-0054) need revision to the folder shape.

### Neutral

- The `knowledge/` folder sits beside `REFERENCES.md` and the gitignored timeline output. The generated knowledge HTML view is a sibling to `ACTIVITY.html`.

## Alternatives considered

### Alternative 1: a single flat file with internal anchors and wikilinks

- Keep one `KNOWLEDGE.md`, add wikilinks and a top index inside it.
- Rejected: a single file is one graph node in Obsidian, a worse fit for "see the evolution and history of each project." The folder gives one node per task, which is the Obsidian-native structure the user asked for.

### Alternative 2: adopt Obsidian (or an alternative app) as the store

- Use an external PKM app as the actual knowledge store.
- Rejected per D-2: it adds a hard app dependency for a local convenience. The captured alternatives inform the link conventions, not a tool choice.

### Alternative 3: fully-silent aggressive auto-linking

- Have task-close auto-detect topics and insert `[[topic]]` links and tags without asking.
- Rejected: the WOS would guess wrong or noisy links. D-11 keeps aggressive coverage but gates topic links behind a human confirm at close.

## References

- `docs/adr/0054-human-knowledge-layer.md` (the foundational decision this amends).
- `docs/adr/0049-activity-timeline-html-view.md` (the generated-view pattern the knowledge HTML view reuses).
- `projects/bmazurok__my-work-tasks/active/2026-06-25_human-knowledge-and-living-docs/DECISIONS.md` (D-8 through D-11).
- `projects/bmazurok__my-work-tasks/active/2026-06-25_human-knowledge-and-living-docs/EXTERNAL_RESEARCH.md` (the 9-source synthesis that grounds D-8).
- [Obsidian](https://obsidian.md/) (the baseline: plain-Markdown vault, wikilinks, graph, Canvas, no lock-in; accessed 2026-06-26).

## Notes

ADR-0054 stays as the foundational decision (the human-first layer, the no-auto-load invariant, written at task-close); this ADR amends only the shape and the linking model. If the folder ever needs a real graph engine rather than a rendered index plus links, that is a new decision and a new ADR.

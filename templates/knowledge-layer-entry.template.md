<!--
Template for ONE per-task note in the per-project human knowledge layer (ADR-0054, ADR-0055; D-8, D-9, D-11).

WHERE this goes: projects/<client>__<project>/knowledge/<task-slug>.md (one note per
closed task). The folder is gitignored. The index lives at knowledge/index.md (see
templates/knowledge-index.template.md).

WHO writes it: task-close creates the note and updates the index (D-11). Nothing else
writes here. Keep a note short (target 120 to 220 words of body). This is a human-read
record, not a full task log.

LINKS: task-close writes the deterministic links automatically (to the task, the index,
the decisions). The topic links and tags are PROPOSED at close and confirmed or edited by
the human; Fhorja never inserts unverified topic links silently.

NEVER auto-loaded: the AI does not read the knowledge/ folder. Its content reaches the AI
only when a human pastes an excerpt into a task prompt (D-3, D-5).

The YAML frontmatter is Obsidian-compatible (properties); `tags` and `[[wikilinks]]` drive
Obsidian's graph and the generated knowledge HTML view.
-->
---
task: <YYYY-MM-DD_task-slug>
date: <YYYY-MM-DD>
tags: [<topic>, <topic>]   # proposed at close, human-confirmed (D-11)
---
# <Task title>

- Task: [[<YYYY-MM-DD_task-slug>]]            <!-- deterministic link (auto) -->
- Index: [[index]]                            <!-- deterministic link (auto) -->
- Decisions: that task's `DECISIONS.md`       <!-- deterministic link (auto) -->
- Topics: [[<topic>]], [[<topic>]]            <!-- proposed at close, human-confirmed -->

What it did: <one short paragraph in plain language: the outcome, not a play-by-play.>

Learnings that mattered:
- <a durable lesson worth carrying forward; omit the section if there were none>

What changed in the product or system:
- <the concrete change a future reader should know about>

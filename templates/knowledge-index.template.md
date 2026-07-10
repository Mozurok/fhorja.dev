<!--
Template for the per-project knowledge index, the map of content (ADR-0055; D-8, D-9).

WHERE this goes: projects/<client>__<project>/knowledge/index.md (one per project).
WHO writes it: task-close adds a wikilink to each new note when it closes a task (D-11),
under "By date" (newest first) and under the confirmed topics in "By topic". Nothing else
writes here. The folder is gitignored.

This is the human entry point and the navigable hub of the vault: in Obsidian it is the
note everything links back to; in the generated knowledge HTML view (scripts/build-knowledge-view.py)
it is the landing page. The AI does not read it (never auto-loaded).
-->
# Knowledge index: <client>__<project>

Map of content for this project's human knowledge layer. One note per closed task. The AI
does not read this folder; open it in Obsidian for the graph and Canvas, or generate the
knowledge HTML view with `scripts/build-knowledge-view.py`.

## By date (newest first)
- <YYYY-MM-DD> [[<task-slug>]] -- <one-line what it was>

## By topic
### <topic>
- [[<task-slug>]]

### <topic>
- [[<task-slug>]]
